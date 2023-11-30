import json

from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config
from utils.mediasource_utils import organize_input_media_data
from utils.output_utils import upload_media_to_hoster

"""
This File contains a Module to call Google Translate Services locally on the DVM Machine

Accepted Inputs: Text, Events, Jobs (Text Extraction, Summary, Translation)
Outputs: Text containing the TranslationGoogle in the desired language.
Params:  -language The target language
"""


class MediaConverter(DVMTaskInterface):
    KIND = EventDefinitions.KIND_NIP90_CONVERT_VIDEO
    TASK = "convert"
    FIX_COST = 20
    PER_UNIT_COST = 0.1

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)

    def is_input_supported(self, tags):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "url":
                    return False
        return True

    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex()}
        url = ""
        media_format = "video/mp4"
        input_type = "text"
        start_time = 0
        end_time = 0
        # TODO parse start/end parameters

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "url":
                    url = tag.as_vec()[1]


            elif tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "format":  # check for param type
                    media_format = tag.as_vec()[2]

        filepath = organize_input_media_data(url, input_type, start_time, end_time, dvm_config, client, True, media_format)
        options = {
            "filepath": filepath
        }

        request_form['options'] = json.dumps(options)
        return request_form

    def process(self, request_form):
        options = DVMTaskInterface.set_options(request_form)
        url = upload_media_to_hoster(options["filepath"])

        return url
