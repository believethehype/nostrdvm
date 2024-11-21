import json
import os
from datetime import timedelta
from itertools import islice

from nostr_sdk import Timestamp, Tag, Keys, Options, SecretKey, NostrSigner, NostrDatabase, \
    ClientBuilder, Filter, SyncOptions, SyncDirection, Kind, PublicKey, RelayFilteringMode, RelayLimits

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import post_process_list_to_users
from nostr_dvm.utils.wot_utils import build_wot_network

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
    wot_counter = 0

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)

        if self.dvm_config.UPDATE_DATABASE:
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
        #print(self.dvm_config.PRIVATE_KEY)

        request_form = {"jobID": event.id().to_hex()}

        # default values
        search = ""
        max_results = 100

        for tag in event.tags().to_vec():
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

        sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        database = NostrDatabase.lmdb(self.db_name)
        cli = ClientBuilder().database(database).signer(NostrSigner.keys(keys)).build()

        for relay in self.dvm_config.SYNC_DB_RELAY_LIST:
            await cli.add_relay(relay)
        # cli.add_relay("wss://atl.purplerelay.com")
        await cli.connect()

        # Negentropy reconciliation

        # Query events from database

        filter1 = Filter().kind(Kind(0))
        events = await cli.database().query([filter1])

        result_list = []
        print("Events: " + str(len(events.to_vec())))
        index = 0
        if len(events.to_vec()) > 0:

            for event in events.to_vec():
                if index < options["max_results"]:
                    try:
                        searchterm = " " + options["search"].lower() + " "
                        if options["search"].lower() in event.content().lower():
                            p_tag = Tag.parse(["p", event.author().to_hex()])
                            #print(event.as_json())
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
        for tag in event.tags().to_vec():
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
                if self.dvm_config.UPDATE_DATABASE:
                    await self.sync_db()
                self.last_schedule = Timestamp.now().as_secs()
                return 1

    async def sync_db(self):
        sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        database = NostrDatabase.lmdb(self.db_name)
        relaylimits = RelayLimits.disable()
        opts = (Options().relay_limits(relaylimits))
        if self.dvm_config.WOT_FILTERING:
            opts = opts.filtering_mode(RelayFilteringMode.WHITELIST)
        cli = ClientBuilder().signer(NostrSigner.keys(keys)).database(database).opts(opts).build()

        for relay in self.dvm_config.SYNC_DB_RELAY_LIST:
            await cli.add_relay(relay)
        await cli.connect()
        if self.dvm_config.WOT_FILTERING and self.wot_counter == 0:
            print("Calculating WOT for " + str(self.dvm_config.WOT_BASED_ON_NPUBS))
            filtering = cli.filtering()
            index_map, G = await build_wot_network(self.dvm_config.WOT_BASED_ON_NPUBS,
                                                   depth=self.dvm_config.WOT_DEPTH, max_batch=500,
                                                   max_time_request=10, dvm_config=self.dvm_config)

            # Do we actually need pagerank here?
            # print('computing global pagerank...')
            # tic = time.time()
            # p_G = nx.pagerank(G, tol=1e-12)
            # print("network after pagerank: " + str(len(p_G)))

            wot_keys = []
            for item in islice(G, len(G)):
                key = next((PublicKey.parse(pubkey) for pubkey, id in index_map.items() if id == item),
                           None)
                wot_keys.append(key)

            # toc = time.time()
            # print(f'finished in {toc - tic} seconds')
            await filtering.add_public_keys(wot_keys)

        self.wot_counter += 1
        # only calculate wot every 10th call
        if self.wot_counter >= 10:
            self.wot_counter = 0

        filter1 = Filter().kind(Kind(0))

        # filter = Filter().author(keys.public_key())
        print("Syncing Profile Database.. this might take a while..")
        try:
            dbopts = SyncOptions().direction(SyncDirection.DOWN)
            await cli.sync(filter1, dbopts)
            print("Done Syncing Profile Database.")
        except Exception as exp:
            print(str(exp))
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

    return SearchUser(name=name, dvm_config=dvm_config, nip89config=nip89config,
                      admin_config=admin_config)


if __name__ == '__main__':
    process_venv(SearchUser)
