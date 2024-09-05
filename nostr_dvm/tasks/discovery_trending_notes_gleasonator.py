import json
import os
from datetime import timedelta

from nostr_sdk import Tag, Kind, init_logger, LogLevel, Filter, Timestamp, RelayOptions, Client, NostrSigner, Keys, \
    SecretKey, Options, SingleLetterTag, Alphabet, PublicKey

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions, relay_timeout_long
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.output_utils import post_process_list_to_events

"""
This File contains a Module to search for notes
Accepted Inputs: a search query
Outputs: A list of events 
Params:  None
"""


class TrendingNotesGleasonator(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY
    TASK: str = "trending-content"
    FIX_COST: float = 0
    dvm_config: DVMConfig
    logger = False

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)

        if self.options is not None:
            if self.options.get("logger"):
                self.logger = bool(self.options.get("logger"))

            if self.logger:
                init_logger(LogLevel.DEBUG)

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.as_vec()[0] == 'i':
                input_value = tag.as_vec()[1]
                input_type = tag.as_vec()[2]
                if input_type != "text":
                    return False
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        request_form = {"jobID": event.id().to_hex()}
        max_results = 200

        for tag in event.tags():
            if tag.as_vec()[0] == 'i':
                input_type = tag.as_vec()[2]
            elif tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "max_results":  # check for param type
                    max_results = int(tag.as_vec()[2])

        options = {
            "max_results": max_results,
            "relay": "wss://gleasonator.de/relay"
        }
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        options = self.set_options(request_form)

        opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT)))
        sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        signer = NostrSigner.keys(keys)
        cli = Client.with_opts(signer, opts)

        ropts = RelayOptions().ping(False)
        await cli.add_relay_with_opts(options["relay"], ropts)
        await cli.connect()

        ltags = ["#e", "pub.ditto.trends"]
        authors = [PublicKey.parse("db0e60d10b9555a39050c258d460c5c461f6d18f467aa9f62de1a728b8a891a4")]
        notes_filter = Filter().authors(authors).kind(Kind(1985)).custom_tag(SingleLetterTag.lowercase(Alphabet.L), ltags)

        events = await cli.get_events_of([notes_filter], relay_timeout_long)

        result_list = []
        if len(events) > 0:
            event = events[0]
            print(event)
            for tag in event.tags():
                if tag.as_vec()[0] == "e":
                    e_tag = Tag.parse(["e", tag.as_vec()[1], tag.as_vec()[2]])
                    result_list.append(e_tag.as_vec())

        else:
            print("Nothing found")
            return ""

        await cli.shutdown()
        print(json.dumps(result_list))
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
def build_example(name, identifier, admin_config, custom_processing_msg):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.CUSTOM_PROCESSING_MESSAGE = custom_processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    # Add NIP89

    nip89info = {
        "name": name,
        "picture": "0c760b3ecdbc993ba47b785d0adecf00c760b3ecdbc993ba47b785d0adecf0ec71fd9c59808e27d0665b9f77a32d8de.png",
        "image": "0c760b3ecdbc993ba47b785d0adecf00c760b3ecdbc993ba47b785d0adecf0ec71fd9c59808e27d0665b9f77a32d8de.png",
        "about": "I show trending notes from Soapbox Ditto",
        "amount": "Free",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "nip90Params": {}
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    return TrendingNotesGleasonator(name=name, dvm_config=dvm_config, nip89config=nip89config,
                              admin_config=admin_config)


if __name__ == '__main__':
    process_venv(TrendingNotesGleasonator)
