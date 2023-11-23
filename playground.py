import json
import os

from tasks.imagegenerationsdxl import ImageGenerationSDXL
from tasks.textextractionpdf import TextExtractionPDF
from tasks.translation import Translation
from utils.admin_utils import AdminConfig
from utils.dvmconfig import DVMConfig

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
    d_tag = os.getenv("TASK_TEXT_EXTRACTION_NIP89_DTAG")
    nip90params = {}
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I extract text from pdf documents",
        "nip90Params": nip90params
    }
    return TextExtractionPDF(name=name, dvm_config=dvm_config, nip89d_tag=d_tag, nip89info=json.dumps(nip89info),
                             admin_config=admin_config)


def build_translator(name, dm_allowed_keys):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv("NOSTR_PRIVATE_KEY")
    dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.DM_ALLOWED = dm_allowed_keys

    d_tag = os.getenv("TASK_TRANSLATION_NIP89_DTAG")
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
    return Translation(name=name, dvm_config=dvm_config, nip89d_tag=d_tag, nip89info=json.dumps(nip89info),
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

    d_tag = os.getenv("TASK_IMAGE_GENERATION_NIP89_DTAG")
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
    return ImageGenerationSDXL(name=name, dvm_config=dvm_config, nip89d_tag=d_tag, nip89info=json.dumps(nip89info),
                               admin_config=admin_config, options=options)


def build_sketcher(name, dm_allowed_keys):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = os.getenv("NOSTR_PRIVATE_KEY2")
    dvm_config.LNBITS_INVOICE_KEY = os.getenv("LNBITS_INVOICE_KEY")
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.DM_ALLOWED = dm_allowed_keys

    d_tag = os.getenv("TASK_IMAGE_GENERATION_NIP89_DTAG2")
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

    # We add an optional AdminConfig for this one, and tell the dvm to rebroadcast its NIP89
    return ImageGenerationSDXL(name=name, dvm_config=dvm_config, nip89d_tag=d_tag, nip89info=json.dumps(nip89info),
                               admin_config=admin_config, options=options)