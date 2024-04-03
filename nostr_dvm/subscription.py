import json
import os
import signal
import time
from datetime import timedelta

from nostr_sdk import (
    Keys, Client, Timestamp, Filter, nip04_decrypt, HandleNotification, EventBuilder,
    PublicKey, Options, Tag, Event, nip04_encrypt, NostrSigner, EventId, Kind
)

from nostr_dvm.utils.database_utils import fetch_user_metadata
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip88_utils import nip88_has_active_subscription
from nostr_dvm.utils.nip89_utils import NIP89Config
from nostr_dvm.utils.nostr_utils import send_event
from nostr_dvm.utils.nwc_tools import nwc_zap
from nostr_dvm.utils.subscription_utils import (
    create_subscription_sql_table, add_to_subscription_sql_table, get_from_subscription_sql_table,
    update_subscription_sql_table, get_all_subscriptions_from_sql_table, delete_from_subscription_sql_table
)
from nostr_dvm.utils.zap_utils import create_bolt11_lud16, zaprequest


class Subscription:
    def __init__(self, dvm_config, admin_config=None):
        self.NAME = "Subscription Handler"
        dvm_config.DB = "db/subscriptions.db"
        self.dvm_config = dvm_config
        nip89config = NIP89Config()
        nip89config.NAME = self.NAME
        self.dvm_config.NIP89 = nip89config
        self.admin_config = admin_config
        self.keys = Keys.parse(dvm_config.PRIVATE_KEY)
        wait_for_send = False
        skip_disconnected_relays = True
        opts = (Options().wait_for_send(wait_for_send).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT))
                .skip_disconnected_relays(skip_disconnected_relays))
        signer = NostrSigner.keys(self.keys)
        self.client = Client.with_opts(signer, opts)

        public_key = self.keys.public_key()

        self.job_list = []

        print(f"Nostr Subscription Handler public key: {public_key.to_bech32()} Hex: {public_key.to_hex()}\n")

        for relay in self.dvm_config.RELAY_LIST:
            self.client.add_relay(relay)
        self.client.connect()

        zap_filter = Filter().pubkey(public_key).kinds([EventDefinitions.KIND_ZAP]).since(Timestamp.now())
        cancel_subscription_filter = Filter().kinds([EventDefinitions.KIND_NIP88_STOP_SUBSCRIPTION_EVENT]).since(
            Timestamp.now())
        authors = []
        if admin_config is not None:
            for key in admin_config.USERNPUBS:
                authors.append(PublicKey.parse(key))
        dvm_filter = Filter().authors(authors).pubkey(public_key).kinds([Kind(5906)]).since(Timestamp.now())

        self.client.subscribe([zap_filter, dvm_filter, cancel_subscription_filter], None)

        create_subscription_sql_table(dvm_config.DB)

        self.client.handle_notifications(self.NotificationHandler(self))

        try:
            while True:
                time.sleep(60.0)
                self.check_subscriptions()

        except KeyboardInterrupt:
            print('Stay weird!')
            os.kill(os.getpid(), signal.SIGTERM)

    def check_subscriptions(self):
        subscriptions = get_all_subscriptions_from_sql_table(self.dvm_config.DB)

        for subscription in subscriptions:
            if subscription.active:
                if subscription.end < Timestamp.now().as_secs():
                    self.handle_subscription_renewal(subscription)
            else:
                self.handle_expired_subscription(subscription)

        print(f"{Timestamp.now().as_secs()}: Checking {len(subscriptions)} Subscription entries..")

    def handle_subscription_renewal(self, subscription):
        subscription_status = nip88_has_active_subscription(
            PublicKey.parse(subscription.subscriber),
            subscription.tier_dtag, self.client, subscription.recipent)

        if subscription_status["expires"]:
            update_subscription_sql_table(self.dvm_config.DB, subscription_status["subscriptionId"],
                                          subscription.recipent,
                                          subscription.subscriber, subscription.nwc,
                                          subscription.cadence, subscription.amount, subscription.unit,
                                          subscription.begin, subscription.end,
                                          subscription.tier_dtag, subscription.zaps,
                                          subscription.recipe,
                                          False,
                                          Timestamp.now().as_secs(), subscription.tier)
        else:
            zaps = json.loads(subscription.zaps)
            success = self.pay_zap_split(subscription.nwc, subscription.amount, zaps, subscription.tier,
                                         subscription.unit)
            if success:
                end = self.infer_subscription_end_time(Timestamp.now().as_secs(), subscription.cadence)
                recipe = self.make_subscription_zap_recipe(subscription.id, subscription.recipent,
                                                           subscription.subscriber, subscription.begin,
                                                           end, subscription.tier_dtag)
            else:
                end = Timestamp.now().as_secs()
                recipe = subscription.recipe

            update_subscription_sql_table(self.dvm_config.DB, subscription.id,
                                          subscription.recipent,
                                          subscription.subscriber, subscription.nwc,
                                          subscription.cadence, subscription.amount, subscription.unit,
                                          subscription.begin, end,
                                          subscription.tier_dtag, subscription.zaps, recipe,
                                          success,
                                          Timestamp.now().as_secs(), subscription.tier)

            print("Updated subscription entry")

            message = (f"Renewed Subscription to DVM {subscription.tier}. "
                       f"Next renewal: {Timestamp.from_secs(end).to_human_datetime().replace('Z', ' ').replace('T', ' ')}")
            self.send_direct_message(subscription.subscriber, message)

    def handle_expired_subscription(self, subscription):
        delete_threshold = 60 * 60 * 24 * 365
        if subscription.cadence == "daily":
            delete_threshold = 60 * 60 * 24 * 3  # After 3 days, delete the subscription, user can make a new one
        elif subscription.cadence == "weekly":
            delete_threshold = 60 * 60 * 24 * 21  # After 21 days, delete the subscription, user can make a new one
        elif subscription.cadence == "monthly":
            delete_threshold = 60 * 60 * 24 * 60  # After 60 days, delete the subscription, user can make a new one
        elif subscription.cadence == "yearly":
            delete_threshold = 60 * 60 * 24 * 500  # After 500 days, delete the subscription, user can make a new one

        if subscription.end < (Timestamp.now().as_secs() - delete_threshold):
            delete_from_subscription_sql_table(self.dvm_config.DB, subscription.id)
            print("Deleted expired subscription")

    def pay_zap_split(self, nwc, overall_amount, zaps, tier, unit="msats"):
        overallsplit = sum(int(zap[3]) for zap in zaps)
        zapped_amount = 0

        for zap in zaps:
            if zap[1] == "":
                zap[1] = self.keys.public_key().to_hex()

            name, nip05, lud16 = fetch_user_metadata(zap[1], self.client)
            splitted_amount = int((int(zap[3]) / overallsplit) * int(overall_amount) / 1000)

            invoice = zaprequest(lud16, splitted_amount, tier, None,
                                 PublicKey.parse(zap[1]), self.keys, DVMConfig.RELAY_LIST)

            if invoice is not None:
                nwc_event_id = nwc_zap(nwc, invoice, self.keys, zap[2])
                if nwc_event_id is None:
                    print(f"Error zapping {lud16}")
                else:
                    zapped_amount += splitted_amount * 1000
                    print(f"{zapped_amount}/{overall_amount}")

        return zapped_amount >= overall_amount * 0.8

    def make_subscription_zap_recipe(self, event7001, recipient, subscriber, start, end, tier_dtag):
        message = "Paid by subscription service"
        p_tag = Tag.parse(["p", recipient])
        p_subscriber_tag = Tag.parse(["P", subscriber])
        e_tag = Tag.parse(["e", event7001])
        valid_tag = Tag.parse(["valid", str(start), str(end)])
        tier_tag = Tag.parse(["tier", tier_dtag])
        alt_tag = Tag.parse(["alt", "This is a NIP90 DVM Subscription Payment Recipe"])

        tags = [p_tag, p_subscriber_tag, e_tag, valid_tag, tier_tag, alt_tag]

        event = EventBuilder(EventDefinitions.KIND_NIP88_PAYMENT_RECIPE,
                             message, tags).to_event(self.keys)

        recipeid = self.client.send_event(event)
        recipe = recipeid.to_hex()
        return recipe

    def infer_subscription_end_time(self, start, cadence):
        end = start
        if cadence == "daily":
            end = start + 60 * 60 * 24
        elif cadence == "weekly":
            end = start + 60 * 60 * 24 * 7
        elif cadence == "monthly":
            end = start + 60 * 60 * 24 * 31
        elif cadence == "yearly":
            end = start + 60 * 60 * 24 * 356
        return end

    def send_direct_message(self, recipient, message):
        evt = EventBuilder.encrypted_direct_msg(self.keys, PublicKey.parse(recipient), message, None).to_event(
            self.keys)
        send_event(evt, client=self.client, dvm_config=self.dvm_config)

    class NotificationHandler(HandleNotification):
        def __init__(self, subscription):
            self.subscription = subscription

        def handle(self, relay_url, subscription_id, nostr_event: Event):
            if nostr_event.kind().as_u64() == 5906:  # TODO add to list of events
                self.subscription.handle_nwc_request(nostr_event)
            elif nostr_event.kind().as_u64() == EventDefinitions.KIND_NIP88_STOP_SUBSCRIPTION_EVENT.as_u64():
                self.subscription.handle_cancel(nostr_event)

        def handle_msg(self, relay_url, msg):
            pass

    def send_status_success(self, original_event, domain):

        e_tag = Tag.parse(["e", original_event.id().to_hex()])
        p_tag = Tag.parse(["p", original_event.author().to_hex()])
        status_tag = Tag.parse(["status", "success", "Job has been scheduled, you can manage it on " + domain])
        reply_tags = [status_tag]
        encryption_tags = []

        encrypted_tag = Tag.parse(["encrypted"])
        encryption_tags.append(encrypted_tag)
        encryption_tags.append(p_tag)
        encryption_tags.append(e_tag)

        str_tags = []
        for element in reply_tags:
            str_tags.append(element.as_vec())

        content = json.dumps(str_tags)
        content = nip04_encrypt(self.keys.secret_key(), PublicKey.from_hex(original_event.author().to_hex()),
                                content)
        reply_tags = encryption_tags

        keys = Keys.parse(self.dvm_config.PRIVATE_KEY)
        reaction_event = EventBuilder(EventDefinitions.KIND_FEEDBACK, str(content), reply_tags).to_event(keys)
        send_event(reaction_event, client=self.client, dvm_config=self.dvm_config)

    def handle_cancel(self, nostr_event):
        print(nostr_event.as_json())
        sender = nostr_event.author().to_hex()
        if sender == self.keys.public_key().to_hex():
            return

        kind7001eventid = ""
        recipient = ""
        for tag in nostr_event.tags():
            if tag.as_vec()[0] == "p":
                recipient = tag.as_vec()[1]
            elif tag.as_vec()[0] == "e":
                kind7001eventid = tag.as_vec()[1]

        if kind7001eventid != "":
            subscription = get_from_subscription_sql_table(self.dvm_config.DB, kind7001eventid)

            if subscription is not None:
                update_subscription_sql_table(self.dvm_config.DB, kind7001eventid, recipient,
                                              subscription.subscriber, subscription.nwc, subscription.cadence,
                                              subscription.amount, subscription.unit, subscription.begin,
                                              subscription.end,
                                              subscription.tier_dtag, subscription.zaps, subscription.recipe,
                                              False, Timestamp.now().as_secs(), subscription.tier)

    def handle_nwc_request(self, nostr_event):
        print(nostr_event.as_json())
        sender = nostr_event.author().to_hex()
        if sender == self.keys.public_key().to_hex():
            return

        try:
            decrypted_text = nip04_decrypt(self.keys.secret_key(), nostr_event.author(), nostr_event.content())
            try:
                jsonevent = json.loads(decrypted_text)
                nwc = ""
                subscriber = ""
                for entry in jsonevent:
                    if entry[1] == "nwc":
                        nwc = entry[2]
                    elif entry[1] == "p":
                        subscriber = entry[2]

                subscriptionfilter = Filter().kind(EventDefinitions.KIND_NIP88_SUBSCRIBE_EVENT).author(
                    PublicKey.parse(subscriber)).limit(1)
                evts = self.client.get_events_of([subscriptionfilter], timedelta(seconds=3))

                if len(evts) > 0:
                    self.process_subscription_event(evts[0], nwc, subscriber)
            except Exception as e:
                print(f"Error processing JSON event: {e}")
        except Exception as e:
            print(f"Error decrypting event content: {e}")

    def process_subscription_event(self, subscription_event, nwc, subscriber):
        event7001id = subscription_event.id().to_hex()
        tier_dtag = ""
        recipient = ""
        cadence = ""
        unit = "msats"
        zaps = []
        tier = "DVM"
        overall_amount = 0
        subscription_event_id = ""

        for tag in subscription_event.tags():
            if tag.as_vec()[0] == "amount":
                overall_amount = int(tag.as_vec()[1])
                unit = tag.as_vec()[2]
                cadence = tag.as_vec()[3]
                print(f"{overall_amount} {unit} {cadence}")
            elif tag.as_vec()[0] == "p":
                recipient = tag.as_vec()[1]
            elif tag.as_vec()[0] == "e":
                subscription_event_id = tag.as_vec()[1]
            elif tag.as_vec()[0] == "event":
                jsonevent = json.loads(tag.as_vec()[1])
                subscription_event = Event.from_json(jsonevent)

                for tag in subscription_event.tags():
                    if tag.as_vec()[0] == "d":
                        tier_dtag = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "zap":
                        zaps.append(tag.as_vec())
                    elif tag.as_vec()[0] == "title":
                        tier = tag.as_vec()[1]

        if tier_dtag == "" or len(zaps) == 0:
            tierfilter = Filter().id(EventId.parse(subscription_event_id))
            evts = self.client.get_events_of([tierfilter], timedelta(seconds=3))
            if len(evts) > 0:
                for tag in evts[0].tags():
                    if tag.as_vec()[0] == "d":
                        tier_dtag = tag.as_vec()[0]

        isactivesubscription = False
        recipe = ""

        subscription = get_from_subscription_sql_table(self.dvm_config.DB, event7001id)
        zapsstr = json.dumps(zaps)
        print(zapsstr)
        success = True
        if subscription is None or subscription.end <= Timestamp.now().as_secs():
            # rather check nostr if our db is right
            subscription_status = nip88_has_active_subscription(
                PublicKey.parse(subscriber),
                tier_dtag, self.client, recipient, checkCanceled=False)

            if not subscription_status["isActive"]:

                success = self.pay_zap_split(nwc, overall_amount, zaps, tier, unit)
                start = Timestamp.now().as_secs()
                end = self.infer_subscription_end_time(start, cadence)
            else:
                start = Timestamp.now().as_secs()
                end = subscription_status["validUntil"]
        else:
            start = subscription.begin
            end = subscription.end

        if success:
            recipe = self.make_subscription_zap_recipe(event7001id, recipient, subscriber, start, end,
                                                       tier_dtag)
            print("RECIPE " + recipe)
            isactivesubscription = True

        if subscription is None:
            add_to_subscription_sql_table(self.dvm_config.DB, event7001id, recipient, subscriber, nwc,
                                          cadence, overall_amount, unit, start, end, tier_dtag,
                                          zapsstr, recipe, isactivesubscription,
                                          Timestamp.now().as_secs(), tier)
            print("new subscription entry")
        else:
            update_subscription_sql_table(self.dvm_config.DB, event7001id, recipient, subscriber, nwc,
                                          cadence, overall_amount, unit, start, end,
                                          tier_dtag, zapsstr, recipe, isactivesubscription,
                                          Timestamp.now().as_secs(), tier)
            print("updated subscription entry")

        self.send_status_success(subscription_event, "noogle.lol")

        message = ("Subscribed to DVM " + tier + ". Renewing on: " + str(
            Timestamp.from_secs(end).to_human_datetime().replace("Z", " ").replace("T", " ")))
        self.send_direct_message(subscriber, message)
