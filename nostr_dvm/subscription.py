import asyncio
import json
import math
import os
import signal
import time
from datetime import timedelta

from nostr_sdk import (Keys, Client, Timestamp, Filter, nip04_decrypt, HandleNotification, EventBuilder, PublicKey,
                       Options, Tag, Event, nip04_encrypt, NostrSigner, EventId, Nip19Event, nip44_decrypt, Kind)

from nostr_dvm.utils.database_utils import fetch_user_metadata
from nostr_dvm.utils.definitions import EventDefinitions, relay_timeout
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip88_utils import nip88_has_active_subscription
from nostr_dvm.utils.nip89_utils import NIP89Config
from nostr_dvm.utils.nostr_utils import send_event
from nostr_dvm.utils.nwc_tools import nwc_zap
from nostr_dvm.utils.subscription_utils import create_subscription_sql_table, add_to_subscription_sql_table, \
    get_from_subscription_sql_table, update_subscription_sql_table, get_all_subscriptions_from_sql_table, \
    delete_from_subscription_sql_table
from nostr_dvm.utils.zap_utils import create_bolt11_lud16, zaprequest


class Subscription:
    job_list: list

    # This is a simple list just to keep track which events we created and manage, so we don't pay for other requests
    def __init__(self, dvm_config, admin_config=None):
        asyncio.run(self.run_subscription(dvm_config, admin_config))

    async def run_subscription(self, dvm_config, admin_config):

        self.NAME = "Subscription Handler"
        dvm_config.DB = "db/" + "subscriptions" + ".db"
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

        pk = self.keys.public_key()

        self.job_list = []

        print("Nostr Subscription Handler public key: " + str(pk.to_bech32()) + " Hex: " + str(
            pk.to_hex()) + "\n")

        for relay in self.dvm_config.RELAY_LIST:
            await self.client.add_relay(relay)
        await self.client.connect()

        zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_ZAP]).since(Timestamp.now())
        cancel_subscription_filter = Filter().kinds([EventDefinitions.KIND_NIP88_STOP_SUBSCRIPTION_EVENT]).since(
            Timestamp.now())
        authors = []
        if admin_config is not None and len(admin_config.USERNPUBS) > 0:
            # we might want to limit which services can connect to the subscription handler
            for key in admin_config.USERNPUBS:
                authors.append(PublicKey.parse(key))
            dvm_filter = Filter().authors(authors).pubkey(pk).kinds(
                [EventDefinitions.KIND_NIP90_DVM_SUBSCRIPTION]).since(
                Timestamp.now())
        else:
            # or we don't
            dvm_filter = Filter().pubkey(pk).kinds(
                [EventDefinitions.KIND_NIP90_DVM_SUBSCRIPTION]).since(
                Timestamp.now())

        await self.client.subscribe([zap_filter, dvm_filter, cancel_subscription_filter], None)

        create_subscription_sql_table(dvm_config.DB)
        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            async def handle(self, relay_url, subscription_id, nostr_event: Event):
                if nostr_event.kind() == EventDefinitions.KIND_NIP90_DVM_SUBSCRIPTION:
                    await handle_nwc_request(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_NIP88_STOP_SUBSCRIPTION_EVENT:
                    await handle_cancel(nostr_event)

            async def handle_msg(self, relay_url, msg):
                return

        async def handle_cancel(nostr_event):
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
                subscription = get_from_subscription_sql_table(dvm_config.DB, kind7001eventid)

                if subscription is not None:
                    update_subscription_sql_table(dvm_config.DB, kind7001eventid, recipient,
                                                  subscription.subscriber, subscription.nwc, subscription.cadence,
                                                  subscription.amount, subscription.unit, subscription.begin,
                                                  subscription.end,
                                                  subscription.tier_dtag, subscription.zaps, subscription.recipe,
                                                  False, Timestamp.now().as_secs(), subscription.tier)

        # send_status_canceled(kind7001eventid, nostr_event) # TODO, waiting for spec

        def infer_subscription_end_time(start, cadence):
            end = start
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
            return end

        async def send_status_success(original_event, domain):

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

            keys = Keys.parse(dvm_config.PRIVATE_KEY)
            reaction_event = EventBuilder(EventDefinitions.KIND_FEEDBACK, str(content), reply_tags).to_event(keys)
            await send_event(reaction_event, client=self.client, dvm_config=self.dvm_config)
            print("[" + self.dvm_config.NIP89.NAME + "]" + ": Sent Kind " + str(
                EventDefinitions.KIND_FEEDBACK.as_u64()) + " Reaction: " + "success" + " " + reaction_event.as_json())

        async def pay_zap_split(nwc, overall_amount, zaps, tier, unit="msats"):
            overallsplit = 0

            for zap in zaps:
                print(zap)
                overallsplit += int(zap[3])

            print(overallsplit)
            zapped_amount = 0
            for zap in zaps:
                if zap[1] == "":
                    # If the client did decide to not add itself to the zap split, or if a slot is left we add the subscription service in the empty space
                    zap[1] = Keys.parse(self.dvm_config.PRIVATE_KEY).public_key().to_hex()

                name, nip05, lud16 = await fetch_user_metadata(zap[1], self.client)
                splitted_amount = math.floor(
                    (int(zap[3]) / overallsplit) * int(overall_amount) / 1000)
                # invoice = create_bolt11_lud16(lud16, splitted_amount)
                # TODO add details about DVM in message

                invoice = zaprequest(lud16, splitted_amount, tier, None,
                                     PublicKey.parse(zap[1]), self.keys, DVMConfig.RELAY_LIST)
                print(invoice)
                if invoice is not None:
                    nwc_event_id = await nwc_zap(nwc, invoice, self.keys, zap[2])
                    if nwc_event_id is None:
                        print("error zapping " + lud16)
                    else:
                        zapped_amount = zapped_amount + (splitted_amount * 1000)
                        print(str(zapped_amount) + "/" + str(overall_amount))

            if zapped_amount < overall_amount * 0.8:  # TODO how do we handle failed zaps for some addresses? we are ok with 80% for now
                # if zapped_amount < int(zaps[0][3]):

                success = False
            else:
                success = True
                # if no active subscription exists OR the subscription ended, pay

            return success

        async def make_subscription_zap_recipe(event7001, recipient, subscriber, start, end, tier_dtag):
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
                await client.add_relay(relay)
            await client.connect()
            recipe = await client.send_event(event)
            recipe_id = recipe.id
            await client.shutdown()
            recipe = recipe_id.to_hex()
            return recipe

        async def handle_nwc_request(nostr_event):
            print(nostr_event.as_json())
            sender = nostr_event.author().to_hex()
            if sender == self.keys.public_key().to_hex():
                return

            try:
                decrypted_text = nip04_decrypt(self.keys.secret_key(), nostr_event.author(), nostr_event.content())
                subscriber = ""
                nwc = ""
                try:
                    jsonevent = json.loads(decrypted_text)
                    for entry in jsonevent:
                        if entry[1] == "nwc":
                            nwc = entry[2]
                        elif entry[1] == "p":
                            subscriber = entry[2]

                    subscriptionfilter = Filter().kind(EventDefinitions.KIND_NIP88_SUBSCRIBE_EVENT).author(
                        PublicKey.parse(subscriber)).limit(1)
                    evts = await self.client.get_events_of([subscriptionfilter], relay_timeout)
                    if len(evts) > 0:
                        event7001id = evts[0].id().to_hex()
                        print(evts[0].as_json())
                        tier_dtag = ""
                        recipient = ""
                        cadence = ""
                        unit = "msats"
                        zaps = []
                        tier = "DVM"
                        overall_amount = 0
                        subscription_event_id = ""
                        for tag in evts[0].tags():
                            if tag.as_vec()[0] == "amount":
                                overall_amount = int(tag.as_vec()[1])

                                unit = tag.as_vec()[2]
                                cadence = tag.as_vec()[3]
                                print(str(overall_amount) + " " + unit + " " + cadence)
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
                            evts = await self.client.get_events_of([tierfilter], relay_timeout)
                            if len(evts) > 0:
                                for tag in evts[0].tags():
                                    if tag.as_vec()[0] == "d":
                                        tier_dtag = tag.as_vec()[0]

                        isactivesubscription = False
                        recipe = ""
                        subscription = get_from_subscription_sql_table(dvm_config.DB, event7001id)

                        zapsstr = json.dumps(zaps)
                        print(zapsstr)
                        success = True
                        if subscription is None or subscription.end <= Timestamp.now().as_secs():
                            # rather check nostr if our db is right
                            subscription_status = await nip88_has_active_subscription(
                                PublicKey.parse(subscriber),
                                tier_dtag, self.client, recipient, checkCanceled=False)

                            if not subscription_status["isActive"]:
                                start = Timestamp.now().as_secs()
                                end = infer_subscription_end_time(start, cadence)

                                # we add or update the subscription in the db, with non-active subscription to avoid double payments
                                if subscription is None:
                                    add_to_subscription_sql_table(dvm_config.DB, event7001id, recipient, subscriber,
                                                                  nwc,
                                                                  cadence, overall_amount, unit, start, end, tier_dtag,
                                                                  zapsstr, recipe, isactivesubscription,
                                                                  Timestamp.now().as_secs(), tier)
                                    print("new subscription entry before payment")
                                else:
                                    update_subscription_sql_table(dvm_config.DB, event7001id, recipient, subscriber,
                                                                  nwc,
                                                                  cadence, overall_amount, unit, start, end,
                                                                  tier_dtag, zapsstr, recipe, isactivesubscription,
                                                                  Timestamp.now().as_secs(), tier)
                                    print("updated subscription entry before payment")

                                # we attempt to pay the subscription
                                success = await pay_zap_split(nwc, overall_amount, zaps, tier, unit)

                            else:
                                start = Timestamp.now().as_secs()
                                end = subscription_status["validUntil"]
                        else:
                            start = subscription.begin
                            end = subscription.end

                        if success:
                            # we create a payment recipe
                            recipe = await make_subscription_zap_recipe(event7001id, recipient, subscriber, start, end,
                                                                        tier_dtag)
                            print("RECIPE " + recipe)
                            isactivesubscription = True

                            # we then update the subscription based on payment success
                            update_subscription_sql_table(dvm_config.DB, event7001id, recipient, subscriber, nwc,
                                                          cadence, overall_amount, unit, start, end,
                                                          tier_dtag, zapsstr, recipe, isactivesubscription,
                                                          Timestamp.now().as_secs(), tier)
                            print("updated subscription entry after payment")

                            await send_status_success(nostr_event, "noogle.lol")

                            keys = Keys.parse(dvm_config.PRIVATE_KEY)
                            message = ("Subscribed to DVM " + tier + ". Renewing on: " + str(
                                Timestamp.from_secs(end).to_human_datetime().replace("Z", " ").replace("T",
                                                                                                       " ") + " GMT"))
                            evt = EventBuilder.encrypted_direct_msg(keys, PublicKey.parse(subscriber), message,
                                                                    None).to_event(keys)
                            await send_event(evt, client=self.client, dvm_config=dvm_config)



                except Exception as e:
                    print(e)

            except Exception as e:
                print("Error in Subscriber " + str(e))

        def handle_expired_subscription(subscription):
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
                delete_from_subscription_sql_table(dvm_config.DB, subscription.id)
                print("Delete expired subscription")

        async def handle_subscription_renewal(subscription):
            zaps = json.loads(subscription.zaps)
            success = await pay_zap_split(subscription.nwc, subscription.amount, zaps, subscription.tier,
                                          subscription.unit)
            if success:
                end = infer_subscription_end_time(Timestamp.now().as_secs(), subscription.cadence)
                recipe = await make_subscription_zap_recipe(subscription.id, subscription.recipent,
                                                            subscription.subscriber, subscription.begin,
                                                            end, subscription.tier_dtag)
            else:
                end = Timestamp.now().as_secs()
                recipe = subscription.recipe

            update_subscription_sql_table(dvm_config.DB, subscription.id,
                                          subscription.recipent,
                                          subscription.subscriber, subscription.nwc,
                                          subscription.cadence, subscription.amount,
                                          subscription.unit,
                                          subscription.begin, end,
                                          subscription.tier_dtag, subscription.zaps, recipe,
                                          success,
                                          Timestamp.now().as_secs(), subscription.tier)

            print("updated subscription entry")

            keys = Keys.parse(dvm_config.PRIVATE_KEY)
            message = (
                    "Renewed Subscription to DVM " + subscription.tier + ". Next renewal: " + str(
                Timestamp.from_secs(end).to_human_datetime().replace("Z", " ").replace("T",
                                                                                       " ")))
            evt = EventBuilder.encrypted_direct_msg(keys, PublicKey.parse(subscription.subscriber),
                                                    message,
                                                    None).to_event(keys)
            await send_event(evt, client=self.client, dvm_config=dvm_config)

        async def check_subscriptions():
            try:
                subscriptions = get_all_subscriptions_from_sql_table(dvm_config.DB)

                for subscription in subscriptions:
                    if subscription.active:
                        if subscription.end < Timestamp.now().as_secs():
                            # We could directly zap, but let's make another check if our subscription expired
                            subscription_status = await nip88_has_active_subscription(
                                PublicKey.parse(subscription.subscriber),
                                subscription.tier_dtag, self.client, subscription.recipent)

                            if subscription_status["expires"]:
                                # if subscription expires, just note it as not active
                                update_subscription_sql_table(dvm_config.DB, subscription_status["subscriptionId"],
                                                              subscription.recipent,
                                                              subscription.subscriber, subscription.nwc,
                                                              subscription.cadence, subscription.amount,
                                                              subscription.unit,
                                                              subscription.begin, subscription.end,
                                                              subscription.tier_dtag, subscription.zaps,
                                                              subscription.recipe,
                                                              False,
                                                              Timestamp.now().as_secs(), subscription.tier)
                            else:
                                await handle_subscription_renewal(subscription)

                    else:
                        handle_expired_subscription(subscription)

                print(str(Timestamp.now().as_secs()) + ": Checking " + str(
                    len(subscriptions)) + " Subscription entries..")
            except Exception as e:
                print(e)

        asyncio.create_task(self.client.handle_notifications(NotificationHandler()))

        try:
            while True:
                await asyncio.sleep(60.0)
                await check_subscriptions()
        except KeyboardInterrupt:
            print('Stay weird!')
            os.kill(os.getpid(), signal.SIGTERM)
