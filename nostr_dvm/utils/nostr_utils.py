import json
import os
from datetime import timedelta
from pathlib import Path
from typing import List

import dotenv
from nostr_sdk import Filter, Client, Alphabet, EventId, Event, PublicKey, Tag, Keys, nip04_decrypt, Metadata, Options, \
    Nip19Event, SingleLetterTag


def get_event_by_id(event_id: str, client: Client, config=None) -> Event | None:
    split = event_id.split(":")
    if len(split) == 3:
        pk = PublicKey.from_hex(split[1])
        id_filter = Filter().author(pk).custom_tag(SingleLetterTag.lowercase(Alphabet.D), [split[2]])
        events = client.get_events_of([id_filter], timedelta(seconds=config.RELAY_TIMEOUT))
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
        events = client.get_events_of([id_filter], timedelta(seconds=config.RELAY_TIMEOUT))
    if len(events) > 0:

        return events[0]
    else:
        return None


def get_events_by_ids(event_ids, client: Client, config=None) -> List | None:
    search_ids = []
    for event_id in event_ids:
        split = event_id.split(":")
        if len(split) == 3:
            pk = PublicKey.from_hex(split[1])
            id_filter = Filter().author(pk).custom_tag(SingleLetterTag.lowercase(Alphabet.D), [split[2]])
            events = client.get_events_of([id_filter], timedelta(seconds=config.RELAY_TIMEOUT))
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
    events = client.get_events_of([id_filter], timedelta(seconds=config.RELAY_TIMEOUT))
    if len(events) > 0:

        return events
    else:
        return None


def get_events_by_id(event_ids: list, client: Client, config=None) -> list[Event] | None:
    id_filter = Filter().ids(event_ids)
    events = client.get_events_of([id_filter], timedelta(seconds=config.RELAY_TIMEOUT))
    if len(events) > 0:
        return events
    else:
        return None


def get_referenced_event_by_id(event_id, client, dvm_config, kinds) -> Event | None:
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

    events = client.get_events_of([job_id_filter], timedelta(seconds=dvm_config.RELAY_TIMEOUT))

    if len(events) > 0:
        return events[0]
    else:
        return None


def send_event(event: Event, client: Client, dvm_config) -> EventId:
    try:
        relays = []

        for tag in event.tags():
            if tag.as_vec()[0] == 'relays':
                for index, param in enumerate(tag.as_vec()):
                    if index != 0:
                        relays.append(tag.as_vec()[index])

        for relay in relays:
            if relay not in dvm_config.RELAY_LIST:
                client.add_relay(relay)

        event_id = client.send_event(event)

        for relay in relays:
            if relay not in dvm_config.RELAY_LIST:
                client.remove_relay(relay)

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


def update_profile(dvm_config, client, lud16=""):
    keys = Keys.parse(dvm_config.PRIVATE_KEY)
    nip89content = json.loads(dvm_config.NIP89.CONTENT)
    if nip89content.get("name"):
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

        print(f"Setting profile metadata for {keys.public_key().to_bech32()}...")
        print(metadata.as_json())
        client.set_metadata(metadata)


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
