import json
import os
import time
import datetime as datetime
from pathlib import Path
from threading import Thread

import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, Timestamp, nip04_decrypt, \
    nip04_encrypt

from utils.dvmconfig import DVMConfig
from utils.nostr_utils import send_event
from utils.definitions import EventDefinitions


# TODO HINT: Best use this path with a previously whitelisted privkey, as zapping events is not implemented in the lib/code
def nostr_client_test_translation(input, kind, lang, sats, satsmax):
    keys = Keys.from_sk_str(os.getenv("NOSTR_TEST_CLIENT_PRIVATE_KEY"))
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
    config = DVMConfig
    send_event(event, client=client, dvm_config=config)
    return event.as_json()


def nostr_client_test_image(prompt):
    keys = Keys.from_sk_str(os.getenv("NOSTR_TEST_CLIENT_PRIVATE_KEY"))

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
    config = DVMConfig
    send_event(event, client=client, dvm_config=config)
    return event.as_json()


def nostr_client_test_image_private(prompt, cashutoken):
    keys = Keys.from_sk_str(os.getenv("NOSTR_TEST_CLIENT_PRIVATE_KEY"))
    receiver_keys = Keys.from_sk_str(os.getenv("NOSTR_PRIVATE_KEY"))


    # TODO more advanced logic, more parsing, params etc, just very basic test functions for now

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]
    i_tag = Tag.parse(["i", prompt, "text"])
    outTag = Tag.parse(["output", "image/png;format=url"])
    paramTag1 = Tag.parse(["param", "size", "1024x1024"])
    tTag = Tag.parse(["t", "bitcoin"])

    bid = str(50 * 1000)
    bid_tag = Tag.parse(['bid', bid, bid])
    relays_tag = Tag.parse(["relays", json.dumps(relay_list)])
    alt_tag = Tag.parse(["alt", "Super secret test"])
    cashu_tag = Tag.parse(["cashu", cashutoken])

    encrypted_params_string = json.dumps([i_tag.as_vec(), outTag.as_vec(), paramTag1.as_vec(), tTag, bid_tag.as_vec(),
                                          relays_tag.as_vec(), alt_tag.as_vec(), cashu_tag.as_vec()])


    encrypted_params = nip04_encrypt(keys.secret_key(), receiver_keys.public_key(),
                                     encrypted_params_string)

    p_tag = Tag.parse(['p', keys.public_key().to_hex()])
    encrypted_tag = Tag.parse(['encrypted'])
    nip90request = EventBuilder(EventDefinitions.KIND_NIP90_GENERATE_IMAGE, encrypted_params,
                                [p_tag, encrypted_tag]).to_event(keys)
    client = Client(keys)
    for relay in relay_list:
        client.add_relay(relay)
    client.connect()
    config = DVMConfig
    send_event(nip90request, client=client, dvm_config=config)
    return nip90request.as_json()

def nostr_client():
    keys = Keys.from_sk_str(os.getenv("NOSTR_TEST_CLIENT_PRIVATE_KEY"))
    sk = keys.secret_key()
    pk = keys.public_key()
    print(f"Nostr Client public key: {pk.to_bech32()}, Hex: {pk.to_hex()} ")
    client = Client(keys)
    dvmconfig = DVMConfig()
    for relay in dvmconfig.RELAY_LIST:
        client.add_relay(relay)
    client.connect()

    dm_zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM,
                                               EventDefinitions.KIND_ZAP]).since(
        Timestamp.now())  # events to us specific
    dvm_filter = (Filter().kinds([EventDefinitions.KIND_NIP90_RESULT_TRANSLATE_TEXT,
                                  EventDefinitions.KIND_FEEDBACK]).since(Timestamp.now()))  # public events
    client.subscribe([dm_zap_filter, dvm_filter])

    #nostr_client_test_translation("This is the result of the DVM in spanish", "text", "es", 20, 20)
    #nostr_client_test_translation("note1p8cx2dz5ss5gnk7c59zjydcncx6a754c0hsyakjvnw8xwlm5hymsnc23rs", "event", "es", 20,20)
    #nostr_client_test_translation("44a0a8b395ade39d46b9d20038b3f0c8a11168e67c442e3ece95e4a1703e2beb", "event", "zh", 20, 20)

    nostr_client_test_image("a beautiful purple ostrich watching the sunset")

   # cashutoken = "cashuAeyJ0b2tlbiI6W3sicHJvb2ZzIjpbeyJpZCI6IlhXQzAvRXRhcVM4QyIsImFtb3VudCI6NCwiQyI6IjAzNzZhYTQ4YTJiMDU1NTlmYzQ4MTU2NjJjZThhMjZmZGM5OTQzYzY2Yzg0OWEzNTg3NDgwYWRmYzE0ZTEwNTRiZCIsInNlY3JldCI6IlIzTGhSZDI5UktJTzRkMHdNZ0Z0K2ZKWlVoYi90K0RmZXMxdFVrZVBVV0E9In0seyJpZCI6IlhXQzAvRXRhcVM4QyIsImFtb3VudCI6MTYsIkMiOiIwMmYyNTdhYzYzOTU4NGY1YTE5NTNkMGI0ODI3OWJkN2EyMjdmZTBkYzI0OWY0MjQwNjgzMDZlOTI0ZGE3ZGVhZDciLCJzZWNyZXQiOiJ4Tmhwdm50SkNwcXFiYmFjWDA0NzluVld4SGo5U05jaVBvdTNYQ3JWcmRjPSJ9LHsiaWQiOiJYV0MwL0V0YXFTOEMiLCJhbW91bnQiOjMyLCJDIjoiMDIyYjhiY2JkYTQ1OTNlMGZlNTY4ZWYyOTM2OWNmZjNmMzY2NzdlZDAzYTQ4ODMxNzYwNDQxN2JkNGE3MTYzZDYyIiwic2VjcmV0IjoiTEprUVlheWNyUE9yZ3hZcHhlcDZVV3U0RjZ3QUVydnZJNHZiRmN0R3h6MD0ifV0sIm1pbnQiOiJodHRwczovL2xuYml0cy5iaXRjb2luZml4ZXN0aGlzLm9yZy9jYXNodS9hcGkvdjEvOXVDcDIyUllWVXE4WjI0bzVCMlZ2VyJ9XX0"
   #nostr_client_test_image_private("a beautiful ostrich watching the sunset", cashutoken )
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
