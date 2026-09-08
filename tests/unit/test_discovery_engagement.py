import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from nostr_sdk import EventBuilder, Filter, Keys, Kind, LogLevel, Tag, Timestamp

from nostr_dvm.tasks.content_discovery_currently_popular import DicoverContentCurrentlyPopular
from nostr_dvm.tasks.content_discovery_update_db_only import DicoverContentDBUpdateScheduler
from nostr_dvm.utils.database_utils import init_db
from nostr_dvm.utils.discovery_utils import discovery_sync_filters, query_engagement, sync_discovery_database


class DiscoveryEngagementTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = await init_db(self.directory.name, print_filesize=False)
        self.now = Timestamp.now().as_secs()
        self.since = Timestamp.from_secs(self.now - 3600)
        self.keys = Keys.generate()

    async def save(self, kind=1, tags=(), age=10):
        event = EventBuilder(Kind(kind), str(tags)).tags([Tag.parse(tag) for tag in tags]).custom_created_at(
            Timestamp.from_secs(self.now - age)).finalize(self.keys)
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

    async def test_popular_uses_shared_database_and_counts_both_reply_kinds(self):
        note = await self.save()
        await self.save(tags=[["e", note.id().to_hex()]])
        await self.save(1111, [["E", note.id().to_hex()], ["e", note.id().to_hex()]])
        task = object.__new__(DicoverContentCurrentlyPopular)
        config = SimpleNamespace(DATABASE=self.database, UPDATE_DATABASE=False,
                                 LOGLEVEL=LogLevel.ERROR, NIP89=SimpleNamespace(NAME="test"))
        task.dvm_config = config
        task.options = {"db_name": "must-not-open-this-path", "db_since": 3600}
        with patch("nostr_dvm.tasks.content_discovery_currently_popular.init_db", new_callable=AsyncMock) as open_db:
            await task.init_dvm("test", config, None)
            open_db.assert_not_awaited()
        self.assertEqual(json.loads(task.result), [["e", note.id().to_hex()]])
        await self.database.delete_events(Filter())
        self.assertEqual(await task.calculate_result(task.request_form), "[]")

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


if __name__ == "__main__":
    unittest.main()
