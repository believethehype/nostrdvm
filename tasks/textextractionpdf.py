import json
import os
import re
from threading import Thread

from dvm import DVM
from interfaces.dvmtaskinterface import DVMTaskInterface
from utils.admin_utils import AdminConfig
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nostr_utils import get_event_by_id

"""
This File contains a Module to extract Text from a PDF file locally on the DVM Machine

Accepted Inputs: Url to pdf file, Event containing an URL to a PDF file
Outputs: Text containing the extracted contents of the PDF file
Params:  None
"""


class TextExtractionPDF(DVMTaskInterface):
    NAME: str = ""
    KIND: int = EventDefinitions.KIND_NIP90_EXTRACT_TEXT
    TASK: str = "pdf-to-text"
    COST: int = 0
    PK: str

    def __init__(self, name, dvm_config: DVMConfig, admin_config: AdminConfig = None):
        self.NAME = name
        dvm_config.SUPPORTED_TASKS = [self]
        dvm_config.DB = "db/" + self.NAME + ".db"
        self.PK = dvm_config.PRIVATE_KEY

        dvm = DVM
        nostr_dvm_thread = Thread(target=dvm, args=[dvm_config, admin_config])
        nostr_dvm_thread.start()

    def is_input_supported(self, input_type, input_content):
        if input_type != "url" and input_type != "event":
            return False
        return True

    def create_request_form_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex()}

        # default values
        input_type = "url"
        input_content = ""
        url = ""

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                input_content = tag.as_vec()[1]

        if input_type == "url":
            url = input_content
        # if event contains url to pdf, we checked for a pdf link before
        elif input_type == "event":
            evt = get_event_by_id(input_content, client=client, config=dvm_config)
            url = re.search("(?P<url>https?://[^\s]+)", evt.content()).group("url")

        options = {
            "url": url,
        }
        request_form['options'] = json.dumps(options)
        return request_form

    def process(self, request_form):
        from pypdf import PdfReader
        from pathlib import Path
        import requests

        options = DVMTaskInterface.set_options(request_form)

        try:
            file_path = Path('temp.pdf')
            response = requests.get(options["url"])
            file_path.write_bytes(response.content)
            reader = PdfReader(file_path)
            number_of_pages = len(reader.pages)
            text = ""
            for page_num in range(number_of_pages):
                page = reader.pages[page_num]
                text = text + page.extract_text()

            os.remove('temp.pdf')
            return text
        except Exception as e:
            raise Exception(e)
