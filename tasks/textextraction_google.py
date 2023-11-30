import json
import os
import time
from multiprocessing.pool import ThreadPool
from pathlib import Path

from backends.nova_server import check_nova_server_status, send_request_to_nova_server, send_file_to_nova_server
from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.dvmconfig import DVMConfig
from utils.mediasource_utils import organize_input_media_data
from utils.nip89_utils import NIP89Config
from utils.definitions import EventDefinitions

"""
This File contains a Module to transform a media file input on Google Cloud

Accepted Inputs: Url to media file (url)
Outputs: Transcribed text

"""


class SpeechToTextGoogle(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_EXTRACT_TEXT
    TASK: str = "speech-to-text"
    FIX_COST: float = 10
    PER_UNIT_COST: float = 0.1

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)
        if options is None:
            options = {}

    def is_input_supported(self, tags):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "url":
                    return False

            elif tag.as_vec()[0] == 'output':
                output = tag.as_vec()[1]
                if output == "" or not (output == "text/plain"):
                    print("Output format not supported, skipping..")
                    return False

        return True

    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}

        url = ""
        input_type = "url"
        start_time = 0
        end_time = 0
        media_format = "audio/wav"
        language = "en-US"

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "url":
                    url = tag.as_vec()[1]

            elif tag.as_vec()[0] == 'param':
                print("Param: " + tag.as_vec()[1] + ": " + tag.as_vec()[2])
                if tag.as_vec()[1] == "language":
                    language = tag.as_vec()[2]
                elif tag.as_vec()[1] == "range":
                    try:
                        t = time.strptime(tag.as_vec()[2], "%H:%M:%S")
                        seconds = t.tm_hour * 60 * 60 + t.tm_min * 60 + t.tm_sec
                        start_time = float(seconds)
                    except:
                        try:
                            t = time.strptime(tag.as_vec()[2], "%M:%S")
                            seconds = t.tm_min * 60 + t.tm_sec
                            start_time = float(seconds)
                        except:
                            start_time = tag.as_vec()[2]
                            try:
                                t = time.strptime(tag.as_vec()[3], "%H:%M:%S")
                                seconds = t.tm_hour * 60 * 60 + t.tm_min * 60 + t.tm_sec
                                end_time = float(seconds)
                            except:
                                try:
                                    t = time.strptime(tag.as_vec()[3], "%M:%S")
                                    seconds = t.tm_min * 60 + t.tm_sec
                                    end_time = float(seconds)
                                except:
                                    end_time = float(tag.as_vec()[3])

        filepath = organize_input_media_data(url, input_type, start_time, end_time, dvm_config, client, True,
                                             media_format)
        options = {
            "filepath": filepath,
            "language": language,
        }
        request_form['options'] = json.dumps(options)
        return request_form

    def process(self, request_form):
        import speech_recognition as sr
        if self.options.get("api_key"):
            api_key = self.options['api_key']
        else:
            api_key = None
        options = DVMTaskInterface.set_options(request_form)
        # Speech recognition instance
        asr = sr.Recognizer()
        with sr.AudioFile(options["filepath"]) as source:
            audio = asr.record(source)  # read the entire audio file

        try:
            # Use Google Web Speech API to recognize speech from audio data
            result = asr.recognize_google(audio, language=options["language"], key=api_key)
        except Exception as e:
            print(e)
            # If an error occurs during speech recognition, return False and the type of the exception
            return "error"

        return result
