import asyncio
import json
import time
from pathlib import Path
from threading import Thread

import dotenv
from nostr_sdk import (
    ClientBuilder, Event, EventBuilder, Filter, Keys, RelayUrl, ReqTarget, SignerAuthenticator, Tag,
    Timestamp, nip04_decrypt,
)

from nostr_dvm.utils.sdk_utils import handle_notifications

from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key
from nostr_dvm.utils.definitions import EventDefinitions


async def nostr_client_test_tts(prompt):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    iTag = Tag.parse(["i", prompt, "text"])
    paramTag1 = Tag.parse(["param", "language", "en"])


    bidTag = Tag.parse(['bid', str(1000 * 1000), str(1000 * 1000)])
    relaysTag = Tag.parse(['relays', "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to generate TTS"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_TEXT_TO_SPEECH, str("Generate an Audio File.")).tags(
                         [iTag, paramTag1, bidTag, relaysTag, alttag]).finalize(keys)

    relay_list = ["wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]


    client = ClientBuilder().authenticator(SignerAuthenticator(keys)).build()
    for relay in relay_list:
        await client.add_relay(RelayUrl.parse(relay))
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()

async def nostr_client():
    keys = Keys.parse(check_and_set_private_key("test_client"))
    sk = keys.secret_key()
    pk = keys.public_key()
    print(f"Nostr Test Client public key: {pk.to_bech32()}, Hex: {pk.to_hex()} ")
    client = ClientBuilder().authenticator(SignerAuthenticator(keys)).build()

    dvmconfig = DVMConfig()
    for relay in dvmconfig.RELAY_LIST:
        await client.add_relay(RelayUrl.parse(relay))
    await client.connect()

    dm_zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM,
                                               EventDefinitions.KIND_ZAP]).since(
        Timestamp.now())  # events to us specific
    dvm_filter = (Filter().kinds([EventDefinitions.KIND_NIP90_RESULT_TEXT_TO_SPEECH,
                                  EventDefinitions.KIND_FEEDBACK]).since(Timestamp.now()))  # public events
    await client.subscribe(ReqTarget.auto([dm_zap_filter]))
    await client.subscribe(ReqTarget.auto([dvm_filter]))


    await nostr_client_test_tts("Hello, this is a test. Mic check one, two.")
    print("Sending Job Request")


    #nostr_client_test_image_private("a beautiful ostrich watching the sunset")
    class NotificationHandler:
        async def handle(self, relay_url, subscription_id, event: Event):
            print(f"Received new event from {relay_url}: {event.as_json()}")
            if event.kind() == 7000:
                print("[Nostr Client]: " + event.as_json())
            elif 6000 < event.kind().as_u16() < 6999:
                print("[Nostr Client]: " + event.as_json())
                print("[Nostr Client]: " + event.content())

            elif event.kind() == 4:
                dec_text = nip04_decrypt(sk, event.author(), event.content())
                print("[Nostr Client]: " + f"Received new msg: {dec_text}")

            elif event.kind() == 9735:
                print("[Nostr Client]: " + f"Received new zap:")
                print(event.as_json())

        async def handle_msg(self, relay_url, msg):
            return

    asyncio.create_task(handle_notifications(client, NotificationHandler()))
    while True:
        await asyncio.sleep(5.0)


if __name__ == '__main__':

    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    asyncio.run(nostr_client())
