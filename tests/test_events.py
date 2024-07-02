import asyncio
from datetime import timedelta
from pathlib import Path

import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, Timestamp, nip04_decrypt, \
    nip04_encrypt, EventId, Options, PublicKey, Event, NostrSigner, Nip19Event

from nostr_dvm.utils import definitions, dvmconfig
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.gallery_utils import gallery_announce_list
from nostr_dvm.utils.nip89_utils import NIP89Config
from nostr_dvm.utils.nostr_utils import check_and_set_private_key



async def test():

    relay_list = dvmconfig.DVMConfig.RELAY_LIST
    keys = Keys.parse(check_and_set_private_key("test_client"))
    wait_for_send = False
    skip_disconnected_relays = True
    opts = (Options().wait_for_send(wait_for_send).send_timeout(timedelta(seconds=5))
            .skip_disconnected_relays(skip_disconnected_relays))

    signer = NostrSigner.keys(keys)
    client = Client.with_opts(signer, opts)

    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()

    await test_referred_events(client,"c70fbd4dbaad22c427d4359981d3bdddd3971ed1a38227ca2f8e5e760f58103c",
                         definitions.EventDefinitions.ANY_RESULT)

    # shows kind 7000 reaction but not kind 6300 result (d05e7ae9271fe2d8968cccb67c01e3458dbafa4a415e306d49b22729b088c8a1)
    await test_referred_events(client, "5635e5dd930b3c831f6ab1e348bb488f3c9aca2f13190e93ab5e5e1e1ba1835e",
                         definitions.EventDefinitions.ANY_RESULT)

    bech32evnt = EventId.from_hex("5635e5dd930b3c831f6ab1e348bb488f3c9aca2f13190e93ab5e5e1e1ba1835e").to_bech32()
    print(bech32evnt)

    test = Nip19Event.from_bech32(
        "nevent1qqsrjcpejsrlt3u7dy42y6rc97svrq9ver08xy4jr2ll55ynq3sxafcppamhxue69uhkummnw3ezumt0d5pzpmnqx2pla0zvxxcfjqeeysy29ll3mtmf4s3yff0y45r7egau080vqvzqqqqqqyu4q839")
    print(test.event_id().to_hex())

    nostruri = EventId.from_hex("5635e5dd930b3c831f6ab1e348bb488f3c9aca2f13190e93ab5e5e1e1ba1835e").to_nostr_uri()
    print(nostruri)

    await test_search_by_user_since_days(client,
        PublicKey.from_bech32("npub1nxa4tywfz9nqp7z9zp7nr7d4nchhclsf58lcqt5y782rmf2hefjquaa6q8"), 60, "Bitcoin")


async def test_referred_events(client, event_id, kinds=None):

    if kinds is None:
        kinds = []

    if len(kinds) > 0:
        job_id_filter = Filter().kinds(kinds).event(EventId.from_hex(event_id))
    else:
        job_id_filter = Filter().event(EventId.from_hex(event_id))

    events = await client.get_events_of([job_id_filter], timedelta(seconds=5))

    if len(events) > 0:
        for event in events:
            print(event.as_json())
        return events[0]
    else:
        print("None")
        return None



async def test_gallery():
    relay_list = dvmconfig.DVMConfig.RELAY_LIST
    keys = Keys.parse(check_and_set_private_key("test_client"))
    wait_for_send = False
    skip_disconnected_relays = True
    opts = (Options().wait_for_send(wait_for_send).send_timeout(timedelta(seconds=5))
            .skip_disconnected_relays(skip_disconnected_relays))

    signer = NostrSigner.keys(keys)
    client = Client.with_opts(signer, opts)

    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    dvm_config = DVMConfig()
    dvm_config.NIP89 = NIP89Config()
    keys = Keys.parse(check_and_set_private_key("RTEST_ACCOUNT_PK"))
    dvm_config.NIP89.PK = keys.secret_key().to_hex()
    tagname = "gallery"
    tags = [

            Tag.parse([tagname, "3b0ec270394dc496f9f9c7db5c68a5b7f7311ff9080a51f1e8cb5f5cffc2c0b2", "https://i.nostr.build/xEZqV.jpg"]),
            Tag.parse([tagname, "dd6e5c2891fbe9f53bcaa351b48faeeedccd16e9541b508adcb2c16d11bceaaf", "https://i.nostr.build/2RnXd.jpg"]),
            Tag.parse([tagname, "b2868e1ef93523ecf15b26e1cfdb6f252fe5074867d9c042fd6fcfbf07959193", "https://i.nostr.build/WG2Ra.jpg"]),
            Tag.parse([tagname, "489402bf3ec070e7ebf2ba459508d2e1a408c0adad02954470602f232026a37d", "https://i.nostr.build/M5keE.jpg"]),
            Tag.parse([tagname, "0e37cb0373189e01be3c744c0434e0c8559953910e44b05ed270313c47abe142", "https://v.nostr.build/M5kZ5.mp4"]),
            Tag.parse([tagname, "102d1f411a9a2b4de37ef62cdd4943673b4941080a51a8fa8829cd9f1de46d13", "https://i.nostr.build/vGLg7.jpg"]),
            Tag.parse([tagname, "4022d4e893c224186bbef4414340e35cbf251c681bc84ab05446fec1d2ec67df", "https://i.nostr.build/O4WxA.jpg"]),
            Tag.parse([tagname, "6f04dc6a2a05f710b9c6c6d09a02c5fe0174da9c95399d3d01963a784d195803", "https://i.nostr.build/M5a96.jpg"]),
            Tag.parse([tagname, "737a169c245ce7957a8b6acf190c57d70256cc52630862f5ba0fd7315ef83425", "https://i.nostr.build/WG02Y.jpg"]),
            Tag.parse([tagname, "c3a3a8759502cb3c06d592e5715cad0826982a2ff60a0ae525e3f253ab9e462a", "https://i.nostr.build/Dj2Q4.jpg"]),
            Tag.parse([tagname, "015e71ded102e96d2b30f63dec0c04546d52a51f709709391af68d73f7502feb", "https://i.nostr.build/7G2G2.jpg"]),
            Tag.parse([tagname, "43da37c84113d4c0bdc60ae1c82cef9761ff7a2a1ef29b1cc26abfd4932786c5", "https://i.nostr.build/XVLkd.jpg"]),
            Tag.parse(["alt", "Profile Gallery List"])
          ]

    await gallery_announce_list(tags, dvm_config, client)

async def test_search_by_user_since_days(client, pubkey, days, prompt):
    since_seconds = int(days) * 24 * 60 * 60
    dif = Timestamp.now().as_secs() - since_seconds
    since = Timestamp.from_secs(dif)

    filterts = Filter().search(prompt).author(pubkey).kinds([1]).since(since)
    events = await client.get_events_of([filterts], timedelta(seconds=5))

    if len(events) > 0:
        for event in events:
            print(event.as_json())
        return events[0]
    else:
        print("None")
        return None



if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    asyncio.run(test_gallery())

    # works

