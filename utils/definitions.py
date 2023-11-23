import os
from dataclasses import dataclass

from nostr_sdk import Event

NEW_USER_BALANCE: int = 250  # Free credits for new users


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
