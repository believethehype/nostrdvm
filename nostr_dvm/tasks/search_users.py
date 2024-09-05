import json
import os
from datetime import timedelta
from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, NostrDatabase, \
    ClientBuilder, Filter, NegentropyOptions, NegentropyDirection, init_logger, LogLevel, Kind

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import post_process_list_to_events, post_process_list_to_users

"""
This File contains a Module to search for notes
Accepted Inputs: a search query
Outputs: A list of events 
Params:  None
"""


class SearchUser(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_USER_SEARCH
    TASK: str = "search-user"
    FIX_COST: float = 0
    dvm_config: DVMConfig
    last_schedule: int = 0
    db_name = "db/nostr_profiles.db"
    relay = "wss://profiles.nostr1.com"



    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)
        if self.options.get("relay"):
            self.relay = self.options['relay']
        await self.sync_db()

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
        search = ""
        max_results = 100

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
                if input_type == "text":
                    search = tag.as_vec()[1]
            elif tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "max_results":  # check for param type
                    max_results = int(tag.as_vec()[2])

        options = {
            "search": search,
            "max_results": max_results,
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

        database = await NostrDatabase.sqlite(self.db_name)
        cli = ClientBuilder().database(database).signer(signer).opts(opts).build()

        await cli.add_relay(self.relay)
        # cli.add_relay("wss://atl.purplerelay.com")
        await cli.connect()

        # Negentropy reconciliation

        # Query events from database

        filter1 = Filter().kind(Kind(0))
        events = await cli.database().query([filter1])

        result_list = []
        print("Events: " + str(len(events)))
        index = 0
        if len(events) > 0:

            for event in events:
                if index < options["max_results"]:
                    try:
                        if options["search"].lower() in event.content().lower():
                            p_tag = Tag.parse(["p", event.author().to_hex()])
                            print(event.as_json())
                            result_list.append(p_tag.as_vec())
                            index += 1
                    except Exception as exp:
                        print(str(exp) + " " + event.author().to_hex())
                else:
                    break

        await cli.shutdown()
        return json.dumps(result_list)

    async def post_process(self, result, event):
        """Overwrite the interface function to return a social client readable format, if requested"""
        for tag in event.tags():
            if tag.as_vec()[0] == 'output':
                format = tag.as_vec()[1]
                if format == "text/plain":  # check for output type
                    result = post_process_list_to_users(result)

        # if not text/plain, don't post-process
        return result

    async def schedule(self, dvm_config):
        if dvm_config.SCHEDULE_UPDATES_SECONDS == 0:
            return 0
        else:
            if Timestamp.now().as_secs() >= self.last_schedule + dvm_config.SCHEDULE_UPDATES_SECONDS:
                await self.sync_db()
                self.last_schedule = Timestamp.now().as_secs()
                return 1

    async def sync_db(self):
        opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT)))
        sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        signer = NostrSigner.keys(keys)
        database = await NostrDatabase.sqlite(self.db_name)
        cli = ClientBuilder().signer(signer).database(database).opts(opts).build()

        await cli.add_relay(self.relay)
        await cli.connect()

        filter1 = Filter().kind(Kind(0))

        # filter = Filter().author(keys.public_key())
        print("Syncing Profile Database.. this might take a while..")
        dbopts = NegentropyOptions().direction(NegentropyDirection.DOWN)
        await cli.reconcile(filter1, dbopts)
        print("Done Syncing Profile Database.")
        await cli.shutdown()


# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = 600  # Every 10 seconds
    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/a99ab925084029d9468fef8330ff3d9be2cf67da473b024f2a6d48b5cd77197f.jpg",
        "about": "I search users.",
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

    options = {"relay": "wss://profiles.nostr1.com"}

    return SearchUser(name=name, dvm_config=dvm_config, nip89config=nip89config,
                      admin_config=admin_config, options=options)


if __name__ == '__main__':
    process_venv(SearchUser)
