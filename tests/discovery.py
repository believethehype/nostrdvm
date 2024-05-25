import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import Keys, init_logger, LogLevel

from nostr_dvm.subscription import Subscription
from nostr_dvm.tasks import content_discovery_currently_popular, content_discovery_currently_popular_topic, \
    discovery_trending_notes_nostrband, content_discovery_currently_popular_followers
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.backend_utils import keep_alive
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys


def playground():
    rebbroadcast_NIP89 = True
    delete_NIP = False
    use_logger = False

    if use_logger:
        init_logger(LogLevel.INFO)

    # Popular NOSTR.band
    admin_config_trending_nostr_band = AdminConfig()
    admin_config_trending_nostr_band.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_trending_nostr_band.UPDATE_PROFILE = False
    admin_config_trending_nostr_band.DELETE_NIP89 = False
    #admin_config_trending_nostr_band.PRIVKEY = "6b0c954dbdeb292785a80a98f0eaf78b55133639c73b8e93aed97a7f748cc88a"
    #admin_config_trending_nostr_band.EVENTID = "adc79716de7ba65ecd4154428fc624e8b43590f4dffbcb757ee2d8c00db54c7a"
    custom_processing_msg = "Looking for trending notes on nostr.band.."
    trending_nb = discovery_trending_notes_nostrband.build_example("Trending Notes on nostr.band",
                                                                   "trending_notes_nostrband",
                                                                   admin_config_trending_nostr_band,
                                                                   custom_processing_msg)
    trending_nb.run()

    # Popular Garden&Plants
    admin_config_plants = AdminConfig()
    admin_config_plants.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_plants.UPDATE_PROFILE = False
    admin_config_plants.DELETE_NIP89 = False
    admin_config_plants.PRIVKEY = "430bacf525a2f6efd6db1f049eb7c04e0c0314182ef1c17df39f46fe66416ddf"
    admin_config_plants.EVENTID = "f42adb15f4c67b884d58b09084907d94471d1a54185dce0217a69111c703aa14"
    admin_config_plants.POW = True
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
        "db_since": 12 * 60 * 60,  # 10h since gmt
        "personalized": False}

    image = "https://image.nostr.build/a816f3f5e98e91e8a47d50f4cd7a2c17545f556d9bb0a6086a659b9abdf7ab68.jpg"
    description = "I show recent notes about plants and gardening"
    custom_processing_msg = ["Finding the best notes for you.. #blooming", "Looking for some positivity.. #touchgrass",
                             "Looking for #goodvibes.."]
    update_db = False
    cost = 0
    discovery_test_sub = content_discovery_currently_popular_topic.build_example("Garden & Growth",
                                                                                 "discovery_content_garden",
                                                                                 admin_config_plants, options_plants,
                                                                                 image,
                                                                                 description, 180, cost,
                                                                                 custom_processing_msg,
                                                                                 update_db)
    discovery_test_sub.run()

    # Popular Animals (Fluffy frens)
    admin_config_animals = AdminConfig()
    admin_config_animals.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_animals.UPDATE_PROFILE = False
    admin_config_animals.DELETE_NIP89 = False
    admin_config_animals.PRIVKEY = "68a5d6bab857d8495e63cac55253b8b92b1117ce69d63305e12a3f994b911aff"
    admin_config_animals.EVENTID = "64e3dcf8793aad1563a6644179cdbc3756d787d7adf613552cd1bc2e33c8031f"
    admin_config_animals.POW = True

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
        "personalized": False}

    image = "https://image.nostr.build/f609311532c470f663e129510a76c9a1912ae9bc4aaaf058e5ba21cfb512c88e.jpg"
    description = "I show recent notes about animals"

    custom_processing_msg = ["Looking for fluffy frens...", "Let's see if we find some animals for you..",
                             "Looking for the goodest bois and girls.."]
    cost = 0
    update_db = True  # As this is our largerst DB we update it here, and the other dvms use it. TODO make an own scheduler that only updates the db
    discovery_animals = content_discovery_currently_popular_topic.build_example("Fluffy Frens",
                                                                                "discovery_content_fluffy",
                                                                                admin_config_animals, options_animal,
                                                                                image,
                                                                                description, 180, cost,
                                                                                custom_processing_msg,
                                                                                update_db)
    discovery_animals.run()

    # Popular Followers
    admin_config_followers = AdminConfig()
    admin_config_followers.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_followers.UPDATE_PROFILE = False
    admin_config_followers.DELETE_NIP89 = False
    admin_config_followers.PRIVKEY = "d09dd9a52857236627eb0c12e0e74343e38d77c5ca98bcd8cdb5d6f5edaaf91d"
    admin_config_followers.EVENTID = "b778cb713565e42e97cf2095f9390c626bb67c564eb4d20e379ef7510ed8e9d4"
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

    discovery_followers = content_discovery_currently_popular_followers.build_example(
        "Popular from npubs you follow",
        "discovery_content_followers",
        admin_config=admin_config_followers,
        options=options_followers_popular,
        cost=cost,
        update_rate=180,
        processing_msg=custom_processing_msg,
        update_db=update_db)
    discovery_followers.run()

    # Popular Global
    admin_config_global_popular = AdminConfig()
    admin_config_global_popular.REBROADCAST_NIP89 = rebbroadcast_NIP89
    admin_config_global_popular.UPDATE_PROFILE = False
    #admin_config_global_popular.DELETE_NIP89 = True
    #admin_config_global_popular.PRIVKEY = "fae983211e316ce37785acc8b15c1bb72c9deb3451fd862f2416fb6c503885f6"
    #admin_config_global_popular.EVENTID = "548b7c3d24b2b4cef8681f16467557eb4d45531691cdc637d010bcd9bdd38ac1"
    custom_processing_msg = ["Looking for popular notes on the Nostr..", "Let's see what's trending on Nostr..",
                             "Finding the best notes on the Nostr.."]
    update_db = False

    options_global_popular = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 60 * 60,  # 1h since gmt,
    }
    cost = 0
    discovery_global = content_discovery_currently_popular.build_example("Currently Popular Notes DVM",
                                                                         "discovery_content_test",
                                                                         admin_config=admin_config_global_popular,
                                                                         options=options_global_popular,
                                                                         cost=cost,
                                                                         update_rate=180,
                                                                         processing_msg=custom_processing_msg,
                                                                         update_db=update_db)
    discovery_global.run()

    # discovery_test_sub = content_discovery_currently_popular.build_example_subscription("Currently Popular Notes DVM (with Subscriptions)", "discovery_content_test", admin_config)
    # discovery_test_sub.run()

    # Subscription Manager DVM
    subscription_config = DVMConfig()
    subscription_config.PRIVATE_KEY = check_and_set_private_key("dvm_subscription")
    npub = Keys.parse(subscription_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, user_id, lnaddress = check_and_set_ln_bits_keys("dvm_subscription", npub)
    subscription_config.LNBITS_INVOICE_KEY = invoice_key
    subscription_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    subscription_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    sub_admin_config = AdminConfig()
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
