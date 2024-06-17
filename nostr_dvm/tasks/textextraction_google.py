import json
import os
import time

from nostr_sdk import Kind

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.mediasource_utils import organize_input_media_data
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.definitions import EventDefinitions

"""
This File contains a Module to extract text form a media file input on Google Cloud

Accepted Inputs: Url to media file (url)
Outputs: Transcribed text

"""


class SpeechToTextGoogle(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_EXTRACT_TEXT
    TASK: str = "speech-to-text"
    FIX_COST: float = 10
    PER_UNIT_COST: float = 0.1
    dependencies = [("nostr-dvm", "nostr-dvm"),
                    ("speech_recognition", "SpeechRecognition==3.10.0")]

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)


    async def is_input_supported(self, tags, client=None, dvm_config=None):
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

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
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

        filepath = await organize_input_media_data(url, input_type, start_time, end_time, dvm_config, client, True,
                                             media_format)
        options = {
            "filepath": filepath,
            "language": language,
        }
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        import speech_recognition as sr
        if self.options.get("api_key"):
            api_key = self.options['api_key']
        else:
            api_key = None
        options = self.set_options(request_form)
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


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    options = {'api_key': None}
    # A module might have options it can be initialized with, here we set a default model, and the nova-server
    # address it should use. These parameters can be freely defined in the task component

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I extract text from media files with the Google API. I understand English by default",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "language": {
                "required": False,
                "values": ["en-US"]
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return SpeechToTextGoogle(name=name, dvm_config=dvm_config, nip89config=nip89config,
                              admin_config=admin_config, options=options)


if __name__ == '__main__':
    process_venv(SpeechToTextGoogle)
