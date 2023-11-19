import os
from pathlib import Path
from threading import Thread

import dotenv
import utils.env as env
from tasks.textextractionPDF import TextExtractionPDF
from tasks.translation import Translation
from utils.definitions import EventDefinitions


def run_nostr_dvm_with_local_config():
    from dvm import dvm, DVMConfig

    PDFextactor = TextExtractionPDF("PDF Extractor", env.NOSTR_PRIVATE_KEY)
    Translator = Translation("Translator", env.NOSTR_PRIVATE_KEY)

    dvmconfig = DVMConfig()
    dvmconfig.PRIVATE_KEY = os.getenv(env.NOSTR_PRIVATE_KEY)
    dvmconfig.SUPPORTED_TASKS = [PDFextactor, Translator]
    dvmconfig.LNBITS_INVOICE_KEY = os.getenv(env.LNBITS_INVOICE_KEY)
    dvmconfig.LNBITS_URL = os.getenv(env.LNBITS_HOST)

    # In admin_utils, set rebroadcast_nip89 to true to (re)broadcast your DVM. You can create a valid dtag and the content on vendata.io
    # Add the dtag in your .env file so you can update your dvm later and change the content in the module file as needed.
    dvmconfig.NIP89s.append(PDFextactor.NIP89_announcement())
    dvmconfig.NIP89s.append(Translator.NIP89_announcement())

    nostr_dvm_thread = Thread(target=dvm, args=[dvmconfig])
    nostr_dvm_thread.start()


if __name__ == '__main__':

    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    run_nostr_dvm_with_local_config()
