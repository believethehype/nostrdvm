import json
import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel, Keys

from nostr_dvm.subscription import Subscription
from nostr_dvm.tasks.content_discovery_currently_popular import DicoverContentCurrentlyPopular
from nostr_dvm.tasks.content_discovery_currently_popular_by_top_zaps import DicoverContentCurrentlyPopularZaps
from nostr_dvm.tasks.content_discovery_currently_popular_followers import DicoverContentCurrentlyPopularFollowers
from nostr_dvm.tasks.content_discovery_currently_popular_topic import DicoverContentCurrentlyPopularbyTopic
from nostr_dvm.tasks.discovery_trending_notes_nostrband import TrendingNotesNostrBand
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config, DVMConfig
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys

global_update_rate = 180  # set this high on first sync so db can fully sync before another process trys to.


def build_example_nostrband(name, identifier, admin_config, image, about, custom_processing_msg):
    dvm_config: DVMConfig = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.CUSTOM_PROCESSING_MESSAGE = custom_processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    # Add NIP89

    nip89info = {
        "name": name,
        "image": image,
        "picture": image,
        "about": about,
        "amount": "Free",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {}
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return TrendingNotesNostrBand(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                  admin_config=admin_config)


def build_example_topic(name, identifier, admin_config, options, image, description, update_rate=600, cost=0,
                        processing_msg=None, update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "image": image,
        "picture": image,
        "about": description,
        "lud16": dvm_config.LN_ADDRESS,
        "encryptionSupported": True,
        "cashuAccepted": True,
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
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return DicoverContentCurrentlyPopularbyTopic(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                 admin_config=admin_config, options=options)


def build_example_popular(name, identifier, admin_config, options, image, cost=0, update_rate=180, processing_msg=None,
                          update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    # dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "image": image,
        "picture": image,
        "about": "I show notes that are currently popular",
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
    return DicoverContentCurrentlyPopular(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                          admin_config=admin_config, options=options)


def build_example_popular_followers(name, identifier, admin_config, options, image, cost=0, update_rate=300,
                                    processing_msg=None, update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every x seconds
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "image": image,
        "picture": image,
        "about": "I show notes that are currently popular from people you follow",
        "lud16": dvm_config.LN_ADDRESS,
        "encryptionSupported": True,
        "cashuAccepted": True,
        "personalized": True,
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
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return DicoverContentCurrentlyPopularFollowers(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                   options=options,
                                                   admin_config=admin_config)


def build_example_top_zapped(name, identifier, admin_config, options, image, cost=0, update_rate=180,
                             processing_msg=None,
                             update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "image": image,
        "picture": image,
        "about": "I show notes that are currently zapped the most.",
        "lud16": dvm_config.LN_ADDRESS,
        "encryptionSupported": True,
        "cashuAccepted": True,
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
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    # admin_config.UPDATE_PROFILE = False
    # admin_config.REBROADCAST_NIP89 = False

    return DicoverContentCurrentlyPopularZaps(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                              admin_config=admin_config, options=options)


def playground():
    rebbroadcast_NIP89 = True  # Announce NIP89 on startup
    use_logger = False

    if use_logger:
        init_logger(LogLevel.INFO)

    # Popular NOSTR.band
    admin_config_trending_nostr_band = AdminConfig()
    admin_config_trending_nostr_band.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_trending_nostr_band.UPDATE_PROFILE = False
    # admin_config_trending_nostr_band.DELETE_NIP89 = True
    # admin_config_trending_nostr_band.PRIVKEY = "6b0c954dbdeb292785a80a98f0eaf78b55133639c73b8e93aed97a7f748cc88a"
    # admin_config_trending_nostr_band.EVENTID = "adc79716de7ba65ecd4154428fc624e8b43590f4dffbcb757ee2d8c00db54c7a"
    custom_processing_msg = "Looking for trending notes on nostr.band.."
    image = "https://nostr.band/android-chrome-192x192.png"
    about = "I show trending notes from nostr.band"
    trending_nb = build_example_nostrband("Trending Notes on nostr.band",
                                          "trending_notes_nostrband",
                                          image=image,
                                          about=about,
                                          admin_config=admin_config_trending_nostr_band,
                                          custom_processing_msg=custom_processing_msg)
    trending_nb.run()


    # Popular Animals (Fluffy frens)
    admin_config_animals = AdminConfig()
    admin_config_animals.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_animals.UPDATE_PROFILE = False
    # admin_config_animals.DELETE_NIP89 = True
    # admin_config_animals.PRIVKEY = "68a5d6bab857d8495e63cac55253b8b92b1117ce69d63305e12a3f994b911aff"
    # admin_config_animals.EVENTID = "64e3dcf8793aad1563a6644179cdbc3756d787d7adf613552cd1bc2e33c8031f"
    # admin_config_animals.POW = True

    options_animal = {
        "search_list": ["catstr", "pawstr", "dogstr", "pugstr", " cat ", " cats ", "doggo", " deer ", " dog ", " dogs ",
                        " fluffy ",
                        "animal",
                        " duck", " lion ", " lions ", " fox ", " foxes ", " koala ", " koalas ", "capybara", "squirrel",
                        " monkey", "panda", "alpaca", " otter"],
        "avoid_list": ["porn", "smoke", "nsfw", "bitcoin", "bolt12", "bolt11", "github", "currency", "utxo",
                       "encryption", "government", "airpod", "ipad", "iphone", "android", "warren",
                       "moderna", "pfizer", " meat ", "pc mouse", "shotgun", "vagina", "rune", "testicle", "victim",
                       "sexualize", "murder", "tax", "engagement", "hodlers", "hodl", "gdp", "global markets", "crypto",
                       "presidency", "dollar", "asset", "microsoft", "amazon", "billionaire", "ceo", "industry",
                       "white house", "hot dog", "spirit animal", "migrant", "invasion", "blocks", "streaming",
                       "summary",
                       "wealth", "beef", "cunt", "nigger", "business", "tore off", "chart",
                       "retail", "bakery", "synth", "slaughterhouse", "hamas", "dog days", "ww3", "socialmedia",
                       "nintendo", "signature", "deepfake", "congressman", "fried chicken", "cypherpunk",
                       "social media",
                       "chef", "cooked", "foodstr", "minister", "dissentwatch", "inkblot", "covid", "robot", "pandemic",
                       " dies ", "bethesda", " defi ", " minister ", "nostr-hotter-site", " ai ", "palestine",
                       "animalistic", "wherostr",
                       " hit by a", "https://boards.4chan", "https://techcrunch.com", "https://screenrant.com"],

        "must_list": ["http"],
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 48 * 60 * 60,  # 48h since gmt,
        "personalized": False,
        "logger": False}

    image = "https://image.nostr.build/f609311532c470f663e129510a76c9a1912ae9bc4aaaf058e5ba21cfb512c88e.jpg"
    description = "I show recent notes about animals"

    custom_processing_msg = ["Looking for fluffy frens...", "Let's see if we find some animals for you..",
                             "Looking for the goodest bois and girls.."]
    cost = 0
    update_db = True  # As this is our largerst DB we update it here, and the other dvms use it. TODO make an own scheduler that only updates the db
    discovery_animals = build_example_topic("Fluffy Frens",
                                            "discovery_content_fluffy",
                                            admin_config_animals, options_animal,
                                            image=image,
                                            description=description,
                                            update_rate=global_update_rate,
                                            cost=cost,
                                            processing_msg=custom_processing_msg,
                                            update_db=update_db)

    discovery_animals.run()

    # Popular Garden&Plants
    admin_config_plants = AdminConfig()
    admin_config_plants.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_plants.UPDATE_PROFILE = False
    # admin_config_plants.DELETE_NIP89 = True
    # admin_config_plants.PRIVKEY = "430bacf525a2f6efd6db1f049eb7c04e0c0314182ef1c17df39f46fe66416ddf"
    # admin_config_plants.EVENTID = "f42adb15f4c67b884d58b09084907d94471d1a54185dce0217a69111c703aa14"
    # admin_config_plants.POW = True
    options_plants = {
        "search_list": ["garden", "gardening", "nature", " plants ", " plant ", " herb ", " herbs " " pine ",
                        "homesteading", "rosemary", "chicken", "🪻", "🌿", "☘️", "🌲", "flower", "forest", "watering",
                        "permies", "planting", "farm", "vegetable", "fruit", " grass ", "sunshine",
                        "#flowerstr", "#bloomscrolling", "#treestr", "#plantstr", "touchgrass", ],
        "avoid_list": ["porn", "smoke", "nsfw", "bitcoin", "bolt12", "bolt11", "github", "currency", "utxo",
                       "encryption", "government", "airpod", "ipad", "iphone", "android", "warren",
                       "moderna", "pfizer", "corona", "socialism",
                       "murder", "tax", "engagement", "hodlers", "hodl", "gdp", "global markets", "crypto", "wherostr",
                       "presidency", "dollar", "asset", "microsoft", "amazon", "billionaire", "ceo", "industry",
                       "white house", "blocks", "streaming", "summary", "wealth", "beef", "cunt", "nigger", "business",
                       "retail", "bakery", "synth", "slaughterhouse", "hamas", "dog days", "ww3", "socialmedia",
                       "nintendo", "signature", "deepfake", "congressman", "cypherpunk", "minister", "dissentwatch",
                       "inkblot", "covid", "robot", "pandemic", "bethesda", "zap farming", " defi ", " minister ",
                       "nostr-hotter-site", " ai ", "palestine", "https://boards.4chan", "https://techcrunch.com",
                       "https://screenrant.com"],
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 12 * 60 * 60,  # 12h since gmt
        "personalized": False,
        "logger": False}

    image = "https://image.nostr.build/a816f3f5e98e91e8a47d50f4cd7a2c17545f556d9bb0a6086a659b9abdf7ab68.jpg"
    description = "I show recent notes about plants and gardening"
    custom_processing_msg = ["Finding the best notes for you.. #blooming", "Looking for some positivity.. #touchgrass",
                             "Looking for #goodvibes..", "All I do is #blooming.."]
    update_db = False
    cost = 0
    discovery_test_sub = build_example_topic("Garden & Growth", "discovery_content_garden",
                                             admin_config_plants, options_plants,
                                             image=image,
                                             description=description,
                                             update_rate=global_update_rate,
                                             cost=cost,
                                             processing_msg=custom_processing_msg,
                                             update_db=update_db)
    discovery_test_sub.run()

    # Popular top zapped
    admin_config_top_zaps = AdminConfig()
    admin_config_top_zaps.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_top_zaps.UPDATE_PROFILE = False
    custom_processing_msg = ["Looking for most zapped notes", "Let's see which notes people currently zap..",
                             "Let's find valuable notes. #value4value"]
    update_db = False

    options_top_zapped = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 60 * 60 * 4,  # 4h since gmt,
    }
    cost = 0
    image = "https://image.nostr.build/c6879f458252641d04d0aa65fd7f1e005a4f7362fd407467306edc2f4acdb113.jpg"
    discovery_topzaps = build_example_top_zapped("Top Zapped notes",
                                                 "discovery_content_top_zaps",
                                                 admin_config=admin_config_top_zaps,
                                                 options=options_top_zapped,
                                                 image=image,
                                                 cost=cost,
                                                 update_rate=global_update_rate,
                                                 processing_msg=custom_processing_msg,
                                                 update_db=update_db)

    discovery_topzaps.run()

    # Popular Followers
    admin_config_followers = AdminConfig()
    admin_config_followers.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_followers.UPDATE_PROFILE = False
    # admin_config_followers.DELETE_NIP89 = True
    # admin_config_followers.PRIVKEY = "d09dd9a52857236627eb0c12e0e74343e38d77c5ca98bcd8cdb5d6f5edaaf91d"
    # admin_config_followers.EVENTID = "b778cb713565e42e97cf2095f9390c626bb67c564eb4d20e379ef7510ed8e9d4"
    admin_config_followers.POW = True
    custom_processing_msg = ["Processing popular notes from npubs you follow..",
                             "Let's see what npubs you follow have been up to..",
                             "Processing a personalized feed, just for you.."]
    update_db = False
    options_followers_popular = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 2 * 60 * 60,  # 2h since gmt,
    }
    cost = 0
    image = "https://image.nostr.build/d92652a6a07677e051d647dcf9f0f59e265299b3335a939d008183a911513f4a.jpg"

    discovery_followers = build_example_popular_followers(
        "Popular from npubs you follow",
        "discovery_content_followers",
        admin_config=admin_config_followers,
        options=options_followers_popular,
        cost=cost,
        image=image,
        update_rate=global_update_rate,
        processing_msg=custom_processing_msg,
        update_db=update_db)
    discovery_followers.run()

    # Popular Global
    admin_config_global_popular = AdminConfig()
    admin_config_global_popular.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_global_popular.UPDATE_PROFILE = False
    # admin_config_global_popular.DELETE_NIP89 = True
    # admin_config_global_popular.PRIVKEY = "fae983211e316ce37785acc8b15c1bb72c9deb3451fd862f2416fb6c503885f6"
    # admin_config_global_popular.EVENTID = "548b7c3d24b2b4cef8681f16467557eb4d45531691cdc637d010bcd9bdd38ac1"
    custom_processing_msg = ["Looking for popular notes on the Nostr..", "Let's see what's trending on Nostr..",
                             "Finding the best notes on the Nostr.."]
    update_db = False

    options_global_popular = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 60 * 60,  # 1h since gmt,
    }
    cost = 0
    image = "https://image.nostr.build/b29b6ec4bf9b6184f69d33cb44862db0d90a2dd9a506532e7ba5698af7d36210.jpg"
    discovery_global = build_example_popular("Currently Popular Notes DVM",
                                             "discovery_content_test",
                                             admin_config=admin_config_global_popular,
                                             options=options_global_popular,
                                             image=image,
                                             cost=cost,
                                             update_rate=global_update_rate,
                                             processing_msg=custom_processing_msg,
                                             update_db=update_db)
    discovery_global.run()

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
