import ast
import asyncio
import importlib
import inspect
import json
import subprocess
import tempfile
import unittest
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import nostr_sdk as sdk

from nostr_dvm.tasks.advanced_search import AdvancedSearch
from nostr_dvm.utils import nip89_utils, nostr_utils, nwc_tools, zap_utils
from nostr_dvm.utils.sdk_utils import format_timestamp, handle_notifications, merge_events


ROOT = Path(__file__).resolve().parents[2]


class SdkStaticTests(unittest.TestCase):
    def test_sdk_version(self):
        self.assertEqual(version("nostr-sdk"), "0.45.1")

    def test_tracked_sources_and_sdk_imports(self):
        paths = subprocess.check_output(
            ["git", "ls-files", "*.py"], cwd=ROOT, text=True
        ).splitlines()
        for path in paths:
            with self.subTest(path=path):
                tree = ast.parse((ROOT / path).read_text(), filename=path)
                compile(tree, path, "exec")
                if path.startswith("tests/unit/"):
                    continue
                parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
                imports = {
                    alias.asname or alias.name: alias.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom) and node.module == "nostr_sdk"
                    for alias in node.names
                }
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module == "nostr_sdk":
                        for alias in node.names:
                            self.assertTrue(hasattr(sdk, alias.name), alias.name)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                        self.assertNotIn(node.func.attr, {
                            "as_vec", "sign_with_keys", "to_human_datetime",
                            "handle_notifications", "set_metadata", "send_event_builder",
                            "opts", "signer", "lmdb", "force_remove_relay", "send_private_msg",
                        })
                        if isinstance(node.func.value, ast.Name) and node.func.value.id in imports:
                            owner = getattr(sdk, imports[node.func.value.id])
                            self.assertTrue(hasattr(owner, node.func.attr), ast.unparse(node.func))
                            method = getattr(owner, node.func.attr)
                            if inspect.iscoroutinefunction(method):
                                self.assertIsInstance(parents.get(node), ast.Await, ast.unparse(node.func))
                        if node.func.attr in {"fetch_events", "subscribe"}:
                            self.assertIsInstance(node.args[0], ast.Call)
                            self.assertEqual(ast.unparse(node.args[0].func), "ReqTarget.auto")
                        if node.func.attr == "sync":
                            self.assertLessEqual(len(node.args), 1)

    def test_core_imports(self):
        for name in ("dvm", "bot", "subscription", "framework"):
            with self.subTest(module=name):
                importlib.import_module("nostr_dvm." + name)


class SdkRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.keys = sdk.Keys.generate()
        self.other_keys = sdk.Keys.generate()
        self.config = SimpleNamespace(
            PRIVATE_KEY=self.keys.secret_key().to_hex(),
            PUBLIC_KEY=self.keys.public_key().to_hex(),
            LOGLEVEL=sdk.LogLevel.ERROR,
            RELAY_LIST=["wss://example.com"],
            ANNOUNCE_RELAY_LIST=["wss://example.com"],
            AVOID_OUTBOX_RELAY_LIST=[],
            NIP89=SimpleNamespace(NAME="test", CONTENT=json.dumps({
                "name": "test", "about": "offline", "picture": "https://example.com/test.png",
            })),
        )

    def event(self, kind=1, content="test", tags=None, timestamp=100):
        return sdk.EventBuilder(sdk.Kind(kind), content).tags(tags or []).custom_created_at(
            sdk.Timestamp.from_secs(timestamp)
        ).finalize(self.keys)

    async def test_signing_tags_and_authentication(self):
        event = self.event(tags=[sdk.Tag.parse(["p", self.other_keys.public_key().to_hex()])])
        self.assertTrue(event.verify())
        self.assertIsInstance(event.tags(), list)
        self.assertEqual(event.tags()[0].to_vec()[0], "p")
        authenticator = sdk.SignerAuthenticator(self.keys)
        authentication = await authenticator.make_auth_event(
            sdk.RelayUrl.parse("wss://example.com"), "challenge"
        )
        self.assertTrue(authentication.verify())
        self.assertEqual(authentication.kind().as_u16(), 22242)
        client = sdk.ClientBuilder().authenticator(authenticator).relay_limits(
            sdk.RelayLimits.disable()
        ).proxy(sdk.Proxy.onion("127.0.0.1:9050")).gossip(sdk.NostrGossip.in_memory()).build()
        await client.shutdown()

    async def test_gift_wrap_round_trip(self):
        gift = await sdk.nip17_make_private_msg_async(
            self.keys, self.other_keys.public_key(), "private message"
        )
        self.assertTrue(gift.verify())
        unwrapped = await sdk.UnwrappedGift.from_gift_wrap_async(self.other_keys, gift)
        self.assertEqual(unwrapped.sender().to_hex(), self.keys.public_key().to_hex())
        self.assertEqual(unwrapped.rumor().content(), "private message")

    async def test_nip04_dm(self):
        client = SimpleNamespace(send_event=AsyncMock())
        await nostr_utils.send_nip04_dm(client, "secret", self.other_keys.public_key(), self.config)
        event = client.send_event.call_args.args[0]
        self.assertTrue(event.verify())
        self.assertEqual(sdk.nip04_decrypt(
            self.other_keys.secret_key(), self.keys.public_key(), event.content()
        ), "secret")

    async def test_private_zap_round_trip(self):
        message = json.dumps({"content": "private zap 🥳", "tags": []})
        encrypted = zap_utils.enrypt_private_zap_message(
            message, self.keys.secret_key(), self.other_keys.public_key()
        )
        self.assertTrue(encrypted.startswith("pzap1"))
        self.assertIn("_iv1", encrypted)
        self.assertEqual(zap_utils.decrypt_private_zap_message(
            encrypted, self.other_keys.secret_key(), self.keys.public_key()
        ), message)

    async def test_notifications_dispatch_and_shutdown(self):
        event = self.event()
        relay = sdk.RelayUrl.parse("wss://example.com")
        notification = sdk.ClientNotification.NEW_EVENT(relay, "subscription", event)
        message = sdk.RelayMessage.notice("test")
        stream = SimpleNamespace(next=AsyncMock(side_effect=[
            notification, sdk.ClientNotification.MESSAGE(relay, message), sdk.ClientNotification.SHUTDOWN(),
        ]))
        client = SimpleNamespace(notifications=lambda: stream)
        handler = SimpleNamespace(handle=AsyncMock(), handle_msg=AsyncMock())
        await handle_notifications(client, handler)
        handler.handle.assert_awaited_once_with(relay, "subscription", event)
        handler.handle_msg.assert_awaited_once_with(relay, message)

    async def test_notification_stream_end_and_cancellation(self):
        stream = SimpleNamespace(next=AsyncMock(return_value=None))
        await handle_notifications(SimpleNamespace(notifications=lambda: stream), SimpleNamespace())
        stream.next = AsyncMock(side_effect=asyncio.CancelledError)
        with self.assertRaises(asyncio.CancelledError):
            await handle_notifications(SimpleNamespace(notifications=lambda: stream), SimpleNamespace())

    async def test_real_notification_stream_shutdown(self):
        client = sdk.Client()
        handler = SimpleNamespace(handle=AsyncMock(), handle_msg=AsyncMock())
        task = asyncio.create_task(handle_notifications(client, handler))
        try:
            await asyncio.sleep(0)
            await client.shutdown()
            await asyncio.wait_for(task, timeout=2)
        finally:
            if not task.done():
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task

    async def test_deletion_with_proof_of_work(self):
        original = self.event()
        unsigned = sdk.EventBuilder(sdk.Kind(5), "deleted").tags([
            sdk.Tag.event(original.id()),
        ]).finalize_unsigned(self.keys.public_key())
        mined = await unsigned.mine_async(sdk.MultiThreadPow(), 4)
        event = mined.sign(self.keys)
        self.assertTrue(event.verify())
        self.assertEqual(event.kind().as_u16(), 5)
        self.assertIn(["e", original.id().to_hex()], [tag.to_vec() for tag in event.tags()])
        self.assertTrue(event.id().to_hex().startswith("0"))

    async def test_database_query_delete_and_sync_options(self):
        with tempfile.TemporaryDirectory() as directory:
            database = await sdk.NostrLmdb.open(directory)
            event = self.event(timestamp=sdk.Timestamp.now().as_secs())
            await database.save_event(event)
            query = sdk.Filter().id(event.id())
            events = await database.query(query)
            self.assertIsInstance(events, list)
            self.assertEqual([item.id().to_hex() for item in events], [event.id().to_hex()])
            client = sdk.ClientBuilder().database(database).build()
            try:
                with self.assertRaises(sdk.NostrSdkError.Generic) as error:
                    await client.sync(query, opts=sdk.SyncOptions().direction(sdk.SyncDirection.DOWN))
                self.assertIn("relay", str(error.exception))
            finally:
                await client.shutdown()
            await database.delete_events(query)
            self.assertEqual(await database.query(query), [])

    async def test_fetch_target_accepted_by_sdk(self):
        client = sdk.Client()
        try:
            with self.assertRaises(sdk.NostrSdkError.Generic) as error:
                await client.fetch_events(sdk.ReqTarget.auto([sdk.Filter()]))
            self.assertIn("relay", str(error.exception))
        finally:
            await client.shutdown()

    async def test_event_merging_and_timestamp_format(self):
        older = self.event(timestamp=100)
        newer = self.event(timestamp=200)
        self.assertEqual(merge_events([older, newer], [newer]), [newer, older])
        self.assertEqual(format_timestamp(sdk.Timestamp.from_secs(0)), "1970-01-01T00:00:00Z")

    async def test_advanced_search_request_and_result(self):
        task = object.__new__(AdvancedSearch)
        task.options = {"relay": "wss://example.com"}
        request = self.event(kind=5302, tags=[
            sdk.Tag.parse(["i", "nostr", "text"]),
            sdk.Tag.parse(["param", "max_results", "5"]),
        ])
        form = await task.create_request_from_nostr_event(request, dvm_config=self.config)
        self.assertEqual(json.loads(form["options"])["relay"], "wss://example.com")
        result = self.event()
        client = SimpleNamespace(
            add_relay=AsyncMock(), connect=AsyncMock(), fetch_events=AsyncMock(return_value=[result]),
            shutdown=AsyncMock(),
        )
        builder = MagicMock()
        builder.authenticator.return_value = builder
        builder.build.return_value = client
        with patch("nostr_dvm.tasks.advanced_search.ClientBuilder", return_value=builder):
            response = await task.process(form)
        self.assertEqual(json.loads(response), [["e", result.id().to_hex()]])
        self.assertIsInstance(client.fetch_events.call_args.args[0], sdk.ReqTarget)
        client.shutdown.assert_awaited_once()

    async def test_event_lookup_helpers_return_lists(self):
        event = self.event()
        client = SimpleNamespace(fetch_events=AsyncMock(return_value=[event]))
        event_id = event.id().to_hex()
        self.assertEqual(await nostr_utils.get_event_by_id(event_id, client), event)
        self.assertEqual(await nostr_utils.get_events_by_ids([event_id], client), [event])
        self.assertEqual(await nostr_utils.get_events_by_id([event.id()], client), [event])
        self.assertEqual(await nostr_utils.get_referenced_event_by_id(event_id, client, self.config, None), event)
        self.assertEqual(await nostr_utils.get_events_by_ids([], client), None)
        self.assertEqual(await nip89_utils.nip89_fetch_all_dvms_by_kind(client, 5302), [event])
        self.assertEqual(await nip89_utils.nip89_fetch_events_pubkey(
            client, self.keys.public_key().to_hex(), sdk.Kind(5302)
        ), event.content())
        client.fetch_events.return_value = []
        self.assertIsNone(await nostr_utils.get_event_by_id(event_id, client))
        self.assertIsNone(await nostr_utils.get_events_by_id([event.id()], client))

    async def test_metadata_is_signed_before_sending(self):
        client = SimpleNamespace(send_event=AsyncMock())
        await nostr_utils.update_profile(self.config, client, "test@example.com", broadcast=False)
        event = client.send_event.call_args.args[0]
        self.assertTrue(event.verify())
        self.assertEqual(event.kind().as_u16(), 0)
        self.assertEqual(json.loads(event.content())["lud16"], "test@example.com")

    async def test_relay_lookup_helpers(self):
        addressed = self.event(tags=[sdk.Tag.public_key(self.keys.public_key())])
        relay_list = self.event(kind=10002, tags=[sdk.Tag.parse(["r", "wss://example.com", "read"])])
        client = MagicMock(
            fetch_events=AsyncMock(return_value=[relay_list]), relays=AsyncMock(return_value={}),
            add_relay=AsyncMock(), connect=AsyncMock(),
        )
        self.assertEqual(await nostr_utils.get_inbox_relays(addressed, client, self.config), ["wss://example.com"])
        self.assertEqual(await nostr_utils.get_dm_relays(addressed, client, self.config), ["wss://example.com"])
        client.fetch_events.return_value = [self.event(kind=3, content=json.dumps({"wss://example.com": {}}))]
        self.assertEqual(await nostr_utils.get_main_relays(addressed, client, self.config), ["wss://example.com"])
        client.fetch_events.return_value = []
        nostr_utils._relay_lookup_cache.clear()
        self.assertEqual(await nostr_utils.get_inbox_relays(addressed, client, self.config), [])

    async def test_nwc_request_and_cleanup(self):
        wallet_client = SimpleNamespace(shutdown=AsyncMock())
        wallet = SimpleNamespace(
            get_info=AsyncMock(return_value="test"),
            get_balance=AsyncMock(return_value=sdk.GetBalanceResponse(balance=100)),
            pay_invoice=AsyncMock(return_value=sdk.PayInvoiceResponse(preimage="test-preimage", fees_paid=0)),
            client=lambda: wallet_client,
        )
        uri = "nostr+walletconnect://" + self.other_keys.public_key().to_hex() + (
            "?relay=wss%3A%2F%2Fexample.com&secret=" + self.keys.secret_key().to_hex()
        )
        with patch.object(nwc_tools, "NostrWalletConnect", return_value=wallet):
            result = await nwc_tools.nwc_zap(uri, "test-invoice", self.keys)
        self.assertEqual(result, "test-preimage")
        request = wallet.pay_invoice.call_args.args[0]
        self.assertIsInstance(request, sdk.PayInvoiceRequest)
        self.assertEqual(request.invoice, "test-invoice")
        wallet_client.shutdown.assert_awaited_once()
        wallet_client.shutdown.reset_mock()
        wallet.pay_invoice.reset_mock(side_effect=True)
        wallet.pay_invoice.side_effect = RuntimeError("payment failed")
        with patch.object(nwc_tools, "NostrWalletConnect", return_value=wallet):
            with self.assertRaisesRegex(RuntimeError, "payment failed"):
                await nwc_tools.nwc_zap(uri, "test-invoice", self.keys)
        wallet.pay_invoice.assert_awaited_once()
        wallet_client.shutdown.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
