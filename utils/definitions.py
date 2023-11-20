import os
from dataclasses import dataclass

from nostr_sdk import Event

from utils import env

NEW_USER_BALANCE: int = 250  # Free credits for new users

RELAY_LIST = ["wss://relay.damus.io", "wss://nostr-pub.wellorder.net", "wss://nos.lol", "wss://nostr.wine",
              "wss://relay.nostfiles.dev", "wss://nostr.mom", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg",
              "wss://relay.f7z.io"]


class EventDefinitions:
    KIND_DM: int = 4
    KIND_ZAP: int = 9735
    KIND_NIP94_METADATA: int = 1063
    KIND_FEEDBACK: int = 7000
    KIND_NIP90_EXTRACT_TEXT = 5000
    KIND_NIP90_RESULT_EXTRACT_TEXT = 6000
    KIND_NIP90_SUMMARIZE_TEXT = 5001
    KIND_NIP90_RESULT_SUMMARIZE_TEXT = 6001
    KIND_NIP90_TRANSLATE_TEXT = 5002
    KIND_NIP90_RESULT_TRANSLATE_TEXT = 6002
    KIND_NIP90_GENERATE_IMAGE = 5100
    KIND_NIP90_RESULT_GENERATE_IMAGE = 6100
    KIND_NIP90_RECOMMEND_NOTES = 65006
    KIND_NIP90_RESULT_RECOMMEND_NOTES = 65001
    KIND_NIP90_RECOMMEND_USERS = 65007
    KIND_NIP90_RESULT_RECOMMEND_USERS = 65001
    KIND_NIP90_CONVERT_VIDEO = 5200
    KIND_NIP90_RESULT_CONVERT_VIDEO = 6200
    KIND_NIP90_GENERIC = 5999
    KIND_NIP90_RESULT_GENERIC = 6999
    ANY_RESULT = [KIND_NIP90_RESULT_EXTRACT_TEXT,
                  KIND_NIP90_RESULT_SUMMARIZE_TEXT,
                  KIND_NIP90_RESULT_TRANSLATE_TEXT,
                  KIND_NIP90_RESULT_GENERATE_IMAGE,
                  KIND_NIP90_RESULT_RECOMMEND_NOTES,
                  KIND_NIP90_RESULT_RECOMMEND_USERS,
                  KIND_NIP90_RESULT_CONVERT_VIDEO,
                  KIND_NIP90_RESULT_GENERIC]


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

    SHOWRESULTBEFOREPAYMENT: bool = True  # if this is true show results even when not paid right after autoprocess


    NIP89s: list = []


@dataclass
class JobToWatch:
    event_id: str
    timestamp: int
    is_paid: bool
    amount: int
    status: str
    result: str
    is_processed: bool
    bolt11: str
    payment_hash: str
    expires: int
    from_bot: bool


@dataclass
class RequiredJobToWatch:
    event: Event
    timestamp: int
