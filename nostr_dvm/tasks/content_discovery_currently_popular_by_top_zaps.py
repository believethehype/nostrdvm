import asyncio
import json
import os
from datetime import timedelta
from nostr_sdk import Client, Timestamp, PublicKey, Tag, Keys, Options, SecretKey, NostrSigner, NostrDatabase, \
    ClientBuilder, Filter, NegentropyOptions, NegentropyDirection, init_logger, LogLevel, Event, EventId, Kind, \
    RelayOptions

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils import definitions
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.nip88_utils import NIP88Config, check_and_set_d_tag_nip88, check_and_set_tiereventid_nip88
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag, create_amount_tag
from nostr_dvm.utils.output_utils import post_process_list_to_events
from nostr_dvm.utils.zap_utils import parse_zap_event_tags, parse_amount_from_bolt11_invoice

"""
This File contains a Module to discover popular notes by amount of zaps
Accepted Inputs: none
Outputs: A list of events 
Params:  None
"""


class DicoverContentCurrentlyPopularZaps(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY
    TASK: str = "discover-content"
    FIX_COST: float = 0
    dvm_config: DVMConfig
    request_form = None
    last_schedule: int
    db_since = 3600
    db_name = "db/nostr_recent_notes.db"
    min_reactions = 1
    personalized = False
    result = ""
    logger = False

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                           admin_config: AdminConfig = None, options=None):

        self.request_form = {"jobID": "generic"}
        opts = {
            "max_results": 200,
        }
        self.request_form['options'] = json.dumps(opts)

        self.last_schedule = Timestamp.now().as_secs()
        if self.options is not None:
            if self.options.get("db_name"):
                self.db_name = self.options.get("db_name")
            if self.options.get("db_since"):
                self.db_since = int(self.options.get("db_since"))
            if self.options.get("logger"):
                self.logger = bool(self.options.get("logger"))

            if self.logger:
                init_logger(LogLevel.DEBUG)

        if self.dvm_config.UPDATE_DATABASE:
            await self.sync_db()
        if not self.personalized:
            self.result = await self.calculate_result(self.request_form)

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

        request_form = {"jobID": event.id().to_hex()}

        # default values
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
        }
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        # if the dvm supports individual results, recalculate it every time for the request
        if self.personalized:
            return await self.calculate_result(request_form)
        # else return the result that gets updated once every scheduled update. In this case on database update.
        else:
            return self.result

    async def calculate_result(self, request_form):
        from nostr_sdk import Filter
        from types import SimpleNamespace
        ns = SimpleNamespace()

        options = self.set_options(request_form)

        #opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT)))
        #sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
        #keys = Keys.parse(sk.to_hex())
        #signer = NostrSigner.keys(keys)

        database = await NostrDatabase.sqlite(self.db_name)
        #cli = ClientBuilder().database(database).signer(signer).opts(opts).build()

        #await cli.connect()

        # Negentropy reconciliation
        # Query events from database
        timestamp_hour_ago = Timestamp.now().as_secs() - self.db_since
        since = Timestamp.from_secs(timestamp_hour_ago)

        filter1 = Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(since)
        events = await database.query([filter1])
        if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
            print("[" + self.dvm_config.NIP89.NAME + "] Considering " + str(len(events)) + " Events")

        ns.finallist = {}
        for event in events:
            if event.created_at().as_secs() > timestamp_hour_ago:
                filt = Filter().kinds([definitions.EventDefinitions.KIND_ZAP]).event(event.id()).since(since)
                zaps = await database.query([filt])
                invoice_amount = 0
                event_author = event.author().to_hex()
                if len(zaps) >= self.min_reactions:
                    has_preimage = False
                    has_amount = False
                    overall_amount = 0
                    for zap in zaps:
                        if event_author == zap.author().to_hex():
                            continue #Skip self zaps..
                        invoice_amount = 0
                        for tag in zap.tags():

                            if tag.as_vec()[0] == 'bolt11':
                                # print(tag.as_vec()[1])
                                invoice_amount = parse_amount_from_bolt11_invoice(tag.as_vec()[1])

                                has_amount = True
                                if has_preimage:
                                    break
                                # print(invoice_amount)
                            if tag.as_vec()[0] == 'preimage':
                                if len(tag.as_vec()) > 1:
                                    if tag.as_vec()[1] == "":
                                        continue
                                    elif tag.as_vec()[1] != "":

                                        has_preimage = True  # TODO further check preimage
                                        if has_amount:
                                            overall_amount += invoice_amount
                                            break
                            #elif tag.as_vec()[0] == 'description':
                            #    try:
                            #        event = Event.from_json(tag.as_vec()[1])
                            #        for tag in event.tags():
                            #            if tag.as_vec()[0] == "amount":
                            #                invoice_amount = tag.as_vec()[1]
                            #                overall_amount += invoice_amount

                            #               has_amount = True
                            #               if has_preimage:
                            #                   break

                            #    except:
                            #        pass

                    if has_preimage:
                        ns.finallist[event.id().to_hex()] = overall_amount

        result_list = []

        finallist_sorted = sorted(ns.finallist.items(), key=lambda x: x[1], reverse=True)[:int(options["max_results"])]
        for entry in finallist_sorted:
            # print(EventId.parse(entry[0]).to_bech32() + "/" + EventId.parse(entry[0]).to_hex() + ": " + str(entry[1]))
            e_tag = Tag.parse(["e", entry[0]])
            result_list.append(e_tag.as_vec())
        if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
            print("[" + self.dvm_config.NIP89.NAME + "] Filtered " + str(
                len(result_list)) + " fitting events.")

        #await cli.shutdown()

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

    async def schedule(self, dvm_config):
        if dvm_config.SCHEDULE_UPDATES_SECONDS == 0:
            return 0
        else:
            if Timestamp.now().as_secs() >= self.last_schedule + dvm_config.SCHEDULE_UPDATES_SECONDS:
                try:
                    if self.dvm_config.UPDATE_DATABASE:
                        await self.sync_db()
                    self.last_schedule = Timestamp.now().as_secs()
                    if not self.personalized:
                        self.result = await self.calculate_result(self.request_form)
                except Exception as e:
                    print(e)
                return 1

    async def sync_db(self):
        try:
            opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=self.dvm_config.RELAY_LONG_TIMEOUT)))
            sk = SecretKey.from_hex(self.dvm_config.PRIVATE_KEY)
            keys = Keys.parse(sk.to_hex())
            signer = NostrSigner.keys(keys)
            database = await NostrDatabase.sqlite(self.db_name)
            cli = ClientBuilder().signer(signer).database(database).opts(opts).build()

            for relay in self.dvm_config.RECONCILE_DB_RELAY_LIST:
                await cli.add_relay(relay)

            await cli.connect()

            timestamp_since = Timestamp.now().as_secs() - self.db_since
            since = Timestamp.from_secs(timestamp_since)

            filter1 = Filter().kinds([definitions.EventDefinitions.KIND_NOTE, definitions.EventDefinitions.KIND_REACTION,
                                      definitions.EventDefinitions.KIND_ZAP]).since(since)  # Notes, reactions, zaps

            # filter = Filter().author(keys.public_key())
            if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                print("[" + self.dvm_config.NIP89.NAME + "] Syncing notes of the last " + str(
                    self.db_since) + " seconds.. this might take a while..")
            dbopts = NegentropyOptions().direction(NegentropyDirection.DOWN)
            await cli.reconcile(filter1, dbopts)
            await cli.database().delete(Filter().until(Timestamp.from_secs(
                Timestamp.now().as_secs() - self.db_since)))  # Clear old events so db doesn't get too full.
            await cli.shutdown()
            if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                print(
                    "[" + self.dvm_config.NIP89.NAME + "] Done Syncing Notes of the last " + str(self.db_since) + " seconds..")
        except Exception as e:
            print(e)

# We build an example here that we can call by either calling this file directly from the main directory,
# or by adding it to our playground. You can call the example and adjust it to your needs or redefine it in the
# playground or elsewhere
def build_example(name, identifier, admin_config, options, cost=0, update_rate=180, processing_msg=None,
                  update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 10 minutes
    dvm_config.UPDATE_DATABASE = update_db
    # Activate these to use a subscription based model instead
    # dvm_config.SUBSCRIPTION_REQUIRED = True
    # dvm_config.SUBSCRIPTION_DAILY_COST = 1
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    image = "https://image.nostr.build/c6879f458252641d04d0aa65fd7f1e005a4f7362fd407467306edc2f4acdb113.jpg",

    # Add NIP89
    nip89info = {
        "name": name,
        "image": image,
        "picture": image,
        "about": "I show notes that are currently zapped the most.",
        "lud16": dvm_config.LN_ADDRESS,
        "encryptionSupported": True,
        "cashuAccepted": True,
        "personalized": False,
        "amount": create_amount_tag(cost),
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 100)"
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    # admin_config.UPDATE_PROFILE = False
    # admin_config.REBROADCAST_NIP89 = False

    return DicoverContentCurrentlyPopularZaps(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                              admin_config=admin_config, options=options)


def build_example_subscription(name, identifier, admin_config, options, update_rate=180, processing_msg=None,
                               update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate  # Every 3 minutes
    dvm_config.UPDATE_DATABASE = update_db
    # Activate these to use a subscription based model instead
    # dvm_config.SUBSCRIPTION_DAILY_COST = 1
    dvm_config.FIX_COST = 0
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    image = "https://image.nostr.build/c6879f458252641d04d0aa65fd7f1e005a4f7362fd407467306edc2f4acdb113.jpg",
    # Add NIP89
    nip89info = {
        "name": name,
        "image": image,
        "picture": image,
        "about": "I show notes that are currently popular all over Nostr. I'm also used for testing subscriptions.",
        "lud16": dvm_config.LN_ADDRESS,
        "encryptionSupported": True,
        "cashuAccepted": True,
        "subscription": True,
        "personalized": False,
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default currently 100)"
            }
        }
    }

    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip89config.CONTENT = json.dumps(nip89info)

    nip88config = NIP88Config()
    nip88config.DTAG = check_and_set_d_tag_nip88(identifier, name, dvm_config.PRIVATE_KEY, nip89info["image"])
    nip88config.TIER_EVENT = check_and_set_tiereventid_nip88(identifier, "1")
    nip89config.NAME = name
    nip88config.IMAGE = nip89info["image"]
    nip88config.TITLE = name
    nip88config.AMOUNT_DAILY = 100
    nip88config.AMOUNT_MONTHLY = 2000
    nip88config.CONTENT = "Subscribe to the DVM for unlimited use during your subscription"
    nip88config.PERK1DESC = "Unlimited requests"
    nip88config.PERK2DESC = "Support NostrDVM & NostrSDK development"
    nip88config.PAYMENT_VERIFIER_PUBKEY = "5b5c045ecdf66fb540bdf2049fe0ef7f1a566fa427a4fe50d400a011b65a3a7e"

    # admin_config.UPDATE_PROFILE = False
    # admin_config.REBROADCAST_NIP89 = False
    # admin_config.REBROADCAST_NIP88 = False

    # admin_config.FETCH_NIP88 = True
    # admin_config.EVENTID = ""
    # admin_config.PRIVKEY = dvm_config.PRIVATE_KEY

    return DicoverContentCurrentlyPopularZaps(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                              nip88config=nip88config, options=options,
                                              admin_config=admin_config)


if __name__ == '__main__':
    process_venv(DicoverContentCurrentlyPopularZaps)
