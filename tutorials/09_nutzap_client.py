
# This is the complementary tutorial for tutorial 08. Sending nutzaps.
# Make sure tutorial 08 is running while testing this. Also make sure you lnbits config is set,
# or manually change the code to access a wallet to mint tokens.
# Check especially the code in line 76 and make sure to replace the npub with the one from
# the dvm in tutorial 8 in line 120.

from pathlib import Path

import dotenv
from nostr_sdk import PublicKey, Client, NostrSigner, EventBuilder, Kind, Tag, Keys, Timestamp, HandleNotification, \
    Filter, Event

import asyncio
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key, print_send_result
from nostr_dvm.utils.nut_wallet_utils import NutZapWallet
from nostr_dvm.utils.print_utils import bcolors


# You already know this from our previous test client in tutorial 03: We simply send a kind 5050 request
# to return some text, just as before. Note: Our dvm in tutorial 08 requires a payment of 3 sats.
async def nostr_client_generic_test(ptag):
    keys = Keys.parse(check_and_set_private_key("test_client"))
    relay_list = ["wss://nostr.oxtr.dev", "wss://relay.primal.net"]
    relaysTag = Tag.parse(["relays"] + relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task"])
    paramTag = Tag.parse(["param", "some_option", "#RUNDVM - With a Nutzap."])
    pTag = Tag.parse(["p", PublicKey.parse(ptag).to_hex()])
    tags = [relaysTag, alttag, pTag, paramTag]
    event = EventBuilder(Kind(5050), "This is a test",
                         ).tags(tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    response_status = await send_event(event, client=client, dvm_config=DVMConfig())
    print_send_result(response_status)


async def nostr_client(target_dvm_npub):

    keys = Keys.parse(check_and_set_private_key("test_client"))
    pk = keys.public_key()
    print(f"Nostr Client public key: {pk.to_bech32()}, Hex: {pk.to_hex()} ")
    client = Client(NostrSigner.keys(keys))

    dvmconfig = DVMConfig()
    for relay in dvmconfig.RELAY_LIST:
        await client.add_relay(relay)
    await client.connect()

    kinds = [EventDefinitions.KIND_NIP90_GENERIC]
    for kind in range(6000, 7001):
        if kind not in kinds:
            kinds.append(Kind(kind))

    dvm_filter = (Filter().kinds(kinds).since(Timestamp.now()).pubkey(pk))
    await client.subscribe(dvm_filter, None)

    # This will send a request to the DVM
    await nostr_client_generic_test(target_dvm_npub)

    # We listen to
    class NotificationHandler(HandleNotification):
        last_event_time = 0
        async def handle(self, relay_url, subscription_id, event: Event):
            if event.kind().as_u16() == 7000:
                print(bcolors.YELLOW + "[Nostr Client]: " + event.content() + bcolors.ENDC)
                amount_sats = 0
                status = ""
                for tag in event.tags().to_vec():
                    if tag.as_vec()[0] == "amount":
                        amount_sats = int(int(tag.as_vec()[1]) / 1000) # millisats
                    if tag.as_vec()[0] == "status":
                       status = tag.as_vec()[1]

                if status == "payment-required":
                    print("do a nutzap of " + str(amount_sats) +" sats here")

                    send_zap_amount = amount_sats
                    send_zap_message = "From my nutsack"
                    send_receiver = event.author().to_hex()
                    send_zapped_event = event.id().to_hex() # None  # None, or zap an event like this: Nip19Event.from_nostr_uri("nostr:nevent1qqsxq59mhz8s6aj9jzltcmqmmv3eutsfcpkeny2x755vdu5dtq44ldqpz3mhxw309ucnydewxqhrqt338g6rsd3e9upzp75cf0tahv5z7plpdeaws7ex52nmnwgtwfr2g3m37r844evqrr6jqvzqqqqqqyqtxyr6").event_id().to_hex()
                    zapped_event_id_hex = send_zapped_event
                    nutzap_wallet = NutZapWallet()
                    nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)

                    if nut_wallet is None:
                        relays = DVMConfig().NUTZAP_RELAYS
                        mints = DVMConfig().NUZAP_MINTS
                        await nutzap_wallet.create_new_nut_wallet(mints, relays, client, keys, "Test", "My Nutsack")
                        nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)
                        if nut_wallet is not None:
                            await nutzap_wallet.announce_nutzap_info_event(nut_wallet, client, keys)
                        else:
                            print("Couldn't fetch wallet, please restart and see if it is there")

                    await nutzap_wallet.send_nut_zap(send_zap_amount, send_zap_message, nut_wallet, zapped_event_id_hex, send_receiver, client,
                                       keys)

            elif 6000 < event.kind().as_u16() < 6999:
                print(bcolors.GREEN + "[Nostr Client]: " +  event.content() + bcolors.ENDC)


        async def handle_msg(self, relay_url, msg):
            return

    asyncio.create_task(client.handle_notifications(NotificationHandler()))
    # await client.handle_notifications(NotificationHandler())
    while True:
        await asyncio.sleep(2)


if __name__ == '__main__':

    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    # Replace this key with the one from your DVM from part 8.
    target_dvm_npub = "npub150laafgrw4dlj5pc7jk2qzhxkghtqn9pplsyg8u6jkpd9afaszzsu06p39"
    asyncio.run(nostr_client(target_dvm_npub))