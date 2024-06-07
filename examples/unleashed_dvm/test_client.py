import asyncio
import json
import time
from datetime import timedelta
from pathlib import Path
from threading import Thread

import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, Timestamp, nip04_decrypt, \
    NostrSigner, Options, Event

from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key
from nostr_dvm.utils.definitions import EventDefinitions


async def nostr_client_test(prompt):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    iTag = Tag.parse(["i", prompt, "text"])


    relaysTag = Tag.parse(['relays', "wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to generate TTS"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_GENERATE_TEXT, str("Answer to prompt"),
                         [iTag, relaysTag, alttag]).to_event(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]

    opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=5)))
    signer = NostrSigner.keys(keys)
    client = Client.with_opts(signer,opts)
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()

async def nostr_client():
    keys = Keys.parse(check_and_set_private_key("test_client"))
    sk = keys.secret_key()
    pk = keys.public_key()
    print(f"Nostr Test Client public key: {pk.to_bech32()}, Hex: {pk.to_hex()} ")
    signer = NostrSigner.keys(keys)
    client = Client(signer)

    dvmconfig = DVMConfig()
    for relay in dvmconfig.RELAY_LIST:
        await client.add_relay(relay)
    await client.connect()

    dm_zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM,
                                               EventDefinitions.KIND_ZAP]).since(
        Timestamp.now())  # events to us specific
    dvm_filter = (Filter().kinds([EventDefinitions.KIND_NIP90_RESULT_GENERATE_TEXT,
                                  EventDefinitions.KIND_FEEDBACK]).since(Timestamp.now()))  # public events
    await client.subscribe([dm_zap_filter, dvm_filter])


    #nostr_client_test("What has Pablo been up to?")
    await nostr_client_test("What is Gigi talking about recently?")
    print("Sending Job Request")


    class NotificationHandler(HandleNotification):
        def handle(self, relay_url, subscription_id, event: Event):
            print(f"Received new event from {relay_url}: {event.as_json()}")
            if event.kind() == 7000:
                print("[Nostr Client]: " + event.as_json())
            elif 6000 < event.kind().as_u64() < 6999:
                print("[Nostr Client " +  event.author().to_bech32() + "]: " + event.as_json())
                print("[Nostr Client " + event.author().to_bech32() + "]: " + event.content())


            elif event.kind() == 4:
                dec_text = nip04_decrypt(sk, event.author(), event.content())
                print("[Nostr Client]: " + f"Received new msg: {dec_text}")

            elif event.kind() == 9735:
                print("[Nostr Client]: " + f"Received new zap:")
                print(event.as_json())

        def handle_msg(self, relay_url, msg):
            return

    asyncio.create_task(client.handle_notifications(NotificationHandler()))

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':

    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    asyncio.run(nostr_client())