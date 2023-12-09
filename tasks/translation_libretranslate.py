import json
import os
from pathlib import Path

import dotenv
import requests

from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.backend_utils import keep_alive
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config, check_and_set_d_tag
from utils.nostr_utils import get_referenced_event_by_id, get_event_by_id, check_and_set_private_key
from utils.zap_utils import check_and_set_ln_bits_keys
from nostr_sdk import  Keys

"""
This File contains a Module to call Google Translate Services locally on the DVM Machine

Accepted Inputs: Text, Events, Jobs (Text Extraction, Summary, Translation)
Outputs: Text containing the Translation with LibreTranslation in the desired language.
Params:  -language The target language

Requires API key or self-hosted instance
"""


class TranslationLibre(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_TRANSLATE_TEXT
    TASK: str = "translation"
    FIX_COST: float = 0

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None, task=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options, task)

    def is_input_supported(self, tags):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "event" and input_type != "job" and input_type != "text":
                    return False
                if input_type != "text" and len(input_value) > 4999:
                    return False
        return True

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex()}
        text = ""
        translation_lang = "en"

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "event":
                    evt = get_event_by_id(tag.as_vec()[1], client=client, config=dvm_config)
                    text = evt.content()
                elif input_type == "text":
                    text = tag.as_vec()[1]
                elif input_type == "job":
                    evt = get_referenced_event_by_id(event_id=tag.as_vec()[1], client=client,
                                                     kinds=[EventDefinitions.KIND_NIP90_RESULT_EXTRACT_TEXT,
                                                            EventDefinitions.KIND_NIP90_RESULT_SUMMARIZE_TEXT,
                                                            EventDefinitions.KIND_NIP90_RESULT_TRANSLATE_TEXT],
                                                     dvm_config=dvm_config)
                    text = evt.content()

            elif tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "language":  # check for param type
                    translation_lang = str(tag.as_vec()[2]).split('-')[0]

        options = {
            "text": text,
            "language": translation_lang
        }
        request_form['options'] = json.dumps(options)
        return request_form

    def process(self, request_form):
        options = DVMTaskInterface.set_options(request_form)
        request = {
            "q":  options["text"],
            "source": "auto",
            "target":  options["language"]
        }
        if options["libre_api_key"] != "":
            request["api_key"] = options["libre_api_key"]

        data = json.dumps(request)

        headers = {'Content-type': 'application/json'}
        response = requests.post(options["libre_end_point"] + "/translate", headers=headers, data=data)
        reply = json.loads(response.text)
        if reply.get("translatedText"):
            translated_text = reply['translatedText']
            #untested
            #confidence = reply["detectedLanguage"]['confidence']
            #language = reply["detectedLanguage"]['language']
            #print(translated_text + "language: " + language + "conf: " + confidence)
        else:
            return response.text

        return translated_text


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    npub = Keys.from_sk_str(dvm_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, user_id, lnaddress = check_and_set_ln_bits_keys(identifier, npub)
    dvm_config.LNBITS_INVOICE_KEY = invoice_key
    dvm_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    admin_config.LUD16 = lnaddress

    options = {'libre_end_point': os.getenv("LIBRE_TRANSLATE_ENDPOINT"),
               'libre_api_key': os.getenv("LIBRE_TRANSLATE_API_KEY")}
    nip90params = {
        "language": {
            "required": False,
            "values": ["en", "az", "be", "bg", "bn", "bs", "ca", "ceb", "co", "cs", "cy", "da", "de", "el", "eo", "es",
                       "et", "eu", "fa", "fi", "fr", "fy", "ga", "gd", "gl", "gu", "ha", "haw", "hi", "hmn", "hr", "ht",
                       "hu", "hy", "id", "ig", "is", "it", "he", "ja", "jv", "ka", "kk", "km", "kn", "ko", "ku", "ky",
                       "la", "lb", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl",
                       "no", "ny", "or", "pa", "pl", "ps", "pt", "ro", "ru", "sd", "si", "sk", "sl", "sm", "sn", "so",
                       "sq", "sr", "st", "su", "sv", "sw", "ta", "te", "tg", "th", "tl", "tr", "ug", "uk", "ur", "uz",
                       "vi", "xh", "yi", "yo", "zh", "zu"]
        }
    }
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I translate text from given text/event/job using LibreTranslate Services to translate "
                 "input into the language defined in params.",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": nip90params
    }
    nip89config = NIP89Config()
    nip89config.DTAG = nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                                              nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    return TranslationLibre(name=name, dvm_config=dvm_config, nip89config=nip89config,
                            admin_config=admin_config, options=options)


if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = False
    admin_config.UPDATE_PROFILE = False
    admin_config.LUD16 = ""
    dvm = build_example("Libre Translator", "libre_translator", admin_config)
    dvm.run()

    keep_alive()
