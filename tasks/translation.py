import os

from interfaces.dvmtaskinterface import DVMTaskInterface
from utils import env
from utils.definitions import EventDefinitions
from utils.nip89_utils import NIP89Announcement
from utils.nostr_utils import get_referenced_event_by_id, get_event_by_id


class Translation(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_TRANSLATE_TEXT
    TASK: str = "translation"
    COST: int = 0

    def __init__(self, name, pk):
        self.NAME = name
        self.PK = pk

    def NIP89_announcement(self):
        nip89 = NIP89Announcement()
        nip89.kind = self.KIND
        nip89.pk = self.PK
        nip89.dtag = os.getenv(env.TASK_TRANSLATION_NIP89_DTAG)
        nip89.content = "{\"name\":\"" + self.NAME + "\",\"image\":\"https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg\",\"about\":\"I translate text from given text/event/job, currently using Google Translation Services into language defined in param.  \",\"nip90Params\":{\"language\":{\"required\":true,\"values\":[\"af\",\"am\",\"ar\",\"az\",\"be\",\"bg\",\"bn\",\"bs\",\"ca\",\"ceb\",\"co\",\"cs\",\"cy\",\"da\",\"de\",\"el\",\"eo\",\"es\",\"et\",\"eu\",\"fa\",\"fi\",\"fr\",\"fy\",\"ga\",\"gd\",\"gl\",\"gu\",\"ha\",\"haw\",\"hi\",\"hmn\",\"hr\",\"ht\",\"hu\",\"hy\",\"id\",\"ig\",\"is\",\"it\",\"he\",\"ja\",\"jv\",\"ka\",\"kk\",\"km\",\"kn\",\"ko\",\"ku\",\"ky\",\"la\",\"lb\",\"lo\",\"lt\",\"lv\",\"mg\",\"mi\",\"mk\",\"ml\",\"mn\",\"mr\",\"ms\",\"mt\",\"my\",\"ne\",\"nl\",\"no\",\"ny\",\"or\",\"pa\",\"pl\",\"ps\",\"pt\",\"ro\",\"ru\",\"sd\",\"si\",\"sk\",\"sl\",\"sm\",\"sn\",\"so\",\"sq\",\"sr\",\"st\",\"su\",\"sv\",\"sw\",\"ta\",\"te\",\"tg\",\"th\",\"tl\",\"tr\",\"ug\",\"uk\",\"ur\",\"uz\",\"vi\",\"xh\",\"yi\",\"yo\",\"zh\",\"zu\"]}}}"
        return nip89

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
            for tag in event.tags():
                if tag.as_vec()[0] == 'i':
                    evt = get_event_by_id(tag.as_vec()[1], config=dvm_config)
                    text = evt.content()
                    break

        elif input_type == "text":
            for tag in event.tags():
                if tag.as_vec()[0] == 'i':
                    text = tag.as_vec()[1]
                    break

        elif input_type == "job":
            for tag in event.tags():
                if tag.as_vec()[0] == 'i':
                    evt = get_referenced_event_by_id(tag.as_vec()[1],
                                                     [EventDefinitions.KIND_NIP90_RESULT_EXTRACT_TEXT,
                                                      EventDefinitions.KIND_NIP90_RESULT_SUMMARIZE_TEXT],
                                                     client,
                                                     config=dvm_config)
                    text = evt.content()
                    break

        request_form["optStr"] = ('translation_lang=' + translation_lang + ';text=' +
                                  text.replace('\U0001f919', "").replace("=", "equals").
                                  replace(";", ","))
        return request_form

    def process(self, request_form):
        options = DVMTaskInterface.setOptions(request_form)
        from translatepy.translators.google import GoogleTranslate
        gtranslate = GoogleTranslate()
        length = len(options["text"])

        step = 0
        translated_text = ""
        if length > 4999:
            while step + 5000 < length:
                text_part = options["text"][step:step + 5000]
                step = step + 5000
                try:
                    translated_text_part = str(gtranslate.translate(text_part, options["translation_lang"]))
                    print("Translated Text part:\n\n " + translated_text_part)
                except Exception as e:
                    raise Exception(e)

                translated_text = translated_text + translated_text_part

        if step < length:
            text_part = options["text"][step:length]
            try:
                translated_text_part = str(gtranslate.translate(text_part, options["translation_lang"]))
                print("Translated Text part:\n\n " + translated_text_part)
            except Exception as e:
                raise Exception(e)

            translated_text = translated_text + translated_text_part

        return translated_text
