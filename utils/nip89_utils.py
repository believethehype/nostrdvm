from datetime import timedelta

from nostr_sdk import Tag, Keys, EventBuilder, Filter, Alphabet, PublicKey, Event

from utils.definitions import EventDefinitions
from utils.nostr_utils import send_event


class NIP89Config:
    DTAG: str = ""
    NAME: str = ""
    KIND: int = None
    PK: str = ""
    CONTENT: str = ""


def nip89_announce_tasks(dvm_config, client):
    k_tag = Tag.parse(["k", str(dvm_config.NIP89.kind)])
    d_tag = Tag.parse(["d", dvm_config.NIP89.dtag])
    keys = Keys.from_sk_str(dvm_config.NIP89.pk)
    content = dvm_config.NIP89.content
    event = EventBuilder(EventDefinitions.KIND_ANNOUNCEMENT, content, [k_tag, d_tag]).to_event(keys)
    send_event(event, client=client, dvm_config=dvm_config)
    print("Announced NIP 89 for " + dvm_config.NIP89.NAME)


def nip89_fetch_all_dvms(client):
    ktags = []
    for i in range(5000, 5999):
        ktags.append(str(i))

    filter = Filter().kind(EventDefinitions.KIND_ANNOUNCEMENT).custom_tag(Alphabet.K, ktags)
    events = client.get_events_of([filter], timedelta(seconds=5))
    for event in events:
        print(event.as_json())


def nip89_fetch_events_pubkey(client, pubkey, kind):
    ktags = [str(kind)]
    # for i in range(5000, 5999):
    #     ktags.append(str(i))
    nip89filter = (Filter().kind(EventDefinitions.KIND_ANNOUNCEMENT).author(PublicKey.from_hex(pubkey)).
                   custom_tag(Alphabet.K, ktags))
    events = client.get_events_of([nip89filter], timedelta(seconds=2))

    dvms = {}
    for event in events:
        if dvms.get(event.pubkey().to_hex()):
            if dvms.get(event.pubkey().to_hex()).created_at().as_secs() < event.created_at().as_secs():
                dvms[event.pubkey().to_hex()] = event
        else:
            dvms[event.pubkey().to_hex()] = event

    # should be one element of the kind now
    for dvm in dvms:
        return dvms[dvm].content()
