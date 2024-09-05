import json
import os
from datetime import timedelta
from pathlib import Path
from typing import List

import dotenv
from nostr_sdk import Filter, Client, Alphabet, EventId, Event, PublicKey, Tag, Keys, nip04_decrypt, Metadata, Options, \
    Nip19Event, SingleLetterTag, RelayOptions, RelayLimits, SecretKey, NostrSigner, Connection, ConnectionTarget, \
    EventSource

from nostr_dvm.utils.definitions import EventDefinitions, relay_timeout, relay_timeout_long


async def get_event_by_id(event_id: str, client: Client, config=None) -> Event | None:
    split = event_id.split(":")
    if len(split) == 3:
        pk = PublicKey.from_hex(split[1])
        id_filter = Filter().author(pk).custom_tag(SingleLetterTag.lowercase(Alphabet.D), [split[2]])
        events = await client.get_events_of([id_filter], relay_timeout)
    else:
        if str(event_id).startswith('note'):
            event_id = EventId.from_bech32(event_id)
        elif str(event_id).startswith("nevent"):
            event_id = Nip19Event.from_bech32(event_id).event_id()
        elif str(event_id).startswith('nostr:note'):
            event_id = EventId.from_nostr_uri(event_id)
        elif str(event_id).startswith("nostr:nevent"):
            event_id = Nip19Event.from_nostr_uri(event_id).event_id()

        else:
            event_id = EventId.from_hex(event_id)

        id_filter = Filter().id(event_id).limit(1)
        events = await client.get_events_of([id_filter], relay_timeout)


    if len(events) > 0:

        return events[0]
    else:
        print("Event not found")
        return None

async def get_events_async(client, filter, timeout):
    source_l = EventSource.relays(timedelta(seconds=timeout))
    events = await client.get_events_of([filter], source_l)
    return events


async def get_events_by_ids(event_ids, client: Client, config=None) -> List | None:
    search_ids = []
    events = []
    for event_id in event_ids:
        split = event_id.split(":")
        if len(split) == 3:
            pk = PublicKey.from_hex(split[1])
            id_filter = Filter().author(pk).custom_tag(SingleLetterTag.lowercase(Alphabet.D), [split[2]])
            events = await client.get_events_of([id_filter], relay_timeout)
        else:
            if str(event_id).startswith('note'):
                event_id = EventId.from_bech32(event_id)
            elif str(event_id).startswith("nevent"):
                event_id = Nip19Event.from_bech32(event_id).event_id()
            elif str(event_id).startswith('nostr:note'):
                event_id = EventId.from_nostr_uri(event_id)
            elif str(event_id).startswith("nostr:nevent"):
                event_id = Nip19Event.from_nostr_uri(event_id).event_id()

            else:
                event_id = EventId.from_hex(event_id)
            search_ids.append(event_id)

            id_filter = Filter().ids(search_ids)
            events = await client.get_events_of([id_filter], relay_timeout)

    if len(events) > 0:
        return events
    else:
        return None


async def get_events_by_id(event_ids: list, client: Client, config=None) -> list[Event] | None:
    id_filter = Filter().ids(event_ids)
    #events = asyncio.run(get_events_async(client, id_filter, config.RELAY_TIMEOUT))
    events = await client.get_events_of([id_filter], relay_timeout)
    if len(events) > 0:
        return events
    else:
        return None


async def get_referenced_event_by_id(event_id, client, dvm_config, kinds) -> Event | None:
    if kinds is None:
        kinds = []
    if str(event_id).startswith('note'):
        event_id = EventId.from_bech32(event_id)
    elif str(event_id).startswith("nevent"):
        event_id = Nip19Event.from_bech32(event_id).event_id()
    elif str(event_id).startswith('nostr:note'):
        event_id = EventId.from_nostr_uri(event_id)
    elif str(event_id).startswith("nostr:nevent"):
        event_id = Nip19Event.from_nostr_uri(event_id).event_id()
    else:
        event_id = EventId.from_hex(event_id)

    if len(kinds) > 0:
        job_id_filter = Filter().kinds(kinds).event(event_id).limit(1)
    else:
        job_id_filter = Filter().event(event_id).limit(1)
    events = await client.get_events_of([job_id_filter], relay_timeout)


    if len(events) > 0:
        return events[0]
    else:
        return None


async def get_inbox_relays(event_to_send: Event, client: Client, dvm_config):
    ptags = []
    for tag in event_to_send.tags():
        if tag.as_vec()[0] == 'p':
            ptag = PublicKey.parse(tag.as_vec()[1])
            ptags.append(ptag)

    filter = Filter().kinds([EventDefinitions.KIND_RELAY_ANNOUNCEMENT]).authors(ptags)
    events = await client.get_events_of([filter], relay_timeout)
    if len(events) == 0:
        return []
    else:
        nip65event = events[0]
        relays = []
        for tag in nip65event.tags():
            if ((tag.as_vec()[0] == 'r' and len(tag.as_vec()) == 2)
                    or ((tag.as_vec()[0] == 'r' and len(tag.as_vec()) == 3) and tag.as_vec()[2] == "read")):
                rtag = tag.as_vec()[1]
                if rtag.rstrip("/") not in dvm_config.AVOID_PAID_OUTBOX_RELAY_LIST:
                    if rtag.startswith("ws") and " " not in rtag:
                        relays.append(rtag)
        return relays


async def get_main_relays(event_to_send: Event, client: Client, dvm_config):
    ptags = []
    for tag in event_to_send.tags():
        if tag.as_vec()[0] == 'p':
            ptag = PublicKey.parse(tag.as_vec()[1])
            ptags.append(ptag)

    if len(await client.relays()) == 0:
            for relay in dvm_config.RELAY_LIST:
                await client.add_relay(relay)

    await client.connect()
    filter = Filter().kinds([EventDefinitions.KIND_FOLLOW_LIST]).authors(ptags)
    events = await client.get_events_of([filter], relay_timeout)
    if len(events) == 0:
        return []
    else:
        followlist = events[0]
        try:
            content = json.loads(followlist.content())
            relays = []
            for relay in content:
               relays.append(relay)
            return relays
        except:
            return []




async def send_event_outbox(event: Event, client, dvm_config) -> EventId:

    # 1. OK, Let's overcomplicate things.
    # 2. If our event has a relays tag, we just send the event to these relay in the classical way.
    relays = []
    for tag in event.tags():
        if tag.as_vec()[0] == 'relays':
            for index, param in enumerate(tag.as_vec()):
                if index != 0:
                    if tag.as_vec()[index].rstrip("/") not in dvm_config.AVOID_PAID_OUTBOX_RELAY_LIST:
                        try:
                            relays.append(tag.as_vec()[index])
                        except:
                            print("[" + dvm_config.NIP89.NAME + "] " + tag.as_vec()[index] + " couldn't be added to outbox relays")
            break


    # 3. If we couldn't find relays, we look in the receivers inbox
    if len(relays) == 0:
        relays = await get_inbox_relays(event, client, dvm_config)

    # 4. If we don't find inbox relays (e.g. because the user didn't announce them, we just send to our default relays
    if len(relays) == 0:
        print("[" + dvm_config.NIP89.NAME + "] No Inbox found, replying to generic relays")
        relays = await get_main_relays(event, client, dvm_config)

        #eventid = await send_event(event, client, dvm_config)
        #return eventid

    # 5. Otherwise, we create a new Outbox client with the inbox relays and send the event there
    relaylimits = RelayLimits.disable()
    connection = Connection().embedded_tor().target(ConnectionTarget.ONION)
    #connection = Connection().addr("127.0.0.1:9050").target(ConnectionTarget.ONION)
    opts = (
        Options().wait_for_send(False).send_timeout(timedelta(seconds=20)).relay_limits(
            relaylimits)).connection(connection).connection_timeout(timedelta(seconds=120))



    sk = SecretKey.from_hex(dvm_config.PRIVATE_KEY)
    keys = Keys.parse(sk.to_hex())
    signer = NostrSigner.keys(keys)
    client = Client.with_opts(signer, opts)



    outboxclient = Client.with_opts(signer, opts)
    print("[" + dvm_config.NIP89.NAME + "] Receiver Inbox relays: " + str(relays))

    for relay in relays:
        try:
            await outboxclient.add_relay(relay)
        except:
            print("[" + dvm_config.NIP89.NAME + "] " + relay + " couldn't be added to outbox relays")
#
    await outboxclient.connect()
    try:
        print("Connected, sending event")
        event_id = await outboxclient.send_event(event)
        print(event_id.output)
    except Exception as e:
        event_id = None
        print(e)

    # 5. Fallback, if we couldn't send the event to any relay, we try to send to generic relays instead.
    if event_id is None:
        for relay in relays:
            await outboxclient.remove_relay(relay)


        relays = await get_main_relays(event, client, dvm_config)
        for relay in relays:
            opts = RelayOptions().ping(False)
            await outboxclient.add_relay_with_opts(relay, opts)
        try:
            await outboxclient.connect()
            event_id = await outboxclient.send_event(event)
        except Exception as e:
            # Love yourself then.
            event_id = None
            print(e)


    await outboxclient.shutdown()
    return event_id




async def send_event(event: Event, client: Client, dvm_config, blastr=False):
    try:
        relays = []
        for tag in event.tags():
            if tag.as_vec()[0] == 'relays':
                for index, param in enumerate(tag.as_vec()):
                    if index != 0:
                        if tag.as_vec()[index].rstrip("/") not in dvm_config.AVOID_PAID_OUTBOX_RELAY_LIST:
                            try:
                                relays.append(tag.as_vec()[index])
                            except:
                                print("[" + dvm_config.NIP89.NAME + "] " + tag.as_vec()[
                                    index] + " couldn't be added to outbox relays")
                break

        for relay in relays:
            if relay not in dvm_config.RELAY_LIST:
                await client.add_relay(relay)

        #if blastr:
        #    client.add_relay("wss://nostr.mutinywallet.com")
        try:
            event_id = await client.send_event(event)
            #event_id = output.id
        except Exception as e:
            print(e)
            event_id = None

        for relay in relays:
            if relay not in dvm_config.RELAY_LIST:
                await client.remove_relay(relay)
        #if blastr:
        #    client.remove_relay("wss://nostr.mutinywallet.com")
        return event_id
    except Exception as e:
        print(e)


def check_and_decrypt_tags(event, dvm_config):
    try:

        is_encrypted = False
        p = ""
        for tag in event.tags():
            if tag.as_vec()[0] == 'encrypted':
                is_encrypted = True
            elif tag.as_vec()[0] == 'p':
                p = tag.as_vec()[1]

        if is_encrypted:
            if p != dvm_config.PUBLIC_KEY:
                print("[" + dvm_config.NIP89.NAME + "] Task encrypted and not addressed to this DVM, "
                                                    "skipping..")
                return None

            elif p == dvm_config.PUBLIC_KEY:
                tags_str = nip04_decrypt(Keys.parse(dvm_config.PRIVATE_KEY).secret_key(),
                                         event.author(), event.content())
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


def check_and_decrypt_own_tags(event, dvm_config):
    try:
        is_encrypted = False
        p = ""
        for tag in event.tags():
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
                tags_str = nip04_decrypt(Keys.parse(dvm_config.PRIVATE_KEY).secret_key(),
                                         PublicKey.from_hex(p), event.content())
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


async def update_profile(dvm_config, client, lud16=""):
    keys = Keys.parse(dvm_config.PRIVATE_KEY)
    try:
        nip89content = json.loads(dvm_config.NIP89.CONTENT)
        name = nip89content.get("name")
        about = nip89content.get("about")
        image = nip89content.get("image")

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
    await client.set_metadata(metadata)


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
