import asyncio
import json
import os
from datetime import timedelta
from sys import platform

from nostr_sdk import PublicKey, Keys, Client, Tag, Event, EventBuilder, Filter, HandleNotification, Timestamp, \
    init_logger, LogLevel, Options, nip04_encrypt, NostrSigner, Kind, RelayLimits

from nostr_dvm.utils.definitions import EventDefinitions, RequiredJobToWatch, JobToWatch
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.admin_utils import admin_make_database_updates, AdminConfig
from nostr_dvm.utils.backend_utils import get_amount_per_task, check_task_is_supported, get_task
from nostr_dvm.utils.database_utils import create_sql_table, get_or_add_user, update_user_balance, update_sql_table, \
    update_user_subscription
from nostr_dvm.utils.mediasource_utils import input_data_file_duration
from nostr_dvm.utils.nip88_utils import nip88_has_active_subscription
from nostr_dvm.utils.nostr_utils import get_event_by_id, get_referenced_event_by_id, send_event, check_and_decrypt_tags, \
    send_event_outbox
from nostr_dvm.utils.nut_wallet_utils import NutZapWallet
from nostr_dvm.utils.output_utils import build_status_reaction
from nostr_dvm.utils.zap_utils import check_bolt11_ln_bits_is_paid, create_bolt11_ln_bits, parse_zap_event_tags, \
    parse_amount_from_bolt11_invoice, zaprequest, pay_bolt11_ln_bits, create_bolt11_lud16
from nostr_dvm.utils.cashu_utils import redeem_cashu
from nostr_dvm.utils.print import bcolors


class DVM:
    dvm_config: DVMConfig
    admin_config: AdminConfig
    keys: Keys
    client: Client
    job_list: list
    jobs_on_hold_list: list

    def __init__(self, dvm_config, admin_config=None):
        asyncio.run(self.run_dvm(dvm_config, admin_config))

    async def run_dvm(self, dvm_config, admin_config):

        self.dvm_config = dvm_config
        self.admin_config = admin_config
        self.keys = Keys.parse(dvm_config.PRIVATE_KEY)
        wait_for_send = False
        skip_disconnected_relays = True
        relaylimits = RelayLimits.disable()
        opts = (
            Options().wait_for_send(wait_for_send).send_timeout(timedelta(seconds=self.dvm_config.RELAY_TIMEOUT))
            .skip_disconnected_relays(skip_disconnected_relays).relay_limits(relaylimits))

        signer = NostrSigner.keys(self.keys)
        self.client = Client.with_opts(signer, opts)
        self.job_list = []
        self.jobs_on_hold_list = []
        pk = self.keys.public_key()
        print(bcolors.BLUE + "[" + self.dvm_config.NIP89.NAME + "] " + "Nostr DVM public key: " + str(
            pk.to_bech32()) + " Hex: " +
              str(pk.to_hex()) + " Supported DVM tasks: " +
              ', '.join(p.NAME + ":" + p.TASK for p in self.dvm_config.SUPPORTED_DVMS) + bcolors.ENDC)

        for relay in self.dvm_config.RELAY_LIST:
            await self.client.add_relay(relay)
        await self.client.connect()

        zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_ZAP, EventDefinitions.KIND_NIP61_NUT_ZAP]).since(Timestamp.now())
        kinds = [EventDefinitions.KIND_NIP90_GENERIC]
        for dvm in self.dvm_config.SUPPORTED_DVMS:
            if dvm.KIND not in kinds:
                kinds.append(dvm.KIND)
        dvm_filter = (Filter().kinds(kinds).since(Timestamp.now()))
        create_sql_table(self.dvm_config.DB)
        await admin_make_database_updates(adminconfig=self.admin_config, dvmconfig=self.dvm_config, client=self.client)
        await self.client.subscribe([dvm_filter, zap_filter], None)

        if self.dvm_config.ENABLE_NUTZAP:
            nutzap_wallet = NutZapWallet()
            nut_wallet = await nutzap_wallet.get_nut_wallet(self.client, self.keys)

            if nut_wallet is None:
                await nutzap_wallet.create_new_nut_wallet(self.dvm_config.NUZAP_MINTS, self.dvm_config.NUTZAP_RELAYS,
                                                          self.client, self.keys, "DVM", "DVM Nutsack")
                nut_wallet = await nutzap_wallet.get_nut_wallet(self.client, self.keys)

                await nutzap_wallet.announce_nutzap_info_event(nut_wallet, self.client, self.keys)

        class NotificationHandler(HandleNotification):
            client = self.client
            dvm_config = self.dvm_config
            keys = self.keys

            async def handle(self, relay_url, subscription_id, nostr_event: Event):
                if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                    print(nostr_event.as_json())
                if EventDefinitions.KIND_NIP90_EXTRACT_TEXT.as_u64() <= nostr_event.kind().as_u64() <= EventDefinitions.KIND_NIP90_GENERIC.as_u64():
                    await handle_nip90_job_event(nostr_event)
                elif nostr_event.kind().as_u64() == EventDefinitions.KIND_ZAP.as_u64():
                    await handle_zap(nostr_event)
                elif nostr_event.kind().as_u64() == EventDefinitions.KIND_NIP61_NUT_ZAP.as_u64():
                    await handle_nutzap(nostr_event)

            async def handle_msg(self, relay_url, msg):
                return

        async def handle_nip90_job_event(nip90_event):
            # decrypted encrypted events
            nip90_event = check_and_decrypt_tags(nip90_event, self.dvm_config)
            # if event is encrypted, but we can't decrypt it (e.g. because its directed to someone else), return
            if nip90_event is None:
                return

            task_is_free = False
            user_has_active_subscription = False
            cashu = ""
            p_tag_str = ""

            for tag in nip90_event.tags():
                if tag.as_vec()[0] == "cashu":
                    cashu = tag.as_vec()[1]
                elif tag.as_vec()[0] == "p":
                    p_tag_str = tag.as_vec()[1]

            if p_tag_str != "" and p_tag_str != self.dvm_config.PUBLIC_KEY:
                if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                    print("[" + self.dvm_config.NIP89.NAME + "] No public request, also not addressed to me.")
                return

            # check if task is supported by the current DVM
            task_supported, task = await check_task_is_supported(nip90_event, client=self.client,
                                                                 config=self.dvm_config)
            # if task is supported, continue, else do nothing.
            if task_supported:
                # fetch or add user contacting the DVM from/to local database
                user = await get_or_add_user(self.dvm_config.DB, nip90_event.author().to_hex(), client=self.client,
                                             config=self.dvm_config, skip_meta=False)
                # if user is blacklisted for some reason, send an error reaction and return
                if user.isblacklisted:
                    await send_job_status_reaction(nip90_event, "error", client=self.client, dvm_config=self.dvm_config)
                    print("[" + self.dvm_config.NIP89.NAME + "] Request by blacklisted user, skipped")
                    return
                if self.dvm_config.LOGLEVEL.value >= LogLevel.INFO.value:
                    print(
                        bcolors.MAGENTA + "[" + self.dvm_config.NIP89.NAME + "] Received new Request: " + task + " from " + user.name + bcolors.ENDC)
                duration = await input_data_file_duration(nip90_event, dvm_config=self.dvm_config, client=self.client)
                amount = get_amount_per_task(task, self.dvm_config, duration)
                if amount is None:
                    return

                # If this is a subscription DVM and the Task is directed to us, check for active subscription
                if dvm_config.NIP88 is not None and p_tag_str == self.dvm_config.PUBLIC_KEY:
                    # await send_job_status_reaction(nip90_event, "subscription-required", True, amount, self.client,
                    #                               "Checking Subscription Status, please wait..", self.dvm_config)
                    # if we stored in the database that the user has an active subscription, we don't need to check it
                    print("User Subscription: " + str(user.subscribed) + " Current time: " + str(
                        Timestamp.now().as_secs()))
                    # if we have an entry in the db that user is subscribed, continue
                    if int(user.subscribed) > int(Timestamp.now().as_secs()):
                        print("User subscribed until: " + str(Timestamp.from_secs(user.subscribed).to_human_datetime()))
                        user_has_active_subscription = True
                        await send_job_status_reaction(nip90_event, "subscription-active", True, amount,
                                                       self.client, "User subscripton active until " +
                                                       Timestamp.from_secs(
                                                           int(user.subscribed)).to_human_datetime().replace(
                                                           "Z", " ").replace("T", " ") + " GMT", self.dvm_config)
                        # otherwise we check for an active subscription by checking recipie events
                        # sleep a little to not get rate limited
                        await asyncio.sleep(0.5)

                    else:
                        print("[" + self.dvm_config.NIP89.NAME + "] Checking Subscription status")
                        # await send_job_status_reaction(nip90_event, "subscription-required", True, amount, self.client,
                        #                               "I Don't have information about subscription status, checking on the Nostr. This might take a few seconds",
                        #                               self.dvm_config)

                        subscription_status = await nip88_has_active_subscription(PublicKey.parse(user.npub),
                                                                                  self.dvm_config.NIP88.DTAG,
                                                                                  self.client,
                                                                                  self.dvm_config.PUBLIC_KEY)

                        if subscription_status["isActive"]:
                            await send_job_status_reaction(nip90_event, "subscription-required", True, amount,
                                                           self.client,
                                                           "User subscripton active until " + Timestamp.from_secs(int(
                                                               subscription_status[
                                                                   "validUntil"])).to_human_datetime().replace("Z",
                                                                                                               " ").replace(
                                                               "T", " ") + " GMT",
                                                           self.dvm_config)

                            print("Checked Recipe: User subscribed until: " + str(
                                Timestamp.from_secs(int(subscription_status["validUntil"])).to_human_datetime()))
                            user_has_active_subscription = True
                            update_user_subscription(user.npub,
                                                     int(subscription_status["validUntil"]),
                                                     self.client, self.dvm_config)

                            # sleep a little before sending next status update


                        else:
                            print("No active subscription found")
                            await send_job_status_reaction(nip90_event, "subscription-required", True, amount,
                                                           self.client,
                                                           "No active subscription found. Manage your subscription at: " + self.dvm_config.SUBSCRIPTION_MANAGEMENT,
                                                           self.dvm_config)

                for dvm in self.dvm_config.SUPPORTED_DVMS:
                    if (dvm.TASK == task or dvm.TASK == "generic") and dvm.FIX_COST == 0 and dvm.PER_UNIT_COST == 0 and dvm_config.NIP88 is None:
                        task_is_free = True

                cashu_redeemed = False
                if cashu != "":
                    print(cashu)
                    cashu_redeemed, cashu_message, redeem_amount, fees = await redeem_cashu(cashu, self.dvm_config,
                                                                                            self.client, int(amount))
                    print(cashu_message)
                    if cashu_message != "success":
                        await send_job_status_reaction(nip90_event, "error", False, amount, self.client, cashu_message,
                                                       self.dvm_config)
                        return
                # if user is whitelisted or task is free, just do the job
                if (user.iswhitelisted or task_is_free or cashu_redeemed) and (
                        p_tag_str == "" or p_tag_str ==
                        self.dvm_config.PUBLIC_KEY):
                    if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                        print(
                            "[" + self.dvm_config.NIP89.NAME + "] Free task or Whitelisted for task " + task +
                            ". Starting processing..")

                    if dvm_config.SEND_FEEDBACK_EVENTS:
                        await send_job_status_reaction(nip90_event, "processing", True, 0,
                                                       content=self.dvm_config.CUSTOM_PROCESSING_MESSAGE,
                                                       client=self.client, dvm_config=self.dvm_config, user=user)

                    #  when we reimburse users on error make sure to not send anything if it was free
                    if user.iswhitelisted or task_is_free:
                        amount = 0
                    await do_work(nip90_event, amount)
                # if task is directed to us via p tag and user has balance or is subscribed, do the job and update balance
                elif (p_tag_str == self.dvm_config.PUBLIC_KEY and (
                        user.balance >= int(
                    amount) and dvm_config.NIP88 is None) or (
                              p_tag_str == self.dvm_config.PUBLIC_KEY and user_has_active_subscription)):

                    if not user_has_active_subscription:
                        balance = max(user.balance - int(amount), 0)
                        update_sql_table(db=self.dvm_config.DB, npub=user.npub, balance=balance,
                                         iswhitelisted=user.iswhitelisted, isblacklisted=user.isblacklisted,
                                         nip05=user.nip05, lud16=user.lud16, name=user.name,
                                         lastactive=Timestamp.now().as_secs(), subscribed=user.subscribed)

                        print(
                            "[" + self.dvm_config.NIP89.NAME + "] Using user's balance for task: " + task +
                            ". Starting processing.. New balance is: " + str(balance))
                    else:
                        print("[" + self.dvm_config.NIP89.NAME + "] User has active subscription for task: " + task +
                              ". Starting processing.. Balance remains at: " + str(user.balance))

                    await send_job_status_reaction(nip90_event, "processing", True, 0,
                                                   content=self.dvm_config.CUSTOM_PROCESSING_MESSAGE,
                                                   client=self.client, dvm_config=self.dvm_config)

                    await do_work(nip90_event, amount)

                # else send a payment required event to user
                elif p_tag_str == "" or p_tag_str == self.dvm_config.PUBLIC_KEY:

                    if dvm_config.NIP88 is not None:
                        print(
                            "[" + self.dvm_config.NIP89.NAME + "]  Hinting user for Subscription: " +
                            nip90_event.id().to_hex())
                        # await send_job_status_reaction(nip90_event, "subscription-required",
                        #                               False, 0, client=self.client,
                        #                               dvm_config=self.dvm_config)
                    else:
                        bid = 0
                        for tag in nip90_event.tags():
                            if tag.as_vec()[0] == 'bid':
                                bid = int(tag.as_vec()[1])

                        print(
                            "[" + self.dvm_config.NIP89.NAME + "] Payment required: New Nostr " + task + " Job event: "
                            + nip90_event.as_json())
                        if bid > 0:
                            bid_offer = int(bid / 1000)
                            if bid_offer >= int(amount):
                                await send_job_status_reaction(nip90_event, "payment-required", False,
                                                               int(amount),  # bid_offer
                                                               client=self.client, dvm_config=self.dvm_config)

                        else:  # If there is no bid, just request server rate from user
                            print(
                                "[" + self.dvm_config.NIP89.NAME + "] Requesting payment for Event: " +
                                nip90_event.id().to_hex())
                            await send_job_status_reaction(nip90_event, "payment-required",
                                                           False, int(amount), client=self.client,
                                                           dvm_config=self.dvm_config)




                else:
                    if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                        print("[" + self.dvm_config.NIP89.NAME + "] Job addressed to someone else, skipping..")
            # else:
            # print("[" + self.dvm_config.NIP89.NAME + "] Task " + task + " not supported on this DVM, skipping..")

        async def handle_nutzap(nut_zap_event):
            if self.dvm_config.ENABLE_NUTZAP:
                nut_wallet = await nutzap_wallet.get_nut_wallet(self.client, self.keys)
                if nut_wallet is not None:
                    received_amount, message, sender = await nutzap_wallet.reedeem_nutzap(nut_zap_event, nut_wallet,
                                                                                          self.client, self.keys)
                    user = await get_or_add_user(db=self.dvm_config.DB, npub=sender, client=self.client,
                                                 config=self.dvm_config)
                    zapped_event = None
                    for tag in nut_zap_event.tags():
                        if tag.as_vec()[0] == 'e':
                            zapped_event = await get_event_by_id(tag.as_vec()[1], client=self.client,
                                                                 config=self.dvm_config)

                    if zapped_event is not None:
                        if zapped_event.kind() == EventDefinitions.KIND_FEEDBACK:
                            amount = 0
                            job_event = None
                            p_tag_str = ""
                            status = ""
                            for tag in zapped_event.tags():
                                if tag.as_vec()[0] == 'amount':
                                    amount = int(float(tag.as_vec()[1]) / 1000)
                                elif tag.as_vec()[0] == 'e':
                                    job_event = await get_event_by_id(tag.as_vec()[1], client=self.client,
                                                                      config=self.dvm_config)
                                    if job_event is not None:
                                        job_event = check_and_decrypt_tags(job_event, self.dvm_config)
                                        if job_event is None:
                                            return
                                    else:
                                        return
                                elif tag.as_vec()[0] == 'status':
                                    status = tag.as_vec()[1]


                                # if a reaction by us got zapped
                            print(status)

                            task_supported, task = await check_task_is_supported(job_event, client=self.client,
                                                                                 config=self.dvm_config)
                            if job_event is not None and task_supported:
                                print("NutZap received for NIP90 task: " + str(received_amount) + " Sats from " + str(
                                    user.name))
                                if amount <= received_amount:
                                    print("[" + self.dvm_config.NIP89.NAME + "]  Payment-request fulfilled...")
                                    await send_job_status_reaction(job_event, "processing", client=self.client,
                                                                   content=self.dvm_config.CUSTOM_PROCESSING_MESSAGE,
                                                                   dvm_config=self.dvm_config, user=user)
                                    indices = [i for i, x in enumerate(self.job_list) if
                                               x.event == job_event]
                                    index = -1
                                    if len(indices) > 0:
                                        index = indices[0]
                                    if index > -1:
                                        if self.job_list[index].is_processed:
                                            self.job_list[index].is_paid = True
                                            await check_and_return_event(self.job_list[index].result, job_event)
                                        elif not (self.job_list[index]).is_processed:
                                            # If payment-required appears before processing
                                            self.job_list.pop(index)
                                            print("Starting work...")
                                            await do_work(job_event, received_amount)
                                    else:
                                        print("Job not in List, but starting work...")
                                        await do_work(job_event, received_amount)

                                else:
                                    await send_job_status_reaction(job_event, "payment-rejected",
                                                                   False, received_amount, client=self.client,
                                                                   dvm_config=self.dvm_config)
                                    print("[" + self.dvm_config.NIP89.NAME + "] Invoice was not paid sufficiently")

                    if self.dvm_config.ENABLE_AUTO_MELT:
                        balance = nut_wallet.balance + received_amount
                        if balance > self.dvm_config.AUTO_MELT_AMOUNT:
                            lud16 = self.admin_config.LUD16
                            npub = self.dvm_config.PUBLIC_KEY
                            mint_index = 0
                            await nutzap_wallet.melt_cashu(nut_wallet, self.dvm_config.NUZAP_MINTS[mint_index],
                                                           self.dvm_config.AUTO_MELT_AMOUNT, self.client, self.keys,
                                                           lud16, npub)

            else:
                print("NutZaps not enabled for this DVM. ")

        async def handle_zap(zap_event):
            try:
                invoice_amount, zapped_event, sender, message, anon = await parse_zap_event_tags(zap_event,
                                                                                                 self.keys,
                                                                                                 self.dvm_config.NIP89.NAME,
                                                                                                 self.client,
                                                                                                 self.dvm_config)
                user = await get_or_add_user(db=self.dvm_config.DB, npub=sender, client=self.client,
                                             config=self.dvm_config)

                if zapped_event is not None:
                    if zapped_event.kind() == EventDefinitions.KIND_FEEDBACK:

                        amount = 0
                        job_event = None
                        p_tag_str = ""
                        status = ""
                        for tag in zapped_event.tags():
                            if tag.as_vec()[0] == 'amount':
                                amount = int(float(tag.as_vec()[1]) / 1000)
                            elif tag.as_vec()[0] == 'e':
                                job_event = await get_event_by_id(tag.as_vec()[1], client=self.client,
                                                                  config=self.dvm_config)
                                if job_event is not None:
                                    job_event = check_and_decrypt_tags(job_event, self.dvm_config)
                                    if job_event is None:
                                        return
                                else:
                                    return
                            elif tag.as_vec()[0] == 'status':
                                status = tag.as_vec()[1]
                                print(status)

                            # if a reaction by us got zapped
                        print(status)
                        if job_event.kind() == EventDefinitions.KIND_NIP88_SUBSCRIBE_EVENT:
                            await send_job_status_reaction(job_event, "subscription-success", client=self.client,
                                                           dvm_config=self.dvm_config, user=user)



                        else:
                            task_supported, task = await check_task_is_supported(job_event, client=self.client,
                                                                                 config=self.dvm_config)
                            if job_event is not None and task_supported:
                                print("Zap received for NIP90 task: " + str(invoice_amount) + " Sats from " + str(
                                    user.name))
                                if amount <= invoice_amount:
                                    print("[" + self.dvm_config.NIP89.NAME + "]  Payment-request fulfilled...")
                                    await send_job_status_reaction(job_event, "processing", client=self.client,
                                                                   content=self.dvm_config.CUSTOM_PROCESSING_MESSAGE,
                                                                   dvm_config=self.dvm_config, user=user)
                                    indices = [i for i, x in enumerate(self.job_list) if
                                               x.event == job_event]
                                    index = -1
                                    if len(indices) > 0:
                                        index = indices[0]
                                    if index > -1:
                                        if self.job_list[index].is_processed:
                                            self.job_list[index].is_paid = True
                                            await check_and_return_event(self.job_list[index].result, job_event)
                                        elif not (self.job_list[index]).is_processed:
                                            # If payment-required appears before processing
                                            self.job_list.pop(index)
                                            print("Starting work...")
                                            await do_work(job_event, invoice_amount)
                                    else:
                                        print("Job not in List, but starting work...")
                                        await do_work(job_event, invoice_amount)

                                else:
                                    await send_job_status_reaction(job_event, "payment-rejected",
                                                                   False, invoice_amount, client=self.client,
                                                                   dvm_config=self.dvm_config)
                                    print("[" + self.dvm_config.NIP89.NAME + "] Invoice was not paid sufficiently")
                    elif zapped_event.kind() == EventDefinitions.KIND_NIP88_SUBSCRIBE_EVENT:
                        print("new subscription, doing nothing")

                    elif zapped_event.kind() in EventDefinitions.ANY_RESULT:
                        print("[" + self.dvm_config.NIP89.NAME + "] "
                                                                 "Someone zapped the result of an exisiting Task. Nice")
                    elif not anon:
                        print("[" + self.dvm_config.NIP89.NAME + "] Note Zap received for DVM balance: " +
                              str(invoice_amount) + " Sats from " + str(user.name))
                    #    update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client,
                    #                        config=self.dvm_config)

                    # a regular note
                elif not anon and dvm_config.NIP88 is None:
                    print("[" + self.dvm_config.NIP89.NAME + "] Profile Zap received for DVM balance: " +
                          str(invoice_amount) + " Sats from " + str(user.name))
                # update_user_balance(self.dvm_config.DB, sender, invoice_amount, client=self.client,
                #                     config=self.dvm_config)

            except Exception as e:
                print("[" + self.dvm_config.NIP89.NAME + "] Error during content decryption: " + str(e))

        async def check_event_has_not_unfinished_job_input(nevent, append, client, dvmconfig):
            task_supported, task = await check_task_is_supported(nevent, client, config=dvmconfig)
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
                            evt = await get_referenced_event_by_id(event_id=input, client=client,
                                                                   kinds=EventDefinitions.ANY_RESULT,
                                                                   dvm_config=dvmconfig)
                            if evt is None:
                                if append:
                                    job_ = RequiredJobToWatch(event=nevent, timestamp=Timestamp.now().as_secs())
                                    self.jobs_on_hold_list.append(job_)
                                    await send_job_status_reaction(nevent, "chain-scheduled", True, 0,
                                                                   client=client, dvm_config=dvmconfig)

                                return False
            else:
                return True

        async def check_and_return_event(data, original_event: Event):
            amount = 0
            for x in self.job_list:
                if x.event == original_event:
                    is_paid = x.is_paid
                    amount = x.amount
                    x.result = data
                    x.is_processed = True
                    if self.dvm_config.SHOW_RESULT_BEFORE_PAYMENT and not is_paid:
                        await send_nostr_reply_event(data, original_event.as_json())
                        await send_job_status_reaction(original_event, "success", amount,
                                                       dvm_config=self.dvm_config,
                                                       )  # or payment-required, or both?
                    elif not self.dvm_config.SHOW_RESULT_BEFORE_PAYMENT and not is_paid:
                        await send_job_status_reaction(original_event, "success", amount,
                                                       dvm_config=self.dvm_config,
                                                       )  # or payment-required, or both?

                    if self.dvm_config.SHOW_RESULT_BEFORE_PAYMENT and is_paid:
                        self.job_list.remove(x)
                    elif not self.dvm_config.SHOW_RESULT_BEFORE_PAYMENT and is_paid:
                        self.job_list.remove(x)
                        await send_nostr_reply_event(data, original_event.as_json())
                    break

                task = await get_task(original_event, self.client, self.dvm_config)
                for dvm in self.dvm_config.SUPPORTED_DVMS:
                    if task == dvm.TASK or dvm.TASK == "generic":
                        try:
                            post_processed = await dvm.post_process(data, original_event)
                            await send_nostr_reply_event(post_processed, original_event.as_json())
                        except Exception as e:
                            print(e)
                            # Zapping back by error in post-processing is a risk for the DVM because work has been done,
                            # but maybe something with parsing/uploading failed. Try to avoid errors here as good as possible
                            await send_job_status_reaction(original_event, "error",
                                                           content="Error in Post-processing: " + str(e),
                                                           dvm_config=self.dvm_config,
                                                           )
                            if amount > 0 and self.dvm_config.LNBITS_ADMIN_KEY != "":
                                user = await get_or_add_user(self.dvm_config.DB, original_event.author().to_hex(),
                                                             client=self.client, config=self.dvm_config)
                                print(user.lud16 + " " + str(amount))
                                bolt11 = zaprequest(user.lud16, amount, "Couldn't finish job, returning sats",
                                                    original_event, "",
                                                    self.keys, self.dvm_config.RELAY_LIST, zaptype="private")
                                if bolt11 is None:
                                    print("Receiver has no Lightning address, can't zap back.")
                                    return
                                try:
                                    payment_hash = pay_bolt11_ln_bits(bolt11, self.dvm_config)
                                except Exception as e:
                                    print(e)

        async def send_nostr_reply_event(content, original_event_as_str):
            original_event = Event.from_json(original_event_as_str)
            request_tag = Tag.parse(["request", original_event_as_str])
            e_tag = Tag.parse(["e", original_event.id().to_hex()])
            p_tag = Tag.parse(["p", original_event.author().to_hex()])
            alt_tag = Tag.parse(["alt", "This is the result of a NIP90 DVM AI task with kind " + str(
                original_event.kind().as_u64()) + ". The task was: " + original_event.content()])
            status_tag = Tag.parse(["status", "success"])
            reply_tags = [request_tag, e_tag, p_tag, alt_tag, status_tag]

            relay_tag = None
            for tag in original_event.tags():
                if tag.as_vec()[0] == "relays":
                    relay_tag = tag
                if tag.as_vec()[0] == "client":
                    client = tag.as_vec()[1]
                    reply_tags.append(Tag.parse(["client", client]))
            if relay_tag is not None:
                reply_tags.append(relay_tag)

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
                print(content)
                content = nip04_encrypt(self.keys.secret_key(), PublicKey.from_hex(original_event.author().to_hex()),
                                        content)

            reply_event = EventBuilder(Kind(original_event.kind().as_u64() + 1000), str(content), reply_tags).to_event(
                self.keys)

            # send_event(reply_event, client=self.client, dvm_config=self.dvm_config)
            await send_event_outbox(reply_event, client=self.client, dvm_config=self.dvm_config)
            if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                print(bcolors.GREEN + "[" + self.dvm_config.NIP89.NAME + "] " + str(
                    original_event.kind().as_u64() + 1000) + " Job Response event sent: " + reply_event.as_json() + bcolors.ENDC)
            elif self.dvm_config.LOGLEVEL.value >= LogLevel.INFO.value:
                print(bcolors.GREEN + "[" + self.dvm_config.NIP89.NAME + "] " + str(
                    original_event.kind().as_u64() + 1000) + " Job Response event sent: " + reply_event.id().to_hex() + bcolors.ENDC)

        async def send_job_status_reaction(original_event, status, is_paid=True, amount=0, client=None,
                                           content=None,
                                           dvm_config=None, user=None):

            task = await get_task(original_event, client=client, dvm_config=dvm_config)
            alt_description, reaction = build_status_reaction(status, task, amount, content, dvm_config)

            e_tag = Tag.parse(["e", original_event.id().to_hex()])
            p_tag = Tag.parse(["p", original_event.author().to_hex()])
            alt_tag = Tag.parse(["alt", alt_description])
            status_tag = Tag.parse(["status", status])

            reply_tags = [e_tag, alt_tag, status_tag]

            relay_tag = None
            for tag in original_event.tags():
                if tag.as_vec()[0] == "relays":
                    relay_tag = tag
                    break
            if relay_tag is not None:
                reply_tags.append(relay_tag)

            encryption_tags = []

            encrypted = False
            for tag in original_event.tags():
                if tag.as_vec()[0] == "encrypted":
                    encrypted = True
                    encrypted_tag = Tag.parse(["encrypted"])
                    encryption_tags.append(encrypted_tag)

            if encrypted:
                encryption_tags.append(p_tag)
                encryption_tags.append(e_tag)

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
            if status == "payment-required" or (
                    status == "processing" and not is_paid):
                if dvm_config.LNBITS_INVOICE_KEY != "":
                    try:
                        bolt11, payment_hash = create_bolt11_ln_bits(amount, dvm_config)
                    except Exception as e:
                        print(e)
                        try:
                            bolt11, payment_hash = create_bolt11_lud16(dvm_config.LN_ADDRESS,
                                                                       amount)
                        except Exception as e:
                            print(e)
                            bolt11 = None
                elif dvm_config.LN_ADDRESS != "":
                    try:
                        bolt11, payment_hash = create_bolt11_lud16(dvm_config.LN_ADDRESS, amount)
                    except Exception as e:
                        print(e)
                        bolt11 = None

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

                if dvm_config.LNBITS_INVOICE_KEY != "" and bolt11 is not None:
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
                content = nip04_encrypt(self.keys.secret_key(), PublicKey.from_hex(original_event.author().to_hex()),
                                        content)
                reply_tags = encryption_tags

            else:
                content = reaction

            keys = Keys.parse(dvm_config.PRIVATE_KEY)
            reaction_event = EventBuilder(EventDefinitions.KIND_FEEDBACK, str(content), reply_tags).to_event(keys)
            # send_event(reaction_event, client=self.client, dvm_config=self.dvm_config)
            await send_event_outbox(reaction_event, client=self.client, dvm_config=self.dvm_config)

            if self.dvm_config.LOGLEVEL.value >= LogLevel.DEBUG.value:
                print(bcolors.YELLOW + "[" + self.dvm_config.NIP89.NAME + "]" + " Sent Kind " + str(
                    EventDefinitions.KIND_FEEDBACK.as_u64()) + " Reaction: " + status + " " + reaction_event.as_json() + bcolors.ENDC)
            elif self.dvm_config.LOGLEVEL.value >= LogLevel.INFO.value:
                print(bcolors.YELLOW + "[" + self.dvm_config.NIP89.NAME + "]" + " Sent Kind " + str(
                    EventDefinitions.KIND_FEEDBACK.as_u64()) + " Reaction: " + status + " " + reaction_event.id().to_hex() + bcolors.ENDC)

            return reaction_event.as_json()

        async def _read_stream(stream, cb):
            while True:
                line = await stream.readline()
                if line:
                    cb(line)
                else:
                    break

        async def _stream_subprocess(cmd, stdout_cb, stderr_cb):
            process = await asyncio.create_subprocess_exec(*cmd,
                                                           stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)

        async def run_subprocess(python_bin, dvm_config, request_form, stdout_cb, stderr_cb):
            print("Running subprocess, please wait..")
            process = await asyncio.create_subprocess_exec(
                python_bin, dvm_config.SCRIPT,
                '--request', json.dumps(request_form),
                '--identifier', dvm_config.IDENTIFIER,
                '--output', 'output.txt',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await asyncio.gather(
                _read_stream(process.stdout, stdout_cb),
                _read_stream(process.stderr, stderr_cb)
            )
            return await process.wait()

            # stdout, stderr = await process.communicate()

            # retcode = process.returncode

            # if retcode != 0:
            #    print(f"Error: {stderr.decode()}")
            # else:
            #    print(f"Output: {stdout.decode()}")

            # return retcode

        async def do_work(job_event, amount):
            if ((
                    EventDefinitions.KIND_NIP90_EXTRACT_TEXT.as_u64() <= job_event.kind().as_u64() <= EventDefinitions.KIND_NIP90_GENERIC.as_u64())
                    or job_event.kind().as_u64() == EventDefinitions.KIND_DM.as_u64()):

                task = await get_task(job_event, client=self.client, dvm_config=self.dvm_config)

                for dvm in self.dvm_config.SUPPORTED_DVMS:
                    result = ""
                    try:
                        if task == dvm.TASK or dvm.TASK == "generic":

                            request_form = await dvm.create_request_from_nostr_event(job_event, self.client,
                                                                                     self.dvm_config)

                            if dvm_config.USE_OWN_VENV:
                                python_location = "/bin/python"
                                if platform == "win32":
                                    python_location = "/Scripts/python"
                                python_bin = (r'cache/venvs/' + os.path.basename(dvm_config.SCRIPT).split(".py")[0]
                                              + python_location)
                                # retcode = subprocess.call([python_bin, dvm_config.SCRIPT,
                                #                           '--request', json.dumps(request_form),
                                #                           '--identifier', dvm_config.IDENTIFIER,
                                #                           '--output', 'output.txt'])
                                await run_subprocess(python_bin, dvm_config, request_form,
                                                     lambda x: print("%s" % x.decode("utf-8").replace("\n", "")),
                                                     lambda x: print("STDERR: %s" % x.decode("utf-8")))
                                print("Finished processing, loading data..")

                                with open(os.path.abspath('output.txt'), encoding="utf-8") as f:
                                    resultall = f.readlines()
                                    for line in resultall:
                                        if line != '\n':
                                            result += line
                                os.remove(os.path.abspath('output.txt'))
                                assert not result.startswith("Error:")
                                print(result)

                            else:  # Some components might have issues with running code in otuside venv.
                                # We install locally in these cases for now
                                result = await dvm.process(request_form)
                            try:
                                post_processed = await dvm.post_process(result, job_event)
                                await send_nostr_reply_event(post_processed, job_event.as_json())
                            except Exception as e:
                                print(bcolors.RED + "[" + self.dvm_config.NIP89.NAME + "] Error: " + str(
                                    e) + bcolors.ENDC)
                                await send_job_status_reaction(job_event, "error", content=str(e),
                                                               dvm_config=self.dvm_config)
                    except Exception as e:
                        print(
                            bcolors.RED + "[" + self.dvm_config.NIP89.NAME + "] Error: " + str(e) + bcolors.ENDC)

                        # we could send the exception here to the user, but maybe that's not a good idea after all.
                        await send_job_status_reaction(job_event, "error", content=result,
                                                       dvm_config=self.dvm_config)
                        # Zapping back the user on error
                        if amount > 0 and self.dvm_config.LNBITS_ADMIN_KEY != "":
                            user = await get_or_add_user(self.dvm_config.DB, job_event.author().to_hex(),
                                                         client=self.client, config=self.dvm_config)
                            print(user.lud16 + " " + str(amount))
                            bolt11 = zaprequest(user.lud16, amount, "Couldn't finish job, returning sats", job_event,
                                                PublicKey.parse(user.npub),
                                                self.keys, self.dvm_config.RELAY_LIST, zaptype="private")
                            if bolt11 is None:
                                print("Receiver has no Lightning address, can't zap back.")
                                return
                            try:
                                payment_hash = pay_bolt11_ln_bits(bolt11, self.dvm_config)
                            except Exception as e:
                                print(e)

                        return

        asyncio.create_task(self.client.handle_notifications(NotificationHandler()))

        while True:
            for dvm in self.dvm_config.SUPPORTED_DVMS:
                await dvm.schedule(self.dvm_config)

            for job in self.job_list:
                if job.bolt11 != "" and job.payment_hash != "" and not job.payment_hash is None and not job.is_paid:
                    ispaid = check_bolt11_ln_bits_is_paid(job.payment_hash, self.dvm_config)
                    if ispaid and job.is_paid is False:
                        print("is paid")
                        job.is_paid = True
                        amount = parse_amount_from_bolt11_invoice(job.bolt11)

                        job.is_paid = True
                        await send_job_status_reaction(job.event, "processing", True, 0,
                                                       content=self.dvm_config.CUSTOM_PROCESSING_MESSAGE,
                                                       client=self.client,
                                                       dvm_config=self.dvm_config)
                        print("[" + self.dvm_config.NIP89.NAME + "] doing work from joblist")
                        await do_work(job.event, amount)
                    elif ispaid is None:  # invoice expired
                        self.job_list.remove(job)

                if Timestamp.now().as_secs() > job.expires:
                    self.job_list.remove(job)

            for job in self.jobs_on_hold_list:
                if await check_event_has_not_unfinished_job_input(job.event, False, client=self.client,
                                                                  dvmconfig=self.dvm_config):
                    await handle_nip90_job_event(nip90_event=job.event)
                    try:
                        self.jobs_on_hold_list.remove(job)
                    except:
                        print("[" + self.dvm_config.NIP89.NAME + "] Error removing Job on Hold from List after expiry")

                if Timestamp.now().as_secs() > job.timestamp + 60 * 20:  # remove jobs to look for after 20 minutes..
                    self.jobs_on_hold_list.remove(job)

            await asyncio.sleep(1)
