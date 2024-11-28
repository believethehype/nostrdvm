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
                      #"wss://relay.primal.net",
                      "wss://nostr.oxtr.dev"]

RELAY_LIST = ["wss://nostr.mom",
              #"wss://relay.primal.net",
              "wss://nostr.oxtr.dev",
              #"wss://relay.nostr.net"
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


def build_example_gallery(name, identifier, admin_config, options, image, cost=0, update_rate=180, processing_msg=None,
                          update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.LOGLEVEL = LogLevel.INFO
    # dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SEND_FEEDBACK_EVENTS = False
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show popular gallery entries",
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
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
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)
    return DicoverContentCurrentlyPopularGallery(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                 admin_config=admin_config, options=options)


def build_example_nostrband(name, identifier, admin_config, image, about, custom_processing_msg):
    dvm_config: DVMConfig = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.CUSTOM_PROCESSING_MESSAGE = custom_processing_msg
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.LOGLEVEL = LogLevel.INFO
    dvm_config.SEND_FEEDBACK_EVENTS = False
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    # Add NIP89

    nip89info = {
        "name": name,
        "picture": image,
        "about": about,
        "amount": "Free",
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "nip90Params": {}
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    return TrendingNotesNostrBand(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                  admin_config=admin_config)


def build_longform(name, identifier, admin_config, options, cost=0, update_rate=180, processing_msg=None,
                   update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SEND_FEEDBACK_EVENTS = False
    dvm_config.LOGLEVEL = LogLevel.INFO
    # Activate these to use a subscription based model instead
    # dvm_config.SUBSCRIPTION_REQUIRED = True
    # dvm_config.SUBSCRIPTION_DAILY_COST = 1
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    image = "https://image.nostr.build/d30a75c438a8b0815b5c65b494988da26fce719f4138058929fa52d2a2dc3433.jpg"

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show the latest longform notes.",
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

    # admin_config.UPDATE_PROFILE = False

    # admin_config.REBROADCAST_NIP89 = False

    return DicoverContentLatestLongForm(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                        admin_config=admin_config, options=options)


def build_wiki(name, identifier, admin_config, options, cost=0, update_rate=180, processing_msg=None,
               update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.LOGLEVEL = LogLevel.INFO
    # Activate these to use a subscription based model instead
    # dvm_config.SUBSCRIPTION_REQUIRED = True
    # dvm_config.SUBSCRIPTION_DAILY_COST = 1
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    dvm_config.SEND_FEEDBACK_EVENTS = False
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    image = "https://i.nostr.build/ctfc5o47ICm56TOv.jpg"

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show the latest wikifreedia entries.",
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

    # admin_config.UPDATE_PROFILE = False

    # admin_config.REBROADCAST_NIP89 = False

    return DicoverContentLatestWiki(name=name, dvm_config=dvm_config, nip89config=nip89config,
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


def build_example_popular(name, identifier, admin_config, options, image, cost=0, update_rate=180, processing_msg=None,
                          update_db=True, database=None):
    dvm_config = build_default_config(identifier)
    dvm_config.LOGLEVEL = LogLevel.INFO
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
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
        "about": "I show notes that are currently popular",
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
    return DicoverContentCurrentlyPopular(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                          admin_config=admin_config, options=options)


def build_example_popular_followers(name, identifier, admin_config, options, image, cost=0, update_rate=300,
                                    processing_msg=None, update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.LOGLEVEL = LogLevel.INFO
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every x seconds
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    admin_config.LUD16 = dvm_config.LN_ADDRESS



    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show notes that are currently popular from people you follow",
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
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
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    return DicoverContentCurrentlyPopularFollowers(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                   options=options,
                                                   admin_config=admin_config)


def build_example_popular_non_followers(name, identifier, admin_config, options, image, cost=0, update_rate=300,
                                        processing_msg=None, update_db=True, database=None):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.LOGLEVEL = LogLevel.INFO
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.DATABASE = database
    # Activate these to use a subscription based model instead
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SUBSCRIPTION_REQUIRED = False
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP88 = False
    # admin_config.REBROADCAST_NIP89 = True
    admin_config.UPDATE_PROFILE = False

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show notes that are currently popular from people you do not follow",
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "subscription": False,
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
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    nip88config = NIP88Config()
    nip88config.DTAG = check_and_set_d_tag_nip88(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip88config.TIER_EVENT = check_and_set_tiereventid_nip88(identifier, "1")
    nip89config.NAME = name
    nip88config.IMAGE = nip89info["picture"]
    nip88config.TITLE = name
    nip88config.AMOUNT_DAILY = 100
    nip88config.AMOUNT_MONTHLY = 2000
    nip88config.CONTENT = "Subscribe to the DVM for unlimited use during your subscription"
    nip88config.PERK1DESC = "Unlimited requests"
    nip88config.PERK2DESC = "Support NostrDVM & NostrSDK development"
    nip88config.PAYMENT_VERIFIER_PUBKEY = "5b5c045ecdf66fb540bdf2049fe0ef7f1a566fa427a4fe50d400a011b65a3a7e"

    # admin_config.FETCH_NIP88 = True
    # admin_config.EVENTID = "63a791cdc7bf78c14031616963105fce5793f532bb231687665b14fb6d805fdb"
    admin_config.PRIVKEY = dvm_config.PRIVATE_KEY

    return DicoverContentCurrentlyPopularNonFollowers(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                      # nip88config=nip88config,
                                                      admin_config=admin_config,
                                                      options=options)


def build_example_top_zapped(name, identifier, admin_config, options, image, cost=0, update_rate=180,
                             processing_msg=None,
                             update_db=True, database=None):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    # dvm_config.ENABLE_NUTZAP = True
    dvm_config.LOGLEVEL = LogLevel.INFO
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
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
        "about": "I show notes that are currently zapped the most.",
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

    # admin_config.UPDATE_PROFILE = False
    # admin_config.REBROADCAST_NIP89 = False

    return DicoverContentCurrentlyPopularZaps(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                              admin_config=admin_config, options=options)


def build_example_mostr(name, identifier, admin_config, options, image, cost=0, update_rate=180, processing_msg=None,
                        update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.LOGLEVEL = LogLevel.INFO
    # dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = ["wss://nfrelay.app/?user=activitypub"]
    dvm_config.SEND_FEEDBACK_EVENTS = False
    # dvm_config.SYNC_DB_RELAY_LIST = ["wss://relay.mostr.pub/"]

    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show notes from Mostr.pub and Momostr.pink that are currently popular on Nostr",
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
    return DicoverContentCurrentlyPopularMostr(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                               admin_config=admin_config, options=options)


def build_example_oneperfollow(name, identifier, admin_config, options, image, cost=0, update_rate=180,
                               processing_msg=None,
                               update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.LOGLEVEL = LogLevel.INFO
    # dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = False
    dvm_config.FIX_COST = cost
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show the single latest note of people you follow",
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
    return Discoverlatestperfollower(name=name, dvm_config=dvm_config, nip89config=nip89config,
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

    admin_config_gallery = AdminConfig()
    admin_config_gallery.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_gallery.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_gallery.UPDATE_PROFILE = update_profile
    # admin_config_global_popular.DELETE_NIP89 = True
    # admin_config_global_popular.PRIVKEY = ""
    # admin_config_global_popular.EVENTID = "2fea4ee2ccf0fa11db171113ffd7a676f800f34121478b7c9a4e73c2f1990028"
    # admin_config_global_popular.POW = True
    custom_processing_msg = ["Looking for popular Gallery entries"]
    update_db = True

    options_gallery = {
        "db_name": "db/nostr_gallery.db",
        "generic_db_name": "db/nostr_recent_notes.db",
        "db_since": 60 * 60 * 24 * 30,  # 1h since gmt,
    }

    # cost = 0
    # image = "https://i.nostr.build/4Rw6lrsH5O0P5zjT.jpg"
    # discover_gallery = build_example_gallery("Gallery entries",
    #                                   "discovery_gallery_entries",
    #                                   admin_config=admin_config_gallery,
    #                                   options=options_gallery,
    #                                   image=image,
    #                                   cost=cost,
    #                                   update_rate=global_update_rate,
    #                                   processing_msg=custom_processing_msg,
    #                                   update_db=update_db)
    # discover_gallery.run()
    #

    # Latest Longform
    admin_config_longform = AdminConfig()
    admin_config_longform.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_longform.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_longform.UPDATE_PROFILE = update_profile
    # admin_config_top_zaps.DELETE_NIP89 = True
    # admin_config_top_zaps.PRIVKEY = ""
    # admin_config_top_zaps.EVENTID = "05a6de88e15aa6c8b4c8ec54481f885f397a30761ff2799958e5c5ee9ad6917b"
    # admin_config_top_zaps.POW = True
    custom_processing_msg = ["Looking for latest Longform Articles", "Let's see what people recently wrote"]
    update_db = True

    options_longform = {
        "db_name": "db/nostr_recent_notes_longform.db",
        "db_since": 60 * 60 * 24 * 21,  # 3 Weeks since gmt,
    }
    cost = 0
    latest_longform = build_longform("Latest Longform Notes",
                                     "discovery_content_longform",
                                     admin_config=admin_config_longform,
                                     options=options_longform,
                                     cost=cost,
                                     update_rate=global_update_rate,
                                     processing_msg=custom_processing_msg,
                                     update_db=update_db)

    latest_longform.run()

    # Latest Wiki
    admin_config_wiki = AdminConfig()
    admin_config_wiki.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_wiki.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_wiki.UPDATE_PROFILE = update_profile
    # admin_config_top_zaps.DELETE_NIP89 = True
    # admin_config_top_zaps.PRIVKEY = ""
    # admin_config_top_zaps.EVENTID = "05a6de88e15aa6c8b4c8ec54481f885f397a30761ff2799958e5c5ee9ad6917b"
    # admin_config_top_zaps.POW = True
    custom_processing_msg = ["Looking for latest Wiki entries", "Let's check Wiki entries.."]
    update_db = True

    options_longform = {
        "db_name": "db/nostr_recent_notes_longform.db",
        "db_since": 60 * 60 * 24 * 21,  # 3 Weeks since gmt,
    }
    cost = 0
    latest_wiki = build_wiki("Latest Wikifreedia Notes",
                             "discovery_content_wiki",
                             admin_config=admin_config_wiki,
                             options=options_longform,
                             cost=cost,
                             update_rate=global_update_rate,
                             processing_msg=custom_processing_msg,
                             update_db=update_db)

    latest_wiki.run()

    # Popular top zapped
    admin_config_top_zaps = AdminConfig()
    admin_config_top_zaps.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_top_zaps.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_top_zaps.UPDATE_PROFILE = update_profile
    # admin_config_top_zaps.DELETE_NIP89 = True
    # admin_config_top_zaps.PRIVKEY = ""
    # admin_config_top_zaps.EVENTID = "05a6de88e15aa6c8b4c8ec54481f885f397a30761ff2799958e5c5ee9ad6917b"
    # admin_config_top_zaps.POW = True
    custom_processing_msg = ["Looking for most zapped notes", "Let's see which notes people currently zap..",
                             "Let's find valuable notes. #value4value"]
    update_db = False

    options_top_zapped = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 60 * 60 * 2,  # 8h since gmt,
    }
    cost = 0
    # image = "https://image.nostr.build/c6879f458252641d04d0aa65fd7f1e005a4f7362fd407467306edc2f4acdb113.jpg"
    image = "https://i.nostr.build/U5AO3vUMy47NWSQG.png"
    discovery_topzaps = build_example_top_zapped("Top Zapped notes",
                                                 "discovery_content_top_zaps",
                                                 admin_config=admin_config_top_zaps,
                                                 options=options_top_zapped,
                                                 image=image,
                                                 cost=cost,
                                                 update_rate=global_update_rate,
                                                 processing_msg=custom_processing_msg,
                                                 update_db=update_db,
                                                 database=DATABASE)

    discovery_topzaps.run()

    # Popular NOSTR.band
    admin_config_trending_nostr_band = AdminConfig()
    admin_config_trending_nostr_band.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_trending_nostr_band.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_trending_nostr_band.UPDATE_PROFILE = update_profile
    # admin_config_trending_nostr_band.DELETE_NIP89 = True
    # admin_config_trending_nostr_band.PRIVKEY = ""
    # admin_config_trending_nostr_band.EVENTID = "e7a7aaa7113f17af94ccbfe86c06e04c27ffce3d2f654d613ce249b68414bdae"
    # admin_config_trending_nostr_band.POW = True
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

    admin_config_mostr = AdminConfig()
    admin_config_mostr.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_mostr.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_mostr.UPDATE_PROFILE = update_profile
    # admin_config_mostr.DELETE_NIP89 = True
    # admin_config_mostr.PRIVKEY = ""
    # admin_config_mostr.EVENTID = "59d0ebe2966426ac359dcb8da214efe34fb735c69099361eae87a426bacf4de2"
    # admin_config_mostr.POW = True
    custom_processing_msg = ["Looking for popular Content on Mostr"]

    options_mostr = {
        "db_name": "db/nostr_mostr.db",
        "db_since": 60 * 60 * 2,  # 1h since gmt,
    }
    cost = 0
    image = "https://i.nostr.build/mtkNd3J8m0mqj9nq.jpg"
    # discovery_mostr = build_example_mostr("Trending on Mostr",
    #                                      "discovery_mostr",
    #
    #                                      admin_config=admin_config_mostr,
    #                                      options=options_mostr,
    #                                      image=image,
    #                                      cost=cost,
    #                                      update_rate=180,
    #                                      processing_msg=custom_processing_msg,
    #                                      update_db=True)
    # discovery_mostr.run()

    # Popular Garden&Plants
    admin_config_asknostr = AdminConfig()
    admin_config_asknostr.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_asknostr.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_asknostr.UPDATE_PROFILE = update_profile
    options_plants = {
        "search_list": ["#asknostr"],
        "avoid_list": [],
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 24 * 60 * 60,  # 12h since gmt
        "personalized": False,
        "logger": False}

    image = "https://i.nostr.build/vIixmuRacIhULsrP.png"
    description = "I show popular questions #asknostr"
    custom_processing_msg = ["Finding the best notes for you.. #asknostr"]
    update_db = False
    cost = 0
    discovery_asknostr = build_example_topic("Popular on #asknostr", "discovery_content_asknostr",
                                             admin_config_asknostr, options_plants,
                                             image=image,
                                             description=description,
                                             update_rate=global_update_rate,
                                             cost=cost,
                                             processing_msg=custom_processing_msg,
                                             update_db=update_db,
                                             database=DATABASE)
    discovery_asknostr.run()

    # Popular Garden&Plants
    admin_config_mining = AdminConfig()
    admin_config_mining.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_mining.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_mining.UPDATE_PROFILE = update_profile
    # admin_config_plants.DELETE_NIP89 = True
    # admin_config_plants.PRIVKEY = ""
    # admin_config_plants.EVENTID = "ff28be59708ee597c7010fd43a7e649e1ab51da491266ca82a84177e0007e4d6"
    # admin_config_plants.POW = True
    options_mining = {
        "search_list": ["bitaxe", "homeminer", " S9 ", "homemining"],
        "avoid_list": ["nsfw"],
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 12 * 60 * 60,  # 12h since gmt
        "personalized": False,
        "logger": False}

    image = "https://i.nostr.build/M6w0qSpRTGHwjYwf.jpg"
    description = "I show recent notes about Bitcoin home mining."
    custom_processing_msg = ["Finding the best notes for you.. #homeminer"]
    update_db = False
    cost = 0
    discovery_mining = build_example_topic("Home mining", "discovery_content_mining",
                                           admin_config_mining, options_mining,
                                           image=image,
                                           description=description,
                                           update_rate=global_update_rate,
                                           cost=cost,
                                           processing_msg=custom_processing_msg,
                                           update_db=update_db,
                                           database=DATABASE)
    discovery_mining.run()

    # Popular Animals (Fluffy frens)
    admin_config_animals = AdminConfig()
    admin_config_animals.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_animals.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_animals.UPDATE_PROFILE = update_profile
    # admin_config_animals.DELETE_NIP89 = True
    # admin_config_animals.PRIVKEY = ""
    # admin_config_animals.EVENTID = "79c613b5f0e71718628bd0c782a5b6b495dac491f36c326ccf416ada80fd8fdc"
    # admin_config_animals.POW = True

    options_animal = {
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
    update_db = False  # As this is our largerst DB we update it here, and the other dvms use it. TODO make an own scheduler that only updates the db
    discovery_animals = build_example_topic("Fluffy Frens",
                                            "discovery_content_fluffy",
                                            admin_config_animals, options_animal,
                                            image=image,
                                            description=description,
                                            update_rate=global_update_rate,
                                            cost=cost,
                                            processing_msg=custom_processing_msg,
                                            update_db=update_db,
                                            database=DATABASE)

    discovery_animals.run()

    # Popular Garden&Plants
    admin_config_plants = AdminConfig()
    admin_config_plants.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_plants.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_plants.UPDATE_PROFILE = update_profile
    # admin_config_plants.DELETE_NIP89 = True
    # admin_config_plants.PRIVKEY = ""
    # admin_config_plants.EVENTID = "ff28be59708ee597c7010fd43a7e649e1ab51da491266ca82a84177e0007e4d6"
    # admin_config_plants.POW = True
    options_plants = {
        "search_list": ["garden", "gardening", "nature", " plants ", " plant ", " herb ", " herbs " " pine ",
                        "homesteading", "rosemary", "chicken", "🪻", "🌿", "☘️", "🌲", "flower", "forest", "watering",
                        "permies", "planting", "farm", "vegetable", "fruit", " grass ", "sunshine",
                        "#flowerstr", "#bloomscrolling", "#treestr", "#plantstr", "touchgrass", ],
        "avoid_list": ["porn", "smoke", "nsfw", "bitcoin", "bolt12", "bolt11", "github", "currency", "utxo",
                       "encryption", "government", "airpod", "ipad", "iphone", "android", "warren",
                       "moderna", "pfizer", "corona", "socialism", "critical theory", "law of nature"
                                                                                      "murder", "tax", "engagement",
                       "hodlers", "hodl", "gdp", "global markets", "crypto", "wherostr",
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
    discovery_garden = build_example_topic("Garden & Growth", "discovery_content_garden",
                                           admin_config_plants, options_plants,
                                           image=image,
                                           description=description,
                                           update_rate=global_update_rate,
                                           cost=cost,
                                           processing_msg=custom_processing_msg,
                                           update_db=update_db,
                                           database=DATABASE)
    discovery_garden.run()

    # Popular Followers
    admin_config_followers = AdminConfig()
    admin_config_followers.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_followers.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_followers.UPDATE_PROFILE = update_profile
    # admin_config_followers.DELETE_NIP89 = True
    # admin_config_followers.PRIVKEY = ""
    # admin_config_followers.EVENTID = "590cd7b2902224f740acbd6845023a5ab4a959386184f3360c2859019cfd48fa"
    # admin_config_followers.POW = True
    custom_processing_msg = ["Processing popular notes from npubs you follow..",
                             "Let's see what npubs you follow have been up to..",
                             "Processing a personalized feed, just for you.."]
    update_db = False
    options_followers_popular = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 2 * 60 * 60,  # 2h since gmt,
    }

    cost = 0
    # image = "https://image.nostr.build/d92652a6a07677e051d647dcf9f0f59e265299b3335a939d008183a911513f4a.jpg"
    image = "https://i.nostr.build/ZJqko0W9ApEVZAPt.png"
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

    # Popular Followers
    admin_config_nonfollowers = AdminConfig()
    admin_config_nonfollowers.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_nonfollowers.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_nonfollowers.UPDATE_PROFILE = update_profile
    # admin_config_followers.DELETE_NIP89 = True
    # admin_config_followers.PRIVKEY = ""
    # admin_config_followers.EVENTID = "590cd7b2902224f740acbd6845023a5ab4a959386184f3360c2859019cfd48fa"
    # admin_config_followers.POW = True
    custom_processing_msg = ["Processing popular notes from npubs you don't follow..",
                             "Let's see what npubs outside of your circle have been up to..",
                             "Processing a personalized feed, just for you.."]
    update_db = False
    options_nonfollowers_popular = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 2 * 60 * 60,  # 2h since gmt,
    }
    cost = 10
    image = "https://i.nostr.build/l11EczDmpZBaxlRm.jpg"

    discovery_non_followers = build_example_popular_non_followers(
        "Popular from npubs you don't follow",
        "discovery_content_nonfollowers",
        admin_config=admin_config_nonfollowers,
        options=options_nonfollowers_popular,
        cost=cost,
        image=image,
        update_rate=global_update_rate,
        processing_msg=custom_processing_msg,
        update_db=update_db,
        database=DATABASE)
    discovery_non_followers.run()

    admin_config_opf = AdminConfig()
    admin_config_opf.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_opf.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_opf.UPDATE_PROFILE = update_profile
    # admin_config_opf.DELETE_NIP89 = True
    # admin_config_opf.PRIVKEY = ""
    # admin_config_opf.EVENTID = ""
    # admin_config_opf.POW = True
    custom_processing_msg = ["Looking for latest content by people you follow.."]
    update_db = True

    options_opf = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 60 * 60 * 2,  # 1h since gmt,
    }
    cost = 0
    # image = "https://i.nostr.build/H6SMmCl7eRDvkbAn.jpg"
    image = "https://i.nostr.build/fsGWicUhyRrfy85d.jpg"
    discovery_one_per_follow = build_example_oneperfollow("One per follow",
                                                          "discovery_latest_per_follow",
                                                          admin_config=admin_config_opf,
                                                          options=options_opf,
                                                          image=image,
                                                          cost=cost,
                                                          update_rate=global_update_rate,
                                                          processing_msg=custom_processing_msg,
                                                          update_db=update_db)
    discovery_one_per_follow.run()

    # Popular Global
    admin_config_global_popular = AdminConfig()
    admin_config_global_popular.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config_global_popular.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config_global_popular.UPDATE_PROFILE = update_profile
    # admin_config_global_popular.DELETE_NIP89 = True
    # admin_config_global_popular.PRIVKEY = ""
    # admin_config_global_popular.EVENTID = "2fea4ee2ccf0fa11db171113ffd7a676f800f34121478b7c9a4e73c2f1990028"
    # admin_config_global_popular.POW = True
    custom_processing_msg = ["Looking for popular notes on the Nostr..", "Let's see what's trending on Nostr..",
                             "Finding the best notes on the Nostr.."]
    update_db = False

    options_global_popular = {
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 60 * 60 * 1,  # 1h since gmt,
    }
    cost = 0
    # image = "https://image.nostr.build/b29b6ec4bf9b6184f69d33cb44862db0d90a2dd9a506532e7ba5698af7d36210.jpg"
    image = "https://i.nostr.build/AnBKrfAIRMhWm0h3.jpg"
    discovery_global = build_example_popular("Currently Popular Notes DVM",
                                             "discovery_content_test",
                                             admin_config=admin_config_global_popular,
                                             options=options_global_popular,
                                             image=image,
                                             cost=cost,
                                             update_rate=global_update_rate,
                                             processing_msg=custom_processing_msg,
                                             update_db=update_db,
                                             database=DATABASE)
    discovery_global.run()

    # discovery_test_sub = content_discovery_currently_popular.build_example_subscription("Currently Popular Notes DVM (with Subscriptions)", "discovery_content_test", admin_config)
    # discovery_test_sub.run()

    admin_config_nostriga = AdminConfig()
    admin_config_nostriga.REBROADCAST_NIP89 = False  # rebroadcast_NIP89
    admin_config_nostriga.REBROADCAST_NIP65_RELAY_LIST = False  # rebroadcast_NIP65_Relay_List
    admin_config_nostriga.UPDATE_PROFILE = update_profile
    admin_config_nostriga.DELETE_NIP89 = True
    # admin_config_nostriga.PRIVKEY = "6221e31813df07037dd90a608fc4cf29222c59da130f76c7f8d0d19c3a876d8e"
    # admin_config_nostriga.EVENTID = "24ac21fb32993744232356bafcabd821e4afed4b18aac8d7e670d1071f6ad77a"
    # admin_config_nostriga.POW = True
    options_nostriga = {
        "search_list": ["nostriga", "#nostriga", "#noobday"],
        "avoid_list": ["porn", "smoke", "nsfw",
                       "encryption", "government", "airpod", "ipad", "iphone", "android", "warren",
                       "moderna", "pfizer", "corona", "socialism", "critical theory", "murder", "tax", "engagement",
                       "gdp", "global markets",
                       "presidency", "dollar", "asset", "microsoft", "amazon", "billionaire", "ceo", "industry",
                       "white house", "summary", "wealth", "beef", "cunt", "nigger", "business",
                       "retail", "bakery", "synth", "slaughterhouse", "hamas", "dog days", "ww3", "socialmedia",
                       "nintendo", "deepfake", "congressman", "cypherpunk", "minister", "dissentwatch",
                       "inkblot", "covid", "robot", "pandemic", "bethesda", "zap farming", " defi ", " minister ",
                       "nostr-hotter-site", "palestine", "https://boards.4chan", "https://techcrunch.com",
                       "https://screenrant.com"],
        "db_name": "db/nostr_recent_notes.db",
        "db_since": 12 * 60 * 60,  # 12h since gmt
        "personalized": False,
        "logger": False}

    image = "https://image.nostr.build/007c8b252f1ea60361082921e1c232260e823c903e7edab092de47ae63bdcf0b.png"
    description = "I'm a temporary DVM and I show notes about Nostriga'"
    custom_processing_msg = ["Finding notes about Nostriga #nostriga", ]
    update_db = False
    cost = 0

    # discovery_nostriga = build_example_topic("Nostriga", "discovery_content_nostriga",
    #                                       admin_config_nostriga, options_nostriga,
    #                                       image=image,
    #                                       description=description,
    #                                       update_rate=global_update_rate,
    #                                       cost=cost,
    #                                       processing_msg=custom_processing_msg,
    #                                       update_db=update_db)
    # discovery_nostriga.run()

    # Subscription Manager DVM
    subscription_config = DVMConfig()
    subscription_config.PRIVATE_KEY = check_and_set_private_key("dvm_subscription")
    npub = Keys.parse(subscription_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, lnaddress = check_and_set_ln_bits_keys("dvm_subscription", npub)
    subscription_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    subscription_config.RELAY_LIST = RELAY_LIST
    subscription_config.LNBITS_INVOICE_KEY = invoice_key
    subscription_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    subscription_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    sub_admin_config = AdminConfig()
    # sub_admin_config.USERNPUBS = ["7782f93c5762538e1f7ccc5af83cd8018a528b9cd965048386ca1b75335f24c6"] #Add npubs of services that can contact the subscription handler

    x = threading.Thread(target=Subscription, args=(Subscription(subscription_config, sub_admin_config),))
    x.start()
    # make sure the last thing joins, either here by calling x.join() or in a call a dvm with .run(True)
    x.join()

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
