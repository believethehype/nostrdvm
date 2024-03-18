import os
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import dotenv
from nostr_sdk import Tag, Keys, EventBuilder, Filter, Alphabet, PublicKey, Client, EventId, SingleLetterTag

from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.nostr_utils import send_event


class NIP89Config:
    DTAG: str = ""
    NAME: str = ""
    KIND: int = None
    PK: str = ""
    CONTENT: str = ""


def nip89_create_d_tag(name, pubkey, image):
    key_str = str(name + image + pubkey)
    d_tag = sha256(key_str.encode('utf-8')).hexdigest()[:16]
    return d_tag


def nip89_announce_tasks(dvm_config, client):
    k_tag = Tag.parse(["k", str(dvm_config.NIP89.KIND.as_u64())])
    d_tag = Tag.parse(["d", dvm_config.NIP89.DTAG])
    keys = Keys.parse(dvm_config.NIP89.PK)
    content = dvm_config.NIP89.CONTENT
    event = EventBuilder(EventDefinitions.KIND_ANNOUNCEMENT, content, [k_tag, d_tag]).to_event(keys)
    send_event(event, client=client, dvm_config=dvm_config)
    print("Announced NIP 89 for " + dvm_config.NIP89.NAME)


def fetch_nip89_parameters_for_deletion(keys, eventid, client, dvmconfig):
    idfilter = Filter().id(EventId.from_hex(eventid)).limit(1)
    nip89events = client.get_events_of([idfilter], timedelta(seconds=dvmconfig.RELAY_TIMEOUT))
    d_tag = ""
    if len(nip89events) == 0:
        print("Event not found. Potentially gone.")

    for event in nip89events:
        print(event.as_json())
        for tag in event.tags():
            if tag.as_vec()[0] == "d":
                d_tag = tag.as_vec()[1]
        if d_tag == "":
            print("No dtag found")
            return

        if event.author().to_hex() == keys.public_key().to_hex():
            nip89_delete_announcement(event.id().to_hex(), keys, d_tag, client, dvmconfig)
            print("NIP89 announcement deleted from known relays!")
        else:
            print("Privatekey does not belong to event")


def nip89_delete_announcement(eid: str, keys: Keys, dtag: str, client: Client, config):
    e_tag = Tag.parse(["e", eid])
    a_tag = Tag.parse(["a", str(EventDefinitions.KIND_ANNOUNCEMENT) + ":" + keys.public_key().to_hex() + ":" + dtag])
    event = EventBuilder(5, "", [e_tag, a_tag]).to_event(keys)
    send_event(event, client, config)


def nip89_fetch_all_dvms(client):
    ktags = []
    for i in range(5000, 5999):
        ktags.append(str(i))

    filter = Filter().kind(EventDefinitions.KIND_ANNOUNCEMENT).custom_tag(SingleLetterTag.lowercase(Alphabet.K), ktags)
    events = client.get_events_of([filter], timedelta(seconds=5))
    for event in events:
        print(event.as_json())


def nip89_fetch_events_pubkey(client, pubkey, kind):
    ktags = [str(kind)]
    # for i in range(5000, 5999):
    #     ktags.append(str(i))
    nip89filter = (Filter().kind(EventDefinitions.KIND_ANNOUNCEMENT).author(PublicKey.from_hex(pubkey)).
                   custom_tag(SingleLetterTag.lowercase(Alphabet.K), ktags))
    events = client.get_events_of([nip89filter], timedelta(seconds=2))

    dvms = {}
    for event in events:
        if dvms.get(event.author().to_hex()):
            if dvms.get(event.author().to_hex()).created_at().as_secs() < event.created_at().as_secs():
                dvms[event.author().to_hex()] = event
        else:
            dvms[event.author().to_hex()] = event

    # should be one element of the kind now
    for dvm in dvms:
        return dvms[dvm].content()


def check_and_set_d_tag(identifier, name, pk, imageurl):
    if not os.getenv("NIP89_DTAG_" + identifier.upper()):
        new_dtag = nip89_create_d_tag(name, Keys.parse(pk).public_key().to_hex(),
                                      imageurl)
        nip89_add_dtag_to_env_file("NIP89_DTAG_" + identifier.upper(), new_dtag)
        print("Some new dtag:" + new_dtag)
        return new_dtag
    else:
        return os.getenv("NIP89_DTAG_" + identifier.upper())


def nip89_add_dtag_to_env_file(dtag, oskey):
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
        dotenv.set_key(env_path, dtag, oskey)
