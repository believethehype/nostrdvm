import asyncio
import json
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.content_discovery_for_you import DiscoverContentForYou
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.database_utils import init_db
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST

rebroadcast_NIP89 = True
rebroadcast_NIP65_Relay_List = True
update_profile = True

global_update_rate = 600
use_logger = True
log_level = LogLevel.ERROR

RELAY_LIST = ["wss://relay.nostrdvm.com",
              "wss://nostr.oxtr.dev"]

SYNC_DB_RELAY_LIST = ["wss://relay.ditto.pub",
                      "wss://purplerelay.com",
                      "wss://nostr.bitcoiner.social",
                      "wss://nostr.oxtr.dev",
                      "wss://relay.nostr.net"]

if use_logger:
    init_logger(log_level)


def build_for_you(name, identifier, admin_config, options, image, cost=0, update_rate=600,
                  processing_msg=None, update_db=True, database=None):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.DATABASE = database
    dvm_config.LOGLEVEL = LogLevel.INFO
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SEND_FEEDBACK_EVENTS = True
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show a personalized For You feed, ranked for you",
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "personalized": True,
        "amount": create_amount_tag(cost),
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default 200)"
            },
            "user": {
                "required": False,
                "values": [],
                "description": "Pubkey to build the feed for (defaults to the requester)"
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)
    return DiscoverContentForYou(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                 admin_config=admin_config, options=options)


def playground():
    framework = DVMFramework()
    main_db = "db/nostr_foryou.db"
    database = asyncio.run(init_db(main_db, wipe=False, limit=1024, print_filesize=True))

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config.UPDATE_PROFILE = update_profile

    options = {
        "db_name": main_db,
        "db_since": 7 * 24 * 60 * 60,
        "history_days": 7,
        "profile_ttl_seconds": 3600,
    }
    for_you = build_for_you("For You", "discovery_content_for_you", admin_config, options,
                            image="https://blossom.primal.net/7677454a5f9a6b8845c67f2934d0429cb68208be076baa780415f5b210b1b502.jpg",
                            update_rate=global_update_rate,
                            processing_msg=["Generating your feed.."],
                            update_db=True, database=database)
    framework.add(for_you)
    framework.run()


if __name__ == '__main__':
    env_path = Path('.env')
    if not env_path.is_file():
        with open('.env', 'w') as f:
            f.write('')
    dotenv.load_dotenv(env_path, verbose=True, override=True)
    playground()
