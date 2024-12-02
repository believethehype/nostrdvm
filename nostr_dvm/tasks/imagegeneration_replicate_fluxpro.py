import json
import os
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
from nostr_dvm.utils.zap_utils import get_price_per_sat

"""
This File contains a Module to generate an Image on replicate and receive results back. 

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
Params: 
"""


class ImageGenerationReplicateFluxPro(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_GENERATE_IMAGE
    TASK: str = "text-to-image"
    FIX_COST: float = 120
    dependencies = [("nostr-dvm", "nostr-dvm"),
                    ("replicate", "replicate")]

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                 admin_config: AdminConfig = None,
                 options=None, task=None):
        super().__init__(name, dvm_config, nip89config, nip88config, admin_config, options, task)
        if options is not None:
            self.model = options["model"]
        else:
            self.model = None

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
        width = "4"
        height = "5"

        for tag in event.tags().to_vec():

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
                        split = tag.as_vec()[2].split(":")
                        if len(split) > 1:
                            width = split[0]
                            height = split[1]
                elif tag.as_vec()[1] == "model":
                    model = tag.as_vec()[2]
                elif tag.as_vec()[1] == "quality":
                    quality = tag.as_vec()[2]

        options = {
            "prompt": prompt,
            "ratio": width + ":" + height,
            "number": 1
        }
        request_form['options'] = json.dumps(options)

        return request_form

    async def process(self, request_form):
        try:
            options = self.set_options(request_form)

            import replicate
            #width = int(options["size"].split("x")[0])
            #height = int(options["size"].split("x")[1])
            output = replicate.run(
                "black-forest-labs/flux-1.1-pro",
                input={"prompt": options["prompt"],
                       "aspect_ratio": options["ratio"],
                       "output_format": "jpg",
                       "output_quality": 80,
                       "safety_tolerance": 2,
                       "prompt_upsampling": True
                       }
            )
            print(output)
            response = requests.get(output)
            image = Image.open(BytesIO(response.content)).convert("RGB")
            image.save("./outputs/image.jpg")
            result = await upload_media_to_hoster("./outputs/image.jpg")
            return result

        except Exception as e:
            print("Error in Module")
            raise Exception(e)

def write_text(data: str, path: str):
    with open(path, 'w') as file:
        file.write(data)
# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    profit_in_sats = 10
    dvm_config.FIX_COST = int(((4.0 / (get_price_per_sat("USD") * 100)) + profit_in_sats))

    nip89info = {
        "name": name,
        "picture": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I use Replicate to run FluxPro",
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "nip90Params": {
            "ratio": {
                "required": False,
                "values": ["1:1" , "3:2", "4:5"]
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    return ImageGenerationReplicateFluxPro(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                        admin_config=admin_config)


if __name__ == '__main__':
    process_venv(ImageGenerationReplicateFluxPro)
