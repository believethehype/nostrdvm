import math
from collections import defaultdict
from datetime import timedelta

from nostr_sdk import ClientBuilder, Filter, Kind, Keys, NostrLmdb, PublicKey, RelayUrl, \
    ReqTarget, SecretKey, SignerAuthenticator, Timestamp

from nostr_dvm.utils.discovery_utils import sync_discovery_database
from nostr_dvm.utils.zap_utils import parse_amount_from_bolt11_invoice

PROFILE_KINDS = [1, 6, 7, 9735]

RANKING_PARAMS = {
    "action_weights": {"reaction": 0.5, "repost": 1.0, "reply": 13.5},
    "zap_base": 1.0,
    "base_floor": 0.1,
    "affinity_cap": 8.0,
    "credibility_denominator": 4.0,
    "recency_half_life_hours": 24.0,
    "oon_discount": 0.5,
    "boost_threshold": 5.0,
    "boost_factor": 1.2,
    "diversity_decay": 0.7,
    "diversity_floor": 0.1,
    "candidate_age_hours": 48,
    "in_network_cap": 200,
    "oon_cap": 300,
    "oon_overlap_threshold": 3,
}


def zap_weight(sats: int) -> float:
    return RANKING_PARAMS["zap_base"] + math.log10(max(sats, 1))


def event_action_weight(event) -> float:
    kind = event.kind().as_u16()
    if kind == 7:
        return RANKING_PARAMS["action_weights"]["reaction"]
    if kind == 6:
        return RANKING_PARAMS["action_weights"]["repost"]
    if kind == 1:
        return RANKING_PARAMS["action_weights"]["reply"]
    if kind == 9735:
        sats = 0
        for tag in event.tags():
            vec = tag.to_vec()
            if vec[0] == "bolt11" and len(vec) > 1:
                try:
                    sats = parse_amount_from_bolt11_invoice(vec[1])
                except Exception:
                    sats = 0
                break
        return zap_weight(sats)
    return 0.0


def note_engagement_base(events: list, note_author_hex: str, exclude_self: bool = True) -> float:
    total = 0.0
    for event in events:
        if exclude_self and event.author().to_hex() == note_author_hex:
            continue
        total += event_action_weight(event)
    return RANKING_PARAMS["base_floor"] + total


def recency_factor(created_at_secs: int, now_secs: int) -> float:
    age_hours = max(0.0, (now_secs - created_at_secs) / 3600.0)
    return 0.5 ** (age_hours / RANKING_PARAMS["recency_half_life_hours"])


def affinity(author_hex: str, actions_by_author: dict) -> float:
    return min(RANKING_PARAMS["affinity_cap"],
               1.0 + math.log(1.0 + actions_by_author.get(author_hex, 0.0)))


def credibility(distinct_engagers: int) -> float:
    return min(1.0, math.log(1.0 + max(0, distinct_engagers)) / RANKING_PARAMS["credibility_denominator"])


def new_author_boost(author_total_weighted_engagement: float) -> float:
    return RANKING_PARAMS["boost_factor"] if author_total_weighted_engagement < RANKING_PARAMS["boost_threshold"] else 1.0


def oon_factor(author_hex: str, follows: set) -> float:
    return RANKING_PARAMS["oon_discount"] if author_hex not in follows else 1.0


def score_note(base: float, affinity_value: float, credibility_value: float,
               recency: float, oon: float, boost: float) -> float:
    return base * affinity_value * credibility_value * recency * oon * boost


def apply_author_diversity(ranked: list, max_results: int) -> list:
    counts = defaultdict(int)
    adjusted = []
    for event, score in ranked:
        k = counts[event.author().to_hex()]
        adjusted.append((event, max(RANKING_PARAMS["diversity_floor"],
                                    score * (RANKING_PARAMS["diversity_decay"] ** k))))
        counts[event.author().to_hex()] += 1
    adjusted.sort(key=lambda pair: -pair[1])
    return adjusted[:max_results]


def top_level(event) -> bool:
    for tag in event.tags():
        if tag.to_vec()[0] in ("e", "E"):
            return False
    return True


def profile_actions_by_author(profile_events: list, note_author_by_id: dict,
                              requester_hex: str) -> tuple:
    actions_by_author = defaultdict(float)
    liked_authors = set()
    for event in profile_events:
        if event.author().to_hex() != requester_hex:
            continue
        weight = event_action_weight(event)
        for tag in event.tags():
            vec = tag.to_vec()
            if vec[0] in ("e", "E") and len(vec) > 1 and vec[1] in note_author_by_id:
                author = note_author_by_id[vec[1]]
                if author == requester_hex:
                    continue
                actions_by_author[author] += weight
                liked_authors.add(author)
    return dict(actions_by_author), liked_authors


def build_coengagement(engagement_events: list, note_author_by_id: dict,
                       requester_hex: str, liked_authors: set,
                       overlap_threshold: int = RANKING_PARAMS["oon_overlap_threshold"]) -> dict:
    engager_authors = defaultdict(set)
    for event in engagement_events:
        engager = event.author().to_hex()
        if engager == requester_hex:
            continue
        for tag in event.tags():
            vec = tag.to_vec()
            if vec[0] in ("e", "E") and len(vec) > 1 and vec[1] in note_author_by_id:
                engager_authors[engager].add(note_author_by_id[vec[1]])
    weights = {}
    for engager, authors in engager_authors.items():
        overlap = len(authors & liked_authors) if liked_authors else 0
        if liked_authors is not None and overlap < overlap_threshold:
            continue
        contribution = max(1, overlap)
        for author in authors:
            if author == requester_hex:
                continue
            weights[author] = weights.get(author, 0) + contribution
    return weights


class ProfileCache:
    def __init__(self, profile_db_name: str, sync_relay_list: list, ttl_seconds: int = 3600,
                 history_days: int = 7):
        self.profile_db_name = profile_db_name
        self.sync_relay_list = sync_relay_list
        self.ttl_seconds = ttl_seconds
        self.history_days = history_days
        self._profiles = {}
        self._follows = {}
        self._mutes = {}

    async def _get_client(self, database=None):
        sk = SecretKey.generate()
        keys = Keys.parse(sk.to_hex())
        builder = ClientBuilder().authenticator(SignerAuthenticator(keys))
        if database is not None:
            builder = builder.database(database)
        cli = builder.build()
        for relay in self.sync_relay_list:
            await cli.add_relay(RelayUrl.parse(relay))
        await cli.connect(timedelta(seconds=15))
        return cli

    def _is_fresh(self, entry, now_secs) -> bool:
        return entry is not None and (now_secs - entry[0]) < self.ttl_seconds

    async def get_profile(self, user_hex: str, note_author_by_id: dict) -> dict:
        now_secs = Timestamp.now().as_secs()
        entry = self._profiles.get(user_hex)
        if self._is_fresh(entry, now_secs):
            return entry[1]
        database = await NostrLmdb.open(self.profile_db_name)
        cli = await self._get_client(database)
        try:
            since = Timestamp.from_secs(now_secs - self.history_days * 24 * 3600)
            event_filter = Filter().kinds([Kind(k) for k in PROFILE_KINDS]).author(
                PublicKey.parse(user_hex)).since(since)
            await sync_discovery_database(cli, event_filter, "profile-sync")
            events = await database.query(event_filter)
        finally:
            await cli.shutdown()
        actions_by_author, liked_authors = profile_actions_by_author(events, note_author_by_id, user_hex)
        profile = {"events": events, "actions_by_author": actions_by_author,
                   "liked_authors": liked_authors}
        self._profiles[user_hex] = (now_secs, profile)
        return profile

    async def get_follows(self, user_hex: str) -> set:
        now_secs = Timestamp.now().as_secs()
        entry = self._follows.get(user_hex)
        if self._is_fresh(entry, now_secs):
            return entry[1]
        cli = await self._get_client()
        try:
            event_filter = Filter().kind(Kind(3)).author(PublicKey.parse(user_hex)).limit(1)
            events = await cli.fetch_events(ReqTarget.auto([event_filter]), timedelta(seconds=10))
            events = events.to_vec() if hasattr(events, "to_vec") else events
        finally:
            await cli.shutdown()
        follows = set()
        for event in events:
            for tag in event.tags():
                vec = tag.to_vec()
                if vec[0] == "p" and len(vec) > 1:
                    follows.add(vec[1])
        self._follows[user_hex] = (now_secs, follows)
        return follows

    async def get_mutes(self, user_hex: str) -> tuple:
        now_secs = Timestamp.now().as_secs()
        entry = self._mutes.get(user_hex)
        if self._is_fresh(entry, now_secs):
            return entry[1]
        cli = await self._get_client()
        try:
            event_filter = Filter().kind(Kind(10000)).author(PublicKey.parse(user_hex)).limit(1)
            events = await cli.fetch_events(ReqTarget.auto([event_filter]), timedelta(seconds=10))
            events = events.to_vec() if hasattr(events, "to_vec") else events
        finally:
            await cli.shutdown()
        muted = set()
        keywords = []
        for event in events:
            for tag in event.tags():
                vec = tag.to_vec()
                if len(vec) > 1 and vec[0] == "p":
                    muted.add(vec[1])
                elif len(vec) > 1 and vec[0] == "t":
                    keywords.append(vec[1].lower())
        self._mutes[user_hex] = (now_secs, (muted, keywords))
        return muted, keywords
