import asyncio
import io
import json
import os
import time
import zipfile
import pandas as pd
import requests
import PIL.Image as Image
from moviepy.video.io.VideoFileClip import VideoFileClip

from nostr_dvm.utils.output_utils import upload_media_to_hoster

"""
This file contains basic calling functions for ML tasks that are outsourced to nova server. It is an Open-Source backend
that enables running models locally based on preefined modules, by accepting a request.
Modules are deployed in in separate virtual environments so dependencies won't conflict. 
"""

"""
send_request_to_n_server(request_form, address)
Function to send a request_form to the server, containing all the information we parsed from the Nostr event and added
in the module that is calling the server

"""

def send_request_to_server(request_form, address):
    print("Sending job to Server")
    url = ('http://' + address + '/process')
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    response = requests.post(url, headers=headers, data=request_form)
    return response.text


def send_file_to_server(filepath, address):
    result = ""
    print("Sending file to Server")
    url = ('http://' + address + '/upload')
    try:
        fp = open(filepath, 'rb')
        response = requests.post(url, files={'file': fp})
        result = response.content.decode('utf-8')
    except Exception as e:
        print(e)
        print(response.content.decode('utf-8'))

    return result

"""
check_n_server_status(request_form, address)
Function that requests the status of the current process with the jobID (we use the Nostr event as jobID).
When the Job is successfully finished we grab the result and depending on the type return the output
We throw an exception on error
"""


def check_server_status(jobID, address) -> str | pd.DataFrame:
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    url_status = 'http://' + address + '/job_status'
    url_log = 'http://' + address + '/log'

    print("Sending Status Request to Server")
    data = {"jobID": jobID}

    status = 0
    length = 0
    while status != 2 and status != 3:
        response_status = requests.post(url_status, headers=headers, data=data)
        response_log = requests.post(url_log, headers=headers, data=data)
        status = int(json.loads(response_status.text)['status'])
        log_content = str(json.loads(response_log.text)['message']).replace("ERROR", "").replace("INFO", "")
        log = log_content[length:]
        length = len(log_content)
        if log != "":
            print(log)
        # WAITING = 0, RUNNING = 1, FINISHED = 2, ERROR = 3
        time.sleep(1.0)


    if status == 2:
        try:
            url_fetch = 'http://' + address + '/fetch_result'
            print("Fetching Results from Server...")
            data = {"jobID": jobID, "delete_after_download": True}
            response = requests.post(url_fetch, headers=headers, data=data)
            content_type = response.headers['content-type']
            print("Content-type: " + str(content_type))
            if content_type == "image/jpeg":
                image = Image.open(io.BytesIO(response.content))
                image.save("./outputs/image.jpg")
                result = asyncio.run(upload_media_to_hoster("./outputs/image.jpg"))
                os.remove("./outputs/image.jpg")
                return result
            elif content_type == 'video/mp4':
                with open('./outputs/video.mp4', 'wb') as f:
                   f.write(response.content)
                f.close()
                clip = VideoFileClip("./outputs/video.mp4")
                clip.write_videofile("./outputs/video2.mp4")
                result = asyncio.run(upload_media_to_hoster("./outputs/video2.mp4"))
                clip.close()
                os.remove("./outputs/video.mp4")
                os.remove("./outputs/video2.mp4")
                return result
            elif content_type == 'text/plain; charset=utf-8':
                return response.content.decode('utf-8')
            elif content_type == "application/x-zip-compressed":
                zf = zipfile.ZipFile(io.BytesIO(response.content), "r")

                for fileinfo in zf.infolist():
                    if fileinfo.filename.endswith(".annotation~"):
                        try:
                            anno_string = zf.read(fileinfo).decode('utf-8', errors='replace')
                            columns = ['from', 'to', 'name', 'conf']
                            result = pd.DataFrame([row.split(';') for row in anno_string.split('\n')],
                                                  columns=columns)
                            return result
                        except Exception as e:
                            print(e)
        except Exception as e:
            print("Couldn't fetch result: " + str(e))

    elif status == 3:
        return "error"