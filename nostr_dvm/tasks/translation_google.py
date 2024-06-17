import json
import os

from nostr_sdk import Kind

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import get_referenced_event_by_id, get_event_by_id

"""
This File contains a Module to call Google Translate Services on the DVM Machine

Accepted Inputs: Text, Events, Jobs (Text Extraction, Summary, Translation)
Outputs: Text containing the TranslationGoogle in the desired language.
Params:  -language The target language
"""


class TranslationGoogle(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_TRANSLATE_TEXT
    TASK: str = "translation"
    FIX_COST: float = 0
    dependencies = [("nostr-dvm", "nostr-dvm"),
                    ("translatepy", "translatepy==2.3")]

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
        from translatepy.translators.google import GoogleTranslate

        options = self.set_options(request_form)
        gtranslate = GoogleTranslate()
        length = len(options["text"])

        step = 0
        translated_text = ""
        if length > 4999:
            while step + 5000 < length:
                text_part = options["text"][step:step + 5000]
                step = step + 5000
                try:
                    translated_text_part = str(gtranslate.translate(text_part, options["language"]))
                    print("Translated Text part:\n\n " + translated_text_part)
                except Exception as e:
                    raise Exception(e)

                translated_text = translated_text + translated_text_part

        if step < length:
            text_part = options["text"][step:length]
            try:
                translated_text_part = str(gtranslate.translate(text_part, options["language"]))
                print("Translated Text part:\n " + translated_text_part)
            except Exception as e:
                raise Exception(e)

            translated_text = translated_text + translated_text_part

        return translated_text


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I translate text from given text/event/job. Currently using Google TranslationGoogle Services to translate "
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

    return TranslationGoogle(name=name, dvm_config=dvm_config, nip89config=nip89config, admin_config=admin_config)


if __name__ == '__main__':
    process_venv(TranslationGoogle)
