import json
import os
from pathlib import Path

import dotenv
from nostr_sdk import Keys, LogLevel, init_logger

from nostr_dvm.tasks import search_users, advanced_search
from nostr_dvm.tasks.advanced_search import AdvancedSearch
from nostr_dvm.tasks.advanced_search_wine import AdvancedSearchWine
from nostr_dvm.tasks.imagegeneration_openai_dalle import ImageGenerationDALLE
from nostr_dvm.tasks.search_users import SearchUser
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys, get_price_per_sat

rebroadcast_NIP89 = False   # Announce NIP89 on startup Only do this if you know what you're doing.
rebroadcast_NIP65_Relay_List = False
update_profile = False

#use_logger = True
log_level = LogLevel.ERROR


#if use_logger:
#    init_logger(log_level)




def build_dalle(name, identifier):
    dvm_config = build_default_config(identifier)

    dvm_config.NEW_USER_BALANCE = 0
    dvm_config.USE_OWN_VENV = False
    dvm_config.ENABLE_NUTZAP = True
    profit_in_sats = 10
    dvm_config.FIX_COST = int(((4.0 / (get_price_per_sat("USD") * 100)) + profit_in_sats))
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/22f2267ca9d4ee9d5e8a0c7818a9fa325bbbcdac5573a60a2d163e699bb69923.jpg",
        "about": "I create Images bridging OpenAI's DALL·E 3",
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
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                           nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    aconfig = AdminConfig()
    aconfig.REBROADCAST_NIP89 = False    # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    aconfig.LUD16 = dvm_config.LN_ADDRESS
    return ImageGenerationDALLE(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=aconfig)

def playground():
    if os.getenv("OPENAI_API_KEY") is not None and os.getenv("OPENAI_API_KEY") != "":
        dalle = build_dalle("Dall-E 3", "dalle3")
        dalle.run()



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
