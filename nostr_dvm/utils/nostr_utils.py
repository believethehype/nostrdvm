import json
import os
from datetime import timedelta
from pathlib import Path
from typing import List

import dotenv
from nostr_sdk import Filter, Client, Alphabet, EventId, Event, PublicKey, Tag, Keys, nip04_decrypt, nip44_decrypt,  Metadata, Options, \
    Nip19Event, SingleLetterTag, RelayLimits, SecretKey, Connection, ConnectionTarget, \
    EventBuilder, Kind, ClientBuilder, SendEventOutput, NostrSigner

from nostr_dvm.utils.definitions import EventDefinitions, relay_timeout


async def get_event_by_id(event_id_str: str, client: Client, config=None) -> Event | None:
    split = event_id_str.split(":")
    if len(split) == 3:
        pk = PublicKey.parse(split[1])
        id_filter = Filter().author(pk).custom_tag(SingleLetterTag.lowercase(Alphabet.D), [split[2]])
        events = await client.fetch_events([id_filter], relay_timeout)
    else:
        event_id = EventId.parse(event_id_str)

        id_filter = Filter().id(event_id).limit(1)

        events = await client.fetch_events([id_filter], relay_timeout)

    if len(events.to_vec()) > 0:
        return events.to_vec()[0]
    else:
        print("Event not found")
        return None


async def get_events_async(client, filter, timeout):
    events = await client.fetch_events([filter], timedelta(seconds=timeout))
    return events.to_vec()


async def get_events_by_ids(event_ids, client: Client, config=None) -> List | None:
    search_ids = []
    events = []
    for event_id in event_ids:
        split = event_id.split(":")
        if len(split) == 3:
            pk = PublicKey.parse(split[1])
            id_filter = Filter().author(pk).custom_tag(SingleLetterTag.lowercase(Alphabet.D), [split[2]])
            events = await client.fetch_events([id_filter], relay_timeout)
        else:

            if str(event_id).startswith("nevent"):
                event_id = Nip19Event.from_bech32(event_id).event_id()
            elif str(event_id).startswith("nostr:nevent"):
                event_id = Nip19Event.from_nostr_uri(event_id).event_id()
            else:
                event_id = EventId.parse(event_id)
            search_ids.append(event_id)

            id_filter = Filter().ids(search_ids)
            events = await client.fetch_events([id_filter], relay_timeout)

    if len(events.to_vec()) > 0:
        return events.to_vec()
    else:
        return None


async def get_events_by_id(event_ids: list, client: Client, config=None) -> list[Event] | None:
    id_filter = Filter().ids(event_ids)
    # events = asyncio.run(get_events_async(client, id_filter, config.RELAY_TIMEOUT))
    events = await client.fetch_events([id_filter], relay_timeout)
    if len(events.to_vec()) > 0:
        return events.to_vec()
    else:
        return None


async def get_referenced_event_by_id(event_id, client, dvm_config, kinds) -> Event | None:
    if kinds is None:
        kinds = []
    if str(event_id).startswith("nevent"):
        event_id = Nip19Event.from_bech32(event_id).event_id()
    elif str(event_id).startswith("nostr:nevent"):
        event_id = Nip19Event.from_nostr_uri(event_id).event_id()
    else:
        event_id = EventId.parse(event_id)

    if len(kinds) > 0:
        job_id_filter = Filter().kinds(kinds).event(event_id).limit(1)
    else:
        job_id_filter = Filter().event(event_id).limit(1)
    events = await client.fetch_events([job_id_filter], relay_timeout)

    if len(events.to_vec()) > 0:
        return events.to_vec()[0]
    else:
        return None


async def get_inbox_relays(event_to_send: Event, client: Client, dvm_config):
    ptags = []
    for tag in event_to_send.tags().to_vec():
        if tag.as_vec()[0] == 'p':
            ptag = PublicKey.parse(tag.as_vec()[1])
            ptags.append(ptag)

    filter = Filter().kinds([EventDefinitions.KIND_RELAY_ANNOUNCEMENT]).authors(ptags)
    events = await client.fetch_events([filter], relay_timeout)
    if len(events.to_vec()) == 0:
        return []
    else:
        nip65event = events.to_vec()[0]
        relays = []
        for tag in nip65event.tags().to_vec():
            if ((tag.as_vec()[0] == 'r' and len(tag.as_vec()) == 2)
                    or ((tag.as_vec()[0] == 'r' and len(tag.as_vec()) == 3) and tag.as_vec()[2] == "read")):
                rtag = tag.as_vec()[1]
                if rtag.rstrip("/") not in dvm_config.AVOID_OUTBOX_RELAY_LIST:
                    if rtag.startswith("ws") and " " not in rtag:
                        relays.append(rtag)
        return relays


async def get_dm_relays(event_to_send: Event, client: Client, dvm_config):
    ptags = []
    for tag in event_to_send.tags().to_vec():
        if tag.as_vec()[0] == 'p':
            ptag = PublicKey.parse(tag.as_vec()[1])
            ptags.append(ptag)

    filter = Filter().kinds([Kind(10050)]).authors(ptags)
    events = await client.fetch_events([filter], relay_timeout)
    if len(events.to_vec()) == 0:
        return []
    else:
        nip65event = events.to_vec()[0]
        relays = []
        for tag in nip65event.tags().to_vec():
            if ((tag.as_vec()[0] == 'r' and len(tag.as_vec()) == 2)
                    or ((tag.as_vec()[0] == 'r' and len(tag.as_vec()) == 3) and tag.as_vec()[2] == "read")):
                rtag = tag.as_vec()[1]
                if rtag.rstrip("/") not in dvm_config.AVOID_OUTBOX_RELAY_LIST:
                    if rtag.startswith("ws") and " " not in rtag:
                        relays.append(rtag)
        return relays


async def get_main_relays(event_to_send: Event, client: Client, dvm_config):
    ptags = []
    for tag in event_to_send.tags().to_vec():
        if tag.as_vec()[0] == 'p':
            ptag = PublicKey.parse(tag.as_vec()[1])
            ptags.append(ptag)

    if len(await client.relays()) == 0:
        for relay in dvm_config.RELAY_LIST:
            await client.add_relay(relay)

    await client.connect()
    filter = Filter().kinds([EventDefinitions.KIND_FOLLOW_LIST]).authors(ptags)
    events = await client.fetch_events([filter], relay_timeout)
    if len(events.to_vec()) == 0:
        return []
    else:
        followlist = events.to_vec()[0]
        try:
            content = json.loads(followlist.content())
            relays = []
            for relay in content:
                if relay.rstrip("/") not in dvm_config.AVOID_OUTBOX_RELAY_LIST:
                    relays.append(relay)
            return relays
        except:
            return []


async def send_event_outbox(event: Event, client, dvm_config) -> SendEventOutput | None:
    # 1. OK, Let's overcomplicate things.
    # 2. If our event has a relays tag, we just send the event to these relay in the classical way.
    relays = []
    for tag in event.tags().to_vec():
        if tag.as_vec()[0] == 'relays':
            for index, param in enumerate(tag.as_vec()):
                if index != 0:
                    if tag.as_vec()[index].rstrip("/") not in dvm_config.AVOID_OUTBOX_RELAY_LIST:
                        try:
                            relays.append(tag.as_vec()[index])
                        except:
                            print("[" + dvm_config.NIP89.NAME + "] " + tag.as_vec()[
                                index] + " couldn't be added to outbox relays")
            break

    # 3. If we couldn't find relays, we look in the receivers inbox
    if len(relays) == 0:
        relays = await get_inbox_relays(event, client, dvm_config)

    # 4. If we don't find inbox relays (e.g. because the user didn't announce them, we just send to our default relays
    if len(relays) == 0:
        print("[" + dvm_config.NIP89.NAME + "] No Inbox found, replying to generic relays")
        relays = await get_main_relays(event, client, dvm_config)


    if len(relays) == 0:
        return
        # eventid = await send_event(event, client, dvm_config)
        # return eventid

    # 5. Otherwise, we create a new Outbox client with the inbox relays and send the event there
    relaylimits = RelayLimits.disable()
    connection = Connection().embedded_tor().target(ConnectionTarget.ONION)    
    
    # connection = Connection().addr("127.0.0.1:9050").target(ConnectionTarget.ONION)
    opts = Options().relay_limits(relaylimits).connection(connection)
    sk = SecretKey.parse(dvm_config.PRIVATE_KEY)
    keys = Keys.parse(sk.to_hex())
    outboxclient = ClientBuilder().signer(NostrSigner.keys(keys)).opts(opts).build()
    #print("[" + dvm_config.NIP89.NAME + "] Receiver Inbox relays: " + str(relays))

    for relay in relays[:5]:
        try:
            if not relay.startswith("ws://") and not relay.startswith("wss://"):
                raise Exception("wrong Scheme")
            await outboxclient.add_relay(relay)
        except:
            print("[" + dvm_config.NIP89.NAME + "] " + relay + " couldn't be added to outbox relays")
    #
    await outboxclient.connect()
    try:
        #print("Connected, sending event")
        event_response = await outboxclient.send_event(event)

    except Exception as e:
        event_response = None
        print(e)

    # 5. Fallback, if we couldn't send the event to any relay, we try to send to generic relays instead.
    if event_response is None:
        relays = await get_main_relays(event, client, dvm_config)
        if len(relays) == 0:
            return None
        for relay in relays:
            try:
                if not relay.startswith("ws://") and not relay.startswith("wss://"):
                    raise Exception("wrong Scheme")
                await outboxclient.add_relay(relay)
            except:
                print("[" + dvm_config.NIP89.NAME + "] " + relay + " couldn't be added to outbox relays")
        try:
            await outboxclient.connect()
            event_response = await outboxclient.send_event(event)
        except Exception as e:
            # Love yourself then.
            event_response = None
            print(e)


    await outboxclient.shutdown()

    return event_response


async def send_event(event: Event, client: Client, dvm_config, broadcast=False):
    try:
        relays = []
        for tag in event.tags().to_vec():
            if tag.as_vec()[0] == 'relays':
                for index, param in enumerate(tag.as_vec()):
                    if index != 0:
                        if tag.as_vec()[index].rstrip("/") not in dvm_config.AVOID_OUTBOX_RELAY_LIST:
                            try:
                                relays.append(tag.as_vec()[index])
                            except:
                                print("[" + dvm_config.NIP89.NAME + "] " + tag.as_vec()[
                                    index] + " couldn't be added to outbox relays")
                break

        relay_list = dvm_config.RELAY_LIST
        if broadcast:
            relay_list = dvm_config.ANNOUNCE_RELAY_LIST

        if len(relays) == 0:
            relays = relay_list

        for relay in relays:
            if relay not in dvm_config.RELAY_LIST:
                try:
                    await client.add_relay(relay)
                except:
                    print("[" + dvm_config.NIP89.NAME + "] " + relay + " couldn't be added to relays")


        await client.connect()

        try:
            response_status = await client.send_event(event)
        except Exception as e:
            print(e)
            response_status = None

        for relay in relays:
            if relay not in dvm_config.RELAY_LIST:
                await client.force_remove_relay(relay)
        return response_status
    except Exception as e:
        print(e)


def print_send_result(response_status):
    print("Success: " + str(response_status.success) + " Failed: " + str(response_status.failed) + " EventID: "
          + response_status.id.to_hex() + " / " + response_status.id.to_bech32())


def check_and_decrypt_tags(event, dvm_config):
    is_encrypted = False
    use_legacy_encryption = False

    try:
        p = ""
        for tag in event.tags().to_vec():
            if tag.as_vec()[0] == 'encrypted':
                is_encrypted = True
            elif tag.as_vec()[0] == 'p':
                p = tag.as_vec()[1]

        if is_encrypted:
            if p != dvm_config.PUBLIC_KEY:
                print("[" + dvm_config.NIP89.NAME + "] Task encrypted and not addressed to this DVM, "
                                                    "skipping..")
                return None, False

            elif p == dvm_config.PUBLIC_KEY:
                try:
                    tags_str = nip04_decrypt(Keys.parse(dvm_config.PRIVATE_KEY).secret_key(),
                                             event.author(), event.content())
                except:
                    try:
                        tags_str = nip44_decrypt(Keys.parse(dvm_config.PRIVATE_KEY).secret_key(),
                                                 event.author(), event.content())
                    except:
                        print("Wrong Nip44 Format")
                        return None, False
                    use_legacy_encryption = True

                params = json.loads(tags_str)
                params.append(Tag.parse(["p", p]).as_vec())
                params.append(Tag.parse(["encrypted"]).as_vec())
                event_as_json = json.loads(event.as_json())
                event_as_json['tags'] = params
                event_as_json['content'] = ""
                event = Event.from_json(json.dumps(event_as_json))
    except Exception as e:
        print(e)

    return event, use_legacy_encryption


def check_and_decrypt_own_tags(event, dvm_config):
    try:
        is_encrypted = False
        p = ""
        for tag in event.tags().to_vec():
            if tag.as_vec()[0] == 'encrypted':
                is_encrypted = True
            elif tag.as_vec()[0] == 'p':
                p = tag.as_vec()[1]

        if is_encrypted:
            if dvm_config.PUBLIC_KEY != event.author().to_hex():
                print("[" + dvm_config.NIP89.NAME + "] Task encrypted and not addressed to this DVM, "
                                                    "skipping..")
                return None

            elif event.author().to_hex() == dvm_config.PUBLIC_KEY:
                try:
                    tags_str = nip44_decrypt(Keys.parse(dvm_config.PRIVATE_KEY).secret_key(),
                                             PublicKey.parse(p), event.content())
                except:
                    tags_str = nip04_decrypt(Keys.parse(dvm_config.PRIVATE_KEY).secret_key(),
                                             PublicKey.parse(p), event.content())
                params = json.loads(tags_str)
                params.append(Tag.parse(["p", p]).as_vec())
                params.append(Tag.parse(["encrypted"]).as_vec())
                event_as_json = json.loads(event.as_json())
                event_as_json['tags'] = params
                event_as_json['content'] = ""
                event = Event.from_json(json.dumps(event_as_json))
    except Exception as e:
        print(e)

    return event


async def update_profile_lnaddress(private_key, dvm_config, lud16="", ):
    keys = Keys.parse(private_key)
    client = Client(NostrSigner.keys(keys))
    for relay in dvm_config.RELAY_LIST:
        await client.add_relay(relay)
    await client.connect()

    metadata = Metadata() \
        .set_lud16(lud16) \
        .set_nip05(lud16)

    await client.set_metadata(metadata)


async def update_profile(dvm_config, client, lud16="", broadcast=True):
    keys = Keys.parse(dvm_config.PRIVATE_KEY)
    try:
        nip89content = json.loads(dvm_config.NIP89.CONTENT)
        name = nip89content.get("name")
        about = nip89content.get("about")
        image = nip89content.get("picture")

        # Set metadata
        metadata = Metadata() \
            .set_name(name) \
            .set_display_name(name) \
            .set_about(about) \
            .set_picture(image) \
            .set_lud16(lud16) \
            .set_nip05(lud16)
        # .set_banner("https://example.com/banner.png") \


    except:
        metadata = Metadata() \
            .set_lud16(lud16) \
            .set_nip05(lud16)

    print("[" + dvm_config.NIP89.NAME + "] Setting profile metadata for " + keys.public_key().to_bech32() + "...")
    print(metadata.as_json())
    if broadcast:
       for relay in dvm_config.ANNOUNCE_RELAY_LIST:
           await client.add_relay(relay)
       await client.connect()

    return await client.set_metadata(metadata)


async def send_nip04_dm(client: Client, msg, receiver: PublicKey, dvm_config):
    keys = Keys.parse(dvm_config.PRIVATE_KEY)
    signer = NostrSigner.keys(keys)
    content = await signer.nip04_encrypt(receiver, msg)
    ptag = Tag.parse(["p", receiver.to_hex()])
    event = EventBuilder(Kind(4), content).tags([ptag]).sign_with_keys(Keys.parse(dvm_config.PRIVATE_KEY))
    await client.send_event(event)

    # relays = await get_dm_relays(event, client, dvm_config)
    #
    # outboxclient = Client(signer)
    # print("[" + dvm_config.NIP89.NAME + "] Receiver Inbox relays: " + str(relays))
    #
    # for relay in relays[:5]:
    #     try:
    #         await outboxclient.add_relay(relay)
    #     except:
    #         print("[" + dvm_config.NIP89.NAME + "] " + relay + " couldn't be added to outbox relays")
    # #
    # await outboxclient.connect()
    # try:
    #     print("Connected, sending event")
    #     event_id = await outboxclient.send_event(event)
    #     print(event_id.output)
    # except Exception as e:
    #     print(e)


def check_and_set_private_key(identifier):
    if not os.getenv("DVM_PRIVATE_KEY_" + identifier.upper()):
        pk = Keys.generate().secret_key().to_hex()
        add_pk_to_env_file("DVM_PRIVATE_KEY_" + identifier.upper(), pk)
        return pk
    else:
        return os.getenv("DVM_PRIVATE_KEY_" + identifier.upper())


def add_pk_to_env_file(dtag, oskey):
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
        dotenv.set_key(env_path, dtag, oskey)
