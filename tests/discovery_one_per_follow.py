import json
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.content_discovery_latest_one_per_follower import Discoverlatestperfollower
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag

rebroadcast_NIP89 = False  # Announce NIP89 on startup
rebroadcast_NIP65_Relay_List = False
update_profile = False

global_update_rate = 60  # set this high on first sync so db can fully sync before another process trys to.
use_logger = True
# these do not support nengentropy
#SYNC_DB_RELAY_LIST = ["wss://relay.momostr.pink", "wss://relay.mostr.pub/"]  # , "wss://relay.snort.social"]

if use_logger:
    init_logger(LogLevel.ERROR)


def build_example_oneperfollow(name, identifier, admin_config, options, image, cost=0, update_rate=180, processing_msg=None,
                      update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.LOGLEVEL = LogLevel.INFO
    # dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = False
    dvm_config.LOGLEVEL = LogLevel.DEBUG
    dvm_config.FIX_COST = cost
    dvm_config.RELAY_LIST = ["wss://relay.damus.io", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg", "wss://relay.primal.net"]
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show the single latest note of people you follow",
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
    return Discoverlatestperfollower(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                 admin_config=admin_config, options=options)


def playground():

    framework = DVMFramework()
    # Popular Global
    admin_config_opf = AdminConfig()
    admin_config_opf.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_opf.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_opf.UPDATE_PROFILE = update_profile
    #admin_config_opf.DELETE_NIP89 = True
    #admin_config_opf.PRIVKEY = ""
    #admin_config_opf.EVENTID = ""
    #admin_config_opf.POW = True
    custom_processing_msg = ["Looking for latest content by people you follow.."]
    update_db = True



    options_opf = {
        "db_name": "db/nostr_mostr.db",
        "db_since": 60 * 60 * 2,  # 1h since gmt,
    }
    cost = 0
    image = "https://i.nostr.build/H6SMmCl7eRDvkbAn.jpg"
    discovery_one_per_follow = build_example_oneperfollow("One per follow",
                                      "discovery_latest_per_follow",
                                      admin_config=admin_config_opf,
                                      options=options_opf,
                                      image=image,
                                      cost=cost,
                                      update_rate=global_update_rate,
                                      processing_msg=custom_processing_msg,
                                      update_db=update_db)

    framework.add(discovery_one_per_follow)

    framework.run()




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
