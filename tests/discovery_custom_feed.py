import json
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.content_discovery_currently_popular_topic import DicoverContentCurrentlyPopularbyTopic
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST

rebroadcast_NIP89 = False  # Announce NIP89 on startup
rebroadcast_NIP65_Relay_List = True
update_profile = True

global_update_rate = 60  # set this high on first sync so db can fully sync before another process trys to.
use_logger = True
# these do not support nengentropy
#SYNC_DB_RELAY_LIST = ["wss://relay.momostr.pink", "wss://relay.mostr.pub/"]  # , "wss://relay.snort.social"]

if use_logger:
    init_logger(LogLevel.ERROR)


SYNC_DB_RELAY_LIST = [ "wss://relay.nostr.net", "wss://relay.nostr.bg", "wss://relay.damus.io", "wss://nostr.oxtr.dev"]
RELAY_LIST = ["wss://relay.primal.net",
              "wss://nostr.mom", "wss://nostr.oxtr.dev",
              "wss://relay.nostr.net"
              ]

def build_example_topic(name, identifier, admin_config, options, image, description, update_rate=600, cost=0,
                        processing_msg=None, update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.LOGLEVEL = LogLevel.DEBUG
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": description,
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "personalized": True,
        "amount": create_amount_tag(cost),
        "nip90Params": {
            "search_list": {
                "required": True,
                "values": [],
                "description": "A comma seperated list of terms to look for"
            },
            "must_list": {
                "required": True,
                "values": [],
                "description": "A comma seperated list of terms that must be in a note"
            },
            "avoid_list": {
                "required": True,
                "values": [],
                "description": "A comma seperated list of terms to avoid in notes"
            },
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 100)"
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    return DicoverContentCurrentlyPopularbyTopic(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                 admin_config=admin_config, options=options)


def playground():
    framework = DVMFramework()

    admin_config_plants = AdminConfig()
    admin_config_plants.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_plants.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_plants.UPDATE_PROFILE = update_profile
    # admin_config_plants.DELETE_NIP89 = True
    # admin_config_plants.PRIVKEY = ""
    # admin_config_plants.EVENTID = "ff28be59708ee597c7010fd43a7e649e1ab51da491266ca82a84177e0007e4d6"
    # admin_config_plants.POW = True
    options_plants = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 48 * 60 * 60,  # 12h since gmt
        "personalized": True,
        "logger": False}

    image = "https://i.nostr.build/VKcTV1Qo79ZRelrG.jpg"
    description = "I show recent notes about custom topics you provide me with"
    custom_processing_msg = ["Finding the best notes for you.. #blooming"]
    update_db = False
    cost = 0
    discovery_custom = build_example_topic("Custom Discovery", "discovery_content_custom",
                                           admin_config_plants, options_plants,
                                           image=image,
                                           description=description,
                                           update_rate=global_update_rate,
                                           cost=cost,
                                           processing_msg=custom_processing_msg,
                                           update_db=update_db)

    framework.add(discovery_custom)

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
