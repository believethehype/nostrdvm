import json
import os
from multiprocessing.pool import ThreadPool
from pathlib import Path

import dotenv

from backends.nova_server import check_nova_server_status, send_request_to_nova_server
from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.backend_utils import keep_alive
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config, check_and_set_d_tag
from utils.definitions import EventDefinitions
from utils.nostr_utils import check_and_set_private_key

"""
This File contains a Module to transform Text input on NOVA-Server and receive results back. 

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
Params: -model         # models: juggernaut, dynavision, colossusProject, newreality, unstable
        -lora          # loras (weights on top of models) voxel, 
"""


class ImageGenerationSDXLIMG2IMG(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_GENERATE_IMAGE
    TASK: str = "image-to-image"
    FIX_COST: float = 50

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)

    def is_input_supported(self, tags):
        hasurl = False
        hasprompt = False
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type == "url":
                    hasurl = True
                elif input_type == "text":
                    hasprompt = True #Little optional when lora is set

            elif tag.as_vec()[0] == 'output':
                output = tag.as_vec()[1]
                if (output == "" or
                        not (output == "image/png" or "image/jpg"
                             or output == "image/png;format=url" or output == "image/jpg;format=url")):
                    print("Output format not supported, skipping..")
                    return False

        if not hasurl:
            return False

        return True

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}
        request_form["trainerFilePath"] = r'modules\stablediffusionxl\stablediffusionxl-img2img.trainer'

        prompt = ""
        negative_prompt = ""
        url = ""
        if self.options.get("default_model"):
            model = self.options['default_model']
        else:
            model = "stabilityai/stable-diffusion-xl-refiner-1.0"

        ratio_width = "1"
        ratio_height = "1"
        width = ""
        height = ""

        if self.options.get("default_lora") and self.options.get("default_lora") != "":
            lora = self.options['default_lora']
        else:
            lora = ""

        lora_weight = ""
        if self.options.get("strength"):
            strength = float(self.options['strength'])
        else:
            strength = 0.8
        if self.options.get("guidance_scale"):
            guidance_scale = float(self.options['guidance_scale'])
        else:
            guidance_scale = 11.0
        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt = tag.as_vec()[1]
                elif input_type == "url":
                    url = tag.as_vec()[1]

            elif tag.as_vec()[0] == 'param':
                print("Param: " + tag.as_vec()[1] + ": " + tag.as_vec()[2])
                if tag.as_vec()[1] == "negative_prompt":
                    negative_prompt = tag.as_vec()[2]
                elif tag.as_vec()[1] == "lora":
                    lora = tag.as_vec()[2]
                elif tag.as_vec()[1] == "lora_weight":
                    lora_weight = tag.as_vec()[2]
                elif tag.as_vec()[1] == "strength":
                    strength = float(tag.as_vec()[2])
                elif tag.as_vec()[1] == "guidance_scale":
                    guidance_scale = float(tag.as_vec()[2])
                elif tag.as_vec()[1] == "ratio":
                    if len(tag.as_vec()) > 3:
                        ratio_width = (tag.as_vec()[2])
                        ratio_height = (tag.as_vec()[3])
                    elif len(tag.as_vec()) == 3:
                        split = tag.as_vec()[2].split(":")
                        ratio_width = split[0]
                        ratio_height = split[1]
                    # if size is set it will overwrite ratio.
                elif tag.as_vec()[1] == "size":
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





        io_input_image = {
        "id": "input_image",
        "type": "input",
        "src": "url:Image",
        "uri": url
        }
        io_input = {
            "id": "input_prompt",
            "type": "input",
            "src": "request:text",
            "data": prompt
        }
        io_negative = {
            "id": "negative_prompt",
            "type": "input",
            "src": "request:text",
            "data": negative_prompt
        }
        io_output = {
            "id": "output_image",
            "type": "output",
            "src": "request:image"
        }

        request_form['data'] = json.dumps([io_input_image, io_input, io_negative, io_output])

        options = {
            "model": model,
            "ratio": ratio_width + '-' + ratio_height,
            "width": width,
            "height": height,
            "strength": strength,
            "guidance_scale": guidance_scale,
            "lora": lora,
            "lora_weight": lora_weight,
            "n_steps": 30
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
def build_example(name, identifier, admin_config, server_address, default_lora="", strength=0.6):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")

    nip90params = {
        "negative_prompt": {
            "required": False,
            "values": []
        },
        "lora": {
            "required": False,
            "values": ["inkpunk", "timburton", "voxel"]
        },

        "strength": {
            "required": False,
            "values": []
        }
    }
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/229c14e440895da30de77b3ca145d66d4b04efb4027ba3c44ca147eecde891f1.jpg",
        "about": "I convert an image to another image, kinda random for now. ",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": nip90params
    }

    # A module might have options it can be initialized with, here we set a default model, lora and the nova-server
    options = {'default_lora': default_lora, 'strength': strength, 'nova_server': server_address}

    nip89config = NIP89Config()

    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                                              nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    return ImageGenerationSDXLIMG2IMG(name=name, dvm_config=dvm_config, nip89config=nip89config,
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
    dvm = build_example("Image Converter Inkpunk", "image2image", admin_config, os.getenv("NOVA_SERVER"), "", 0.6)
    dvm.run()

    keep_alive()