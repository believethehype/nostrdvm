import json
import time
from datetime import timedelta
from threading import Thread

from nostr_sdk import (Keys, Client, Timestamp, Filter, nip04_decrypt, HandleNotification, EventBuilder, PublicKey,
                       Options, Tag, Event, nip04_encrypt)

from utils.admin_utils import admin_make_database_updates
from utils.backend_utils import get_amount_per_task
from utils.database_utils import get_or_add_user, update_user_balance, create_sql_table, update_sql_table, User
from utils.definitions import EventDefinitions
from utils.nostr_utils import send_event
from utils.zap_utils import parse_zap_event_tags, pay_bolt11_ln_bits, zap


class Bot:
    job_list: list
    # This is a simple list just to keep track which events we created and manage, so we don't pay for other requests
    def __init__(self, dvm_config, admin_config=None):
        self.NAME = "Bot"
        dvm_config.DB = "db/" + self.NAME + ".db"
        self.dvm_config = dvm_config
        self.admin_config = admin_config
        self.keys = Keys.from_sk_str(dvm_config.PRIVATE_KEY)
        wait_for_send = True
        skip_disconnected_relays = True
        opts = (Options().wait_for_send(wait_for_send).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT))
                .skip_disconnected_relays(skip_disconnected_relays))
        self.client = Client.with_opts(self.keys, opts)

        pk = self.keys.public_key()

        self.job_list = []

        print("Nostr BOT public key: " + str(pk.to_bech32()) + " Hex: " + str(pk.to_hex()) + " Name: " + self.NAME +
              " Supported DVM tasks: " +
              ', '.join(p.NAME + ":" + p.TASK for p in self.dvm_config.SUPPORTED_DVMS) + "\n")

        for relay in self.dvm_config.RELAY_LIST:
            self.client.add_relay(relay)
        self.client.connect()

        zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_ZAP]).since(Timestamp.now())
        dm_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM]).since(Timestamp.now())
        kinds = [EventDefinitions.KIND_NIP90_GENERIC, EventDefinitions.KIND_FEEDBACK]
        for dvm in self.dvm_config.SUPPORTED_DVMS:
            if dvm.KIND not in kinds:
                kinds.append(dvm.KIND + 1000)
        dvm_filter = (Filter().kinds(kinds).since(Timestamp.now()))

        self.client.subscribe([zap_filter, dm_filter, dvm_filter])

        create_sql_table(self.dvm_config.DB)
        admin_make_database_updates(adminconfig=self.admin_config, dvmconfig=self.dvm_config, client=self.client)

        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            def handle(self, relay_url, nostr_event):
                if (EventDefinitions.KIND_NIP90_EXTRACT_TEXT + 1000 <= nostr_event.kind()
                        <= EventDefinitions.KIND_NIP90_GENERIC + 1000):
                    handle_nip90_response_event(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_FEEDBACK:
                    handle_nip90_feedback(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_DM:
                    handle_dm(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_ZAP:
                    handle_zap(nostr_event)

            def handle_msg(self, relay_url, msg):
                return

        def handle_dm(nostr_event):
            sender = nostr_event.pubkey().to_hex()

            try:
                decrypted_text = nip04_decrypt(self.keys.secret_key(), nostr_event.pubkey(), nostr_event.content())
                print(decrypted_text)
                user = get_or_add_user(db=self.dvm_config.DB, npub=sender, client=self.client, config=self.dvm_config)

                if decrypted_text[0].isdigit():
                    index = int(decrypted_text.split(' ')[0]) - 1
                    task = self.dvm_config.SUPPORTED_DVMS[index].TASK
                    print("[" + self.NAME + "] Request from " + str(user.name) + " (" + str(user.nip05) + ", Balance: "
                          + str(user.balance) + " Sats) Task: " + str(task))

                    duration = 1
                    required_amount = get_amount_per_task(self.dvm_config.SUPPORTED_DVMS[index].TASK,
                                                          self.dvm_config, duration)

                    if user.isblacklisted:
                        # For some reason an admin might blacklist npubs, e.g. for abusing the service
                        evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                    "Your are currently blocked from all "
                                                                    "services.", None).to_event(self.keys)
                        send_event(evt, client=self.client, dvm_config=dvm_config)

                    elif user.balance >= required_amount or required_amount == 0:
                        command = decrypted_text.replace(decrypted_text.split(' ')[0] + " ", "")
                        input = command.split("-")[0].rstrip()

                        i_tag = Tag.parse(["i", input, "text"])
                        bid = str(self.dvm_config.SUPPORTED_DVMS[index].COST * 1000)
                        bid_tag = Tag.parse(['bid', bid, bid])
                        relays_tag = Tag.parse(["relays", json.dumps(self.dvm_config.RELAY_LIST)])
                        alt_tag = Tag.parse(["alt", self.dvm_config.SUPPORTED_DVMS[index].TASK])

                        tags = [i_tag.as_vec(), bid_tag.as_vec(), relays_tag.as_vec(), alt_tag.as_vec()]

                        remaining_text = command.replace(input, "")
                        params = remaining_text.rstrip().split("-")

                        for i in params:
                            if i != " ":
                                try:
                                    split = i.split(" ")
                                    param = str(split[0])
                                    print(str(param))
                                    value = str(split[1])
                                    print(str(value))
                                    tag = Tag.parse(["param", param, value])
                                    tags.append(tag.as_vec())
                                    print("Added params: " + tag.as_vec())
                                except Exception as e:
                                    print(e)
                                    print("Couldn't add " + str(i))

                        encrypted_params_string = json.dumps(tags)

                        print(encrypted_params_string)

                        encrypted_params = nip04_encrypt(self.keys.secret_key(),
                                                         PublicKey.from_hex(
                                                             self.dvm_config.SUPPORTED_DVMS[index].PUBLIC_KEY),
                                                         encrypted_params_string)

                        encrypted_tag = Tag.parse(['encrypted'])
                        p_tag = Tag.parse(['p', self.dvm_config.SUPPORTED_DVMS[index].PUBLIC_KEY])
                        encrypted_nip90request = (EventBuilder(self.dvm_config.SUPPORTED_DVMS[index].KIND,
                                                               encrypted_params, [p_tag, encrypted_tag]).
                                                  to_event(self.keys))

                        entry = {"npub": user.npub, "event_id": encrypted_nip90request.id().to_hex(),
                                 "dvm_key": self.dvm_config.SUPPORTED_DVMS[index].PUBLIC_KEY, "is_paid": False}
                        self.job_list.append(entry)

                        send_event(encrypted_nip90request, client=self.client, dvm_config=dvm_config)


                    else:
                        print("Bot payment-required")
                        time.sleep(2.0)
                        evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                    "Balance required, please zap me with at least " +
                                                                    str(int(required_amount - user.balance))
                                                                    + " Sats, then try again.",
                                                                    nostr_event.id()).to_event(self.keys)
                        send_event(evt, client=self.client, dvm_config=dvm_config)


                else:
                    print("[" + self.NAME + "] Message from " + user.name + ": " + decrypted_text)
                    message = "DVMs that I support:\n\n"
                    index = 1
                    for p in self.dvm_config.SUPPORTED_DVMS:
                        message += str(index) + " " + p.NAME + " " + p.TASK + " " + str(p.COST) + " Sats" + "\n"
                        index += 1

                    time.sleep(1.0)
                    evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                message + "\nSelect an Index and provide an input ("
                                                                          "e.g. 1 A purple ostrich)",
                                                                nostr_event.id()).to_event(self.keys)

                    send_event(evt, client=self.client, dvm_config=dvm_config)

            except Exception as e:

                print("Error in bot " + str(e))

        def handle_nip90_feedback(nostr_event):

            try:
                is_encrypted = False
                status = ""
                etag = ""
                ptag = ""

                for tag in nostr_event.tags():
                    if tag.as_vec()[0] == "status":
                        status = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "e":
                        etag = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "p":
                        ptag = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "encrypted":
                        is_encrypted = True

                content = nostr_event.content()
                if is_encrypted:
                    if ptag == self.dvm_config.PUBLIC_KEY:
                        tags_str = nip04_decrypt(Keys.from_sk_str(dvm_config.PRIVATE_KEY).secret_key(),
                                                 nostr_event.pubkey(), nostr_event.content())
                        params = json.loads(tags_str)
                        params.append(Tag.parse(["p", ptag]).as_vec())
                        params.append(Tag.parse(["encrypted"]).as_vec())
                        print(params)
                        event_as_json = json.loads(nostr_event.as_json())
                        event_as_json['tags'] = params
                        event_as_json['content'] = ""
                        nostr_event = Event.from_json(json.dumps(event_as_json))

                        for tag in nostr_event.tags():
                            if tag.as_vec()[0] == "status":
                                status = tag.as_vec()[1]
                            elif tag.as_vec()[0] == "e":
                                etag = tag.as_vec()[1]
                            elif tag.as_vec()[0] == "content":
                                content = tag.as_vec()[1]

                    else:
                        return

                if status == "success" or status == "error" or status == "processing" or status == "partial":
                    entry = next((x for x in self.job_list if x['event_id'] == etag), None)
                    if entry is not None:
                        user = get_or_add_user(db=self.dvm_config.DB, npub=entry['npub'],
                                               client=self.client, config=self.dvm_config)

                        reply_event = EventBuilder.new_encrypted_direct_msg(self.keys,
                                                                            PublicKey.from_hex(user.npub),
                                                                            content,
                                                                            None).to_event(self.keys)
                        print(status + ": " + content)
                        print(
                            "[" + self.NAME + "] Received reaction from " + nostr_event.pubkey().to_hex() + " message to orignal sender " + user.name)
                        send_event(reply_event, client=self.client, dvm_config=dvm_config)

                elif status == "payment-required" or status == "partial":
                    for tag in nostr_event.tags():
                        if tag.as_vec()[0] == "amount":
                            amount_msats = int(tag.as_vec()[1])
                            amount = int(amount_msats / 1000)
                            entry = next((x for x in self.job_list if x['event_id'] == etag), None)
                            if entry is not None and entry['is_paid'] is False and entry['dvm_key'] == nostr_event.pubkey().to_hex():
                                # if we get a bolt11, we pay and move on
                                user = get_or_add_user(db=self.dvm_config.DB, npub=entry["npub"],
                                                       client=self.client, config=self.dvm_config)
                                balance = max(user.balance - amount, 0)
                                update_sql_table(db=self.dvm_config.DB, npub=user.npub, balance=balance,
                                                 iswhitelisted=user.iswhitelisted, isblacklisted=user.isblacklisted,
                                                 nip05=user.nip05, lud16=user.lud16, name=user.name,
                                                 lastactive=Timestamp.now().as_secs())
                                time.sleep(2.0)
                                evt = EventBuilder.new_encrypted_direct_msg(self.keys,
                                                                            PublicKey.from_hex(entry["npub"]),
                                                                            "Paid " + str(
                                                                                amount) + " Sats from balance to DVM. New balance is " +
                                                                            str(balance)
                                                                            + " Sats.\n",
                                                                            None).to_event(self.keys)

                                print("[" + self.NAME + "] Replying " + user.name + " with \"scheduled\" confirmation")
                                send_event(evt, client=self.client, dvm_config=dvm_config)

                                if len(tag.as_vec()) > 2:
                                    bolt11 = tag.as_vec()[2]
                                # else we create a zap
                                else:
                                    user = get_or_add_user(db=self.dvm_config.DB, npub=nostr_event.pubkey().to_hex(),
                                                           client=self.client, config=self.dvm_config)
                                    print("Paying: " + user.name)
                                    bolt11 = zap(user.lud16, amount, "Zap", nostr_event, self.keys, self.dvm_config,
                                                 "private")
                                    if bolt11 == None:
                                        print("Receiver has no Lightning address")
                                        return
                                try:
                                    payment_hash = pay_bolt11_ln_bits(bolt11, self.dvm_config)
                                    self.job_list[self.job_list.index(entry)]['is_paid'] = True
                                    print("[" + self.NAME + "] payment_hash: " + payment_hash +
                                          " Forwarding payment of " + str(amount) + " Sats to DVM")
                                except Exception as e:
                                    print(e)


            except Exception as e:
                print(e)

        def handle_nip90_response_event(nostr_event: Event):
            try:
                ptag = ""
                is_encrypted = False
                for tag in nostr_event.tags():
                    if tag.as_vec()[0] == "e":
                        etag = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "p":
                        ptag = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "encrypted":
                        is_encrypted = True

                entry = next((x for x in self.job_list if x['event_id'] == etag), None)
                if entry is not None:
                    print(entry)
                    user = get_or_add_user(db=self.dvm_config.DB, npub=entry['npub'],
                                           client=self.client, config=self.dvm_config)

                    self.job_list.remove(entry)
                    content = nostr_event.content()
                    if is_encrypted:
                        if ptag == self.dvm_config.PUBLIC_KEY:
                            content = nip04_decrypt(self.keys.secret_key(), nostr_event.pubkey(), content)
                        else:
                            return

                    print("[" + self.NAME + "] Received results, message to orignal sender " + user.name)
                    time.sleep(1.0)
                    reply_event = EventBuilder.new_encrypted_direct_msg(self.keys,
                                                                        PublicKey.from_hex(user.npub),
                                                                        content,
                                                                        None).to_event(self.keys)
                    send_event(reply_event, client=self.client, dvm_config=dvm_config)

            except Exception as e:
                print(e)

        def handle_zap(zap_event):
            print("[" + self.NAME + "] Zap received")
            try:
                invoice_amount, zapped_event, sender, message, anon = parse_zap_event_tags(zap_event,
                                                                                           self.keys, self.NAME,
                                                                                           self.client, self.dvm_config)

                user = get_or_add_user(self.dvm_config.DB, sender, client=self.client, config=self.dvm_config)
                print("ZAPED EVENT: " + zapped_event.as_json())
                if zapped_event is not None:
                    if not anon:
                        print("[" + self.NAME + "] Note Zap received for Bot balance: " + str(
                            invoice_amount) + " Sats from " + str(
                            user.name))
                        update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client,
                                            config=self.dvm_config)

                        # a regular note
                elif not anon:
                    print("[" + self.NAME + "] Profile Zap received for Bot balance: " + str(
                        invoice_amount) + " Sats from " + str(
                        user.name))
                    update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client,
                                        config=self.dvm_config)

            except Exception as e:
                print("[" + self.NAME + "] Error during content decryption:" + str(e))

        self.client.handle_notifications(NotificationHandler())
        while True:
            time.sleep(1.0)

    def run(self):
        bot = Bot
        nostr_dvm_thread = Thread(target=bot, args=[self.dvm_config])
        nostr_dvm_thread.start()
