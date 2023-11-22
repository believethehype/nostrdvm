import os

from utils import env
from utils.nip89_utils import NIP89Announcement


class DVMConfig:
    SUPPORTED_TASKS = []
    PRIVATE_KEY: str = os.getenv(env.NOSTR_PRIVATE_KEY)

    RELAY_LIST = ["wss://relay.damus.io", "wss://nostr-pub.wellorder.net", "wss://nos.lol", "wss://nostr.wine",
                  "wss://relay.nostfiles.dev", "wss://nostr.mom", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg",
                  "wss://relay.f7z.io"]

    RELAY_TIMEOUT = 5
    LNBITS_INVOICE_KEY = ''
    LNBITS_URL = 'https://lnbits.com'
    DB: str
    NIP89: NIP89Announcement

    REQUIRES_NIP05: bool = False
    SHOW_RESULT_BEFORE_PAYMENT: bool = True  # if this is true show results even when not paid right after autoprocess



