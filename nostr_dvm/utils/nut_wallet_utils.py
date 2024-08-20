import asyncio
import json
import os
from collections import namedtuple
from datetime import timedelta

import requests
from nostr_dvm.utils.database_utils import fetch_user_metadata
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.zap_utils import pay_bolt11_ln_bits, zaprequest
from nostr_sdk import Tag, Keys, nip44_encrypt, nip44_decrypt, Nip44Version, EventBuilder, Client, Filter, Kind, \
    EventId, nip04_decrypt, nip04_encrypt, Options, NostrSigner, PublicKey, init_logger, LogLevel, Metadata
from nostr_dvm.utils.print import bcolors

class NutWallet(object):
    def __init__(self):
        self.name: str = "NutWallet"
        self.description: str = ""
        self.balance: int = 0
        self.unit: str = "sat"
        self.mints: list = []
        self.relays: list = []
        self.nutmints: list = []
        self.privkey: str = ""
        self.d: str = ""
        self.a: str = ""
        self.legacy_encryption: bool = False  # Use Nip04 instead of Nip44, for reasons, turn to False ASAP.
        self.trust_unknown_mints: bool = False
        self.missing_balance_strategy: str = "mint" #swap to use existing tokens from other mints (fees!) or mint to mint from lightning


class NutMint(object):
    def __init__(self):
        self.previous_event_id = None
        self.proofs: list = []
        self.mint_url: str = ""
        self.previous_event_id: EventId
        self.a: str = ""

    def available_balance(self):
        balance = 0
        for proof in self.proofs:
            balance += proof.amount
        return balance



class NutZapWallet:

    async def client_connect(self, relay_list):
        keys = Keys.parse(check_and_set_private_key("TEST_ACCOUNT_PK"))
        wait_for_send = False
        skip_disconnected_relays = True
        opts = (Options().wait_for_send(wait_for_send).send_timeout(timedelta(seconds=5))
                .skip_disconnected_relays(skip_disconnected_relays))

        signer = NostrSigner.keys(keys)
        client = Client.with_opts(signer, opts)
        for relay in relay_list:
            await client.add_relay(relay)
        await client.connect()
        return client, keys

    async def create_new_nut_wallet(self, mint_urls, relays, client, keys, name, description):
        new_nut_wallet = NutWallet()
        new_nut_wallet.privkey = Keys.generate().secret_key().to_hex()
        new_nut_wallet.balance = 0
        new_nut_wallet.unit = "sats"
        new_nut_wallet.name = name
        new_nut_wallet.description = description
        new_nut_wallet.mints = mint_urls
        new_nut_wallet.relays = relays
        new_nut_wallet.d = "wallet"  # sha256(str(new_nut_wallet.name + new_nut_wallet.description).encode('utf-8')).hexdigest()[:16]
        new_nut_wallet.a = str(Kind(7375).as_u64()) + ":" + keys.public_key().to_hex() + ":" + new_nut_wallet.d
        print("Creating Wallet..")
        send_response_id = await self.create_or_update_nut_wallet_event(new_nut_wallet, client, keys)

        if send_response_id is None:
            print("Warning: Not published")

        print(new_nut_wallet.name + ": " + str(new_nut_wallet.balance) + " " + new_nut_wallet.unit + " Mints: " + str(
            new_nut_wallet.mints) + " Key: " + new_nut_wallet.privkey)

    async def create_or_update_nut_wallet_event(self, nut_wallet: NutWallet, client, keys):
        innertags = [Tag.parse(["balance", str(nut_wallet.balance), nut_wallet.unit]).as_vec(),
                     Tag.parse(["privkey", nut_wallet.privkey]).as_vec()]

        if nut_wallet.legacy_encryption:
            content = nip04_encrypt(keys.secret_key(), keys.public_key(), json.dumps(innertags))
        else:
            content = nip44_encrypt(keys.secret_key(), keys.public_key(), json.dumps(innertags), Nip44Version.V2)

        if nut_wallet.unit is None:
            nut_wallet.unit = "sat"

        tags = [Tag.parse(["name", nut_wallet.name]),
                Tag.parse(["unit", nut_wallet.unit]),
                Tag.parse(["description", nut_wallet.description]),
                Tag.parse(["d", nut_wallet.d])]

        for mint in nut_wallet.mints:
            mint_tag = Tag.parse(["mint", mint])
            tags.append(mint_tag)

        for relay in nut_wallet.relays:
            relay_tag = Tag.parse(["relay", relay])
            tags.append(relay_tag)

        event = EventBuilder(EventDefinitions.KIND_NUT_WALLET, content, tags).to_event(keys)
        send_response = await client.send_event(event)

        print(
            bcolors.BLUE + "[" + nut_wallet.name + "] announced nut wallet (" + send_response.id.to_hex() + ")" + bcolors.ENDC)
        return send_response.id

    async def get_nut_wallet(self, client, keys) -> NutWallet:
        from cashu.core.base import Proof
        nut_wallet = None

        wallet_filter = Filter().kind(EventDefinitions.KIND_NUT_WALLET).author(keys.public_key())
        wallets = await client.get_events_of([wallet_filter], timedelta(10))

        if len(wallets) > 0:

            nut_wallet = NutWallet()

            latest = 0
            best_wallet = None
            for wallet_event in wallets:

                isdeleted = False
                for tag in wallet_event.tags():
                    if tag.as_vec()[0] == "deleted":
                        isdeleted = True
                        break
                if isdeleted:
                    continue
                else:
                    if wallet_event.created_at().as_secs() > latest:
                        latest = wallet_event.created_at().as_secs()
                        best_wallet = wallet_event

            try:
                content = nip44_decrypt(keys.secret_key(), keys.public_key(), best_wallet.content())
                print(content)
            except:
                content = nip04_decrypt(keys.secret_key(), keys.public_key(), best_wallet.content())
                print(content)
                print("Warning: This Wallet is using a NIP04 enconding.., it should use NIP44 encoding ")
                nut_wallet.legacy_encryption = True

            inner_tags = json.loads(content)
            for tag in inner_tags:
                # These tags must be encrypted instead of in the outer tags
                if tag[0] == "balance":
                    nut_wallet.balance = int(tag[1])
                elif tag[0] == "privkey":
                    nut_wallet.privkey = tag[1]

                # These tags can be encrypted instead of in the outer tags
                elif tag[0] == "name":
                    nut_wallet.name = tag[1]
                elif tag[0] == "description":
                    nut_wallet.description = tag[1]
                elif tag[0] == "unit":
                    nut_wallet.unit = tag[1]
                elif tag[0] == "relay":
                    if tag[1] not in nut_wallet.relays:
                        nut_wallet.relays.append(tag[1])
                elif tag[0] == "mint":
                    if tag[1] not in nut_wallet.mints:
                        nut_wallet.mints.append(tag[1])

            for tag in best_wallet.tags():
                if tag.as_vec()[0] == "d":
                    nut_wallet.d = tag.as_vec()[1]

                # These tags can be in the outer tags (if not encrypted)
                elif tag.as_vec()[0] == "name":
                    nut_wallet.name = tag.as_vec()[1]
                elif tag.as_vec()[0] == "description":
                    nut_wallet.description = tag.as_vec()[1]
                elif tag.as_vec()[0] == "unit":
                    nut_wallet.unit = tag.as_vec()[1]
                elif tag.as_vec()[0] == "relay":
                    if tag.as_vec()[1] not in nut_wallet.relays:
                        nut_wallet.relays.append(tag.as_vec()[1])
                elif tag.as_vec()[0] == "mint":
                    if tag.as_vec()[1] not in nut_wallet.mints:
                        nut_wallet.mints.append(tag.as_vec()[1])
            nut_wallet.a = str("37375:" + best_wallet.author().to_hex() + ":" + nut_wallet.d)

            # Now all proof events
            proof_filter = Filter().kind(Kind(7375)).author(keys.public_key())
            proof_events = await client.get_events_of([proof_filter], timedelta(5))

            latest_proof_sec = 0
            latest_proof_event_id = EventId
            for proof_event in proof_events:
                if proof_event.created_at().as_secs() > latest_proof_sec:
                    latest_proof_sec = proof_event.created_at().as_secs()
                    latest_proof_event_id = proof_event.id()

            for proof_event in proof_events:
                try:
                    content = nip44_decrypt(keys.secret_key(), keys.public_key(), proof_event.content())
                except:
                    content = nip04_decrypt(keys.secret_key(), keys.public_key(), proof_event.content())
                    print("Warning: This Proofs event is using a NIP04 enconding.., it should use NIP44 encoding ")

                proofs_json = json.loads(content)
                mint_url = ""
                a = ""
                print("")
                print("AVAILABLE MINT:")

                try:
                    mint_url = proofs_json['mint']
                    print("mint: " + mint_url)
                    a = proofs_json['a']
                    print("a: " + a)
                except Exception as e:
                    pass

                for tag in proof_event.tags():
                    if tag.as_vec()[0] == "mint":
                        mint_url = tag.as_vec()[1]
                        print("mint: " + mint_url)
                    elif tag.as_vec()[0] == "a":
                        a = tag.as_vec()[1]
                        print("a: " + a)

                nut_mint = NutMint()
                nut_mint.mint_url = mint_url
                nut_mint.a = a
                nut_mint.previous_event_id = latest_proof_event_id
                nut_mint.proofs = []

                for proof in proofs_json['proofs']:
                    proofs = [x for x in nut_mint.proofs if x.secret == proof['secret']]
                    if len(proofs) == 0:
                        nut_proof = Proof()
                        nut_proof.id = proof['id']
                        nut_proof.secret = proof['secret']
                        nut_proof.amount = proof['amount']
                        nut_proof.C = proof['C']
                        nut_mint.proofs.append(nut_proof)
                        #print(proof)

                mints = [x for x in nut_wallet.nutmints if x.mint_url == mint_url]
                if len(mints) == 0:
                    nut_wallet.nutmints.append(nut_mint)
                print("Mint Balance: " + str(nut_mint.available_balance()) + " Sats")

        return nut_wallet

    async def update_nut_wallet(self, nut_wallet, mints, client, keys):
        for mint in mints:
            if mint not in nut_wallet.mints:
                nut_wallet.mints.append(mint)

        balance = 0
        for mint in nut_wallet.nutmints:
            for proof in mint.proofs:
                balance += proof.amount

        nut_wallet.balance = balance

        id = await self.create_or_update_nut_wallet_event(nut_wallet, client, keys)

        if id is None:
            print(bcolors.RED + str("Error publishing WalletEvent") + bcolors.ENDC)

        print(nut_wallet.name + ": " + str(nut_wallet.balance) + " " + nut_wallet.unit + " Mints: " + str(
            nut_wallet.mints) + " Key: " + nut_wallet.privkey)

        return nut_wallet

    def get_mint(self, nut_wallet, mint_url) -> NutMint:
        mints = [x for x in nut_wallet.nutmints if x.mint_url == mint_url]
        if len(mints) == 0:
            mint = NutMint()
            mint.proofs = []
            mint.previous_event_id = None
            mint.a = nut_wallet.a
            mint.mint_url = mint_url

        else:
            mint = mints[0]

        return mint

    async def create_transaction_history_event(self, nut_wallet: NutWallet, amount: int, unit: str,
                                               event_old: EventId | None,
                                               event_new: EventId, direction: str, marker, sender_hex, event_hex,
                                               client: Client, keys: Keys):
        # direction
        # in = received
        # out = sent

        # marker:
        # created - A new token event was created.
        # destroyed - A token event was destroyed.
        # redeemed - A [[NIP-61]] nutzap was redeemed."

        relays = await client.relays()
        relay_hints = relays.keys()
        relay_hint = list(relay_hints)[0]

        inner_tags = []
        inner_tags.append(["direction", direction])
        inner_tags.append(["amount", str(amount), unit])

        if event_old is not None:
            inner_tags.append(["e", event_old.to_hex(), relay_hint, "destroyed"])

        inner_tags.append(["e", event_new.to_hex(), relay_hint, "created"])

        message = json.dumps(inner_tags)
        if nut_wallet.legacy_encryption:
            content = nip04_encrypt(keys.secret_key(), keys.public_key(), message)
        else:
            content = nip44_encrypt(keys.secret_key(), keys.public_key(), message, Nip44Version.V2)

        tags = [Tag.parse(["a", nut_wallet.a])]
        if marker == "redeemed" or marker == "zapped":
            e_tag = Tag.parse(["e", event_hex, relay_hint, marker])
            tags.append(e_tag)
            p_tag = Tag.parse(["p", sender_hex])
            tags.append(p_tag)

        event = EventBuilder(Kind(7376), content, tags).to_event(keys)
        eventid = await client.send_event(event)

    async def create_unspent_proof_event(self, nut_wallet: NutWallet, mint_proofs, mint_url, amount, direction, marker,
                                         sender_hex, event_hex,
                                         client, keys):
        new_proofs = []
        mint = self.get_mint(nut_wallet, mint_url)
        mint.proofs = mint_proofs
        for proof in mint_proofs:
            proofjson = {
                "id": proof['id'],
                "amount": proof['amount'],
                "secret": proof['secret'],
                "C": proof['C']
            }
            #print("Mint proofs:")
            #print(proof)
            new_proofs.append(proofjson)
        old_event_id = mint.previous_event_id

        if mint.previous_event_id is not None:
            print(
                bcolors.MAGENTA + "[" + nut_wallet.name + "] Deleted previous proofs event.. : (" + mint.previous_event_id.to_hex() + ")" + bcolors.ENDC)
            evt = EventBuilder.delete([mint.previous_event_id], reason="deleted").to_event(
                keys)  # .to_pow_event(keys, 28)
            response = await client.send_event(evt)

        tags = []
        # print(nut_wallet.a)
        a_tag = Tag.parse(["a", nut_wallet.a])
        tags.append(a_tag)

        j = {
            "mint": mint_url,
            "proofs": new_proofs
        }

        message = json.dumps(j)

        # print(message)
        if nut_wallet.legacy_encryption:
            content = nip04_encrypt(keys.secret_key(), keys.public_key(), message)
        else:
            content = nip44_encrypt(keys.secret_key(), keys.public_key(), message, Nip44Version.V2)

        event = EventBuilder(Kind(7375), content, tags).to_event(keys)
        eventid = await client.send_event(event)
        await self.create_transaction_history_event(nut_wallet, amount, nut_wallet.unit, old_event_id, eventid.id,
                                                    direction, marker, sender_hex, event_hex, client, keys)

        print(
            bcolors.GREEN + "[" + nut_wallet.name + "] Published new proofs event.. : (" + eventid.id.to_hex() + ")" + bcolors.ENDC)

        return eventid.id

    async def mint_token(self, mint, amount):
        from cashu.wallet.wallet import Wallet
        # TODO probably there's a library function for this
        url = mint + "/v1/mint/quote/bolt11"
        json_object = {"unit": "sat", "amount": amount}

        headers = {"Content-Type": "application/json; charset=utf-8"}
        request_body = json.dumps(json_object).encode('utf-8')
        request = requests.post(url, data=request_body, headers=headers)
        tree = json.loads(request.text)

        lnbits_config = {
            "LNBITS_ADMIN_KEY": os.getenv("LNBITS_ADMIN_KEY"),
            "LNBITS_URL": os.getenv("LNBITS_HOST")
        }
        lnbits_config_obj = namedtuple("LNBITSCONFIG", lnbits_config.keys())(*lnbits_config.values())

        paymenthash = pay_bolt11_ln_bits(tree["request"], lnbits_config_obj)
        print(paymenthash)
        url = f"{mint}/v1/mint/quote/bolt11/{tree['quote']}"

        response = requests.get(url, data=request_body, headers=headers)
        tree2 = json.loads(response.text)
        waitfor = 5
        while not tree2["paid"]:
            await asyncio.sleep(1)
            response = requests.get(url, data=request_body, headers=headers)
            tree2 = json.loads(response.text)
            waitfor -= 1
            if waitfor == 0:
                break

        if tree2["paid"]:
            # print(response.text)
            wallet = await Wallet.with_db(
                url=mint,
                db="db/Cashu",
            )

            await wallet.load_mint()
            proofs = await wallet.mint(amount, tree['quote'], None)
            return proofs

    async def announce_nutzap_info_event(self, nut_wallet, client, keys):
        tags = []
        for relay in nut_wallet.relays:
            tags.append(Tag.parse(["relay", relay]))
        for mint in nut_wallet.mints:
            tags.append(Tag.parse(["mint", mint]))

        pubkey = Keys.parse(nut_wallet.privkey).public_key().to_hex()
        tags.append(Tag.parse(["pubkey", pubkey]))

        event = EventBuilder(Kind(10019), "", tags).to_event(keys)
        eventid = await client.send_event(event)
        print(
            bcolors.CYAN + "[" + nut_wallet.name + "] Announced mint preferences info event (" + eventid.id.to_hex() + ")" + bcolors.ENDC)

    async def fetch_mint_info_event(self, pubkey, client):
        mint_info_filter = Filter().kind(Kind(10019)).author(PublicKey.parse(pubkey))
        preferences = await client.get_events_of([mint_info_filter], timedelta(5))
        mints = []
        relays = []
        pubkey = ""

        if len(preferences) > 0:
            preference = preferences[0]

            for tag in preference.tags():
                if tag.as_vec()[0] == "pubkey":
                    pubkey = tag.as_vec()[1]
                elif tag.as_vec()[0] == "relay":
                    relays.append(tag.as_vec()[1])
                elif tag.as_vec()[0] == "mint":
                    mints.append(tag.as_vec()[1])

        return pubkey, mints, relays

    async def update_spend_mint_proof_event(self, nut_wallet, send_proofs, mint_url, marker, sender_hex, event_hex,
                                            client, keys):
        mint = self.get_mint(nut_wallet, mint_url)

        print(mint.mint_url)
        print(send_proofs)
        amount = 0
        for send_proof in send_proofs:
            entry = [x for x in mint.proofs if x.id == send_proof.id and x.secret == send_proof.secret]
            if len(entry) > 0:
                mint.proofs.remove(entry[0])
                amount += send_proof.amount

        # create new event
        mint.previous_event_id = await self.create_unspent_proof_event(nut_wallet, mint.proofs, mint.mint_url, amount,
                                                                       "out",
                                                                       marker, sender_hex,
                                                                       event_hex, client, keys)
        nut_wallet.balance = nut_wallet.balance - amount
        return await self.update_nut_wallet(nut_wallet, [mint.mint_url], client, keys)

    async def mint_cashu(self, nut_wallet: NutWallet, mint_url, client, keys, amount):
        print("Minting new tokens on: " + mint_url)
        # Mint the Token at the selected mint
        proofs = await self.mint_token(mint_url, amount)
        print(proofs)

        return await self.add_proofs_to_wallet(nut_wallet, mint_url, proofs, "created", None, None, client, keys)

    async def add_proofs_to_wallet(self, nut_wallet, mint_url, new_proofs, marker, sender, event, client: Client,
                                   keys: Keys):
        mint = self.get_mint(nut_wallet, mint_url)
        additional_amount = 0
        # store the new proofs in proofs_temp
        all_proofs = []
        # check for other proofs from same mint, add them to the list of proofs
        for nut_proof in mint.proofs:
            all_proofs.append(nut_proof)
        # add new proofs and calculate additional balance
        for proof in new_proofs:
            all_proofs.append(proof)
            nut_wallet.balance += proof.amount
            additional_amount += proof.amount

        print("New amount: " + str(additional_amount))
        mint.previous_event_id = await self.create_unspent_proof_event(nut_wallet, all_proofs, mint_url,
                                                                       additional_amount, "in",
                                                                       marker,
                                                                       sender, event, client, keys)

        return await self.update_nut_wallet(nut_wallet, [mint_url], client, keys)


    async def handle_low_balance_on_mint(self, nut_wallet, outgoing_mint_url, mint, amount, client, keys):

        required_amount = amount - mint.available_balance()
        if nut_wallet.missing_balance_strategy == "mint":
            await self.mint_cashu(nut_wallet, outgoing_mint_url, client, keys, required_amount)

        elif nut_wallet.missing_balance_strategy == "swap":
            for nutmint in nut_wallet.nutmints:
                estimated_fees = 3
                if nutmint.available_balance() > required_amount+estimated_fees:
                    await self.swap(required_amount, nutmint.mint_url, outgoing_mint_url)
                    break



    async def send_nut_zap(self, amount, comment, nut_wallet: NutWallet, zapped_event, zapped_user, client: Client,
                           keys: Keys):
        from cashu.wallet.wallet import Wallet
        unit = "sats"

        p2pk_pubkey, mints, relays = await self.fetch_mint_info_event(zapped_user, client)
        if len(mints) == 0:
            print("No preferred mint set, returning")
            return

        mint_success = False
        index = 0
        mint_url = ""
        sufficent_budget = False

        # Some logic.
        # First look if we have balance on a mint the user has in their list of trusted mints and use it
        for mint in nut_wallet.nutmints:
            if mint.available_balance() >= amount and mint.mint_url in mints:
                mint_url = mint.mint_url
                sufficent_budget = True
                break
        # If that's not the case, lets look or mints we both trust, take the first one.
        if not sufficent_budget:
            mint_url = next(i for i in nut_wallet.mints if i in mints)
            mint = self.get_mint(nut_wallet, mint_url)
            if mint.available_balance() < amount:
                await self.handle_low_balance_on_mint(nut_wallet, mint_url, mint, amount, client, keys)


            # If that's not the case, iterate over the recipents mints and try to mint there. This might be a bit dangerous as not all mints might give cashu, so loss of ln is possible
            if mint_url is None:
                if nut_wallet.trust_unknown_mints:
                    # maybe we don't do this for now..
                    while not mint_success:
                        try:
                            mint_url = mints[index]  #
                            # Maybe we introduce a list of known failing mints..
                            if mint_url == "https://stablenut.umint.cash":
                                raise Exception("stablemint bad")
                            mint = self.get_mint(nut_wallet, mint_url)
                            if mint.available_balance() < amount:
                                await self.handle_low_balance_on_mint(nut_wallet, mint_url, mint, amount, client, keys)
                            mint_success = True
                        except:
                            mint_success = False
                            index += 1
                else:
                    print("No trusted mints founds, enable trust_unknown_mints if you still want to proceed...")
                    return

        tags = [Tag.parse(["amount", str(amount)]),
                Tag.parse(["unit", unit]),
                Tag.parse(["u", mint_url]),
                Tag.parse(["p", zapped_user])]

        if zapped_event != "" and zapped_event is not None:
            tags.append(Tag.parse(["e", zapped_event]))

        mint = self.get_mint(nut_wallet, mint_url)

        cashu_wallet = await Wallet.with_db(
            url=mint_url,
            db="db/Cashu",
            name="wallet_mint_api",
        )

        await cashu_wallet.load_mint()
        secret_lock = await cashu_wallet.create_p2pk_lock("02" + p2pk_pubkey)  # sender side

        try:
            proofs, fees = await cashu_wallet.select_to_send(mint.proofs, amount)
            print(fees)
            keep_proofs, send_proofs = await cashu_wallet.swap_to_send(
                proofs, amount, secret_lock=secret_lock, set_reserved=True
            )

            print(keep_proofs)

            for proof in send_proofs:
                nut_proof = {
                    'id': proof.id,
                    'C': proof.C,
                    'amount': proof.amount,
                    'secret': proof.secret,
                }
                tags.append(Tag.parse(["proof", json.dumps(nut_proof)]))

            event = EventBuilder(Kind(9321), comment, tags).to_event(keys)
            response = await client.send_event(event)

            await self.update_spend_mint_proof_event(nut_wallet, proofs, mint_url, "zapped", keys.public_key().to_hex(),
                                                     response.id.to_hex(), client, keys)

            print(bcolors.YELLOW + "[" + nut_wallet.name + "] Sent NutZap 🥜️⚡ with " + str(
                amount) + " " + nut_wallet.unit + " to "
                  + PublicKey.parse(zapped_user).to_bech32() +
                  "(" + response.id.to_hex() + ")" + bcolors.ENDC)

        except Exception as e:
            print(e)

    def print_transaction_history(self, transactions, keys):
        for transaction in transactions:
            try:
                content = nip44_decrypt(keys.secret_key(), keys.public_key(), transaction.content())
            except:
                content = nip04_decrypt(keys.secret_key(), keys.public_key(), transaction.content())

            innertags = json.loads(content)
            direction = ""
            amount = ""
            unit = "sats"
            for tag in innertags:
                if tag[0] == "direction":
                    direction = tag[1]
                elif tag[0] == "amount":
                    amount = tag[1]
                    unit = tag[2]
                    if amount == "1" and unit == "sats":
                        unit = "sat"
            sender = ""
            event = ""
            for tag in transaction.tags():
                if tag.as_vec()[0] == "p":
                    sender = tag.as_vec()[1]
                elif tag.as_vec()[0] == "e":
                    event = tag.as_vec()[1]
                    # marker = tag.as_vec()[2]

            if direction == "in":
                color = bcolors.GREEN
                action = "minted"
                dir = "from"
            else:
                color = bcolors.RED
                action = "spent"
                dir = "to"

            if sender != "" and event != "":
                print(
                    color + f"{direction:3}" + " " + f"{amount:6}" + " " + unit + " at " + transaction.created_at().to_human_datetime().replace(
                        "T", " ").replace("Z",
                                          " ") + "GMT" + bcolors.ENDC + " " + bcolors.YELLOW + " (Nutzap 🥜⚡️ " + dir + ": " + PublicKey.parse(
                        sender).to_bech32() + "(" + event + "))" + bcolors.ENDC)
            else:
                print(
                    color + f"{direction:3}" + " " + f"{amount:6}" + " " + unit + " at " + transaction.created_at().to_human_datetime().replace(
                        "T", " ").replace("Z", " ") + "GMT" + " " + " (" + action + ")" + bcolors.ENDC)

    async def reedeem_nutzap(self, event, nut_wallet: NutWallet, client: Client, keys: Keys):
        from cashu.wallet.wallet import Wallet
        from cashu.core.base import Proof
        from cashu.core.crypto.keys import PrivateKey

        proofs = []
        mint_url = ""
        amount = 0
        unit = "sat"
        zapped_user = ""
        zapped_event = ""
        sender = event.author().to_hex()
        message = event.content()
        for tag in event.tags():
            if tag.as_vec()[0] == "proof":
                proof_json = json.loads(tag.as_vec()[1])
                proof = Proof().from_dict(proof_json)
                proofs.append(proof)
            elif tag.as_vec()[0] == "u":
                mint_url = tag.as_vec()[1]
            elif tag.as_vec()[0] == "amount":
                amount = int(tag.as_vec()[1])
            elif tag.as_vec()[0] == "unit":
                unit = tag.as_vec()[1]
            elif tag.as_vec()[0] == "p":
                zapped_user = tag.as_vec()[1]
            elif tag.as_vec()[0] == "e":
                zapped_event = tag.as_vec()[1]

        cashu_wallet = await Wallet.with_db(
            url=mint_url,
            db="db/Receiver",
            name="receiver",
        )
        cashu_wallet.private_key = PrivateKey(bytes.fromhex(nut_wallet.privkey), raw=True)
        await cashu_wallet.load_mint()
        try:
            new_proofs, _ = await cashu_wallet.redeem(proofs)
            mint = self.get_mint(nut_wallet, mint_url)
            print(mint.proofs)
            print(new_proofs)
            count_amount = 0
            for proof in new_proofs:
                count_amount += proof.amount
            await self.add_proofs_to_wallet(nut_wallet, mint_url, new_proofs, "redeemed", event.author().to_hex(),
                                            event.id().to_hex(), client, keys)

            return count_amount, message, sender
        except Exception as e:
            print(bcolors.RED + str(e) + bcolors.ENDC)
            return None, message, sender


    async def melt_cashu(self, nut_wallet, mint_url, total_amount, client, keys, lud16=None, npub=None):
        from cashu.wallet.wallet import Wallet
        mint = self.get_mint(nut_wallet, mint_url)

        cashu_wallet = await Wallet.with_db(
            url=mint_url,
            db="db/Cashu",
            name="wallet_mint_api",
        )
        await cashu_wallet.load_mint()
        cashu_wallet.proofs = mint.proofs

        estimated_fees = max(int(total_amount * 0.02), 3)
        estimated_redeem_invoice_amount = total_amount - estimated_fees

        if npub is None:
            # if we don't pass the npub, we default to our pubkey
            npub = Keys.parse(check_and_set_private_key("TEST_ACCOUNT_PK")).public_key().to_hex()

        if lud16 is None:
            # if we don't pass a lud16, we try to fetch one from our profile (make sure it's set)
            name, nip05, lud16 = await fetch_user_metadata(npub, client)

        invoice = zaprequest(lud16, estimated_redeem_invoice_amount, "Melting from your nutsack", None,
                             PublicKey.parse(npub), keys, DVMConfig().RELAY_LIST, zaptype="private")
        # else:
        #    invoice = create_bolt11_lud16(lud16, estimated_redeem_invoice_amount)
        quote = await cashu_wallet.melt_quote(invoice)

        send_proofs, _ = await cashu_wallet.select_to_send(cashu_wallet.proofs, total_amount)
        await cashu_wallet.melt(send_proofs, invoice, estimated_fees, quote.quote)
        await self.update_spend_mint_proof_event(nut_wallet, send_proofs, mint_url, "", None,
                                                 None, client, keys)

        print(bcolors.YELLOW + "[" + nut_wallet.name + "] Redeemed on Lightning ⚡ " + str(
            total_amount - estimated_fees) + " (Fees: " + str(estimated_fees) + ") " + nut_wallet.unit
              + bcolors.ENDC)

    async def swap(self, amountinsats, outgoing_mint_url, incoming_mint_url):
        from cashu.wallet.cli.cli_helpers import print_mint_balances
        from cashu.wallet.wallet import Wallet
        # print("Select the mint to swap from:")
        # outgoing_wallet = await get_mint_wallet(ctx, force_select=True)

        outgoing_wallet = await Wallet.with_db(
            url=outgoing_mint_url,
            db="db/Sender",
            name="sender",
        )

        print("Select the mint to swap to:")
        # incoming_wallet = await get_mint_wallet(ctx, force_select=True)

        incoming_wallet = await Wallet.with_db(
            url=incoming_mint_url,
            db="db/Receiver",
            name="reeciver",
        )

        await incoming_wallet.load_mint()
        await outgoing_wallet.load_mint()

        if incoming_wallet.url == outgoing_wallet.url:
            raise Exception("mints for swap have to be different")

        print("Incoming Mint units: " + incoming_wallet.unit.name)

        assert amountinsats > 0, "amount is not positive"

        # request invoice from incoming mint
        invoice = await incoming_wallet.request_mint(amountinsats)

        # pay invoice from outgoing mint
        quote = await outgoing_wallet.melt_quote(invoice.bolt11)
        total_amount = quote.amount + quote.fee_reserve
        if outgoing_wallet.available_balance < total_amount:
            raise Exception("balance too low")
        send_proofs, fees = await outgoing_wallet.select_to_send(
            outgoing_wallet.proofs, total_amount, set_reserved=True
        )
        await outgoing_wallet.melt(
            send_proofs, invoice.bolt11, quote.fee_reserve, quote.quote
        )

        # mint token in incoming mint
        await incoming_wallet.mint(amountinsats, id=invoice.id)

        await incoming_wallet.load_proofs(reload=True)
        await print_mint_balances(incoming_wallet, show_mints=True)

    async def set_profile(self, name, about, lud16, image, client, keys):
        metadata = Metadata() \
            .set_name(name) \
            .set_display_name(name) \
            .set_about(about) \
            .set_picture(image) \
            .set_lud16(lud16) \
            .set_nip05("")
        print("[" + name + "] Setting profile metadata for " + keys.public_key().to_bech32() + "...")
        print(metadata.as_json())
        await client.set_metadata(metadata)
