import io
import json
import os
import time
import zipfile
import pandas as pd
import requests
import PIL.Image as Image

from utils.output_utils import upload_media_to_hoster

"""
This file contains basic calling functions for ML tasks that are outsourced to nova-server 
(https://github.com/hcmlab/nova-server). nova-server is an Open-Source backend that enables running models locally
 based on preefined modules (nova-server-modules), by accepting a request form.
 Modules are deployed in in separate virtual environments so dependencies won't conflict. 

Setup nova-server:
https://hcmlab.github.io/nova-server/docbuild/html/tutorials/introduction.html

"""

"""
send_request_to_nova_server(request_form, address)
Function to send a request_form to the server, containing all the information we parsed from the Nostr event and added
in the module that is calling the server

"""


def send_request_to_nova_server(request_form, address):
    print("Sending job to NOVA-Server")
    url = ('http://' + address + '/process')
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    response = requests.post(url, headers=headers, data=request_form)
    return response.text


"""
check_nova_server_status(request_form, address)
Function that requests the status of the current process with the jobID (we use the Nostr event as jobID).
When the Job is successfully finished we grab the result and depending on the type return the output
We throw an exception on error
"""


def check_nova_server_status(jobID, address):
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    url_status = 'http://' + address + '/job_status'
    url_log = 'http://' + address + '/log'

    print("Sending Status Request to NOVA-Server")
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
            result = ""
            url_fetch = 'http://' + address + '/fetch_result'
            print("Fetching Results from NOVA-Server...")
            data = {"jobID": jobID, "delete_after_download": True}
            response = requests.post(url_fetch, headers=headers, data=data)
            content_type = response.headers['content-type']
            print("Content-type: " + str(content_type))
            if content_type == "image/jpeg":
                image = Image.open(io.BytesIO(response.content))
                image.save("./outputs/image.jpg")
                result = upload_media_to_hoster("./outputs/image.jpg")
                os.remove("./outputs/image.jpg")
            elif content_type == 'text/plain; charset=utf-8':
                result = response.content.decode('utf-8')
            elif content_type == "zip":
                zf = zipfile.ZipFile(io.BytesIO(response.content), "r")

                for fileinfo in zf.infolist():
                    if fileinfo.filename.endswith(".annotation~"):
                        try:
                            anno_string = zf.read(fileinfo).decode('utf-8', errors='replace')
                            columns = ['from', 'to', 'name', 'conf']
                            result = pd.DataFrame([row.split(';') for row in anno_string.split('\n')],
                                                  columns=columns)
                            print(result)
                            with open("response.zip", "wb") as f:
                                f.write(response.content)
                        except Exception as e:
                            #zf.extractall()
                            print(e)

            return result
        except Exception as e:
            print("Couldn't fetch result: " + str(e))

    elif status == 3:
        return "error"
