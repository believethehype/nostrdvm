import os
import signal
import time
from pathlib import Path
import dotenv

from bot.bot import Bot
from playground import build_pdf_extractor, build_googletranslator, build_unstable_diffusion, build_sketcher, \
    build_dalle, \
    build_whisperx, build_libretranslator, build_external_dvm, build_media_converter, build_inactive_follows_finder, \
    build_image_converter, build_googletranscribe
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nostr_utils import check_and_set_private_key
from utils.output_utils import PostProcessFunctionType


def run_nostr_dvm_with_local_config():
    # We will run an optional bot that can  communicate  with the DVMs
    # Note this is very basic for now and still under development
    bot_config = DVMConfig()
    bot_config.PRIVATE_KEY = check_and_set_private_key("bot")
    bot_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    bot_config.LNBITS_ADMIN_KEY = os.getenv("LNBITS_ADMIN_KEY")  # The bot will forward zaps for us, use responsibly
    bot_config.LNBITS_URL = os.getenv("LNBITS_HOST")

    # Spawn some DVMs in the playground and run them
    # You can add arbitrary DVMs there and instantiate them here

    # Spawn DVM1 Kind 5000: A local Text Extractor from PDFs
    pdfextractor = build_pdf_extractor("PDF Extractor", "pdf_extractor")
    # If we don't add it to the bot, the bot will not provide access to the DVM
    pdfextractor.run()

    # Spawn DVM2 Kind 5002 Local Text TranslationGoogle, calling the free Google API.
    translator = build_googletranslator("Google Translator", "google_translator")
    bot_config.SUPPORTED_DVMS.append(translator)  # We add translator to the bot
    translator.run()

    # Spawn DVM3 Kind 5002 Local Text TranslationLibre, calling the free LibreTranslateApi, as an alternative.
    # This will only run and appear on the bot if an endpoint is set in the .env
    if os.getenv("LIBRE_TRANSLATE_ENDPOINT") is not None and os.getenv("LIBRE_TRANSLATE_ENDPOINT") != "":
        libre_translator = build_libretranslator("Libre Translator", "libre_translator")
        bot_config.SUPPORTED_DVMS.append(libre_translator)  # We add translator to the bot
        libre_translator.run()

    # Spawn DVM3 Kind 5100 Image Generation This one uses a specific backend called nova-server.
    # If you want to use it, see the instructions in backends/nova_server
    if os.getenv("NOVA_SERVER") is not None and os.getenv("NOVA_SERVER") != "":
        unstable_artist = build_unstable_diffusion("Unstable Diffusion", "unstable_diffusion")
        bot_config.SUPPORTED_DVMS.append(unstable_artist)  # We add unstable Diffusion to the bot
        unstable_artist.run()

    # Spawn DVM4, another Instance of text-to-image, as before but use a different privatekey, model and lora this time.
    if os.getenv("NOVA_SERVER") is not None and os.getenv("NOVA_SERVER") != "":
        sketcher = build_sketcher("Sketcher", "sketcher")
        bot_config.SUPPORTED_DVMS.append(sketcher)  # We also add Sketcher to the bot
        sketcher.run()

    # Spawn DVM5, image-to-image, .
    if os.getenv("NOVA_SERVER") is not None and os.getenv("NOVA_SERVER") != "":
        imageconverter = build_image_converter("Image Converter Inkpunk", "image_converter_inkpunk")
        bot_config.SUPPORTED_DVMS.append(imageconverter)  # We also add Sketcher to the bot
        imageconverter.run()


    # Spawn DVM5, Another script on nova-server calling WhisperX to transcribe media files

    if os.getenv("NOVA_SERVER") is not None and os.getenv("NOVA_SERVER") != "":
        whisperer = build_whisperx("Whisperer", "whisperx")
        bot_config.SUPPORTED_DVMS.append(whisperer)  # We also add Sketcher to the bot
        whisperer.run()

    transcriptor = build_googletranscribe("Transcriptor", "speech_recognition")
    bot_config.SUPPORTED_DVMS.append(transcriptor)  # We also add Sketcher to the bot
    transcriptor.run()

    # Spawn DVM6, this one requires an OPENAI API Key and balance with OpenAI, you will move the task to them and pay
    # per call. Make sure you have enough balance and the DVM's cost is set higher than what you pay yourself, except, you know,
    # you're being generous.
    if os.getenv("OPENAI_API_KEY") is not None and os.getenv("OPENAI_API_KEY") != "":
        dalle = build_dalle("Dall-E 3", "dalle3")
        bot_config.SUPPORTED_DVMS.append(dalle)
        dalle.run()

    # Spawn DVM7.. oh wait, actually we don't spawn a new DVM, we use the dvmtaskinterface to define an external dvm by providing some info about it, such as
    # their pubkey, a name, task, kind etc. (unencrypted)
    tasktiger_external = build_external_dvm(name="External DVM: TaskTiger",
                                                 pubkey="d483935d6bfcef3645195c04c97bbb70aedb6e65665c5ea83e562ca3c7acb978",
                                                 task="text-to-image",
                                                 kind=EventDefinitions.KIND_NIP90_GENERATE_IMAGE,
                                                 fix_cost=80, per_unit_cost=0)

    tasktiger_external.SUPPORTS_ENCRYPTION = False # if the dvm does not support encrypted events, just send a regular event and mark it with p tag. Other dvms might initial answer
    bot_config.SUPPORTED_DVMS.append(tasktiger_external)
    # Don't run it, it's on someone else's machine, and we simply make the bot aware of it.


    # DVM: 8 Another external dvm for recommendations:
    ymhm_external = build_external_dvm(name="External DVM: You might have missed",
                                       pubkey="6b37d5dc88c1cbd32d75b713f6d4c2f7766276f51c9337af9d32c8d715cc1b93",
                                       task="content-discovery",
                                       kind=EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY,
                                       fix_cost=0, per_unit_cost=0,
                                       external_post_process=PostProcessFunctionType.LIST_TO_EVENTS)

    ymhm_external.SUPPORTS_ENCRYPTION = False  # if the dvm does not support encrypted events, just send a regular event and mark it with p tag. Other dvms might initial answer
    bot_config.SUPPORTED_DVMS.append(ymhm_external)

    # Spawn DVM9.. A Media Grabber/Converter
    media_bringer = build_media_converter("Media Bringer", "media_converter")
    bot_config.SUPPORTED_DVMS.append(media_bringer)
    media_bringer.run()

    # Spawn DVM10 Discover inactive followers
    discover_inactive = build_inactive_follows_finder("Bygones", "discovery_inactive_follows")
    bot_config.SUPPORTED_DVMS.append(discover_inactive)
    discover_inactive.run()




    Bot(bot_config)

    # Keep the main function alive for libraries that require it, like openai
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        os.kill(os.getpid(), signal.SIGKILL)
        exit(1)


if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')
    run_nostr_dvm_with_local_config()
