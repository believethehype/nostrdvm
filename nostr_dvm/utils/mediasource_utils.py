import os
import urllib
from datetime import time
from urllib.parse import urlparse
import ffmpegio

import requests
from nostr_dvm.utils.nostr_utils import get_event_by_id
from nostr_dvm.utils.scrapper.media_scrapper import YTDownload, get_media_duration


async def input_data_file_duration(event, dvm_config, client, start=0, end=0):
    # print("[" + dvm_config.NIP89.NAME + "] Getting Duration of the Media file..")
    if end != 0:
        return end - start

    input_value = ""
    input_type = ""
    count = 0
    for tag in event.tags():
        if tag.as_vec()[0] == 'i':
            input_value = tag.as_vec()[1]
            input_type = tag.as_vec()[2]
            count = count + 1

    if input_type == "text":
        return len(input_value)

    if input_type == "event":  # NIP94 event
        if count > 1:
            return 1  # we ignore length for multiple event inputs for now
        evt = await get_event_by_id(input_value, client=client, config=dvm_config)
        if evt is not None:
            input_value, input_type = check_nip94_event_for_media(evt, input_value, input_type)
            if input_type == "text":
                # For now, ingore length of any text, just return 1.
                return len(input_value)

    if input_type == "url":
        source_type = check_source_type(input_value)
        duration = get_media_duration(input_value)
        if duration is None:
            filename, start, end, type = get_file_start_end_type(input_value, source_type, start, end, True)
            if type != "audio" and type != "video":
                return 1
            if filename == "" or filename is None:
                return 0
            try:
                duration = ffmpegio.probe.format_basic(filename)['duration']
            except Exception as e:
                print(e)
                return 0
        print("Original Duration of the Media file: " + str(duration))
        start_time, end_time, new_duration = (
            convert_media_length(start, end, duration))
        print("New Duration of the Media file: " + str(new_duration))
        return new_duration

    return 1


async def organize_input_media_data(input_value, input_type, start, end, dvm_config, client, process=True,
                                    media_format="audio/mp3") -> str:
    if input_type == "event":  # NIP94 event
        evt = await get_event_by_id(input_value, client=client, config=dvm_config)
        if evt is not None:
            input_value, input_type = check_nip94_event_for_media(evt, input_value, input_type)

    if input_type == "url":
        source_type = check_source_type(input_value)
        audio_only = True
        if media_format.split('/')[0] == "video":
            audio_only = False

        filename, start, end, type = get_file_start_end_type(input_value, source_type, start, end, audio_only)

        if filename == "" or filename is None:
            return ""
        if type != "audio" and type != "video":
            return filename
        try:
            source_type = check_source_type(input_value)
            duration = get_media_duration(input_value)
            if duration is None:
                # file_reader = AudioReader(filename, ctx=cpu(0), mono=False)
                # duration = float(file_reader.duration())
                duration = ffmpegio.probe.format_basic(filename)['duration']

        except Exception as e:
            print(e)
            try:
                from moviepy.editor import VideoFileClip
                clip = VideoFileClip(filename)
                duration = clip.duration
            except Exception as e:
                print(e)
                return ""

        print("Original Duration of the Media file: " + str(duration))
        start_time, end_time, new_duration = (
            convert_media_length(start, end, duration))
        print("New Duration of the Media file: " + str(new_duration))

        # TODO if already in a working format and time is 0 0, dont convert

        # for now, we cut and convert all files to mp3
        if process:
            # for now we cut and convert all files to mp3
            file = r'processed.' + str(media_format.split('/')[1])
            final_filename = os.path.abspath(os.curdir + r'/outputs/' + file)
            if media_format.split('/')[0] == "audio":
                print("Converting Audio from " + str(start_time) + " until " + str(end_time))
                fs, x = ffmpegio.audio.read(filename, ss=start_time, to=end_time, sample_fmt='dbl', ac=1)
                ffmpegio.audio.write(final_filename, fs, x, overwrite=True)
            elif media_format.split('/')[0] == "video":
                print("Converting Video from " + str(start_time) + " until " + str(end_time))
                ffmpegio.transcode(filename, final_filename, overwrite=True, show_log=True)
            elif media_format.split('/')[1] == "gif":
                from moviepy.editor import VideoFileClip
                print("Converting Video from " + str(start_time) + " until " + str(end_time))
                videoClip = VideoFileClip(filename)
                videoClip.write_gif(final_filename, program="ffmpeg")
            print(final_filename)
            return final_filename
        else:
            return filename


def check_nip94_event_for_media(evt, input_value, input_type):
    # Parse NIP94 event for url, if found, use it.
    input_type = "text"
    input_value = evt.content()
    if evt.kind() == 1063:
        for tag in evt.tags():
            if tag.as_vec()[0] == 'url':
                input_type = "url"
                input_value = tag.as_vec()[1]
                return input_value, input_type

    return input_value, input_type


def convert_media_length(start: float, end: float, duration: float):
    if end == 0.0:
        end_time = duration
    elif end > duration:
        end_time = duration
    else:
        end_time = end
    if start <= 0.0 or start > end_time:
        start_time = 0.0
    else:
        start_time = start
    dur = end_time - start_time
    return start_time, end_time, dur


def get_file_start_end_type(url, source_type, start, end, audio_only=True) -> (str, str):
    #  Overcast
    if source_type == "overcast":
        name, start, end = get_overcast(url, start, end)
        return name, start, end, "audio"
    #  Youtube
    elif source_type == "youtube":
        name, start, end = get_youtube(url, start, end, audio_only)

        return name, start, end, "audio"
    #  Xitter
    elif source_type == "xitter":
        name, start, end = get_Twitter(url, start, end)
        return name, start, end, "video"
    #  Tiktok
    elif source_type == "tiktok":
        name, start, end = get_TikTok(url, start, end)
        return name, start, end, "video"
    #  Instagram
    elif source_type == "instagram":
        name, start, end = get_Instagram(url, start, end)
        if name.endswith("jpg"):
            type = "image"
        else:
            type = "video"
        return name, start, end, type
    #  A file link
    else:
        filename, filetype = get_media_link(url)
        return filename, start, end, filetype


def media_source(source_type):
    if source_type == "overcast":
        return "audio"
    elif source_type == "youtube":
        return "audio"
    elif source_type == "xitter":
        return "video"
    elif source_type == "tiktok":
        return "video"
    elif source_type == "instagram":
        return "video"
    else:
        return "url"


def check_source_type(url):
    if str(url).startswith("https://overcast.fm/"):
        return "overcast"
    elif str(url).replace("http://", "").replace("https://", "").replace(
            "www.", "").replace("youtu.be/", "youtube.com?v=")[0:11] == "youtube.com":
        return "youtube"
    elif str(url).startswith("https://x.com") or str(url).startswith("https://twitter.com"):
        return "xitter"
    elif str(url).startswith("https://vm.tiktok.com") or str(url).startswith(
            "https://www.tiktok.com") or str(url).startswith("https://m.tiktok.com"):
        return "tiktok"
    elif str(url).startswith("https://www.instagram.com") or str(url).startswith(
            "https://instagram.com"):
        return "instagram"
    else:
        return "url"


def get_overcast(input_value, start, end):
    filename = os.path.abspath(os.curdir + r'/outputs/originalaudio.mp3')
    print("Found overcast.fm Link.. downloading")
    start_time = start
    end_time = end
    download(input_value, filename)
    finaltag = str(input_value).replace("https://overcast.fm/", "").split('/')
    if start == 0.0:
        if len(finaltag) > 1:
            t = time.strptime(finaltag[1], "%H:%M:%S")
            seconds = t.tm_hour * 60 * 60 + t.tm_min * 60 + t.tm_sec
            start_time = float(seconds)
            print("Setting start time automatically to " + str(start_time))
            if end > 0.0:
                end_time = float(seconds + end)
                print("Moving end time automatically to " + str(end_time))

    return filename, start_time, end_time


def get_TikTok(input_value, start, end):
    filepath = os.path.abspath(os.curdir + r'/outputs/')
    try:
        filename = download(input_value, filepath)
        print(filename)
    except Exception as e:
        print(e)
        return "", start, end
    return filename, start, end


def get_Instagram(input_value, start, end):
    filepath = os.path.abspath(os.curdir + r'/outputs/')
    try:
        filename = download(input_value, filepath)
        print(filename)
    except Exception as e:
        print(e)
        return "", start, end
    return filename, start, end


def get_Twitter(input_value, start, end):
    filepath = os.path.abspath(os.curdir) + r'/outputs/'
    cleanlink = str(input_value).replace("twitter.com", "x.com")
    try:
        filename = download(cleanlink, filepath)
    except Exception as e:
        print(e)
        return "", start, end
    return filename, start, end


def get_youtube(input_value, start, end, audioonly=True):
    filepath = os.path.abspath(os.curdir) + r'/outputs/'
    print(filepath)
    filename = ""
    try:
        filename = download(input_value, filepath, audioonly)

    except Exception as e:
        print("Youtube " + str(e))
        return filename, start, end
    try:
        o = urlparse(input_value)
        q = urllib.parse.parse_qs(o.query)
        if start == 0.0:
            if o.query.find('?t=') != -1:
                start = q['t'][0]  # overwrite from link.. why not..
                print("Setting start time automatically to " + start)
                if end > 0.0:
                    end = float(q['t'][0]) + end
                    print("Moving end time automatically to " + str(end))

    except Exception as e:
        print(e)
        return filename, start, end

    return filename, start, end


def get_media_link(url) -> (str, str):
    req = requests.get(url)
    content_type = req.headers['content-type']
    print(content_type)
    if content_type == 'audio/x-wav' or str(url).lower().endswith(".wav"):
        ext = "wav"
        file_type = "audio"
        with open(os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), 'wb') as fd:
            fd.write(req.content)
        return os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), file_type
    elif content_type == 'audio/mpeg' or str(url).lower().endswith(".mp3"):
        ext = "mp3"
        file_type = "audio"
        with open(os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), 'wb') as fd:
            fd.write(req.content)
        return os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), file_type
    elif content_type == 'audio/ogg' or str(url).lower().endswith(".ogg"):
        ext = "ogg"
        file_type = "audio"
        with open(os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), 'wb') as fd:
            fd.write(req.content)
        return os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), file_type
    elif content_type == 'video/mp4' or str(url).lower().endswith(".mp4"):
        ext = "mp4"
        file_type = "video"

        with open(os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), 'wb') as fd:
            fd.write(req.content)
        return os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), file_type
    elif content_type == 'video/avi' or str(url).lower().endswith(".avi"):
        ext = "avi"
        file_type = "video"
        with open(os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), 'wb') as fd:
            fd.write(req.content)
        return os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), file_type
    elif content_type == 'video/quicktime' or str(url).lower().endswith(".mov"):
        ext = "mov"
        file_type = "video"
        with open(os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), 'wb') as fd:
            fd.write(req.content)
        return os.path.abspath(os.curdir + r'/outputs/' + 'file.' + ext), file_type

    else:
        print(str(url).lower())
        return None, None


def download(videourl, path, audio_only=False):
    return YTDownload(videourl, path, audio_only=audio_only)
