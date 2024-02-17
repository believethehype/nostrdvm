import json
import time
from pathlib import Path
from threading import Thread

import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, Timestamp, nip04_decrypt, \
    nip04_encrypt, NostrSigner

from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key
from nostr_dvm.utils.definitions import EventDefinitions


# TODO HINT: Best use this path with a previously whitelisted privkey, as zapping events is not implemented in the lib/code
def nostr_client_test_translation(input, kind, lang, sats, satsmax):
    keys = Keys.parse(check_and_set_private_key("test_client"))
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

    signer = NostrSigner.keys(keys)
    client = Client(signer)

    for relay in relay_list:
        client.add_relay(relay)
    client.connect()
    config = DVMConfig
    send_event(event, client=client, dvm_config=config)
    return event.as_json()
def nostr_client_test_search_profile(input):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    iTag = Tag.parse(["i", input, "text"])



    relaysTag = Tag.parse(['relays', "wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to translate a given Input"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_USER_SEARCH, str("Search for user"),
                         [iTag, relaysTag, alttag]).to_event(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]

    signer = NostrSigner.keys(keys)
    client = Client(signer)

    for relay in relay_list:
        client.add_relay(relay)
    client.connect()
    config = DVMConfig
    send_event(event, client=client, dvm_config=config)
    return event.as_json()

def nostr_client_test_image(prompt):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    iTag = Tag.parse(["i", prompt, "text"])
    outTag = Tag.parse(["output", "image/png;format=url"])
    paramTag1 = Tag.parse(["param", "size", "1024x1024"])
    tTag = Tag.parse(["t", "bitcoin"])

    bidTag = Tag.parse(['bid', str(1000 * 1000), str(1000 * 1000)])
    relaysTag = Tag.parse(['relays', "wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to generate an Image from a given Input"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_GENERATE_IMAGE, str("Generate an Image."),
                         [iTag, outTag, tTag, paramTag1, bidTag, relaysTag, alttag]).to_event(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        client.add_relay(relay)
    client.connect()
    config = DVMConfig
    send_event(event, client=client, dvm_config=config)
    return event.as_json()


def nostr_client_test_tts(prompt):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    iTag = Tag.parse(["i", prompt, "text"])
    paramTag1 = Tag.parse(["param", "language", "en"])

    bidTag = Tag.parse(['bid', str(1000 * 1000), str(1000 * 1000)])
    relaysTag = Tag.parse(['relays', "wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to generate TTSt"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_TEXT_TO_SPEECH, str("Generate an Audio File."),
                         [iTag, paramTag1, bidTag, relaysTag, alttag]).to_event(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        client.add_relay(relay)
    client.connect()
    config = DVMConfig
    send_event(event, client=client, dvm_config=config)
    return event.as_json()


def nostr_client_test_image_private(prompt, cashutoken):
    keys = Keys.parse(check_and_set_private_key("test_client"))
    receiver_keys = Keys.parse(check_and_set_private_key("replicate_sdxl"))

    # TODO more advanced logic, more parsing, params etc, just very basic test functions for now

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]
    i_tag = Tag.parse(["i", prompt, "text"])
    outTag = Tag.parse(["output", "image/png;format=url"])
    paramTag1 = Tag.parse(["param", "size", "1024x1024"])
    pTag = Tag.parse(["p", receiver_keys.public_key().to_hex()])

    bid = str(50 * 1000)
    bid_tag = Tag.parse(['bid', bid, bid])
    relays_tag = Tag.parse(["relays", json.dumps(relay_list)])
    alt_tag = Tag.parse(["alt", "Super secret test"])
    cashu_tag = Tag.parse(["cashu", cashutoken])

    encrypted_params_string = json.dumps([i_tag.as_vec(), outTag.as_vec(), paramTag1.as_vec(), bid_tag.as_vec(),
                                          relays_tag.as_vec(), alt_tag.as_vec(), cashu_tag.as_vec()])

    encrypted_params = nip04_encrypt(keys.secret_key(), receiver_keys.public_key(),
                                     encrypted_params_string)

    encrypted_tag = Tag.parse(['encrypted'])
    nip90request = EventBuilder(EventDefinitions.KIND_NIP90_GENERATE_IMAGE, encrypted_params,
                                [pTag, encrypted_tag]).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        client.add_relay(relay)
    client.connect()
    config = DVMConfig
    send_event(nip90request, client=client, dvm_config=config)
    return nip90request.as_json()


def nostr_client():
    keys = Keys.parse(check_and_set_private_key("test_client"))
    sk = keys.secret_key()
    pk = keys.public_key()
    print(f"Nostr Client public key: {pk.to_bech32()}, Hex: {pk.to_hex()} ")
    signer = NostrSigner.keys(keys)
    client = Client(signer)

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

    # nostr_client_test_translation("This is the result of the DVM in spanish", "text", "es", 20, 20)
    # nostr_client_test_translation("note1p8cx2dz5ss5gnk7c59zjydcncx6a754c0hsyakjvnw8xwlm5hymsnc23rs", "event", "es", 20,20)
    # nostr_client_test_translation("44a0a8b395ade39d46b9d20038b3f0c8a11168e67c442e3ece95e4a1703e2beb", "event", "zh", 20, 20)
    #nostr_client_test_image("a beautiful purple ostrich watching the sunset")
    nostr_client_test_search_profile("dontbelievew")
    # nostr_client_test_tts("Hello, this is a test. Mic check one, two.")

    # cashutoken = "cashuAeyJ0b2tlbiI6W3sicHJvb2ZzIjpbeyJpZCI6InZxc1VRSVorb0sxOSIsImFtb3VudCI6MSwiQyI6IjAyNWU3ODZhOGFkMmExYTg0N2YxMzNiNGRhM2VhMGIyYWRhZGFkOTRiYzA4M2E2NWJjYjFlOTgwYTE1NGIyMDA2NCIsInNlY3JldCI6InQ1WnphMTZKMGY4UElQZ2FKTEg4V3pPck5rUjhESWhGa291LzVzZFd4S0U9In0seyJpZCI6InZxc1VRSVorb0sxOSIsImFtb3VudCI6NCwiQyI6IjAyOTQxNmZmMTY2MzU5ZWY5ZDc3MDc2MGNjZmY0YzliNTMzMzVmZTA2ZGI5YjBiZDg2Njg5Y2ZiZTIzMjVhYWUwYiIsInNlY3JldCI6IlRPNHB5WE43WlZqaFRQbnBkQ1BldWhncm44UHdUdE5WRUNYWk9MTzZtQXM9In0seyJpZCI6InZxc1VRSVorb0sxOSIsImFtb3VudCI6MTYsIkMiOiIwMmRiZTA3ZjgwYmMzNzE0N2YyMDJkNTZiMGI3ZTIzZTdiNWNkYTBhNmI3Yjg3NDExZWYyOGRiZDg2NjAzNzBlMWIiLCJzZWNyZXQiOiJHYUNIdHhzeG9HM3J2WWNCc0N3V0YxbU1NVXczK0dDN1RKRnVwOHg1cURzPSJ9XSwibWludCI6Imh0dHBzOi8vbG5iaXRzLmJpdGNvaW5maXhlc3RoaXMub3JnL2Nhc2h1L2FwaS92MS9ScDlXZGdKZjlxck51a3M1eVQ2SG5rIn1dfQ=="
    # nostr_client_test_image_private("a beautiful ostrich watching the sunset")
    class NotificationHandler(HandleNotification):
        def handle(self, relay_url, event):
            print(f"Received new event from {relay_url}: {event.as_json()}")
            if event.kind() == 7000:
                print("[Nostr Client]: " + event.as_json())
            elif 6000 < event.kind() < 6999:
                print("[Nostr Client]: " + event.as_json())
                print("[Nostr Client]: " + event.content())

            elif event.kind() == 4:
                dec_text = nip04_decrypt(sk, event.author(), event.content())
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
