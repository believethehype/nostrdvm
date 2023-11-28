import json
import typing
from datetime import timedelta

from nostr_sdk import PublicKey, Keys, Client, Tag, Event, EventBuilder, Filter, HandleNotification, Timestamp, \
    init_logger, LogLevel, nip04_decrypt, Options, nip04_encrypt

import time

from utils.definitions import EventDefinitions, RequiredJobToWatch, JobToWatch
from utils.dvmconfig import DVMConfig
from utils.admin_utils import admin_make_database_updates, AdminConfig
from utils.backend_utils import get_amount_per_task, check_task_is_supported, get_task
from utils.database_utils import create_sql_table, get_or_add_user, update_user_balance, update_sql_table
from utils.nostr_utils import get_event_by_id, get_referenced_event_by_id, send_event, check_and_decrypt_tags
from utils.output_utils import post_process_result, build_status_reaction
from utils.zap_utils import check_bolt11_ln_bits_is_paid, create_bolt11_ln_bits, parse_zap_event_tags, redeem_cashu

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

    def __init__(self, dvm_config, admin_config=None):
        self.dvm_config = dvm_config
        self.admin_config = admin_config
        self.keys = Keys.from_sk_str(dvm_config.PRIVATE_KEY)
        wait_for_send = True
        skip_disconnected_relays = True
        opts = (Options().wait_for_send(wait_for_send).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT))
                .skip_disconnected_relays(skip_disconnected_relays))

        self.client = Client.with_opts(self.keys, opts)

        self.job_list = []
        self.jobs_on_hold_list = []

        pk = self.keys.public_key()

        print("Nostr DVM public key: " + str(pk.to_bech32()) + " Hex: " + str(pk.to_hex()) + " Supported DVM tasks: " +
              ', '.join(p.NAME + ":" + p.TASK for p in self.dvm_config.SUPPORTED_DVMS) + "\n")

        for relay in self.dvm_config.RELAY_LIST:
            self.client.add_relay(relay)
        self.client.connect()

        zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_ZAP]).since(Timestamp.now())
        # bot_dm_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM]).authors(self.dvm_config.DM_ALLOWED).since(
        #    Timestamp.now())

        kinds = [EventDefinitions.KIND_NIP90_GENERIC]
        for dvm in self.dvm_config.SUPPORTED_DVMS:
            if dvm.KIND not in kinds:
                kinds.append(dvm.KIND)
        dvm_filter = (Filter().kinds(kinds).since(Timestamp.now()))
        self.client.subscribe([dvm_filter, zap_filter])

        create_sql_table(self.dvm_config.DB)
        admin_make_database_updates(adminconfig=self.admin_config, dvmconfig=self.dvm_config, client=self.client)

        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            def handle(self, relay_url, nostr_event):
                if EventDefinitions.KIND_NIP90_EXTRACT_TEXT <= nostr_event.kind() <= EventDefinitions.KIND_NIP90_GENERIC:
                    handle_nip90_job_event(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_ZAP:
                    handle_zap(nostr_event)
                # elif nostr_event.kind() == EventDefinitions.KIND_DM:
                #   handle_dm(nostr_event)

            def handle_msg(self, relay_url, msg):
                return

        def handle_nip90_job_event(nip90_event):

            nip90_event = check_and_decrypt_tags(nip90_event, self.dvm_config)
            if nip90_event is None:
                return

            user = get_or_add_user(self.dvm_config.DB, nip90_event.pubkey().to_hex(), client=self.client,
                                   config=self.dvm_config)
            cashu = ""
            p_tag_str = ""
            for tag in nip90_event.tags():
                if tag.as_vec()[0] == "cashu":
                    cashu = tag.as_vec()[1]
                elif tag.as_vec()[0] == "p":
                    p_tag_str = tag.as_vec()[1]

            task_supported, task, duration = check_task_is_supported(nip90_event, client=self.client,
                                                                     get_duration=(not user.iswhitelisted),
                                                                     config=self.dvm_config)

            if user.isblacklisted:
                send_job_status_reaction(nip90_event, "error", client=self.client, dvm_config=self.dvm_config)
                print("[" + self.dvm_config.NIP89.name + "] Request by blacklisted user, skipped")

            elif task_supported:
                print("[" + self.dvm_config.NIP89.name + "] Received new Request: " + task + " from " + user.name)
                amount = get_amount_per_task(task, self.dvm_config, duration)
                if amount is None:
                    return

                task_is_free = False
                for dvm in self.dvm_config.SUPPORTED_DVMS:
                    if dvm.TASK == task and dvm.COST == 0:
                        task_is_free = True

                cashu_redeemed = False
                cashu_message = ""
                if cashu != "":
                    cashu_redeemed, cashu_message = redeem_cashu(cashu, amount, self.dvm_config, self.client)
                    if cashu_message != "":
                        send_job_status_reaction(nip90_event, "error", False, amount, self.client, cashu_message,
                                                 self.dvm_config)
                        return
                # if user is whitelisted or task is free, just do the job
                if user.iswhitelisted or task_is_free or cashu_redeemed:
                    print(
                        "[" + self.dvm_config.NIP89.name + "] Free task or Whitelisted for task " + task +
                        ". Starting processing..")

                    send_job_status_reaction(nip90_event, "processing", True, 0,
                                             client=self.client, dvm_config=self.dvm_config)

                    do_work(nip90_event)
                # if task is directed to us via p tag and user has balance, do the job and update balance

                elif p_tag_str == Keys.from_sk_str(
                        self.dvm_config.PUBLIC_KEY) and user.balance >= amount:
                    balance = max(user.balance - amount, 0)
                    update_sql_table(db=self.dvm_config.DB, npub=user.npub, balance=balance,
                                     iswhitelisted=user.iswhitelisted, isblacklisted=user.isblacklisted,
                                     nip05=user.nip05, lud16=user.lud16, name=user.name,
                                     lastactive=Timestamp.now().as_secs())

                    print(
                        "[" + self.dvm_config.NIP89.name + "] Using user's balance for task: " + task +

                        ". Starting processing.. New balance is: " + str(balance))

                    send_job_status_reaction(nip90_event, "processing", True, 0,
                                             client=self.client, dvm_config=self.dvm_config)

                    do_work(nip90_event)

                # else send a payment required event to user
                else:
                    bid = 0
                    for tag in nip90_event.tags():
                        if tag.as_vec()[0] == 'bid':
                            bid = int(tag.as_vec()[1])

                    print(
                        "[" + self.dvm_config.NIP89.name + "] Payment required: New Nostr " + task + " Job event: "
                        + nip90_event.as_json())
                    if bid > 0:
                        bid_offer = int(bid / 1000)
                        if bid_offer >= amount:
                            send_job_status_reaction(nip90_event, "payment-required", False,
                                                     amount,  # bid_offer
                                                     client=self.client, dvm_config=self.dvm_config)

                    else:  # If there is no bid, just request server rate from user
                        print(
                            "[" + self.dvm_config.NIP89.name + "]  Requesting payment for Event: " +
                            nip90_event.id().to_hex())
                        send_job_status_reaction(nip90_event, "payment-required",
                                                 False, amount, client=self.client, dvm_config=self.dvm_config)

            #else:
                #print("[" + self.dvm_config.NIP89.name + "] Task " + task + " not supported on this DVM, skipping..")

        def handle_zap(zap_event):
            try:
                invoice_amount, zapped_event, sender, message, anon = parse_zap_event_tags(zap_event,
                                                                                           self.keys,
                                                                                           self.dvm_config.NIP89.name,
                                                                                           self.client, self.dvm_config)
                user = get_or_add_user(db=self.dvm_config.DB, npub=sender, client=self.client, config=self.dvm_config)


                if zapped_event is not None:
                    if zapped_event.kind() == EventDefinitions.KIND_FEEDBACK:

                        amount = 0
                        job_event = None
                        p_tag_str = ""
                        for tag in zapped_event.tags():
                            if tag.as_vec()[0] == 'amount':
                                amount = int(float(tag.as_vec()[1]) / 1000)
                            elif tag.as_vec()[0] == 'e':
                                job_event = get_event_by_id(tag.as_vec()[1], client=self.client, config=self.dvm_config)
                                if job_event is not None:
                                    job_event = check_and_decrypt_tags(job_event, self.dvm_config)
                                    if job_event is None:
                                        return
                                else:
                                    return

                            # if a reaction by us got zapped

                        task_supported, task, duration = check_task_is_supported(job_event,
                                                                                 client=self.client,
                                                                                 get_duration=False,
                                                                                 config=self.dvm_config)
                        if job_event is not None and task_supported:
                            print("Zap received for NIP90 task: " + str(invoice_amount) + " Sats from " + str(
                                user.name))
                            if amount <= invoice_amount:
                                print("[" + self.dvm_config.NIP89.name + "]  Payment-request fulfilled...")
                                send_job_status_reaction(job_event, "processing", client=self.client,
                                                         dvm_config=self.dvm_config)
                                indices = [i for i, x in enumerate(self.job_list) if
                                           x.event == job_event]
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
                                        do_work(job_event)
                                else:
                                    print("Job not in List, but starting work...")
                                    do_work(job_event)

                            else:
                                send_job_status_reaction(job_event, "payment-rejected",
                                                         False, invoice_amount, client=self.client,
                                                         dvm_config=self.dvm_config)
                                print("[" + self.dvm_config.NIP89.name + "] Invoice was not paid sufficiently")

                    elif zapped_event.kind() in EventDefinitions.ANY_RESULT:
                        print("[" + self.dvm_config.NIP89.name + "] "
                                                                 "Someone zapped the result of an exisiting Task. Nice")
                    elif not anon:
                        print("[" + self.dvm_config.NIP89.name + "] Note Zap received for DVM balance: " +
                              str(invoice_amount) + " Sats from " + str(user.name))
                        update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client,
                                            config=self.dvm_config)

                        # a regular note
                elif not anon:
                    print("[" + self.dvm_config.NIP89.name + "] Profile Zap received for DVM balance: " +
                          str(invoice_amount) + " Sats from " + str(user.name))
                    update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client,
                                        config=self.dvm_config)

            except Exception as e:
                print("[" + self.dvm_config.NIP89.name + "] Error during content decryption: " + str(e))

        def check_event_has_not_unfinished_job_input(nevent, append, client, dvmconfig):
            task_supported, task, duration = check_task_is_supported(nevent, client, False,
                                                                     config=dvmconfig)
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
                            evt = get_referenced_event_by_id(event_id=input, client=client,
                                                             kinds=EventDefinitions.ANY_RESULT,
                                                             dvm_config=dvmconfig)
                            if evt is None:
                                if append:
                                    job_ = RequiredJobToWatch(event=nevent, timestamp=Timestamp.now().as_secs())
                                    self.jobs_on_hold_list.append(job_)
                                    send_job_status_reaction(nevent, "chain-scheduled", True, 0,
                                                             client=client, dvm_config=dvmconfig)

                                return False
            else:
                return True

        def check_and_return_event(data, original_event_str: str):
            original_event = Event.from_json(original_event_str)

            for x in self.job_list:
                if x.event == original_event:
                    is_paid = x.is_paid
                    amount = x.amount
                    x.result = data
                    x.is_processed = True
                    if self.dvm_config.SHOW_RESULT_BEFORE_PAYMENT and not is_paid:
                        send_nostr_reply_event(data, original_event_str)
                        send_job_status_reaction(original_event, "success", amount,
                                                 dvm_config=self.dvm_config,
                                                 )  # or payment-required, or both?
                    elif not self.dvm_config.SHOW_RESULT_BEFORE_PAYMENT and not is_paid:
                        send_job_status_reaction(original_event, "success", amount,
                                                 dvm_config=self.dvm_config,
                                                 )  # or payment-required, or both?

                    if self.dvm_config.SHOW_RESULT_BEFORE_PAYMENT and is_paid:
                        self.job_list.remove(x)
                    elif not self.dvm_config.SHOW_RESULT_BEFORE_PAYMENT and is_paid:
                        self.job_list.remove(x)
                        send_nostr_reply_event(data, original_event_str)
                    break

            try:
                post_processed_content = post_process_result(data, original_event)
                send_nostr_reply_event(post_processed_content, original_event_str)
            except Exception as e:
                send_job_status_reaction(original_event, "error", content=str(e), dvm_config=self.dvm_config,
                                         )

        def send_nostr_reply_event(content, original_event_as_str):
            original_event = Event.from_json(original_event_as_str)
            request_tag = Tag.parse(["request", original_event_as_str.replace("\\", "")])
            e_tag = Tag.parse(["e", original_event.id().to_hex()])
            p_tag = Tag.parse(["p", original_event.pubkey().to_hex()])
            alt_tag = Tag.parse(["alt", "This is the result of a NIP90 DVM AI task with kind " + str(
                original_event.kind()) + ". The task was: " + original_event.content()])
            status_tag = Tag.parse(["status", "success"])
            reply_tags = [request_tag, e_tag, p_tag, alt_tag, status_tag]
            encrypted = False
            for tag in original_event.tags():
                if tag.as_vec()[0] == "encrypted":
                    encrypted = True
                    encrypted_tag = Tag.parse(["encrypted"])
                    reply_tags.append(encrypted_tag)

            for tag in original_event.tags():
                if tag.as_vec()[0] == "i":
                    i_tag = tag
                    if not encrypted:
                        reply_tags.append(i_tag)

            if encrypted:
                content = nip04_encrypt(self.keys.secret_key(), PublicKey.from_hex(original_event.pubkey().to_hex()),
                                        content)

            reply_event = EventBuilder(original_event.kind() + 1000, str(content), reply_tags).to_event(self.keys)

            send_event(reply_event, client=self.client, dvm_config=self.dvm_config)
            print("[" + self.dvm_config.NIP89.name + "] " + str(
                original_event.kind() + 1000) + " Job Response event sent: " + reply_event.as_json())

        def send_job_status_reaction(original_event, status, is_paid=True, amount=0, client=None,
                                     content=None,
                                     dvm_config=None):

            task = get_task(original_event, client=client, dvmconfig=dvm_config)
            alt_description, reaction = build_status_reaction(status, task, amount, content)

            e_tag = Tag.parse(["e", original_event.id().to_hex()])
            p_tag = Tag.parse(["p", original_event.pubkey().to_hex()])
            alt_tag = Tag.parse(["alt", alt_description])
            status_tag = Tag.parse(["status", status])
            reply_tags = [e_tag, alt_tag, status_tag]
            encryption_tags = []

            encrypted = False
            for tag in original_event.tags():
                if tag.as_vec()[0] == "encrypted":
                    encrypted = True
                    encrypted_tag = Tag.parse(["encrypted"])
                    encryption_tags.append(encrypted_tag)

            if encrypted:
                encryption_tags.append(p_tag)
            else:
                reply_tags.append(p_tag)

            if status == "success" or status == "error":  #
                for x in self.job_list:
                    if x.event == original_event:
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

            if not any(x.event == original_event for x in self.job_list):
                self.job_list.append(
                    JobToWatch(event=original_event,
                               timestamp=original_event.created_at().as_secs(),
                               amount=amount,
                               is_paid=is_paid,
                               status=status, result="", is_processed=False, bolt11=bolt11,
                               payment_hash=payment_hash,
                               expires=expires))
                # print(str(self.job_list))
            if (status == "payment-required" or status == "payment-rejected" or (
                    status == "processing" and not is_paid)
                    or (status == "success" and not is_paid)):

                if dvm_config.LNBITS_INVOICE_KEY != "":
                    amount_tag = Tag.parse(["amount", str(amount * 1000), bolt11])
                else:
                    amount_tag = Tag.parse(["amount", str(amount * 1000)])  # to millisats
                reply_tags.append(amount_tag)

            if encrypted:
                content_tag = Tag.parse(["content", reaction])
                reply_tags.append(content_tag)
                str_tags = []
                for element in reply_tags:
                    str_tags.append(element.as_vec())

                content = json.dumps(str_tags)
                content = nip04_encrypt(self.keys.secret_key(), PublicKey.from_hex(original_event.pubkey().to_hex()),
                                        content)
                reply_tags = encryption_tags

            else:
                content = reaction

            keys = Keys.from_sk_str(dvm_config.PRIVATE_KEY)
            reaction_event = EventBuilder(EventDefinitions.KIND_FEEDBACK, str(content), reply_tags).to_event(keys)
            send_event(reaction_event, client=self.client, dvm_config=self.dvm_config)
            print("[" + self.dvm_config.NIP89.name + "]" + ": Sent Kind " + str(
                EventDefinitions.KIND_FEEDBACK) + " Reaction: " + status + " " + reaction_event.as_json())
            return reaction_event.as_json()

        def do_work(job_event):
            if ((EventDefinitions.KIND_NIP90_EXTRACT_TEXT <= job_event.kind() <= EventDefinitions.KIND_NIP90_GENERIC)
                    or job_event.kind() == EventDefinitions.KIND_DM):

                task = get_task(job_event, client=self.client, dvmconfig=self.dvm_config)

                for dvm in self.dvm_config.SUPPORTED_DVMS:
                    try:
                        if task == dvm.TASK:
                            request_form = dvm.create_request_form_from_nostr_event(job_event, self.client,
                                                                                    self.dvm_config)
                            result = dvm.process(request_form)
                            check_and_return_event(result, str(job_event.as_json()))


                    except Exception as e:
                        print(e)
                        send_job_status_reaction(job_event, "error", content=str(e), dvm_config=self.dvm_config)
                        return

        self.client.handle_notifications(NotificationHandler())
        while True:
            for job in self.job_list:
                if job.bolt11 != "" and job.payment_hash != "" and not job.is_paid:
                    ispaid = check_bolt11_ln_bits_is_paid(job.payment_hash, self.dvm_config)
                    if ispaid and job.is_paid is False:
                        print("is paid")

                        job.is_paid = True
                        send_job_status_reaction(job.event, "processing", True, 0,
                                                 client=self.client,
                                                 dvm_config=self.dvm_config)
                        print("[" + self.dvm_config.NIP89.name + "] doing work from joblist")
                        do_work(job.event)
                    elif ispaid is None:  # invoice expired
                        self.job_list.remove(job)

                if Timestamp.now().as_secs() > job.expires:
                    self.job_list.remove(job)

            for job in self.jobs_on_hold_list:
                if check_event_has_not_unfinished_job_input(job.event, False, client=self.client,
                                                            dvmconfig=self.dvm_config):
                    handle_nip90_job_event(nip90_event=job.event)
                    try:
                        self.jobs_on_hold_list.remove(job)
                    except:
                        print("[" + self.dvm_config.NIP89.name + "] Error removing Job on Hold from List after expiry")

                if Timestamp.now().as_secs() > job.timestamp + 60 * 20:  # remove jobs to look for after 20 minutes..
                    self.jobs_on_hold_list.remove(job)

            time.sleep(1.0)
