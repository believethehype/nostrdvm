import json
import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel, Keys, NostrLibrary

from nostr_dvm.tasks.content_discovery_currently_popular_mostr import DicoverContentCurrentlyPopularMostr
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST


rebroadcast_NIP89 = False  # Announce NIP89 on startup
rebroadcast_NIP65_Relay_List = False
update_profile = False

global_update_rate = 60  # set this high on first sync so db can fully sync before another process trys to.
use_logger = True
# these do not support nengentropy
#SYNC_DB_RELAY_LIST = ["wss://relay.momostr.pink", "wss://relay.mostr.pub/"]  # , "wss://relay.snort.social"]

if use_logger:
    init_logger(LogLevel.DEBUG)


RELAY_LIST = ["wss://nostr.mom",
              #"wss://relay.primal.net",
              "wss://nostr.oxtr.dev",
              #"wss://relay.nostr.net"
              ]

def build_example_mostr(name, identifier, admin_config, options, image, cost=0, update_rate=180, processing_msg=None,
                      update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.LOGLEVEL = LogLevel.INFO
    # dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.SYNC_DB_RELAY_LIST = ["wss://nfrelay.app/?user=activitypub"]
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.LOGLEVEL = LogLevel.DEBUG
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show popular notes from Mostr.pub and Momostr.pink",
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "personalized": False,
        "amount": create_amount_tag(cost),
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 200)"
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)
    return DicoverContentCurrentlyPopularMostr(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                 admin_config=admin_config, options=options)


def playground():
    # Popular Global
    admin_config_global_wot = AdminConfig()
    admin_config_global_wot.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_global_wot.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_global_wot.UPDATE_PROFILE = update_profile
    #admin_config_global_wot.DELETE_NIP89 = True
    #admin_config_global_wot.PRIVKEY = ""
    #admin_config_global_wot.EVENTID = "c9dc34d2a2eca8a0d4972210aed1b63a36995cced07e1401d264c3bb48b4b715"
    #admin_config_global_wot.POW = True
    custom_processing_msg = ["Looking for popular Content on Mostr"]
    update_db = True



    options_mostr = {
        "db_name": "db/nostr_mostr.db",
        "db_since": 60 * 60 * 2,  # 1h since gmt,
    }
    cost = 0
    image = "https://i.nostr.build/mtkNd3J8m0mqj9nq.jpg"
    discovery_mostr = build_example_mostr("Trending on Mostr",
                                      "discovery_mostr",
                                      admin_config=admin_config_global_wot,
                                      options=options_mostr,
                                      image=image,
                                      cost=cost,
                                      update_rate=global_update_rate,
                                      processing_msg=custom_processing_msg,
                                      update_db=update_db)
    discovery_mostr.run(True)



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
