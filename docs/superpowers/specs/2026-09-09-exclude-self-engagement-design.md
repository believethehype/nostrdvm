# Design: Exclude self-engagement from popularity DVMs

**Date:** 2026-09-09
**Status:** Approved

## Problem

The popularity discovery DVMs rank notes by engagement: reactions (kind 7), reposts (kind 6),
zaps (kind 9735), kind-1 replies, and kind-1111 comments. The central counting helper is
`query_engagement()` in `nostr_dvm/utils/discovery_utils.py`, and every caller scores a note as
`len(reactions_vec)` — the raw count of matching events, with no author filtering.

This means an author can inflate their own note's score by reacting to, replying to, reposting,
or zapping it themselves. The goal is to exclude the note author's own engagement so scores
reflect engagement from other users.

Precedent: `content_discovery_currently_popular_by_top_zaps.py` already skips self-zaps when
summing zap amounts, but its `min_reactions` gate still counts them.

## Requirements

- Exclude a note's author from its engagement count across all engagement kinds:
  reactions (7), reposts (6), zaps (9735), replies (1), comments (1111).
- Opt-out via a new `DVMConfig.EXCLUDE_SELF_ENGAGEMENT` flag, default `True`.
- The `min_reactions` threshold applies to the filtered count, so a note whose engagement is
  entirely self-engagement is excluded from results.
- Align `by_top_zaps` so self-zaps are also excluded from its `min_reactions` gate.

## Approach (approved: A)

Central filtering inside `query_engagement()` with an explicit author parameter; call sites pass
the parent note's author when the config flag is on. No extra database queries; one filtering
implementation.

## Changes

### 1. Config flag — `nostr_dvm/utils/dvmconfig.py`

New class attribute next to `UPDATE_DATABASE`:

```python
EXCLUDE_SELF_ENGAGEMENT = True  # Do not count a note author's own reactions/replies/reposts/zaps towards its engagement score
```

### 2. Central filter — `nostr_dvm/utils/discovery_utils.py`

`query_engagement()` gains an optional parameter (with `PublicKey` imported from `nostr_sdk`):

```python
async def query_engagement(database, event_id: EventId, since: Timestamp,
                           exclude_author: PublicKey = None):
```

After the existing `merge_events(...)` call, drop any event whose `author().to_hex()` equals
`exclude_author.to_hex()`. When `exclude_author is None`, behavior is unchanged (list returned
as before). Comparison is on hex strings; no new failure modes.

### 3. Call sites (8 tasks)

Each caller computes the author to exclude and passes it:

```python
exclude = event.author() if self.dvm_config.EXCLUDE_SELF_ENGAGEMENT else None
reactions = await query_engagement(database, event.id(), since, exclude_author=exclude)
```

Tasks to update:

1. `content_discovery_currently_popular.py` (calculate_result)
2. `content_discovery_currently_popular_followers.py`
3. `content_discovery_currently_popular_nonfollowers.py`
4. `content_discovery_currently_popular_topic.py`
5. `content_discovery_currently_popular_gallery.py` — author checked is the scored image note
   (`event`), not the gallery wrapper event (`ge_event`) that receives the score.
6. `content_discovery_currently_popular_mostr.py`
7. `content_discovery_currently_popular_tweets.py`
8. `content_discovery_on_this_day.py`

All eight already have `self.dvm_config` in scope in `calculate_result`. The `min_reactions`
gate then applies to the filtered count.

### 4. Zap DVM alignment — `content_discovery_currently_popular_by_top_zaps.py`

Restructure the zap loop: first build the list of valid zaps (skipping zaps authored by the
note author, only when `EXCLUDE_SELF_ENGAGEMENT` is true), then gate on
`len(valid_zaps) >= self.min_reactions` before summing amounts. Net behavior when the flag is
on: self-zaps count toward neither the threshold nor the amount. When off: current behavior.

### 5. Test — `tests/discovery_self_engagement.py`

The repo has no pytest infrastructure; `tests/` contains manual scripts. Add a standalone
script that:

1. Opens a temporary LMDB database.
2. Creates a note (kind 1) by author A.
3. Creates a self-reaction (kind 7, author A), a self-reply (kind 1, author A), a self-comment
   (kind 1111, author A), a self-repost (kind 6, author A), a self-zap (kind 9735, author A),
   and one genuine reaction (kind 7, author B).
4. Asserts `query_engagement(..., exclude_author=A)` returns 1 event (author B's reaction) and
   `query_engagement(...)` (no exclude) returns 6 events.

## Out of scope

- Changes to which kinds count as engagement (`engagement_kinds()` stays as is).
- Weighting (e.g. zaps worth more than reactions).
- Anti-gaming beyond author exclusion (e.g. web-of-trust weighting, dedup of multiple
  reactions from the same user).
