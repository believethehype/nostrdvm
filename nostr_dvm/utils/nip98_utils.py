import base64
import hashlib
from nostr_sdk import EventBuilder, Tag, Kind, Keys


def sha256sum(filename):
    with open(filename, 'rb', buffering=0) as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

async def generate_nip98_header(filepath, dvm_config):
    keys = Keys.parse(dvm_config.NIP89.PK)
    utag = Tag.parse(["u", "https://nostr.build/api/v2/upload/files"])
    methodtag = Tag.parse(["method", "POST"])
    payloadtag = Tag.parse(["payload", sha256sum(filepath)])
    event = EventBuilder(Kind(27235), "", [utag, methodtag, payloadtag]).to_event(keys)

    encoded_nip98_event = base64.b64encode(event.as_json().encode('utf-8')).decode('utf-8')

    return "Nostr " + encoded_nip98_event

