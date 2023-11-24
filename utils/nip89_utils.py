from nostr_sdk import Tag, Keys, EventBuilder

from utils.nostr_utils import send_event


class NIP89Announcement:
    name: str
    kind: int
    dtag: str
    pk: str
    content: str


class NIP89Config:
    DTAG: str
    CONTENT: str


def nip89_announce_tasks(dvm_config, client):
    k_tag = Tag.parse(["k", str(dvm_config.NIP89.kind)])
    d_tag = Tag.parse(["d", dvm_config.NIP89.dtag])
    keys = Keys.from_sk_str(dvm_config.NIP89.pk)
    content = dvm_config.NIP89.content
    event = EventBuilder(31990, content, [k_tag, d_tag]).to_event(keys)
    send_event(event, client=client, dvm_config=dvm_config)
    print("Announced NIP 89 for " + dvm_config.NIP89.name)
