import json
import time
from datetime import timedelta
from threading import Thread

from nostr_sdk import (Keys, Client, Timestamp, Filter, nip04_decrypt, HandleNotification, EventBuilder, PublicKey,
                       Options)

from utils.admin_utils import admin_make_database_updates
from utils.backend_utils import get_amount_per_task
from utils.database_utils import get_or_add_user, update_user_balance, create_sql_table, update_sql_table, User
from utils.definitions import EventDefinitions
from utils.nostr_utils import send_event
from utils.zap_utils import parse_zap_event_tags


class Bot:
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

        print("Nostr BOT public key: " + str(pk.to_bech32()) + " Hex: " + str(pk.to_hex()) + " Name: " + self.NAME +
              " Supported DVM tasks: " +
              ', '.join(p.NAME + ":" + p.TASK for p in self.dvm_config.SUPPORTED_DVMS) + "\n")

        for relay in self.dvm_config.RELAY_LIST:
            self.client.add_relay(relay)
        self.client.connect()

        zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_ZAP]).since(Timestamp.now())
        dm_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM]).since(Timestamp.now())

        self.client.subscribe([zap_filter, dm_filter])

        create_sql_table(self.dvm_config.DB)
        admin_make_database_updates(adminconfig=self.admin_config, dvmconfig=self.dvm_config, client=self.client)

        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            def handle(self, relay_url, nostr_event):
                if nostr_event.kind() == EventDefinitions.KIND_DM:
                    handle_dm(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_ZAP:
                    handle_zap(nostr_event)

            def handle_msg(self, relay_url, msg):
                return

        def handle_dm(nostr_event):
            sender = nostr_event.pubkey().to_hex()

            try:
                decrypted_text = nip04_decrypt(self.keys.secret_key(), nostr_event.pubkey(), nostr_event.content())
                user = get_or_add_user(db=self.dvm_config.DB, npub=sender, client=self.client, config=self.dvm_config)

                # We do a selection of tasks now, maybe change this later, Idk.
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
                                                                    "services.",None).to_event(self.keys)
                        send_event(evt, client=self.client, dvm_config=dvm_config)

                    elif user.iswhitelisted or user.balance >= required_amount or required_amount == 0:

                        if not user.iswhitelisted:

                            balance = max(user.balance - required_amount, 0)
                            update_sql_table(db=self.dvm_config.DB, npub=user.npub, balance=balance,
                                             iswhitelisted=user.iswhitelisted, isblacklisted=user.isblacklisted,
                                             nip05=user.nip05, lud16=user.lud16, name=user.name,
                                             lastactive=Timestamp.now().as_secs())
                            time.sleep(2.0)
                            evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                        "Your Job is now scheduled. New balance is " +
                                                                        str(balance)
                                                                        + " Sats.\nI will DM you once I'm done "
                                                                          "processing.",
                                                                        nostr_event.id()).to_event(self.keys)
                        else:
                            time.sleep(2.0)
                            evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                        "Your Job is now scheduled. As you are "
                                                                        "whitelisted, your balance remains at"
                                                                        + str(user.balance) + " Sats.\n"
                                                                                              "I will DM you once I'm "
                                                                                              "done processing.",
                                                                        nostr_event.id()).to_event(self.keys)

                        print("[" + self.NAME + "] Replying " + user.name + " with \"scheduled\" confirmation")
                        send_event(evt, client=self.client, dvm_config=dvm_config)

                        i_tag = decrypted_text.replace(decrypted_text.split(' ')[0] + " ", "")
                        # TODO more advanced logic, more parsing, params etc, just very basic test functions for now
                        dvm_keys = Keys.from_sk_str(self.dvm_config.SUPPORTED_DVMS[index].PK)
                        params = {
                            "sender": nostr_event.pubkey().to_hex(),
                            "input": i_tag,
                            "task": self.dvm_config.SUPPORTED_DVMS[index].TASK
                        }
                        message = json.dumps(params)
                        evt = EventBuilder.new_encrypted_direct_msg(self.keys, dvm_keys.public_key(),
                                                                    message, None).to_event(self.keys)
                        print("[" + self.NAME + "] Forwarding task " + self.dvm_config.SUPPORTED_DVMS[index].TASK +
                              " for user " + user.name + " to " + self.dvm_config.SUPPORTED_DVMS[index].NAME)
                        send_event(evt, client=self.client, dvm_config=dvm_config)
                    else:
                        print("payment-required")
                        time.sleep(2.0)
                        evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                    "Balance required, please zap me with at least " +
                                                                    str(int(required_amount - user.balance))
                                                                    + " Sats, then try again.",
                                                                    nostr_event.id()).to_event(self.keys)
                        send_event(evt, client=self.client, dvm_config=dvm_config)


                # TODO if we receive the result from one of the dvms, need some better management, maybe check for keys
                elif decrypted_text.startswith('{"result":'):

                    dvm_result = json.loads(decrypted_text)
                    user_npub_hex = dvm_result["sender"]
                    user = get_or_add_user(db=self.dvm_config.DB, npub=user_npub_hex,
                                           client=self.client, config=self.dvm_config)
                    print("[" + self.NAME + "] Received results, message to orignal sender " + user.name)
                    reply_event = EventBuilder.new_encrypted_direct_msg(self.keys,
                                                                        PublicKey.from_hex(user.npub),
                                                                        dvm_result["result"],
                                                                        None).to_event(self.keys)

                    send_event(reply_event, client=self.client, dvm_config=dvm_config)

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

        def handle_zap(zap_event):
            print("[" + self.NAME + "] Zap received")
            try:
                invoice_amount, zapped_event, sender, anon = parse_zap_event_tags(zap_event,
                                                                                  self.keys, self.NAME,
                                                                                  self.client, self.dvm_config)

                user = get_or_add_user(self.dvm_config.DB, sender, client=self.client, config=self.dvm_config)

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
