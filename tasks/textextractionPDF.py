import os
import re

from interfaces.dvmtaskinterface import DVMTaskInterface
from utils import env
from utils.definitions import EventDefinitions
from utils.nip89_utils import NIP89Announcement
from utils.nostr_utils import get_event_by_id, get_referenced_event_by_id


class TextExtractionPDF(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_EXTRACT_TEXT
    TASK: str = "pdf-to-text"
    COST: int = 20

    def __init__(self, name, pk):
        self.NAME = name
        self.PK = pk

    def NIP89_announcement(self):
        nip89 = NIP89Announcement()
        nip89.kind = self.KIND
        nip89.pk = self.PK
        nip89.dtag = os.getenv(env.TASK_TEXTEXTRACTION_NIP89_DTAG)
        nip89.content = "{\"name\":\"" + self.NAME + "\",\"image\":\"https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg\",\"about\":\"I extract Text from pdf documents\",\"nip90Params\":{}}"
        return nip89

    def is_input_supported(self, input_type, input_content):
        if input_type != "url":
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
        elif input_type == "event":
            evt = get_event_by_id(input_content, config=dvm_config)
            url = re.search("(?P<url>https?://[^\s]+)", evt.content()).group("url")
        elif input_type == "job":
            evt = get_referenced_event_by_id(input_content, [EventDefinitions.KIND_NIP90_RESULT_GENERATE_IMAGE],
                                             client, config=dvm_config)

            url = re.search("(?P<url>https?://[^\s]+)", evt.content()).group("url")

        request_form["optStr"] = 'url=' + url
        return request_form

    def process(self, request_form):
        options = DVMTaskInterface.setOptions(request_form)
        from pypdf import PdfReader
        from pathlib import Path
        import requests
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