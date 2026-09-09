# Design: "For You" personalized content DVM (X-algorithm-inspired)

**Date:** 2026-09-09
**Status:** Approved
**Reference:** https://github.com/xai-org/x-algorithm (X For You feed)

## Goal

A fully personalized content-discovery DVM: per-requester ranking of recent Nostr notes,
mixing in-network notes (from the requester's follows) with out-of-network discovery
(co-engagement similarity), scored with X-style weighted multi-action signals, diversity
and boost adjustments, and visibility filters. This is the personalized, multi-signal
successor to the existing global "popular" DVMs, built on the same synced data.

## Decisions (from brainstorming)

- **Fully personalized:** every request is scored for the specific requester.
- **Candidates:** in-network (follows) + out-of-network via engagement-graph similarity,
  with X's OON discount.
- **Signals:** full v1 set — weighted actions, author affinity, author credibility,
  recency, OON discount, new-author boost, author diversity decay, negative filters.
- **Freshness:** per-user profiles cached with TTL (~1h); requests never hit relays on
  cache hits.
- **History depth:** 7 days for user profiles and the engagement graph.

## Architecture

| Unit | Responsibility |
|---|---|
| `nostr_dvm/tasks/content_discovery_for_you.py` | The DVM task: `DicoverContentForYou`, `KIND_NIP90_CONTENT_DISCOVERY`, `TASK = "discover-content"`, `personalized=True`, `FIX_COST = 0`. Output: JSON list of `["e", <id>]` tags like the other discovery DVMs. |
| `nostr_dvm/utils/engagement_profile_utils.py` | Pure-ish logic: profile build/cache, affinity, co-engagement OON discovery, credibility, ranking math (weights, recency, diversity, boosts). I/O (DB queries, relay sync) separated from pure functions for testability. |
| `tests/unit/test_for_you_ranking.py` | Unit tests for the math, profile affinity, OON selection, filters, and a `calculate_result` test with the mocked-client pattern from `test_discovery_engagement.py`. |

**Data stores**

- `db/nostr_foryou.db` — the DVM's own global DB: notes (kind 1) and engagement
  (kinds 1, 6, 7, 9735, 1111) synced with `engagement_kinds()` + `sync_discovery_database()`
  on the scheduler (`UPDATE_DATABASE = True`), events older than `db_since` deleted
  (default 7 days). Self-contained, like the other popular DVMs.
- `db/nostr_profiles_foryou.db` — per-user engagement profiles: each user's own
  engagement events (kinds 1, 6, 7, 9735) from the last 7 days, synced per user on cache
  miss. Freshness tracked in an in-memory `{pubkey: last_built_ts}` dict (TTL 1 hour).
- Follows (kind 3) and mute lists (kind 10000) per requester: fetched on cache miss,
  TTL 1 hour, kept in memory.

**Config knobs (task options, not DVMConfig):** `db_name`, `db_since` (default
7 days), `history_days` (default 7), `profile_ttl_seconds` (default 3600),
`max_results` (NIP-90 param, default 200).

## Data flow (per request)

1. Requester pubkey: `param user` tag if present (hex or npub), else the request author.
2. Profile = cached or built: sync requester's engagement events (7d) into the profile DB;
   fetch follows + mute list. Cache miss costs a few seconds; hits are local-only.
3. **Candidate pools** (local DB queries only):
   - In-network: top-level kind-1 notes, `author ∈ follows`, created within 48h.
   - OON: co-engagement graph — from the global DB, users whose engaged-author set
     overlaps the requester's liked-author set by ≥ 3 authors are co-engagers; candidate
     authors = authors co-engagers engage with, minus follows/mutes/self; candidates =
     their top-level notes ≤ 48h, ranked by author weight (sum of overlaps) × note
     engagement, capped at 300. In-network capped at 200. Total ≤ 500.
4. **Filters (pre-scoring):** drop self-posts; age > 48h; blocked/muted authors (mute
   list p tags); muted keywords (mute list t tags matched in content); OON replies and
   reposts (OON pool is top-level notes only, so this holds by construction).
5. **Scoring and selection** (below), then top-K by final score.
6. Output `["e", id]` list; `post_process` converts to text events when requested
  (same as existing discovery tasks).

## Scoring formula

```
final(note) = base × affinity(author) × credibility(author) × recency × oon × boost
```

- `base = 0.1 + Σ action_weight(e)` over the note's engagement events (7d window,
  **self-engagement excluded** via `query_engagement(..., exclude_author=note_author)`
  when `EXCLUDE_SELF_ENGAGEMENT`; the floor 0.1 keeps zero-engagement followed notes
  rankable).
- `action_weight`: reaction 0.5, repost 1.0, reply 13.5, zap `1 + log10(max(sats, 1))`
  (a 100k-sat zap ≈ 6, 1M ≈ 7 — money counts, log-tamed).
- `affinity = min(8, 1 + ln(1 + Σ weights of the requester's own actions on that
  author's notes))` from the profile.
- `credibility = min(1, ln(1 + distinct_engagers_7d(author)) / 4)` — reaches 1 at ~54
  distinct engagers (user-cred-v2-lite).
- `recency = 0.5 ** (age_hours / 24)`.
- `oon = 0.5` if the author is not followed, else 1.0.
- `boost = 1.2` if the author's total weighted engagement in the window is < 5
  (new-author boost), else 1.0.
- **Author diversity (applied during selection, X's repeated-author decay):** walk the
  score-sorted list; the k-th selected note by the same author is multiplied by
  `0.7 ** (k-1)` (floor 0.1); re-sort and take top `max_results`.

All constants live in one `RANKING_PARAMS` dict in `engagement_profile_utils.py`.

## Error handling

- Profile or relay failure during a cache miss → log, degrade to a global ranking
  (popularity-based, from the same global DB) so the requester always gets a feed.
- No engagement history (new user) → affinity neutralized to 1 for all authors; if the
  requester also has no follows → global ranking fallback.
- Empty candidate set → return `"[]"` (existing pattern).
- The scoring path reads local DBs only; relay calls happen exclusively on profile
  cache misses, bounded by the sync timeouts in `sync_discovery_database()`.

## Testing

- Pure math: action weights (incl. zap log-scaling), recency decay, OON discount,
  credibility capping, diversity decay across multiple notes of one author.
- Affinity computed from synthetic profile events; self-engagement of the requester on
  their own notes does not inflate affinity.
- Co-engagement OON: synthetic global DB where an overlapping engager surfaces an
  author the requester doesn't follow; overlap threshold enforced; follows/mutes
  excluded.
- Filters: self-post, 48h age, muted author, muted keyword.
- `calculate_result` end-to-end with mocked clients (empty live fetch, profile cache
  hit, degraded mode on profile failure).

## Explicitly out of scope (v1)

- Seen/served-post tracking (clients do not report impressions).
- Embedding/ML retrieval (Phoenix-lite) — phase 2 upgrade for the OON pool; the
  co-engagement heuristic keeps the same interface so it can be swapped.
- Media/adult classifiers, VM-ranker-style reordering, ads/blending.
- Payments: free like the other discovery DVMs.

## Ops

- Identifier: `discovery_content_for_you` → env keys `DVM_PRIVATE_KEY_DISCOVERY_CONTENT_FOR_YOU`
  and `NIP89_DTAG_DISCOVERY_CONTENT_FOR_YOU`.
- **Key sync:** the first local run generates the private key (and NIP-89 d-tag) via
  `check_and_set_private_key` / `check_and_set_d_tag` and writes them to the local repo
  `.env`. Those exact values must then be copied into `/root/dvm/.env` on the VPS
  **before** first start there, so local and VPS instances share one identity (same
  pubkey, same d-tag → continuous announcements and request routing).
- New pm2 process on the VPS alongside the other DVMs (`for_you.py` script building the
  example DVM), NIP-89 announced as "For You" with `max_results` param.
- Default relays per `build_default_config`; `SYNC_DB_RELAY_LIST` for both DBs.
- Personalized DVMs compute per request; no scheduled result publication needed beyond
  DB sync.
