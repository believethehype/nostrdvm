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

    dvmconfig = DVMConfig()
    dvmconfig.PRIVATE_KEY = os.getenv(env.NOSTR_PRIVATE_KEY)

    #Spawn two DVMs
    PDFextactor = TextExtractionPDF("PDF Extractor", env.NOSTR_PRIVATE_KEY)
    Translator = Translation("Translator", env.NOSTR_PRIVATE_KEY)

    #Add  the 2 DVMS to the config
    dvmconfig.SUPPORTED_TASKS = [PDFextactor, Translator]

    # Add  NIP89 events for both DVMs (set rebroad_cast = True in admin_utils)
    # Add the dtag in your .env file so you can update your dvm later and change the content in the module file as needed.
    # Get a dtag at vendata.io
    dvmconfig.NIP89s.append(PDFextactor.NIP89_announcement())
    dvmconfig.NIP89s.append(Translator.NIP89_announcement())

    #SET Lnbits Invoice Key and Server if DVM should provide invoices directly, else make sure you have a lnaddress on the profile
    dvmconfig.LNBITS_INVOICE_KEY = os.getenv(env.LNBITS_INVOICE_KEY)
    dvmconfig.LNBITS_URL = os.getenv(env.LNBITS_HOST)

    #Start the DVM
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
