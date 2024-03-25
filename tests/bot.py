import json
import os
from pathlib import Path

import dotenv
from nostr_sdk import Keys

from nostr_dvm.bot import Bot
from nostr_dvm.tasks import textextraction_pdf
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.backend_utils import keep_alive
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip89_utils import NIP89Config
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys



def playground():
    bot_config = DVMConfig()
    identifier = "bot_test"
    bot_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    npub = Keys.parse(bot_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, user_id, lnaddress = check_and_set_ln_bits_keys(identifier, npub)
    bot_config.LNBITS_INVOICE_KEY = invoice_key
    bot_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    bot_config.LNBITS_URL = os.getenv("LNBITS_HOST")


    admin_config = AdminConfig()

    pdfextractor = textextraction_pdf.build_example("PDF Extractor", "pdf_extractor", admin_config)
    # If we don't add it to the bot, the bot will not provide access to the DVM
    pdfextractor.run()
    bot_config.SUPPORTED_DVMS.append(pdfextractor)  # We add translator to the bot




    Bot(bot_config, admin_config)
    # Keep the main function alive for libraries that require it, like openai
    keep_alive()


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
