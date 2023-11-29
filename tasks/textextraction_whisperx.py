import json
import os
import time
from multiprocessing.pool import ThreadPool
from pathlib import Path

from backends.nova_server import check_nova_server_status, send_request_to_nova_server, send_file_to_nova_server
from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.dvmconfig import DVMConfig
from utils.mediasource_utils import organize_input_data_to_audio
from utils.nip89_utils import NIP89Config
from utils.definitions import EventDefinitions

"""
This File contains a Module to transform Text input on NOVA-Server and receive results back. 

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
Params: -model         # models: juggernaut, dynavision, colossusProject, newreality, unstable
        -lora          # loras (weights on top of models) voxel, 
"""


class SpeechToTextWhisperX(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_EXTRACT_TEXT
    TASK: str = "speech-to-text"
    FIX_COST: float = 10
    PER_UNIT_COST: float  = 0.1

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
                if (output == "" or not (output == "text/plain")):
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
                elif tag.as_vec()[1] == "range": #hui
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

        filepath = organize_input_data_to_audio(url, input_type, start_time, end_time, dvm_config, client)
        pathonserver = send_file_to_nova_server(filepath, self.options['nova_server'])

        io_input = {
            "id": "audio",
            "type": "input",
            "src": "file:stream",
            "uri": pathonserver
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
