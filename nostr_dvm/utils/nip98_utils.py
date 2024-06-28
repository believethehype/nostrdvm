import base64
import hashlib
from nostr_sdk import EventBuilder, Tag, Kind, Keys


def sha256sum(filename):
    with open(filename, 'rb', buffering=0) as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

async def generate_nip98_header(pkeys_hex, url="", kind="POST", filepath=""):
    keys = Keys.parse(pkeys_hex)
    utag = Tag.parse(["u", url])
    methodtag = Tag.parse(["method", kind])
    tags = [utag, methodtag]
    if kind == "POST":
        payloadtag = Tag.parse(["payload", sha256sum(filepath)])
        tags.append(payloadtag)
    event = EventBuilder(Kind(27235), "", tags).to_event(keys)

    encoded_nip98_event = base64.b64encode(event.as_json().encode('utf-8')).decode('utf-8')

    return "Nostr " + encoded_nip98_event

