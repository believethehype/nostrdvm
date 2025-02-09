import json
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.content_discovery_currently_latest_longform import DicoverContentLatestLongForm
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST

rebroadcast_NIP89 = True  # Announce NIP89 on startup Only do this if you know what you're doing.
rebroadcast_NIP65_Relay_List = True
update_profile = False

global_update_rate = 180  # set this high on first sync so db can fully sync before another process trys to.
use_logger = True
log_level = LogLevel.INFO


RELAY_LIST = ["wss://nostr.mom",
              "wss://relay.primal.net",
              "wss://nostr.oxtr.dev",
              "wss://relay.nostrdvm.com",
              ]

SYNC_DB_RELAY_LIST = [
                      "wss://pareto.nostr1.com",
                      "wss://nostr.pareto.space"
                    ]

if use_logger:
    init_logger(log_level)


def build_longform_alt(name, identifier, admin_config, options, image, description, cost=0, update_rate=180,  processing_msg=None,
                       update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = True
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SEND_FEEDBACK_EVENTS = False
    dvm_config.LOGLEVEL = LogLevel.INFO
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    dvm_config.DELETE_ANNOUNCEMENT_ON_SHUTDOWN = True
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

    return DicoverContentLatestLongForm(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                        admin_config=admin_config, options=options)

def playground():
    framework = DVMFramework()


    # Popular Animals (Fluffy frens)
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config.UPDATE_PROFILE = update_profile

    options = {
        "db_name": "db/nostr_pareto.db",
        "db_since": 24 * 60 * 60 * 365,  # 48h since gmt,
        "personalized": False,
        "logger": False}

    image = "https://route96.pareto.space/c96d2bff659509249cd7f8ce39e0e63f1c13d0c2e1da427b60dd991acc9984a5.webp"
    description = "I show Notes on Pareto"

    custom_processing_msg = ["Checking new Posts on Pareto."]
    cost = 0
    update_db = True  # we use the DB scheduler above for a shared database. Or don't use it and let the DVM manage it
    pareto = build_longform_alt("Pareto",
                                            "pareto_test",
                                            admin_config, options,
                                            image=image,
                                            description=description,
                                            update_rate=global_update_rate,
                                            cost=cost,
                                            processing_msg=custom_processing_msg,
                                            update_db=update_db,
                                            )

    framework.add(pareto)

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
