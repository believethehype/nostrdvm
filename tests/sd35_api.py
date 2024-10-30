import json
import os
from pathlib import Path

import dotenv
from nostr_sdk import LogLevel, init_logger


from nostr_dvm.tasks.imagegeneration_sd35_api import ImageGenerationSD35
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.zap_utils import  get_price_per_sat

rebroadcast_NIP89 = False  # Announce NIP89 on startup Only do this if you know what you're doing.
rebroadcast_NIP65_Relay_List = False
update_profile = False

use_logger = True
log_level = LogLevel.ERROR

if use_logger:
    init_logger(log_level)


def build_sd35(name, identifier):
    dvm_config = build_default_config(identifier)

    dvm_config.NEW_USER_BALANCE = 0
    dvm_config.USE_OWN_VENV = False
    dvm_config.ENABLE_NUTZAP = True
    profit_in_sats = 10
    dvm_config.FIX_COST = int(((4.0 / (get_price_per_sat("USD") * 100)) + profit_in_sats))
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
                "values": ["1:1", "5:4", "3:2", "16:9","21:9", "9:21", "9:16", "2:3", "4:5"]
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                           nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    aconfig = AdminConfig()
    aconfig.REBROADCAST_NIP89 = False  # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    aconfig.LUD16 = dvm_config.LN_ADDRESS
    aconfig.PRIVKEY = dvm_config.PRIVATE_KEY
    aconfig.MELT_ON_STARTUP = False # set this to true to melt cashu tokens to our ln address on startup


    options= {"API_KEY": os.getenv("STABILITY_KEY")}


    return ImageGenerationSD35(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=aconfig, options=options)


def playground():
    if os.getenv("STABILITY_KEY") is not None and os.getenv("STABILITY_KEY") != "":
        sd35 = build_sd35("Stable Diffusion 3.5", "sd35")
        sd35.run(True)


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
    playground()
