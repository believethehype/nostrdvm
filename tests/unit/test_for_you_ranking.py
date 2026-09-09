import json
import math
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from nostr_sdk import EventBuilder, Keys, Kind, LogLevel, Tag, Timestamp

from nostr_dvm.tasks.content_discovery_for_you import DiscoverContentForYou
from nostr_dvm.utils.database_utils import init_db
from nostr_dvm.utils.engagement_profile_utils import (
    RANKING_PARAMS, ProfileCache, affinity, apply_author_diversity,
    build_coengagement, credibility, event_action_weight, new_author_boost,
    note_engagement_base, oon_factor, profile_actions_by_author, recency_factor,
    score_note, top_level)


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
            builder.return_value.authenticator.return_value.database.return_value.build.return_value = client
            profile = await cache.get_profile(user.public_key().to_hex(), {note_hex: note_author_hex})
        self.assertAlmostEqual(profile["actions_by_author"][note_author_hex], 14.0)
        self.assertEqual(profile["liked_authors"], {note_author_hex})
        # second call is a cache hit: sync must not be called again
        with patch("nostr_dvm.utils.engagement_profile_utils.ClientBuilder") as builder:
            builder.return_value.authenticator.return_value.database.return_value.build.return_value = client
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
            builder.return_value.authenticator.return_value.build.return_value = client
            follows = await cache.get_follows(user.public_key().to_hex())
            muted, keywords = await cache.get_mutes(user.public_key().to_hex())
        self.assertEqual(follows, {follow_a, follow_b})
        self.assertEqual(muted, {mute_c})
        self.assertEqual(keywords, ["spam"])

    async def test_get_requester_context_single_connect(self):
        note_author = Keys.generate()
        note = EventBuilder(Kind(1), "n").custom_created_at(
            Timestamp.from_secs(self.now - 120)).finalize(note_author)
        note_hex = note.id().to_hex()
        note_author_hex = note_author.public_key().to_hex()
        user = Keys.generate()
        await self.save_profile_event(7, user, [["e", note_hex]])
        follow_a = Keys.generate().public_key().to_hex()
        follow_b = Keys.generate().public_key().to_hex()
        mute_c = Keys.generate().public_key().to_hex()
        contact = EventBuilder(Kind(3), "").tags(
            [Tag.parse(["p", follow_a]), Tag.parse(["p", follow_b])]).custom_created_at(
            Timestamp.from_secs(self.now - 60)).finalize(user)
        mutes = EventBuilder(Kind(10000), "").tags(
            [Tag.parse(["p", mute_c]), Tag.parse(["t", "spam"])]).custom_created_at(
            Timestamp.from_secs(self.now - 60)).finalize(user)
        cache = ProfileCache("unused.db", ["wss://broken"], ttl_seconds=3600, history_days=7)
        client = MagicMock()
        client.sync = AsyncMock(return_value=SimpleNamespace(
            success=["wss://ok"], failed={}, report=SimpleNamespace(received={})))
        client.database.return_value = self.profile_db
        client.add_relay = AsyncMock()
        client.connect = AsyncMock()
        client.shutdown = AsyncMock()
        client.fetch_events = AsyncMock(side_effect=[[contact], [mutes]])
        with patch("nostr_dvm.utils.engagement_profile_utils.ClientBuilder") as builder, \
                patch("nostr_dvm.utils.engagement_profile_utils.NostrLmdb.open",
                      new_callable=AsyncMock) as open_db:
            open_db.return_value = self.profile_db
            builder.return_value.authenticator.return_value.database.return_value.build.return_value = client
            context = await cache.get_requester_context(user.public_key().to_hex(),
                                                        {note_hex: note_author_hex})
        self.assertEqual(
            builder.return_value.authenticator.return_value.database.return_value.build.call_count, 1)
        self.assertEqual(client.connect.await_count, 1)
        self.assertAlmostEqual(context["actions_by_author"][note_author_hex], 0.5)
        self.assertEqual(context["liked_authors"], {note_author_hex})
        self.assertEqual(context["follows"], {follow_a, follow_b})
        self.assertEqual(context["muted"], {mute_c})
        self.assertEqual(context["keywords"], ["spam"])

    async def test_cached_profile_payload_excludes_raw_events(self):
        note_author = Keys.generate()
        note = EventBuilder(Kind(1), "n").custom_created_at(
            Timestamp.from_secs(self.now - 120)).finalize(note_author)
        note_hex = note.id().to_hex()
        note_author_hex = note_author.public_key().to_hex()
        user = Keys.generate()
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
            builder.return_value.authenticator.return_value.database.return_value.build.return_value = client
            profile = await cache.get_profile(user.public_key().to_hex(), {note_hex: note_author_hex})
        self.assertNotIn("events", profile)
        stored = cache._profiles[user.public_key().to_hex()][1]
        self.assertNotIn("events", stored)
        self.assertAlmostEqual(stored["actions_by_author"][note_author_hex], 0.5)
        self.assertEqual(stored["liked_authors"], {note_author_hex})

    async def test_profile_write_evicts_expired_other_users(self):
        user = Keys.generate().public_key().to_hex()
        stale_user = Keys.generate().public_key().to_hex()
        fresh_user = Keys.generate().public_key().to_hex()
        cache = ProfileCache("unused.db", ["wss://broken"], ttl_seconds=3600, history_days=7)
        now_secs = Timestamp.now().as_secs()
        cache._profiles[stale_user] = (now_secs - 3600, {"actions_by_author": {}, "liked_authors": set()})
        cache._profiles[fresh_user] = (now_secs - 10, {"actions_by_author": {}, "liked_authors": set()})
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
            builder.return_value.authenticator.return_value.database.return_value.build.return_value = client
            await cache.get_profile(user, {})
        self.assertNotIn(stale_user, cache._profiles)
        self.assertIn(fresh_user, cache._profiles)
        self.assertIn(user, cache._profiles)


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
        cache.get_requester_context = AsyncMock(return_value={
            "actions_by_author": {}, "liked_authors": set(),
            "follows": set(), "muted": set(), "keywords": []})
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
        # the in-network note must actually be followed by the requester
        cache.get_requester_context = AsyncMock(return_value={
            "actions_by_author": {oon_author.public_key().to_hex(): 13.5},
            "liked_authors": {oon_author.public_key().to_hex(),
                              author_three.public_key().to_hex(),
                              liked_extra_keys.public_key().to_hex()},
            "follows": {followed_author.public_key().to_hex()},
            "muted": set(), "keywords": []})
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
        cache.get_requester_context = AsyncMock(side_effect=RuntimeError("relay down"))
        with patch("nostr_dvm.tasks.content_discovery_for_you.NostrLmdb.open",
                   new_callable=AsyncMock) as open_db:
            open_db.return_value = self.global_db
            result = await task.calculate_result(
                {"jobID": "generic", "requester": user, "options": json.dumps({"max_results": 10})})
        self.assertIsInstance(json.loads(result), list)  # degraded mode ran, no crash

    async def test_empty_candidate_pool_falls_back_to_global_ranking(self):
        author = Keys.generate()
        note = await self.save_global(1, author, age_secs=30)
        await self.save_global(7, Keys.generate(), tags=[["e", note.id().to_hex()]], age_secs=20)
        user = Keys.generate().public_key().to_hex()
        task, cache = self.make_task(user)
        cache.get_requester_context = AsyncMock(return_value={
            "actions_by_author": {}, "liked_authors": set(),
            "follows": set(), "muted": set(), "keywords": []})
        with patch("nostr_dvm.tasks.content_discovery_for_you.NostrLmdb.open",
                   new_callable=AsyncMock) as open_db:
            open_db.return_value = self.global_db
            result = await task.calculate_result(
                {"jobID": "generic", "requester": user, "options": json.dumps({"max_results": 10})})
        entries = [tuple(t) for t in json.loads(result)]
        self.assertIn(("e", note.id().to_hex()), entries)
        cache.get_requester_context.assert_awaited_once()


    async def seed_reply_dedupe_notes(self, with_reply):
        requester = Keys.generate().public_key().to_hex()
        author_one = Keys.generate()
        author_two = Keys.generate()
        author_three = Keys.generate()
        note_one = await self.save_global(1, author_one, age_secs=30)
        if with_reply:
            # NIP-10 reply to a top-level note: root and reply tags carry the same id
            await self.save_global(1, Keys.generate(), tags=[
                ["e", note_one.id().to_hex(), "", "root"], ["e", note_one.id().to_hex(), "", "reply"]], age_secs=25)
        mid_note = await self.save_global(1, author_two, age_secs=30)
        for _ in range(9):
            await self.save_global(7, Keys.generate(), tags=[["e", mid_note.id().to_hex()]], age_secs=20)
        low_note = await self.save_global(1, author_three, age_secs=30)
        await self.save_global(7, Keys.generate(), tags=[["e", low_note.id().to_hex()]], age_secs=20)

        task, cache = self.make_task(requester)
        cache.get_requester_context = AsyncMock(return_value={
            "actions_by_author": {}, "liked_authors": set(),
            "follows": {author_one.public_key().to_hex(),
                        author_two.public_key().to_hex(),
                        author_three.public_key().to_hex()},
            "muted": set(), "keywords": []})
        with patch("nostr_dvm.tasks.content_discovery_for_you.NostrLmdb.open",
                   new_callable=AsyncMock) as open_db:
            open_db.return_value = self.global_db
            result = await task.calculate_result(
                {"jobID": "generic", "requester": requester, "options": json.dumps({"max_results": 2})})
        ids = [entry[1] for entry in json.loads(result)]
        return ids, note_one.id().to_hex(), mid_note.id().to_hex()

    async def test_reply_to_note_counts_once_per_note(self):
        ids, note_one_id, mid_id = await self.seed_reply_dedupe_notes(with_reply=True)
        # reply contributes 13.5 once: note_one scores 13.6*ln(2)/4 = 2.36 below mid's 3.18;
        # double-counted it would score 27.1*ln(2)/4 = 4.70 and take first place
        self.assertEqual(ids, [mid_id, note_one_id])

    async def test_note_without_reply_stays_out_of_top_results(self):
        ids, note_one_id, _ = await self.seed_reply_dedupe_notes(with_reply=False)
        self.assertNotIn(note_one_id, ids)


class EngagementIndexTests(unittest.IsolatedAsyncioTestCase):
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

    def make_task(self):
        from nostr_dvm.tasks.content_discovery_for_you import DiscoverContentForYou
        task = object.__new__(DiscoverContentForYou)
        task.db_since = 7 * 24 * 3600
        task.dvm_config = SimpleNamespace(EXCLUDE_SELF_ENGAGEMENT=True, LOGLEVEL=LogLevel.ERROR,
                                          NIP89=SimpleNamespace(NAME="For You"))
        task._engagement_index = None
        task._engagement_index_built_at = 0
        return task

    async def test_index_groups_events_dedupes_and_aggregates(self):
        from nostr_dvm.utils.engagement_profile_utils import weights_from_engager_authors
        author = Keys.generate()
        note = await self.save_global(1, author, age_secs=30)
        note_id = note.id().to_hex()
        author_hex = author.public_key().to_hex()
        fan = Keys.generate()
        await self.save_global(1, fan, tags=[
            ["e", note_id, "", "root"], ["e", note_id, "", "reply"]], age_secs=20)
        engager = Keys.generate()
        await self.save_global(7, engager, tags=[["e", note_id]], age_secs=25)

        task = self.make_task()
        index = await task._build_engagement_index(self.global_db,
                                                   Timestamp.from_secs(self.now - 3600))
        self.assertEqual(len(index["engagement_by_note"][note_id]), 2)  # reply + reaction, deduped tags
        self.assertIn(fan.public_key().to_hex(), index["engagers_by_author"][author_hex])
        self.assertAlmostEqual(index["total_by_author"][author_hex], 14.0)
        self.assertIn(engager.public_key().to_hex(), index["engager_authors"])
        self.assertIn(author_hex, index["engager_authors"][engager.public_key().to_hex()])
        # OON weights work straight off the precomputed graph (both fan and engager
        # engaged with the author; each contributes 1 at overlap threshold 1)
        weights = weights_from_engager_authors(index["engager_authors"],
                                               requester_hex="a" * 64,
                                               liked_authors={author_hex},
                                               overlap_threshold=1)
        self.assertEqual(weights.get(author_hex), 2)

    async def test_index_reused_within_ttl_and_rebuilt_after(self):
        task = self.make_task()
        calls = {"n": 0}
        original = type(task)._build_engagement_index

        async def counting(inner, database, graph_since):
            calls["n"] += 1
            return await original(inner, database, graph_since)

        with patch.object(type(task), "_build_engagement_index", counting):
            await task._get_engagement_index(self.global_db, now_secs=self.now)
            await task._get_engagement_index(self.global_db, now_secs=self.now + 400)  # within 600s TTL
            self.assertEqual(calls["n"], 1)
            await task._get_engagement_index(self.global_db, now_secs=self.now + 601)  # expired
            self.assertEqual(calls["n"], 2)

    async def test_calculate_result_builds_index_once_across_requests(self):
        from nostr_dvm.tasks.content_discovery_for_you import DiscoverContentForYou
        author = Keys.generate()
        note = await self.save_global(1, author, age_secs=30)
        await self.save_global(7, Keys.generate(), tags=[["e", note.id().to_hex()]], age_secs=20)
        user = Keys.generate().public_key().to_hex()

        task = self.make_task()
        cache = MagicMock()
        cache.get_requester_context = AsyncMock(return_value={
            "actions_by_author": {}, "liked_authors": set(),
            "follows": {author.public_key().to_hex()}, "muted": set(), "keywords": []})
        task.profile_cache = cache

        calls = {"n": 0}
        original = type(task)._build_engagement_index

        async def counting(inner, database, graph_since):
            calls["n"] += 1
            return await original(inner, database, graph_since)

        with patch("nostr_dvm.tasks.content_discovery_for_you.NostrLmdb.open",
                   new_callable=AsyncMock) as open_db, \
                patch.object(type(task), "_build_engagement_index", counting):
            open_db.return_value = self.global_db
            for _ in range(2):
                result = await task.calculate_result(
                    {"jobID": "generic", "requester": user, "options": json.dumps({"max_results": 10})})
            self.assertEqual(calls["n"], 1)  # two requests, one index build
        self.assertIn(("e", note.id().to_hex()), [tuple(t) for t in json.loads(result)])


if __name__ == "__main__":
    unittest.main()
