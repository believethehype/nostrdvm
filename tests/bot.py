import asyncio
import json
import os
import threading
from pathlib import Path

import dotenv
from nostr_sdk import Keys

from nostr_dvm.bot import Bot
from nostr_dvm.tasks import textextraction_pdf, convert_media, discovery_inactive_follows, translation_google
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.backend_utils import keep_alive
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.external_dvm_utils import build_external_dvm
from nostr_dvm.utils.nip89_utils import NIP89Config
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.output_utils import PostProcessFunctionType
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys


def playground():
    bot_config = DVMConfig()
    identifier = "bot_test"
    bot_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    npub = Keys.parse(bot_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, user_id, lnaddress = check_and_set_ln_bits_keys(identifier, npub)
    bot_config.LN_ADDRESS = lnaddress
    bot_config.LNBITS_INVOICE_KEY = invoice_key
    bot_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    bot_config.LNBITS_URL = os.getenv("LNBITS_HOST")


    admin_config = AdminConfig()

    pdfextractor = textextraction_pdf.build_example("PDF Extractor", "pdf_extractor", admin_config)
    # If we don't add it to the bot, the bot will not provide access to the DVM
    pdfextractor.run()
    bot_config.SUPPORTED_DVMS.append(pdfextractor)  # We add translator to the bot

    ymhm_external = build_external_dvm(pubkey="58c52fdca7593dffea63ba6f758779d8251c6732f54e9dc0e56d7a1afe1bb1b6",
                                       task="wot-discovery",
                                       kind=EventDefinitions.KIND_NIP90_PEOPLE_DISCOVERY,
                                       fix_cost=0, per_unit_cost=0, config=bot_config,
                                       external_post_process=PostProcessFunctionType.NONE)

    bot_config.SUPPORTED_DVMS.append(ymhm_external)

    admin_config_media = AdminConfig()
    admin_config_media.UPDATE_PROFILE = True
    admin_config_media.REBROADCAST_NIP65_RELAY_LIST = True
    media_bringer = convert_media.build_example("Nostr AI DVM Media Converter",
                                          "media_converter", admin_config_media)
    bot_config.SUPPORTED_DVMS.append(media_bringer)
    media_bringer.run()


    admin_config_followers = AdminConfig()
    admin_config_followers.UPDATE_PROFILE = True
    admin_config_followers.REBROADCAST_NIP65_RELAY_LIST = True
    discover_inactive = discovery_inactive_follows.build_example("Those who left",
                                                      "discovery_inactive_follows", admin_config_followers)
    bot_config.SUPPORTED_DVMS.append(discover_inactive)
    discover_inactive.run()

    admin_config_google = AdminConfig()
    admin_config_google.UPDATE_PROFILE = True
    admin_config_google.REBROADCAST_NIP65_RELAY_LIST = True

    translator = translation_google.build_example("NostrAI DVM Translator", "google_translator", admin_config_google)
    bot_config.SUPPORTED_DVMS.append(translator)  # We add translator to the bot
    translator.run()

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP65_RELAY_LIST = True
    admin_config.UPDATE_PROFILE = True
    x = threading.Thread(target=Bot, args=([bot_config, admin_config]))
    x.start()

    # Keep the main function alive for libraries that require it, like openai
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