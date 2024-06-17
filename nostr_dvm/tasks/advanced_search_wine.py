import json
import os
from datetime import timedelta

import requests
from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, Event, Kind

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import post_process_list_to_events

"""
This File contains a Module to search for notes
Accepted Inputs: a search query
Outputs: A list of events 
Params:  None
"""


class AdvancedSearchWine(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_CONTENT_SEARCH
    TASK: str = "search-content"
    FIX_COST: float = 0
    dvm_config: DVMConfig

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "text":
                    return False
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        self.dvm_config = dvm_config
        print(self.dvm_config.PRIVATE_KEY)

        request_form = {"jobID": event.id().to_hex()}

        # default values
        user = ""
        users = []
        since_seconds = Timestamp.now().as_secs() - (365 * 24 * 60 * 60)
        until_seconds = Timestamp.now().as_secs()
        search = ""
        max_results = 100

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    search = tag.as_vec()[1]
            elif tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "user":  # check for param type
                    user = tag.as_vec()[2]
                elif param == "users":  # check for param type
                    users = json.loads(tag.as_vec()[2])
                elif param == "since":  # check for param type
                    since_seconds = int(tag.as_vec()[2])
                elif param == "until":  # check for param type
                    until_seconds = int(tag.as_vec()[2])
                elif param == "max_results":  # check for param type
                    max_results = int(tag.as_vec()[2])

        options = {
            "search": search,
            "user": user,
            "users": users,
            "since": since_seconds,
            "until": until_seconds,
            "max_results": max_results,

        }
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        from nostr_sdk import Filter
        options = self.set_options(request_form)
        userkeys = []
        for user in options["users"]:
            tag = Tag.parse(user)
            user = tag.as_vec()[1]
            user = str(user).lstrip("@")
            if str(user).startswith('npub'):
                userkey = PublicKey.from_bech32(user)
            elif str(user).startswith("nostr:npub"):
                userkey = PublicKey.from_nostr_uri(user)
            else:
                userkey = PublicKey.from_hex(user)

            userkeys.append(userkey)

        print("Sending job to nostr.wine API")
        if options["users"]:
            url = ('https://api.nostr.wine/search?query=' + options["search"] + '&kind=1' + '&pubkey=' +
                   options["users"][0][1] + "&limit=100" + "&sort=time" + "&until=" + str(
                        options["until"]) + "&since=" + str(options["since"]))
        else:
            url = ('https://api.nostr.wine/search?query=' + options[
                "search"] + '&kind=1' + "&limit=100" + "&sort=time" + "&until=" + str(
                options["until"]) + "&since=" + str(options["since"]))

        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        response = requests.get(url, headers=headers)
        # print(response.text)
        result_list = []
        try:
            ob = json.loads(response.text)
            data = ob['data']
            for el in data:
                try:
                    e_tag = Tag.parse(["e", el['id']])
                    result_list.append(e_tag.as_vec())
                except Exception as e:
                    print("ERROR: " + str(e))
        except Exception as e:
            print(e)

        return json.dumps(result_list)

    async def post_process(self, result, event):
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
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/d844d6a963724b9f9deb6b3326984fd95352343336718812424d5e99d93a6f2d.jpg",
        "about": "I search notes on nostr.wine using the nostr-wine API",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "users": {
                "required": False,
                "values": [],
                "description": "Search for content from specific users"
            },
            "since": {
                "required": False,
                "values": [],
                "description": "The number of days in the past from now the search should include"
            },
            "until": {
                "required": False,
                "values": [],
                "description": "The number of days in the past from now the search should include up to"
            },
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 20)"
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return AdvancedSearchWine(name=name, dvm_config=dvm_config, nip89config=nip89config,
                              admin_config=admin_config)


if __name__ == '__main__':
    process_venv(AdvancedSearchWine)
