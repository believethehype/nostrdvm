import json
import os
import random
import re
from datetime import timedelta
from threading import Thread

from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, EventId, Kind

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


class DiscoverInactiveFollows(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_PEOPLE_DISCOVERY
    TASK: str = "inactive-follows"
    FIX_COST: float = 50
    client: Client
    dvm_config: DVMConfig

    def __init__(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                 admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)
        super().__init__(name=name, dvm_config=dvm_config, nip89config=nip89config, nip88config=nip88config,
                         admin_config=admin_config, options=options)

    def is_input_supported(self, tags, client=None, dvm_config=None):
        # no input required
        return True

    def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        self.dvm_config = dvm_config

        request_form = {"jobID": event.id().to_hex()}

        # default values
        user = event.author().to_hex()
        since_days = 90

        for tag in event.tags():
            if tag.as_vec()[0] == 'param':
                param = tag.as_vec()[1]
                if param == "user":  # check for param type
                    user = tag.as_vec()[2]
                elif param == "since_days":  # check for param type
                    since_days = int(tag.as_vec()[2])

        options = {
            "user": user,
            "since_days": since_days
        }
        request_form['options'] = json.dumps(options)
        return request_form

    def process(self, request_form):
        from nostr_sdk import Filter
        from types import SimpleNamespace
        ns = SimpleNamespace()

        opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT)))
        sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        keys = Keys.parse(sk.to_hex())
        signer = NostrSigner.keys(keys)
        cli = Client.with_opts(signer, opts)
        for relay in self.dvm_config.RELAY_LIST:
            cli.add_relay(relay)
        cli.connect()

        options = DVMTaskInterface.set_options(request_form)



        inactivefollowerslist = ""
        relay_list = ["wss://relay.damus.io", "wss://nostr-pub.wellorder.net", "wss://nos.lol", "wss://nostr.wine",
                      "wss://relay.nostfiles.dev", "wss://nostr.mom", "wss://nostr.oxtr.dev",
                      "wss://relay.nostr.bg", "wss://relay.f7z.io"]
        relaytimeout = 5
        step = 20
        keys = Keys.parse(os.getenv(env.NOSTR_PRIVATE_KEY))
        opts = Options().wait_for_send(False).send_timeout(timedelta(seconds=5)).skip_disconnected_relays(
            True)
        cl = Client.with_opts(keys, opts)
        for relay in relay_list:
            cl.add_relay(relay)
        cl.connect()

        timeinseconds = 3 * 24 * 60 * 60
        dif = Timestamp.now().as_secs() - timeinseconds
        considernotessince = Timestamp.from_secs(dif)
        filt = Filter().author(user).kind(1).since(considernotessince)
        reactions = cl.get_events_of([filt], timedelta(seconds=relaytimeout))
        list = []
        random.shuffle(reactions)
        for reaction in reactions:
            if reaction.kind() == 1:
                list.append(reaction.content())
        all = json.dumps(list)
        all = all.replace("\n", " ").replace("\n\n", " ")
        cleared = ""
        tokens = all.split()
        for item in tokens:
            item = item.replace("\n", " ").lstrip("\"").rstrip(",").rstrip(("."))
            # print(item)
            if item.__contains__("http") or item.__contains__("\nhttp") or item.__contains__(
                    "\n\nhttp") or item.lower().__contains__("nostr:") or item.lower().__contains__(
                    "nevent") or item.__contains__("\\u"):
                cleareditem = ""
            else:
                cleareditem = item
            cleared = cleared + " " + cleareditem

        cleared = cleared.replace("\n", " ")
        # res = re.sub(r"[^ a-zA-Z0-9.!?/\\:,]+", '', all)
        # print(cleared)
        try:
            answer = LLAMA2(
                "Give me the 15 most important substantives as keywords of the following input: " + cleared,
                "nostruser",
                "Reply only with a comma-seperated keywords. return topics starting with a *", clear=True)
        except:
            answer = ""

        promptarr = answer.split(":")
        if len(promptarr) > 1:
            # print(promptarr[1])
            prompt = promptarr[1].lstrip("\n").replace("\n", ",").replace("*", ",").replace("•", ",")
        else:
            prompt = promptarr[0].replace("\n", ",").replace("*", "")

        pattern = r"[^a-zA-Z,#'\s]"
        text = re.sub(pattern, "", prompt) + ","

        # text = (text.replace("Let's,", "").replace("Why,", "").replace("GM,", "")
        #        .replace("Remember,", "").replace("I,", "").replace("Think,", "")
        #        .replace("Already,", ""))
        # print(text)
        keywords = text.split(', ')
        keywords = [x.lstrip().rstrip(',') for x in keywords if x]

        print(keywords)

        # answer = LLAMA2("Extent the given list with 5 synonyms per entry  " + str(keywords), user,
        #                "Reply only with a comma-seperated keywords. return topics starting with a *")
        # answer.replace(" - Alternatives:", ",")
        # print(answer)
        # promptarr = answer.split(":")
        # if len(promptarr) > 1:
        #    # print(promptarr[1])
        #    prompt = promptarr[1].lstrip("\n").replace("\n", ",").replace("*", "").replace("•", "")
        # else:
        #    prompt = promptarr[0].replace("\n", ",").replace("*", "")

        # pattern = r"[^a-zA-Z,'\s]"
        # text = re.sub(pattern, "", prompt) + ","
        # keywords = text.split(', ')

        # print(keywords)

        timeinseconds = 30 * 60  # last 30 min?
        dif = Timestamp.now().as_secs() - timeinseconds
        looksince = Timestamp.from_secs(dif)
        filt2 = Filter().kind(1).since(looksince)
        notes = cl.get_events_of([filt2], timedelta(seconds=6))

        # finallist = []
        ns.finallist = {}

        print("Notes found: " + str(len(notes)))

        def scanList(noteid: EventId, instance, i, length):

            relay_list = ["wss://relay.damus.io", "wss://nostr-pub.wellorder.net", "wss://nos.lol",
                          "wss://nostr.wine",
                          "wss://relay.nostfiles.dev", "wss://nostr.mom", "wss://nostr.oxtr.dev",
                          "wss://relay.nostr.bg", "wss://relay.f7z.io"]
            keys = Keys.parse(os.getenv(env.NOSTR_PRIVATE_KEY))
            opts = Options().wait_for_send(wait_for_send).send_timeout(
                timedelta(seconds=5)).skip_disconnected_relays(True)
            cli = Client.with_opts(keys, opts)
            for relay in relay_list:
                cli.add_relay(relay)
            cli.connect()

            filters = []
            instance.finallist[noteid.to_hex()] = 0
            filt = Filter().kinds([9735, 7, 1]).event(noteid)
            reactions = cl.get_events_of([filt], timedelta(seconds=5))
            print(str(len(reactions)) + "   " + str(j) + "/" + str(len(notes)))
            instance.finallist[noteid.to_hex()] = len(reactions)

            print(str(i) + "/" + str(length))
            cli.disconnect()

        j = 0

        threads = []

        for note in notes:

            j = j + 1
            res = [ele for ele in keywords if (ele.replace(',', "") in note.content())]
            if bool(res):
                if not note.id().to_hex() in ns.finallist and note.pubkey().to_hex() != user:
                    args = [note.id(), ns, j, len(notes)]
                    t = Thread(target=scanList, args=args)
                    threads.append(t)

            # Start all threads
        for x in threads:
            x.start()

            # Wait for all of them to finish
        for x in threads:
            x.join()

        finallist_sorted = sorted(ns.finallist.items(), key=lambda x: x[1], reverse=True)
        converted_dict = dict(finallist_sorted)
        print(json.dumps(converted_dict))

        notelist = ""
        resultlist = []
        i = 0
        notelist = "Based on topics: " + json.dumps(keywords).lstrip("[").rstrip(("]")) + "\n\n"
        for k in converted_dict:
            # print(k)
            if is_bot:
                i = i + 1
                notelist = notelist + "nostr:" + EventId.from_hex(k).to_bech32() + "\n\n"
                if i == 25:
                    break
            else:
                p_tag = Tag.parse(["p", k])
                resultlist.append(p_tag.as_vec())

        else:
            return json.dumps(resultlist[:25])

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
    admin_config.LUD16 = dvm_config.LN_ADDRESS
    # Add NIP89
    nip89info = {
        "name": name,
        "image": "https://image.nostr.build/b29b6ec4bf9b6184f69d33cb44862db0d90a2dd9a506532e7ba5698af7d36210.jpg",
        "about": "I discover users you follow, but that have been inactive on Nostr",
        "encryptionSupported": True,
        "cashuAccepted": True,
        "amount": "Free",
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

    return DiscoverInactiveFollows(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                   admin_config=admin_config)


if __name__ == '__main__':
    process_venv(DiscoverInactiveFollows)
