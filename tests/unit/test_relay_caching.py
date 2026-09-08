import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from nostr_sdk import Filter, RelayUrl

from nostr_dvm.utils.discovery_utils import sync_discovery_database
from nostr_dvm.utils import nostr_utils


class RelayCachingTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_explicitly_unsupported_relays_are_skipped(self):
        unsupported = RelayUrl.parse("wss://unsupported.example.com")
        slow = RelayUrl.parse("wss://slow.example.com")
        client = MagicMock()
        client.relays = AsyncMock(return_value={unsupported: None, slow: None})
        client.sync = AsyncMock(return_value=SimpleNamespace(
            success=[], failed={unsupported: "negentropy not supported", slow: "timeout"},
            report=SimpleNamespace(received={})))
        client.fetch_events = AsyncMock(return_value=[MagicMock()])
        client.database.return_value.save_event = AsyncMock()
        client.database.return_value.count = AsyncMock(return_value=1)
        state = set()
        await sync_discovery_database(client, Filter(), "batch 1", state)
        await sync_discovery_database(client, Filter(), "batch 2", state)
        self.assertEqual(state, {str(unsupported)})
        self.assertEqual(client.sync.call_args.kwargs["_with"], [slow])
        self.assertEqual(client.fetch_events.await_count, 2)
        await sync_discovery_database(client, Filter(), "new cycle", set())
        self.assertIsNone(client.sync.call_args.kwargs["_with"])

    async def test_all_unsupported_skips_negentropy_entirely(self):
        relay = RelayUrl.parse("wss://unsupported.example.com")
        client = MagicMock()
        client.relays = AsyncMock(return_value={relay: None})
        client.sync = AsyncMock()
        client.fetch_events = AsyncMock(return_value=[MagicMock()])
        client.database.return_value.save_event = AsyncMock()
        client.database.return_value.count = AsyncMock(return_value=1)
        await sync_discovery_database(client, Filter(), "test", {str(relay)})
        client.sync.assert_not_awaited()
        client.fetch_events.assert_awaited_once()

    async def test_positive_negative_cache_and_expiration(self):
        for events, lifetime in [(["event"], 300), ([], 30)]:
            with self.subTest(events=events):
                client = MagicMock(fetch_events=AsyncMock(return_value=events))
                with patch.object(nostr_utils.time, "monotonic", return_value=100):
                    self.assertEqual(await nostr_utils.fetch_relay_metadata(client, Filter()), events)
                    self.assertEqual(await nostr_utils.fetch_relay_metadata(client, Filter()), events)
                    client.fetch_events.assert_awaited_once()
                with patch.object(nostr_utils.time, "monotonic", return_value=101 + lifetime):
                    await nostr_utils.fetch_relay_metadata(client, Filter())
                self.assertEqual(client.fetch_events.await_count, 2)
                self.assertEqual(client.fetch_events.call_args.args[1].total_seconds(), 5)

    async def test_failed_lookup_falls_back_and_is_cached(self):
        client = MagicMock(fetch_events=AsyncMock(side_effect=TimeoutError()))
        self.assertEqual(await nostr_utils.fetch_relay_metadata(client, Filter()), [])
        self.assertEqual(await nostr_utils.fetch_relay_metadata(client, Filter()), [])
        client.fetch_events.assert_awaited_once()
