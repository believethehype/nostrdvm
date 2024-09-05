import json
import os
from datetime import timedelta
from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, Kind, RelayOptions

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions, relay_timeout
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


class AdvancedSearch(DVMTaskInterface):
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
        relay = "wss://relay.nostr.band"

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    search = tag.as_vec()[1]
            elif tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "user":  # check for param type
                    # user = tag.as_vec()[2]
                    users.append(Tag.parse(["p", tag.as_vec()[2]]))
                elif param == "users":  # check for param type
                    users = json.loads(tag.as_vec()[2])
                elif param == "since":  # check for param type
                    since_seconds = int(tag.as_vec()[2])
                elif param == "until":  # check for param type
                    until_seconds = min(int(tag.as_vec()[2]), until_seconds)
                elif param == "max_results":  # check for param type
                    max_results = int(tag.as_vec()[2])

        options = {
            "search": search,
            "users": users,
            "since": since_seconds,
            "until": until_seconds,
            "max_results": max_results,
            "relay": relay
        }
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        from nostr_sdk import Filter
        options = self.set_options(request_form)

        opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT)))
        sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        signer = NostrSigner.keys(keys)
        cli = Client.with_opts(signer, opts)

        ropts = RelayOptions().ping(False)
        await cli.add_relay_with_opts(options["relay"], ropts)

        await cli.connect()

        # earch_since_seconds = int(options["since"]) * 24 * 60 * 60
        # dif = Timestamp.now().as_secs() - search_since_seconds
        # search_since = Timestamp.from_secs(dif)
        search_since = Timestamp.from_secs(int(options["since"]))

        # search_until_seconds = int(options["until"]) * 24 * 60 * 60
        # dif = Timestamp.now().as_secs() - search_until_seconds
        # search_until = Timestamp.from_secs(dif)
        search_until = Timestamp.from_secs(int(options["until"]))
        userkeys = []
        for user in options["users"]:
            tag = Tag.parse(user)
            user = tag.as_vec()[1]
            # user = user[1]
            user = str(user).lstrip("@")
            if str(user).startswith('npub'):
                userkey = PublicKey.from_bech32(user)
            elif str(user).startswith("nostr:npub"):
                userkey = PublicKey.from_nostr_uri(user)
            else:
                userkey = PublicKey.from_hex(user)

            userkeys.append(userkey)

        if not options["users"]:
            notes_filter = Filter().kind(Kind(1)).search(options["search"]).since(search_since).until(
                search_until).limit(options["max_results"])
        elif options["search"] == "":
            notes_filter = Filter().kind(Kind(1)).authors(userkeys).since(search_since).until(
                search_until).limit(options["max_results"])
        else:
            notes_filter = Filter().kind(Kind(1)).authors(userkeys).search(options["search"]).since(
                search_since).until(search_until).limit(options["max_results"])

        events = await cli.get_events_of([notes_filter], relay_timeout)

        result_list = []
        if len(events) > 0:

            for event in events:
                e_tag = Tag.parse(["e", event.id().to_hex()])
                result_list.append(e_tag.as_vec())

        await cli.shutdown()
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
        "image": "https://nostr.band/android-chrome-192x192.png",
        "about": "I search notes on Nostr.band.",
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
                "description": "A unix timestamp in the past from where the search should start"
            },
            "until": {
                "required": False,
                "values": [],
                "description": "A unix timestamp that tells until the search should include results"
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

    options = {"relay": "wss://relay.nostr.band"}

    return AdvancedSearch(name=name, dvm_config=dvm_config, nip89config=nip89config,
                          admin_config=admin_config, options=options)


if __name__ == '__main__':
    process_venv(AdvancedSearch)
