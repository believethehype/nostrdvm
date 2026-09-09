import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from nostr_sdk import EventBuilder, Filter, Keys, Kind, LogLevel, Tag, Timestamp

from nostr_dvm.tasks.content_discovery_currently_popular import DicoverContentCurrentlyPopular
from nostr_dvm.tasks.content_discovery_currently_popular_by_top_zaps import DicoverContentCurrentlyPopularZaps
from nostr_dvm.tasks.content_discovery_currently_popular_gallery import DicoverContentCurrentlyPopularGallery
from nostr_dvm.tasks.content_discovery_update_db_only import DicoverContentDBUpdateScheduler
from nostr_dvm.utils.database_utils import init_db
from nostr_dvm.utils.discovery_utils import discovery_sync_filters, query_engagement, sync_discovery_database
from nostr_dvm.utils.dvmconfig import DVMConfig


class DiscoveryEngagementTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = await init_db(self.directory.name, print_filesize=False)
        self.now = Timestamp.now().as_secs()
        self.since = Timestamp.from_secs(self.now - 3600)
        self.keys = Keys.generate()

    async def save(self, kind=1, tags=(), age=10, keys=None):
        event = EventBuilder(Kind(kind), str(tags)).tags([Tag.parse(tag) for tag in tags]).custom_created_at(
            Timestamp.from_secs(self.now - age)).finalize(keys or self.keys)
        await self.database.save_event(event)
        return event

    async def test_legacy_and_nip22_parent_and_root_replies_are_deduplicated(self):
        note = await self.save()
        note_id = note.id().to_hex()
        legacy = await self.save(tags=[["e", note_id]])
        direct = await self.save(1111, [["E", note_id], ["e", note_id], ["K", "1"], ["k", "1"]])
        nested = await self.save(1111, [["E", note_id], ["e", direct.id().to_hex()], ["K", "1"], ["k", "1111"]])
        parent_only = await self.save(1111, [["E", "a" * 64], ["e", note_id]])
        reaction = await self.save(7, [["e", note_id]])
        repost = await self.save(6, [["e", note_id]])
        zap = await self.save(9735, [["e", note_id]])
        await self.save(1111, [["E", "b" * 64], ["e", "b" * 64]])
        await self.save(1111, [["E", note_id], ["e", note_id]], age=7200)
        await self.save(1111, [["q", note_id]])
        await self.save(7, [["E", note_id]])
        events = await query_engagement(self.database, note.id(), self.since)
        self.assertEqual({event.id().to_hex() for event in events},
                         {event.id().to_hex() for event in [legacy, direct, nested, parent_only, reaction, repost, zap]})
        self.assertEqual(len(events), 7)

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

    async def test_popular_uses_shared_database_and_counts_both_reply_kinds(self):
        note = await self.save()
        await self.save(tags=[["e", note.id().to_hex()]])
        await self.save(1111, [["E", note.id().to_hex()], ["e", note.id().to_hex()]])
        task = object.__new__(DicoverContentCurrentlyPopular)
        config = SimpleNamespace(DATABASE=self.database, UPDATE_DATABASE=False,
                                 EXCLUDE_SELF_ENGAGEMENT=False,
                                 LOGLEVEL=LogLevel.ERROR, NIP89=SimpleNamespace(NAME="test"))
        task.dvm_config = config
        task.options = {"db_name": "must-not-open-this-path", "db_since": 3600}
        with patch("nostr_dvm.tasks.content_discovery_currently_popular.init_db", new_callable=AsyncMock) as open_db:
            await task.init_dvm("test", config, None)
            open_db.assert_not_awaited()
        self.assertEqual(json.loads(task.result), [["e", note.id().to_hex()]])
        await self.database.delete_events(Filter())
        self.assertEqual(await task.calculate_result(task.request_form), "[]")

    async def test_popular_weights_zaps_above_reactions(self):
        # zapped note: 100k-sat zap (6.0) + one reaction (0.5) -> weighted 6.5 (+0.1 floor)
        zap_note = await self.save(age=30)
        other = Keys.generate()
        await self.save(9735, [["e", zap_note.id().to_hex()], ["bolt11", "lnbc1m1fake"],
                               ["preimage", "p"]], age=20, keys=other)
        await self.save(7, [["e", zap_note.id().to_hex()]], age=20, keys=Keys.generate())
        # liked note: two plain reactions (1.0) -> below the min_reactions gate once weighted
        liked_note = await self.save(age=25)
        await self.save(7, [["e", liked_note.id().to_hex()]], age=20, keys=Keys.generate())
        await self.save(7, [["e", liked_note.id().to_hex()]], age=20, keys=Keys.generate())

        task = object.__new__(DicoverContentCurrentlyPopular)
        config = SimpleNamespace(DATABASE=self.database, UPDATE_DATABASE=False,
                                 EXCLUDE_SELF_ENGAGEMENT=True,
                                 LOGLEVEL=LogLevel.ERROR, NIP89=SimpleNamespace(NAME="test"))
        task.dvm_config = config
        task.options = {"db_name": "must-not-open-this-path", "db_since": 3600}
        with patch("nostr_dvm.tasks.content_discovery_currently_popular.init_db", new_callable=AsyncMock) as open_db:
            await task.init_dvm("test", config, None)
            open_db.assert_not_awaited()
        entries = json.loads(task.result)
        self.assertEqual(entries, [["e", zap_note.id().to_hex()]])

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

    async def test_sync_reports_partial_failure_and_database_count(self):
        client = MagicMock()
        client.sync = AsyncMock(return_value=SimpleNamespace(
            success=["wss://ok"], failed={"wss://broken": "timeout"},
            report=SimpleNamespace(received={"event": []})))
        client.database.return_value.count = AsyncMock(return_value=3)
        with patch("builtins.print") as output:
            await sync_discovery_database(client, Filter(), "test")
        self.assertIn("timeout", str(output.call_args_list))
        self.assertIn("3 matching events", str(output.call_args_list))

    def test_wot_filters_are_bounded_and_preserve_author_coverage(self):
        authors = [Keys.generate().public_key() for _ in range(1001)]
        filters = discovery_sync_filters(self.since, authors)
        decoded = [json.loads(event_filter.as_json()) for event_filter in filters]
        self.assertEqual([len(event_filter["authors"]) for event_filter in decoded], [500, 500, 1])
        self.assertEqual({author for event_filter in decoded for author in event_filter["authors"]},
                         {author.to_hex() for author in authors})
        for event_filter in decoded:
            self.assertEqual(event_filter["since"], self.since.as_secs())
            self.assertEqual(set(event_filter["kinds"]), {1, 6, 7, 1111, 9735})

    def test_empty_wot_does_not_disable_author_filtering(self):
        with self.assertRaises(ValueError):
            discovery_sync_filters(self.since, [])
        self.assertNotIn("authors", json.loads(discovery_sync_filters(self.since)[0].as_json()))

    async def test_failed_scheduler_sync_preserves_data_and_closes_client(self):
        client = MagicMock()
        client.add_relay = AsyncMock()
        client.connect = AsyncMock()
        client.shutdown = AsyncMock()
        client.sync = AsyncMock(return_value=SimpleNamespace(success=[], failed={"wss://broken": "timeout"}))
        client.fetch_events = AsyncMock(return_value=[])
        client.database.return_value.delete_events = AsyncMock()
        task = object.__new__(DicoverContentDBUpdateScheduler)
        task.database = self.database
        task.dvm_config = SimpleNamespace(PRIVATE_KEY=self.keys.secret_key().to_hex(),
                                         SYNC_DB_RELAY_LIST=["wss://broken"], WOT_FILTERING=False,
                                         LOGLEVEL=LogLevel.ERROR, IDENTIFIER="test")
        with patch("nostr_dvm.tasks.content_discovery_update_db_only.ClientBuilder") as builder:
            builder.return_value.authenticator.return_value.database.return_value.relay_limits.return_value.build.return_value = client
            await task.sync_db()
        client.database.return_value.delete_events.assert_not_awaited()
        client.shutdown.assert_awaited_once()
        kinds = json.loads(client.sync.call_args.args[0].as_json())["kinds"]
        self.assertEqual(set(kinds), {1, 6, 7, 1111, 9735})

    async def test_sync_fallback_persists_replies_and_preserves_filter(self):
        event = EventBuilder(Kind(1111), "fallback reply").finalize(self.keys)
        for raises in (False, True):
            with self.subTest(sync_raises=raises):
                await self.database.delete_events(Filter())
                client = MagicMock()
                client.database.return_value = self.database
                client.sync = AsyncMock(return_value=SimpleNamespace(
                    success=[], failed={"wss://relay": "unsupported"}, report=SimpleNamespace(received={})))
                if raises:
                    client.sync.side_effect = RuntimeError("negentropy unavailable")
                client.fetch_events = AsyncMock(return_value=[event])
                event_filter = Filter().kind(Kind(1111)).author(self.keys.public_key()).since(self.since)
                await sync_discovery_database(client, event_filter, "test")
                self.assertEqual(await self.database.count(event_filter), 1)
                client.fetch_events.assert_awaited_once()

    async def test_gallery_falls_back_to_database_when_live_fetch_is_empty(self):
        pic_author_a = Keys.generate()
        pic_author_b = Keys.generate()
        fan_a = Keys.generate()
        fan_b = Keys.generate()
        pic_a = await self.save(20, [], keys=pic_author_a)
        pic_b = await self.save(20, [], keys=pic_author_b)
        await self.save(7, [["e", pic_a.id().to_hex()]], keys=fan_a)
        await self.save(7, [["e", pic_a.id().to_hex()]], keys=fan_b)
        await self.save(7, [["e", pic_b.id().to_hex()]], keys=fan_a)
        await self.save(7, [["e", pic_b.id().to_hex()]], keys=fan_b)

        task = object.__new__(DicoverContentCurrentlyPopularGallery)
        task.options = {"db_name": "must-not-open-this-path", "db_since": 3600}
        task.dvm_config = SimpleNamespace(
            DATABASE=self.database, UPDATE_DATABASE=False, EXCLUDE_SELF_ENGAGEMENT=True,
            PRIVATE_KEY=Keys.generate().secret_key().to_hex(),
            SYNC_DB_RELAY_LIST=["wss://broken"], LOGLEVEL=LogLevel.ERROR,
            NIP89=SimpleNamespace(NAME="test"))
        task.result = ""
        expected = {("e", pic_a.id().to_hex()), ("e", pic_b.id().to_hex())}
        for label, fetched in [("empty", []), ("partial", [pic_a])]:
            with self.subTest(live_fetch=label):
                client = MagicMock()
                client.database.return_value = self.database
                client.add_relay = AsyncMock()
                client.connect = AsyncMock()
                client.shutdown = AsyncMock()
                client.sync = AsyncMock(return_value=SimpleNamespace(
                    success=["wss://ok"], failed={}, report=SimpleNamespace(received={})))
                client.fetch_events = AsyncMock(return_value=fetched)  # relay outage: nothing or only some served
                with patch("nostr_dvm.tasks.content_discovery_currently_popular_gallery.NostrLmdb.open",
                           new_callable=AsyncMock) as open_db, \
                        patch("nostr_dvm.tasks.content_discovery_currently_popular_gallery.ClientBuilder") as builder:
                    open_db.return_value = self.database
                    builder.return_value.database.return_value.authenticator.return_value.relay_limits.return_value.build.return_value = client
                    result = await task.calculate_result(
                        {"jobID": "generic", "options": json.dumps({"max_results": 200})})
                self.assertEqual({tuple(tag) for tag in json.loads(result)}, expected)


if __name__ == "__main__":
    unittest.main()
