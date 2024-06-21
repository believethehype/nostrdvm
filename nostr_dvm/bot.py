import asyncio
import json
import os
import signal
import time
from datetime import timedelta

from nostr_sdk import (Keys, Client, Timestamp, Filter, nip04_decrypt, HandleNotification, EventBuilder, PublicKey,
                       Options, Tag, Event, nip04_encrypt, NostrSigner, EventId, Nip19Event, Kind, KindEnum,
                       UnsignedEvent, UnwrappedGift)

from nostr_dvm.utils.admin_utils import admin_make_database_updates
from nostr_dvm.utils.database_utils import get_or_add_user, update_user_balance, create_sql_table, update_sql_table
from nostr_dvm.utils.definitions import EventDefinitions, InvoiceToWatch
from nostr_dvm.utils.nip89_utils import nip89_fetch_events_pubkey, NIP89Config
from nostr_dvm.utils.nostr_utils import send_event
from nostr_dvm.utils.output_utils import PostProcessFunctionType, post_process_list_to_users, \
    post_process_list_to_events
from nostr_dvm.utils.zap_utils import parse_zap_event_tags, pay_bolt11_ln_bits, zaprequest, create_bolt11_ln_bits, \
    check_bolt11_ln_bits_is_paid, parse_amount_from_bolt11_invoice
from nostr_dvm.utils.cashu_utils import redeem_cashu


class Bot:
    job_list: list
    invoice_list: list

    # This is a simple list just to keep track which events we created and manage, so we don't pay for other requests

    def __init__(self, dvm_config, admin_config=None):
        asyncio.run(self.run_bot(dvm_config, admin_config))

        # add_sql_table_column(dvm_config.DB)

    async def run_bot(self, dvm_config, admin_config):
        self.NAME = "Bot"
        dvm_config.DB = "db/" + self.NAME + ".db"
        self.dvm_config = dvm_config
        nip89config = NIP89Config()
        nip89config.PK = self.dvm_config.PRIVATE_KEY
        self.dvm_config.NIP89 = nip89config
        self.admin_config = admin_config
        self.keys = Keys.parse(dvm_config.PRIVATE_KEY)

        wait_for_send = True
        skip_disconnected_relays = True
        opts = (Options().wait_for_send(wait_for_send).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT))
                .skip_disconnected_relays(skip_disconnected_relays))
        signer = NostrSigner.keys(self.keys)
        self.client = Client.with_opts(signer, opts)
        self.invoice_list = []

        pk = self.keys.public_key()

        self.job_list = []

        print("Nostr BOT public key: " + str(pk.to_bech32()) + " Hex: " + str(pk.to_hex()) + " Name: " + self.NAME)  # +
        # " Supported DVM tasks: " +
        # ', '.join(p.NAME + ":" + p.TASK for p in self.dvm_config.SUPPORTED_DVMS) + "\n")

        for relay in self.dvm_config.RELAY_LIST:
            await self.client.add_relay(relay)
        await self.client.connect()

        zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_ZAP]).since(Timestamp.now())
        dm_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM]).since(Timestamp.now())
        nip17_filter = Filter().pubkey(pk).kinds([Kind.from_enum(KindEnum.GIFT_WRAP())]).limit(0)
        kinds = [EventDefinitions.KIND_NIP90_GENERIC, EventDefinitions.KIND_FEEDBACK]
        for dvm in self.dvm_config.SUPPORTED_DVMS:
            if dvm.KIND not in kinds:
                kinds.append(Kind(dvm.KIND.as_u64() + 1000))
        dvm_filter = (Filter().kinds(kinds).since(Timestamp.now()))

        await self.client.subscribe([zap_filter, dm_filter, nip17_filter, dvm_filter], None)

        create_sql_table(self.dvm_config.DB)
        await admin_make_database_updates(adminconfig=self.admin_config, dvmconfig=self.dvm_config, client=self.client)

        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            async def handle(self, relay_url, subscription_id, nostr_event):
                if (EventDefinitions.KIND_NIP90_EXTRACT_TEXT.as_u64() + 1000 <= nostr_event.kind().as_u64()
                        <= EventDefinitions.KIND_NIP90_GENERIC.as_u64() + 1000):
                    await handle_nip90_response_event(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_FEEDBACK:
                    await handle_nip90_feedback(nostr_event)

                elif nostr_event.kind() == EventDefinitions.KIND_ZAP:
                    await handle_zap(nostr_event)

                elif nostr_event.kind() == EventDefinitions.KIND_DM:
                    try:
                        await handle_dm(nostr_event, False)
                    except Exception as e:
                        print(f"Error during content NIP04 decryption: {e}")
                elif nostr_event.kind().as_enum() == KindEnum.GIFT_WRAP():
                    try:
                        await handle_dm(nostr_event, True)
                    except Exception as e:
                        print(f"Error during content NIP59 decryption: {e}")

            async def handle_msg(self, relay_url, msg):
                return

        async def handle_dm(nostr_event, giftwrap):
            sender = nostr_event.author().to_hex()
            if sender == self.keys.public_key().to_hex():
                return
            decrypted_text = ""
            try:
                sealed = " "
                if giftwrap:
                    try:
                        # Extract rumor
                        unwrapped_gift = UnwrappedGift.from_gift_wrap(self.keys, nostr_event)
                        sender = unwrapped_gift.sender().to_hex()
                        rumor: UnsignedEvent = unwrapped_gift.rumor()

                        # client.send_sealed_msg(sender, f"Echo: {msg}", None)
                        if rumor.created_at().as_secs() >= Timestamp.now().as_secs():
                            if rumor.kind().as_enum() == KindEnum.PRIVATE_DIRECT_MESSAGE():
                                print(f"Received new msg [sealed]: {decrypted_text}")
                                decrypted_text = rumor.content()
                                sealed = " [sealed] "
                            else:
                                print(f"{rumor.as_json()}")


                    except Exception as e:
                        print(f"Error during content NIP59 decryption: {e}")

                else:
                    try:
                        decrypted_text = nip04_decrypt(self.keys.secret_key(), nostr_event.author(),
                                                       nostr_event.content())
                    except Exception as e:
                        print(f"Error during content NIP04 decryption: {e}")

                if decrypted_text != "":
                    user = await get_or_add_user(db=self.dvm_config.DB, npub=sender, client=self.client,
                                                 config=self.dvm_config)

                    print("[" + self.NAME + "]" + sealed + "Message from " + user.name + ": " + decrypted_text)

                    # if user selects an index from the overview list...
                    if decrypted_text != "" and decrypted_text[0].isdigit():

                        split = decrypted_text.split(' ')
                        index = int(split[0]) - 1
                        # if user sends index info, e.g. 1 info, we fetch the nip89 information and reply with it.
                        if len(split) > 1 and split[1].lower() == "info":
                            await answer_nip89(nostr_event, index, giftwrap, sender)
                        # otherwise we probably have to do some work, so build an event from input and send it to the DVM
                        else:
                            task = self.dvm_config.SUPPORTED_DVMS[index].TASK
                            print("[" + self.NAME + "] Request from " + str(user.name) + " (" + str(user.nip05) +
                                  ", Balance: " + str(user.balance) + " Sats) Task: " + str(task))

                            if user.isblacklisted:
                                # If users are blacklisted for some reason, tell them.
                                answer_blacklisted(nostr_event, giftwrap, sender)

                            else:
                                # Parse inputs to params
                                tags = build_params(decrypted_text, sender, index)
                                p_tag = Tag.parse(['p', self.dvm_config.SUPPORTED_DVMS[index].PUBLIC_KEY])

                                if self.dvm_config.SUPPORTED_DVMS[index].SUPPORTS_ENCRYPTION:
                                    tags_str = []
                                    for tag in tags:
                                        tags_str.append(tag.as_vec())
                                    params_as_str = json.dumps(tags_str)
                                    print(params_as_str)
                                    #  and encrypt them
                                    encrypted_params = nip04_encrypt(self.keys.secret_key(),
                                                                     PublicKey.from_hex(
                                                                         self.dvm_config.SUPPORTED_DVMS[
                                                                             index].PUBLIC_KEY),
                                                                     params_as_str)
                                    #  add encrypted and p tag on the outside
                                    encrypted_tag = Tag.parse(['encrypted'])
                                    #  add the encrypted params to the content
                                    nip90request = (EventBuilder(self.dvm_config.SUPPORTED_DVMS[index].KIND,
                                                                 encrypted_params, [p_tag, encrypted_tag]).
                                                    to_event(self.keys))
                                else:
                                    tags.append(p_tag)

                                    nip90request = (EventBuilder(self.dvm_config.SUPPORTED_DVMS[index].KIND,
                                                                 "", tags).
                                                    to_event(self.keys))

                                # remember in the job_list that we have made an event, if anybody asks for payment,
                                # we know we actually sent the request
                                entry = {"npub": user.npub, "event_id": nip90request.id().to_hex(),
                                         "dvm_key": self.dvm_config.SUPPORTED_DVMS[index].PUBLIC_KEY, "is_paid": False,
                                         "giftwrap": giftwrap}
                                self.job_list.append(entry)

                                # send the event to the DVM
                                await send_event(nip90request, client=self.client, dvm_config=self.dvm_config)
                                # print(nip90request.as_json())


                    elif decrypted_text.lower().startswith("invoice"):
                        requests_rq = False
                        amount_str = decrypted_text.lower().split(" ")[1]
                        if amount_str == "qr":
                            amount_str = decrypted_text.lower().split(" ")[2]
                            requests_rq = True
                        try:
                            amount = int(amount_str)
                        except:
                            amount = 100

                        invoice, hash = create_bolt11_ln_bits(amount, self.dvm_config)
                        expires = nostr_event.created_at().as_secs() + (60 * 60 * 24)
                        qr_code = "https://qrcode.tec-it.com/API/QRCode?data=" + invoice + "&backcolor=%23ffffff&size=small&quietzone=1&errorcorrection=H"

                        self.invoice_list.append(
                            InvoiceToWatch(sender=sender, bolt11=invoice, payment_hash=hash, is_paid=False,
                                           expires=expires, amount=amount))

                        if requests_rq:
                            message = invoice + "\n" + qr_code
                        else:
                            message = invoice
                        if giftwrap:
                            await self.client.send_private_msg(PublicKey.parse(sender), message, None)
                        else:
                            await asyncio.sleep(2.0)
                            evt = EventBuilder.encrypted_direct_msg(self.keys, PublicKey.parse(sender),
                                                                    message, None).to_event(self.keys)
                            await send_event(evt, client=self.client, dvm_config=dvm_config)


                    elif decrypted_text.lower().startswith("balance"):
                        await asyncio.sleep(2.0)
                        message = "Your current balance is " + str(user.balance) + (" Sats. Zap me to add to your "
                                                                                    "balance. I will use your "
                                                                                    "balance interact with the DVMs "
                                                                                    "for you.\nI support both "
                                                                                    "public and private Zaps, "
                                                                                    "as well as "
                                                                                    "Zapplepay.\nOr write \"invoice "
                                                                                    "100\" to receive an invoice of "
                                                                                    "100 sats (or any other amount) "
                                                                                    "to top up your balance")
                        if giftwrap:
                            await self.client.send_private_msg(PublicKey.parse(sender), message, None)
                        else:
                            evt = EventBuilder.encrypted_direct_msg(self.keys, PublicKey.parse(sender),
                                                                    message, None).to_event(self.keys)
                            await send_event(evt, client=self.client, dvm_config=dvm_config)
                    elif decrypted_text.startswith("cashuA"):
                        print("Received Cashu token:" + decrypted_text)
                        cashu_redeemed, cashu_message, total_amount, fees = await redeem_cashu(decrypted_text,
                                                                                               self.dvm_config,
                                                                                               self.client)
                        print(cashu_message)
                        if cashu_message == "success":
                            await update_user_balance(self.dvm_config.DB, sender, total_amount, client=self.client,
                                                      config=self.dvm_config)
                        else:
                            await asyncio.sleep(2.0)
                            message = "Error: " + cashu_message + ". Token has not been redeemed."

                            if giftwrap:
                                await self.client.send_private_msg(PublicKey.parse(sender), message, None)
                            else:
                                evt = EventBuilder.encrypted_direct_msg(self.keys, PublicKey.from_hex(sender), message,
                                                                        None).to_event(self.keys)
                                await send_event(evt, client=self.client, dvm_config=self.dvm_config)
                    elif decrypted_text.lower().startswith("what's the second best"):
                        await asyncio.sleep(2.0)
                        message = "No, there is no second best.\n\nhttps://cdn.nostr.build/p/mYLv.mp4"
                        if giftwrap:
                            await self.client.send_private_msg(PublicKey.parse(sender), message, None)
                        else:
                            evt = await EventBuilder.encrypted_direct_msg(self.keys, PublicKey.parse(sender),
                                                                          message,
                                                                          nostr_event.id()).to_event(self.keys)
                            await send_event(evt, client=self.client, dvm_config=self.dvm_config)

                    else:
                        # Build an overview of known DVMs and send it to the user
                        await answer_overview(nostr_event, giftwrap, sender)

            except Exception as e:
                print("Error in bot " + str(e))

        async def handle_nip90_feedback(nostr_event):
            # print(nostr_event.as_json())
            try:
                is_encrypted = False
                status = ""
                etag = ""
                ptag = ""
                content = nostr_event.content()
                for tag in nostr_event.tags():
                    if tag.as_vec()[0] == "status":
                        status = tag.as_vec()[1]
                        if len(tag.as_vec()) > 2:
                            content = tag.as_vec()[2]
                    elif tag.as_vec()[0] == "e":
                        etag = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "p":
                        ptag = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "encrypted":
                        is_encrypted = True

                if is_encrypted:
                    if ptag == self.keys.public_key().to_hex():
                        tags_str = nip04_decrypt(Keys.parse(dvm_config.PRIVATE_KEY).secret_key(),
                                                 nostr_event.author(), nostr_event.content())
                        params = json.loads(tags_str)
                        params.append(Tag.parse(["p", ptag]).as_vec())
                        params.append(Tag.parse(["encrypted"]).as_vec())
                        event_as_json = json.loads(nostr_event.as_json())
                        event_as_json['tags'] = params
                        event_as_json['content'] = ""
                        nostr_event = Event.from_json(json.dumps(event_as_json))

                        for tag in nostr_event.tags():
                            if tag.as_vec()[0] == "status":
                                status = tag.as_vec()[1]
                                if len(tag.as_vec()) > 2:
                                    content = tag.as_vec()[2]
                            elif tag.as_vec()[0] == "e":
                                etag = tag.as_vec()[1]
                            elif tag.as_vec()[0] == "content":
                                content = tag.as_vec()[1]

                    else:
                        return

                if status == "success" or status == "error" or status == "processing" or status == "partial" and content != "":
                    entry = next((x for x in self.job_list if x['event_id'] == etag), None)
                    if entry is not None and entry['dvm_key'] == nostr_event.author().to_hex():
                        user = await get_or_add_user(db=self.dvm_config.DB, npub=entry['npub'],
                                                     client=self.client, config=self.dvm_config)
                        await asyncio.sleep(2.0)
                        if entry["giftwrap"]:
                            await self.client.send_private_msg(PublicKey.parse(entry["npub"]), content, None)
                        else:
                            reply_event = EventBuilder.encrypted_direct_msg(self.keys,
                                                                            PublicKey.from_hex(entry['npub']),
                                                                            content,
                                                                            None).to_event(self.keys)

                            await send_event(reply_event, client=self.client, dvm_config=dvm_config)
                        print(status + ": " + content)
                        print(
                            "[" + self.NAME + "] Received reaction from " + nostr_event.author().to_hex() + " message to orignal sender " + user.name)

                elif status == "payment-required" or status == "partial":
                    for tag in nostr_event.tags():
                        if tag.as_vec()[0] == "amount":
                            amount_msats = int(tag.as_vec()[1])
                            amount = int(amount_msats / 1000)
                            entry = next((x for x in self.job_list if x['event_id'] == etag), None)
                            if entry is not None and entry['is_paid'] is False and entry[
                                'dvm_key'] == nostr_event.author().to_hex():
                                # if we get a bolt11, we pay and move on
                                user = await get_or_add_user(db=self.dvm_config.DB, npub=entry["npub"],
                                                             client=self.client, config=self.dvm_config)
                                if user.balance >= amount:
                                    balance = max(user.balance - amount, 0)
                                    update_sql_table(db=self.dvm_config.DB, npub=user.npub, balance=balance,
                                                     iswhitelisted=user.iswhitelisted, isblacklisted=user.isblacklisted,
                                                     nip05=user.nip05, lud16=user.lud16, name=user.name,
                                                     lastactive=Timestamp.now().as_secs(), subscribed=user.subscribed)

                                    message = "Paid " + str(
                                        amount) + " Sats from balance to DVM. New balance is " + str(
                                        balance) + " Sats.\n"
                                    if entry["giftwrap"]:
                                        await self.client.send_private_msg(PublicKey.parse(entry["npub"]), message,
                                                                           None)
                                    else:
                                        evt = EventBuilder.encrypted_direct_msg(self.keys,
                                                                                PublicKey.parse(entry["npub"]),
                                                                                message,
                                                                                None).to_event(self.keys)
                                        await send_event(evt, client=self.client, dvm_config=dvm_config)
                                    print(
                                        "[" + self.NAME + "] Replying " + user.name + " with \"scheduled\" confirmation")

                                else:
                                    print("Bot payment-required")
                                    await asyncio.sleep(2.0)
                                    evt = EventBuilder.encrypted_direct_msg(self.keys,
                                                                            PublicKey.parse(entry["npub"]),
                                                                            "Current balance: " + str(
                                                                                user.balance) + " Sats. Balance of " + str(
                                                                                amount) + " Sats required. Please zap me with at least " +
                                                                            str(int(amount - user.balance))
                                                                            + " Sats, then try again.",
                                                                            None).to_event(self.keys)
                                    await send_event(evt, client=self.client, dvm_config=dvm_config)
                                    return

                                if len(tag.as_vec()) > 2:
                                    bolt11 = tag.as_vec()[2]
                                # else we create a zap
                                else:
                                    user = await get_or_add_user(db=self.dvm_config.DB,
                                                                 npub=nostr_event.author().to_hex(),
                                                                 client=self.client, config=self.dvm_config)
                                    print("Paying: " + user.name)
                                    bolt11 = zaprequest(user.lud16, amount, "Zap", nostr_event, self.keys,
                                                        self.dvm_config,
                                                        "private")
                                    if bolt11 is None:
                                        print("Receiver has no Lightning address")
                                        return
                                try:
                                    print(bolt11)
                                    payment_hash = pay_bolt11_ln_bits(bolt11, self.dvm_config)
                                    self.job_list[self.job_list.index(entry)]['is_paid'] = True
                                    print("[" + self.NAME + "] payment_hash: " + payment_hash +
                                          " Forwarding payment of " + str(amount) + " Sats to DVM")
                                except Exception as e:
                                    print(e)


            except Exception as e:
                print(str(e))

        async def handle_nip90_response_event(nostr_event: Event):
            try:
                ptag = ""
                etag = ""
                is_encrypted = False
                for tag in nostr_event.tags():
                    if tag.as_vec()[0] == "e":
                        etag = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "p":
                        ptag = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "encrypted":
                        is_encrypted = True

                entry = next((x for x in self.job_list if x['event_id'] == etag), None)
                if entry is not None and entry[
                    'dvm_key'] == nostr_event.author().to_hex():
                    print(entry)
                    user = await get_or_add_user(db=self.dvm_config.DB, npub=entry['npub'],
                                                 client=self.client, config=self.dvm_config)

                    self.job_list.remove(entry)
                    content = nostr_event.content()
                    if is_encrypted:
                        if ptag == self.keys.public_key().to_hex():
                            content = nip04_decrypt(self.keys.secret_key(), nostr_event.author(), content)
                        else:
                            return

                    dvms = [x for x in self.dvm_config.SUPPORTED_DVMS if
                            x.PUBLIC_KEY == nostr_event.author().to_hex() and x.KIND.as_u64() == nostr_event.kind().as_u64() - 1000]
                    if len(dvms) > 0:
                        dvm = dvms[0]
                        if dvm.dvm_config.EXTERNAL_POST_PROCESS_TYPE != PostProcessFunctionType.NONE:
                            if dvm.dvm_config.EXTERNAL_POST_PROCESS_TYPE == PostProcessFunctionType.LIST_TO_EVENTS:
                                content = post_process_list_to_events(content)
                            elif dvm.dvm_config.EXTERNAL_POST_PROCESS_TYPE == PostProcessFunctionType.LIST_TO_USERS:
                                content = post_process_list_to_users(content)

                    print("[" + self.NAME + "] Received results, message to orignal sender " + user.name)
                    await asyncio.sleep(2.0)
                    if entry["giftwrap"]:
                        await self.client.send_private_msg(PublicKey.parse(user.npub), content, None)
                    else:
                        reply_event = EventBuilder.encrypted_direct_msg(self.keys,
                                                                        PublicKey.parse(user.npub),
                                                                        content,
                                                                        None).to_event(self.keys)
                        await send_event(reply_event, client=self.client, dvm_config=dvm_config)

            except Exception as e:
                print(e)

        async def handle_zap(zap_event):
            print("[" + self.NAME + "] Zap received")
            try:
                invoice_amount, zapped_event, sender, message, anon = await parse_zap_event_tags(zap_event,
                                                                                                 self.keys, self.NAME,
                                                                                                 self.client,
                                                                                                 self.dvm_config)

                etag = ""
                print(zap_event.tags())
                print(zapped_event.tags())
                for tag in zapped_event.tags():
                    if tag.as_vec()[0] == "e":
                        etag = tag.as_vec()[1]

                user = await get_or_add_user(self.dvm_config.DB, sender, client=self.client, config=self.dvm_config)

                entry = next((x for x in self.job_list if x['event_id'] == etag), None)
                print(entry)
                # print(entry['dvm_key'])
                # print(str(zapped_event.author().to_hex()))
                # print(str(zap_event.author().to_hex()))
                print(sender)
                if entry is not None and entry['is_paid'] is True and entry['dvm_key'] == sender:
                    # if we get a bolt11, we pay and move on
                    user = await get_or_add_user(db=self.dvm_config.DB, npub=entry["npub"],
                                                 client=self.client, config=self.dvm_config)

                    sender = user.npub

                if zapped_event is not None:
                    if not anon:
                        print("[" + self.NAME + "] Note Zap received for Bot balance: " + str(
                            invoice_amount) + " Sats from " + str(
                            user.name))
                        await update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client,
                                                  config=self.dvm_config)

                        # a regular note
                elif not anon:
                    print("[" + self.NAME + "] Profile Zap received for Bot balance: " + str(
                        invoice_amount) + " Sats from " + str(
                        user.name))
                    await update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client,
                                              config=self.dvm_config)

            except Exception as e:
                print("[" + self.NAME + "] Error during content decryption:" + str(e))

        async def answer_overview(nostr_event, giftwrap, sender):
            message = "DVMs that I support:\n\n"
            index = 1
            for p in self.dvm_config.SUPPORTED_DVMS:
                if p.PER_UNIT_COST != 0 and p.PER_UNIT_COST is not None:
                    message += (str(index) + " " + p.NAME + " " + p.TASK + "\n\t" + str(p.FIX_COST) +
                                " Sats + " + str(p.PER_UNIT_COST) + " Sats per Second\n\n")
                else:
                    message += (str(index) + " " + p.NAME + " " + p.TASK + "\n\t" + str(p.FIX_COST) +
                                " Sats\n\n")
                index += 1

            await asyncio.sleep(2.0)

            text = message + "\nSelect an Index and provide an input (e.g. \"2 A purple ostrich\")\nType \"index info\" to learn more about each DVM. (e.g. \"2 info\")\n\n Type \"balance\" to see your current balance"
            if giftwrap:
                await self.client.send_private_msg(PublicKey.parse(sender), text, None)
            else:
                evt = EventBuilder.encrypted_direct_msg(self.keys, PublicKey.parse(sender),
                                                        text,
                                                        nostr_event.id()).to_event(self.keys)

                await send_event(evt, client=self.client, dvm_config=dvm_config)

        def answer_blacklisted(nostr_event, giftwrap, sender):
            message = "Your are currently blocked from this service."
            if giftwrap:
                self.client.send_sealed_msg(PublicKey.parse(sender), message, None)
            else:
                # For some reason an admin might blacklist npubs, e.g. for abusing the service
                evt = EventBuilder.encrypted_direct_msg(self.keys, nostr_event.author(),
                                                        message, None).to_event(self.keys)
                send_event(evt, client=self.client, dvm_config=dvm_config)

        async def answer_nip89(nostr_event, index, giftwrap, sender):
            info = await print_dvm_info(self.client, index)
            if info is None:
                info = "No NIP89 Info found for " + self.dvm_config.SUPPORTED_DVMS[index].NAME
            await asyncio.sleep(2.0)

            if giftwrap:
                await self.client.send_private_msg(PublicKey.parse(sender), info, None)
            else:
                evt = EventBuilder.encrypted_direct_msg(self.keys, nostr_event.author(),
                                                        info, None).to_event(self.keys)
                await send_event(evt, client=self.client, dvm_config=dvm_config)

        def build_params(decrypted_text, author, index):
            tags = []
            splitzero = decrypted_text.split(' -')
            split = splitzero[0].split(' ')
            # If only a command without parameters is sent, we assume no input is required, and that means the dvm might take in the user as input (e.g. for content discovery)
            if len(split) == 1:
                remaining_text = decrypted_text.replace(split[0], "")
                params = remaining_text.split(" -")
                tag = Tag.parse(["param", "user", author])
                tags.append(tag)
                for i in params:
                    print(i)
                    if i != " ":
                        try:
                            split = i.split(" ")
                            if len(split) > 1:
                                param = str(split[0])
                                print(str(param))
                                value = str(split[1])
                                print(str(value))
                                if param == "cashu":
                                    tag = Tag.parse([param, value])
                                else:
                                    if param == "user":
                                        if value.startswith("@") or value.startswith("nostr:") or value.startswith(
                                                "npub"):
                                            value = PublicKey.from_bech32(
                                                value.replace("@", "").replace("nostr:", "")).to_hex()
                                    tag = Tag.parse(["param", param, value])
                                tags.append(tag)
                        except Exception as e:
                            print(e)
                            print("Couldn't add " + str(i))
                        output = Tag.parse(["output", "text/plain"])
                        tags.append(output)
                        relay_list = ["relays"]
                        for relay in self.dvm_config.RELAY_LIST:
                            relay_list.append(relay)

                        relays = Tag.parse(relay_list)
                        tags.append(relays)

                return tags

            tags = []
            command = decrypted_text.replace(split[0] + " ", "")
            split = command.split(" -")
            input = split[0].rstrip()
            if input.startswith("http"):
                temp = input.split(" ")
                if len(temp) > 1:
                    input_type = "url"
                    i_tag1 = Tag.parse(["i", temp[0], input_type])
                    tags.append(i_tag1)
                    input_type = "text"
                    i_tag2 = Tag.parse(["i", input.replace(temp[0], "").lstrip(), input_type])
                    tags.append(i_tag2)
                else:
                    input_type = "url"
                    i_tag = Tag.parse(["i", input, input_type])
                    tags.append(i_tag)
            elif (input.startswith("nevent") or input.startswith("nostr:nevent") or input.startswith("note") or
                  input.startswith("nostr:note")):
                input_type = "event"
                if str(input).startswith('note'):
                    event_id = EventId.from_bech32(input)
                elif str(input).startswith("nevent"):
                    event_id = Nip19Event.from_bech32(input).event_id()
                elif str(input).startswith('nostr:note'):
                    event_id = EventId.from_nostr_uri(input)
                elif str(input).startswith("nostr:nevent"):
                    event_id = Nip19Event.from_nostr_uri(input).event_id()
                else:
                    event_id = EventId.from_hex(input)
                i_tag = Tag.parse(["i", event_id.to_hex(), input_type])
                tags.append(i_tag)
            else:
                print(input)
                input_type = "text"
                i_tag = Tag.parse(["i", input, input_type])
                tags.append(i_tag)

            alt_tag = Tag.parse(["alt", self.dvm_config.SUPPORTED_DVMS[index].TASK])
            tags.append(alt_tag)
            relaylist = ["relays"]
            for relay in self.dvm_config.RELAY_LIST:
                relaylist.append(relay)
            relays_tag = Tag.parse(relaylist)
            tags.append(relays_tag)
            output_tag = Tag.parse(["output", "text/plain"])
            tags.append(output_tag)
            remaining_text = command.replace(input, "")
            print(remaining_text)

            params = remaining_text.rstrip().split(" -")

            for i in params:
                print(i)
                if i != " ":
                    try:
                        split = i.split(" ")
                        if len(split) > 1:
                            param = str(split[0])
                            print(str(param))
                            value = str(split[1])
                            print(str(value))
                            if param == "cashu":
                                tag = Tag.parse([param, value])
                            else:
                                if param == "user":
                                    if value.startswith("@") or value.startswith("nostr:") or value.startswith("npub"):
                                        value = PublicKey.from_bech32(
                                            value.replace("@", "").replace("nostr:", "")).to_hex()
                                tag = Tag.parse(["param", param, value])
                            tags.append(tag)
                            print("Added params: " + str(tag.as_vec()))
                    except Exception as e:
                        print(e)
                        print("Couldn't add " + str(i))

            return tags

        async def print_dvm_info(client, index):
            pubkey = self.dvm_config.SUPPORTED_DVMS[index].dvm_config.PUBLIC_KEY
            kind = self.dvm_config.SUPPORTED_DVMS[index].KIND
            nip89content_str = await nip89_fetch_events_pubkey(client, pubkey, kind)
            print(nip89content_str)
            if nip89content_str is not None:
                nip89content = json.loads(nip89content_str)
                info = ""
                cashu_accepted = False
                encryption_supported = False

                if nip89content.get("name"):
                    info += "Name: " + nip89content.get("name") + "\n"
                if nip89content.get("image"):
                    info += nip89content.get("image") + "\n"
                if nip89content.get("about"):
                    info += "About:\n" + nip89content.get("about") + "\n\n"
                if nip89content.get("cashuAccepted"):
                    cashu_accepted = str(nip89content.get("cashuAccepted"))
                if nip89content.get("encryptionSupported"):
                    encryption_supported = str(nip89content.get("encryptionSupported"))

                info += "Encryption supported: " + str(encryption_supported) + "\n"
                info += "Cashu accepted: " + str(cashu_accepted) + "\n\n"
                if nip89content.get("nip90Params"):
                    params = nip89content["nip90Params"]
                    info += "\nParameters:\n"
                    for param in params:
                        info += "-" + param + '\n'
                        info += "Required: " + str(params[param]['required']) + '\n'
                        info += "Possible Values: " + json.dumps(params[param]['values']) + '\n\n'
                return info

            return None

        asyncio.create_task(self.client.handle_notifications(NotificationHandler()))

        try:
            while True:
                for invoice in self.invoice_list:
                    if invoice.bolt11 != "" and invoice.payment_hash != "" and not invoice.payment_hash is None and not invoice.is_paid:
                        ispaid = check_bolt11_ln_bits_is_paid(invoice.payment_hash, self.dvm_config)
                        if ispaid and invoice.is_paid is False:
                            print("is paid")
                            invoice.is_paid = True

                            await update_user_balance(self.dvm_config.DB, invoice.sender, invoice.amount,
                                                      client=self.client,
                                                      config=self.dvm_config)

                            print("[" + self.dvm_config.NIP89.NAME + "] updating balance from invoice list")

                        elif ispaid is None:  # invoice expired
                            self.invoice_list.remove(invoice)

                    elif Timestamp.now().as_secs() > invoice.expires:
                        self.invoice_list.remove(invoice)

                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            print('Stay weird!')
            os.kill(os.getpid(), signal.SIGTERM)
