from nostr_sdk import PublicKey, Keys, Client, Tag, Event, EventBuilder, Filter, HandleNotification, Timestamp, \
    init_logger, LogLevel

import time

from utils.definitions import EventDefinitions, RequiredJobToWatch, JobToWatch
from utils.dvmconfig import DVMConfig
from utils.admin_utils import admin_make_database_updates, AdminConfig
from utils.backend_utils import get_amount_per_task, check_task_is_supported, get_task
from utils.database_utils import update_sql_table, get_from_sql_table, \
    create_sql_table, get_or_add_user, update_user_balance
from utils.nostr_utils import get_event_by_id, get_referenced_event_by_id, send_event
from utils.output_utils import post_process_result, build_status_reaction
from utils.zap_utils import check_bolt11_ln_bits_is_paid, parse_amount_from_bolt11_invoice, \
    check_for_zapplepay, decrypt_private_zap_message, create_bolt11_ln_bits

use_logger = False
if use_logger:
    init_logger(LogLevel.DEBUG)




class DVM:
    dvm_config: DVMConfig
    admin_config: AdminConfig
    keys: Keys
    client: Client
    job_list: list
    jobs_on_hold_list: list

    def __init__(self, dvmconfig, adminconfig = None):
        self.dvm_config = dvmconfig
        self.admin_config = adminconfig
        self.keys = Keys.from_sk_str(dvmconfig.PRIVATE_KEY)
        self.client = Client(self.keys)
        self.job_list = []
        self.jobs_on_hold_list = []

        pk = self.keys.public_key()

        print("Nostr DVM public key: " + str(pk.to_bech32()) + "Hex: " + str(pk.to_hex()) + " Supported DVM tasks: " +
              ', '.join(p.NAME + ":" + p.TASK for p in self.dvm_config.SUPPORTED_TASKS) + "\n")

        for relay in self.dvm_config.RELAY_LIST:
            self.client.add_relay(relay)
        self.client.connect()

        dm_zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_ZAP]).since(Timestamp.now())

        kinds = [EventDefinitions.KIND_NIP90_GENERIC]
        for dvm in self.dvm_config.SUPPORTED_TASKS:
            if dvm.KIND not in kinds:
                kinds.append(dvm.KIND)
        dvm_filter = (Filter().kinds(kinds).since(Timestamp.now()))
        self.client.subscribe([dm_zap_filter, dvm_filter])

        create_sql_table(self.dvm_config.DB)
        admin_make_database_updates(adminconfig=self.admin_config, dvmconfig=self.dvm_config, client=self.client)

        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            def handle(self, relay_url, nostr_event):
                if EventDefinitions.KIND_NIP90_EXTRACT_TEXT <= nostr_event.kind() <= EventDefinitions.KIND_NIP90_GENERIC:
                    print("[" + self.dvm_config.NIP89.name + "] " + f"Received new NIP90 Job Request from {relay_url}: {nostr_event.as_json()}")
                    handle_nip90_job_event(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_ZAP:
                    handle_zap(nostr_event)

            def handle_msg(self, relay_url, msg):
                return

        def handle_nip90_job_event(nip90_event):
            user = get_or_add_user(self.dvm_config.DB, nip90_event.pubkey().to_hex(), client=self.client)
            task_supported, task, duration = check_task_is_supported(nip90_event, client=self.client,
                                                                     get_duration=(not user.iswhitelisted),
                                                                     config=self.dvm_config)

            if user.isblacklisted:
                send_job_status_reaction(nip90_event, "error", client=self.client, dvm_config=self.dvm_config)
                print("[" + self.dvm_config.NIP89.name + "] Request by blacklisted user, skipped")

            elif task_supported:
                print("Received new Task: " + task + " from " + user.name)
                amount = get_amount_per_task(task, self.dvm_config, duration)
                if amount is None:
                    return

                task_is_free = False
                for dvm in self.dvm_config.SUPPORTED_TASKS:
                    if dvm.TASK == task and dvm.COST == 0:
                        task_is_free = True

                if user.iswhitelisted or task_is_free:
                    print("[" + self.dvm_config.NIP89.name + "] Free or Whitelisted for task " + task + ". Starting processing..")
                    send_job_status_reaction(nip90_event, "processing", True, 0, client=self.client,
                                             dvm_config=self.dvm_config)
                    do_work(nip90_event, is_from_bot=False)
                # otherwise send payment request
                else:
                    bid = 0
                    for tag in nip90_event.tags():
                        if tag.as_vec()[0] == 'bid':
                            bid = int(tag.as_vec()[1])

                    print("[" + self.dvm_config.NIP89.name + "] Payment required: New Nostr " + task + " Job event: " + nip90_event.as_json())
                    if bid > 0:
                        bid_offer = int(bid / 1000)
                        if bid_offer >= amount:
                            send_job_status_reaction(nip90_event, "payment-required", False,
                                                     amount,  # bid_offer
                                                     client=self.client, dvm_config=self.dvm_config)

                    else:  # If there is no bid, just request server rate from user
                        print("[" + self.dvm_config.NIP89.name + "]  Requesting payment for Event: " + nip90_event.id().to_hex())
                        send_job_status_reaction(nip90_event, "payment-required",
                                                 False, amount, client=self.client, dvm_config=self.dvm_config)
            else:
                print("Task not supported on this DVM, skipping..")

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
                print(str(user))

                if zapped_event is not None:
                    if zapped_event.kind() == EventDefinitions.KIND_FEEDBACK:  # if a reaction by us got zapped
                        print("Zap received for NIP90 task: " + str(invoice_amount) + " Sats from " + str(
                            user.name))
                        amount = 0
                        job_event = None
                        for tag in zapped_event.tags():
                            if tag.as_vec()[0] == 'amount':
                                amount = int(float(tag.as_vec()[1]) / 1000)
                            elif tag.as_vec()[0] == 'e':
                                job_event = get_event_by_id(tag.as_vec()[1], client=self.client, config=self.dvm_config)

                        task_supported, task, duration = check_task_is_supported(job_event, client=self.client,
                                                                                 get_duration=False,
                                                                                 config=self.dvm_config)
                        if job_event is not None and task_supported:
                            if amount <= invoice_amount:
                                print("[" + self.dvm_config.NIP89.name + "]  Payment-request fulfilled...")
                                send_job_status_reaction(job_event, "processing", client=self.client,
                                                         dvm_config=self.dvm_config)
                                indices = [i for i, x in enumerate(self.job_list) if
                                           x.event_id == job_event.id().to_hex()]
                                index = -1
                                if len(indices) > 0:
                                    index = indices[0]
                                if index > -1:
                                    if self.job_list[index].is_processed:  # If payment-required appears a processing
                                        self.job_list[index].is_paid = True
                                        check_and_return_event(self.job_list[index].result,
                                                               str(job_event.as_json()))
                                    elif not (self.job_list[index]).is_processed:
                                        # If payment-required appears before processing
                                        self.job_list.pop(index)
                                        print("Starting work...")
                                        do_work(job_event, is_from_bot=False)
                                else:
                                    print("Job not in List, but starting work...")
                                    do_work(job_event, is_from_bot=False)

                            else:
                                send_job_status_reaction(job_event, "payment-rejected",
                                                         False, invoice_amount, client=self.client,
                                                         dvm_config=self.dvm_config)
                                print("[" + self.dvm_config.NIP89.name + "] Invoice was not paid sufficiently")

                    elif zapped_event.kind() in EventDefinitions.ANY_RESULT:
                        print("Someone zapped the result of an exisiting Task. Nice")
                    elif not anon:
                        print("Note Zap received for Bot balance: " + str(invoice_amount) + " Sats from " + str(
                            user.name))
                        update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client, config=self.dvm_config)

                        # a regular note
                elif not anon:
                    print("Profile Zap received for Bot balance: " + str(invoice_amount) + " Sats from " + str(
                        user.name))
                    update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client, config=self.dvm_config)

            except Exception as e:
                print(f"Error during content decryption: {e}")

        def check_event_has_not_unfinished_job_input(nevent, append, client, dvmconfig):
            task_supported, task, duration = check_task_is_supported(nevent, client, False, config=dvmconfig)
            if not task_supported:
                return False

            for tag in nevent.tags():
                if tag.as_vec()[0] == 'i':
                    if len(tag.as_vec()) < 3:
                        print("Job Event missing/malformed i tag, skipping..")
                        return False
                    else:
                        input = tag.as_vec()[1]
                        input_type = tag.as_vec()[2]
                        if input_type == "job":
                            evt = get_referenced_event_by_id(event_id=input, client=client, kinds=EventDefinitions.ANY_RESULT,
                                                             dvm_config=dvmconfig)
                            if evt is None:
                                if append:
                                    job = RequiredJobToWatch(event=nevent, timestamp=Timestamp.now().as_secs())
                                    self.jobs_on_hold_list.append(job)
                                    send_job_status_reaction(nevent, "chain-scheduled", True, 0, client=client,
                                                             dvm_config=dvmconfig)

                                return False
            else:
                return True

        def check_and_return_event(data, original_event_str: str):
            original_event = Event.from_json(original_event_str)

            for x in self.job_list:
                if x.event_id == original_event.id().to_hex():
                    is_paid = x.is_paid
                    amount = x.amount
                    x.result = data
                    x.is_processed = True
                    if self.dvm_config.SHOWRESULTBEFOREPAYMENT and not is_paid:
                        send_nostr_reply_event(data, original_event_str,)
                        send_job_status_reaction(original_event, "success", amount,
                                                 dvm_config=self.dvm_config)  # or payment-required, or both?
                    elif not self.dvm_config.SHOWRESULTBEFOREPAYMENT and not is_paid:
                        send_job_status_reaction(original_event, "success", amount,
                                                 dvm_config=self.dvm_config)  # or payment-required, or both?

                    if self.dvm_config.SHOWRESULTBEFOREPAYMENT and is_paid:
                        self.job_list.remove(x)
                    elif not self.dvm_config.SHOWRESULTBEFOREPAYMENT and is_paid:
                        self.job_list.remove(x)
                        send_nostr_reply_event(data, original_event_str)
                    break

            try:
                post_processed_content = post_process_result(data, original_event)
                send_nostr_reply_event(post_processed_content, original_event_str)
            except Exception as e:
                respond_to_error(str(e), original_event_str, False)

        def send_nostr_reply_event(content, original_event_as_str):
            original_event = Event.from_json(original_event_as_str)
            request_tag = Tag.parse(["request", original_event_as_str.replace("\\", "")])
            e_tag = Tag.parse(["e", original_event.id().to_hex()])
            p_tag = Tag.parse(["p", original_event.pubkey().to_hex()])
            alt_tag = Tag.parse(["alt", "This is the result of a NIP90 DVM AI task with kind " + str(
                original_event.kind()) + ". The task was: " + original_event.content()])
            status_tag = Tag.parse(["status", "success"])
            reply_tags = [request_tag, e_tag, p_tag, alt_tag, status_tag]
            for tag in original_event.tags():
                if tag.as_vec()[0] == "i":
                    i_content = tag.as_vec()[1]
                    i_kind = tag.as_vec()[2]
                    i_tag = Tag.parse(["i", i_content, i_kind])
                    reply_tags.append(i_tag)

            key = Keys.from_sk_str(self.dvm_config.PRIVATE_KEY)

            response_kind = original_event.kind() + 1000
            reply_event = EventBuilder(response_kind, str(content), reply_tags).to_event(key)
            send_event(reply_event, client=self.client, dvm_config=self.dvm_config)
            print("[" + self.dvm_config.NIP89.name + "]" + str(response_kind) + " Job Response event sent: " + reply_event.as_json())
            return reply_event.as_json()

        def respond_to_error(content: str, original_event_as_str: str, is_from_bot=False):
            print("ERROR: " + str(content))
            keys = Keys.from_sk_str(self.dvm_config.PRIVATE_KEY)
            original_event = Event.from_json(original_event_as_str)
            sender = ""
            task = ""
            if not is_from_bot:
                send_job_status_reaction(original_event, "error", content=content, dvm_config=self.dvm_config)
                # TODO Send Zap back
            else:
                for tag in original_event.tags():
                    if tag.as_vec()[0] == "p":
                        sender = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "i":
                        task = tag.as_vec()[1]

                user = get_from_sql_table(self.dvm_config.DB, sender)
                if not user.iswhitelisted:
                    amount = int(user.balance) + get_amount_per_task(task, self.dvm_config)
                    update_sql_table(self.dvm_config.DB, sender, amount, user.iswhitelisted, user.isblacklisted, user.nip05, user.lud16,
                                     user.name,
                                     Timestamp.now().as_secs())
                    message = "There was the following error : " + content + ". Credits have been reimbursed"
                else:
                    # User didn't pay, so no reimbursement
                    message = "There was the following error : " + content

                evt = EventBuilder.new_encrypted_direct_msg(keys, PublicKey.from_hex(sender), message,
                                                            None).to_event(keys)
                send_event(evt, client=self.client, dvm_config=self.dvm_config)

        def send_job_status_reaction(original_event, status, is_paid=True, amount=0, client=None,
                                     content=None,
                                     dvm_config=None):
            dvm_config = dvm_config
            task = get_task(original_event, client=client, dvmconfig=dvm_config)
            alt_description, reaction = build_status_reaction(status, task, amount, content)

            e_tag = Tag.parse(["e", original_event.id().to_hex()])
            p_tag = Tag.parse(["p", original_event.pubkey().to_hex()])
            alt_tag = Tag.parse(["alt", alt_description])
            status_tag = Tag.parse(["status", status])
            tags = [e_tag, p_tag, alt_tag, status_tag]

            if status == "success" or status == "error":  #
                for x in self.job_list:
                    if x.event_id == original_event.id():
                        is_paid = x.is_paid
                        amount = x.amount
                        break

            bolt11 = ""
            payment_hash = ""
            expires = original_event.created_at().as_secs() + (60 * 60 * 24)
            if status == "payment-required" or (status == "processing" and not is_paid):
                if dvm_config.LNBITS_INVOICE_KEY != "":
                    try:
                        bolt11, payment_hash = create_bolt11_ln_bits(amount, dvm_config)
                    except Exception as e:
                        print(e)

            if not any(x.event_id == original_event.id().to_hex() for x in self.job_list):
                self.job_list.append(
                    JobToWatch(event_id=original_event.id().to_hex(),
                               timestamp=original_event.created_at().as_secs(),
                               amount=amount,
                               is_paid=is_paid,
                               status=status, result="", is_processed=False, bolt11=bolt11,
                               payment_hash=payment_hash,
                               expires=expires, from_bot=False))
                #print(str(self.job_list))
            if (status == "payment-required" or status == "payment-rejected" or (
                    status == "processing" and not is_paid)
                    or (status == "success" and not is_paid)):

                if dvm_config.LNBITS_INVOICE_KEY != "":
                    amount_tag = Tag.parse(["amount", str(amount * 1000), bolt11])
                else:
                    amount_tag = Tag.parse(["amount", str(amount * 1000)])  # to millisats
                tags.append(amount_tag)

            keys = Keys.from_sk_str(dvm_config.PRIVATE_KEY)
            event = EventBuilder(EventDefinitions.KIND_FEEDBACK, reaction, tags).to_event(keys)

            send_event(event, client=self.client, dvm_config=self.dvm_config)
            print("[" + self.dvm_config.NIP89.name + "]" + ": Sent Kind " + str(
                    EventDefinitions.KIND_FEEDBACK) + " Reaction: " + status + " " + event.as_json())
            return event.as_json()

        def do_work(job_event, is_from_bot=False):
            if ((
                    EventDefinitions.KIND_NIP90_EXTRACT_TEXT <= job_event.kind() <= EventDefinitions.KIND_NIP90_GENERIC)
                    or job_event.kind() == EventDefinitions.KIND_DM):

                task = get_task(job_event, client=self.client, dvmconfig=self.dvm_config)
                result = ""
                for dvm in self.dvm_config.SUPPORTED_TASKS:
                    try:
                        if task == dvm.TASK:
                            request_form = dvm.create_request_form_from_nostr_event(job_event, self.client,
                                                                                    self.dvm_config)
                            result = dvm.process(request_form)
                            check_and_return_event(result, str(job_event.as_json()))

                    except Exception as e:
                        print(e)
                        respond_to_error(str(e), job_event.as_json(), is_from_bot)
                        return

        self.client.handle_notifications(NotificationHandler())
        while True:
            for job in self.job_list:
                if job.bolt11 != "" and job.payment_hash != "" and not job.is_paid:
                    if str(check_bolt11_ln_bits_is_paid(job.payment_hash, self.dvm_config)) == "True":
                        job.is_paid = True
                        event = get_event_by_id(job.event_id, client=self.client, config=self.dvm_config)
                        if event is not None:
                            send_job_status_reaction(event, "processing", True, 0,
                                                     client=self.client,
                                                     dvm_config=self.dvm_config)
                            print("do work from joblist")

                            do_work(event, is_from_bot=False)
                    elif check_bolt11_ln_bits_is_paid(job.payment_hash, self.dvm_config) is None:  # invoice expired
                        try:
                            self.job_list.remove(job)
                        except:
                            print("Error removing Job from List after payment")

                if Timestamp.now().as_secs() > job.expires:
                    try:
                        self.job_list.remove(job)
                    except:
                        print("Error removing Job from List after expiry")

            for job in self.jobs_on_hold_list:
                if check_event_has_not_unfinished_job_input(job.event, False, client=self.client,
                                                            dvmconfig=self.dvm_config):
                    handle_nip90_job_event(nip90_event=job.event)
                    try:
                        self.jobs_on_hold_list.remove(job)
                    except:
                        print("Error removing Job on Hold from List after expiry")

                if Timestamp.now().as_secs() > job.timestamp + 60 * 20:  # remove jobs to look for after 20 minutes..
                    self.jobs_on_hold_list.remove(job)

            time.sleep(1.0)
