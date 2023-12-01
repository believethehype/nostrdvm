import json
import os
import time
from multiprocessing.pool import ThreadPool
from pathlib import Path

import dotenv

from backends.nova_server import check_nova_server_status, send_request_to_nova_server, send_file_to_nova_server
from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.backend_utils import keep_alive
from utils.dvmconfig import DVMConfig
from utils.mediasource_utils import organize_input_media_data
from utils.nip89_utils import NIP89Config, check_and_set_d_tag
from utils.definitions import EventDefinitions
from utils.nostr_utils import check_and_set_private_key

"""
This File contains a Module to transform A media file input on NOVA-Server and receive results back. 

Accepted Inputs: Url to media file (url)
Outputs: Transcribed text

"""


class SpeechToTextWhisperX(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_EXTRACT_TEXT
    TASK: str = "speech-to-text"
    FIX_COST: float = 10
    PER_UNIT_COST: float = 0.1

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)

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
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", ""),
                        "trainerFilePath": 'modules\\whisperx\\whisperx_transcript.trainer'}

        if self.options.get("default_model"):
            model = self.options['default_model']
        else:
            model = "base"
        if self.options.get("alignment"):
            alignment = self.options['alignment']
        else:
            alignment = "raw"

        url = ""
        input_type = "url"
        start_time = 0
        end_time = 0
        media_format = "audio/mp3"

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "url":
                    url = tag.as_vec()[1]

            elif tag.as_vec()[0] == 'param':
                print("Param: " + tag.as_vec()[1] + ": " + tag.as_vec()[2])
                if tag.as_vec()[1] == "alignment":
                    alignment = tag.as_vec()[2]
                elif tag.as_vec()[1] == "model":
                    model = tag.as_vec()[2]
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

        filepath = organize_input_media_data(url, input_type, start_time, end_time, dvm_config, client, True, media_format)
        path_on_server = send_file_to_nova_server(os.path.realpath(filepath), self.options['nova_server'])

        io_input = {
            "id": "audio",
            "type": "input",
            "src": "file:stream",
            "uri": path_on_server
        }

        io_output = {
            "id": "transcript",
            "type": "output",
            "src": "request:annotation:free"
        }

        request_form['data'] = json.dumps([io_input, io_output])

        options = {
            "model": model,
            "alignment_mode": alignment,
        }
        request_form['options'] = json.dumps(options)
        return request_form

    def process(self, request_form):
        try:
            # Call the process route of NOVA-Server with our request form.
            response = send_request_to_nova_server(request_form, self.options['nova_server'])
            if bool(json.loads(response)['success']):
                print("Job " + request_form['jobID'] + " sent to NOVA-server")

            pool = ThreadPool(processes=1)
            thread = pool.apply_async(check_nova_server_status, (request_form['jobID'], self.options['nova_server']))
            print("Wait for results of NOVA-Server...")
            result = thread.get()
            return result

        except Exception as e:
            raise Exception(e)

# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config, server_address):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")

    # A module might have options it can be initialized with, here we set a default model, and the nova-server
    # address it should use. These parameters can be freely defined in the task component
    options = {'default_model': "base", 'nova_server': server_address}

    nip90params = {
        "model": {
            "required": False,
            "values": ["base", "tiny", "small", "medium", "large-v1", "large-v2", "tiny.en", "base.en", "small.en",
                       "medium.en"]
        },
        "alignment": {
            "required": False,
            "values": ["raw", "segment", "word"]
        }
    }
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I extract text from media files with WhisperX",
        "nip90Params": nip90params
    }
    nip89config = NIP89Config()
    nip89config.DTAG = nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                                              nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    return SpeechToTextWhisperX(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                admin_config=admin_config, options=options)


if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = False
    admin_config.UPDATE_PROFILE = False
    admin_config.LUD16 = ""
    dvm = build_example("Whisperer", "whisperx", admin_config, os.getenv("NOVA_SERVER"))
    dvm.run()

    keep_alive()
