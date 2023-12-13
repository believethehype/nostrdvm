import json
import os
from io import BytesIO
from pathlib import Path

import dotenv
import requests
from PIL import Image

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.backend_utils import keep_alive
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.output_utils import upload_media_to_hoster
from nostr_dvm.utils.zap_utils import get_price_per_sat, check_and_set_ln_bits_keys
from nostr_sdk import Keys

"""
This File contains a Module to transform Text input on OpenAI's servers with DALLE-3 and receive results back. 

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
"""


class ImageGenerationDALLE(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_GENERATE_IMAGE
    TASK: str = "text-to-image"
    FIX_COST: float = 120
    dependencies = ["openai==1.3.5"]

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)

    def is_input_supported(self, tags):
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

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
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
            # rehost the result instead of relying on the openai link
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content)).convert("RGB")
            image.save("./outputs/image.jpg")
            result = upload_media_to_hoster("./outputs/image.jpg")
            return result

        except Exception as e:
            print("Error in Module")
            raise Exception(e)

# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    npub = Keys.from_sk_str(dvm_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, user_id, lnaddress = check_and_set_ln_bits_keys(identifier, npub)
    dvm_config.LNBITS_INVOICE_KEY = invoice_key
    dvm_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    admin_config.LUD16 = lnaddress
    profit_in_sats = 10
    dvm_config.FIX_COST = int(((4.0 / (get_price_per_sat("USD") * 100)) + profit_in_sats))

    nip90params = {
        "size": {
            "required": False,
            "values": ["1024:1024", "1024x1792", "1792x1024"]
        }
    }
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I use OpenAI's DALL·E 3",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": nip90params
    }


    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                                              nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    return ImageGenerationDALLE(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=admin_config)


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
    dvm = build_example("Dall-E 3", "dalle3", admin_config)
    dvm.run()

    keep_alive()
