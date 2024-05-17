import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import Keys

from nostr_dvm.subscription import Subscription
from nostr_dvm.tasks import content_discovery_currently_popular, content_discovery_currently_popular_topic, \
    discovery_trending_notes_nostrband, content_discovery_currently_popular_followers
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.backend_utils import keep_alive
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys


def playground():
    # Popular NOSTR.band
    admin_config_trending_nostr_band = AdminConfig()
    custom_processing_msg = "Looking for trending notes on nostr.band.."
    trending_nb = discovery_trending_notes_nostrband.build_example("Trending Notes on nostr.band",
                                                                   "trending_notes_nostrband",
                                                                   admin_config_trending_nostr_band,
                                                                   custom_processing_msg)
    trending_nb.run()

    # Popular Garden&Plants
    admin_config_plants = AdminConfig()
    admin_config_plants.REBROADCAST_NIP89 = False
    admin_config_plants.UPDATE_PROFILE = False
    # admin_config_plants.DELETE_NIP89 = True
    # admin_config_plants.PRIVKEY = ""
    # admin_config_plants.EVENTID = ""

    options_plants = {
        "search_list": ["garden", "gardening", "nature", " plants ", " plant ", " herb ", " herbs " " pine ",
                        "homesteading", "rosemary", "chicken", "🪻", "🌿", "☘️", "🌲", "flower", "forest", "watering",
                        "permies", "planting", "farm", "vegetable", "fruit", " grass ", "sunshine",
                        "#flowerstr", "#bloomscrolling", "#treestr", "#plantstr", "touchgrass", ],
        "avoid_list": ["porn", "smoke", "nsfw", "bitcoin", "bolt12", "bolt11", "github", "currency", "utxo",
                       "encryption", "government", "airpod", "ipad", "iphone", "android", "warren",
                       "moderna", "pfizer",
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
                                                                                 description, 180, cost, custom_processing_msg,
                                                                                 update_db)
    discovery_test_sub.run()

    # Popular Animals (Fluffy frens)
    admin_config_animals = AdminConfig()
    admin_config_animals.REBROADCAST_NIP89 = False
    admin_config_animals.UPDATE_PROFILE = False
    options_animal = {
        "search_list": ["catstr", "pawstr", "dogstr", " cat ", " cats ", "🐾", "🐈", "🐕", " dog ", " dogs ", " fluffy ",
                        "animal",
                        " duck", " lion ", " lions ", " fox ", " foxes ", " koala ", " koalas ", "capybara", "squirrel",
                        "monkey", "panda", "alpaca", " otter"],
        "avoid_list": ["porn", "smoke", "nsfw", "bitcoin", "bolt12", "bolt11", "github", "currency", "utxo",
                       "encryption", "government", "airpod", "ipad", "iphone", "android", "warren",
                       "moderna", "pfizer",
                       "murder", "tax", "engagement", "hodlers", "hodl", "gdp", "global markets", "crypto", "wherostr",
                       "presidency", "dollar", "asset", "microsoft", "amazon", "billionaire", "ceo", "industry",
                       "white house", "blocks", "streaming", "summary", "wealth", "beef", "cunt", "nigger", "business",
                       "retail", "bakery", "synth", "slaughterhouse", "hamas", "dog days", "ww3", "socialmedia",
                       "nintendo", "signature", "deepfake", "congressman", "fried chicken", "cypherpunk",
                       "chef", "cooked", "foodstr", "minister", "dissentwatch", "inkblot", "covid", "robot", "pandemic",
                       " dies ", "bethesda", " defi ", " minister ", "nostr-hotter-site", " ai ", "palestine", "animalistic",
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
    update_db = True  #As this is our largerst DB we update it here, and the other dvms use it. TODO make an own scheduler that only updates the db
    discovery_animals = content_discovery_currently_popular_topic.build_example("Fluffy Frens",
                                                                                "discovery_content_fluffy",
                                                                                admin_config_animals, options_animal,
                                                                                image,
                                                                                description,180, cost,   custom_processing_msg,
                                                                                update_db)
    discovery_animals.run()

    # Popular Followers
    admin_config_followers = AdminConfig()
    admin_config_followers.REBROADCAST_NIP89 = False
    admin_config_followers.UPDATE_PROFILE = False
    custom_processing_msg = ["Looking for popular notes from npubs you follow..",
                             "Let's see what npubs you follow have been up to..",
                             "Processing a personalized feed, just for you.."]
    update_db = False
    options_followers_popular = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 2 * 60 * 60,  # 2h since gmt,
    }
    cost = 0

    discovery_followers = content_discovery_currently_popular_followers.build_example(
        "Currently Popular Notes from npubs you follow",
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
    admin_config_global_popular.REBROADCAST_NIP89 = False
    admin_config_global_popular.UPDATE_PROFILE = False
    custom_processing_msg = ["Looking for popular notes on the Nostr..", "Let's see what's trending on Nostr..",
                             "Finding the best notes for you.."]
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
    x = threading.Thread(target=Subscription, args=(Subscription(subscription_config, sub_admin_config),))
    x.start()

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
