import json
import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel, Keys, NostrLibrary

from nostr_dvm.tasks.content_discovery_currently_popular_gallery import DicoverContentCurrentlyPopularGallery
from nostr_dvm.tasks.content_discovery_currently_popular_mostr import DicoverContentCurrentlyPopularMostr
from nostr_dvm.tasks.content_discovery_latest_one_per_follower import Discoverlatestperfollower
from nostr_dvm.tasks.people_discovery_wot import DiscoverPeopleWOT
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag

rebroadcast_NIP89 = False  # Announce NIP89 on startup
rebroadcast_NIP65_Relay_List = False
update_profile = False

global_update_rate = 60  # set this high on first sync so db can fully sync before another process trys to.
use_logger = True
# these do not support nengentropy
#RECONCILE_DB_RELAY_LIST = ["wss://relay.momostr.pink", "wss://relay.mostr.pub/"]  # , "wss://relay.snort.social"]

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
    # "wss://relay.nostr.net"]
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    # dvm_config.RELAY_LIST = ["wss://dvms.f7z.io",
    #                         "wss://nostr.mom", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg"
    #                         ]
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "image": image,
        "picture": image,
        "about": "I show the single latest note of people you follow",
        "lud16": dvm_config.LN_ADDRESS,
        "encryptionSupported": True,
        "cashuAccepted": True,
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
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    return Discoverlatestperfollower(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                 admin_config=admin_config, options=options)


def playground():
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
    discovery_one_per_follow = build_example_oneperfollow("Lasted per follow",
                                      "discovery_latest_per_follow",
                                      admin_config=admin_config_opf,
                                      options=options_opf,
                                      image=image,
                                      cost=cost,
                                      update_rate=global_update_rate,
                                      processing_msg=custom_processing_msg,
                                      update_db=update_db)
    discovery_one_per_follow.run()

    # discovery_test_sub = content_discovery_currently_popular.build_example_subscription("Currently Popular Notes DVM (with Subscriptions)", "discovery_content_test", admin_config)
    # discovery_test_sub.run()

    # Subscription Manager DVM
    # subscription_config = DVMConfig()
    # subscription_config.PRIVATE_KEY = check_and_set_private_key("dvm_subscription")
    # npub = Keys.parse(subscription_config.PRIVATE_KEY).public_key().to_bech32()
    # invoice_key, admin_key, wallet_id, user_id, lnaddress = check_and_set_ln_bits_keys("dvm_subscription", npub)
    # subscription_config.LNBITS_INVOICE_KEY = invoice_key
    # subscription_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    # subscription_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    # sub_admin_config = AdminConfig()
    # sub_admin_config.USERNPUBS = ["7782f93c5762538e1f7ccc5af83cd8018a528b9cd965048386ca1b75335f24c6"] #Add npubs of services that can contact the subscription handler

    # currently there is none, but add this once subscriptions are live.
    # x = threading.Thread(target=Subscription, args=(Subscription(subscription_config, sub_admin_config),))
    # x.start()

    # keep_alive()


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
