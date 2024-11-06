import json
import os
import time
from io import BytesIO

import requests
from PIL import Image
from nostr_sdk import Kind

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import upload_media_to_hoster

"""
This File contains a module to transform Text input on stabity AI API

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
"""
#STABILITY_KEY = os.getenv("STABILITY_KEY")



class ImageGenerationSD35(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_GENERATE_IMAGE
    TASK: str = "text-to-image"
    FIX_COST: float = 50

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                 admin_config: AdminConfig = None,
                 options=None, task=None):
        super().__init__(name, dvm_config, nip89config, nip88config, admin_config, options, task)
        if options is not None:
            self.STABILITY_KEY = options["API_KEY"]

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "text":
                    return False

            elif tag.as_vec()[0] == 'output':
                output = tag.as_vec()[1]
                if (output == "" or
                        not (output == "image/png" or "image/jpg"
                             or output == "image/png;format=url" or output == "image/jpg;format=url")):
                    print("Output format not supported, skipping..")
                    return False

        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}

        prompt = ""
        negative_prompt = ""
        if self.options.get("default_model") and self.options.get("default_model") != "":
            model = self.options['default_model']
        else:
            model = "sd3" #ultra

        ratio_width = "4"
        ratio_height = "5"
        width = ""
        height = ""
        seed = "0"
        if self.options.get("default_lora") and self.options.get("default_lora") != "":
            lora = self.options['default_lora']
        else:
            lora = ""
        lora_weight = ""
        strength = ""
        guidance_scale = ""
        for tag in event.tags().to_vec():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt = tag.as_vec()[1]

            elif tag.as_vec()[0] == 'param':
                print("Param: " + tag.as_vec()[1] + ": " + tag.as_vec()[2])
                if tag.as_vec()[1] == "negative_prompt":
                    negative_prompt = tag.as_vec()[2]
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
                elif tag.as_vec()[1] == "seed":
                    seed = tag.as_vec()[2]



        options = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "ratio": ratio_width + ':' + ratio_height,
            "width": width,
            "height": height,
            "seed": seed,
            "model": model,
        }
        request_form['options'] = json.dumps(options)

        return request_form

    def send_async_generation_request(self,
            host,
            params,
    ):

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.STABILITY_KEY}",

        }

        # Encode parameters
        files = {}
        if "image" in params:
            image = params.pop("image")
            files = {"image": open(image, 'rb')}

        # Send request
        print(f"Sending REST request to {host}...")
        response = requests.post(
            host,
            headers=headers,
            files=files,
            data=params
        )
        if not response.ok:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        # Process async response
        response_dict = json.loads(response.text)
        generation_id = response_dict.get("id", None)
        assert generation_id is not None, "Expected id in response"

        # Loop until result or timeout
        timeout = int(os.getenv("WORKER_TIMEOUT", 500))
        start = time.time()
        status_code = 202
        while status_code == 202:
            response = requests.get(
                f"{host}/result/{generation_id}",
                headers={
                    **headers,
                    "Accept": "image/*"
                },
            )

            if not response.ok:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            status_code = response.status_code
            time.sleep(10)
            if time.time() - start > timeout:
                raise Exception(f"Timeout after {timeout} seconds")

        return response

    def send_generation_request(self,
            host,
            params,
    ):
        headers = {
            "Accept": "image/*",
            "Authorization": f"Bearer {self.STABILITY_KEY}"
        }



        # Encode parameters
        files = {}
        image = params.pop("image", None)
        mask = params.pop("mask", None)
        if image is not None and image != '':
            files["image"] = open(image, 'rb')
        if mask is not None and mask != '':
            files["mask"] = open(mask, 'rb')
        if len(files) == 0:
            files["none"] = ''

        # Send request
        print(f"Sending REST request to {host}...")
        response = requests.post(
            host,
            headers=headers,
            files=files,
            data=params
        )
        if not response.ok:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        return response

    async def process(self, request_form):
        try:

            options = self.set_options(request_form)


            #host = f"https://api.stability.ai/v2beta/stable-image/generate/ultra"
            #host = f"https://api.stability.ai/v2beta/stable-image/generate/sd3"
            model = "sd3.5-large"

            params = {
                "prompt": options['prompt'], # "dark high contrast render of a psychedelic tree of life illuminating dust in a mystical cave.",
                "negative_prompt": options['negative_prompt'],
                "aspect_ratio": options['ratio'],
                #"seed": int(options['seed']),
                "output_format": "jpeg",
                #"model": model,
                #"mode": "text-to-image"
            }

            host =  f"https://api.stability.ai/v2beta/stable-image/generate/{options['model']}"
            host = f"https://api.stability.ai/v2beta/stable-image/generate/ultra"
            response = self.send_generation_request(host, params)
            image = Image.open(BytesIO(response.content)).convert("RGB")
            image.save("./outputs/image.jpg")
            result = await upload_media_to_hoster("./outputs/image.jpg")
            return result

        except Exception as e:
            raise Exception(e)


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config, server_address, default_model="sd3", default_lora=""):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    # A module might have options it can be initialized with, here we set a default model, and the server
    # address it should use. These parameters can be freely defined in the task component
    options = {'default_model': default_model, 'default_lora': default_lora, 'server': server_address}

    nip89info = {
        "name": name,
        "image": "https://i.nostr.build/NOXcCIPmOZrDTK35.jpg",
        "about": "I draw images using Stable diffusion ultra",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "negative_prompt": {
                "required": False,
                "values": []
            },
            "ratio": {
                "required": False,
                "values": ["1:1", "5:4", "3:2", "16:9", "21:9", "9:21", "9:16", "2:3", "4:5"]
            },
            "seed": {
                "required": False,
                "values": []
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return ImageGenerationSD35(name=name, dvm_config=dvm_config, nip89config=nip89config,
                               admin_config=admin_config, options=options)


if __name__ == '__main__':
    process_venv(ImageGenerationSD35)
