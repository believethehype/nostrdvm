# Exclude Self-Engagement from Popularity DVMs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Popularity discovery DVMs must not count a note author's own reactions/replies/comments/reposts/zaps towards that note's engagement score, so self-engagement can't fake popularity.

**Architecture:** Central filtering in `query_engagement()` (the shared counting helper in `nostr_dvm/utils/discovery_utils.py`) via a new optional `exclude_author` parameter. All 8 popular-DVM call sites pass the parent note's author when the new `DVMConfig.EXCLUDE_SELF_ENGAGEMENT` flag (default `True`) is on. The zap-amount DVM gets its `min_reactions` gate aligned with its existing self-zap amount skip. Spec: `docs/superpowers/specs/2026-09-09-exclude-self-engagement-design.md`.

**Tech Stack:** Python 3.12, `nostr_sdk` (rust-nostr Python bindings), `unittest.IsolatedAsyncioTestCase` (run via `python -m unittest discover -s tests/unit -t . -v`, same as CI).

## Global Constraints

- Test command: `python -m unittest tests.unit.test_discovery_engagement -v` for the touched test file; full suite: `python -m unittest discover -s tests/unit -t . -v`.
- `EXCLUDE_SELF_ENGAGEMENT` default is `True` (exact name, verbatim from spec).
- `query_engagement()` signature must stay backward compatible: `exclude_author` is the 4th positional-optional param, `None` keeps old behavior.
- Follow existing code style in each file (inline comments allowed, 4-space indent, no reformatting of untouched code).
- Do not refactor anything outside the listed edits.
- nostr_sdk `Event` objects expose `.author()` (→ `PublicKey`), `.id()` (→ `EventId`), `.created_at()`; `PublicKey.to_hex()` gives the 64-char hex string used for comparison.

---

### Task 1: Config flag + `exclude_author` param in `query_engagement()`

**Files:**
- Modify: `nostr_dvm/utils/dvmconfig.py` (add flag near line 71, next to `UPDATE_DATABASE`)
- Modify: `nostr_dvm/utils/discovery_utils.py:3` (import) and `:25-29` (`query_engagement`)
- Test: `tests/unit/test_discovery_engagement.py`

**Interfaces:**
- Consumes: existing `query_engagement(database, event_id: EventId, since: Timestamp)` returning `list[Event]` (deduped via `merge_events`).
- Produces: `query_engagement(database, event_id: EventId, since: Timestamp, exclude_author: PublicKey = None) -> list[Event]` — all later tasks call it with `exclude_author=`. Also produces `DVMConfig.EXCLUDE_SELF_ENGAGEMENT: bool = True`, read by Tasks 2 and 3.

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_discovery_engagement.py`, add this import to the existing import block (after the existing `from nostr_dvm.utils...` imports):

```python
from nostr_dvm.utils.dvmconfig import DVMConfig
```

Then add these two test methods inside `class DiscoveryEngagementTests`:

```python
    def test_dvm_config_excludes_self_engagement_by_default(self):
        self.assertTrue(DVMConfig.EXCLUDE_SELF_ENGAGEMENT)

    async def test_query_engagement_excludes_note_author_self_engagement(self):
        author = Keys.generate()
        other = Keys.generate()
        note = EventBuilder(Kind(1), "note").custom_created_at(
            Timestamp.from_secs(self.now - 10)).finalize(author)
        await self.database.save_event(note)
        note_id = note.id().to_hex()

        async def save_with(kind, keys, tags):
            event = EventBuilder(Kind(kind), "engagement").tags(
                [Tag.parse(tag) for tag in tags]).custom_created_at(
                Timestamp.from_secs(self.now - 5)).finalize(keys)
            await self.database.save_event(event)
            return event

        self_reaction = await save_with(7, author, [["e", note_id]])
        self_reply = await save_with(1, author, [["e", note_id]])
        self_comment = await save_with(1111, author,
                                       [["E", note_id], ["e", note_id], ["K", "1"], ["k", "1"]])
        self_repost = await save_with(6, author, [["e", note_id]])
        self_zap = await save_with(9735, author, [["e", note_id]])
        other_reaction = await save_with(7, other, [["e", note_id]])

        all_events = await query_engagement(self.database, note.id(), self.since)
        self.assertEqual({event.id().to_hex() for event in all_events},
                         {event.id().to_hex() for event in
                          [self_reaction, self_reply, self_comment, self_repost, self_zap, other_reaction]})
        self.assertEqual(len(all_events), 6)

        filtered = await query_engagement(self.database, note.id(), self.since,
                                          exclude_author=author.public_key())
        self.assertEqual([event.id().to_hex() for event in filtered],
                         [other_reaction.id().to_hex()])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_discovery_engagement -v`
Expected: FAIL — `AttributeError: <class 'nostr_dvm.utils.dvmconfig.DVMConfig'> ... EXCLUDE_SELF_ENGAGEMENT` on the flag test, and `TypeError: query_engagement() got an unexpected keyword argument 'exclude_author'` on the filter test. All previously existing tests still PASS.

- [ ] **Step 3: Add the config flag**

In `nostr_dvm/utils/dvmconfig.py`, directly after the `UPDATE_DATABASE` line, add:

```python
    EXCLUDE_SELF_ENGAGEMENT = True  # Do not count a note author's own reactions/replies/reposts/zaps towards its engagement score
```

- [ ] **Step 4: Add the `exclude_author` parameter**

In `nostr_dvm/utils/discovery_utils.py`, update the import on line 3 to add `PublicKey`:

```python
from nostr_sdk import EventId, Filter, PublicKey, ReqTarget, SingleLetterTag, SyncDirection, SyncOptions, Timestamp
```

Replace the whole `query_engagement` function with:

```python
async def query_engagement(database, event_id: EventId, since: Timestamp,
                           exclude_author: PublicKey = None):
    parent_filter = Filter().kinds(engagement_kinds()).event(event_id).since(since)
    root_filter = Filter().kind(EventDefinitions.KIND_NIP22_COMMENT).custom_tags(
        SingleLetterTag.from_byte(ord('E')), [event_id.to_hex()]).since(since)
    events = merge_events(await database.query(parent_filter), await database.query(root_filter))
    if exclude_author is not None:
        author_hex = exclude_author.to_hex()
        events = [event for event in events if event.author().to_hex() != author_hex]
    return events
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_discovery_engagement -v`
Expected: all PASS, including the two new tests and all pre-existing tests (backward compatibility: no `exclude_author` → unchanged results).

- [ ] **Step 6: Commit**

```bash
git add nostr_dvm/utils/dvmconfig.py nostr_dvm/utils/discovery_utils.py tests/unit/test_discovery_engagement.py
git commit -m "Add exclude_author to query_engagement and EXCLUDE_SELF_ENGAGEMENT config flag"
```

---

### Task 2: Pass the note author at the 8 popular-DVM call sites

**Files:**
- Modify (8 task files, exact locations listed per step below):
  - `nostr_dvm/tasks/content_discovery_currently_popular.py` (~line 138)
  - `nostr_dvm/tasks/content_discovery_currently_popular_followers.py` (~line 146)
  - `nostr_dvm/tasks/content_discovery_currently_popular_nonfollowers.py` (~line 197)
  - `nostr_dvm/tasks/content_discovery_currently_popular_topic.py` (~line 189)
  - `nostr_dvm/tasks/content_discovery_currently_popular_gallery.py` (~line 184)
  - `nostr_dvm/tasks/content_discovery_currently_popular_mostr.py` (~line 136)
  - `nostr_dvm/tasks/content_discovery_currently_popular_tweets.py` (~line 164)
  - `nostr_dvm/tasks/content_discovery_on_this_day.py` (~line 128)
- Test: `tests/unit/test_discovery_engagement.py`

**Interfaces:**
- Consumes: `query_engagement(..., exclude_author: PublicKey = None)` and `DVMConfig.EXCLUDE_SELF_ENGAGEMENT` from Task 1.
- Produces: popular-DVM scoring that respects the flag; no interface changes.

- [ ] **Step 1: Make the existing popular-task test flag-aware and add a failing exclusion test**

In `tests/unit/test_discovery_engagement.py`:

(a) In `test_popular_uses_shared_database_and_counts_both_reply_kinds`, update the config namespace (this test verifies reply-kind counting with legacy behavior, so it opts out of exclusion):

Old:
```python
        config = SimpleNamespace(DATABASE=self.database, UPDATE_DATABASE=False,
                                 LOGLEVEL=LogLevel.ERROR, NIP89=SimpleNamespace(NAME="test"))
```
New:
```python
        config = SimpleNamespace(DATABASE=self.database, UPDATE_DATABASE=False,
                                 EXCLUDE_SELF_ENGAGEMENT=False,
                                 LOGLEVEL=LogLevel.ERROR, NIP89=SimpleNamespace(NAME="test"))
```

(b) Update the `save()` helper to accept an optional author (needed by new tests; defaults preserve existing behavior):

Old:
```python
    async def save(self, kind=1, tags=(), age=10):
        event = EventBuilder(Kind(kind), str(tags)).tags([Tag.parse(tag) for tag in tags]).custom_created_at(
            Timestamp.from_secs(self.now - age)).finalize(self.keys)
        await self.database.save_event(event)
        return event
```
New:
```python
    async def save(self, kind=1, tags=(), age=10, keys=None):
        event = EventBuilder(Kind(kind), str(tags)).tags([Tag.parse(tag) for tag in tags]).custom_created_at(
            Timestamp.from_secs(self.now - age)).finalize(keys or self.keys)
        await self.database.save_event(event)
        return event
```

(c) Add this new test method to the class:

```python
    async def test_popular_excludes_author_self_engagement(self):
        note = await self.save()
        note_id = note.id().to_hex()
        await self.save(7, [["e", note_id]])  # self reaction
        await self.save(1, [["e", note_id]])  # self reply
        task = object.__new__(DicoverContentCurrentlyPopular)
        task.options = {"db_name": "must-not-open-this-path", "db_since": 3600}
        # min_reactions is 2; the note has exactly 2 self-engagement events:
        # excluded when the flag is on (count 0), included when off (count 2).
        for exclude_self, expected in [(True, []), (False, [["e", note_id]])]:
            config = SimpleNamespace(DATABASE=self.database, UPDATE_DATABASE=False,
                                     EXCLUDE_SELF_ENGAGEMENT=exclude_self,
                                     LOGLEVEL=LogLevel.ERROR, NIP89=SimpleNamespace(NAME="test"))
            task.dvm_config = config
            with patch("nostr_dvm.tasks.content_discovery_currently_popular.init_db",
                       new_callable=AsyncMock) as open_db:
                await task.init_dvm("test", config, None)
                open_db.assert_not_awaited()
            self.assertEqual(json.loads(task.result), expected)
```

- [ ] **Step 2: Run tests to verify the new test fails**

Run: `python -m unittest tests.unit.test_discovery_engagement -v`
Expected: `test_popular_excludes_author_self_engagement` FAILS on the `(True, [])` case — the call sites don't read the flag yet, so the note is still counted and `task.result` contains it. All other tests PASS.

- [ ] **Step 3: Update all 8 call sites**

Every edit inserts one line before the `query_engagement(...)` call and adds `exclude_author=exclude` to the call. Apply exactly these edits:

(a) `nostr_dvm/tasks/content_discovery_currently_popular.py`:

Old:
```python
            if event.created_at().as_secs() > timestamp_since:
                reactions = await query_engagement(database, event.id(), since)
```
New:
```python
            if event.created_at().as_secs() > timestamp_since:
                exclude = event.author() if self.dvm_config.EXCLUDE_SELF_ENGAGEMENT else None
                reactions = await query_engagement(database, event.id(), since, exclude_author=exclude)
```

(b) `nostr_dvm/tasks/content_discovery_currently_popular_followers.py`:

Old:
```python
            for event in events_vec:
                # if event.created_at().as_secs() > timestamp_since:
                reactions = await query_engagement(cli.database(), event.id(), since)
```
New:
```python
            for event in events_vec:
                # if event.created_at().as_secs() > timestamp_since:
                exclude = event.author() if self.dvm_config.EXCLUDE_SELF_ENGAGEMENT else None
                reactions = await query_engagement(cli.database(), event.id(), since, exclude_author=exclude)
```

(c) `nostr_dvm/tasks/content_discovery_currently_popular_nonfollowers.py`:

Old:
```python
            if event.author().to_hex() in followings:
                continue

            reactions = await query_engagement(self.database, event.id(), since)
```
New:
```python
            if event.author().to_hex() in followings:
                continue

            exclude = event.author() if self.dvm_config.EXCLUDE_SELF_ENGAGEMENT else None
            reactions = await query_engagement(self.database, event.id(), since, exclude_author=exclude)
```

(d) `nostr_dvm/tasks/content_discovery_currently_popular_topic.py`:

Old:
```python
                    if not any(ele in event.content().lower() for ele in self.avoid_list):
                        reactions = await query_engagement(self.database, event.id(), since)
```
New:
```python
                    if not any(ele in event.content().lower() for ele in self.avoid_list):
                        exclude = event.author() if self.dvm_config.EXCLUDE_SELF_ENGAGEMENT else None
                        reactions = await query_engagement(self.database, event.id(), since, exclude_author=exclude)
```

(e) `nostr_dvm/tasks/content_discovery_currently_popular_gallery.py`:

Old:
```python
                    if len(deletions) > 0:
                        print("Deleted event, skipping")
                        continue

                    reactions = await query_engagement(databasegallery, event.id(), since)
```
New:
```python
                    if len(deletions) > 0:
                        print("Deleted event, skipping")
                        continue

                    exclude = event.author() if self.dvm_config.EXCLUDE_SELF_ENGAGEMENT else None
                    reactions = await query_engagement(databasegallery, event.id(), since, exclude_author=exclude)
```

(f) `nostr_dvm/tasks/content_discovery_currently_popular_mostr.py`:

Old:
```python
            if event.created_at().as_secs() > timestamp_since:
                reactions = await query_engagement(database, event.id(), since)
```
New:
```python
            if event.created_at().as_secs() > timestamp_since:
                exclude = event.author() if self.dvm_config.EXCLUDE_SELF_ENGAGEMENT else None
                reactions = await query_engagement(database, event.id(), since, exclude_author=exclude)
```

(g) `nostr_dvm/tasks/content_discovery_currently_popular_tweets.py`:

Old:
```python
                    if is_reply:
                        continue
                    reactions = await query_engagement(self.database, event.id(), since)
```
New:
```python
                    if is_reply:
                        continue
                    exclude = event.author() if self.dvm_config.EXCLUDE_SELF_ENGAGEMENT else None
                    reactions = await query_engagement(self.database, event.id(), since, exclude_author=exclude)
```

(h) `nostr_dvm/tasks/content_discovery_on_this_day.py`:

Old:
```python
            if event.created_at().as_secs() > timestamp_since:
                reactions = await query_engagement(database, event.id(), since)
```
New:
```python
            if event.created_at().as_secs() > timestamp_since:
                exclude = event.author() if self.dvm_config.EXCLUDE_SELF_ENGAGEMENT else None
                reactions = await query_engagement(database, event.id(), since, exclude_author=exclude)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_discovery_engagement -v`
Expected: all PASS, including `test_popular_excludes_author_self_engagement`.

- [ ] **Step 5: Verify nothing else broke**

Run: `python -m unittest discover -s tests/unit -t . -v`
Expected: entire unit suite PASS. If any other unit test constructs one of the 8 tasks with a `SimpleNamespace` config, add `EXCLUDE_SELF_ENGAGEMENT=False` to that namespace (only if a failure shows up — do not preemptively change passing tests).

- [ ] **Step 6: Syntax-check the modified task files**

Run: `python -m compileall -q nostr_dvm/tasks/content_discovery_currently_popular.py nostr_dvm/tasks/content_discovery_currently_popular_followers.py nostr_dvm/tasks/content_discovery_currently_popular_nonfollowers.py nostr_dvm/tasks/content_discovery_currently_popular_topic.py nostr_dvm/tasks/content_discovery_currently_popular_gallery.py nostr_dvm/tasks/content_discovery_currently_popular_mostr.py nostr_dvm/tasks/content_discovery_currently_popular_tweets.py nostr_dvm/tasks/content_discovery_on_this_day.py`
Expected: exit code 0, no output.

- [ ] **Step 7: Commit**

```bash
git add nostr_dvm/tasks/content_discovery_currently_popular.py nostr_dvm/tasks/content_discovery_currently_popular_followers.py nostr_dvm/tasks/content_discovery_currently_popular_nonfollowers.py nostr_dvm/tasks/content_discovery_currently_popular_topic.py nostr_dvm/tasks/content_discovery_currently_popular_gallery.py nostr_dvm/tasks/content_discovery_currently_popular_mostr.py nostr_dvm/tasks/content_discovery_currently_popular_tweets.py nostr_dvm/tasks/content_discovery_on_this_day.py tests/unit/test_discovery_engagement.py
git commit -m "Popular discovery DVMs exclude the note author's own engagement"
```

---

### Task 3: Align `by_top_zaps` gate with its self-zap skip

**Files:**
- Modify: `nostr_dvm/tasks/content_discovery_currently_popular_by_top_zaps.py:124-140` (zap loop pre-filter)
- Test: `tests/unit/test_discovery_engagement.py`

**Interfaces:**
- Consumes: `DVMConfig.EXCLUDE_SELF_ENGAGEMENT` from Task 1.
- Produces: zap DVM gate that excludes self-zaps when the flag is on; no interface changes.

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_discovery_engagement.py`, add this import to the existing import block:

```python
from nostr_dvm.tasks.content_discovery_currently_popular_by_top_zaps import DicoverContentCurrentlyPopularZaps
```

Then add this test method to the class:

```python
    async def test_top_zaps_gate_excludes_self_zaps(self):
        note = await self.save()
        note_id = note.id().to_hex()
        await self.save(9735, [["e", note_id],
                               ["bolt11", "lnbc10m1fake"],
                               ["preimage", "selfpreimage"]])
        await self.save(9735, [["e", note_id],
                               ["bolt11", "lnbc2m1fake"],
                               ["preimage", "otherpreimage"]], keys=Keys.generate())
        task = object.__new__(DicoverContentCurrentlyPopularZaps)
        task.options = {"db_name": "must-not-open-this-path", "db_since": 3600}
        task.min_reactions = 2
        task.result = ""
        task.request_form = {"jobID": "generic", "options": json.dumps({"max_results": 200})}
        # min_reactions is 2 and the note has 1 self-zap + 1 genuine zap:
        # excluded when the flag is on (1 valid zap), included when off (2 zaps).
        for exclude_self, expected in [(True, []), (False, [["e", note_id]])]:
            task.dvm_config = SimpleNamespace(EXCLUDE_SELF_ENGAGEMENT=exclude_self,
                                              LOGLEVEL=LogLevel.ERROR,
                                              NIP89=SimpleNamespace(NAME="test"))
            with patch("nostr_dvm.tasks.content_discovery_currently_popular_by_top_zaps.NostrLmdb.open",
                       new_callable=AsyncMock) as open_db:
                open_db.return_value = self.database
                result = await task.calculate_result(task.request_form)
            self.assertEqual(json.loads(result), expected)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_discovery_engagement -v`
Expected: `test_top_zaps_gate_excludes_self_zaps` FAILS on the `(True, [])` case — the gate still counts the self-zap, so the note is included.

- [ ] **Step 3: Implement the pre-filter**

In `nostr_dvm/tasks/content_discovery_currently_popular_by_top_zaps.py`, find (inside `calculate_result`, around lines 129-138):

Old:
```python
                invoice_amount = 0
                event_author = event.author().to_hex()
                zaps_vec = zaps
                if len(zaps_vec) >= self.min_reactions:
```
New:
```python
                invoice_amount = 0
                event_author = event.author().to_hex()
                zaps_vec = zaps
                if self.dvm_config.EXCLUDE_SELF_ENGAGEMENT:
                    zaps_vec = [zap for zap in zaps_vec if event_author != zap.author().to_hex()]
                if len(zaps_vec) >= self.min_reactions:
```

Leave the inner `if event_author == zap.author().to_hex(): continue  # Skip self zaps..` line untouched: when the flag is on the pre-filtered list contains no self-zaps so it is a no-op; when the flag is off it preserves the current amount-summation behavior.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_discovery_engagement -v`
Expected: all PASS.

- [ ] **Step 5: Full suite + syntax check**

Run: `python -m unittest discover -s tests/unit -t . -v && python -m compileall -q nostr_dvm/tasks/content_discovery_currently_popular_by_top_zaps.py`
Expected: entire unit suite PASS; compileall exit code 0.

- [ ] **Step 6: Commit**

```bash
git add nostr_dvm/tasks/content_discovery_currently_popular_by_top_zaps.py tests/unit/test_discovery_engagement.py
git commit -m "Top-zaps DVM: exclude self-zaps from the min_reactions gate"
```
