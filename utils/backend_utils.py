
import requests

from utils.definitions import EventDefinitions
from utils.nostr_utils import get_event_by_id


def get_task(event, client, dvmconfig):
    if event.kind() == EventDefinitions.KIND_NIP90_GENERIC:  # use this for events that have no id yet
        for tag in event.tags():
            if tag.as_vec()[0] == 'j':
                return tag.as_vec()[1]
        else:
            return "unknown job: " + event.as_json()
    elif event.kind() == EventDefinitions.KIND_DM:  # dm
        for tag in event.tags():
            if tag.as_vec()[0] == 'j':
                return tag.as_vec()[1]
        else:
            return "unknown job: " + event.as_json()

    elif event.kind() == EventDefinitions.KIND_NIP90_EXTRACT_TEXT:
        for tag in event.tags():
            if tag.as_vec()[0] == "i":
                if tag.as_vec()[2] == "url":
                    file_type = check_url_is_readable(tag.as_vec()[1])
                    if file_type == "pdf":
                        return "pdf-to-text"
                    else:
                        return "unknown job"
                elif tag.as_vec()[2] == "event":
                     evt = get_event_by_id(tag.as_vec()[1],config=dvmconfig)
                     if evt is not None:
                         if evt.kind() == 1063:
                            for tag in evt.tags():
                                if tag.as_vec()[0] == 'url':
                                    file_type = check_url_is_readable(tag.as_vec()[1])
                                    if file_type == "pdf":
                                        return "pdf-to-text"
                                    else:
                                        return "unknown job"
                         else:
                             return "unknown type"


    elif event.kind() == EventDefinitions.KIND_NIP90_TRANSLATE_TEXT:
        return "translation"

    else:
        return "unknown type"
def check_task_is_supported(event, client, get_duration = False, config=None):
    dvmconfig = config
    input_value = ""
    input_type = ""
    duration = 1

    output_is_set = True

    for tag in event.tags():
        if tag.as_vec()[0] == 'i':
            if len(tag.as_vec()) < 3:
                print("Job Event missing/malformed i tag, skipping..")
                return False, "", 0
            else:
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type == "event":
                   evt = get_event_by_id(input_value, config=dvmconfig)
                   if evt == None:
                       print("Event not found")
                       return False, "", 0

        elif tag.as_vec()[0] == 'output':
                output = tag.as_vec()[1]
                output_is_set = True
                if not (output == "text/plain" or output == "text/json" or output == "json" or output == "image/png" or "image/jpg" or output == ""):
                    print("Output format not supported, skipping..")
                    return False, "", 0

    task = get_task(event, client=client, dvmconfig=dvmconfig)
    if not output_is_set:
        print("No output set")
    if task not in dvmconfig.SUPPORTED_TASKS:  # The Tasks this DVM supports (can be extended)
        return False, task, duration


    elif task == "translation" and (
            input_type != "event" and input_type != "job" and input_type != "text"):  # The input types per task
        return False, task, duration
    if task == "translation" and input_type != "text" and len(event.content()) > 4999:  # Google Services have a limit of 5000 signs
        return False, task, duration
    if input_type == 'url' and check_url_is_readable(input_value) is None:
        print("url not readable")
        return False, task, duration

    return True, task, duration

def check_url_is_readable(url):
    if not str(url).startswith("http"):
        return None
    # If it's a YouTube oder Overcast link, we suppose we support it
    if (str(url).replace("http://", "").replace("https://", "").replace("www.", "").replace("youtu.be/",
                                                                                           "youtube.com?v=")[
       0:11] == "youtube.com" and str(url).find("live") == -1) or str(url).startswith('https://x.com') or str(url).startswith('https://twitter.com') :
        return "video"

    elif str(url).startswith("https://overcast.fm/"):
        return "audio"

    # If link is comaptible with one of these file formats, it's fine.
    req = requests.get(url)
    content_type = req.headers['content-type']
    if content_type == 'audio/x-wav' or str(url).endswith(".wav") or content_type == 'audio/mpeg' or str(url).endswith(
            ".mp3") or content_type == 'audio/ogg' or str(url).endswith(".ogg"):
        return "audio"
    elif content_type == 'image/png' or str(url).endswith(".png") or content_type == 'image/jpg' or str(url).endswith(
            ".jpg") or content_type == 'image/jpeg' or str(url).endswith(".jpeg") or content_type == 'image/png' or str(
            url).endswith(".png"):
        return "image"
    elif content_type == 'video/mp4' or str(url).endswith(".mp4") or content_type == 'video/avi' or str(url).endswith(
            ".avi") or content_type == 'video/mov' or str(url).endswith(".mov"):
        return "video"
    elif (str(url)).endswith(".pdf"):
        return "pdf"

    # Otherwise we will not offer to do the job.
    return None

def get_amount_per_task(task, duration = 0, config=None):
    dvmconfig = config
    if task == "translation":
        amount = dvmconfig.COSTPERUNIT_TRANSLATION
    elif task == "pdf-to-text":
        amount = dvmconfig.COSTPERUNIT_TEXT_EXTRACTION

    else:
        print("[Nostr] Task " + task + " is currently not supported by this instance, skipping")
        return None
    return amount


