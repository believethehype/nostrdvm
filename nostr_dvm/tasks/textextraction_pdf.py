import json
import os
import re

from nostr_sdk import Kind

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import get_event_by_id

"""
This File contains a Module to extract Text from a PDF file locally on the DVM Machine

Accepted Inputs: Url to pdf file, Event containing an URL to a PDF file
Outputs: Text containing the extracted contents of the PDF file
Params:  None
"""


class TextExtractionPDF(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_EXTRACT_TEXT
    TASK: str = "pdf-to-text"
    FIX_COST: float = 0
    dependencies = [("nostr-dvm", "nostr-dvm"),
                    ("pypdf", "pypdf==3.17.1")]

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "url" and input_type != "event":
                    return False
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
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
            evt = await get_event_by_id(input_content, client=client, config=dvm_config)
            url = re.search("(?P<url>https?://[^\s]+)", evt.content()).group("url")

        options = {
            "url": url,
        }
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        from pypdf import PdfReader
        from pathlib import Path
        import requests

        options = self.set_options(request_form)

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


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I extract text from pdf documents. I only support Latin letters",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {}
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    return TextExtractionPDF(name=name, dvm_config=dvm_config, nip89config=nip89config,
                             admin_config=admin_config)


if __name__ == '__main__':
    process_venv(TextExtractionPDF)
