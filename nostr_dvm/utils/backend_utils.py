import os
import signal
import time

import requests
from nostr_sdk import Event

from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.mediasource_utils import check_source_type, media_source
from nostr_dvm.utils.nostr_utils import get_event_by_id, get_referenced_event_by_id


async def get_task(event, client, dvm_config):
    try:
        if event.kind() == EventDefinitions.KIND_NIP90_GENERIC:  # use this for events that have no id yet, inclufr j tag
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
                        print(file_type)
                        if file_type == "pdf":
                            return "pdf-to-text"
                        elif file_type == "audio" or file_type == "video":
                            return "speech-to-text"
                        elif file_type == "image":
                            return "image-to-text"
                        else:
                            return "unknown job"
                    elif tag.as_vec()[2] == "event":
                        evt = await get_event_by_id(tag.as_vec()[1], client=client, config=dvm_config)
                        if evt is not None:
                            if evt.kind() == 1063:
                                for tg in evt.tags():
                                    if tg.as_vec()[0] == 'url':
                                        file_type = check_url_is_readable(tg.as_vec()[1])
                                        if file_type == "pdf":
                                            return "pdf-to-text"
                                        elif file_type == "audio" or file_type == "video":
                                            return "speech-to-text"
                                        else:
                                            return "unknown job"
                            else:
                                return "unknown type"
                    else:
                        return "unknown job"
        elif event.kind() == EventDefinitions.KIND_NIP90_GENERATE_IMAGE:
            has_image_tag = False
            has_text_tag = False
            for tag in event.tags():
                if tag.as_vec()[0] == "i":
                    if tag.as_vec()[2] == "url":
                        file_type = check_url_is_readable(tag.as_vec()[1])
                        if file_type == "image":
                            has_image_tag = True
                            print("found image tag")
                    elif tag.as_vec()[2] == "job":
                        evt = await get_referenced_event_by_id(event_id=tag.as_vec()[1], kinds=
                        [EventDefinitions.KIND_NIP90_RESULT_EXTRACT_TEXT,
                         EventDefinitions.KIND_NIP90_RESULT_TRANSLATE_TEXT,
                         EventDefinitions.KIND_NIP90_RESULT_SUMMARIZE_TEXT],
                                                         client=client,
                                                         dvm_config=dvm_config)
                        if evt is not None:
                            file_type = check_url_is_readable(evt.content())
                            if file_type == "image":
                                has_image_tag = True
                    elif tag.as_vec()[2] == "text":
                        has_text_tag = True

            if has_image_tag:
                return "image-to-image"
            elif has_text_tag and not has_image_tag:
                return "text-to-image"
        #  TODO if a task can consist of multiple inputs add them here
        #  This is not ideal. Maybe such events should have their own kind

        #  else if kind is supported, simply return task
        else:

            for dvm in dvm_config.SUPPORTED_DVMS:
                if dvm.KIND.as_u64() == event.kind().as_u64():
                    return dvm.TASK
    except Exception as e:
        print("Get task: " + str(e))

    return "unknown type"


def is_input_supported_generic(tags, client, dvm_config) -> bool:
    # Handle malformed tags, missing events etc here.
    try:
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                if len(tag.as_vec()) < 3:
                    print("Job Event missing/malformed i tag, skipping..")
                    return False
                else:
                    input_value = tag.as_vec()[1]
                    input_type = tag.as_vec()[2]
                    #if input_type == "event":
                    #    evt = get_event_by_id(input_value, client=client, config=dvm_config)
                    #    if evt is None:
                    #        print("Event not found")
                    #        return False
                    # TODO check_url_is_readable might be more relevant per task in the future
                    # if input_type == 'url' and check_url_is_readable(input_value) is None:
                    #    print("Url not readable / supported")
                    #    return False

        return True
    except Exception as e:
        print("Generic input check: " + str(e))


async def check_task_is_supported(event: Event, client, config=None):
    try:
        dvm_config = config
        # Check for generic issues, event maformed, referenced event not found etc..
        if not is_input_supported_generic(event.tags(), client, dvm_config):
            return False, ""

        # See if current dvm supports the task
        task = await get_task(event, client=client, dvm_config=dvm_config)
       # if task not in (x.TASK for x in dvm_config.SUPPORTED_DVMS) and not task == "generic":
       #     return False, task
        # See if current dvm can handle input for given task
        for dvm in dvm_config.SUPPORTED_DVMS:
            if dvm.TASK == task:
                if not await dvm.is_input_supported(event.tags(), client, config):
                    return False, task
        return True, task

    except Exception as e:
        print("Check task: " + str(e))


def check_url_is_readable(url):
    if not str(url).startswith("http"):
        return None

    source = check_source_type(url)
    type = media_source(source)

    if type == "url":
        # If link is comaptible with one of these file formats, move on.
        req = requests.get(url)
        content_type = req.headers['content-type']
        if content_type == 'audio/x-wav' or str(url).endswith(".wav") or content_type == 'audio/mpeg' or str(
                url).endswith(
                ".mp3") or content_type == 'audio/ogg' or str(url).endswith(".ogg"):
            return "audio"
        elif (content_type == 'image/png' or str(url).endswith(".png") or content_type == 'image/jpg' or str(
                url).endswith(
                ".jpg") or content_type == 'image/jpeg' or str(url).endswith(".jpeg") or content_type == 'image/png' or
              str(url).endswith(".png")):
            return "image"
        elif content_type == 'video/mp4' or str(url).endswith(".mp4") or content_type == 'video/avi' or str(
                url).endswith(
                ".avi") or content_type == 'video/mov' or str(url).endswith(".mov"):
            return "video"
        elif (str(url)).endswith(".pdf"):
            return "pdf"
    else:
        return type

    # Otherwise we will not offer to do the job.
    return None


def get_amount_per_task(task, dvm_config, duration=1):
    #  duration is either static 1 (for images etc) or in seconds by default (e.g. audio/video)
    for dvm in dvm_config.SUPPORTED_DVMS:  # this is currently just one
        if dvm.TASK == task or dvm.TASK  == "generic":
            amount = dvm.FIX_COST + (dvm.PER_UNIT_COST * duration)
            return amount
    else:
        print("[" + dvm_config.SUPPORTED_DVMS[
            0].NAME + "] Task " + task + " is currently not supported by this instance, skipping")
        return None


def keep_alive():
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        os.kill(os.getpid(), signal.SIGKILL)
        exit(1)
