import json
import os
import re
from datetime import timedelta
from pathlib import Path
from threading import Thread

import dotenv
from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, Alphabet, SecretKey, Event

from interfaces.dvmtaskinterface import DVMTaskInterface

from utils.admin_utils import AdminConfig
from utils.backend_utils import keep_alive
from utils.definitions import EventDefinitions
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import NIP89Config, check_and_set_d_tag
from utils.nostr_utils import get_event_by_id, check_and_set_private_key
from utils.output_utils import post_process_list_to_users, post_process_list_to_events
from utils.zap_utils import check_and_set_ln_bits_keys

"""
This File contains a Module to search for notes
Accepted Inputs: a search query
Outputs: A list of events 
Params:  None
"""


class TrendingNotesNostrBand(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY
    TASK: str = "trending-content"
    FIX_COST: float = 0
    dvm_config: DVMConfig

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        super().__init__(name, dvm_config, nip89config, admin_config, options)

    def is_input_supported(self, tags):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "text":
                    return False
        return True

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        self.dvm_config = dvm_config
        print(self.dvm_config.PRIVATE_KEY)

        request_form = {"jobID": event.id().to_hex()}

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]

        options = {

        }
        request_form['options'] = json.dumps(options)
        return request_form

    def process(self, request_form):
        from nostr_sdk import Filter
        options = DVMTaskInterface.set_options(request_form)

        import requests

        url = "https://api.nostr.band/v0/trending/notes"
        try:
            response = requests.get(url)
            response_json = response.json()
            result_list = []
            i = 0
            if len(response_json["notes"]) > 0:
                for note in response_json["notes"]:
                    i += 1
                    if i < 20:
                        e_tag = Tag.parse(["e", note["id"]])
                        print(e_tag.as_vec())
                        result_list.append(e_tag.as_vec())
                    else:
                        break

            return json.dumps(result_list)

        except:
            return "error"





    def post_process(self, result, event):
        """Overwrite the interface function to return a social client readable format, if requested"""
        for tag in event.tags():
            if tag.as_vec()[0] == 'output':
                format = tag.as_vec()[1]
                if format == "text/plain":  # check for output type
                    result = post_process_list_to_events(result)

        # if not text/plain, don't post-process
        return result


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    npub = Keys.from_sk_str(dvm_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, user_id, lnaddress = check_and_set_ln_bits_keys(identifier, npub)
    dvm_config.LNBITS_INVOICE_KEY = invoice_key
    dvm_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    admin_config.LUD16 = lnaddress
    # Add NIP89
    nip90params = {
    }
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I show trending notes from nostr.band",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": nip90params
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY,
                                                              nip89info["image"])

    nip89config.CONTENT = json.dumps(nip89info)
    return TrendingNotesNostrBand(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                   admin_config=admin_config)


if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = False
    admin_config.UPDATE_PROFILE = False

    dvm = build_example("Trending Notes on Nostr.band", "trending_notes_nostrband", admin_config)
    dvm.run()

    keep_alive()
