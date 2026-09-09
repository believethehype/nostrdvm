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
