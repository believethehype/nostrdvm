import json
from threading import Thread

from dvm import DVM
from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config
from utils.nostr_utils import get_referenced_event_by_id, get_event_by_id

"""
This File contains a Module to call Google Translate Services locally on the DVM Machine

Accepted Inputs: Text, Events, Jobs (Text Extraction, Summary, Translation)
Outputs: Text containing the Translation in the desired language.
Params:  -language The target language
"""


class Translation(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_TRANSLATE_TEXT
    TASK: str = "translation"
    COST: int = 0

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)

    def is_input_supported(self, input_type, input_content):
        if input_type != "event" and input_type != "job" and input_type != "text":
            return False
        if input_type != "text" and len(input_content) > 4999:
            return False
        return True

    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex()}

        input_type = "event"
        text = ""
        translation_lang = "en"

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]

            elif tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "language":  # check for param type
                    translation_lang = str(tag.as_vec()[2]).split('-')[0]

        if input_type == "event":
            for tag in event.tags:
                if tag.as_vec()[0] == 'i':
                    evt = get_event_by_id(tag.as_vec()[1], client=client, config=dvm_config)
                    text = evt.content()
                    break

        elif input_type == "text":
            for tag in event.tags:
                if tag.as_vec()[0] == 'i':
                    text = tag.as_vec()[1]
                    break

        elif input_type == "job":
            for tag in event.tags:
                if tag.as_vec()[0] == 'i':
                    evt = get_referenced_event_by_id(event_id=tag.as_vec()[1], client=client,
                                                     kinds=[EventDefinitions.KIND_NIP90_RESULT_EXTRACT_TEXT,
                                                            EventDefinitions.KIND_NIP90_RESULT_SUMMARIZE_TEXT,
                                                            EventDefinitions.KIND_NIP90_RESULT_TRANSLATE_TEXT],
                                                     dvm_config=dvm_config)
                    text = evt.content()
                    break

        options = {
            "text": text,
            "language": translation_lang
        }
        request_form['options'] = json.dumps(options)

        return request_form

    def process(self, request_form):
        from translatepy.translators.google import GoogleTranslate

        options = DVMTaskInterface.set_options(request_form)
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
