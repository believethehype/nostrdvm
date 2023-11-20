import os
import time
import datetime as datetime
from pathlib import Path
from threading import Thread

import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, Timestamp, nip04_decrypt

from utils.nostr_utils import send_event
from utils.definitions import EventDefinitions, RELAY_LIST

import utils.env as env


# TODO HINT: Best use this path with a previously whitelisted privkey, as zapping events is not implemented in the lib/code
def nostr_client_test_translation(input, kind, lang, sats, satsmax):
    keys = Keys.from_sk_str(os.getenv(env.NOSTR_TEST_CLIENT_PRIVATE_KEY))
    if kind == "text":
        iTag = Tag.parse(["i", input, "text"])
    elif kind == "event":
        iTag = Tag.parse(["i", input, "event"])
    paramTag1 = Tag.parse(["param", "language", lang])

    bidTag = Tag.parse(['bid', str(sats * 1000), str(satsmax * 1000)])
    relaysTag = Tag.parse(['relays', "wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to translate a given Input"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_TRANSLATE_TEXT, str("Translate the given input."),
                         [iTag, paramTag1, bidTag, relaysTag, alttag]).to_event(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]

    client = Client(keys)
    for relay in relay_list:
        client.add_relay(relay)
    client.connect()
    send_event(event, client, keys)
    return event.as_json()


def nostr_client_test_image(prompt):
    keys = Keys.from_sk_str(os.getenv(env.NOSTR_TEST_CLIENT_PRIVATE_KEY))

    iTag = Tag.parse(["i", prompt, "text"])
    outTag = Tag.parse(["output", "image/png;format=url"])
    paramTag1 = Tag.parse(["param", "size", "1024x1024"])
    tTag = Tag.parse(["t", "bitcoin"])

    bidTag = Tag.parse(['bid', str(1000 * 1000), str(1000 * 1000)])
    relaysTag = Tag.parse(['relays', "wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to translate a given Input"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_GENERATE_IMAGE, str("Generate an Image."),
                         [iTag, outTag, tTag, paramTag1, bidTag, relaysTag, alttag]).to_event(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]

    client = Client(keys)
    for relay in relay_list:
        client.add_relay(relay)
    client.connect()
    send_event(event, client, keys)
    return event.as_json()

def nostr_client():
    keys = Keys.from_sk_str(os.getenv(env.NOSTR_TEST_CLIENT_PRIVATE_KEY))
    sk = keys.secret_key()
    pk = keys.public_key()
    print(f"Nostr Client public key: {pk.to_bech32()}, Hex: {pk.to_hex()} ")
    client = Client(keys)
    for relay in RELAY_LIST:
        client.add_relay(relay)
    client.connect()

    dm_zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM,
                                               EventDefinitions.KIND_ZAP]).since(
        Timestamp.now())  # events to us specific
    dvm_filter = (Filter().kinds([EventDefinitions.KIND_NIP90_RESULT_TRANSLATE_TEXT,
                                  EventDefinitions.KIND_FEEDBACK]).since(Timestamp.now()))  # public events
    client.subscribe([dm_zap_filter, dvm_filter])

    # nostr_client_test_translation("This is the result of the DVM in spanish", "text", "es", 20, 20)
    #nostr_client_test_translation("44a0a8b395ade39d46b9d20038b3f0c8a11168e67c442e3ece95e4a1703e2beb", "event", "es", 20,
    #                              20)

    # nostr_client_test_translation("9c5d6d054e1b7a34a6a4b26ac59469c96e77f7cba003a30456fa6a57974ea86d", "event", "zh", 20, 20)

    nostr_client_test_image("a beautiful purple ostrich watching the sunset")
    class NotificationHandler(HandleNotification):
        def handle(self, relay_url, event):
            print(f"Received new event from {relay_url}: {event.as_json()}")
            if event.kind() == 7000:
                print("[Nostr Client]: " + event.as_json())
            elif event.kind() > 6000 and event.kind() < 6999:
                print("[Nostr Client]: " + event.as_json())
                print("[Nostr Client]: " + event.content())

            elif event.kind() == 4:
                dec_text = nip04_decrypt(sk, event.pubkey(), event.content())
                print("[Nostr Client]: " + f"Received new msg: {dec_text}")

            elif event.kind() == 9735:
                print("[Nostr Client]: " + f"Received new zap:")
                print(event.as_json())

        def handle_msg(self, relay_url, msg):
            return

    client.handle_notifications(NotificationHandler())
    while True:
        time.sleep(5.0)


if __name__ == '__main__':

    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    nostr_dvm_thread = Thread(target=nostr_client())
    nostr_dvm_thread.start()
