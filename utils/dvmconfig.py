import os

from utils import env


class DVMConfig:
    SUPPORTED_TASKS = []
    PRIVATE_KEY: str = os.getenv(env.NOSTR_PRIVATE_KEY)

    RELAY_LIST = ["wss://relay.damus.io", "wss://nostr-pub.wellorder.net", "wss://nos.lol", "wss://nostr.wine",
                  "wss://relay.nostfiles.dev", "wss://nostr.mom", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg",
                  "wss://relay.f7z.io"]
    RELAY_TIMEOUT = 5
    LNBITS_INVOICE_KEY = ''
    LNBITS_URL = 'https://lnbits.com'
    REQUIRES_NIP05: bool = False
    DB: str

    SHOWRESULTBEFOREPAYMENT: bool = True  # if this is true show results even when not paid right after autoprocess


    NIP89s: list = []
