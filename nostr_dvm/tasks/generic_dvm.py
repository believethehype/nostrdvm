import json
import os
from datetime import timedelta
from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, Kind, RelayOptions

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import post_process_list_to_events

"""
This File contains a Generic DVM that can be overwritten by the user
Accepted Inputs: None
Outputs: Text
Params:  None
"""


class GenericDVM(DVMTaskInterface):
    KIND: Kind = Kind(5000)
    TASK: str = "generic"
    FIX_COST: float = 0
    dvm_config: DVMConfig
    options = {}

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)
        if dvm_config.KIND is not None:
            self.KIND = dvm_config.KIND

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        self.dvm_config = dvm_config
        print(self.dvm_config.PRIVATE_KEY)
        prompt = ""
        user = event.author().to_hex()
        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    prompt = tag.as_vec()[1]
            elif tag.as_vec()[0] == 'param':
                if tag.as_vec()[1] == 'user':
                    user = tag.as_vec()[2]

        request_form = {"jobID": event.id().to_hex()}

        self.options["user"] = user
        self.options["request_event_id"] = event.id().to_hex()
        self.options["request_event_author"] = event.author().to_hex()
        if prompt != "":
            self.options["input"] = prompt
        request_form['options'] = json.dumps(self.options)
        return request_form

    async def process(self, request_form):
        options = self.set_options(request_form)
        result = "I'm manipulating the DVM from my inside function\n"
        result += options["some_option"]
        print(result)
        return result


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config,  announce = False):

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = announce
    admin_config.REBROADCAST_NIP65_RELAY_LIST = announce
    admin_config.UPDATE_PROFILE = announce

    name = "Generic DVM"
    identifier = "a_very_generic_dvm"  # Chose a unique identifier in order to get a lnaddress
    dvm_config = build_default_config(identifier)
    dvm_config.KIND = Kind(5050)  # Manually set the Kind Number (see data-vending-machines.org)

    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/28da676a19841dcfa7dcf7124be6816842d14b84f6046462d2a3f1268fe58d03.png",
        "about": "I'm an all purpose DVM'",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    options = {
        "some_option": "#RunDVM",
    }

    dvm = GenericDVM(name=name, dvm_config=dvm_config, nip89config=nip89config,
                     admin_config=admin_config, options=options)

    async def process(request_form):
        options = dvm.set_options(request_form)
        result = "I'm manipulating the DVM from outside\n"
        result += options["some_option"]
        print(result)
        return result

    dvm.process = process  # overwrite the process function with the above one
    return dvm


if __name__ == '__main__':
    process_venv(GenericDVM)
