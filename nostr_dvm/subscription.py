import json
import math
import os
import signal
import time
from datetime import timedelta

from nostr_sdk import (Keys, Client, Timestamp, Filter, nip04_decrypt, HandleNotification, EventBuilder, PublicKey,
                       Options, Tag, Event, nip04_encrypt, NostrSigner, EventId, Nip19Event, nip44_decrypt, Kind)

from nostr_dvm.utils.database_utils import fetch_user_metadata
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip89_utils import NIP89Config
from nostr_dvm.utils.nwc_tools import nwc_zap
from nostr_dvm.utils.subscription_utils import create_subscription_sql_table, add_to_subscription_sql_table, \
    get_from_subscription__sql_table, update_subscription_sql_table
from nostr_dvm.utils.zap_utils import create_bolt11_lud16, zaprequest


class Subscription:
    job_list: list

    # This is a simple list just to keep track which events we created and manage, so we don't pay for other requests
    def __init__(self, dvm_config, admin_config=None):
        self.NAME = "Subscription Handler"
        dvm_config.DB = "db/" + self.NAME + ".db"
        self.dvm_config = dvm_config
        nip89config = NIP89Config()
        nip89config.NAME = self.NAME
        self.dvm_config.NIP89 = nip89config
        self.admin_config = admin_config
        self.keys = Keys.parse(dvm_config.PRIVATE_KEY)
        wait_for_send = True
        skip_disconnected_relays = True
        opts = (Options().wait_for_send(wait_for_send).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT))
                .skip_disconnected_relays(skip_disconnected_relays))
        signer = NostrSigner.keys(self.keys)
        self.client = Client.with_opts(signer, opts)

        pk = self.keys.public_key()

        self.job_list = []

        print("Nostr Subscription Handler public key: " + str(pk.to_bech32()) + " Hex: " + str(
            pk.to_hex()) + " Name: " + self.NAME +
              " Supported DVM tasks: " +
              ', '.join(p.NAME + ":" + p.TASK for p in self.dvm_config.SUPPORTED_DVMS) + "\n")

        for relay in self.dvm_config.RELAY_LIST:
            self.client.add_relay(relay)
        self.client.connect()

        zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_ZAP]).since(Timestamp.now())
        cancel_subscription_filter = Filter().kinds([EventDefinitions.KIND_NIP88_STOP_SUBSCRIPTION_EVENT]).since(
            Timestamp.now())
        # TODO define allowed senders somewhere
        dm_filter = Filter().author(
            Keys.parse("ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e").public_key()).pubkey(
            pk).kinds([EventDefinitions.KIND_DM]).since(Timestamp.now())

        self.client.subscribe([zap_filter, dm_filter, cancel_subscription_filter], None)

        create_subscription_sql_table("db/subscriptions")

        #  admin_make_database_updates(adminconfig=self.admin_config, dvmconfig=self.dvm_config, client=self.client)

        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            def handle(self, relay_url, subscription_id, nostr_event: Event):
                if nostr_event.kind().as_u64() == EventDefinitions.KIND_DM.as_u64():
                    print(nostr_event.as_json())
                    handle_dm(nostr_event)
                elif nostr_event.kind().as_u64() == EventDefinitions.KIND_NIP88_STOP_SUBSCRIPTION_EVENT.as_u64():
                    handle_cancel(nostr_event)

            def handle_msg(self, relay_url, msg):
                return

        def handle_cancel(nostr_event):
            print(nostr_event.as_json())
            sender = nostr_event.author().to_hex()
            kind7001eventid = ""
            recipient = ""
            if sender == self.keys.public_key().to_hex():
                return

            for tag in nostr_event.tags():
                if tag.as_vec()[0] == "p":
                    recipient = tag.as_vec()[1]
                elif tag.as_vec()[0] == "e":
                    kind7001eventid = tag.as_vec()[1]

            if kind7001eventid != "":
                subscription = get_from_subscription__sql_table("db/subscriptions", kind7001eventid)

                if subscription is not None:
                    update_subscription_sql_table("db/subscriptions", kind7001eventid, recipient,
                                                  subscription.subscriber, subscription.nwc, subscription.cadence,
                                                  subscription.amount, subscription.begin, subscription.end,
                                                  subscription.tier_dtag, subscription.zaps, subscription.recipe, False)

        def handle_dm(nostr_event):

            sender = nostr_event.author().to_hex()
            if sender == self.keys.public_key().to_hex():
                return

            try:
                decrypted_text = nip04_decrypt(self.keys.secret_key(), nostr_event.author(), nostr_event.content())
                try:
                    jsonevent = json.loads(decrypted_text)
                    print(jsonevent)
                    nwc = nip44_decrypt(self.keys.secret_key(), nostr_event.author(), jsonevent['nwc'])
                    event7001 = jsonevent['subscribe_event']
                    cadence = jsonevent['cadence']
                    recipient = jsonevent['recipient']
                    subscriber = jsonevent['subscriber']
                    overall_amount = int(jsonevent['overall_amount'])
                    tier_dtag = jsonevent['tier_dtag']

                    start = Timestamp.now().as_secs()
                    end = Timestamp.now().as_secs()

                    isactivesubscription = False
                    recipe = ""

                    subscription = get_from_subscription__sql_table("db/subscriptions", event7001)
                    if subscription is not None and subscription.end > start:
                        start = subscription.end
                        isactivesubscription = True



                    if cadence == "daily":
                        end = start + 60 * 60 * 24
                    elif cadence == "weekly":
                        end = start + 60 * 60 * 24 * 7
                    elif cadence == "monthly":
                        # TODO check days of month -.-
                        end = start + 60 * 60 * 24 * 31
                    elif cadence == "yearly":
                        # TODO check extra day every 4 years
                        end = start + 60 * 60 * 24 * 356
                    zapsstr = json.dumps(jsonevent['zaps'])
                    print(zapsstr)
                    success = True
                    if subscription is None or subscription.end <= Timestamp.now().as_secs():

                        overallsplit = 0

                        for zap in jsonevent['zaps']:
                            overallsplit += int(zap['split'])

                        zapped_amount = 0
                        for zap in jsonevent['zaps']:
                            name, nip05, lud16 = fetch_user_metadata(zap['key'], self.client)
                            splitted_amount = math.floor(
                                (int(zap['split']) / overallsplit) * int(jsonevent['overall_amount']) / 1000)
                            # invoice = create_bolt11_lud16(lud16, splitted_amount)
                            # TODO add details about DVM in message
                            invoice = zaprequest(lud16, splitted_amount, "DVM subscription", None,
                                                 PublicKey.parse(zap['key']), self.keys, DVMConfig.RELAY_LIST)
                            print(invoice)
                            if invoice is not None:
                                nwc_event_id = nwc_zap(nwc, invoice, self.keys, zap['relay'])
                                if nwc_event_id is None:
                                    print("error zapping " + lud16)
                                else:
                                    zapped_amount = zapped_amount + (splitted_amount * 1000)
                                    print(str(zapped_amount) + "/" + str(overall_amount))

                            if zapped_amount < overall_amount * 0.8:  # TODO how do we handle failed zaps for some addresses? we are ok with 80% for now
                                success = False
                            else:
                                print("Zapped successfully")
                            # if no active subscription exists OR the subscription ended, pay

                    if success:
                        message = "payed by subscription service"
                        pTag = Tag.parse(["p", recipient])
                        PTag = Tag.parse(["P", subscriber])
                        eTag = Tag.parse(["e", event7001])
                        validTag = Tag.parse(["valid", str(start), str(end)])
                        tierTag = Tag.parse(["tier", tier_dtag])
                        alttag = Tag.parse(["alt", "This is a NIP90 DVM Subscription Payment Recipe"])

                        tags = [pTag, PTag, eTag, validTag, tierTag, alttag]

                        event = EventBuilder(EventDefinitions.KIND_NIP88_PAYMENT_RECIPE,
                                             message, tags).to_event(self.keys)

                        dvmconfig = DVMConfig()
                        signer = NostrSigner.keys(self.keys)
                        client = Client(signer)
                        for relay in dvmconfig.RELAY_LIST:
                            client.add_relay(relay)
                        client.connect()
                        recipeid = client.send_event(event)
                        recipe = recipeid.to_hex()
                        print("RECIPE " + recipe)
                        isactivesubscription = True

                    if subscription is None:
                        add_to_subscription_sql_table("db/subscriptions", event7001, recipient, subscriber, nwc,
                                                      cadence, overall_amount, start, end, tier_dtag,
                                                      zapsstr, recipe, isactivesubscription)
                        print("new subscription entry")
                    else:
                        update_subscription_sql_table("db/subscriptions", event7001, recipient, subscriber, nwc,
                                                      cadence, overall_amount, start, end,
                                                      tier_dtag, zapsstr, recipe, isactivesubscription)
                        print("updated subscription entry")


                except Exception as e:
                    print(e)




            except Exception as e:
                print("Error in Subscriber " + str(e))

        self.client.handle_notifications(NotificationHandler())

        try:
            while True:
                time.sleep(60.0)


                print("Checking Subscription")
        except KeyboardInterrupt:
            print('Stay weird!')
            os.kill(os.getpid(), signal.SIGTERM)
