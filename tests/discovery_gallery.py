import json
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.content_discovery_currently_popular_gallery import DicoverContentCurrentlyPopularGallery
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag

rebroadcast_NIP89 = False  # Announce NIP89 on startup
rebroadcast_NIP65_Relay_List = True
update_profile = True

global_update_rate = 500  # set this high on first sync so db can fully sync before another process trys to.
use_logger = True

if use_logger:
    init_logger(LogLevel.ERROR)


def build_example_gallery(name, identifier, admin_config, options, image, cost=0, update_rate=180, processing_msg=None,
                      update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show popular pictures from the Olas feed",
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
    return DicoverContentCurrentlyPopularGallery(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                 admin_config=admin_config, options=options)


def playground():
    framework = DVMFramework()

    # Popular Global
    admin_config_global_gallery = AdminConfig()
    admin_config_global_gallery.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_global_gallery.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_global_gallery.UPDATE_PROFILE = update_profile
    admin_config_global_gallery.DELETE_NIP89 = False
    admin_config_global_gallery.PRIVKEY = ""
    admin_config_global_gallery.EVENTID = ""
    admin_config_global_gallery.POW = False
    custom_processing_msg = ["Looking for popular Gallery entries"]
    update_db = True

    options_gallery = {
        "db_name": "db/nostr_olas.db",
        "db_since": 60 * 60 * 24 * 4,  # 2d since gmt,
    }


    cost = 0
    image = "https://image.nostr.build/f5901156825ef1d9dad557890020ce9c5d917f52bc31863226b980fa232a9c23.png"
    discover_gallery = build_example_gallery("Popular on Olas",
                                      "discovery_gallery_entries",
                                      admin_config=admin_config_global_gallery,
                                      options=options_gallery,
                                      image=image,
                                      cost=cost,
                                      update_rate=global_update_rate,
                                      processing_msg=custom_processing_msg,
                                      update_db=update_db)

    framework.add(discover_gallery)

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
