import json
import os
import time
from multiprocessing.pool import ThreadPool

from nostr_sdk import Kind

from nostr_dvm.backends.nova_server.utils import check_server_status, send_request_to_server, send_file_to_server
from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.mediasource_utils import organize_input_media_data
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.definitions import EventDefinitions

"""
This File contains a Module to transform A media file input on n-server and receive results back. 

Accepted Inputs: Url to media file (url)
Outputs: Transcribed text

"""


class SpeechToTextWhisperX(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_EXTRACT_TEXT
    TASK: str = "speech-to-text"
    FIX_COST: float = 10
    PER_UNIT_COST: float = 0.1

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
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", ""),
                        "trainerFilePath": r'modules\whisperx\whisperx_transcript.trainer'}

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

        filepath = await  organize_input_media_data(url, input_type, start_time, end_time, dvm_config, client, True,
                                             media_format)
        path_on_server = send_file_to_server(os.path.realpath(filepath), self.options['server'])

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

    async def process(self, request_form):
        try:
            # Call the process route of NOVA-Server with our request form.
            response = send_request_to_server(request_form, self.options['server'])
            if bool(json.loads(response)['success']):
                print("Job " + request_form['jobID'] + " sent to server")

            pool = ThreadPool(processes=1)
            thread = pool.apply_async(check_server_status, (request_form['jobID'], self.options['server']))
            print("Wait for results of server...")
            result = thread.get()
            return result

        except Exception as e:
            raise Exception(e)


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config, server_address):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # A module might have options it can be initialized with, here we set a default model, and the server
    # address it should use. These parameters can be freely defined in the task component
    options = {'default_model': "base", 'server': server_address}

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I extract text from media files with WhisperX",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
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
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return SpeechToTextWhisperX(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                admin_config=admin_config, options=options)


if __name__ == '__main__':
    process_venv(SpeechToTextWhisperX)
