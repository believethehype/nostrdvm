import asyncio
import json
import time
from pathlib import Path
from threading import Thread

from nostr_dvm.utils.nip65_utils import nip65_announce_relays
from nostr_dvm.utils.nut_wallet_utils import NutZapWallet
from nostr_dvm.utils.print import bcolors

import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, Timestamp, nip04_decrypt, \
    nip04_encrypt, NostrSigner, PublicKey, Event, Kind, RelayOptions

from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key
from nostr_dvm.utils.definitions import EventDefinitions


# TODO HINT: Best use this path with a previously whitelisted privkey, as zapping events is not implemented in the lib/code
async def nostr_client_test_translation(input, kind, lang, sats, satsmax):
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
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()


async def nostr_client_test_search_profile(input):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    iTag = Tag.parse(["i", input, "text"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to translate a given Input"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_USER_SEARCH, str("Search for user"),
                         [iTag, alttag]).to_event(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]

    signer = NostrSigner.keys(keys)
    client = Client(signer)

    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()


async def nostr_client_test_image(prompt):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    iTag = Tag.parse(["i", prompt, "text"])
    outTag = Tag.parse(["output", "image/png;format=url"])
    paramTag1 = Tag.parse(["param", "size", "1024x1024"])

    bidTag = Tag.parse(['bid', str(1000 * 1000), str(1000 * 1000)])
    relaysTag = Tag.parse(['relays', "wss://relay.primal.net", "wss://nostr.oxtr.dev"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to generate an Image from a given Input"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_GENERATE_IMAGE, str("Generate an Image."),
                         [iTag, outTag, paramTag1, bidTag, relaysTag, alttag]).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in DVMConfig().RELAY_LIST:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    #config.NIP89.PK = keys.secret_key().to_hex()
    #await nip65_announce_relays(config, client=client)
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()


async def nostr_client_test_censor_filter(users):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  ]

    relaysTag = Tag.parse(relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to find people to ignore based on people the user trusts"])
    # pTag = Tag.parse(["p", user, "text"])
    tags = [relaysTag, alttag]
    for user in users:
        iTag = Tag.parse(["i", user, "text"])
        tags.append(iTag)

    event = EventBuilder(EventDefinitions.KIND_NIP90_PEOPLE_DISCOVERY, str("Give me bad actors"),
                         tags).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()


async def nostr_client_test_inactive_filter(user):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz",
                  ]

    relaysTag = Tag.parse(relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to find people that are inactive"])
    paramTag = Tag.parse(["param", "user", user])
    paramTag2 = Tag.parse(["param", "since_days", "120"])

    tags = [relaysTag, alttag, paramTag, paramTag2]

    event = EventBuilder(EventDefinitions.KIND_NIP90_PEOPLE_DISCOVERY, str("Give me inactive users"),
                         tags).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        await client.add_relay(relay)
    ropts = RelayOptions().ping(False)
    await client.add_relay_with_opts("wss://nostr.band", ropts)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()


async def nostr_client_test_tts(prompt):
    keys = Keys.parse(check_and_set_private_key("test_client"))
    iTag = Tag.parse(["i", "9d867cd3e868111a31c8acfa41ab7523b9940fc46c804d7db89d7f373c007fa6", "event"])
    # iTag = Tag.parse(["i", prompt, "text"])
    paramTag1 = Tag.parse(["param", "language", "en"])

    bidTag = Tag.parse(['bid', str(1000 * 1000), str(1000 * 1000)])
    relaysTag = Tag.parse(['relays', "wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to generate TTSt"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_TEXT_TO_SPEECH, str("Generate an Audio File."),
                         [iTag, paramTag1, bidTag, relaysTag, alttag]).to_event(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org" "wss://dvms.f7z.io",
                  ]

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()


async def nostr_client_test_discovery(user, ptag):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz",
                  ]

    relaysTag = Tag.parse(relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to find content"])
    paramTag = Tag.parse(["param", "user", user])
    pTag = Tag.parse(["p", ptag])

    tags = [relaysTag, alttag, paramTag, pTag]

    event = EventBuilder(EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY, str("Give me content"),
                         tags).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        await client.add_relay(relay)
    ropts = RelayOptions().ping(False)
    await client.add_relay_with_opts("wss://nostr.band", ropts)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()



async def nostr_client_custom_discovery(user, ptag):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    relay_list = ["wss://nostr.oxtr.dev", "wss://relay.primal.net",
                  ]

    relaysTag = Tag.parse(relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to find content"])
    paramTag = Tag.parse(["param", "user", user])

    search = " art , photograph , photo , photography , painting ,#artstr, drawing "
    avoid = "sex"
    must = "http"

    paramTagSearch = Tag.parse(["param", "search_list", search])
    paramTagAvoid = Tag.parse(["param", "avoid_list", avoid])
    paramTagMust = Tag.parse(["param", "must_list", must])
    pTag = Tag.parse(["p", ptag])

    tags = [relaysTag, alttag, paramTag, pTag, paramTagSearch, paramTagMust, paramTagAvoid]

    event = EventBuilder(EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY, str("Give me content"),
                         tags).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        await client.add_relay(relay)
    ropts = RelayOptions().ping(False)
    await client.add_relay_with_opts("wss://nostr.band", ropts)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()


async def nostr_client_generic_test(ptag):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    relay_list = ["wss://nostr.oxtr.dev", "wss://relay.primal.net",
                  ]

    relaysTag = Tag.parse(relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task"])

    pTag = Tag.parse(["p", ptag])

    tags = [relaysTag, alttag, pTag]

    event = EventBuilder(Kind(5050), str("Give me content"),
                         tags).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        await client.add_relay(relay)
    ropts = RelayOptions().ping(False)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()


async def nostr_client_duckduck_test(ptag, query):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    relay_list = ["wss://nostr.oxtr.dev", "wss://relay.primal.net",
                  ]

    relaysTag = Tag.parse(relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task"])

    pTag = Tag.parse(["p", ptag])
    iTag = Tag.parse(["i", query, "text"])

    tags = [relaysTag, alttag, pTag, iTag]

    event = EventBuilder(Kind(5050), str("Give me content"),
                         tags).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        await client.add_relay(relay)
    ropts = RelayOptions().ping(False)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()




async def nostr_client_test_discovery_user(user, ptag):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    relay_list = ["wss://relay.primal.net", "wss://dvms.f7z.io",
                  ]

    relaysTag = Tag.parse(relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to find users"])
    paramTag = Tag.parse(["param", "user", user])
    pTag = Tag.parse(["p", ptag])

    tags = [relaysTag, alttag, paramTag, pTag]

    event = EventBuilder(EventDefinitions.KIND_NIP90_PEOPLE_DISCOVERY, str("Give me people"),
                         tags).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    eventid = await send_event(event, client=client, dvm_config=config)
    return event.as_json()


async def nostr_client_test_discovery_gallery(user, ptag):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    relay_list = ["wss://relay.damus.io", "wss://dvms.f7z.io",
                  ]

    relaysTag = Tag.parse(relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to find users"])
    paramTag = Tag.parse(["param", "user", user])
    pTag = Tag.parse(["p", ptag])

    tags = [relaysTag, alttag, paramTag, pTag]

    event = EventBuilder(EventDefinitions.KIND_NIP90_VISUAL_DISCOVERY, str("Give me visuals"),
                         tags).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    eventid = await send_event(event, client=client, dvm_config=config)
    print(eventid.to_hex())
    return event.as_json()


async def nostr_client_test_image_private(prompt, cashutoken):
    keys = Keys.parse(check_and_set_private_key("test_client"))
    receiver_keys = Keys.parse(check_and_set_private_key("replicate_sdxl"))

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
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    await send_event(nip90request, client=client, dvm_config=config)
    return nip90request.as_json()


async def nostr_client():
    keys = Keys.parse(check_and_set_private_key("test_client"))
    sk = keys.secret_key()
    pk = keys.public_key()
    print(f"Nostr Client public key: {pk.to_bech32()}, Hex: {pk.to_hex()} ")
    signer = NostrSigner.keys(keys)
    client = Client(signer)

    dvmconfig = DVMConfig()
    for relay in dvmconfig.RELAY_LIST:
        await client.add_relay(relay)
    await client.connect()

    dm_zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM,
                                               EventDefinitions.KIND_ZAP]).since(
        Timestamp.now())  # events to us specific
    kinds = [EventDefinitions.KIND_NIP90_GENERIC]
    #SUPPORTED_KINDS = [Kind(6100), Kind(7000)]

    for kind in range(6000, 7001):
        if kind not in kinds:
            kinds.append(Kind(kind))
    dvm_filter = (Filter().kinds(kinds).since(Timestamp.now()).pubkey(pk))
    await client.subscribe([dm_zap_filter, dvm_filter], None)

    # await nostr_client_test_translation("This is the result of the DVM in spanish", "text", "es", 20, 20)
    # await nostr_client_test_translation("note1p8cx2dz5ss5gnk7c59zjydcncx6a754c0hsyakjvnw8xwlm5hymsnc23rs", "event", "es", 20,20)
    # await nostr_client_test_translation("44a0a8b395ade39d46b9d20038b3f0c8a11168e67c442e3ece95e4a1703e2beb", "event", "zh", 20, 20)

    #await nostr_client_test_image("a beautiful purple ostrich watching the sunset, eating a cashew nut")
   # await nostr_client_custom_discovery("99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64", "8e998d62eb20ec892acf9d5e8efa58050ccd951cae15a64eabbc5c0a7c74d185")

    await nostr_client_duckduck_test("a018ba05af400b52772e33162d8326fca4a167fe7b6d3cd2382e14cac2af6841", "Write me a poem about purple ostriches")

    # await nostr_client_test_search_profile("dontbelieve")
    #wot = ["99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64"]
    # await nostr_client_test_discovery("99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64", "ab6cdf12ca3ae5109416295b8cd8a53fdec3a9d54beb7a9aee0ebfb67cb4edf7")
    # await nostr_client_test_discovery_gallery("99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64", "4add3944eb596a27a650f9b954f5ed8dfefeec6ca50473605b0fbb058dd11306")

    # await nostr_client_test_discovery("99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64",
    #                                      "2cf10ff849d2769b2b021bd93a0270d03eecfd14126d07f94c6ca2269cb3f3b1")

    # await nostr_client_test_censor_filter(wot)
    # await nostr_client_test_inactive_filter("99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64")

    #await nostr_client_test_tts("Hello, this is a test. Mic check one, two.")

    # cashutoken = "cashuAeyJ0b2tlbiI6W3sicHJvb2ZzIjpbeyJpZCI6InZxc1VRSVorb0sxOSIsImFtb3VudCI6MSwiQyI6IjAyNWU3ODZhOGFkMmExYTg0N2YxMzNiNGRhM2VhMGIyYWRhZGFkOTRiYzA4M2E2NWJjYjFlOTgwYTE1NGIyMDA2NCIsInNlY3JldCI6InQ1WnphMTZKMGY4UElQZ2FKTEg4V3pPck5rUjhESWhGa291LzVzZFd4S0U9In0seyJpZCI6InZxc1VRSVorb0sxOSIsImFtb3VudCI6NCwiQyI6IjAyOTQxNmZmMTY2MzU5ZWY5ZDc3MDc2MGNjZmY0YzliNTMzMzVmZTA2ZGI5YjBiZDg2Njg5Y2ZiZTIzMjVhYWUwYiIsInNlY3JldCI6IlRPNHB5WE43WlZqaFRQbnBkQ1BldWhncm44UHdUdE5WRUNYWk9MTzZtQXM9In0seyJpZCI6InZxc1VRSVorb0sxOSIsImFtb3VudCI6MTYsIkMiOiIwMmRiZTA3ZjgwYmMzNzE0N2YyMDJkNTZiMGI3ZTIzZTdiNWNkYTBhNmI3Yjg3NDExZWYyOGRiZDg2NjAzNzBlMWIiLCJzZWNyZXQiOiJHYUNIdHhzeG9HM3J2WWNCc0N3V0YxbU1NVXczK0dDN1RKRnVwOHg1cURzPSJ9XSwibWludCI6Imh0dHBzOi8vbG5iaXRzLmJpdGNvaW5maXhlc3RoaXMub3JnL2Nhc2h1L2FwaS92MS9ScDlXZGdKZjlxck51a3M1eVQ2SG5rIn1dfQ=="
    # await nostr_client_test_image_private("a beautiful ostrich watching the sunset")

    nutzap_wallet = NutZapWallet()
    nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)
    #dangerous, dont use this, except your wallet is messed up.
    delete = False
    if delete:
        for mint in nut_wallet.nutmints:
            await nutzap_wallet.update_spend_mint_proof_event(nut_wallet, mint.proofs, mint.mint_url, "", None,
                                                     None, client, keys)

        nut_wallet.balance = 0
        await nutzap_wallet.update_nut_wallet(nut_wallet, [], client, keys)
        nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)



    class NotificationHandler(HandleNotification):
        last_event_time = 0
        async def handle(self, relay_url, subscription_id, event: Event):

            print(
                bcolors.BLUE + f"Received new event from {relay_url}: {event.as_json()}" + bcolors.ENDC)
            if event.kind().as_u64() == 7000:
                print("[Nostr Client]: " + event.as_json())
                amount_sats = 0
                status = ""
                for tag in event.tags():
                    if tag.as_vec()[0] == "amount":
                        amount_sats = int(int(tag.as_vec()[1]) / 1000) # millisats
                    if tag.as_vec()[0] == "status":
                       status = tag.as_vec()[1]
                # THIS IS FOR TESTING
                if event.author().to_hex() == "89669b03bb25232f33192fdda77b8e36e3d3886e9b55b3c74b95091e916c8f98" and status == "payment-required" and event.created_at().as_secs() > self.last_event_time:
                    self.last_event_time = event.created_at().as_secs()
                    nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)
                    if nut_wallet is None:
                        await nutzap_wallet.create_new_nut_wallet(dvmconfig.NUZAP_MINTS, dvmconfig.NUTZAP_RELAYS, client, keys, "Test", "My Nutsack")
                        nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)
                        if nut_wallet is not None:
                            await nutzap_wallet.announce_nutzap_info_event(nut_wallet, client, keys)
                        else:
                            print("Couldn't fetch wallet, please restart and see if it is there")

                    await nutzap_wallet.send_nut_zap(amount_sats, "From my nutsack lol", nut_wallet, event.id().to_hex(),
                                                     event.author().to_hex(), client,
                                                     keys)


            elif 6000 < event.kind().as_u64() < 6999:
                print("[Nostr Client]: " + event.as_json())
                print("[Nostr Client]: " + event.content())

            elif event.kind().as_u64() == 4:
                dec_text = nip04_decrypt(sk, event.author(), event.content())
                print("[Nostr Client]: " + f"Received new msg: {dec_text}")

            elif event.kind().as_u64() == 9735:
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

    asyncio.run(nostr_client())
