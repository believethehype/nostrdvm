import os
from pathlib import Path
from threading import Thread

import dotenv
from nostr_sdk import Keys

from bot import Bot
from playground import build_pdf_extractor, build_translator, build_unstable_diffusion, build_sketcher
from utils.dvmconfig import DVMConfig


def run_nostr_dvm_with_local_config():
    # We extract the Publickey from our bot, so the DVMs know who they should listen and react to.
    bot_publickey = Keys.from_sk_str(os.getenv("BOT_PRIVATE_KEY")).public_key()

    # Spawn some DVMs in the playground and run them
    # You can add arbitrary DVMs there and instantiate them here

    # Spawn DVM1 Kind 5000 Text Extractor from PDFs
    pdfextractor = build_pdf_extractor("PDF Extractor", [bot_publickey])
    pdfextractor.run()

    # Spawn DVM2 Kind 5002 Text Translation
    translator = build_translator("Translator", [bot_publickey])
    translator.run()

    # Spawn DVM3 Kind 5100 Image Generation This one uses a specific backend called nova-server.
    # If you want to use it, see the instructions in backends/nova_server
    unstable_artist = build_unstable_diffusion("Unstable Diffusion", [bot_publickey])
    unstable_artist.run()

    # Spawn DVM4, another Instance of text-to-image, as before but use a different privatekey, model and lora this time.
    sketcher = build_sketcher("Sketcher", [bot_publickey])
    sketcher.run()

    # We will run an optional bot that can  communicate  with the DVMs
    # Note this is very basic for now and still under development
    bot_config = DVMConfig()
    bot_config.PRIVATE_KEY = os.getenv("BOT_PRIVATE_KEY")
    bot_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    bot_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    # Finally we add some of the DVMs we created before to the Bot and start it.
    bot_config.SUPPORTED_TASKS = [sketcher, unstable_artist, translator]

    bot = Bot
    nostr_dvm_thread = Thread(target=bot, args=[bot_config])
    nostr_dvm_thread.start()


if __name__ == '__main__':

    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    run_nostr_dvm_with_local_config()
