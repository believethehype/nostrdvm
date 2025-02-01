# Welcome to part 3. This actually is is a simplistic client that will interact with our DVM.
# We will address the DVM we created in part 02, so make sure it's still running and run this Script in a new instance.
# Copy the DVM's hex key that pops up at the beginning and replace the one down in the main function with your DVM's key.
# This way we will tag it and it will know it should reply to us.

import asyncio
from pathlib import Path
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.print_utils import bcolors

import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, Timestamp, nip04_decrypt, \
    NostrSigner, Event, Kind, PublicKey
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key, print_send_result
from nostr_dvm.utils.definitions import EventDefinitions



async def nostr_client_generic_test(ptag):
    # Create or manage some private keys for our client.
    keys = Keys.parse(check_and_set_private_key("test_client"))

    # We tell the DVM to which relays it should reply
    relay_list = ["wss://nostr.oxtr.dev", "wss://relay.primal.net"]
    relaysTag = Tag.parse(["relays"] + relay_list)
    # The alt tag is optional, and just describes what the event does.
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task"])

    #We know our DVM has an option some_option. We can also overwrite it by setting the parameter.
    paramTag = Tag.parse(["param", "some_option", "#RUNDVM - The client puts the option."])
    # The ptag tags the DVM we want to address. Make sure to set it down in the main function.
    pTag = Tag.parse(["p", PublicKey.parse(ptag).to_hex()])

    # These are out tags
    tags = [relaysTag, alttag, pTag, paramTag]

    # We now send a 5050 Request (for Text Generation) with our tags. The content is optional.
    event = EventBuilder(Kind(5050), "This is a test",
                         ).tags(tags).sign_with_keys(keys)

    # We create a signer with some random keys
    client = Client(NostrSigner.keys(keys))
    # We add the relays we defined above and told our DVM we would want to receive events to.
    for relay in relay_list:
        await client.add_relay(relay)
    # We connect the client
    await client.connect()
    # and send the Event.
    response_status = await send_event(event, client=client, dvm_config=DVMConfig())
    print_send_result(response_status)


async def nostr_client(target_dvm_npub):

    # This is some logic for listening to events. For example we want to see replies from the DVM.
    keys = Keys.parse(check_and_set_private_key("test_client"))
    sk = keys.secret_key()
    pk = keys.public_key()
    print(f"Nostr Client public key: {pk.to_bech32()}, Hex: {pk.to_hex()} ")
    client = Client(NostrSigner.keys(keys))

    dvmconfig = DVMConfig()
    for relay in dvmconfig.RELAY_LIST:
        await client.add_relay(relay)
    await client.connect()

    dm_zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM,
                                               EventDefinitions.KIND_ZAP]).since(Timestamp.now())
    kinds = [EventDefinitions.KIND_NIP90_GENERIC]
    for kind in range(6000, 7001):
        if kind not in kinds:
            kinds.append(Kind(kind))

    dvm_filter = (Filter().kinds(kinds).since(Timestamp.now()).pubkey(pk))
    await client.subscribe(dm_zap_filter, None)
    await client.subscribe(dvm_filter, None)




    # This will send a request to the DVM
    await nostr_client_generic_test(target_dvm_npub)

    # We listen to
    class NotificationHandler(HandleNotification):
        last_event_time = 0
        async def handle(self, relay_url, subscription_id, event: Event):

            print(
                bcolors.BLUE + f"Received new event from {relay_url}: {event.as_json()}" + bcolors.ENDC)
            if event.kind().as_u16() == 7000:
                print(bcolors.YELLOW + "[Nostr Client]: " + event.content() + bcolors.ENDC)
                amount_sats = 0
                status = ""
                for tag in event.tags().to_vec():
                    if tag.as_vec()[0] == "amount":
                        amount_sats = int(int(tag.as_vec()[1]) / 1000) # millisats
                    if tag.as_vec()[0] == "status":
                       status = tag.as_vec()[1]

            elif 6000 < event.kind().as_u16() < 6999:
                print(bcolors.GREEN + "[Nostr Client]: " +  event.content() + bcolors.ENDC)

            elif event.kind().as_u16() == 4:
                dec_text = nip04_decrypt(sk, event.author(), event.content() )
                print("[Nostr Client]: " + f"Received new msg: {dec_text}")

            elif event.kind().as_u16() == 9735:
                print("[Nostr Client]: " + f"Received new zap:")
                print(event.as_json())

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

    # Replace this key with the one from your DVM from part 3.
    target_dvm_npub = "aaf3b2bda1f19651417af4b1ccc35ebb6675d718843fdc444bdca4da1c8cd2fc"
    asyncio.run(nostr_client(target_dvm_npub))
