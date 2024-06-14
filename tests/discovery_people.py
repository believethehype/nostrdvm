import json
import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel, Keys, NostrLibrary

from nostr_dvm.tasks.people_discovery_wot import DiscoverPeopleWOT
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag



rebroadcast_NIP89 = False   # Announce NIP89 on startup
rebroadcast_NIP65_Relay_List = False
update_profile = False

global_update_rate = 1200     # set this high on first sync so db can fully sync before another process trys to.
use_logger = True

AVOID_PAID_OUTBOX_RELAY_LIST = ["wss://nostrelay.yeghro.site", "wss://nostr.wine", "wss://filter.nostr.wine"
                                    "wss://nostr21.com", "wss://nostr.bitcoiner.social", "wss://nostr.orangepill.dev",
                                    "wss://relay.lnpay.me", "wss://relay.snort.social", "wss://relay.minds.com/nostr/v1/ws",
                                    "wss://nostr-pub.semisol.dev", "wss://mostr.mostr.pub", "wss://relay.mostr.pub", "wss://minds.com",
                                    "wss://yabu.me", "wss://relay.yozora.world", "wss://filter.nostr.wine/?global=all", "wss://eden.nostr.land",
                                    "wss://relay.orangepill.ovh", "wss://nostr.jcloud.es", "wss://af.purplerelay.com",  "wss://za.purplerelay.com",
                                    "wss://relay.nostrich.land", "wss://relay.nostrplebs.com", "wss://relay.nostrich.land",
                                    "wss://rss.nos.social", "wss://atlas.nostr.land", "wss://puravida.nostr.land", "wss://nostr.inosta.cc",
                                    "wss://relay.orangepill.dev", "wss://no.str.cr", "wss://nostr.milou.lol", "wss://relay.nostr.com.au",
                                    "wss://puravida.nostr.land", "wss://atlas.nostr.land", "wss://nostr-pub.wellorder.net", "wss://eelay.current.fyi",
                                    "wss://nostr.thesamecat.io", "wss://nostr.plebchain.org", "wss://relay.noswhere.com", "wss://nostr.uselessshit.co",
                                    "wss://bitcoiner.social", "wss://relay.stoner.com", "wss://nostr.l00p.org", "wss://relay.nostr.ro", "wss://nostr.kollider.xyz",
                                    "wss://relay.valera.co", "wss://relay.austrich.net", "wss://relay.nostrich.de", "wss://nostr.azte.co", "wss://nostr-relay.schnitzel.world",
                                    "wss://relay.nostriches.org", "wss://happytavern.co", "wss://onlynotes.lol", "wss://offchain.pub", "wss://purplepag.es", "wss://relay.plebstr.com",
                                    "wss://poster.place/relay", "wss://relayable.org", "wss://bbb.santos.lol", "wss://relay.bitheaven.social", "wss://theforest.nostr1.com",
                                    "wss://relay.nostrati.com", "wss://purplerelay.com", "wss://hist.nostr.land", "wss://creatr.nostr.wine", "ws://localhost:4869",
                                    "wss://pyramid.fiatjaf.com", "wss://relay.nos.social", "wss://nostr.thank.eu", "wss://inbox.nostr.wine", "wss://relay.pleb.to", "wss://welcome.nostr.wine",
                                    "wss://relay.nostrview.com", "wss://nostr.land", "wss://eu.purplerelay.com", "wss://xmr.usenostr.org",  "wss://relay.pleb.to", "wss://nostr-relay.app"
                                    ]

RECONCILE_DB_RELAY_LIST = ["wss://relay.damus.io"]  # , "wss://relay.snort.social"]


if use_logger:
    init_logger(LogLevel.INFO)




def build_example_wot(name, identifier, admin_config, options, image, cost=0, update_rate=180, processing_msg=None,
                          update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.LOGLEVEL = LogLevel.INFO
    # dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.RECONCILE_DB_RELAY_LIST = RECONCILE_DB_RELAY_LIST
    dvm_config.LOGLEVEL = LogLevel.DEBUG
    dvm_config.FIX_COST = cost
    #dvm_config.RELAY_LIST = ["wss://dvms.f7z.io", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg",
    #"wss://relay.nostr.net"]
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    dvm_config.AVOID_PAID_OUTBOX_RELAY_LIST = AVOID_PAID_OUTBOX_RELAY_LIST
    #dvm_config.RELAY_LIST = ["wss://dvms.f7z.io",
    #                         "wss://nostr.mom", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg"
    #                         ]
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "image": image,
        "picture": image,
        "about": "I show people to follow from your WOT",
        "lud16": dvm_config.LN_ADDRESS,
        "encryptionSupported": True,
        "cashuAccepted": True,
        "personalized": True,
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
    return DiscoverPeopleWOT(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                          admin_config=admin_config, options=options)



def playground():


    # Popular Global
    admin_config_global_wot = AdminConfig()
    admin_config_global_wot.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_global_wot.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_global_wot.UPDATE_PROFILE = update_profile
    # admin_config_global_popular.DELETE_NIP89 = True
    # admin_config_global_popular.PRIVKEY = ""
    # admin_config_global_popular.EVENTID = "2fea4ee2ccf0fa11db171113ffd7a676f800f34121478b7c9a4e73c2f1990028"
    # admin_config_global_popular.POW = True
    custom_processing_msg = ["Looking for people, that your WOT follows"]
    update_db = True

    options_wot = {
        "db_name": "db/nostr_followlists.db",
        "db_since": 60 * 60 * 24 * 365,  # 1h since gmt,
    }
    cost = 0
    image = "https://image.nostr.build/b29b6ec4bf9b6184f69d33cb44862db0d90a2dd9a506532e7ba5698af7d36210.jpg"
    discovery_wot = build_example_wot("People you might know",
                                             "discovery_people_wot",
                                             admin_config=admin_config_global_wot,
                                             options=options_wot,
                                             image=image,
                                             cost=cost,
                                             update_rate=global_update_rate,
                                             processing_msg=custom_processing_msg,
                                             update_db=update_db)
    discovery_wot.run()

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
