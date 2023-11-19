import os
from typing import re

from utils import env
from utils.definitions import EventDefinitions
from utils.nip89_utils import NIP89Announcement
from utils.nostr_utils import get_event_by_id, get_referenced_event_by_id


class TextExtractionPDF:
    TASK: str = "pdf-to-text"
    COST: int = 20

    @staticmethod
    def NIP89_announcement():
        nip89 = NIP89Announcement()
        nip89.kind = EventDefinitions.KIND_NIP90_TRANSLATE_TEXT
        nip89.dtag = os.getenv(env.TASK_TRANSLATION_NIP89_DTAG)
        nip89.pk = os.getenv(env.NOSTR_PRIVATE_KEY)
        nip89.content = "{\"name\":\"Translator\",\"image\":\"https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg\",\"about\":\"I translate text from given text/event/job, currently using Google Translation Services into language defined in param.  \",\"nip90Params\":{\"language\":{\"required\":true,\"values\":[\"af\",\"am\",\"ar\",\"az\",\"be\",\"bg\",\"bn\",\"bs\",\"ca\",\"ceb\",\"co\",\"cs\",\"cy\",\"da\",\"de\",\"el\",\"eo\",\"es\",\"et\",\"eu\",\"fa\",\"fi\",\"fr\",\"fy\",\"ga\",\"gd\",\"gl\",\"gu\",\"ha\",\"haw\",\"hi\",\"hmn\",\"hr\",\"ht\",\"hu\",\"hy\",\"id\",\"ig\",\"is\",\"it\",\"he\",\"ja\",\"jv\",\"ka\",\"kk\",\"km\",\"kn\",\"ko\",\"ku\",\"ky\",\"la\",\"lb\",\"lo\",\"lt\",\"lv\",\"mg\",\"mi\",\"mk\",\"ml\",\"mn\",\"mr\",\"ms\",\"mt\",\"my\",\"ne\",\"nl\",\"no\",\"ny\",\"or\",\"pa\",\"pl\",\"ps\",\"pt\",\"ro\",\"ru\",\"sd\",\"si\",\"sk\",\"sl\",\"sm\",\"sn\",\"so\",\"sq\",\"sr\",\"st\",\"su\",\"sv\",\"sw\",\"ta\",\"te\",\"tg\",\"th\",\"tl\",\"tr\",\"ug\",\"uk\",\"ur\",\"uz\",\"vi\",\"xh\",\"yi\",\"yo\",\"zh\",\"zu\"]}}}"
        return nip89


    @staticmethod
    def is_input_supported(input_type, input_content):
        if input_type != "url":
            return False
        return True

    @staticmethod
    def create_requestform_from_nostr_event(event, client=None, dvmconfig=None):
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
            evt = get_event_by_id(input_content, config=dvmconfig)
            url = re.search("(?P<url>https?://[^\s]+)", evt.content()).group("url")
        elif input_type == "job":
            evt = get_referenced_event_by_id(input_content, [EventDefinitions.KIND_NIP90_RESULT_GENERATE_IMAGE],
                                             client, config=dvmconfig)

            url = re.search("(?P<url>https?://[^\s]+)", evt.content()).group("url")

        request_form["optStr"] = 'url=' + url
        return request_form

    @staticmethod
    def process(options):
        from pypdf import PdfReader
        from pathlib import Path
        import requests
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
