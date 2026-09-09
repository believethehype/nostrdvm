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
