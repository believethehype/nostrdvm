
from typing import Any
from urllib.request import urlopen, Request

import requests
import json
import yt_dlp
import sys
import os
import re

import requests
import bs4

from tqdm import tqdm
from pathlib import Path

browser = "chrome" #"firefox"

def download_xvideo(url, target_location) -> None:
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get("content-length", 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size, unit="B", unit_scale=True)
    download_path = target_location
    with open(download_path, "wb") as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)

    progress_bar.close()
    print("Video downloaded successfully!")


def XDownload(url, filepath=""):
    api_url = f"https://twitsave.com/info?url={url}"

    response = requests.get(api_url)
    data = bs4.BeautifulSoup(response.text, "html.parser")
    download_button = data.find_all("div", class_="origin-top-right")[0]
    quality_buttons = download_button.find_all("a")
    highest_quality_url = quality_buttons[0].get("href")  # Highest quality video url
    download_xvideo(highest_quality_url, filepath)
    return filepath


def getDict() -> dict:
    response = requests.get('https://ttdownloader.com/')
    point = response.text.find('<input type="hidden" id="token" name="token" value="') + \
            len('<input type="hidden" id="token" name="token" value="')
    token = response.text[point:point + 64]
    TTDict = {
        'token': token,
    }

    for i in response.cookies:
        TTDict[str(i).split()[1].split('=')[0].strip()] = str(
            i).split()[1].split('=')[1].strip()
    return TTDict


def createHeader(parseDict) -> tuple[dict[str, Any], dict[str | Any, str | Any], dict[str, str | Any]]:
    cookies = {
        'PHPSESSID': parseDict['PHPSESSID'],
        # 'popCookie': parseDict['popCookie'],
    }
    headers = {
        'authority': 'ttdownloader.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://ttdownloader.com',
        'referer': 'https://ttdownloader.com/',
        'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/108.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }
    data = {
        'url': '',
        'format': '',
        'token': parseDict['token'],
    }
    return cookies, headers, data


def TikTokDownload(cookies, headers, data, name, path) -> str:
    response = requests.post('https://ttdownloader.com/search/',
                             cookies=cookies, headers=headers, data=data)
    parsed_link = [i for i in str(response.text).split()
                   if i.startswith("href=")][0]

    response = requests.get(parsed_link[6:-10])
    with open(path + "\\" + name + ".mp4", "wb") as f:
        f.write(response.content)
    return path + "\\" + name + ".mp4"


def TiktokDownloadAll(linkList, path) -> str:
    parseDict = getDict()
    cookies, headers, data = createHeader(parseDict)
    # linkList = getLinkDict()['tiktok']
    for i in linkList:
        try:
            data['url'] = i
            result = TikTokDownload(cookies, headers, data, "tiktok", path)  # str(linkList.index(i))
            return result
        except IndexError:
            parseDict = getDict()
            cookies, headers, data = createHeader(parseDict)
        except Exception as err:
            print(err)
            exit(1)


def YTDownload(link, path, audio_only=True):

    if audio_only:
        return get_audio([link])
    else:
        return get_video([link])


def get_media_duration(url):
    try:
        # ℹ️ See help(yt_dlp.YoutubeDL) for a list of available options and public functions
        ydl_opts = {
            'cookiesfrombrowser': (browser, None, None, None),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # ℹ️ ydl.sanitize_info makes the info json-serializable
            return float(json.dumps(ydl.sanitize_info(info)["duration"]))
    except:
        return None

def get_media_info(url):
    try:
        # ℹ️ See help(yt_dlp.YoutubeDL) for a list of available options and public functions
        ydl_opts = {
            'cookiesfrombrowser': (browser, None, None, None),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # ℹ️ ydl.sanitize_info makes the info json-serializable
            return json.dumps(ydl.sanitize_info(info))
    except:
        return None


def get_audio(URLS):
    try:
        ydl_opts = {
            'cookiesfrombrowser': (browser, None, None, None),
            'format': 'm4a/bestaudio/best',
            "outtmpl": 'outputs/audio',
            'overwrites': 'True',
            # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
            'postprocessors': [{  # Extract audio using ffmpeg
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download(URLS)

        return "outputs/audio.mp3"
    except:
        return None


def get_video(URLS):
    try:
        ydl_opts = {
            'cookiesfrombrowser': (browser, None, None, None),
            'format': 'mp4',
            'overwrites': 'True',
            # "outtmpl": '/%(uploader)s_%(title)s.%(ext)s',
            "outtmpl": 'outputs/video.mp4',
        }


        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(URLS)
        return "outputs/video.mp4"

    except:
        return None


# OVERCAST
def OvercastDownload(source_url, target_location):
    def get_title(html_str):
        """Get the title from the meta tags"""

        title = re.findall(r"<meta name=\"og:title\" content=\"(.+)\"", html_str)
        if len(title) == 1:
            return title[0].replace("&mdash;", "-")
        return None

    def get_description(html_str):
        """Get the description from the Meta tag"""

        desc_re = r"<meta name=\"og:description\" content=\"(.+)\""
        description = re.findall(desc_re, html_str)
        if len(description) == 1:
            return description[0]
        return None

    def get_url(html_string):
        """Find the URL from the <audio><relay_timeout>.... tag"""

        url = re.findall(r"<relay_timeout src=\"(.+?)\"", html_string)
        if len(url) == 1:
            # strip off the last 4 characters to cater for the #t=0 in the URL
            # which urlretrieve flags as invalid
            return url[0][:-4]
        return None

    """Given a Overcast relay_timeout URL fetch the file it points to"""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.11 (KHTML, like Gecko) "
                      "Chrome/23.0.1271.64 Safari/537.11",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
        "Accept-Encoding": "none",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
    }
    req = Request(source_url, None, headers)
    source_data = urlopen(req).read().decode('utf-8')
    title = get_title(source_data)
    url = get_url(source_data)

    if url is None or title is None:
        sys.exit("Could not find parse URL")
    if not os.path.exists(target_location):
        req = requests.get(url)
        file = open(target_location, 'wb')
        for chunk in req.iter_content(100000):
            file.write(chunk)
        file.close()
