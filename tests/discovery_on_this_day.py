import asyncio
import datetime
import json
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel

# os.environ["RUST_BACKTRACE"] = "full"
from nostr_dvm.tasks.content_discovery_on_this_day import DicoverContentOnThisDay
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.database_utils import init_db
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST

rebroadcast_NIP89 = False  # Announce NIP89 on startup Only do this if you know what you're doing.
rebroadcast_NIP65_Relay_List = True
update_profile = True

global_update_rate = 60*60  # set this high on first sync so db can fully sync before another process trys to.
use_logger = True
log_level = LogLevel.ERROR
max_sync_duration_in_h = 24

if use_logger:
    init_logger(log_level)


RELAY_LIST = ["wss://nostr.mom",
              "wss://relay.primal.net",
              "wss://nostr.oxtr.dev",
              ]

SYNC_DB_RELAY_LIST = ["wss://relay.damus.io",
                      "wss://relay.primal.net",
                      "wss://nostr.oxtr.dev"
                      ]



def build_example_on_this_day(name, identifier, admin_config, options, image, description, update_rate=600, cost=0,
                        processing_msg=None, update_db=True, database=None):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.LOGLEVEL = LogLevel.INFO
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.DATABASE = database
    dvm_config.SEND_FEEDBACK_EVENTS = False
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": description,
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "personalized": False,
        "amount": create_amount_tag(cost),
        "nip90Params": {
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

    return DicoverContentOnThisDay(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                 admin_config=admin_config, options=options)


def playground():
    main_db = "db/nostr_on_this_day.db"
    main_db_limit = 1024  # in mb

    database = asyncio.run(init_db(main_db, wipe=True, limit=main_db_limit, print_filesize=True))
    last_year = datetime.date.today().year - 1

    if last_year % 4 == 0 and (last_year % 100 != 0 or last_year % 400 == 0):
        days = 366
    else:
        days = 365

    # Popular Tweets 
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config.UPDATE_PROFILE = update_profile

    options = {
        "db_name": main_db,
        "db_since": 24 * 60 * 60 * (days+1),
        "personalized": False,
        "logger": False}

    image = "https://i.nostr.build/TxRou5DdFhxVqtHa.png"
    description = "I show popular notes on this day one year ago"

    custom_processing_msg = ["Let's see"]
    cost = 0
    update_db = True  # we use the DB scheduler above for a shared database. Or don't use it and let the DVM manage it
    discovery_onthisday= build_example_on_this_day("On This Day",
                                            "discovery_content_on_this_day",
                                            admin_config, options,
                                            image=image,
                                            description=description,
                                            update_rate=global_update_rate,
                                            cost=cost,
                                            processing_msg=custom_processing_msg,
                                            update_db=update_db,
                                            database=database)

    discovery_onthisday.run()


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
