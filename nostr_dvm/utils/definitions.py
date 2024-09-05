import os
from dataclasses import dataclass
from datetime import timedelta

from nostr_sdk import Event, Kind, EventSource


class EventDefinitions:
    KIND_PROFILE = Kind(0)
    KIND_NOTE = Kind(1)
    KIND_FOLLOW_LIST = Kind(3)
    KIND_DM = Kind(4)
    KIND_DELETION = Kind(5)
    KIND_REPOST = Kind(6)
    KIND_REACTION = Kind(7)
    KIND_NIP94_METADATA = Kind(1063)
    KIND_NIP93_GALLERYENTRY = Kind(1163)
    KIND_NIP90_EXTRACT_TEXT = Kind(5000)
    KIND_NIP90_RESULT_EXTRACT_TEXT = Kind(6000)
    KIND_NIP90_SUMMARIZE_TEXT = Kind(5001)
    KIND_NIP90_RESULT_SUMMARIZE_TEXT = Kind(6001)
    KIND_NIP90_TRANSLATE_TEXT = Kind(5002)
    KIND_NIP90_RESULT_TRANSLATE_TEXT = Kind(6002)
    KIND_NIP90_GENERATE_TEXT = Kind(5050)
    KIND_NIP90_RESULT_GENERATE_TEXT = Kind(6050)
    KIND_NIP90_GENERATE_IMAGE = Kind(5100)
    KIND_NIP90_RESULT_GENERATE_IMAGE = Kind(6100)
    KIND_NIP90_CONVERT_VIDEO = Kind(5200)
    KIND_NIP90_RESULT_CONVERT_VIDEO = Kind(6200)
    KIND_NIP90_GENERATE_VIDEO = Kind(5202)
    KIND_NIP90_RESULT_GENERATE_VIDEO = Kind(6202)
    KIND_NIP90_TEXT_TO_SPEECH = Kind(5250)
    KIND_NIP90_RESULT_TEXT_TO_SPEECH = Kind(6250)
    KIND_NIP90_GENERATE_MUSIC = Kind(5251)
    KIND_NIP90_RESULT_GENERATE_MUSIC = Kind(5651)
    KIND_NIP90_CONTENT_DISCOVERY = Kind(5300)
    KIND_NIP90_RESULT_CONTENT_DISCOVERY = Kind(6300)
    KIND_NIP90_PEOPLE_DISCOVERY = Kind(5301)
    KIND_NIP90_RESULT_PEOPLE_DISCOVERY = Kind(6301)
    KIND_NIP90_CONTENT_SEARCH = Kind(5302)
    KIND_NIP90_RESULTS_CONTENT_SEARCH = Kind(6302)
    KIND_NIP90_USER_SEARCH = Kind(5303)
    KIND_NIP90_RESULTS_USER_SEARCH = Kind(6303)
    KIND_NIP90_VISUAL_DISCOVERY = Kind(5304)
    KIND_NIP90_RESULT_VISUAL_DISCOVERY = Kind(6304)
    KIND_NIP90_DVM_SUBSCRIPTION = Kind(5906)
    KIND_NIP90_RESULT_DVM_SUBSCRIPTION = Kind(6906)

    KIND_NIP90_GENERIC = Kind(5999)
    KIND_NIP90_RESULT_GENERIC = Kind(6999)
    KIND_FEEDBACK = Kind(7000)
    KIND_NIP88_SUBSCRIBE_EVENT = Kind(7001)
    KIND_NIP88_STOP_SUBSCRIPTION_EVENT = Kind(7002)
    KIND_NIP88_PAYMENT_RECIPE = Kind(7003)
    KIND_NIP60_NUT_PROOF = Kind(7375)
    KIND_NIP60_NUT_HISTORY = Kind(7376)
    KIND_NIP61_NUT_ZAP = Kind(9321)
    KIND_ZAP = Kind(9735)
    KIND_RELAY_ANNOUNCEMENT = Kind(10002)
    KIND_ANNOUNCEMENT = Kind(31990)
    KIND_WIKI = Kind(30818)
    KIND_LONGFORM = Kind(30023)
    KIND_NIP88_TIER_EVENT = Kind(37001)
    KIND_NUT_WALLET = Kind(37375)


    ANY_RESULT = [KIND_NIP90_RESULT_EXTRACT_TEXT,
                  KIND_NIP90_RESULT_SUMMARIZE_TEXT,
                  KIND_NIP90_RESULT_TRANSLATE_TEXT,
                  KIND_NIP90_RESULT_GENERATE_TEXT,
                  KIND_NIP90_RESULT_GENERATE_IMAGE,
                  KIND_NIP90_CONTENT_DISCOVERY,
                  KIND_NIP90_PEOPLE_DISCOVERY,
                  KIND_NIP90_RESULT_CONVERT_VIDEO,
                  KIND_NIP90_RESULT_CONTENT_DISCOVERY,
                  KIND_NIP90_RESULT_PEOPLE_DISCOVERY,
                  KIND_NIP90_RESULT_GENERATE_VIDEO,
                  KIND_NIP90_RESULT_GENERIC]


@dataclass
class JobToWatch:
    event: str
    timestamp: int
    is_paid: bool
    amount: int
    status: str
    result: str
    is_processed: bool
    bolt11: str
    payment_hash: str
    expires: int


@dataclass
class RequiredJobToWatch:
    event: Event
    timestamp: int

@dataclass
class InvoiceToWatch:
    sender: str
    bolt11: str
    amount: int
    payment_hash: str
    is_paid: bool
    expires: int


relay_timeout = EventSource.relays(timedelta(seconds=5))
relay_timeout_long = EventSource.relays(timedelta(seconds=10))