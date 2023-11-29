import json

import requests

from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config
from utils.nostr_utils import get_referenced_event_by_id, get_event_by_id

"""
This File contains a Module to call Google Translate Services locally on the DVM Machine

Accepted Inputs: Text, Events, Jobs (Text Extraction, Summary, TranslationGoogle)
Outputs: Text containing the TranslationGoogle in the desired language.
Params:  -language The target language
"""


class TranslationLibre(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_TRANSLATE_TEXT
    TASK: str = "translation"
    FIX_COST: float = 0

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)

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

    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None):
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

            confidence = reply["detectedLanguage"]['confidence']
            language = reply["detectedLanguage"]['language']
            print(translated_text + "language: " + language + "conf: " + confidence)
        else:
            return response.text

        return translated_text
