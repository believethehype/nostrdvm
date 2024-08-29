import json
import os
import re

from nostr_sdk import Tag, Kind
from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import get_referenced_event_by_id, get_events_by_ids, get_event_by_id

"""
This File contains a Module to generate Text, based on a prompt using the Unleashed.chat API.

Accepted Inputs: Prompt (text)
Outputs: Generated text
"""


class SummarizationDuckDuck(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_SUMMARIZE_TEXT
    TASK: str = "text-to-text"
    FIX_COST: float = 10
    dependencies = [("nostr-dvm", "nostr-dvm"),
                    ("duck_chat", "-U https://github.com/mrgick/duckduckgo-chat-ai/archive/master.zip")]

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                print(tag.as_vec())
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "event" and input_type != "job" and input_type != "text":
                    return False

        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex() + "_" + self.NAME.replace(" ", "")}
        prompt = ""
        collect_events = []
        nostr_mode = True

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt += tag.as_vec()[1] + "\n"
                elif input_type == "event":
                    collect_events.append(tag.as_vec()[1])
                    # evt = get_event_by_id(tag.as_vec()[1], client=client, config=dvm_config)
                    # prompt += evt.content() + "\n"
                elif input_type == "job":
                    evt = await get_referenced_event_by_id(event_id=tag.as_vec()[1], client=client,
                                                     kinds=[EventDefinitions.KIND_NIP90_RESULT_EXTRACT_TEXT,
                                                            EventDefinitions.KIND_NIP90_RESULT_SUMMARIZE_TEXT,
                                                            EventDefinitions.KIND_NIP90_RESULT_TRANSLATE_TEXT,
                                                            EventDefinitions.KIND_NIP90_RESULT_CONTENT_DISCOVERY],
                                                     dvm_config=dvm_config)
                    if evt is None:
                        print("Event not found")
                        raise Exception

                    if evt.kind() == EventDefinitions.KIND_NIP90_RESULT_CONTENT_DISCOVERY:
                        result_list = json.loads(evt.content())
                        prompt = ""
                        for tag in result_list:
                            e_tag = Tag.parse(tag)
                            evt = await get_event_by_id(e_tag.as_vec()[1], client=client, config=dvm_config)
                            prompt += evt.content() + "\n"

                    else:
                        prompt = evt.content()

        evts = await get_events_by_ids(collect_events, client=client, config=dvm_config)
        if evts is not None:
            for evt in evts:
                prompt += evt.content() + "\n"

        clean_prompt = re.sub(r'^https?:\/\/.*[\r\n]*', '', prompt, flags=re.MULTILINE)
        options = {
            "input": clean_prompt[:4000],
            "nostr": nostr_mode,
        }
        request_form['options'] = json.dumps(options)

        return request_form

    async def process(self, request_form):
        from duck_chat import DuckChat
        from duck_chat import ModelType

        options = self.set_options(request_form)
        try:
            async with DuckChat(model=ModelType.GPT4o) as chat:
                query = "Summarize the following notes by different authors: " + options["input"]
                result = await chat.ask_question(query)
                print(result)
                return result

        except Exception as e:
            print("Error in Module: " + str(e))
            raise Exception(e)



# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    dvm_config.SEND_FEEDBACK_EVENTS = True
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I summarize Text",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {}
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)
    admin_config2 = AdminConfig()
    admin_config2.REBROADCAST_NIP89 = False

    return SummarizationDuckDuck(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                      admin_config=admin_config2)


if __name__ == '__main__':
    process_venv(SummarizationDuckDuck)
