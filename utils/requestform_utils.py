import os
import re
from configparser import ConfigParser
import time

from nostr_sdk import PublicKey

from utils.definitions import EventDefinitions
from utils.backend_utils import get_task
from utils.nostr_utils import get_referenced_event_by_id, get_event_by_id
from utils.definitions import LOCAL_TASKS
import utils.env as env


def create_requestform_from_nostr_event(event, is_bot=False, client=None, dvmconfig=None):
    task = get_task(event, client=client, dvmconfig=dvmconfig)

    request_form = {"jobID": event.id().to_hex(), "frameSize": 0, "stride": 0,
                    "leftContext": 0, "rightContext": 0,
                    "startTime": "0", "endTime": "0"}

    if task == "translation":
        input_type = "event"
        text = ""
        translation_lang = "en"
        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]

            elif tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "language":  # check for paramtype
                    translation_lang = str(tag.as_vec()[2]).split('-')[0]
                elif param == "lang":  # check for paramtype
                    translation_lang = str(tag.as_vec()[2]).split('-')[0]

        if input_type == "event":
            for tag in event.tags():
                if tag.as_vec()[0] == 'i':
                    evt = get_event_by_id(tag.as_vec()[1], config=dvmconfig)
                    text = evt.content()
                    break

        elif input_type == "text":
            for tag in event.tags():
                if tag.as_vec()[0] == 'i':
                    text = tag.as_vec()[1]
                    break

        elif input_type == "job":
            for tag in event.tags():
                if tag.as_vec()[0] == 'i':
                    evt = get_referenced_event_by_id(tag.as_vec()[1],
                                                     [EventDefinitions.KIND_NIP90_RESULT_EXTRACT_TEXT,
                                                      EventDefinitions.KIND_NIP90_RESULT_SUMMARIZE_TEXT],
                                                     client,
                                                     config=dvmconfig)
                    text = evt.content()
                    break

        request_form["optStr"] = ('translation_lang=' + translation_lang + ';text=' +
                                  text.replace('\U0001f919', "").replace("=", "equals").
                                  replace(";", ","))

    return request_form
