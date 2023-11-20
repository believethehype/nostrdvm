import os
from pathlib import Path
from threading import Thread

import dotenv
import utils.env as env
from tasks.imagegenerationsdxl import ImageGenerationSDXL
from tasks.textextractionpdf import TextExtractionPDF
from tasks.translation import Translation

def run_nostr_dvm_with_local_config():
    from dvm import DVM, DVMConfig

    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv(env.NOSTR_PRIVATE_KEY)

    # Spawn the DVMs
    # Add  NIP89 events for each DVM (set rebroad_cast = True for the next start in admin_utils)
    # Add the dtag here or in your .env file, so you can update your dvm later and change the content as needed.
    # Get a dtag and the content at vendata.io

    # Spawn DVM1 Kind 5000 Text Ectractor from PDFs
    pdfextactor = TextExtractionPDF("PDF Extractor", os.getenv(env.NOSTR_PRIVATE_KEY))
    d_tag = os.getenv(env.TASK_TEXTEXTRACTION_NIP89_DTAG)
    content = "{\"name\":\"" + pdfextactor.NAME + ("\",\"image\":\"https://image.nostr.build"
                                                   "/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669"
                                                   ".jpg\",\"about\":\"I extract Text from pdf documents\","
                                                   "\"nip90Params\":{}}")
    dvm_config.NIP89s.append(pdfextactor.NIP89_announcement(d_tag, content))

    # Spawn DVM2 Kind 5002 Text Translation
    translator = Translation("Translator", os.getenv(env.NOSTR_PRIVATE_KEY))
    d_tag = os.getenv(env.TASK_TRANSLATION_NIP89_DTAG)
    content = "{\"name\":\"" + translator.NAME + ("\",\"image\":\"https://image.nostr.build"
                                                  "/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669"
                                                  ".jpg\",\"about\":\"I translate text from given text/event/job, "
                                                  "currently using Google Translation Services into language defined "
                                                  "in param.  \",\"nip90Params\":{\"language\":{\"required\":true,"
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
    dvm_config.NIP89s.append(translator.NIP89_announcement(d_tag, content))

    # Spawn DVM3 Kind 5100 Image Generation This one uses a specific backend called nova-server. If you want to use
    # it see the instructions in backends/nova_server
    artist = ImageGenerationSDXL("Unstable Diffusion", os.getenv(env.NOSTR_PRIVATE_KEY))
    d_tag = os.getenv(env.TASK_IMAGEGENERATION_NIP89_DTAG)
    content = "{\"name\":\"" + artist.NAME + ("\",\"image\":\"https://image.nostr.build"
                                              "/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg"
                                              "\",\"about\":\"I draw images based on a prompt with Stable Diffusion "
                                              "XL 1.0.\",\"nip90Params\":{}}")
    dvm_config.NIP89s.append(artist.NIP89_announcement(d_tag, content))



    # Add the DVMS you want to use to the config
    dvm_config.SUPPORTED_TASKS = [pdfextactor, translator, artist]

    # SET Lnbits Invoice Key and Server if DVM should provide invoices directly, else make sure you have a lnaddress
    # on the profile
    dvm_config.LNBITS_INVOICE_KEY = os.getenv(env.LNBITS_INVOICE_KEY)
    dvm_config.LNBITS_URL = os.getenv(env.LNBITS_HOST)

    # Start the Server
    nostr_dvm_thread = Thread(target=DVM, args=[dvm_config])
    nostr_dvm_thread.start()


if __name__ == '__main__':

    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    run_nostr_dvm_with_local_config()
