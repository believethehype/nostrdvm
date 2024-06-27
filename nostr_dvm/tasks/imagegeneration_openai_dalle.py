import json
import os
import time
from io import BytesIO

import requests
from PIL import Image

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import upload_media_to_hoster
from nostr_dvm.utils.zap_utils import get_price_per_sat

"""
This File contains a Module to transform Text input on OpenAI's servers with DALLE-3 and receive results back. 

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
"""


class ImageGenerationDALLE(DVMTaskInterface):
    KIND = EventDefinitions.KIND_NIP90_GENERATE_IMAGE
    TASK: str = "text-to-image"
    FIX_COST: float = 120
    dependencies = [("nostr-dvm", "nostr-dvm"),
                    ("openai", "openai==1.3.5")]

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

    async def process(self, request_form):
        try:
            options = self.set_options(request_form)

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
            # rehost the result instead of relying on the openai link
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content)).convert("RGB")
            image.save("./outputs/image.jpg")
            result = await upload_media_to_hoster("./outputs/image.jpg")
            return result

        except Exception as e:
            if str(e).startswith("Error code: 400"):
                raise Exception('Your request was rejected as a result of OpenAI´s safety system. Your prompt may '
                                'contain text that is not allowed by their safety system.')

# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = True
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    profit_in_sats = 10
    cost_in_cent = 4.0
    dvm_config.FIX_COST = int(((cost_in_cent / (get_price_per_sat("USD") * 100)) + profit_in_sats))

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I use OpenAI's DALL·E 3",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "size": {
                "required": False,
                "values": ["1024:1024", "1024x1792", "1792x1024"]
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return ImageGenerationDALLE(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=admin_config)


if __name__ == '__main__':
    process_venv(ImageGenerationDALLE)
