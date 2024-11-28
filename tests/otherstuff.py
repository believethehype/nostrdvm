import json
import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import LogLevel, init_logger

from nostr_dvm.bot import Bot
from nostr_dvm.tasks.convert_media import MediaConverter
from nostr_dvm.tasks.discovery_bot_farms import DiscoveryBotFarms
from nostr_dvm.tasks.discovery_censor_wot import DiscoverReports
from nostr_dvm.tasks.discovery_inactive_follows import DiscoverInactiveFollows
from nostr_dvm.tasks.imagegeneration_openai_dalle import ImageGenerationDALLE
from nostr_dvm.tasks.imagegeneration_replicate import ImageGenerationReplicate
from nostr_dvm.tasks.imagegeneration_replicate_fluxpro import ImageGenerationReplicateFluxPro
from nostr_dvm.tasks.imagegeneration_replicate_recraft import ImageGenerationReplicateRecraft
from nostr_dvm.tasks.imagegeneration_sd35_api import ImageGenerationSD35
from nostr_dvm.tasks.videogeneration_replicate_svd import VideoGenerationReplicateSVD
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST
from nostr_dvm.utils.zap_utils import get_price_per_sat

# Some other DVMs to run.

use_logger = True
log_level = LogLevel.ERROR


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

def build_sd35(name, identifier, announce):
    dvm_config = build_default_config(identifier)

    dvm_config.NEW_USER_BALANCE = 0
    dvm_config.USE_OWN_VENV = False
    dvm_config.ENABLE_NUTZAP = False
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    profit_in_sats = 10
    dvm_config.FIX_COST = int(((4.0 / (get_price_per_sat("USD") * 100)) + profit_in_sats))
    nip89info = {
        "name": name,
        "picture": "https://i.nostr.build/NOXcCIPmOZrDTK35.jpg",
        "about": "I draw images using Stable diffusion ultra",
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "nip90Params": {
            "negative_prompt": {
                "required": False,
                "values": []
            },
            "ratio": {
                "required": False,
                "values": ["1:1", "5:4", "3:2", "16:9","21:9", "9:21", "9:16", "2:3", "4:5"]
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                           nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)
    aconfig = AdminConfig()
    aconfig.REBROADCAST_NIP89 = announce  # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    aconfig.REBROADCAST_NIP65_RELAY_LIST = announce
    aconfig.LUD16 = dvm_config.LN_ADDRESS
    aconfig.PRIVKEY = dvm_config.PRIVATE_KEY
    aconfig.MELT_ON_STARTUP = False # set this to true to melt cashu tokens to our ln address on startup


    options= {"API_KEY": os.getenv("STABILITY_KEY")}


    return ImageGenerationSD35(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=aconfig, options=options)

def build_dalle(name, identifier, announce):
    dvm_config = build_default_config(identifier)
    admin_config = AdminConfig()
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    dvm_config.NEW_USER_BALANCE = 0
    dvm_config.USE_OWN_VENV = False
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    profit_in_sats = 10
    dvm_config.FIX_COST = int(((4.0 / (get_price_per_sat("USD") * 100)) + profit_in_sats))


    nip89info = {
        "name": name,
        "picture": "https://image.nostr.build/22f2267ca9d4ee9d5e8a0c7818a9fa325bbbcdac5573a60a2d163e699bb69923.jpg",
        "about": "I create Images bridging OpenAI's DALL·E 3",
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "nip90Params": {
            "size": {
                "required": False,
                "values": ["1024:1024", "1024x1792", "1792x1024"]
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                                              nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    return ImageGenerationDALLE(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=admin_config)

def build_svd(name, identifier, announce):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    admin_config = AdminConfig()
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    profit_in_sats = 10
    cost_in_cent = 4.0
    dvm_config.FIX_COST = int(((cost_in_cent / (get_price_per_sat("USD") * 100)) + profit_in_sats))

    nip89info = {
        "name": name,
        "picture": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I use Stable Video Diffusion to create short videos",
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "nip90Params": {}
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                           nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)
    # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    return VideoGenerationReplicateSVD(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                       admin_config=admin_config)


def build_media_converter(name, identifier, announce):
    dvm_config = build_default_config(identifier)
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    admin_config = AdminConfig()
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    nip89info = {
    "name": name,
    "picture": "https://cdn.nostr.build/i/a177be1159da5aad8396a1188f686728d55647d3a7371549584daf2b5e50eec9.jpg",
        "about": "I convert videos from urls to given output format.",
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "nip90Params": {
            "media_format": {
                "required": False,
                "values": ["video/mp4", "audio/mp3"]
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)
    return MediaConverter(name=name, dvm_config=dvm_config, nip89config=nip89config,
                          admin_config=admin_config)


def build_inactive_follows_finder(name, identifier, announce):
    dvm_config = build_default_config(identifier)
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    admin_config = AdminConfig()
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    dvm_config.USE_OWN_VENV = False
    dvm_config.FIX_COST = 0

    # Add NIP89
    nip89info = {
        "name": name,
        "picture": "https://image.nostr.build/50621bbf8082c478bc06a06684e1c443b5d37f1362ad56d679cab7328e0481db.jpg",
        "about": "I discover npubs you follow, but that have been inactive on Nostr for the last 90 days",
        "action": "unfollow",
        "acceptsNutZaps": False,
        "nip90Params": {
            "user": {
                "required": False,
                "values": [],
                "description": "Do the task for another user"
            },
            "since_days": {
                "required": False,
                "values": [],
                "description": "The number of days a user has not been active to be considered inactive"

                }
    }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                                              nip89info["picture"])

    nip89config.CONTENT = json.dumps(nip89info)
    return DiscoverInactiveFollows(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                   admin_config=admin_config)

def build_1984(name, identifier, announce):
    dvm_config = build_default_config(identifier)
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.USE_OWN_VENV = False
    admin_config = AdminConfig()
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    # Add NIP89
    nip89info = {
        "name": name,
        "picture": "https://image.nostr.build/19872a2edd866258fa9eab137631efda89310d52b2c6ea8f99ef057325aa1c7b.jpg",
        "about": "I show users that have been reported by either your followers or your Web of Trust. Note: Anyone can report, so you might double check and decide for yourself who to mute. Considers spam, illegal and impersonation reports. Notice: This works with NIP51 mute lists. Not all clients support the new mute list format.",
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "action": "mute",  # follow, unfollow, mute, unmute
        "nip90Params": {
            "since_days": {
                "required": False,
                "values": [],
                "description": "The number of days a report is ago in order to be considered "
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    return DiscoverReports(name=name, dvm_config=dvm_config, nip89config=nip89config,
                           admin_config=admin_config)

def build_botfarms(name, identifier, announce):
    dvm_config = build_default_config(identifier)
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.USE_OWN_VENV = False
    dvm_config.UPDATE_DATABASE = False
    dvm_config.SCHEDULE_UPDATES_SECONDS = 600  # Every 10 seconds
    admin_config = AdminConfig()
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    # Add NIP89
    nip89info = {
        "name": name,
        "picture": "https://image.nostr.build/981b560820bc283c58de7989b7abc6664996b487a531d852e4ef7322586a2122.jpg",
        "about": "I hunt down bot farms.",
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "action": "mute",  # follow, unfollow, mute, unmute
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 20)"
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    options = {"relay": "wss://relay.damus.io"}

    return DiscoveryBotFarms(name=name, dvm_config=dvm_config, nip89config=nip89config,
                             admin_config=admin_config, options=options)

def build_replicate(name, identifier, model,  announce):
    dvm_config = build_default_config(identifier)
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    admin_config = AdminConfig()
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce

    profit_in_sats = 10
    dvm_config.FIX_COST = int(((4.0 / (get_price_per_sat("USD") * 100)) + profit_in_sats))

    nip89info = {
        "name": name,
        "picture": "https://i.nostr.build/qnoBIN4jSkfF8IHk.png",
        "about": "I use Replicate to run StableDiffusion XL",
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "nip90Params": {
            "size": {
                "required": False,
                "values": ["1024:1024", "1024x1792", "1792x1024"]
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)

    opts = {"model": model}

    return ImageGenerationReplicate(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                        admin_config=admin_config, options=opts)


def build_replicate_recraft(name, identifier,  announce):
    dvm_config = build_default_config(identifier)
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    admin_config = AdminConfig()
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce

    profit_in_sats = 10
    dvm_config.FIX_COST = int(((4.0 / (get_price_per_sat("USD") * 100)) + profit_in_sats))

    nip89info = {
        "name": name,
        "picture": "https://i.nostr.build/jSbrXvYglXCzSeAc.jpg",
        "about": "I use Replicate to run Recraft v3",
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "nip90Params": {
            "size": {
                "required": False,
                "values": ["1024:1024"]
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)


    return ImageGenerationReplicateRecraft(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                        admin_config=admin_config)

def build_replicate_fluxpro(name, identifier, announce):
    dvm_config = build_default_config(identifier)
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    admin_config = AdminConfig()
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce

    profit_in_sats = 10
    dvm_config.FIX_COST = int(((4.0 / (get_price_per_sat("USD") * 100)) + profit_in_sats))

    nip89info = {
        "name": name,
        "picture": "https://i.nostr.build/AQTujqzVmLxLmG16.jpg",
        "about": "I use Replicate to FluxPro 1.1.",
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "nip90Params": {
            "size": {
                "required": False,
                "values": ["5:4"]
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)


    return ImageGenerationReplicateFluxPro(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                        admin_config=admin_config)


def playground(announce=False):
    #bot_config = DVMConfig()
    bot_config = build_default_config("bot")
    bot_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    bot_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    bot_config.RELAY_LIST = RELAY_LIST
    #bot_config.PRIVATE_KEY = check_and_set_private_key("bot")
    #npub = Keys.parse(bot_config.PRIVATE_KEY).public_key().to_bech32()
    #invoice_key, admin_key, wallet_id, lnaddress = check_and_set_ln_bits_keys("bot",npub)
    #bot_config.LNBITS_INVOICE_KEY = invoice_key
    #bot_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back bot_config.LNBITS_URL = os.getenv("LNBITS_HOST")

    if os.getenv("OPENAI_API_KEY") is not None and os.getenv("OPENAI_API_KEY") != "":
        dalle = build_dalle("Dall-E 3", "dalle3", announce)
        bot_config.SUPPORTED_DVMS.append(dalle)
        dalle.run()
    if os.getenv("STABILITY_KEY") is not None and os.getenv("STABILITY_KEY") != "":
        sd35 = build_sd35("Stable Diffusion Ultra", "sd35", announce)
        sd35.run()

    if os.getenv("REPLICATE_API_TOKEN") is not None and os.getenv("REPLICATE_API_TOKEN") != "":
        model = "stability-ai/stable-diffusion-3.5-large"
        sd3replicate = build_replicate("Stable Diffusion 3.5 Large", "replicate_svd", model, announce)
        bot_config.SUPPORTED_DVMS.append(sd3replicate)
        sd3replicate.run()

        model = "black-forest-labs/flux-1.1-pro"
        fluxreplicate = build_replicate_fluxpro("Flux 1.1. Pro", "fluxpro", announce)
        bot_config.SUPPORTED_DVMS.append(fluxreplicate)
        fluxreplicate.run()

        recraftreplicate = build_replicate_recraft("Recraft v3", "recraftsvg", announce)
        bot_config.SUPPORTED_DVMS.append(recraftreplicate)
        recraftreplicate.run()


    media_bringer = build_media_converter("Nostr AI DVM Media Converter", "media_converter", announce)
    #bot_config.SUPPORTED_DVMS.append(media_bringer)
    media_bringer.run()


    discover_inactive = build_inactive_follows_finder("Those who left", "discovery_inactive_follows", announce)
    bot_config.SUPPORTED_DVMS.append(discover_inactive)
    discover_inactive.run()


    discovery_censor = build_1984("Censorship 1984", "discovery_censor", announce)
    #bot_config.SUPPORTED_DVMS.append(discovery_censor)
    discovery_censor.run()



    discovery_bots = build_botfarms("Bot Hunter", "discovery_botfarms", announce)
    #bot_config.SUPPORTED_DVMS.append(discovery_bots)
    discovery_bots.run()


    admin_config = AdminConfig()
    #admin_config.REBROADCAST_NIP65_RELAY_LIST = True
    x = threading.Thread(target=Bot, args=([bot_config, admin_config]))
    x.start()


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
    announce = False
    playground(announce)

