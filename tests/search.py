import json
import os
from pathlib import Path

import dotenv
from nostr_sdk import Keys, LogLevel, init_logger

from nostr_dvm.tasks import search_users, advanced_search
from nostr_dvm.tasks.advanced_search import AdvancedSearch
from nostr_dvm.tasks.advanced_search_wine import AdvancedSearchWine
from nostr_dvm.tasks.search_users import SearchUser
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys

rebroadcast_NIP89 = False   # Announce NIP89 on startup Only do this if you know what you're doing.
rebroadcast_NIP65_Relay_List = False
update_profile = False

use_logger = True
log_level = LogLevel.ERROR


if use_logger:
    init_logger(log_level)


RELAY_LIST = ["wss://nostr.mom",
              #"wss://relay.primal.net",
              "wss://nostr.oxtr.dev",
              #"wss://relay.nostr.net"
              ]

SYNC_DB_RELAY_LIST = ["wss://relay.damus.io",
                      #"wss://relay.primal.net",
                      "wss://nostr.oxtr.dev"]



def build_advanced_search(name, identifier):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    npub = Keys.parse(dvm_config.PRIVATE_KEY).public_key().to_bech32()
    dvm_config = build_default_config(identifier)
    #    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.FIX_COST = 0
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST


    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config.UPDATE_PROFILE = update_profile
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    # Add NIP89

    nip89info = {
        "name": name,
        "image": "https://nostr.band/android-chrome-192x192.png",
        "about": "I search notes on nostr.band",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "users": {
                "required": False,
                "values": [],
                "description": "Search for specific authors"
            },
            "since": {
                "required": False,
                "values": [],
                "description": "The number of days in the past from now the search should include"
            },
            "until": {
                "required": False,
                "values": [],
                "description": "The number of days in the past from now the search should include up to"
            },
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 150)"
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                           nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return AdvancedSearch(name=name, dvm_config=dvm_config, nip89config=nip89config,
                          admin_config=admin_config)

def build_advanced_search_wine(name, identifier):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    npub = Keys.parse(dvm_config.PRIVATE_KEY).public_key().to_bech32()
    dvm_config.RELAY_LIST = RELAY_LIST
    invoice_key, admin_key, wallet_id, lnaddress = check_and_set_ln_bits_keys(identifier, npub)
    dvm_config.LNBITS_INVOICE_KEY = invoice_key
    dvm_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config.UPDATE_PROFILE = update_profile
    admin_config.LUD16 = lnaddress

    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/d844d6a963724b9f9deb6b3326984fd95352343336718812424d5e99d93a6f2d.jpg",
        "about": "I search notes on nostr.wine using the nostr-wine API",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "users": {
                "required": False,
                "values": [],
                "description": "Search for content from specific users"
            },
            "since": {
                "required": False,
                "values": [],
                "description": "The number of days in the past from now the search should include"
            },
            "until": {
                "required": False,
                "values": [],
                "description": "The number of days in the past from now the search should include up to"
            },
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 20)"
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                           nip89info["image"])

    nip89config.CONTENT = json.dumps(nip89info)


    return AdvancedSearchWine(name=name, dvm_config=dvm_config, nip89config=nip89config,
                              admin_config=admin_config)


def build_user_search(name, identifier):
    dvm_config = build_default_config(identifier)
    dvm_config.SYNC_DB_RELAY_LIST = ["wss://relay.damus.io"]
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    npub = Keys.parse(dvm_config.PRIVATE_KEY).public_key().to_bech32()
    dvm_config.RELAY_LIST = RELAY_LIST
    invoice_key, admin_key, wallet_id, lnaddress = check_and_set_ln_bits_keys(identifier, npub)
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config.UPDATE_PROFILE = update_profile
    admin_config.LUD16 = lnaddress

    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/bd0181a3089181f1d92a5da1ef85cffbe37ba80fbcc695b9d85648dc2fa92583.jpg",
        "about": "I search users based on their profile info.",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 150)"
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    options = {"relay": "wss://profiles.nostr1.com"}


    return SearchUser(name=name, dvm_config=dvm_config, nip89config=nip89config,
                      admin_config=admin_config, options=options)





def playground():

    advanced_search = build_advanced_search("Nostr.band Search",
                                           "discovery_content_search")
    advanced_search.run()

    advanced_search_wine = build_advanced_search_wine("Nostr.wine Search", "discovery_content_searchwine")
    advanced_search_wine.run()

    #profile_search = build_user_search("Profile Searcher", "profile_search")
    #profile_search.run()



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
