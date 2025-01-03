import os

from nostr_sdk import Keys, LogLevel

from nostr_dvm.utils import outbox_utils
from nostr_dvm.utils.nip88_utils import NIP88Config
from nostr_dvm.utils.nip89_utils import NIP89Config
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.zap_utils import check_and_set_ln_bits_keys


class DVMConfig:
    SUPPORTED_DVMS = []
    PRIVATE_KEY: str = ""
    PUBLIC_KEY: str = ""
    FIX_COST: float = None
    PER_UNIT_COST: float = None

    # The relays the dvm is operating on and announces in its inbox relays
    RELAY_LIST = ["wss://relay.nostrdvm.com",
                  ]
    # DBs to sync with
    SYNC_DB_RELAY_LIST = ["wss://relay.damus.io",
                          "wss://nostr.oxtr.dev",
                          "wss://relay.primal.net",
                         ]
    # announce inbox relays, dm relays and NIP89 announcement to
    ANNOUNCE_RELAY_LIST = ["wss://relay.primal.net",
                  "wss://relay.damus.io",
                  "wss://nostr.oxtr.dev", "wss://relay.nostrdvm.com"
                  ]

    # Straight Censorship (reply guy spam)
    WOT_FILTERING = False
    WOT_BASED_ON_NPUBS = ["99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64",
                          "460c25e682fda7832b52d1f22d3d22b3176d972f60dcdc3212ed8c92ef85065c",
                          "3f770d65d3a764a9c5cb503ae123e62ec7598ad035d836e2a810f3877a745b24"
                          ]
    WOT_DEPTH = 2

    AVOID_OUTBOX_RELAY_LIST = outbox_utils.AVOID_OUTBOX_RELAY_LIST
    # If a DVM has a paid subscription, overwrite list without the paid one.

    DELETE_ANNOUNCEMENT_ON_SHUTDOWN = True
    # remove the announcement when the DVM stops. Recommended.
    # Make sure to set admin_utils.REBROADCAST_NIP89 = True on start.

    DELETE_ANNOUNCEMENT_ON_SHUTDOWN_POW = False
    RELAY_TIMEOUT = 5
    RELAY_LONG_TIMEOUT = 30
    EXTERNAL_POST_PROCESS_TYPE = 0  # Leave this on None, except the DVM is external
    LNBITS_INVOICE_KEY = ''  # Will all automatically generated by default, or read from .env
    LNBITS_ADMIN_KEY = ''  # In order to pay invoices, e.g. from the bot to DVMs, or reimburse users.
    LNBITS_URL = 'https://lnbits.com'
    PROVIDE_INVOICE = True
    LN_ADDRESS = ''
    SCRIPT = ''
    IDENTIFIER = ''
    USE_OWN_VENV = False  # Make an own venv for each dvm's process function.Disable if you want to install packages into main venv. Only recommended if you dont want to run dvms with different dependency versions
    DB: str
    DATABASE = None
    NEW_USER_BALANCE: int = 0  # Free credits for new users
    SUBSCRIPTION_MANAGEMENT = 'https://noogle.lol/discovery'
    NIP88: NIP88Config = NIP88Config()
    NIP89: NIP89Config = NIP89Config()
    SEND_FEEDBACK_EVENTS = True
    SHOW_RESULT_BEFORE_PAYMENT: bool = False  # if this is true show results even when not paid right after autoprocess
    SCHEDULE_UPDATES_SECONDS = 0
    UPDATE_DATABASE = True  # DVMs that use a db manage their db by default. If a dvm should use the same db as another DVM, deactive it for those who do.
    CUSTOM_PROCESSING_MESSAGE = None
    LOGLEVEL = LogLevel.INFO
    KIND = None

    DVM_KEY = None
    CHATBOT = None

    # Make sure you have the cashu library installed and built correctly on your system, before enableing nutzaps for a DVM
    # this is not installed by default
    # pip install cashu. You might run into trouble with building secp256k1
    # More info see here: https://github.com/cashubtc/nutshell

    ENABLE_NUTZAP = False
    NUTZAP_RELAYS = ["wss://relay.nostr.net"]
    NUZAP_MINTS = ["https://mint.gwoq.com"]
    ENABLE_AUTO_MELT = False
    AUTO_MELT_AMOUNT = 1000
    REANNOUNCE_MINTS = True


def build_default_config(identifier):
    dvm_config = DVMConfig()
    dvm_config.PRIVATE_KEY = check_and_set_private_key(identifier)
    dvm_config.IDENTIFIER = identifier
    npub = Keys.parse(dvm_config.PRIVATE_KEY).public_key().to_bech32()
    invoice_key, admin_key, wallet_id, lnaddress = check_and_set_ln_bits_keys(identifier, npub)
    dvm_config.LNBITS_INVOICE_KEY = invoice_key
    dvm_config.LNBITS_ADMIN_KEY = admin_key  # The dvm might pay failed jobs back
    dvm_config.LNBITS_URL = os.getenv("LNBITS_HOST")
    dvm_config.LN_ADDRESS = lnaddress
    return dvm_config
