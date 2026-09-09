# For You Personalized Content DVM — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A fully personalized content-discovery DVM ("For You") that ranks recent Nostr notes per requester using X-style weighted multi-action scoring: in-network (follows) + out-of-network (co-engagement) candidates, author affinity from the requester's own engagement profile, credibility, recency, diversity decay, boosts, and visibility filters.

**Architecture:** Three units: `nostr_dvm/utils/engagement_profile_utils.py` (pure ranking math + co-engagement graph + `ProfileCache` I/O class), `nostr_dvm/tasks/content_discovery_for_you.py` (the DVM task, `personalized=True`, computes per request from local DBs), and `tests/for_you.py` (runner script for VPS deployment). Data: the DVM's own global DB (`db/nostr_foryou.db`, 7d retention) + a shared profile LMDB (`db/nostr_profiles_foryou.db`). Spec: `docs/superpowers/specs/2026-09-09-for-you-feed-dvm-design.md`.

**Tech Stack:** Python 3.12, `nostr_sdk` (rust-nostr bindings), LMDB via `NostrLmdb`/`init_db`, `unittest.IsolatedAsyncioTestCase` (CI: `python -m unittest discover -s tests/unit -t . -v`).

## Global Constraints

- Test command: `python -m unittest tests.unit.test_for_you_ranking -v` (this feature); full suite: `python -m unittest discover -s tests/unit -t . -v`.
- Ranking constants — exact values (single `RANKING_PARAMS` dict in `engagement_profile_utils.py`): reaction 0.5, repost 1.0, reply 13.5, zap `1 + log10(max(sats, 1))`, base floor 0.1, affinity `min(8, 1 + ln(1 + x))`, credibility `min(1, ln(1 + n) / 4)`, recency `0.5 ** (age_hours / 24)`, OON discount 0.5, new-author boost 1.2 when author's 7d weighted engagement < 5, diversity decay 0.7 with floor 0.1, in-network cap 200, OON cap 300, co-engager overlap threshold 3, candidate age limit 48h, profile TTL 3600s, history window 7 days.
- Identifier: `discovery_content_for_you`; NIP-89 name: `For You`; env keys written on first run: `DVM_PRIVATE_KEY_DISCOVERY_CONTENT_FOR_YOU`, `NIP89_DTAG_DISCOVERY_CONTENT_FOR_YOU`.
- The task is `personalized=True` and computes per request; the scoring path reads local DBs only (relay calls only on profile cache misses).
- `DVMConfig.EXCLUDE_SELF_ENGAGEMENT` (exists, default True) must be honored: when on, a note author's own engagement of their note is excluded from `base` and from affinity/credibility inputs.
- Follow existing code style; do not refactor files outside the listed edits; unit tests use real nostr_sdk events + temp LMDB via `init_db` (mocks only for clients/relays).

---

### Task 1: Ranking math + co-engagement graph (pure functions)

**Files:**
- Create: `nostr_dvm/utils/engagement_profile_utils.py`
- Test: `tests/unit/test_for_you_ranking.py`

**Interfaces:**
- Consumes: `parse_amount_from_bolt11_invoice(bolt11: str) -> int` from `nostr_dvm.utils.zap_utils`.
- Produces (used by Tasks 2 and 3 — exact signatures):
  - `RANKING_PARAMS: dict`
  - `event_action_weight(event) -> float`
  - `note_engagement_base(events: list, note_author_hex: str, exclude_self: bool = True) -> float`
  - `recency_factor(created_at_secs: int, now_secs: int) -> float`
  - `affinity(author_hex: str, actions_by_author: dict[str, float]) -> float`
  - `credibility(distinct_engagers: int) -> float`
  - `new_author_boost(author_total_weighted_engagement: float) -> float`
  - `oon_factor(author_hex: str, follows: set[str]) -> float`
  - `score_note(base, affinity, credibility, recency, oon, boost) -> float`
  - `apply_author_diversity(ranked: list[tuple[Event, float]], max_results: int) -> list[tuple[Event, float]]`
  - `top_level(event) -> bool`
  - `profile_actions_by_author(profile_events: list, note_author_by_id: dict[str, str], requester_hex: str) -> tuple[dict[str, float], set[str]]`
  - `build_coengagement(engagement_events: list, note_author_by_id: dict[str, str], requester_hex: str, liked_authors: set[str], overlap_threshold: int = 3) -> dict[str, int]`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_for_you_ranking.py`:

```python
import math
import unittest

from nostr_sdk import EventBuilder, Keys, Kind, Tag, Timestamp

from nostr_dvm.utils.engagement_profile_utils import (
    RANKING_PARAMS, affinity, apply_author_diversity, build_coengagement,
    credibility, event_action_weight, new_author_boost, note_engagement_base,
    oon_factor, profile_actions_by_author, recency_factor, score_note, top_level)


def make_event(kind, author_keys, tags=(), age_secs=60):
    event = EventBuilder(Kind(kind), "content").tags([Tag.parse(t) for t in tags]).custom_created_at(
        Timestamp.from_secs(Timestamp.now().as_secs() - age_secs)).finalize(author_keys)
    return event


class RankingMathTests(unittest.TestCase):
    def setUp(self):
        self.now = Timestamp.now().as_secs()

    def test_action_weights_match_params(self):
        keys = Keys.generate()
        self.assertEqual(event_action_weight(make_event(7, keys)), 0.5)
        self.assertEqual(event_action_weight(make_event(6, keys)), 1.0)
        self.assertEqual(event_action_weight(make_event(1, keys)), 13.5)

    def test_zap_weight_is_log_scaled_by_sats(self):
        keys = Keys.generate()
        bolt11 = "lnbc1m1fake"  # 1 milli-BTC = 100k sats -> 1 + log10(100000) = 6
        zap = make_event(9735, keys, tags=[["bolt11", bolt11], ["preimage", "p"]])
        self.assertAlmostEqual(event_action_weight(zap), 1.0 + math.log10(100000))
        unparseable = make_event(9735, keys, tags=[["preimage", "p"]])
        self.assertEqual(event_action_weight(unparseable), 1.0)

    def test_note_engagement_base_has_floor_and_excludes_self(self):
        keys = Keys.generate()
        note = make_event(1, keys)
        note_author = note.author().to_hex()
        events = [make_event(7, Keys.generate(), tags=[["e", note.id().to_hex()]]),
                  make_event(7, keys, tags=[["e", note.id().to_hex()]])]
        self.assertAlmostEqual(note_engagement_base(events, note_author, exclude_self=True), 0.6)
        self.assertAlmostEqual(note_engagement_base(events, note_author, exclude_self=False), 1.1)

    def test_recency_halves_daily(self):
        self.assertAlmostEqual(recency_factor(self.now - 3600 * 24, self.now), 0.5)
        self.assertAlmostEqual(recency_factor(self.now, self.now), 1.0)

    def test_affinity_grows_with_actions_and_caps(self):
        self.assertEqual(affinity("a", {}), 1.0)
        self.assertAlmostEqual(affinity("a", {"a": 13.5}), 1.0 + math.log(14.5))
        self.assertEqual(affinity("a", {"a": 10 ** 9}), RANKING_PARAMS["affinity_cap"])

    def test_credibility_caps_at_one(self):
        self.assertEqual(credibility(0), 0.0)
        self.assertEqual(credibility(10 ** 6), 1.0)

    def test_new_author_boost_threshold(self):
        self.assertEqual(new_author_boost(4.9), RANKING_PARAMS["boost_factor"])
        self.assertEqual(new_author_boost(5.0), 1.0)

    def test_oon_factor_discounts_unfollowed(self):
        self.assertEqual(oon_factor("a", {"a"}), 1.0)
        self.assertEqual(oon_factor("b", {"a"}), RANKING_PARAMS["oon_discount"])

    def test_score_note_multiplies(self):
        self.assertAlmostEqual(score_note(2.0, 1.5, 0.5, 1.0, 0.5, 1.2), 0.9)

    def test_top_level_rejects_replies(self):
        keys = Keys.generate()
        self.assertTrue(top_level(make_event(1, keys)))
        self.assertFalse(top_level(make_event(1, keys, tags=[["e", "a" * 64]])))


class DiversityTests(unittest.TestCase):
    def test_repeated_author_decays_and_resorts(self):
        keys = Keys.generate()
        a1 = make_event(1, keys, age_secs=10)
        a2 = make_event(1, keys, age_secs=20)
        a3 = make_event(1, keys, age_secs=30)
        other = make_event(1, Keys.generate(), age_secs=15)
        ranked = [(a1, 10.0), (a2, 9.0), (other, 8.0), (a3, 7.0)]
        selected = apply_author_diversity(ranked, 3)
        scores = {e.id().to_hex(): s for e, s in selected}
        # a1 keeps 10, a2 decays 9*0.7=6.3, a3 7*0.49=3.43, other 8 -> top3: a1, other, a2
        self.assertEqual([e.id().to_hex() for e, _ in selected],
                         [a1.id().to_hex(), other.id().to_hex(), a2.id().to_hex()])
        self.assertAlmostEqual(scores[a2.id().to_hex()], 6.3)


class CoEngagementTests(unittest.TestCase):
    def test_coengagement_weights_and_thresholds(self):
        note_author = Keys.generate()
        note = make_event(1, note_author, tags=[])
        note_hex = note.id().to_hex()
        note_author_hex = note_author.public_key().to_hex()
        requester = Keys.generate().public_key().to_hex()
        liked = {note_author_hex}
        engager = Keys.generate()
        events = [make_event(7, engager, tags=[["e", note_hex]])]
        weights = build_coengagement(events, {note_hex: note_author_hex}, requester, liked, overlap_threshold=1)
        self.assertEqual(weights.get(note_author_hex), 1)
        # below threshold -> no candidates
        weights = build_coengagement(events, {note_hex: note_author_hex}, requester, liked, overlap_threshold=3)
        self.assertEqual(weights, {})

    def test_profile_actions_map_to_note_authors(self):
        note_author = Keys.generate()
        note = make_event(1, note_author)
        note_hex = note.id().to_hex()
        note_author_hex = note_author.public_key().to_hex()
        user = Keys.generate()
        replies = [make_event(1, user, tags=[["e", note_hex]]),
                   make_event(7, user, tags=[["e", note_hex]])]
        actions, liked = profile_actions_by_author(replies, {note_hex: note_author_hex}, user.public_key().to_hex())
        self.assertAlmostEqual(actions.get(note_author_hex), 14.0)
        self.assertEqual(liked, {note_author_hex})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_for_you_ranking -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'nostr_dvm.utils.engagement_profile_utils'`.

- [ ] **Step 3: Write the implementation**

Create `nostr_dvm/utils/engagement_profile_utils.py`:

```python
import math
from collections import defaultdict

from nostr_dvm.utils.zap_utils import parse_amount_from_bolt11_invoice

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
    kind = event.kind()
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_for_you_ranking -v`
Expected: all PASS. If the `custom_created_at(None)` path in the helper is rejected by nostr_sdk, change `make_event` to always pass `Timestamp.from_secs(Timestamp.now().as_secs() - age_secs)` with `age_secs=0` default instead of None.

- [ ] **Step 5: Run the full suite**

Run: `python -m unittest discover -s tests/unit -t . -v`
Expected: entire suite PASS (no regressions).

- [ ] **Step 6: Commit**

```bash
git add nostr_dvm/utils/engagement_profile_utils.py tests/unit/test_for_you_ranking.py
git commit -m "Add For You ranking math and co-engagement graph"
```

---

### Task 2: ProfileCache (per-user profiles, follows, mutes)

**Files:**
- Modify: `nostr_dvm/utils/engagement_profile_utils.py` (append the `ProfileCache` class)
- Test: `tests/unit/test_for_you_ranking.py` (append)

**Interfaces:**
- Consumes: Task 1's `profile_actions_by_author`; `sync_discovery_database(client, event_filter, label)` from `nostr_dvm.utils.discovery_utils`; `init_db` from `nostr_dvm.utils.database_utils`; nostr_sdk `ClientBuilder, Filter, Kind, Keys, NostrLmdb, RelayUrl, ReqTarget, SecretKey, SignerAuthenticator, Timestamp, timedelta`.
- Produces (used by Task 3):
  - `ProfileCache(profile_db_name: str, sync_relay_list: list[str], ttl_seconds: int = 3600, history_days: int = 7)`
  - `await cache.get_profile(user_hex: str, note_author_by_id: dict[str, str]) -> dict` with keys `"events"` (list of events), `"actions_by_author"` (dict), `"liked_authors"` (set)
  - `await cache.get_follows(user_hex: str) -> set[str]`
  - `await cache.get_mutes(user_hex: str) -> tuple[set[str], list[str]]` (muted pubkeys, muted keyword list)

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_for_you_ranking.py` (add these imports at the top of the file: `import tempfile`, `from types import SimpleNamespace`, `from unittest.mock import AsyncMock, MagicMock, patch`, and `from nostr_sdk import Timestamp`; add `from nostr_dvm.utils.database_utils import init_db` and `from nostr_dvm.utils.engagement_profile_utils import ProfileCache`; convert the test class below to `unittest.IsolatedAsyncioTestCase` as a separate class):

```python
class ProfileCacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.profile_db = await init_db(self.directory.name, print_filesize=False)
        self.now = Timestamp.now().as_secs()

    async def save_profile_event(self, kind, author_keys, tags):
        event = EventBuilder(Kind(kind), "x").tags([Tag.parse(t) for t in tags]).custom_created_at(
            Timestamp.from_secs(self.now - 60)).finalize(author_keys)
        await self.profile_db.save_event(event)
        return event

    async def test_get_profile_builds_actions_and_likes_from_db(self):
        note_author = Keys.generate()
        note = EventBuilder(Kind(1), "n").custom_created_at(
            Timestamp.from_secs(self.now - 120)).finalize(note_author)
        note_hex = note.id().to_hex()
        note_author_hex = note_author.public_key().to_hex()
        user = Keys.generate()
        await self.save_profile_event(1, user, [["e", note_hex]])
        await self.save_profile_event(7, user, [["e", note_hex]])
        cache = ProfileCache("unused.db", ["wss://broken"], ttl_seconds=3600, history_days=7)
        client = MagicMock()
        client.sync = AsyncMock(return_value=SimpleNamespace(
            success=["wss://ok"], failed={}, report=SimpleNamespace(received={})))
        client.database.return_value = self.profile_db
        client.add_relay = AsyncMock()
        client.connect = AsyncMock()
        client.shutdown = AsyncMock()
        with patch("nostr_dvm.utils.engagement_profile_utils.ClientBuilder") as builder, \
                patch("nostr_dvm.utils.engagement_profile_utils.NostrLmdb.open",
                      new_callable=AsyncMock) as open_db:
            open_db.return_value = self.profile_db
            builder.return_value.database.return_value.authenticator.return_value.build.return_value = client
            profile = await cache.get_profile(user.public_key().to_hex(), {note_hex: note_author_hex})
        self.assertAlmostEqual(profile["actions_by_author"][note_author_hex], 14.0)
        self.assertEqual(profile["liked_authors"], {note_author_hex})
        # second call is a cache hit: sync must not be called again
        with patch("nostr_dvm.utils.engagement_profile_utils.ClientBuilder") as builder:
            builder.return_value.database.return_value.authenticator.return_value.build.return_value = client
            await cache.get_profile(user.public_key().to_hex(), {note_hex: note_author_hex})
            client.sync.assert_awaited_once()

    async def test_get_follows_and_mutes_from_fetched_lists(self):
        user = Keys.generate()
        follow_a = Keys.generate().public_key().to_hex()
        follow_b = Keys.generate().public_key().to_hex()
        mute_c = Keys.generate().public_key().to_hex()
        contact = EventBuilder(Kind(3), "").tags(
            [Tag.parse(["p", follow_a]), Tag.parse(["p", follow_b])]).custom_created_at(
            Timestamp.from_secs(self.now - 60)).finalize(user)
        mutes = EventBuilder(Kind(10000), "").tags(
            [Tag.parse(["p", mute_c]), Tag.parse(["t", "spam"])], ).custom_created_at(
            Timestamp.from_secs(self.now - 60)).finalize(user)
        cache = ProfileCache("unused.db", ["wss://broken"], ttl_seconds=3600, history_days=7)
        client = MagicMock()
        client.database.return_value = self.profile_db
        client.add_relay = AsyncMock()
        client.connect = AsyncMock()
        client.shutdown = AsyncMock()
        client.fetch_events = AsyncMock(side_effect=[[contact], [mutes]])
        with patch("nostr_dvm.utils.engagement_profile_utils.ClientBuilder") as builder:
            builder.return_value.database.return_value.authenticator.return_value.build.return_value = client
            follows = await cache.get_follows(user.public_key().to_hex())
            muted, keywords = await cache.get_mutes(user.public_key().to_hex())
        self.assertEqual(follows, {follow_a, follow_b})
        self.assertEqual(muted, {mute_c})
        self.assertEqual(keywords, ["spam"])
```

Note: `client.database.return_value` is set so `sync_discovery_database`'s `client.database().count(...)` works against the real temp DB.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_for_you_ranking.ProfileCacheTests -v`
Expected: ERROR — `ImportError: cannot import name 'ProfileCache'`.

- [ ] **Step 3: Implement ProfileCache**

Append to `nostr_dvm/utils/engagement_profile_utils.py` (add these imports at the top of the file):

```python
from datetime import timedelta

from nostr_sdk import ClientBuilder, Filter, Kind, Keys, NostrLmdb, PublicKey, RelayUrl, \
    ReqTarget, SecretKey, SignerAuthenticator, Timestamp

from nostr_dvm.utils.discovery_utils import sync_discovery_database

PROFILE_KINDS = [1, 6, 7, 9735]
```

Then the class:

```python
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
```

Add `PublicKey` to the nostr_sdk import line (it is used in the filters above).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_for_you_ranking -v`
Expected: all PASS including the two new `ProfileCacheTests` tests.

- [ ] **Step 5: Run the full suite and commit**

```bash
python -m unittest discover -s tests/unit -t . -v
git add nostr_dvm/utils/engagement_profile_utils.py tests/unit/test_for_you_ranking.py
git commit -m "Add per-user engagement ProfileCache for the For You DVM"
```

Expected: entire suite PASS.

---

### Task 3: The `DiscoverContentForYou` DVM task

**Files:**
- Create: `nostr_dvm/tasks/content_discovery_for_you.py`
- Test: `tests/unit/test_for_you_ranking.py` (append `ForYouTaskTests`)

**Interfaces:**
- Consumes: Task 1's pure functions; Task 2's `ProfileCache`; `engagement_kinds()` and `sync_discovery_database()` from `nostr_dvm.utils.discovery_utils`; `DVMTaskInterface, process_venv` from `nostr_dvm.interfaces.dvmtaskinterface`; `build_default_config`, `init_db`, NIP-88/89 config helpers — same imports as `content_discovery_currently_popular.py`.
- Produces: `DiscoverContentForYou` task class; `build_example(name, identifier, admin_config, options, cost=0, update_rate=600, processing_msg=None, update_db=True)`; runner entry via `process_venv(DiscoverContentForYou)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_for_you_ranking.py` (add import `from nostr_dvm.tasks.content_discovery_for_you import DiscoverContentForYou`):

```python
class ForYouTaskTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.global_db = await init_db(self.directory.name, print_filesize=False)
        self.now = Timestamp.now().as_secs()

    async def save_global(self, kind, author_keys, tags=(), age_secs=60):
        event = EventBuilder(Kind(kind), "c").tags([Tag.parse(t) for t in tags]).custom_created_at(
            Timestamp.from_secs(self.now - age_secs)).finalize(author_keys)
        await self.global_db.save_event(event)
        return event

    def make_task(self, user):
        task = object.__new__(DiscoverContentForYou)
        task.options = {"db_name": "unused.db", "db_since": 7 * 24 * 3600}
        task.db_since = 7 * 24 * 3600
        task.profile_ttl_seconds = 3600
        task.history_days = 7
        cache = MagicMock()
        cache.get_profile = AsyncMock(return_value={"events": [], "actions_by_author": {}, "liked_authors": set()})
        cache.get_follows = AsyncMock(return_value={user})
        cache.get_mutes = AsyncMock(return_value=(set(), []))
        task.profile_cache = cache
        task.dvm_config = SimpleNamespace(EXCLUDE_SELF_ENGAGEMENT=True, LOGLEVEL=LogLevel.ERROR,
                                          NIP89=SimpleNamespace(NAME="For You"))
        return task, cache

    async def test_ranks_oon_with_discount_and_affinity_boost(self):
        followed_author = Keys.generate()
        oon_author = Keys.generate()
        author_three = Keys.generate()
        engager = Keys.generate()
        requester = Keys.generate().public_key().to_hex()
        # in-network note: 1 reaction
        in_note = await self.save_global(1, followed_author, age_secs=30)
        await self.save_global(7, Keys.generate(), tags=[["e", in_note.id().to_hex()]], age_secs=20)
        # OON note: 1 reaction too, but author is co-engaged with the requester
        oon_note = await self.save_global(1, oon_author, age_secs=30)
        await self.save_global(7, Keys.generate(), tags=[["e", oon_note.id().to_hex()]], age_secs=20)
        # the requester's mocked liked set: oon_author + two more; the engager must
        # engage with notes by >= 3 of the liked authors to become a co-engager
        author_three_note = await self.save_global(1, author_three, age_secs=3600 * 72)
        await self.save_global(7, engager, tags=[["e", author_three_note.id().to_hex()]], age_secs=3600 * 72)
        liked_extra_keys = Keys.generate()
        liked_extra_note = await self.save_global(1, liked_extra_keys, age_secs=3600 * 72)
        await self.save_global(7, engager, tags=[["e", liked_extra_note.id().to_hex()]], age_secs=3600 * 72)
        await self.save_global(7, engager, tags=[["e", oon_note.id().to_hex()]], age_secs=25)

        task, cache = self.make_task(requester)
        cache.get_profile = AsyncMock(return_value={
            "events": [],
            "actions_by_author": {oon_author.public_key().to_hex(): 13.5},
            "liked_authors": {oon_author.public_key().to_hex(),
                              author_three.public_key().to_hex(),
                              liked_extra_keys.public_key().to_hex()}})
        with patch("nostr_dvm.tasks.content_discovery_for_you.NostrLmdb.open",
                   new_callable=AsyncMock) as open_db:
            open_db.return_value = self.global_db
            result = await task.calculate_result(
                {"jobID": "generic", "requester": requester, "options": json.dumps({"max_results": 10})})
        entries = [tuple(t) for t in json.loads(result)]
        self.assertIn(("e", in_note.id().to_hex()), entries)
        self.assertIn(("e", oon_note.id().to_hex()), entries)

    async def test_degrades_on_profile_failure(self):
        user = Keys.generate().public_key().to_hex()
        await self.save_global(1, Keys.generate(), age_secs=30)
        task, cache = self.make_task(user)
        cache.get_profile = AsyncMock(side_effect=RuntimeError("relay down"))
        with patch("nostr_dvm.tasks.content_discovery_for_you.NostrLmdb.open",
                   new_callable=AsyncMock) as open_db:
            open_db.return_value = self.global_db
            result = await task.calculate_result(
                {"jobID": "generic", "requester": user, "options": json.dumps({"max_results": 10})})
        self.assertIsInstance(json.loads(result), list)  # degraded mode ran, no crash
```

The degraded-mode test asserts a valid JSON list (possibly empty) is returned without raising.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_for_you_ranking.ForYouTaskTests -v`
Expected: ERROR — `ModuleNotFoundError: No module named 'nostr_dvm.tasks.content_discovery_for_you'`.

- [ ] **Step 3: Implement the task**

Create `nostr_dvm/tasks/content_discovery_for_you.py`:

```python
import json
import os

from nostr_sdk import (
    ClientBuilder, Filter, Kind, LogLevel, NostrLmdb, PublicKey, RelayUrl, SecretKey,
    SignerAuthenticator, Timestamp,
)

from nostr_dvm.interfaces.dvmtaskinterface import DVMTaskInterface, process_venv
from nostr_dvm.utils import definitions
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.database_utils import init_db
from nostr_dvm.utils.discovery_utils import engagement_kinds, sync_discovery_database
from nostr_dvm.utils.dvmconfig import DVMConfig, build_default_config
from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.engagement_profile_utils import (
    RANKING_PARAMS, affinity, apply_author_diversity, build_coengagement, credibility,
    event_action_weight, new_author_boost, note_engagement_base, oon_factor, profile_actions_by_author,
    recency_factor, score_note, top_level, ProfileCache)
from nostr_dvm.utils.nip88_utils import NIP88Config, check_and_set_d_tag_nip88, check_and_set_tiereventid_nip88
from nostr_dvm.utils.nip89_utils import NIP89Config, check_and_set_d_tag, create_amount_tag

"""
This File contains a Module to discover a personalized "For You" feed per requester,
inspired by the X For You algorithm: in-network (follows) + out-of-network (co-engagement)
candidates, weighted multi-action scoring, credibility, recency, diversity decay and
visibility filters.
Accepted Inputs: none (requester = param user, else the request author)
Outputs: A list of events
Params: max_results
"""


class DiscoverContentForYou(DVMTaskInterface):
    KIND: Kind = EventDefinitions.KIND_NIP90_CONTENT_DISCOVERY
    TASK: str = "discover-content"
    FIX_COST: float = 0
    dvm_config: DVMConfig
    request_form = None
    last_schedule: int
    db_since = 7 * 24 * 3600
    db_name = "db/nostr_foryou.db"
    profile_db_name = "db/nostr_profiles_foryou.db"
    history_days = 7
    profile_ttl_seconds = 3600
    personalized = True
    result = "[]"
    database = None
    profile_cache = None

    async def init_dvm(self, name, dvm_config: DVMConfig, nip89config: NIP89Config, nip88config: NIP88Config = None,
                       admin_config: AdminConfig = None, options=None):
        dvm_config.SCRIPT = os.path.abspath(__file__)
        self.database = dvm_config.DATABASE
        self.request_form = {"jobID": "generic"}
        opts = {"max_results": 200}
        self.request_form['options'] = json.dumps(opts)
        self.last_schedule = Timestamp.now().as_secs()
        if self.options.get("db_name"):
            self.db_name = self.options.get("db_name")
        if self.options.get("db_since"):
            self.db_since = int(self.options.get("db_since"))
        if self.options.get("history_days"):
            self.history_days = int(self.options.get("history_days"))
        if self.options.get("profile_ttl_seconds"):
            self.profile_ttl_seconds = int(self.options.get("profile_ttl_seconds"))
        self.profile_cache = ProfileCache(self.profile_db_name, self.dvm_config.SYNC_DB_RELAY_LIST,
                                          ttl_seconds=self.profile_ttl_seconds, history_days=self.history_days)
        if self.dvm_config.UPDATE_DATABASE:
            await self.sync_db()

    async def is_input_supported(self, tags, client=None, dvm_config=None):
        for tag in tags:
            if tag.to_vec()[0] == 'i':
                if tag.to_vec()[2] != "text":
                    return False
        return True

    async def create_request_from_nostr_event(self, event, client=None, dvm_config=None):
        self.dvm_config = dvm_config
        request_form = {"jobID": event.id().to_hex(), "requester": event.author().to_hex()}
        max_results = 200
        user = None
        for tag in event.tags():
            vec = tag.to_vec()
            if vec[0] == 'i':
                pass
            elif vec[0] == 'param':
                if vec[1] == "max_results":
                    max_results = int(vec[2])
                elif vec[1] == "user":
                    user = vec[2]
        options = {"max_results": max_results}
        if user:
            options["user"] = user
        request_form['options'] = json.dumps(options)
        return request_form

    async def process(self, request_form):
        return await self.calculate_result(request_form)

    def _resolve_user(self, request_form):
        options = self.set_options(request_form)
        user = options.get("user") or request_form.get("requester")
        if user:
            try:
                user = PublicKey.parse(user).to_hex()
            except Exception:
                user = None
        return user, int(options.get("max_results", 200))

    async def calculate_result(self, request_form):
        user, max_results = self._resolve_user(request_form)
        database = await NostrLmdb.open(self.db_name)
        try:
            return await self._personalized(database, user, max_results)
        except Exception as error:
            print("[" + self.dvm_config.NIP89.NAME + "] Personalized ranking failed, "
                  "falling back to global ranking: " + str(error))
            return await self._global_fallback(database, max_results)

    async def _personalized(self, database, user, max_results):
        now_secs = Timestamp.now().as_secs()
        candidate_since_secs = now_secs - RANKING_PARAMS["candidate_age_hours"] * 3600
        candidate_since = Timestamp.from_secs(candidate_since_secs)
        graph_since = Timestamp.from_secs(now_secs - self.db_since)

        notes = await database.query(Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(candidate_since))
        note_author_by_id = {note.id().to_hex(): note.author().to_hex() for note in notes}

        profile = await self.profile_cache.get_profile(user, note_author_by_id)
        follows = await self.profile_cache.get_follows(user)
        muted, keywords = await self.profile_cache.get_mutes(user)
        actions_by_author = profile["actions_by_author"]
        liked_authors = profile["liked_authors"]

        engagement = await database.query(
            Filter().kinds(engagement_kinds()).since(graph_since))

        # group engagement by tagged note id; compute per-author distinct engagers + totals
        engagement_by_note = {}
        engagers_by_author = {}
        total_by_author = {}
        for event in engagement:
            weight = event_action_weight(event)
            engager = event.author().to_hex()
            for tag in event.tags():
                vec = tag.to_vec()
                if vec[0] in ("e", "E") and len(vec) > 1 and vec[1] in note_author_by_id:
                    author = note_author_by_id[vec[1]]
                    engagement_by_note.setdefault(vec[1], []).append(event)
                    engagers_by_author.setdefault(author, set()).add(engager)
                    total_by_author[author] = total_by_author.get(author, 0.0) + weight

        exclude_self = getattr(self.dvm_config, "EXCLUDE_SELF_ENGAGEMENT", True)

        def passes_filters(note) -> bool:
            author = note.author().to_hex()
            if author == user or author in muted:
                return False
            content = note.content().lower()
            if any(keyword in content for keyword in keywords):
                return False
            return True

        def note_score(note) -> float:
            author = note.author().to_hex()
            base = note_engagement_base(engagement_by_note.get(note.id().to_hex(), []),
                                        author, exclude_self=exclude_self)
            return score_note(base,
                              affinity(author, actions_by_author),
                              credibility(len(engagers_by_author.get(author, set()))),
                              recency_factor(note.created_at().as_secs(), now_secs),
                              oon_factor(author, follows),
                              new_author_boost(total_by_author.get(author, 0.0)))

        in_network = [note for note in notes
                      if note.author().to_hex() in follows and passes_filters(note) and top_level(note)]
        in_network.sort(key=lambda note: -note.created_at().as_secs())
        in_network = in_network[:RANKING_PARAMS["in_network_cap"]]

        author_weights = build_coengagement(engagement, note_author_by_id, user, liked_authors)
        oon_author_set = {author for author in author_weights
                          if author not in follows and author not in muted and author != user}
        oon = [note for note in notes
               if note.author().to_hex() in oon_author_set and passes_filters(note) and top_level(note)]
        oon.sort(key=lambda note: -(author_weights[note.author().to_hex()]
                                    * note_engagement_base(engagement_by_note.get(note.id().to_hex(), []),
                                                           note.author().to_hex(), exclude_self=exclude_self)))
        oon = oon[:RANKING_PARAMS["oon_cap"]]

        candidates = in_network + oon
        if not candidates:
            return "[]"

        ranked = sorted([(note, note_score(note)) for note in candidates], key=lambda pair: -pair[1])
        selected = apply_author_diversity(ranked, max_results)
        return json.dumps([["e", event.id().to_hex()] for event, score in selected])

    async def _global_fallback(self, database, max_results):
        now_secs = Timestamp.now().as_secs()
        candidate_since = Timestamp.from_secs(now_secs - RANKING_PARAMS["candidate_age_hours"] * 3600)
        graph_since = Timestamp.from_secs(now_secs - self.db_since)
        notes = await database.query(Filter().kind(definitions.EventDefinitions.KIND_NOTE).since(candidate_since))
        engagement = await database.query(Filter().kinds(engagement_kinds()).since(graph_since))
        engagement_by_note = {}
        for event in engagement:
            for tag in event.tags():
                vec = tag.to_vec()
                if vec[0] in ("e", "E") and len(vec) > 1:
                    engagement_by_note.setdefault(vec[1], []).append(event)
        exclude_self = getattr(self.dvm_config, "EXCLUDE_SELF_ENGAGEMENT", True)
        scored = []
        for note in notes:
            if not top_level(note):
                continue
            author = note.author().to_hex()
            scored.append((note, note_engagement_base(engagement_by_note.get(note.id().to_hex(), []),
                                                      author, exclude_self=exclude_self)))
        scored.sort(key=lambda pair: -pair[1])
        return json.dumps([["e", event.id().to_hex()] for event, score in scored[:max_results]])

    async def schedule(self, dvm_config):
        if dvm_config.SCHEDULE_UPDATES_SECONDS == 0:
            return 0
        if Timestamp.now().as_secs() >= self.last_schedule + dvm_config.SCHEDULE_UPDATES_SECONDS:
            if self.dvm_config.UPDATE_DATABASE:
                await self.sync_db()
            self.last_schedule = Timestamp.now().as_secs()
            return 1
        return 0

    async def sync_db(self):
        cli = None
        try:
            sk = SecretKey.parse(self.dvm_config.PRIVATE_KEY)
            keys = Keys.parse(sk.to_hex())
            if self.database is None:
                self.database = await init_db(self.db_name, print_filesize=False)
            database = self.database
            cli = ClientBuilder().authenticator(SignerAuthenticator(keys)).database(database).build()
            for relay in self.dvm_config.SYNC_DB_RELAY_LIST:
                await cli.add_relay(RelayUrl.parse(relay))
            await cli.connect(timedelta(seconds=15))
            since = Timestamp.from_secs(Timestamp.now().as_secs() - self.db_since)
            event_filter = Filter().kinds(engagement_kinds()).since(since)
            await sync_discovery_database(cli, event_filter, self.dvm_config.NIP89.NAME)
            await cli.database().delete_events(Filter().until(Timestamp.from_secs(
                Timestamp.now().as_secs() - self.db_since)))
        except Exception as e:
            print(e)
        finally:
            if cli is not None:
                await cli.shutdown()


def build_example(name, identifier, admin_config, options, cost=0, update_rate=600, processing_msg=None,
                  update_db=True):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    image = "https://image.nostr.build/b29b6ec4bf9b6184f69d33cb44862db0d90a2dd9a506532e7ba5698af7d36210.jpg"
    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show a personalized For You feed, ranked for you",
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": False,
        "personalized": True,
        "amount": create_amount_tag(cost),
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default 200)"
            },
            "user": {
                "required": False,
                "values": [],
                "description": "Pubkey to build the feed for (defaults to the requester)"
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)
    return DiscoverContentForYou(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                 admin_config=admin_config, options=options)


if __name__ == '__main__':
    process_venv(DiscoverContentForYou)
```

Add `from datetime import timedelta` to the imports (used in `sync_db`), and mirror the `post_process` method from `content_discovery_currently_popular.py` verbatim (it converts `text/plain` outputs via `post_process_list_to_events`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_for_you_ranking -v`
Expected: all PASS. If `ForYouTaskTests.test_ranks_oon_with_discount_and_affinity_boost` ordering assumptions are brittle, keep the set-membership assertions (both notes present) and drop strict ordering assertions.

- [ ] **Step 5: Full suite + syntax check, then commit**

```bash
python -m unittest discover -s tests/unit -t . -v
python -m compileall -q nostr_dvm/tasks/content_discovery_for_you.py
git add nostr_dvm/tasks/content_discovery_for_you.py tests/unit/test_for_you_ranking.py
git commit -m "Add For You personalized content discovery DVM"
```

Expected: entire suite PASS; compileall exit 0.

---

### Task 4: Runner script + VPS deployment (key sync per spec)

**Files:**
- Create: `tests/for_you.py` (runner; also deployed to the VPS as `/root/dvm/for_you.py`)

**Interfaces:**
- Consumes: `DiscoverContentForYou` + its `build_example` from Task 3; `DVMFramework`, `AdminConfig`, `build_default_config` — same pattern as `tests/discovery_content.py`.
- Produces: a running `For You` DVM on the VPS announcing NIP-89 with identifier `discovery_content_for_you`; env keys `DVM_PRIVATE_KEY_DISCOVERY_CONTENT_FOR_YOU` and `NIP89_DTAG_DISCOVERY_CONTENT_FOR_YOU` present in BOTH the local repo `.env` and `/root/dvm/.env`.

- [ ] **Step 1: Write the runner script**

Create `tests/for_you.py` (modeled on `tests/discovery_content.py`):

```python
import asyncio
import json
from pathlib import Path

import dotenv
from nostr_sdk import init_logger, LogLevel

from nostr_dvm.framework import DVMFramework
from nostr_dvm.tasks.content_discovery_for_you import DiscoverContentForYou
from nostr_dvm.utils.admin_utils import AdminConfig
from nostr_dvm.utils.database_utils import init_db
from nostr_dvm.utils.dvmconfig import build_default_config
from nostr_dvm.utils.nip89_utils import create_amount_tag, NIP89Config, check_and_set_d_tag
from nostr_dvm.utils.outbox_utils import AVOID_OUTBOX_RELAY_LIST

rebroadcast_NIP89 = True
rebroadcast_NIP65_Relay_List = True
update_profile = True

global_update_rate = 600
use_logger = True
log_level = LogLevel.ERROR

RELAY_LIST = ["wss://relay.nostrdvm.com",
              "wss://nostr.oxtr.dev"]

SYNC_DB_RELAY_LIST = ["wss://relay.ditto.pub",
                      "wss://purplerelay.com",
                      "wss://nostr.bitcoiner.social",
                      "wss://nostr.oxtr.dev",
                      "wss://relay.nostr.net"]

if use_logger:
    init_logger(log_level)


def build_for_you(name, identifier, admin_config, options, image, cost=0, update_rate=600,
                  processing_msg=None, update_db=True, database=None):
    dvm_config = build_default_config(identifier)
    dvm_config.USE_OWN_VENV = False
    dvm_config.SHOWLOG = True
    dvm_config.SCHEDULE_UPDATES_SECONDS = update_rate
    dvm_config.UPDATE_DATABASE = update_db
    dvm_config.FIX_COST = cost
    dvm_config.DATABASE = database
    dvm_config.LOGLEVEL = LogLevel.INFO
    dvm_config.CUSTOM_PROCESSING_MESSAGE = processing_msg
    dvm_config.AVOID_OUTBOX_RELAY_LIST = AVOID_OUTBOX_RELAY_LIST
    dvm_config.SYNC_DB_RELAY_LIST = SYNC_DB_RELAY_LIST
    dvm_config.RELAY_LIST = RELAY_LIST
    dvm_config.SEND_FEEDBACK_EVENTS = False
    admin_config.LUD16 = dvm_config.LN_ADDRESS

    nip89info = {
        "name": name,
        "picture": image,
        "about": "I show a personalized For You feed, ranked for you",
        "lud16": dvm_config.LN_ADDRESS,
        "supportsEncryption": True,
        "acceptsNutZaps": dvm_config.ENABLE_NUTZAP,
        "personalized": True,
        "amount": create_amount_tag(cost),
        "nip90Params": {
            "max_results": {
                "required": False,
                "values": [],
                "description": "The number of maximum results to return (default 200)"
            },
            "user": {
                "required": False,
                "values": [],
                "description": "Pubkey to build the feed for (defaults to the requester)"
            }
        }
    }
    nip89config = NIP89Config()
    nip89config.DTAG = check_and_set_d_tag(identifier, name, dvm_config.PRIVATE_KEY, nip89info["picture"])
    nip89config.CONTENT = json.dumps(nip89info)
    return DiscoverContentForYou(name=name, dvm_config=dvm_config, nip89config=nip89config,
                                 admin_config=admin_config, options=options)


def playground():
    framework = DVMFramework()
    main_db = "db/nostr_foryou.db"
    database = asyncio.run(init_db(main_db, wipe=False, limit=1024, print_filesize=True))

    admin_config = AdminConfig()
    admin_config.REBROADCAST_NIP89 = rebroadcast_NIP89
    admin_config.REBROADCAST_NIP65_RELAY_LIST = rebroadcast_NIP65_Relay_List
    admin_config.UPDATE_PROFILE = update_profile

    options = {
        "db_name": main_db,
        "db_since": 7 * 24 * 60 * 60,
        "history_days": 7,
        "profile_ttl_seconds": 3600,
    }
    for_you = build_for_you("For You", "discovery_content_for_you", admin_config, options,
                            image="https://image.nostr.build/b29b6ec4bf9b6184f69d33cb44862db0d90a2dd9a506532e7ba5698af7d36210.jpg",
                            update_rate=global_update_rate,
                            processing_msg=["Ranking your For You feed"],
                            update_db=True, database=database)
    framework.add(for_you)
    framework.run()


if __name__ == '__main__':
    env_path = Path('.env')
    if not env_path.is_file():
        with open('.env', 'w') as f:
            f.write('')
    dotenv.load_dotenv(env_path, verbose=True, override=True)
    playground()
```

- [ ] **Step 2: Verify locally (also generates the key per spec)**

Run: `timeout 60 python tests/for_you.py` from the repo root (a relay connection is expected; a clean startup log with the DVM pubkey is the pass signal; the timeout kill is intentional).
Then check: `grep -E 'DVM_PRIVATE_KEY_DISCOVERY_CONTENT_FOR_YOU|NIP89_DTAG_DISCOVERY_CONTENT_FOR_YOU' .env`
Expected: both keys present in the local `.env` (generated by `check_and_set_private_key` / `check_and_set_d_tag`). If only the private key appears (d-tag is written on announcement), it will be present after the first announcement — verify again after Step 3 on the VPS.

- [ ] **Step 3: Deploy to the VPS**

```bash
# sync runner + package
rsync -rlptDz tests/for_you.py vps:/root/dvm/for_you.py
rsync -rlptDz --checksum --exclude='__pycache__' --exclude='*.pyc' nostr_dvm/ vps:/root/dvm/nostr_dvm/

# copy the new key env vars into the VPS .env (before first start there)
for KEY in DVM_PRIVATE_KEY_DISCOVERY_CONTENT_FOR_YOU NIP89_DTAG_DISCOVERY_CONTENT_FOR_YOU; do
  VAL=$(grep "^$KEY=" .env | tail -1)
  ssh vps "grep -q '^$KEY=' /root/dvm/.env || echo '$VAL' >> /root/dvm/.env"
done
```

Then on the VPS start under pm2 from `/root/dvm`:

```bash
ssh vps "cd /root/dvm && export PATH=/root/.nvm/versions/node/v20.17.0/bin:\$PATH && pm2 start ./venv/bin/python --name for_you -- for_you.py && sleep 10 && pm2 list | grep for_you"
```

Expected: `for_you` status `online`, restart counter not climbing across a 30s re-check.

- [ ] **Step 4: Verify announcement and key sync**

```bash
ssh vps "grep -E 'DVM_PRIVATE_KEY_DISCOVERY_CONTENT_FOR_YOU|NIP89_DTAG_DISCOVERY_CONTENT_FOR_YOU' /root/dvm/.env"
```
Expected: both keys present on the VPS. Then fetch the NIP-89 announcement (kind 31990) by the DVM pubkey (printed in the local Step-2 log and in `/root/.pm2/logs/for_you-out.log` as `Nostr DVM public key:`) from `wss://relay.nostrdvm.com` and confirm `name == "For You"`.

- [ ] **Step 5: Commit the runner**

```bash
git add tests/for_you.py
git commit -m "Add For You DVM runner script"
```
