import json
import os
from datetime import timedelta
from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, NostrDatabase, \
    ClientBuilder, Filter, NegentropyOptions, NegentropyDirection, init_logger, LogLevel, Event, EventId

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import post_process_list_to_events, post_process_list_to_users

"""
This File contains a Module to search for notes
Accepted Inputs: a search query
Outputs: A list of events 
Params:  None
"""


class SearchUser(DVMTaskInterface):
    KIND: int = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY
    TASK: str = "discover-content"
    FIX_COST: float = 0
    dvm_config: DVMConfig
    last_schedule: int

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config,
                 admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)
        self.last_schedule = Timestamp.now().as_secs()

        use_logger = False
        if use_logger:
            init_logger(LogLevel.DEBUG)

        super().__init__(name, dvm_config, nip89config, admin_config, options)

        self.sync_db()

    def is_input_supported(self, tags, client=None, dvm_config=None):
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

        # default values
        search = ""
        max_results = 100

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
            elif tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "max_results":  # check for param type
                    max_results = int(tag.as_vec()[2])

        options = {
            "max_results": max_results,
        }
        request_form['options'] = json.dumps(options)
        return request_form

    def process(self, request_form):
        from nostr_sdk import Filter
        from types import SimpleNamespace
        ns = SimpleNamespace()

        options = DVMTaskInterface.set_options(request_form)

        opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT)))
        sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        signer = NostrSigner.keys(keys)

        database = NostrDatabase.sqlite("db/nostr_recent_notes.db")
        cli = ClientBuilder().database(database).signer(signer).opts(opts).build()

        cli.add_relay("wss://relay.damus.io")
        # cli.add_relay("wss://atl.purplerelay.com")
        cli.connect()

        # Negentropy reconciliation

        # Query events from database
        timestamp_hour_ago = Timestamp.now().as_secs() - 3600
        lasthour = Timestamp.from_secs(timestamp_hour_ago)
        filter1 = Filter().kind(1).since(lasthour)
        events = cli.database().query([filter1])
        ns.finallist = {}
        for event in events:
            ns.finallist[event.id().to_hex()] = 0
            filt = Filter().kinds([9735, 7, 1]).event(event.id()).since(lasthour)
            reactions = cli.database().query([filt])
            ns.finallist[event.id().to_hex()] = len(reactions)

        # for event in events:
        #    print(event.as_json())

        # events = cli.get_events_of([notes_filter], timedelta(seconds=5))
        result_list = []
        finallist_sorted = sorted(ns.finallist.items(), key=lambda x: x[1], reverse=True)[:int(options["max_results"])]
        for entry in finallist_sorted:
            print(EventId.parse(entry[0]).to_bech32() + "/" + EventId.parse(entry[0]).to_hex() + ": " + str(entry[1]))
            e_tag = Tag.parse(["e", entry[0]])
            result_list.append(e_tag.as_vec())

        return json.dumps(result_list)

    def post_process(self, result, event):
        """Overwrite the interface function to return a social client readable format, if requested"""
        for tag in event.tags():
            if tag.as_vec()[0] == 'output':
                format = tag.as_vec()[1]
                if format == "text/plain":  # check for output type
                    result = post_process_list_to_users(result)

        # if not text/plain, don't post-process
        return result

    def schedule(self, dvm_config):
        if dvm_config.SCHEDULE_UPDATES_SECONDS == 0:
            return 0
        else:
            if Timestamp.now().as_secs() >= self.last_schedule + dvm_config.SCHEDULE_UPDATES_SECONDS:
                self.sync_db()
                self.last_schedule = Timestamp.now().as_secs()
                return 1

    def sync_db(self):
        opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT)))
        sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        signer = NostrSigner.keys(keys)
        database = NostrDatabase.sqlite("db/nostr_recent_notes.db")
        cli = ClientBuilder().signer(signer).database(database).opts(opts).build()

        cli.add_relay("wss://relay.damus.io")
        cli.connect()

        timestamp_hour_ago = Timestamp.now().as_secs() - 3600
        lasthour = Timestamp.from_secs(timestamp_hour_ago)
        filter1 = Filter().kinds([1, 7, 9735]).since(lasthour)  # Notes, reactions, zaps

        # filter = Filter().author(keys.public_key())
        print("Syncing Notes of last hour.. this might take a while..")
        dbopts = NegentropyOptions().direction(NegentropyDirection.DOWN)
        cli.reconcile(filter1, dbopts)
        print("Done Syncing Notes of Last hour.")


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
        "about": "I show popular content",
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

    options = {"relay": "wss://relay.damus.io"}

    return SearchUser(name=name, dvm_config=dvm_config, nip89config=nip89config,
                      admin_config=admin_config, options=options)


if __name__ == '__main__':
    process_venv(SearchUser)
