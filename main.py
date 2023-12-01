import json
import os
from pathlib import Path
import dotenv
from nostr_sdk import PublicKey

from bot.bot import Bot
from interfaces.dvmtaskinterface import DVMTaskInterface

import tasks.convert_media as convert_media
import tasks.discovery_inactive_follows as discovery_inactive_follows
import tasks.imagegeneration_openai_dalle as imagegeneration_openai_dalle
import tasks.imagegeneration_sdxl as imagegeneration_sdxl
import tasks.imagegeneration_sdxlimg2img as imagegeneration_sdxlimg2img
import tasks.textextraction_pdf as textextraction_pdf
import tasks.textextraction_google as textextraction_google
import tasks.textextraction_whisperx as textextraction_whisperx
import tasks.translation_google as translation_google
import tasks.translation_libretranslate as translation_libretranslate

from utils.admin_utils import AdminConfig
from utils.backend_utils import keep_alive
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config, check_and_set_d_tag
from utils.nostr_utils import check_and_set_private_key
from utils.output_utils import PostProcessFunctionType


def playground():
    # We will run an optional bot that can  communicate  with the DVMs
    # Note this is very basic for now and still under development
    bot_config = DVMConfig()
    bot_config.PRIVATE_KEY = check_and_set_private_key("bot")
    bot_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    bot_config.LNBITS_ADMIN_KEY = os.getenv("LNBITS_ADMIN_KEY")  # The bot will forward zaps for us, use responsibly
    bot_config.LNBITS_URL = os.getenv("LNBITS_HOST")

    # Generate an optional Admin Config, in this case, whenever we give our DVMs this config, they will (re)broadcast
    # their NIP89 announcement
    # You can create individual admins configs and hand them over when initializing the dvm,
    # for example to whilelist users or add to their balance.
    # If you use this global config, options will be set for all dvms that use it.
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = False
    # Set rebroadcast to true once you have set your NIP89 descriptions and d tags. You only need to rebroadcast once you
    # want to update your NIP89 descriptions
    admin_config.UPDATE_PROFILE = False
    admin_config.LUD16 = ""

    # Spawn some DVMs in the playground and run them
    # You can add arbitrary DVMs there and instantiate them here

    # Spawn DVM1 Kind 5000: A local Text Extractor from PDFs
    pdfextractor = textextraction_pdf.build_example("PDF Extractor", "pdf_extractor", admin_config)
    # If we don't add it to the bot, the bot will not provide access to the DVM
    pdfextractor.run()

    # Spawn DVM2 Kind 5002 Local Text TranslationGoogle, calling the free Google API.
    translator = translation_google.build_example("Google Translator", "google_translator", admin_config)
    bot_config.SUPPORTED_DVMS.append(translator)  # We add translator to the bot
    translator.run()

    # Spawn DVM3 Kind 5002 Local Text TranslationLibre, calling the free LibreTranslateApi, as an alternative.
    # This will only run and appear on the bot if an endpoint is set in the .env
    if os.getenv("LIBRE_TRANSLATE_ENDPOINT") is not None and os.getenv("LIBRE_TRANSLATE_ENDPOINT") != "":
        libre_translator = translation_libretranslate.build_example("Libre Translator", "libre_translator", admin_config)
        bot_config.SUPPORTED_DVMS.append(libre_translator)  # We add translator to the bot
        libre_translator.run()

    # Spawn DVM3 Kind 5100 Image Generation This one uses a specific backend called nova-server.
    # If you want to use it, see the instructions in backends/nova_server
    if os.getenv("NOVA_SERVER") is not None and os.getenv("NOVA_SERVER") != "":
        stable_artist = imagegeneration_sdxl.build_example("Stable Diffusion XL", "stable_diffusion",
                                                           admin_config, os.getenv("NOVA_SERVER"),
                                                              "stabilityai/stable-diffusion-xl",
                                                              "")
        bot_config.SUPPORTED_DVMS.append(stable_artist)  # We add unstable Diffusion to the bot
        stable_artist.run()

    # Spawn DVM4, another Instance of text-to-image, as before but use a different privatekey, model and lora this time.
    if os.getenv("NOVA_SERVER") is not None and os.getenv("NOVA_SERVER") != "":
        # Let's not use one of the examples in this one, but generate our own variation of the dvm. We make a new DVM
        # called "Sketcher", with a predefined model and lora, so it will always make sketches of prompts
        def build_sketcher(name, identifier, admin_config):
            dvm_config = DVMConfig()
            dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
            dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
            dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")

            nip90params = {
                "negative_prompt": {
                    "required": False,
                    "values": []
                },
                "ratio": {
                    "required": False,
                    "values": ["1:1", "4:3", "16:9", "3:4", "9:16", "10:16"]
                }
            }
            nip89info = {
                "name": name,
                "image": "https://image.nostr.build/229c14e440895da30de77b3ca145d66d4b04efb4027ba3c44ca147eecde891f1.jpg",
                "about": "I draw images based on a prompt in the style of paper sketches",
                "nip90Params": nip90params
            }

            # A module might have options it can be initialized with, here we set a default model, lora and the nova-server
            # address it should use. These parameters can be freely defined in the task component
            options = {'default_model': "mohawk", 'default_lora': "timburton", 'nova_server': os.getenv("NOVA_SERVER")}

            nip89config = NIP89Config()
            nip89config.DTAG = nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                                                      nip89info["image"])
            nip89config.CONTENT = json.dumps(nip89info)
            # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
            return imagegeneration_sdxl.ImageGenerationSDXL(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                                            admin_config=admin_config, options=options)

        sketcher = build_sketcher("Sketcher", "sketcher", admin_config)
        bot_config.SUPPORTED_DVMS.append(sketcher)  # We also add Sketcher to the bot
        sketcher.run()

    # Spawn DVM5, image-to-image, .
    if os.getenv("NOVA_SERVER") is not None and os.getenv("NOVA_SERVER") != "":
        imageconverter = imagegeneration_sdxlimg2img.build_example("Image Converter Inkpunk",
                                                                      "image_converter_inkpunk", admin_config,
                                                                   os.getenv("NOVA_SERVER"),
                                                                      "inkpunk", 0.6)
        bot_config.SUPPORTED_DVMS.append(imageconverter)  # We also add Sketcher to the bot
        imageconverter.run()

    # Spawn DVM5, Another script on nova-server calling WhisperX to transcribe media files

    if os.getenv("NOVA_SERVER") is not None and os.getenv("NOVA_SERVER") != "":
        whisperer = textextraction_whisperx.build_example("Whisperer", "whisperx", admin_config, os.getenv("NOVA_SERVER"))
        bot_config.SUPPORTED_DVMS.append(whisperer)  # We also add Sketcher to the bot
        whisperer.run()

    transcriptor = textextraction_google.build_example("Transcriptor", "speech_recognition", admin_config)
    bot_config.SUPPORTED_DVMS.append(transcriptor)  # We also add Sketcher to the bot
    transcriptor.run()

    # Spawn DVM6, this one requires an OPENAI API Key and balance with OpenAI, you will move the task to them and pay
    # per call. Make sure you have enough balance and the DVM's cost is set higher than what you pay yourself, except, you know,
    # you're being generous.
    if os.getenv("OPENAI_API_KEY") is not None and os.getenv("OPENAI_API_KEY") != "":
        dalle = imagegeneration_openai_dalle.build_example("Dall-E 3", "dalle3", admin_config)
        bot_config.SUPPORTED_DVMS.append(dalle)
        dalle.run()


    #Let's define a function so we can add external DVMs to our bot, we will instanciate it afterwards
    def build_external_dvm(name, pubkey, task, kind, fix_cost, per_unit_cost,
                           external_post_process=PostProcessFunctionType.NONE):
        dvm_config = DVMConfig()
        dvm_config.PUBLIC_KEY = PublicKey.from_hex(pubkey).to_hex()
        dvm_config.FIX_COST = fix_cost
        dvm_config.PER_UNIT_COST = per_unit_cost
        dvm_config.EXTERNAL_POST_PROCESS_TYPE = external_post_process
        nip89info = {
            "name": name,
        }
        nip89config = NIP89Config()
        nip89config.KIND = kind
        nip89config.CONTENT = json.dumps(nip89info)

        interface = DVMTaskInterface(name=name, dvm_config=dvm_config, nip89config=nip89config, task=task)

        return interface

    # Spawn DVM7.. oh wait, actually we don't spawn a new DVM, we use the dvmtaskinterface to define an external dvm by providing some info about it, such as
    # their pubkey, a name, task, kind etc. (unencrypted)
    tasktiger_external = build_external_dvm(name="External DVM: TaskTiger",
                                            pubkey="d483935d6bfcef3645195c04c97bbb70aedb6e65665c5ea83e562ca3c7acb978",
                                            task="text-to-image",
                                            kind=EventDefinitions.KIND_NIP90_GENERATE_IMAGE,
                                            fix_cost=80, per_unit_cost=0)

    tasktiger_external.SUPPORTS_ENCRYPTION = False  # if the dvm does not support encrypted events, just send a regular NIP90 event and mark it with p tag. Other dvms might answer initally
    bot_config.SUPPORTED_DVMS.append(tasktiger_external)
    # Don't run it, it's on someone else's machine, and we simply make the bot aware of it.

    # Spawn DVM8 A Media Grabber/Converter
    media_bringer = convert_media.build_example("Media Bringer", "media_converter", admin_config)
    bot_config.SUPPORTED_DVMS.append(media_bringer)
    media_bringer.run()

    # DVM: 9 Another external dvm for recommendations:
    ymhm_external = build_external_dvm(name="External DVM: You might have missed",
                                       pubkey="6b37d5dc88c1cbd32d75b713f6d4c2f7766276f51c9337af9d32c8d715cc1b93",
                                       task="content-discovery",
                                       kind=EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY,
                                       fix_cost=0, per_unit_cost=0,
                                       external_post_process=PostProcessFunctionType.LIST_TO_EVENTS)
    # If we get back a list of people or events, we can post-process it to make it readable in social clients

    ymhm_external.SUPPORTS_ENCRYPTION = False
    bot_config.SUPPORTED_DVMS.append(ymhm_external)

    # Spawn DVM10 Find inactive followers
    discover_inactive = discovery_inactive_follows.build_example("Bygones", "discovery_inactive_follows",
                                                                 admin_config)
    bot_config.SUPPORTED_DVMS.append(discover_inactive)
    discover_inactive.run()

    Bot(bot_config)
    # Keep the main function alive for libraries that require it, like openai
    keep_alive()


if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')
    playground()
