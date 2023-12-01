from utils.nip89_utils import NIP89Config
from utils.output_utils import PostProcessFunctionType


class DVMConfig:
    SUPPORTED_DVMS= []
    PRIVATE_KEY: str = ""
    PUBLIC_KEY: str = ""
    FIX_COST: float = None
    PER_UNIT_COST: float = None

    RELAY_LIST = ["wss://relay.damus.io", "wss://nostr-pub.wellorder.net", "wss://nos.lol", "wss://nostr.wine",
                  "wss://relay.nostfiles.dev", "wss://nostr.mom", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg",
                  "wss://relay.f7z.io", "wss://pablof7z.nostr1.com", "wss://purplepag.es", "wss://nos.lol",
                  "wss://relay.snort.social", "wss://offchain.pub/",
                  "wss://nostr-pub.wellorder.net"]

    RELAY_TIMEOUT = 3
    EXTERNAL_POST_PROCESS_TYPE = PostProcessFunctionType.NONE  # Leave this on None, except the DVM is external
    LNBITS_INVOICE_KEY = ''
    LNBITS_ADMIN_KEY = ''  # In order to pay invoices, e.g. from the bot to DVMs, or reimburse users.
    LNBITS_URL = 'https://lnbits.com'
    DB: str
    NEW_USER_BALANCE: int = 0  # Free credits for new users
    NIP89: NIP89Config
    SHOW_RESULT_BEFORE_PAYMENT: bool = False  # if this is true show results even when not paid right after autoprocess



