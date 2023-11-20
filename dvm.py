from nostr_sdk import PublicKey, Keys, Client, Tag, Event, EventBuilder, Filter, HandleNotification, Timestamp, \
    init_logger, LogLevel
import time
import emoji

from utils.definitions import EventDefinitions, DVMConfig, RequiredJobToWatch, JobToWatch
from utils.admin_utils import admin_make_database_updates
from utils.backend_utils import get_amount_per_task, check_task_is_supported, get_task
from utils.database_utils import update_sql_table, get_from_sql_table, \
    create_sql_table, get_or_add_user, update_user_balance
from utils.nostr_utils import get_event_by_id, get_referenced_event_by_id, send_event
from utils.output_utils import post_process_result
from utils.zap_utils import check_bolt11_ln_bits_is_paid, parse_bolt11_invoice, \
    check_for_zapplepay, decrypt_private_zap_message, create_bolt11_ln_bits

use_logger = False
if use_logger:
    init_logger(LogLevel.DEBUG)

job_list = []
jobs_on_hold_list = []


class DVM:
    dvm_config: DVMConfig
    keys: Keys
    client: Client

    def __init__(self, config):
        self.dvm_config = config
        self.keys = Keys.from_sk_str(config.PRIVATE_KEY)
        self.client = Client(self.keys)

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

        create_sql_table()
        admin_make_database_updates(config=self.dvm_config, client=self.client)

        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            def handle(self, relay_url, nostr_event):
                print(f"[Nostr] Received new NIP90 Job Request from {relay_url}: {nostr_event.as_json()}")
                if EventDefinitions.KIND_NIP90_EXTRACT_TEXT <= nostr_event.kind() <= EventDefinitions.KIND_NIP90_GENERIC:
                    self.handle_nip90_job_event(nostr_event)
                elif nostr_event.kind() == EventDefinitions.KIND_ZAP:
                    self.handle_zap(nostr_event)

            def handle_msg(self, relay_url, msg):
                return

            def handle_nip90_job_event(self, nip90_event):
                user = get_or_add_user(nip90_event.pubkey().to_hex())
                task_supported, task, duration = check_task_is_supported(nip90_event, client=self.client,
                                                                         get_duration=(not user.iswhitelisted),
                                                                         config=self.dvm_config)
                print(task)

                if user.isblacklisted:
                    send_job_status_reaction(nip90_event, "error", client=self.client, config=self.dvm_config)
                    print("[Nostr] Request by blacklisted user, skipped")

                elif task_supported:
                    print("Received new Task: " + task)
                    amount = get_amount_per_task(task, self.dvm_config, duration)
                    if amount is None:
                        return

                    task_is_free = False
                    for dvm in self.dvm_config.SUPPORTED_TASKS:
                        if dvm.TASK == task and dvm.COST == 0:
                            task_is_free = True

                    if user.iswhitelisted or task_is_free:
                        print("[Nostr] Free or Whitelisted for task " + task + ". Starting processing..")
                        send_job_status_reaction(nip90_event, "processing", True, 0, client=self.client,
                                                 config=self.dvm_config)
                        do_work(nip90_event, is_from_bot=False)
                    # otherwise send payment request
                    else:
                        bid = 0
                        for tag in nip90_event.tags():
                            if tag.as_vec()[0] == 'bid':
                                bid = int(tag.as_vec()[1])

                        print("[Nostr][Payment required] New Nostr " + task + " Job event: " + nip90_event.as_json())
                        if bid > 0:
                            bid_offer = int(bid / 1000)
                            if bid_offer >= amount:
                                send_job_status_reaction(nip90_event, "payment-required", False,
                                                         amount,  # bid_offer
                                                         client=self.client, config=self.dvm_config)

                        else:  # If there is no bid, just request server rate from user
                            print("[Nostr] Requesting payment for Event: " + nip90_event.id().to_hex())
                            send_job_status_reaction(nip90_event, "payment-required",
                                                     False, amount, client=self.client, config=self.dvm_config)
                else:
                    print("Task not supported on this DVM, skipping..")

            def handle_zap(self, event):
                zapped_event = None
                invoice_amount = 0
                anon = False
                sender = event.pubkey()

                try:
                    for tag in event.tags():
                        if tag.as_vec()[0] == 'bolt11':
                            invoice_amount = parse_bolt11_invoice(tag.as_vec()[1])
                        elif tag.as_vec()[0] == 'e':
                            zapped_event = get_event_by_id(tag.as_vec()[1], config=self.dvm_config)
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
                    user = get_or_add_user(sender)
                    print(str(user))

                    if zapped_event is not None:
                        if zapped_event.kind() == EventDefinitions.KIND_FEEDBACK:  # if a reaction by us got zapped
                            if not self.dvm_config.IS_BOT:
                                print("Zap received for NIP90 task: " + str(invoice_amount) + " Sats from " + str(
                                    user.name))
                                amount = 0
                                job_event = None
                                for tag in zapped_event.tags():
                                    if tag.as_vec()[0] == 'amount':
                                        amount = int(float(tag.as_vec()[1]) / 1000)
                                    elif tag.as_vec()[0] == 'e':
                                        job_event = get_event_by_id(tag.as_vec()[1], config=self.dvm_config)

                                task_supported, task, duration = check_task_is_supported(job_event, client=self.client,
                                                                                         get_duration=False,
                                                                                         config=self.dvm_config)
                                if job_event is not None and task_supported:
                                    if amount <= invoice_amount:
                                        print("[Nostr] Payment-request fulfilled...")
                                        send_job_status_reaction(job_event, "processing", client=self.client,
                                                                      config=self.dvm_config)
                                        indices = [i for i, x in enumerate(job_list) if
                                                   x.event_id == job_event.id().to_hex()]
                                        index = -1
                                        if len(indices) > 0:
                                            index = indices[0]
                                        if index > -1:
                                            if job_list[index].is_processed:  # If payment-required appears a processing
                                                job_list[index].is_paid = True
                                                check_and_return_event(job_list[index].result,
                                                                            str(job_event.as_json()),
                                                                            dvm_key=self.dvm_config.PRIVATE_KEY)
                                            elif not (job_list[index]).is_processed:
                                                # If payment-required appears before processing
                                                job_list.pop(index)
                                                print("Starting work...")
                                                do_work(job_event, is_from_bot=False)
                                        else:
                                            print("Job not in List, but starting work...")
                                            do_work(job_event, is_from_bot=False)

                                    else:
                                        send_job_status_reaction(job_event, "payment-rejected",
                                                                      False, invoice_amount, client=self.client,
                                                                      config=self.dvm_config)
                                        print("[Nostr] Invoice was not paid sufficiently")

                        elif zapped_event.kind() in EventDefinitions.ANY_RESULT:
                            print("Someone zapped the result of an exisiting Task. Nice")
                        elif not anon and not self.dvm_config.PASSIVE_MODE:
                            print("Note Zap received for Bot balance: " + str(invoice_amount) + " Sats from " + str(
                                user.name))
                            update_user_balance(sender, invoice_amount, config=self.dvm_config)

                            # a regular note
                    elif not anon and not self.dvm_config.PASSIVE_MODE:
                        print("Profile Zap received for Bot balance: " + str(invoice_amount) + " Sats from " + str(
                            user.name))
                        update_user_balance(sender, invoice_amount, config=self.dvm_config)

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
                            evt = get_referenced_event_by_id(input, EventDefinitions.ANY_RESULT, client,
                                                             config=dvmconfig)
                            if evt is None:
                                if append:
                                    job = RequiredJobToWatch(event=nevent, timestamp=Timestamp.now().as_secs())
                                    jobs_on_hold_list.append(job)
                                    send_job_status_reaction(nevent, "chain-scheduled", True, 0, client=client,
                                                                  config=dvmconfig)

                                return False
            else:
                return True



        def check_and_return_event(data, original_event_str: str, dvm_key=""):
            original_event = Event.from_json(original_event_str)
            keys = Keys.from_sk_str(dvm_key)

            for x in job_list:
                if x.event_id == original_event.id().to_hex():
                    is_paid = x.is_paid
                    amount = x.amount
                    x.result = data
                    x.is_processed = True
                    if self.dvm_config.SHOWRESULTBEFOREPAYMENT and not is_paid:
                        send_nostr_reply_event(data, original_event_str, key=keys)
                        send_job_status_reaction(original_event, "success", amount,
                                                      config=self.dvm_config)  # or payment-required, or both?
                    elif not self.dvm_config.SHOWRESULTBEFOREPAYMENT and not is_paid:
                        send_job_status_reaction(original_event, "success", amount,
                                                      config=self.dvm_config)  # or payment-required, or both?

                    if self.dvm_config.SHOWRESULTBEFOREPAYMENT and is_paid:
                        job_list.remove(x)
                    elif not self.dvm_config.SHOWRESULTBEFOREPAYMENT and is_paid:
                        job_list.remove(x)
                        send_nostr_reply_event(data, original_event_str, key=keys)
                    break

            try:
                post_processed_content = post_process_result(data, original_event)
                send_nostr_reply_event(post_processed_content, original_event_str, key=keys)
            except Exception as e:
                respond_to_error(e, original_event_str, False, self.dvm_config.PRIVATE_KEY)

        def send_nostr_reply_event(content, original_event_as_str, key=None):
            originalevent = Event.from_json(original_event_as_str)
            requesttag = Tag.parse(["request", original_event_as_str.replace("\\", "")])
            etag = Tag.parse(["e", originalevent.id().to_hex()])
            ptag = Tag.parse(["p", originalevent.pubkey().to_hex()])
            alttag = Tag.parse(["alt", "This is the result of a NIP90 DVM AI task with kind " + str(
                originalevent.kind()) + ". The task was: " + originalevent.content()])
            statustag = Tag.parse(["status", "success"])
            replytags = [requesttag, etag, ptag, alttag, statustag]
            for tag in originalevent.tags():
                if tag.as_vec()[0] == "i":
                    icontent = tag.as_vec()[1]
                    ikind = tag.as_vec()[2]
                    itag = Tag.parse(["i", icontent, ikind])
                    replytags.append(itag)

            if key is None:
                key = Keys.from_sk_str(self.dvm_config.PRIVATE_KEY)

            response_kind = originalevent.kind() + 1000
            event = EventBuilder(response_kind, str(content), replytags).to_event(key)
            send_event(event, key=key)
            print("[Nostr] " + str(response_kind) + " Job Response event sent: " + event.as_json())
            return event.as_json()

        def respond_to_error(content, originaleventstr, is_from_bot=False, dvm_key=None):
            print("ERROR")
            if dvm_key is None:
                keys = Keys.from_sk_str(self.dvm_config.PRIVATE_KEY)
            else:
                keys = Keys.from_sk_str(dvm_key)

            original_event = Event.from_json(originaleventstr)
            sender = ""
            task = ""
            if not is_from_bot:
                send_job_status_reaction(original_event, "error", content=str(content), key=dvm_key)
                # TODO Send Zap back
            else:
                for tag in original_event.tags():
                    if tag.as_vec()[0] == "p":
                        sender = tag.as_vec()[1]
                    elif tag.as_vec()[0] == "i":
                        task = tag.as_vec()[1]

                user = get_from_sql_table(sender)
                if not user.iswhitelisted:
                    amount = int(user.balance) + get_amount_per_task(task, self.dvm_config)
                    update_sql_table(sender, amount, user.iswhitelisted, user.isblacklisted, user.nip05, user.lud16,
                                     user.name,
                                     Timestamp.now().as_secs())
                    message = "There was the following error : " + content + ". Credits have been reimbursed"
                else:
                    # User didn't pay, so no reimbursement
                    message = "There was the following error : " + content

                evt = EventBuilder.new_encrypted_direct_msg(keys, PublicKey.from_hex(sender), message,
                                                            None).to_event(keys)
                send_event(evt, key=keys)

        def send_job_status_reaction(original_event, status, is_paid=True, amount=0, client=None,
                                         content=None,
                                         config=None,
                                         key=None):
                dvmconfig = config
                alt_description = "This is a reaction to a NIP90 DVM AI task. "
                task = get_task(original_event, client=client, dvmconfig=dvmconfig)
                if status == "processing":
                    alt_description = "NIP90 DVM AI task " + task + " started processing. "
                    reaction = alt_description + emoji.emojize(":thumbs_up:")
                elif status == "success":
                    alt_description = "NIP90 DVM AI task " + task + " finished successfully. "
                    reaction = alt_description + emoji.emojize(":call_me_hand:")
                elif status == "chain-scheduled":
                    alt_description = "NIP90 DVM AI task " + task + " Chain Task scheduled"
                    reaction = alt_description + emoji.emojize(":thumbs_up:")
                elif status == "error":
                    alt_description = "NIP90 DVM AI task " + task + " had an error. "
                    if content is None:
                        reaction = alt_description + emoji.emojize(":thumbs_down:")
                    else:
                        reaction = alt_description + emoji.emojize(":thumbs_down:") + content

                elif status == "payment-required":

                    alt_description = "NIP90 DVM AI task " + task + " requires payment of min " + str(
                        amount) + " Sats. "
                    reaction = alt_description + emoji.emojize(":orange_heart:")

                elif status == "payment-rejected":
                    alt_description = "NIP90 DVM AI task " + task + " payment is below required amount of " + str(
                        amount) + " Sats. "
                    reaction = alt_description + emoji.emojize(":thumbs_down:")
                elif status == "user-blocked-from-service":
                    alt_description = "NIP90 DVM AI task " + task + " can't be performed. User has been blocked from Service. "
                    reaction = alt_description + emoji.emojize(":thumbs_down:")
                else:
                    reaction = emoji.emojize(":thumbs_down:")

                e_tag = Tag.parse(["e", original_event.id().to_hex()])
                p_tag = Tag.parse(["p", original_event.pubkey().to_hex()])
                alt_tag = Tag.parse(["alt", alt_description])
                status_tag = Tag.parse(["status", status])
                tags = [e_tag, p_tag, alt_tag, status_tag]

                if status == "success" or status == "error":  #
                    for x in job_list:
                        if x.event_id == original_event.id():
                            is_paid = x.is_paid
                            amount = x.amount
                            break

                bolt11 = ""
                payment_hash = ""
                expires = original_event.created_at().as_secs() + (60 * 60 * 24)
                if status == "payment-required" or (status == "processing" and not is_paid):
                    if dvmconfig.LNBITS_INVOICE_KEY != "":
                        try:
                            bolt11, payment_hash = create_bolt11_ln_bits(amount, dvmconfig)
                        except Exception as e:
                            print(e)

                if not any(x.event_id == original_event.id().to_hex() for x in job_list):
                    job_list.append(
                        JobToWatch(event_id=original_event.id().to_hex(),
                                   timestamp=original_event.created_at().as_secs(),
                                   amount=amount,
                                   is_paid=is_paid,
                                   status=status, result="", is_processed=False, bolt11=bolt11,
                                   payment_hash=payment_hash,
                                   expires=expires, from_bot=False))
                    print(str(job_list))
                if status == "payment-required" or status == "payment-rejected" or (
                        status == "processing" and not is_paid) or (
                        status == "success" and not is_paid):

                    if dvmconfig.LNBITS_INVOICE_KEY != "":
                        amount_tag = Tag.parse(["amount", str(amount * 1000), bolt11])
                    else:
                        amount_tag = Tag.parse(["amount", str(amount * 1000)])  # to millisats
                    tags.append(amount_tag)
                if key is not None:
                    keys = Keys.from_sk_str(key)
                else:
                    keys = Keys.from_sk_str(dvmconfig.PRIVATE_KEY)
                event = EventBuilder(EventDefinitions.KIND_FEEDBACK, reaction, tags).to_event(keys)

                send_event(event, key=keys)
                print(
                    "[Nostr] Sent Kind " + str(
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
                            check_and_return_event(result, str(job_event.as_json()),
                                                        dvm_key=self.dvm_config.PRIVATE_KEY)

                    except Exception as e:
                        print(e)
                        respond_to_error(e, job_event.as_json(), is_from_bot, self.dvm_config.PRIVATE_KEY)
                        return

        self.client.handle_notifications(NotificationHandler())
        while True:
            for job in job_list:
                if job.bolt11 != "" and job.payment_hash != "" and not job.is_paid:
                    if str(check_bolt11_ln_bits_is_paid(job.payment_hash, self.dvm_config)) == "True":
                        job.is_paid = True
                        event = get_event_by_id(job.event_id, config=self.dvm_config)
                        if event is not None:
                            send_job_status_reaction(event, "processing", True, 0,
                                                                         client=self.client,
                                                                         config=self.dvm_config)
                            print("do work from joblist")

                            do_work(event, is_from_bot=False)
                    elif check_bolt11_ln_bits_is_paid(job.payment_hash, self.dvm_config) is None:  # invoice expired
                        try:
                            job_list.remove(job)
                        except:
                            continue

                if Timestamp.now().as_secs() > job.expires:
                    try:
                        job_list.remove(job)
                    except:
                        continue

            for job in jobs_on_hold_list:
                if check_event_has_not_unfinished_job_input(job.event, False, client=self.client,
                                                                               dvmconfig=self.dvm_config):
            #        handle_nip90_job_event(event=job.event)
                    try:
                        jobs_on_hold_list.remove(job)
                    except:
                        continue


                if Timestamp.now().as_secs() > job.timestamp + 60 * 20:  # remove jobs to look for after 20 minutes..
                    jobs_on_hold_list.remove(job)

            time.sleep(1.0)
