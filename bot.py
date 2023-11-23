import json
import time
from threading import Thread

from nostr_sdk import Keys, Client, Timestamp, Filter, nip04_decrypt, HandleNotification, EventBuilder, PublicKey, Event

from utils.admin_utils import admin_make_database_updates
from utils.database_utils import get_or_add_user, update_user_balance
from utils.definitions import EventDefinitions
from utils.nostr_utils import send_event, get_event_by_id
from utils.zap_utils import parse_amount_from_bolt11_invoice, check_for_zapplepay, decrypt_private_zap_message


class Bot:
    job_list: list

    def __init__(self, dvm_config, admin_config=None):
        self.dvm_config = dvm_config
        self.admin_config = admin_config
        self.keys = Keys.from_sk_str(dvm_config.PRIVATE_KEY)
        self.client = Client(self.keys)
        self.job_list = []

        pk = self.keys.public_key()
        self.dvm_config.DB = "db/bot.db"

        print("Nostr BOT public key: " + str(pk.to_bech32()) + " Hex: " + str(pk.to_hex()) + " Supported DVM tasks: " +
              ', '.join(p.NAME + ":" + p.TASK for p in self.dvm_config.SUPPORTED_TASKS) + "\n")

        for relay in self.dvm_config.RELAY_LIST:
            self.client.add_relay(relay)
        self.client.connect()

        dm_zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM, EventDefinitions.KIND_ZAP]).since(
            Timestamp.now())
        self.client.subscribe([dm_zap_filter])

        admin_make_database_updates(adminconfig=self.admin_config, dvmconfig=self.dvm_config, client=self.client)

        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            def handle(self, relay_url, nostr_event):
                if EventDefinitions.KIND_DM:
                    print(
                        "[Bot] " + f"Received new DM from {relay_url}: {nostr_event.as_json()}")
                    handle_dm(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_ZAP:
                    print("yay zap")
                    handle_zap(nostr_event)

            def handle_msg(self, relay_url, msg):
                return

        def handle_dm(nostr_event):
            sender = nostr_event.pubkey().to_hex()
            try:
                decrypted_text = nip04_decrypt(self.keys.secret_key(), nostr_event.pubkey(), nostr_event.content())
                # TODO more advanced logic, more parsing, just very basic test functions for now
                if decrypted_text[0].isdigit():
                    index = int(decrypted_text.split(' ')[0]) - 1
                    i_tag = decrypted_text.replace(decrypted_text.split(' ')[0] + " ", "")

                    keys = Keys.from_sk_str(self.dvm_config.SUPPORTED_TASKS[index].PK)
                    params = {
                        "sender": nostr_event.pubkey().to_hex(),
                        "input": i_tag,
                        "task": self.dvm_config.SUPPORTED_TASKS[index].TASK
                    }
                    message = json.dumps(params)
                    evt = EventBuilder.new_encrypted_direct_msg(self.keys, keys.public_key(),
                                                                message, None).to_event(self.keys)
                    send_event(evt, client=self.client, dvm_config=dvm_config)

                elif decrypted_text.startswith('{"result":'):

                    dvm_result = json.loads(decrypted_text)

                    job_event = EventBuilder.new_encrypted_direct_msg(self.keys,
                                                                      PublicKey.from_hex(dvm_result["sender"]),
                                                                      dvm_result["result"],
                                                                      None).to_event(self.keys)
                    send_event(job_event, client=self.client, dvm_config=dvm_config)
                    user = get_or_add_user(db=self.dvm_config.DB, npub=dvm_result["sender"], client=self.client)
                    print("BOT received and forwarded to " + user.name + ": " + str(decrypted_text))


                else:
                    message = "DVMs that I support:\n\n"
                    index = 1
                    for p in self.dvm_config.SUPPORTED_TASKS:
                        message += str(index) + " " + p.NAME + " " + p.TASK + "\n"
                        index += 1

                    evt = EventBuilder.new_encrypted_direct_msg(self.keys, nostr_event.pubkey(),
                                                                message + "\nSelect an Index and provide an input ("
                                                                          "e.g. 1 A purple ostrich)",
                                                                nostr_event.id()).to_event(self.keys)
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
                        for ztag in zap_request_event.tags():
                            if ztag.as_vec()[0] == 'anon':
                                if len(ztag.as_vec()) > 1:
                                    print("Private Zap received.")
                                    decrypted_content = decrypt_private_zap_message(ztag.as_vec()[1],
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
                print(str(user.name))

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
