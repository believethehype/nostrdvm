import asyncio
import json
from pathlib import Path

import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, Timestamp, nip04_decrypt, \
    nip44_encrypt, Nip44Version, NostrSigner, Event, Kind, RelayOptions

from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key
from nostr_dvm.utils.nut_wallet_utils import NutZapWallet
from nostr_dvm.utils.print_utils import bcolors


# TODO HINT: Best use this path with a previously whitelisted privkey, as zapping events is not implemented in the lib/code
async def nostr_client_test_translation(input, kind, lang, sats, satsmax):
    keys = Keys.parse(check_and_set_private_key("test_client"))
    if kind == "text":
        iTag = Tag.parse(["i", input, "text"])
    else:
        iTag = Tag.parse(["i", input, "event"])
    paramTag1 = Tag.parse(["param", "language", lang])

    bidTag = Tag.parse(['bid', str(sats * 1000), str(satsmax * 1000)])
    relaysTag = Tag.parse(['relays', "wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to translate a given Input"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_TRANSLATE_TEXT, str("Translate the given input.")).tags(
                         [iTag, paramTag1, bidTag, relaysTag, alttag]).sign_with_keys(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]

    client = Client(NostrSigner.keys(keys))

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
    event = EventBuilder(EventDefinitions.KIND_NIP90_USER_SEARCH, str("Search for user")).tags(
                         [iTag, alttag]).sign_with_keys(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]

    client = Client(NostrSigner.keys(keys))

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
    event = EventBuilder(EventDefinitions.KIND_NIP90_GENERATE_IMAGE, str("Generate an Image.")).tags(
                         [iTag, outTag, paramTag1, bidTag, relaysTag, alttag]).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
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

    event = EventBuilder(EventDefinitions.KIND_NIP90_PEOPLE_DISCOVERY, str("Give me bad actors")).tags(
                         tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
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

    event = EventBuilder(EventDefinitions.KIND_NIP90_PEOPLE_DISCOVERY, str("Give me inactive users")).tags(
                         tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)
    await client.add_relay("wss://nostr.band")
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
    event = EventBuilder(EventDefinitions.KIND_NIP90_TEXT_TO_SPEECH, str("Generate an Audio File.")).tags(
                         [iTag, paramTag1, bidTag, relaysTag, alttag]).sign_with_keys(keys)

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org" "wss://dvms.f7z.io",
                  ]

    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()


async def nostr_client_test_discovery(user, ptag):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    relay_list = ["wss://relay.nostrdvm.com",
                  ]

    relaysTag = Tag.parse(relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to find content"])
    paramTag = Tag.parse(["param", "user", user])
    pTag = Tag.parse(["p", ptag])
    expiration_tag = Tag.parse(["expiration", str(Timestamp.now().as_secs() + 60*60)])

    tags = [relaysTag, alttag, paramTag, pTag, expiration_tag]

    event = EventBuilder(EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY, str("Give me content")).tags(
                         tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)

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

    tags = [relaysTag, alttag, paramTag, pTag]# paramTagSearch, paramTagMust, paramTagAvoid]

    event = EventBuilder(EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY, str("Give me content")).tags(
                         tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)

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

    event = EventBuilder(Kind(5050), str("Give me content")).tags(
                         tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)
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

    event = EventBuilder(Kind(5050), str("Give me content")).tags(
                         tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    await send_event(event, client=client, dvm_config=config)
    return event.as_json()
async def nostr_client_flux_schnell(ptag, query):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    relay_list = ["wss://nostr.oxtr.dev", "wss://relay.primal.net",
                  ]

    relaysTag = Tag.parse(relay_list)
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task"])

    pTag = Tag.parse(["p", ptag])
    iTag = Tag.parse(["i", query, "text"])

    tags = [relaysTag, alttag, pTag, iTag]

    event = EventBuilder(Kind(5100), str("Give me image")).tags(
                         tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
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

    event = EventBuilder(EventDefinitions.KIND_NIP90_PEOPLE_DISCOVERY, str("Give me people")).tags(
                         tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
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

    event = EventBuilder(EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY, str("Give me visuals")).tags(
                         tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    eventid = await send_event(event, client=client, dvm_config=config)

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

    encrypted_params = nip44_encrypt(keys.secret_key(), receiver_keys.public_key(),
                                     encrypted_params_string, Nip44Version.V2)

    encrypted_tag = Tag.parse(['encrypted'])
    nip90request = EventBuilder(EventDefinitions.KIND_NIP90_GENERATE_IMAGE, encrypted_params).tags(
                                [pTag, encrypted_tag]).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    config = DVMConfig
    await send_event(nip90request, client=client, dvm_config=config)
    return nip90request.as_json()


async def nostr_client():
    keys = Keys.parse(check_and_set_private_key("test_client5"))
    sk = keys.secret_key()
    pk = keys.public_key()
    print(f"Nostr Client public key: {pk.to_bech32()}, Hex: {pk.to_hex()} ")
    client = Client(NostrSigner.keys(keys))

    dvmconfig = DVMConfig()
    for relay in dvmconfig.RELAY_LIST:
        await client.add_relay(relay)
    await client.connect()

    dm_zap_filter = Filter().pubkey(pk).kinds([EventDefinitions.KIND_DM,
                                               EventDefinitions.KIND_ZAP, EventDefinitions.KIND_NIP61_NUT_ZAP]).since(
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
    #await nostr_client_custom_discovery("99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64", "7240284b84951cfedbc20fce26f0e3f0a36da3e9c1be85d7a06965f0d4fe25fb")
    #"a018ba05af400b52772e33162d8326fca4a167fe7b6d3cd2382e14cac2af6841"
   # await nostr_client_duckduck_test(PublicKey.parse("7a63849b684d90c0de983492578b12e147e56f5d79ed6585cc64e5aa8a122744").to_hex() , "How do i create a dockerfile for python 3.12")
    #await nostr_client_flux_schnell("d57f1efb7582f58cade6f482d53eefa998d8082711b996aae3dc5f5527cbdd6e" , "topics")

    # await nostr_client_test_search_profile("dontbelieve")
    #wot = ["99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64"]
    await nostr_client_test_discovery("99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64", "9e09a914f41db178ba442b7372944b021135c08439516464a9bd436588af0b58")
    #await nostr_client_test_discovery_gallery("99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64", "4add3944eb596a27a650f9b954f5ed8dfefeec6ca50473605b0fbb058dd11306")

    #await nostr_client_test_discovery("99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64",
    #                                      "7a63849b684d90c0de983492578b12e147e56f5d79ed6585cc64e5aa8a122744")

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
    else:
        nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)
        if nut_wallet is None:
            await nutzap_wallet.create_new_nut_wallet(dvmconfig.NUZAP_MINTS, dvmconfig.NUTZAP_RELAYS, client, keys,
                                                      "Test", "My Nutsack")
            nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)
            if nut_wallet is not None:
                await nutzap_wallet.announce_nutzap_info_event(nut_wallet, client, keys)
            else:
                print("Couldn't fetch wallet, please restart and see if it is there")



    class NotificationHandler(HandleNotification):
        last_event_time = 0
        async def handle(self, relay_url, subscription_id, event: Event):

            print(
                bcolors.BLUE + f"Received new event from {relay_url}: {event.as_json()}" + bcolors.ENDC)
            if event.kind().as_u16() == 7000:
                print("[Nostr Client]: " + event.as_json())
                amount_sats = 0
                status = ""
                for tag in event.tags().to_vec():
                    if tag.as_vec()[0] == "amount":
                        amount_sats = int(int(tag.as_vec()[1]) / 1000) # millisats
                    if tag.as_vec()[0] == "status":
                       status = tag.as_vec()[1]
                # THIS IS FOR TESTING


            elif 6000 < event.kind().as_u16() < 6999:
                print("[Nostr Client]: " + event.as_json())
                print("[Nostr Client]: " + event.content())

            elif event.kind().as_u16() == 4:
                dec_text = nip04_decrypt(sk, event.author(), event.content())
                print("[Nostr Client]: " + f"Received new msg: {dec_text}")

            elif event.kind().as_u16() == 9735:
                print("[Nostr Client]: " + f"Received new zap:")
                print(event.as_json())
            if event.kind().as_u16() == 9321:
                print(bcolors.YELLOW + "[Client] NutZap 🥜️⚡ received" + event.as_json() + bcolors.ENDC)

                # if event.author().to_hex() == keys.public_key().to_hex():
                #     #sleep to avoid event not being updated on self zap
                #     await asyncio.sleep(5)

                nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)
                if nut_wallet is not None:
                    await nutzap_wallet.reedeem_nutzap(event, nut_wallet, client, keys)
                    # await get_nut_wallet(client, keys)

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
