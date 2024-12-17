import base64
import hashlib

from nostr_sdk import EventBuilder, Tag, Kind, Keys


def sha256sum(filename):
    with open(filename, 'rb', buffering=0) as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


async def generate_nip98_header(pkeys_hex, url="", kind="POST", filepath=""):
    """
    Generates a NIP-98 authentication header for a Nostr-based server. This header is
    intended to be used for authenticating requests by signing events with specific
    keys and including necessary metadata tags. The resulting header is encoded into
    a format suitable for HTTP authorization headers.

    :param pkeys_hex: The private keys in hexadecimal format, used for signing the
        event.
    :type pkeys_hex: str
    :param url: The URL that the NIP-98 header should apply to. Defaults to an empty
        string.
    :type url: str, optional
    :param kind: The HTTP method type for which the header is generated (e.g.,
        "POST"). Defaults to "POST".
    :type kind: str, optional
    :param filepath: The path to a file whose content will be hashed and included in
        the payload as a tag if the method is "POST". Defaults to an empty string.
    :type filepath: str, optional
    :return: The generated NIP-98 header in the format "Nostr <Base64 encoded event>".
    :rtype: str
    """
    keys = Keys.parse(pkeys_hex)
    utag = Tag.parse(["u", url])
    methodtag = Tag.parse(["method", kind])
    tags = [utag, methodtag]
    if kind == "POST":
        payloadtag = Tag.parse(["payload", sha256sum(filepath)])
        tags.append(payloadtag)
    eb = EventBuilder(Kind(27235), "").tags(tags)
    event  = eb.sign_with_keys(keys)

    encoded_nip98_event = base64.b64encode(event.as_json().encode('utf-8')).decode('utf-8')

    return "Nostr " + encoded_nip98_event
