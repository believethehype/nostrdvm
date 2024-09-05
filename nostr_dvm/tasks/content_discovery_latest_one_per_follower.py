import asyncio
import json
import os
from datetime import timedelta
from threading import Thread

from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, Kind, RelayOptions, \
    RelayLimits, Event

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions, relay_timeout_long, relay_timeout
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import post_process_list_to_users, post_process_list_to_events

"""
This File contains a Module to find inactive follows for a user on nostr

Accepted Inputs: None needed
Outputs: A list of users that have been inactive 
Params:  None
"""


class Discoverlatestperfollower(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY
    TASK: str = "content-discovery"
    FIX_COST: float = 0
    client: Client
    dvm_config: DVMConfig

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        # no input required
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        self.dvm_config = dvm_config

        request_form = {"jobID": event.id().to_hex()}

        # default values
        user = event.author().to_hex()
        since_days = 30
        max_results = 200

        for tag in event.tags():
            if tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "user":  # check for param type
                    user = tag.as_vec()[2]
                elif param == "since_days":  # check for param type
                    since_days = int(tag.as_vec()[2])

        options = {
            "user": user,
            "since_days": since_days,
            "max_results": max_results
        }
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        from nostr_sdk import Filter
        from types import SimpleNamespace
        ns = SimpleNamespace()

        sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        signer = NostrSigner.keys(keys)

        relaylimits = RelayLimits.disable()

        opts = (
            Options().wait_for_send(False).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT))).relay_limits(
            relaylimits)

        cli = Client.with_opts(signer, opts)
        for relay in self.dvm_config.RELAY_LIST:
            await cli.add_relay(relay)
        #ropts = RelayOptions().ping(False)
        #await cli.add_relay_with_opts("wss://nostr.band", ropts)

        await cli.connect()

        options = self.set_options(request_form)
        step = 20

        followers_filter = Filter().author(PublicKey.parse(options["user"])).kind(Kind(3))
        followers = await cli.get_events_of([followers_filter], relay_timeout)

        if len(followers) > 0:
            result_list = []
            newest = 0
            best_entry = followers[0]
            for entry in followers:
                print(len(best_entry.tags()))
                print(best_entry.created_at().as_secs())
                if entry.created_at().as_secs() > newest:
                    newest = entry.created_at().as_secs()
                    best_entry = entry

            followings = []
            ns.dic = {}
            tagcount = 0
            for tag in best_entry.tags():
                tagcount += 1
                if tag.as_vec()[0] == "p":
                    following = tag.as_vec()[1]
                    followings.append(following)
                    ns.dic[following] = None
            print("Followings: " + str(len(followings)) + " Tags: " + str(tagcount))

            print(ns.dic)
            print(len(ns.dic))

            search_since = int(options["since_days"]) * 24 * 60 * 60
            dif = Timestamp.now().as_secs() - search_since
            search_since_ts = Timestamp.from_secs(dif)

            async def scanList(users, instance, i, st, notactivesince):
                from nostr_sdk import Filter

                keys = Keys.parse(self.dvm_config.PRIVATE_KEY)
                opts = Options().wait_for_send(True).send_timeout(
                    timedelta(seconds=10)).skip_disconnected_relays(True)
                signer = NostrSigner.keys(keys)
                cli = Client.with_opts(signer, opts)
                for relay in self.dvm_config.RELAY_LIST:
                    await cli.add_relay(relay)
                await cli.connect()

                filters = []
                for i in range(i, i + st):
                    filter1 = (Filter().author(PublicKey.from_hex(users[i])).kind(Kind(1))
                               .limit(1))
                    filters.append(filter1)
                event_from_authors = await cli.get_events_of(filters, relay_timeout_long)
                for author in event_from_authors:
                    if instance.dic[author.author().to_hex()] is None:
                        instance.dic[author.author().to_hex()] = author
                print(str(i) + "/" + str(len(users)))
                await cli.shutdown()

            threads = []
            begin = 0
            # Spawn some threads to speed things up
            while begin < len(followings) - step:
                t = Thread(target=asyncio.run, args=(scanList(followings, ns, begin, step, search_since_ts),))
                threads.append(t)
                begin = begin + step - 1

            # last to step size
            missing_scans = (len(followings) - begin)
            t = Thread(target=asyncio.run, args=(scanList(followings, ns, begin, missing_scans, search_since_ts),))

            threads.append(t)

            # Start all threads
            for x in threads:
                x.start()

            # Wait for all of them to finish
            for x in threads:
                x.join()

            result = {v for (k, v) in ns.dic.items() if v is not None}

            #print(result)
            #result = sorted(result, key=lambda x: x.created_at().as_secs(), reverse=True)
            new_list = sorted(result, key=lambda evt: evt.created_at().as_secs(), reverse=True)
            new_res = new_list[:int(options["max_results"])]
            #result = {v.id().to_hex() for (k, v) in finallist_sorted if v is not None}

            #[: int(options["max_results"])]
            print("events found: " + str(len(new_res)))
            for v in new_res:
                e_tag = Tag.parse(["e", v.id().to_hex()])
                result_list.append(e_tag.as_vec())

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
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://i.nostr.build/H6SMmCl7eRDvkbAn.jpg",
        "about": "I discover users you follow, but that have been inactive on Nostr",
        "action": "unfollow",  # follow, mute, unmute
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {
            "user": {
                "required": False,
                "values": [],
                "description": "Do the task for another user"
            },
            "since_days": {
                "required": False,
                "values": [],
                "description": "The number of days a user has not been active to be considered inactive"
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return Discoverlatestperfollower(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                     admin_config=admin_config)


if __name__ == '__main__':
    process_venv(Discoverlatestperfollower)
