import json
import os
import requests
from nostr_sdk import Kind

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import get_referenced_event_by_id, get_event_by_id

"""
This File contains a Module to call Libre Translate Services

Accepted Inputs: Text, Events, Jobs (Text Extraction, Summary, Translation)
Outputs: Text containing the Translation with LibreTranslation in the desired language.
Params:  -language The target language

Requires API key or self-hosted instance
"""


class TranslationLibre(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_TRANSLATE_TEXT
    TASK: str = "translation"
    FIX_COST: float = 0

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "event" and input_type != "job" and input_type != "text":
                    return False
                if input_type != "text" and len(input_value) > 4999:
                    return False
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex()}
        text = ""
        translation_lang = "en"

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "event":
                    evt = await get_event_by_id(tag.as_vec()[1], client=client, config=dvm_config)
                    text = evt.content()
                elif input_type == "text":
                    text = tag.as_vec()[1]
                elif input_type == "job":
                    evt = await get_referenced_event_by_id(event_id=tag.as_vec()[1], client=client,
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

    async def process(self, request_form):
        options = self.set_options(request_form)
        request = {
            "q": options["text"],
            "relay_timeout": "auto",
            "target": options["language"]
        }
        if options["libre_api_key"] != "":
            request["api_key"] = options["libre_api_key"]

        data = json.dumps(request)

        headers = {'Content-type': 'application/json'}
        response = requests.post(options["libre_end_point"] + "/translate", headers=headers, data=data)
        reply = json.loads(response.text)
        if reply.get("translatedText"):
            translated_text = reply['translatedText']
            # untested
            # confidence = reply["detectedLanguage"]['confidence']
            # language = reply["detectedLanguage"]['language']
            # print(translated_text + "language: " + language + "conf: " + confidence)
        else:
            return response.text

        return translated_text


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    options = {'libre_end_point': os.getenv("LIBRE_TRANSLATE_ENDPOINT"),
               'libre_api_key': os.getenv("LIBRE_TRANSLATE_API_KEY")}

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I translate text from given text/event/job using LibreTranslate Services to translate "
                 "input into the language defined in params.",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "language": {
                "required": False,
                "values": ["en", "az", "be", "bg", "bn", "bs", "ca", "ceb", "co", "cs", "cy", "da", "de", "el", "eo",
                           "es",
                           "et", "eu", "fa", "fi", "fr", "fy", "ga", "gd", "gl", "gu", "ha", "haw", "hi", "hmn", "hr",
                           "ht",
                           "hu", "hy", "id", "ig", "is", "it", "he", "ja", "jv", "ka", "kk", "km", "kn", "ko", "ku",
                           "ky",
                           "la", "lb", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne",
                           "nl",
                           "no", "ny", "or", "pa", "pl", "ps", "pt", "ro", "ru", "sd", "si", "sk", "sl", "sm", "sn",
                           "so",
                           "sq", "sr", "st", "su", "sv", "sw", "ta", "te", "tg", "th", "tl", "tr", "ug", "uk", "ur",
                           "uz",
                           "vi", "xh", "yi", "yo", "zh", "zu"]
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return TranslationLibre(name=name, dvm_config=dvm_config, nip89config=nip89config,
                            admin_config=admin_config, options=options)



if __name__ == '__main__':
    process_venv(TranslationLibre)
