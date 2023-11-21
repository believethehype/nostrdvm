from nostr_sdk import Tag, Keys, EventBuilder
from utils.nostr_utils import send_event

class NIP89Announcement:
    name: str
    kind: int
    dtag: str
    pk: str
    content: str

def nip89_announce_tasks(dvmconfig):
    k_tag = Tag.parse(["k", str(dvmconfig.NIP89.kind)])
    d_tag = Tag.parse(["d", dvmconfig.NIP89.dtag])
    keys = Keys.from_sk_str(dvmconfig.NIP89.pk)
    content = dvmconfig.NIP89.content
    event = EventBuilder(31990, content, [k_tag, d_tag]).to_event(keys)
    send_event(event, key=keys)
    print("Announced NIP 89 for " + dvmconfig.NIP89.name)