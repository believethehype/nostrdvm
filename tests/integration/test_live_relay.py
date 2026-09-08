import asyncio
import os
import unittest
from datetime import timedelta

from nostr_sdk import Client, Filter, Kind, RelayUrl, ReqTarget


@unittest.skipUnless(os.getenv("NOSTR_TEST_RELAY"), "Set NOSTR_TEST_RELAY for an opt-in, read-only relay check")
class LiveRelayTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_signed_note(self):
        client = Client()
        try:
            await client.add_relay(RelayUrl.parse(os.environ["NOSTR_TEST_RELAY"]))
            connected = await asyncio.wait_for(client.try_connect(timedelta(seconds=5)), timeout=10)
            self.assertTrue(connected.success, str(connected.failed))
            events = await asyncio.wait_for(client.fetch_events(
                ReqTarget.auto([Filter().kind(Kind(1)).limit(1)]), timeout=timedelta(seconds=5),
            ), timeout=10)
            self.assertTrue(events, "Relay returned no notes; the read check is inconclusive")
            for event in events:
                self.assertTrue(event.verify())
                self.assertEqual(event.kind().as_u16(), 1)
        finally:
            await client.shutdown()


if __name__ == "__main__":
    unittest.main()
