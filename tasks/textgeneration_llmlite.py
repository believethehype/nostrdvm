import json
import os
from io import BytesIO
from pathlib import Path

import dotenv
import requests
from litellm import completion

from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.backend_utils import keep_alive
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config, check_and_set_d_tag
from utils.nostr_utils import check_and_set_private_key
from utils.output_utils import upload_media_to_hoster
from utils.zap_utils import get_price_per_sat, check_and_set_ln_bits_keys
from nostr_sdk import Keys

"""
This File contains a Module to transform Text input on OpenAI's servers with DALLE-3 and receive results back. 

Accepted Inputs: Prompt (text)
Outputs: An url to an Image
"""


class TextGenerationOLLAMA(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_GENERATE_TEXT
    TASK: str = "text-to-text"
    FIX_COST: float = 0

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)
        if options is not None and options.get("server"):
            self.options["server"] = options["server"]

    def is_input_supported(self, tags):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "text":
                    return False

        return True

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}
        prompt = ""
        model = "ollama/llama2-uncensored" #ollama/nous-hermes # This requires an instance of OLLAMA running
        #model = "gpt-4-1106-preview" # This will call chatgpt and requires an OpenAI API Key set in .env
        server = "http://localhost:11434"

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt = tag.as_vec()[1]

        options = {
            "prompt": prompt,
            "model": model,
            "server": server
        }
        request_form['options'] = json.dumps(options)

        return request_form

    def process(self, request_form):
        options = DVMTaskInterface.set_options(request_form)

        try:
            if options["model"].startswith("ollama"):
                response = completion(
                    model=options["model"],
                    messages=[{"content": options["prompt"], "role": "user"}],
                    api_base=options["server"]
                )
                print(response.choices[0].message.content)
                return response.choices[0].message.content
            else:
                response = completion(
                    model=options["model"],
                    messages=[{"content": options["prompt"], "role": "user"}],
                )
                print(response.choices[0].message.content)
                return response.choices[0].message.content

        except Exception as e:
            print("Error in Module: " + str(e))
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

    nip90params = {
        "size": {
            "required": False,
            "values": ["1024:1024", "1024x1792", "1792x1024"]
        }
    }
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I use a LLM connected via OLLAMA",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": nip90params
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                           nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    return TextGenerationOLLAMA(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=admin_config)


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

    dvm = build_example("LLM", "llmlite", admin_config)
    dvm.run()

    keep_alive()
