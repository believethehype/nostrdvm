from nostr_sdk import Tag, Keys, EventBuilder
from utils.nostr_utils import send_event

class NIP89Announcement:
    kind: int
    dtag: str
    pk: str
    content: str

def nip89_announce_tasks(dvmconfig):
    for nip89 in dvmconfig.NIP89s:
        k_tag = Tag.parse(["k", str(nip89.kind)])
        d_tag = Tag.parse(["d", nip89.dtag])
        keys = Keys.from_sk_str(nip89.pk)
        content = nip89.content
        event = EventBuilder(31990, content, [k_tag, d_tag]).to_event(keys)
        send_event(event, key=keys)

    print("Announced NIP 89")