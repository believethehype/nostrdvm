import json
import os
from pathlib import Path

import dotenv
from nostr_sdk import Kind

from nostr_dvm.tasks.generic_dvm import GenericDVM
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import upload_media_to_hoster


def playground(announce=False):

    kind = 5100
    model = "dev" #schnell

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce

    name = "Flux"
    identifier = "flux"  # Chose a unique identifier in order to get a lnaddress
    dvm_config = build_default_config(identifier)
    dvm_config.KIND = Kind(kind)  # Manually set the Kind Number (see data-vending-machines.org)
    dvm_config.CUSTOM_PROCESSING_MESSAGE = ["Generating image.."]
    dvm_config.SEND_FEEDBACK_EVENTS = True
    dvm_config.FIX_COST = 20

    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I produce images with Flux-Schnell'",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
        }
    }

    nip89config = NIP89Config()
    nip89config.KIND = kind
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    options = {
        "input": "A purple ostrich holding a sign saying Don't believe the hype",
    }

    dvm = GenericDVM(name=name, dvm_config=dvm_config, nip89config=nip89config,
                     admin_config=admin_config, options=options)

    async def process(request_form):
        import requests
        options = dvm.set_options(request_form)

        API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-" + model
        # set the HUGGINGFACE_TOKEN in .env or replace os.getenv("HUGGINGFACE_TOKEN")
        # HUGGINGFACE_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxx"
        headers = {"Authorization": "Bearer " + os.getenv("HUGGINGFACE_TOKEN") }

        def query(payload):
            response = requests.post(API_URL, headers=headers, json=payload)
            if response.status_code == 500:
                raise Exception("Internal server error, try again later.")
            else:
                return response.content

        image_bytes = query({
            "inputs": options["input"],
            "options": {"use_cache": False},

        })
        import io
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        image.save("flux.png")
        url = await upload_media_to_hoster("flux.png")
        os.remove("flux.png")
        return url


    dvm.process = process  # overwrite the process function with the above one
    dvm.run(True)


if __name__ == '__main__':
    env_path = Path('.env')
    if not env_path.is_file():
        with open('.env', 'w') as f:
            print("Writing new .env file")
            f.write('')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    playground(announce=False)
