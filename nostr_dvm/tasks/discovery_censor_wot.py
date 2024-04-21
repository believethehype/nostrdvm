import json
import os
from datetime import timedelta
from threading import Thread

from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, Kind, RelayOptions, \
    RelayLimits

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
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
    TASK: str = "people to block"
    FIX_COST: float = 0
    client: Client
    dvm_config: DVMConfig

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                 admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)
        super().__init__(name=name, dvm_config=dvm_config, nip89config=nip89config, nip88config=nip88config,
                         admin_config=admin_config, options=options)

    def is_input_supported(self, tags, client=None, dvm_config=None):
        return True

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        self.dvm_config = dvm_config

        request_form = {"jobID": event.id().to_hex()}

        # default values
        users = []
        # users.append(event.author().to_hex())

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                users.append(tag.as_vec()[1])

        options = {
            "users": users,
        }
        request_form['options'] = json.dumps(options)
        return request_form

    def process(self, request_form):
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
            cli.add_relay(relay)
        #add nostr band, too.
        ropts = RelayOptions().ping(False)
        cli.add_relay_with_opts("wss://nostr.band", ropts)

        cli.connect()

        options = DVMTaskInterface.set_options(request_form)
        step = 20

        pubkeys = []
        for user in options["users"]:
            pubkeys.append(PublicKey.parse(user))

        kind1984_filter = Filter().authors(pubkeys).kind(Kind(1984))
        reports = cli.get_events_of([kind1984_filter], timedelta(seconds=self.dvm_config.RELAY_TIMEOUT))

        bad_actors = []
        ns.dic = {}
        reasons = ["spam", "illegal", "impersonation"]
        # init
        for report in reports:
            for tag in report.tags():
                if tag.as_vec()[0] == "p":
                    ns.dic[tag.as_vec()[1]] = 0

        for report in reports:
            print(report.as_json())
            for tag in report.tags():
                if tag.as_vec()[0] == "p":
                    if len(tag.as_vec()) > 2 and tag.as_vec()[2] in reasons or len(tag.as_vec()) <= 2:
                        ns.dic[tag.as_vec()[1]] += 1


        #result = {k for (k, v) in ns.dic.items() if v > 0}
        #result = sorted(ns.dic.items(), key=lambda x: x[1], reverse=True)
        finallist_sorted = sorted(ns.dic.items(), key=lambda x: x[1], reverse=True)
        converted_dict = dict(finallist_sorted)
        print(json.dumps(converted_dict))
        for k in converted_dict:
            p_tag = Tag.parse(["p", k])
            bad_actors.append(p_tag.as_vec())

        print(json.dumps(bad_actors))
        return json.dumps(bad_actors)

    def post_process(self, result, event):
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
