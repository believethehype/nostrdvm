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

    # This looks a bit more complicated, but we do several tasks for text-extraction in the future
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
                    evt = get_event_by_id(tag.as_vec()[1], client=client, config=dvmconfig)
                    if evt is not None:
                        if evt.kind() == 1063:
                            for tg in evt.tags():
                                if tg.as_vec()[0] == 'url':
                                    file_type = check_url_is_readable(tg.as_vec()[1])
                                    if file_type == "pdf":
                                        return "pdf-to-text"
                                    else:
                                        return "unknown job"
                        else:
                            return "unknown type"

    elif event.kind() == EventDefinitions.KIND_NIP90_TRANSLATE_TEXT:
        return "translation"
    elif event.kind() == EventDefinitions.KIND_NIP90_GENERATE_IMAGE:
        return "text-to-image"

    else:
        return "unknown type"


def check_task_is_supported(event, client, get_duration=False, config=None):
    dvm_config = config
    input_value = ""
    input_type = ""
    duration = 1
    task = get_task(event, client=client, dvmconfig=dvm_config)
    for tag in event.tags:
        if tag.as_vec()[0] == 'i':
            if len(tag.as_vec()) < 3:
                print("Job Event missing/malformed i tag, skipping..")
                return False, "", 0
            else:
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type == "event":
                    evt = get_event_by_id(input_value, client=client, config=dvm_config)
                    if evt is None:
                        print("Event not found")
                        return False, "", 0
                elif input_type == 'url' and check_url_is_readable(input_value) is None:
                    print("Url not readable / supported")
                    return False, task, duration

        elif tag.as_vec()[0] == 'output':
            output = tag.as_vec()[1]
            if not (output == "text/plain"
                    or output == "text/json" or output == "json"
                    or output == "image/png" or "image/jpg"
                    or output == "image/png;format=url" or output == "image/jpg;format=url"
                    or output == ""):
                print("Output format not supported, skipping..")
                return False, "", 0

    for dvm in dvm_config.SUPPORTED_DVMS:
        if dvm.TASK == task:
            if not dvm.is_input_supported(input_type, event.content()):
                return False, task, duration

    if task not in (x.TASK for x in dvm_config.SUPPORTED_DVMS):
        return False, task, duration

    return True, task, duration


def check_url_is_readable(url):
    if not str(url).startswith("http"):
        return None
    # If link is comaptible with one of these file formats, move on.
    req = requests.get(url)
    content_type = req.headers['content-type']
    if content_type == 'audio/x-wav' or str(url).endswith(".wav") or content_type == 'audio/mpeg' or str(url).endswith(
            ".mp3") or content_type == 'audio/ogg' or str(url).endswith(".ogg"):
        return "audio"
    elif (content_type == 'image/png' or str(url).endswith(".png") or content_type == 'image/jpg' or str(url).endswith(
            ".jpg") or content_type == 'image/jpeg' or str(url).endswith(".jpeg") or content_type == 'image/png' or
          str(url).endswith(".png")):
        return "image"
    elif content_type == 'video/mp4' or str(url).endswith(".mp4") or content_type == 'video/avi' or str(url).endswith(
            ".avi") or content_type == 'video/mov' or str(url).endswith(".mov"):
        return "video"
    elif (str(url)).endswith(".pdf"):
        return "pdf"

    # Otherwise we will not offer to do the job.
    return None


def get_amount_per_task(task, dvm_config, duration=1):
    for dvm in dvm_config.SUPPORTED_DVMS: #this is currently just one
        if dvm.TASK == task:
            amount = dvm.COST * duration
            return amount
    else:
        print("["+dvm_config.SUPPORTED_DVMS[0].NAME +"] Task " + task + " is currently not supported by this instance, skipping")
        return None
