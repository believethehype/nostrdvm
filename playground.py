import json
import os

from tasks.imagegeneration_openai_dalle import ImageGenerationDALLE
from tasks.imagegeneration_sdxl import ImageGenerationSDXL
from tasks.textextractionpdf import TextExtractionPDF
from tasks.translation import Translation
from utils.admin_utils import AdminConfig
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config
"""
This File is a playground to create DVMs. It shows some examples of DVMs that make use of the modules in the tasks folder
These DVMs should be considered examples and will be extended in the future. env variables are used to not commit keys,
but if used privatley, these can also be directly filled in this file. The main.py function calls some of the functions
defined here and starts the DVMs.

Note that the admin_config is optional, and if given commands as defined in admin_utils will be called at start of the 
DVM. For example the NIP89 event can be rebroadcasted (store the d_tag somewhere).

DM_ALLOWED is used to tell the DVM to which npubs it should listen to. We use this here to listen to our bot, 
as defined in main.py to perform jobs on it's behalf and reply. 

if LNBITS_INVOICE_KEY is not set (=""), the DVM is still zappable but a lud16 address in required in the profile. 

additional options can be set, for example to preinitalize vaiables or give parameters that are required to perform a 
task, for example an address or an API key. 


"""

# Generate an optional Admin Config, in this case, whenever we give our DVMs this config, they will (re)broadcast
# their NIP89 announcement
admin_config = AdminConfig()
admin_config.REBROADCAST_NIP89 = False


def build_pdf_extractor(name, dm_allowed_keys):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv("NOSTR_PRIVATE_KEY")
    dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.DM_ALLOWED = dm_allowed_keys
    # Add NIP89
    nip90params = {}
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I extract text from pdf documents",
        "nip90Params": nip90params
    }

    nip89config = NIP89Config()
    nip89config.DTAG = os.getenv("TASK_TEXT_EXTRACTION_NIP89_DTAG")
    nip89config.CONTENT = json.dumps(nip89info)
    return TextExtractionPDF(name=name, dvm_config=dvm_config, nip89config=nip89config,
                             admin_config=admin_config)


def build_translator(name, dm_allowed_keys):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv("NOSTR_PRIVATE_KEY")
    dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.DM_ALLOWED = dm_allowed_keys

    nip90params = {
        "language": {
            "required": False,
            "values": ["en", "az", "be", "bg", "bn", "bs", "ca", "ceb", "co", "cs", "cy", "da", "de", "el", "eo", "es",
                       "et", "eu", "fa", "fi", "fr", "fy", "ga", "gd", "gl","gu", "ha", "haw", "hi", "hmn", "hr", "ht",
                       "hu", "hy", "id", "ig", "is", "it", "he", "ja", "jv", "ka", "kk","km", "kn", "ko", "ku", "ky",
                       "la", "lb", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl",
                       "no", "ny", "or", "pa", "pl", "ps", "pt", "ro", "ru", "sd", "si", "sk", "sl", "sm", "sn", "so",
                       "sq", "sr", "st", "su", "sv", "sw", "ta", "te","tg", "th", "tl", "tr", "ug", "uk", "ur", "uz",
                       "vi", "xh", "yi", "yo", "zh", "zu"]
        }
    }
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I translate text from given text/event/job. Currently using Google Translation Services to translate "
                 "input into the language defined in params.",
        "nip90Params": nip90params
    }
    nip89config = NIP89Config()
    nip89config.DTAG = os.getenv("TASK_TRANSLATION_NIP89_DTAG")
    nip89config.CONTENT = json.dumps(nip89info)
    return Translation(name=name, dvm_config=dvm_config, nip89config=nip89config,
                       admin_config=admin_config)


def build_unstable_diffusion(name, dm_allowed_keys):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv("NOSTR_PRIVATE_KEY")
    dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.DM_ALLOWED = dm_allowed_keys

    # A module might have options it can be initialized with, here we set a default model, and the nova-server
    # address it should use. These parameters can be freely defined in the task component
    options = {'default_model': "unstable", 'nova_server': os.getenv("NOVA_SERVER")}

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
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I draw images based on a prompt with a Model called unstable diffusion",
        "nip90Params": nip90params
    }
    nip89config = NIP89Config()
    nip89config.DTAG = os.getenv("TASK_IMAGE_GENERATION_NIP89_DTAG")
    nip89config.CONTENT = json.dumps(nip89info)
    return ImageGenerationSDXL(name=name, dvm_config=dvm_config, nip89config=nip89config,
                               admin_config=admin_config, options=options)


def build_sketcher(name, dm_allowed_keys):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv("NOSTR_PRIVATE_KEY2")
    dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.DM_ALLOWED = dm_allowed_keys

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
    nip89config.DTAG = os.getenv("TASK_IMAGE_GENERATION_NIP89_DTAG2")
    nip89config.CONTENT = json.dumps(nip89info)
    # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    return ImageGenerationSDXL(name=name, dvm_config=dvm_config, nip89config=nip89config,
                               admin_config=admin_config, options=options)

def build_dalle(name, dm_allowed_keys):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv("NOSTR_PRIVATE_KEY3")
    dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.DM_ALLOWED = dm_allowed_keys

    nip90params = {
        "size": {
            "required": False,
            "values": ["1024:1024", "1024x1792", "1792x1024"]
        }
    }
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I use OpenAI's DALL·E 3",
        "nip90Params": nip90params
    }

    # A module might have options it can be initialized with, here we set a default model, lora and the nova-server
    # address it should use. These parameters can be freely defined in the task component

    nip89config = NIP89Config()
    nip89config.DTAG = os.getenv("TASK_IMAGE_GENERATION_NIP89_DTAG3")
    nip89config.CONTENT = json.dumps(nip89info)
    # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    return ImageGenerationDALLE(name=name, dvm_config=dvm_config, nip89config=nip89config,
                               admin_config=admin_config)