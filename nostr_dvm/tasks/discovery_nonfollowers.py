import asyncio
import json
import os
from datetime import timedelta
from threading import Thread

from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, Kind, RelayOptions, \
    RelayLimits

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions, relay_timeout
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.output_utils import post_process_list_to_users

"""
This File contains a Module to find inactive follows for a user on nostr

Accepted Inputs: None needed
Outputs: A list of users that have been inactive 
Params:  None
"""


class DiscoverNonFollowers(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_PEOPLE_DISCOVERY
    TASK: str = "non-followers"
    FIX_COST: float = 50
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
        for tag in event.tags():
            if tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "user":  # check for param type
                    user = tag.as_vec()[2]

        options = {
            "user": user,
        }
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        from nostr_sdk import Filter
        from types import SimpleNamespace
        ns = SimpleNamespace()
        relaylimits = RelayLimits.disable()
        opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT)).relay_limits(relaylimits))
        sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        signer = NostrSigner.keys(keys)
        cli = Client.with_opts(signer, opts)
        # cli.add_relay("wss://relay.nostr.band")
        for relay in self.dvm_config.RELAY_LIST:
            await cli.add_relay(relay)
        #add nostr band, too.
        ropts = RelayOptions().ping(False)
        await cli.add_relay_with_opts("wss://nostr.band", ropts)

        await cli.connect()

        options = self.set_options(request_form)
        step = 20

        followers_filter = Filter().author(PublicKey.from_hex(options["user"])).kind(Kind(3))
        followers = await cli.get_events_of([followers_filter], relay_timeout)

        if len(followers) > 0:
            result_list = []
            newest = 0
            best_entry = followers[0]
            for entry in followers:
                if entry.created_at().as_secs() > newest:
                    newest = entry.created_at().as_secs()
                    best_entry = entry

            print(best_entry.as_json())
            followings = []
            ns.dic = {}
            for tag in best_entry.tags():
                if tag.as_vec()[0] == "p":
                    following = tag.as_vec()[1]
                    followings.append(following)
                    ns.dic[following] = "True"
            print("Followings: " + str(len(followings)))

            async def scanList(users, instance, i, st):
                from nostr_sdk import Filter

                keys = Keys.parse(self.dvm_config.PRIVATE_KEY)
                opts = Options().wait_for_send(True).send_timeout(
                    timedelta(seconds=5)).skip_disconnected_relays(True)
                signer = NostrSigner.keys(keys)
                cli = Client.with_opts(signer, opts)
                for relay in self.dvm_config.RELAY_LIST:
                    await cli.add_relay(relay)
                await cli.connect()

                for i in range(i, i + st):
                    filters = []
                    filter1 = Filter().author(PublicKey.from_hex(users[i])).kind(Kind(3))
                    filters.append(filter1)
                    followers = await cli.get_events_of(filters, relay_timeout)

                    if len(followers) > 0:
                        result_list = []
                        newest = 0
                        best_entry = followers[0]
                        for entry in followers:
                            if entry.created_at().as_secs() > newest:
                                newest = entry.created_at().as_secs()
                                best_entry = entry

                        foundfollower = False
                        for tag in best_entry.tags():
                            if tag.as_vec()[0] == "p":
                                if len(tag.as_vec()) > 1:
                                    if tag.as_vec()[1] == options["user"]:
                                        foundfollower = True
                                        break

                        if not foundfollower:
                            instance.dic[best_entry.author().to_hex()] = "False"
                            print("DIDNT FIND " + best_entry.author().to_nostr_uri())

                print(str(i) + "/" + str(len(users)))
                await cli.shutdown()

            threads = []
            begin = 0
            # Spawn some threads to speed things up
            while begin < len(followings) - step:
                args = [followings, ns, begin, step]
                t = Thread(target=asyncio.run, args=(scanList(followings, ns, begin, step),))
                threads.append(t)
                begin = begin + step - 1

            # last to step size
            missing_scans = (len(followings) - begin)
            args = [followings, ns, begin, missing_scans]
            t = Thread(target=asyncio.run, args=(scanList(followings, ns, begin, missing_scans),))
            threads.append(t)

            # Start all threads
            for x in threads:
                x.start()

            # Wait for all of them to finish
            for x in threads:
                x.join()

            result = {k for (k, v) in ns.dic.items() if v == "False"}

            print("Non backfollowing accounts found: " + str(len(result)))
            for k in result:
                p_tag = Tag.parse(["p", k])
                result_list.append(p_tag.as_vec())

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
        "image": "https://image.nostr.build/c33ca6fc4cc038ca4adb46fdfdfda34951656f87ee364ef59095bae1495ce669.jpg",
        "about": "I discover users you follow, but that don't follow you back.",
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

    return DiscoverNonFollowers(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                admin_config=admin_config)


if __name__ == '__main__':
    process_venv(DiscoverNonFollowers)
