import os
from pathlib import Path
import dotenv

from nostr_dvm.bot import Bot
from nostr_dvm.tasks import videogeneration_replicate_svd, imagegeneration_replicate_sdxl, textgeneration_llmlite, \
    trending_notes_nostrband, discovery_inactive_follows, translation_google, textextraction_pdf, \
    translation_libretranslate, textextraction_google, convert_media, imagegeneration_openai_dalle, texttospeech
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.backend_utils import keep_alive
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.external_dvm_utils import build_external_dvm
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.output_utils import PostProcessFunctionType
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys
from nostr_sdk import Keys


def playground():
    # We will run an optional bot that can  communicate  with the DVMs
    # Note this is very basic for now and still under development
    bot_config = DVMConfig()
    bot_config.PRIVATE_KEY = check_and_set_private_key("bot")
    npub = Keys.from_sk_str(bot_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, user_id, lnaddress = check_and_set_ln_bits_keys("bot", npub)
    bot_config.LNBITS_INVOICE_KEY = invoice_key
    bot_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    bot_config.LNBITS_URL = os.getenv("LNBITS_HOST")


    # Generate an optional Admin Config, in this case, whenever we give our DVMs this config, they will (re)broadcast
    # their NIP89 announcement
    # You can create individual admins configs and hand them over when initializing the dvm,
    # for example to whilelist users or add to their balance.
    # If you use this global config, options will be set for all dvms that use it.
    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = False
    admin_config.LUD16 = lnaddress
    # Set rebroadcast to true once you have set your NIP89 descriptions and d tags. You only need to rebroadcast once you
    # want to update your NIP89 descriptions

    # Update the DVMs (not the bot) profile. For example after you updated the NIP89 or the lnaddress, you can automatically update profiles here.
    admin_config.UPDATE_PROFILE = False


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


    # Spawn DVM4, this one requires an OPENAI API Key and balance with OpenAI, you will move the task to them and pay
    # per call. Make sure you have enough balance and the DVM's cost is set higher than what you pay yourself, except, you know,
    # you're being generous.
    if os.getenv("OPENAI_API_KEY") is not None and os.getenv("OPENAI_API_KEY") != "":
        dalle = imagegeneration_openai_dalle.build_example("Dall-E 3", "dalle3", admin_config)
        bot_config.SUPPORTED_DVMS.append(dalle)
        dalle.run()

    if os.getenv("REPLICATE_API_TOKEN") is not None and os.getenv("REPLICATE_API_TOKEN") != "":
        sdxlreplicate = imagegeneration_replicate_sdxl.build_example("Stable Diffusion XL", "replicate_sdxl", admin_config)
        bot_config.SUPPORTED_DVMS.append(sdxlreplicate)
        sdxlreplicate.run()

    if os.getenv("REPLICATE_API_TOKEN") is not None and os.getenv("REPLICATE_API_TOKEN") != "":
        svdreplicate = videogeneration_replicate_svd.build_example("Stable Video Diffusion", "replicate_svd", admin_config)
        bot_config.SUPPORTED_DVMS.append(svdreplicate)
        svdreplicate.run()


    #Let's define a function so we can add external DVMs to our bot, we will instanciate it afterwards

    # Spawn DVM5.. oh wait, actually we don't spawn a new DVM, we use the dvmtaskinterface to define an external dvm by providing some info about it, such as
    # their pubkey, a name, task, kind etc. (unencrypted)
    tasktiger_external = build_external_dvm(pubkey="d483935d6bfcef3645195c04c97bbb70aedb6e65665c5ea83e562ca3c7acb978",
                                            task="text-to-image",
                                            kind=EventDefinitions.KIND_NIP90_GENERATE_IMAGE,
                                            fix_cost=80, per_unit_cost=0, config=bot_config)
    bot_config.SUPPORTED_DVMS.append(tasktiger_external)
    # Don't run it, it's on someone else's machine, and we simply make the bot aware of it.


    # DVM: 6 Another external dvm for recommendations:
    ymhm_external = build_external_dvm(pubkey="6b37d5dc88c1cbd32d75b713f6d4c2f7766276f51c9337af9d32c8d715cc1b93",
                                       task="content-discovery",
                                       kind=EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY,
                                       fix_cost=0, per_unit_cost=0,
                                       external_post_process=PostProcessFunctionType.LIST_TO_EVENTS, config=bot_config)
    # If we get back a list of people or events, we can post-process it to make it readable in social clients
    bot_config.SUPPORTED_DVMS.append(ymhm_external)


    # Spawn DVM 7 Find inactive followers
    googleextractor = textextraction_google.build_example("Extractor", "speech_recognition",
                                                          admin_config)
    bot_config.SUPPORTED_DVMS.append(googleextractor)
    googleextractor.run()


    # Spawn DVM 8 A Media Grabber/Converter
    media_bringer = convert_media.build_example("Media Bringer", "media_converter", admin_config)
    bot_config.SUPPORTED_DVMS.append(media_bringer)
    media_bringer.run()



    # Spawn DVM9  Find inactive followers
    discover_inactive = discovery_inactive_follows.build_example("Bygones", "discovery_inactive_follows",
                                                                 admin_config)
    bot_config.SUPPORTED_DVMS.append(discover_inactive)
    discover_inactive.run()

    trending = trending_notes_nostrband.build_example("Trending Notes on nostr.band", "trending_notes_nostrband", admin_config)
    bot_config.SUPPORTED_DVMS.append(trending)
    trending.run()

    ollama = textgeneration_llmlite.build_example("LLM", "llmlite", admin_config)
    bot_config.SUPPORTED_DVMS.append(ollama)
    ollama.run()

    tts = texttospeech.build_example("Text To Speech Test", "tts", admin_config)
    bot_config.SUPPORTED_DVMS.append(tts)
    tts.run()

    # Run the bot
    Bot(bot_config)
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
