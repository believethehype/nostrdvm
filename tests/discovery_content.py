import asyncio
import json
import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel, Keys

# os.environ["RUST_BACKTRACE"] = "full"
from nostr_dvm.subscription import Subscription
from nostr_dvm.tasks.content_discovery_currently_latest_longform import DicoverContentLatestLongForm
from nostr_dvm.tasks.content_discovery_currently_latest_wiki import DicoverContentLatestWiki
from nostr_dvm.tasks.content_discovery_currently_popular import DicoverContentCurrentlyPopular
from nostr_dvm.tasks.content_discovery_currently_popular_by_top_zaps import DicoverContentCurrentlyPopularZaps
from nostr_dvm.tasks.content_discovery_currently_popular_followers import DicoverContentCurrentlyPopularFollowers
from nostr_dvm.tasks.content_discovery_currently_popular_gallery import DicoverContentCurrentlyPopularGallery
from nostr_dvm.tasks.content_discovery_currently_popular_mostr import DicoverContentCurrentlyPopularMostr
from nostr_dvm.tasks.content_discovery_currently_popular_nonfollowers import DicoverContentCurrentlyPopularNonFollowers
from nostr_dvm.tasks.content_discovery_currently_popular_topic import DicoverContentCurrentlyPopularbyTopic
from nostr_dvm.tasks.content_discovery_latest_one_per_follower import Discoverlatestperfollower
from nostr_dvm.tasks.content_discovery_update_db_only import DicoverContentDBUpdateScheduler
from nostr_dvm.tasks.discovery_trending_notes_nostrband import TrendingNotesNostrBand
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.database_utils import init_db
from nostr_dvm.utils.dvmconfig import build_default_config, DVMConfig
from nostr_dvm.utils.nip88_utils import NIP88Config, check_and_set_d_tag_nip88, check_and_set_tiereventid_nip88
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys

rebroadcast_NIP89 = False  # Announce NIP89 on startup Only do this if you know what you're doing.
rebroadcast_NIP65_Relay_List = True
update_profile = False

global_update_rate = 180  # set this high on first sync so db can fully sync before another process trys to.
use_logger = True
log_level = LogLevel.ERROR
max_sync_duration_in_h = 24

SYNC_DB_RELAY_LIST = ["wss://relay.damus.io",
                      "wss://relay.primal.net",
                      "wss://nostr.oxtr.dev"]

RELAY_LIST = ["wss://nostr.mom",
              "wss://relay.primal.net",
              "wss://nostr.oxtr.dev",
              ]

if use_logger:
    init_logger(log_level)


def build_db_scheduler(name, identifier, admin_config, options, image, description, update_rate=600, cost=0,
                       processing_msg=None, update_db=True, database=None):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.LOGLEVEL = LogLevel.INFO
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.DATABASE = database
    dvm_config.WOT_FILTERING = True

    # Activate these to use a subscription based model instead
    # dvm_config.SUBSCRIPTION_REQUIRED = True
    # dvm_config.SUBSCRIPTION_DAILY_COST = 1
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
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

    return DicoverContentDBUpdateScheduler(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                           admin_config=admin_config, options=options)


def build_example_topic(name, identifier, admin_config, options, image, description, update_rate=600, cost=0,
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

    return DicoverContentCurrentlyPopularbyTopic(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                 admin_config=admin_config, options=options)



def playground():
    main_db = "db/nostr_recent_notes.db"
    main_db_limit = 1024 # in mb

    DATABASE = asyncio.run(init_db(main_db, wipe=True, limit=main_db_limit, print_filesize=True))
    # DB Scheduler, do not announce, just use it to update the DB for the other DVMs.
    admin_config_db_scheduler = AdminConfig()
    options_db = {
        "db_name": main_db,
        "db_since": max_sync_duration_in_h * 60 * 60,  # 48h since gmt,
        "personalized": False,
        "max_db_size" : main_db_limit,
        "logger": False}
    image = ""
    about = "I just update the Database based on my schedule"
    db_scheduler = build_db_scheduler("DB Scheduler",
                                      "db_scheduler",
                                      admin_config_db_scheduler, options_db,
                                      image=image,
                                      description=about,
                                      update_rate=global_update_rate,
                                      cost=0,
                                      update_db=True,
                                      database=DATABASE)
    db_scheduler.run()



    # Popular Animals (Fluffy frens)
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config.UPDATE_PROFILE = update_profile

    options = {
        "search_list": ["catstr", "pawstr", "dogstr", "pugstr", " cat ", " cats ", "doggo", " deer ", " dog ", " dogs ",
                        " fluffy ",
                        " animal",
                        " duck", " lion ", " lions ", " fox ", " foxes ", " koala ", " koalas ", "capybara", "squirrel",
                        " monkey", " panda", "alpaca", " otter"],
        "avoid_list": ["porn", "broth", "smoke", "nsfw", "bitcoin", "bolt12", "bolt11", "github", "currency", "utxo",
                       "encryption", "government", "airpod", "ipad", "iphone", "android", "warren",
                       "moderna", "pfizer", " meat ", "pc mouse", "shotgun", "vagina", "rune", "testicle", "victim",
                       "sexualize", "murder", "tax", "engagement", "hodlers", "hodl", "gdp", "global markets", "crypto",
                       "presidency", "dollar", "asset", "microsoft", "amazon", "billionaire", "ceo", "industry",
                       "white house", "hot dog", "spirit animal", "migrant", "invasion", "blocks", "streaming",
                       "summary", "duckfat", "carnivore", "protein", "fats", "ass",
                       "wealth", "beef", "cunt", "nigger", "business", "tore off", "chart", "critical theory",
                       "law of nature",
                       "retail", "bakery", "synth", "slaughterhouse", "hamas", "dog days", "ww3", "socialmedia",
                       "nintendo", "signature", "deepfake", "congressman", "fried chicken", "cypherpunk",
                       "social media",
                       "chef", "cooked", "foodstr", "minister", "dissentwatch", "inkblot", "covid", "robot", "pandemic",
                       " dies ", "bethesda", " defi ", " minister ", "nostr-hotter-site", " ai ", "palestine",
                       "animalistic", "wherostr",
                       " hit by a", "https://boards.4chan", "https://techcrunch.com", "https://screenrant.com"],

        "must_list": ["http"],
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 24 * 60 * 60,  # 48h since gmt,
        "personalized": False,
        "logger": False}

    image = "https://image.nostr.build/f609311532c470f663e129510a76c9a1912ae9bc4aaaf058e5ba21cfb512c88e.jpg"
    description = "I show recent notes about animals"

    custom_processing_msg = ["Looking for fluffy frens...", "Let's see if we find some animals for you..",
                             "Looking for the goodest bois and girls.."]
    cost = 0
    update_db = False # we use the DB scheduler above for a shared database. Or don't use it and let the DVM manage it
    discovery_animals = build_example_topic("Fluffy Frens",
                                            "discovery_content_fluffy",
                                            admin_config, options,
                                            image=image,
                                            description=description,
                                            update_rate=global_update_rate,
                                            cost=cost,
                                            processing_msg=custom_processing_msg,
                                            update_db=update_db,
                                            database=DATABASE)

    discovery_animals.run()



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
