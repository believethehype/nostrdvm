import json
import os
import time
from multiprocessing.pool import ThreadPool
from threading import Thread

from backends.nova_server import check_nova_server_status, send_request_to_nova_server
from dvm import DVM
from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config

"""
This File contains a Module to transform Text input on NOVA-Server and receive results back. 

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
Params: -model         # models: juggernaut, dynavision, colossusProject, newreality, unstable
        -lora          # loras (weights on top of models) voxel, 
"""


class ImageGenerationDALLE(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_GENERATE_IMAGE
    TASK: str = "text-to-image"
    COST: int = 120

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)

    def is_input_supported(self, input_type, input_content):
        if input_type != "text":
            return False
        return True

    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}
        prompt = ""
        width = "1024"
        height = "1024"
        model = "dall-e-3"
        quality = "standard"

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt = tag.as_vec()[1]

            elif tag.as_vec()[0] == 'param':
                print("Param: " + tag.as_vec()[1] + ": " + tag.as_vec()[2])
                if tag.as_vec()[1] == "size":
                    if len(tag.as_vec()) > 3:
                        width = (tag.as_vec()[2])
                        height = (tag.as_vec()[3])
                    elif len(tag.as_vec()) == 3:
                        split = tag.as_vec()[2].split("x")
                        if len(split) > 1:
                            width = split[0]
                            height = split[1]
                elif tag.as_vec()[1] == "model":
                    model = tag.as_vec()[2]
                elif tag.as_vec()[1] == "quality":
                    quality = tag.as_vec()[2]

        options = {
            "prompt": prompt,
            "size": width + "x" + height,
            "model": model,
            "quality": quality,
            "number": 1
        }
        request_form['options'] = json.dumps(options)

        return request_form

    def process(self, request_form):
        try:
            options = DVMTaskInterface.set_options(request_form)

            from openai import OpenAI
            client = OpenAI()
            print("Job " + request_form['jobID'] + " sent to OpenAI API..")

            response = client.images.generate(
                model=options['model'],
                prompt=options['prompt'],
                size=options['size'],
                quality=options['quality'],
                n=int(options['number']),
            )

            image_url = response.data[0].url
            return image_url

        except Exception as e:
            print("Error in Module")
            raise Exception(e)
