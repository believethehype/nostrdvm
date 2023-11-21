import os
from pathlib import Path

import dotenv
import utils.env as env
from tasks.imagegenerationsdxl import ImageGenerationSDXL
from tasks.textextractionpdf import TextExtractionPDF
from tasks.translation import Translation
from utils.admin_utils import AdminConfig
from utils.dvmconfig import DVMConfig


def run_nostr_dvm_with_local_config():
    #Generate a optional Admin Config, in this case, whenever we give our DVMS this config, they will (re)broadcast
    # their NIP89 announcement
    admin_config = AdminConfig()
    admin_config.REBROADCASTNIP89 = True

    # Spawn the DVMs
    # Add  NIP89 events for each DVM
    # Add the dtag here or in your .env file, so you can update your dvm later and change the content as needed.
    # Get a dtag and the content at vendata.io

    # Spawn DVM1 Kind 5000 Text Extractor from PDFs

    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv(env.NOSTR_PRIVATE_KEY)
    dvm_config.LNBITS_INVOICE_KEY = os.getenv(env.LNBITS_INVOICE_KEY)
    dvm_config.LNBITS_URL = os.getenv(env.LNBITS_HOST)

    pdfextactor = TextExtractionPDF("PDF Extractor", dvm_config)
    d_tag = os.getenv(env.TASK_TEXTEXTRACTION_NIP89_DTAG)
    content = ("{\"name\":\"" + pdfextactor.NAME + "\","
                "\"image\":\"https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg\","
                "\"about\":\"I extract Text from pdf documents\","
                "\"nip90Params\":{}}")
    dvm_config.NIP89 = pdfextactor.NIP89_announcement(d_tag, content)

    # Spawn DVM2 Kind 5002 Text Translation
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv(env.NOSTR_PRIVATE_KEY)
    dvm_config.LNBITS_INVOICE_KEY = os.getenv(env.LNBITS_INVOICE_KEY)
    dvm_config.LNBITS_URL = os.getenv(env.LNBITS_HOST)

    translator = Translation("Translator", dvm_config)
    d_tag = os.getenv(env.TASK_TRANSLATION_NIP89_DTAG)
    content = ("{\"name\":\"" + translator.NAME + "\","
                "\"image\":\"https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg\","
                "\"about\":\"I translate text from given text/event/job, ""currently using Google Translation Services into language defined in params.\","
                "\"nip90Params\":{\"language\":{\"required\":true,"
                                                  "\"values\":[\"af\",\"am\",\"ar\",\"az\",\"be\",\"bg\",\"bn\","
                                                  "\"bs\",\"ca\",\"ceb\",\"co\",\"cs\",\"cy\",\"da\",\"de\",\"el\","
                                                  "\"eo\",\"es\",\"et\",\"eu\",\"fa\",\"fi\",\"fr\",\"fy\",\"ga\","
                                                  "\"gd\",\"gl\",\"gu\",\"ha\",\"haw\",\"hi\",\"hmn\",\"hr\",\"ht\","
                                                  "\"hu\",\"hy\",\"id\",\"ig\",\"is\",\"it\",\"he\",\"ja\",\"jv\","
                                                  "\"ka\",\"kk\",\"km\",\"kn\",\"ko\",\"ku\",\"ky\",\"la\",\"lb\","
                                                  "\"lo\",\"lt\",\"lv\",\"mg\",\"mi\",\"mk\",\"ml\",\"mn\",\"mr\","
                                                  "\"ms\",\"mt\",\"my\",\"ne\",\"nl\",\"no\",\"ny\",\"or\",\"pa\","
                                                  "\"pl\",\"ps\",\"pt\",\"ro\",\"ru\",\"sd\",\"si\",\"sk\",\"sl\","
                                                  "\"sm\",\"sn\",\"so\",\"sq\",\"sr\",\"st\",\"su\",\"sv\",\"sw\","
                                                  "\"ta\",\"te\",\"tg\",\"th\",\"tl\",\"tr\",\"ug\",\"uk\",\"ur\","
                                                  "\"uz\",\"vi\",\"xh\",\"yi\",\"yo\",\"zh\",\"zu\"]}}}")

    dvm_config.NIP89 = translator.NIP89_announcement(d_tag, content)

    # Spawn DVM3 Kind 5100 Image Generation This one uses a specific backend called nova-server. If you want to use
    # it see the instructions in backends/nova_server
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv(env.NOSTR_PRIVATE_KEY)
    dvm_config.LNBITS_INVOICE_KEY = os.getenv(env.LNBITS_INVOICE_KEY)
    dvm_config.LNBITS_URL = os.getenv(env.LNBITS_HOST)
    unstableartist = ImageGenerationSDXL("Unstable Diffusion", dvm_config, "unstable")
    d_tag = os.getenv(env.TASK_IMAGEGENERATION_NIP89_DTAG)
    content = ("{\"name\":\"" + unstableartist.NAME + "\","
               "\"image\":\"https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg\","
               "\"about\":\"I draw images based on a prompt with a Model called unstable diffusion.\","
               "\"nip90Params\":{}}")
    dvm_config.NIP89 = unstableartist.NIP89_announcement(d_tag, content)


    # Spawn another Instance of text-to-image but use a different privatekey, model and lora this time.
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = "73b262d31edc6ea1316dffcc7daa772651d661e6475761b7b78291482c1bf5cb"
    dvm_config.LNBITS_INVOICE_KEY = os.getenv(env.LNBITS_INVOICE_KEY)
    dvm_config.LNBITS_URL = os.getenv(env.LNBITS_HOST)
    #We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    sketcher = ImageGenerationSDXL("Sketcher", dvm_config, admin_config, default_model="mohawk", default_lora="timburton")
    d_tag = os.getenv(env.TASK_IMAGEGENERATION_NIP89_DTAG2)
    content = ("{\"name\":\"" + unstableartist.NAME + "\","
               "\"image\":\"https://image.nostr.build/229c14e440895da30de77b3ca145d66d4b04efb4027ba3c44ca147eecde891f1.jpg\","
               "\"about\":\"I draw images based on a prompt with a Model called unstable diffusion.\","
               "\"nip90Params\":{}}")

    dvm_config.NIP89 = sketcher.NIP89_announcement(d_tag, content)


if __name__ == '__main__':

    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    run_nostr_dvm_with_local_config()
