import json
import time
from datetime import timedelta

from nostr_sdk import Keys, Client, Timestamp, Filter, nip04_decrypt, HandleNotification, EventBuilder, PublicKey, \
    Event, Options

from utils.admin_utils import admin_make_database_updates
from utils.backend_utils import get_amount_per_task
from utils.database_utils import get_or_add_user, update_user_balance, create_sql_table, update_sql_table, User
from utils.definitions import EventDefinitions
from utils.nostr_utils import send_event, get_event_by_id
from utils.zap_utils import parse_amount_from_bolt11_invoice, check_for_zapplepay, decrypt_private_zap_message


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

        print("Nostr BOT public key: " + str(pk.to_bech32()) + " Hex: " + str(pk.to_hex()) + " Name: " + self.NAME + " Supported DVM tasks: " +
              ', '.join(p.NAME + ":" + p.TASK for p in self.dvm_config.SUPPORTED_DVMS) + "\n")

        for relay in self.dvm_config.RELAY_LIST:
            self.client.add_relay(relay)
        self.client.connect()

        zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_ZAP]).since(Timestamp.now())
        dm_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM]).since(
            Timestamp.now())

        self.client.subscribe([zap_filter, dm_filter])

        create_sql_table(self.dvm_config.DB)
        admin_make_database_updates(adminconfig=self.admin_config, dvmconfig=self.dvm_config, client=self.client)

        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            def handle(self, relay_url, nostr_event):
                if EventDefinitions.KIND_DM:
                    handle_dm(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_ZAP:
                    handle_zap(nostr_event)

            def handle_msg(self, relay_url, msg):
                return

        def handle_dm(nostr_event):
            sender = nostr_event.pubkey().to_hex()

            try:
                decrypted_text = nip04_decrypt(self.keys.secret_key(), nostr_event.pubkey(), nostr_event.content())
                user = get_or_add_user(db=self.dvm_config.DB, npub=sender, client=self.client)

                # user = User
                # user.npub = sender
                # user.balance = 250
                # user.iswhitelisted = False
                # user.isblacklisted = False
                # user.name = "Test"
                # user.nip05 = "Test@test"
                # user.lud16 = "Test@test"

                # We do a selection of tasks now, maybe change this later, Idk.
                if decrypted_text[0].isdigit():
                    index = int(decrypted_text.split(' ')[0]) - 1
                    task = self.dvm_config.SUPPORTED_DVMS[index].TASK
                    print("["+ self.NAME + "] Request from " + str(user.name) + " (" + str(user.nip05) + ", Balance: "+ str(user.balance)+ " Sats) Task: " + str(task))

                    required_amount = self.dvm_config.SUPPORTED_DVMS[index].COST

                    if user.isblacklisted:
                        # For some reason an admin might blacklist npubs, e.g. for abusing the service
                        evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                    "Your are currently blocked from all services.",
                                                                    None).to_event(self.keys)
                        send_event(evt, client=self.client, dvm_config=dvm_config)

                    elif user.iswhitelisted or user.balance >= required_amount or required_amount == 0:
                        if not user.iswhitelisted:

                            balance = max(user.balance - required_amount, 0)
                            update_sql_table(db=self.dvm_config.DB, npub=user.npub, balance=balance,
                                             iswhitelisted=user.iswhitelisted, isblacklisted=user.isblacklisted,
                                             nip05=user.nip05, lud16=user.lud16, name=user.name,
                                             lastactive=Timestamp.now().as_secs())

                            evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                        "Your Job is now scheduled. New balance is " +
                                                                        str(balance)
                                                                        + " Sats.\nI will DM you once I'm done "
                                                                          "processing.",
                                                                        nostr_event.id()).to_event(self.keys)
                        else:
                            evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                        "Your Job is now scheduled. As you are "
                                                                        "whitelisted, your balance remains at"
                                                                        + str(user.balance) + " Sats.\n"
                                                                                              "I will DM you once I'm "
                                                                                              "done processing.",
                                                                        nostr_event.id()).to_event(self.keys)

                        print("[" + self.NAME + "] Replying " + user.name + " with \"scheduled\" confirmation")
                        time.sleep(2.0)
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
                                                                    "Balance required, please zap me with at least " + str(
                                                                        int(required_amount - user.balance))
                                                                    + " Sats, then try again.",
                                                                    nostr_event.id()).to_event(self.keys)
                        time.sleep(2.0)
                        send_event(evt, client=self.client, dvm_config=dvm_config)


                # TODO if we receive the result from one of the dvms, need some better management, maybe check for keys
                elif decrypted_text.startswith('{"result":'):


                    dvm_result = json.loads(decrypted_text)
                    user_npub_hex = dvm_result["sender"]
                    user = get_or_add_user(db=self.dvm_config.DB, npub=user_npub_hex, client=self.client)
                    print("[" + self.NAME + "] Received results, message to orignal sender " + user.name)
                    reply_event = EventBuilder.new_encrypted_direct_msg(self.keys,
                                                                        PublicKey.from_hex(user.npub),
                                                                        dvm_result["result"],
                                                                        None).to_event(self.keys)
                    time.sleep(2.0)
                    send_event(reply_event, client=self.client, dvm_config=dvm_config)

                else:
                    print("Message from " + user.name + ": " + decrypted_text)
                    message = "DVMs that I support:\n\n"
                    index = 1
                    for p in self.dvm_config.SUPPORTED_DVMS:
                        message += str(index) + " " + p.NAME + " " + p.TASK + " " + str(p.COST) + " Sats" + "\n"
                        index += 1

                    evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                message + "\nSelect an Index and provide an input ("
                                                                          "e.g. 1 A purple ostrich)",
                                                                None).to_event(self.keys)
                                                                #nostr_event.id()).to_event(self.keys)
                    time.sleep(3)
                    send_event(evt, client=self.client, dvm_config=dvm_config)
            except Exception as e:
                print(e)

        def handle_zap(zap_event):
            zapped_event = None
            invoice_amount = 0
            anon = False
            sender = zap_event.pubkey()
            print("Zap received")

            try:
                for tag in zap_event.tags():
                    if tag.as_vec()[0] == 'bolt11':
                        invoice_amount = parse_amount_from_bolt11_invoice(tag.as_vec()[1])
                    elif tag.as_vec()[0] == 'e':
                        zapped_event = get_event_by_id(tag.as_vec()[1], client=self.client, config=self.dvm_config)
                    elif tag.as_vec()[0] == 'description':
                        zap_request_event = Event.from_json(tag.as_vec()[1])
                        sender = check_for_zapplepay(zap_request_event.pubkey().to_hex(),
                                                     zap_request_event.content())
                        for z_tag in zap_request_event.tags():
                            if z_tag.as_vec()[0] == 'anon':
                                if len(z_tag.as_vec()) > 1:
                                    print("Private Zap received.")
                                    decrypted_content = decrypt_private_zap_message(z_tag.as_vec()[1],
                                                                                    self.keys.secret_key(),
                                                                                    zap_request_event.pubkey())
                                    decrypted_private_event = Event.from_json(decrypted_content)
                                    if decrypted_private_event.kind() == 9733:
                                        sender = decrypted_private_event.pubkey().to_hex()
                                        message = decrypted_private_event.content()
                                        if message != "":
                                            print("Zap Message: " + message)
                                else:
                                    anon = True
                                    print("Anonymous Zap received. Unlucky, I don't know from whom, and never will")
                user = get_or_add_user(self.dvm_config.DB, sender, client=self.client)

                if zapped_event is not None:
                    if not anon:
                        print("Note Zap received for Bot balance: " + str(invoice_amount) + " Sats from " + str(
                            user.name))
                        update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client,
                                            config=self.dvm_config)

                        # a regular note
                elif not anon:
                    print("Profile Zap received for Bot balance: " + str(invoice_amount) + " Sats from " + str(
                        user.name))
                    update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client,
                                        config=self.dvm_config)

            except Exception as e:
                print(f"Error during content decryption: {e}")

        self.client.handle_notifications(NotificationHandler())
        while True:
            time.sleep(1.0)
