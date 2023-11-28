import os

from nostr_sdk import Keys

from utils.nip89_utils import NIP89Announcement


class DVMConfig:
    SUPPORTED_DVMS= []
    PRIVATE_KEY: str = ""
    PUBLIC_KEY: str = ""
    FIX_COST: float = None
    PER_UNIT_COST: float = None

    RELAY_LIST = ["wss://relay.damus.io", "wss://nostr-pub.wellorder.net", "wss://nos.lol", "wss://nostr.wine",
                  "wss://relay.nostfiles.dev", "wss://nostr.mom", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg",
                  "wss://relay.f7z.io"]

    RELAY_TIMEOUT = 3
    LNBITS_INVOICE_KEY = ''
    LNBITS_ADMIN_KEY = ''  # In order to pay invoices, e.g. from the bot to DVMs, or reimburse users.
    LNBITS_URL = 'https://lnbits.com'
    DB: str
    NEW_USER_BALANCE: int = 250  # Free credits for new users
    NIP89: NIP89Announcement
    SHOW_RESULT_BEFORE_PAYMENT: bool = False  # if this is true show results even when not paid right after autoprocess



