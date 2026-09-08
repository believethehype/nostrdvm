import json
import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from nostr_sdk import EventBuilder, Keys, Kind, LogLevel, Timestamp

from nostr_dvm.tasks.content_discovery_currently_popular_topic import DicoverContentCurrentlyPopularbyTopic
from nostr_dvm.tasks.content_discovery_currently_popular_gallery import DicoverContentCurrentlyPopularGallery
from nostr_dvm.utils import database_utils, wot_utils, zap_utils


class UserDatabaseTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.db = str(Path(directory.name) / "users.db")
        with sqlite3.connect(self.db) as connection:
            connection.execute("CREATE TABLE users (npub TEXT PRIMARY KEY, sats INTEGER, "
                               "iswhitelisted BOOLEAN, isblacklisted BOOLEAN, nip05 TEXT, "
                               "lud16 TEXT, name TEXT, lastactive INTEGER, subscribed INTEGER)")
        self.config = SimpleNamespace(DB=self.db, NEW_USER_BALANCE=5)

    def test_user_records_are_independent_instances(self):
        for name, balance in [("alice", 10), ("bob", 20)]:
            database_utils.add_to_sql_table(self.db, name, balance, False, False, "", "", name, 0, None)
        alice = database_utils.get_from_sql_table(self.db, "alice")
        bob = database_utils.get_from_sql_table(self.db, "bob")
        self.assertIsInstance(alice, database_utils.User)
        self.assertIsNot(alice, bob)
        self.assertEqual((alice.npub, alice.balance, alice.subscribed), ("alice", 10, 0))
        self.assertEqual((bob.npub, bob.balance), ("bob", 20))

    async def test_new_user_balance_awaits_metadata(self):
        with patch.object(database_utils, "fetch_user_metadata", new_callable=AsyncMock,
                          return_value=("Alice", "", "")) as metadata:
            await database_utils.update_user_balance(self.db, "alice", 10, None, self.config)
        metadata.assert_awaited_once_with("alice", None)
        user = database_utils.get_from_sql_table(self.db, "alice")
        self.assertEqual((user.name, user.balance), ("Alice", 15))

    def test_concurrent_debits_cannot_overspend(self):
        database_utils.credit_user_balance(self.db, "alice", 10)
        with ThreadPoolExecutor(max_workers=8) as executor:
            balances = list(executor.map(lambda amount: database_utils.debit_user_balance(self.db, "alice", amount),
                                         [1] * 30))
        self.assertEqual(sum(balance is not None for balance in balances), 10)
        self.assertEqual(database_utils.get_from_sql_table(self.db, "alice").balance, 0)
        with self.assertRaises(ValueError):
            database_utils.debit_user_balance(self.db, "alice", -1)

    async def test_profile_refresh_does_not_overwrite_intervening_credit(self):
        database_utils.credit_user_balance(self.db, "alice", 10)

        async def metadata(*args):
            database_utils.credit_user_balance(self.db, "alice", 5)
            database_utils.update_user_fields(self.db, "alice", subscribed=123)
            return "Alice", "verified", "address"

        with patch.object(database_utils, "fetch_user_metadata", side_effect=metadata):
            user = await database_utils.get_or_add_user(self.db, "alice", None, self.config, update=True)
        self.assertEqual((user.balance, user.subscribed, user.name), (15, 123, "Alice"))

    def test_concurrent_credits_preserve_every_increment_and_one_initial_balance(self):
        for npub, existing in [("new", False), ("existing", True)]:
            with self.subTest(existing=existing):
                if existing:
                    database_utils.add_to_sql_table(self.db, npub, 5, True, False, "", "", "name", 0, 123)
                with ThreadPoolExecutor(max_workers=8) as executor:
                    balances = list(executor.map(
                        lambda amount: database_utils.credit_user_balance(self.db, npub, amount, 5), [1] * 40))
                user = database_utils.get_from_sql_table(self.db, npub)
                self.assertEqual(user.balance, 45)
                self.assertEqual(sorted(balances), list(range(6, 46)))
                if existing:
                    self.assertEqual((user.name, user.subscribed, user.iswhitelisted), ("name", 123, True))

    async def test_subscription_creates_and_updates_expiration(self):
        with patch.object(database_utils, "fetch_user_metadata", new_callable=AsyncMock,
                          return_value=("Alice", "", "")) as metadata:
            await database_utils.update_user_subscription("alice", 100, None, self.config)
            self.assertEqual(database_utils.get_from_sql_table(self.db, "alice").subscribed, 100)
            await database_utils.update_user_subscription("alice", 200, None, self.config)
        metadata.assert_awaited_once()
        user = database_utils.get_from_sql_table(self.db, "alice")
        self.assertEqual((user.subscribed, user.balance), (200, 5))


class WalletLoggingTests(unittest.TestCase):
    def test_lnbits_requests_have_explicit_timeouts(self):
        config = SimpleNamespace(LNBITS_URL="https://example.com", LNBITS_ADMIN_KEY="key", LNBITS_INVOICE_KEY="key",
                                 NIP89=SimpleNamespace(NAME="test"))
        for function, argument, method in [(zap_utils.pay_bolt11_ln_bits, "invoice", "post"),
                                           (zap_utils.create_bolt11_ln_bits, 1, "post"),
                                           (zap_utils.check_bolt11_ln_bits_is_paid, "hash", "get")]:
            with self.subTest(function=function.__name__), patch.object(
                    zap_utils.requests, method, return_value=SimpleNamespace(text='{}')) as request:
                function(argument, config)
                self.assertEqual(request.call_args.kwargs["timeout"], (5, 30))
                request.assert_called_once()

    def test_wallet_and_account_responses_do_not_leak_credentials(self):
        wallet = {"inkey": "secret-invoice", "adminkey": "secret-admin", "id": "wallet-id"}
        with patch.dict(os.environ, {"LNBITS_ADMIN_KEY": "configured-key", "LNBITS_HOST": "https://example.com"}):
            for function, body in [(zap_utils.create_lnbits_wallet, wallet),
                                   (zap_utils.create_lnbits_account, {"wallets": [wallet], "id": "account"})]:
                with self.subTest(function=function.__name__), patch.object(
                        zap_utils.requests, "post", return_value=SimpleNamespace(text=json.dumps(body))), patch(
                        "builtins.print") as output:
                    self.assertEqual(function("test")[-1], "success")
                    self.assertNotIn("secret-invoice", str(output.call_args_list))
                    self.assertNotIn("secret-admin", str(output.call_args_list))

    def test_wallet_exception_does_not_log_sensitive_details(self):
        with patch.dict(os.environ, {"LNBITS_ADMIN_KEY": "key", "LNBITS_HOST": "https://example.com"}), patch.object(
                zap_utils.requests, "post", side_effect=RuntimeError("secret-admin")), patch("builtins.print") as output:
            self.assertEqual(zap_utils.create_lnbits_wallet("test")[-1], "failed")
            self.assertNotIn("secret-admin", str(output.call_args_list))


class TopicScheduleTests(unittest.IsolatedAsyncioTestCase):
    async def test_gallery_ranking_failure_closes_client_at_info_log_level(self):
        task = object.__new__(DicoverContentCurrentlyPopularGallery)
        keys = Keys.generate()
        task.dvm_config = SimpleNamespace(PRIVATE_KEY=keys.secret_key().to_hex(), SYNC_DB_RELAY_LIST=[],
                                         LOGLEVEL=LogLevel.INFO, NIP89=SimpleNamespace(NAME="gallery"))
        database = MagicMock()
        database.query = AsyncMock(return_value=[EventBuilder(Kind(20), "image").finalize(keys)])
        client = MagicMock()
        client.connect = AsyncMock()
        client.shutdown = AsyncMock()
        module = "nostr_dvm.tasks.content_discovery_currently_popular_gallery"
        with patch(module + ".NostrLmdb.open", new_callable=AsyncMock, return_value=database), patch(
                module + ".ClientBuilder") as builder, patch(module + ".sync_discovery_database",
                new_callable=AsyncMock, side_effect=RuntimeError("offline")):
            builder.return_value.database.return_value.authenticator.return_value.relay_limits.return_value.build.return_value = client
            with self.assertRaises(RuntimeError):
                await task.calculate_result({"options": '{"max_results": 10}'})
        client.shutdown.assert_awaited_once()

    async def test_failed_sync_does_not_prune_and_closes_client(self):
        client = MagicMock()
        client.add_relay = AsyncMock()
        client.connect = AsyncMock()
        client.shutdown = AsyncMock()
        client.database.return_value.delete_events = AsyncMock()
        task = object.__new__(DicoverContentCurrentlyPopularbyTopic)
        task.dvm_config = SimpleNamespace(PRIVATE_KEY=Keys.generate().secret_key().to_hex(),
                                         SYNC_DB_RELAY_LIST=[], LOGLEVEL=LogLevel.ERROR,
                                         NIP89=SimpleNamespace(NAME="test"))
        module = "nostr_dvm.tasks.content_discovery_currently_popular_topic"
        with patch(module + ".NostrLmdb.open", new_callable=AsyncMock), patch(module + ".ClientBuilder") as builder, patch(
                module + ".sync_discovery_database", new_callable=AsyncMock, side_effect=RuntimeError("offline")):
            builder.return_value.authenticator.return_value.database.return_value.build.return_value = client
            await task.sync_db()
        client.database.return_value.delete_events.assert_not_awaited()
        client.shutdown.assert_awaited_once()

    async def test_disabled_pending_and_due_schedules(self):
        for interval, elapsed, update_db, expected in [(0, 100, True, 0), (180, 10, True, 0),
                                                       (180, 200, True, 1), (180, 200, False, 1)]:
            with self.subTest(interval=interval, elapsed=elapsed, update_db=update_db):
                task = object.__new__(DicoverContentCurrentlyPopularbyTopic)
                task.dvm_config = SimpleNamespace(SCHEDULE_UPDATES_SECONDS=interval, UPDATE_DATABASE=update_db)
                task.last_schedule = Timestamp.now().as_secs() - elapsed
                task.request_form = {"options": "{}"}
                task.sync_db = AsyncMock()
                task.calculate_result = AsyncMock(return_value='[["e", "note"]]')
                result = await task.schedule(task.dvm_config)
                self.assertEqual(result, expected)
                self.assertEqual(task.sync_db.await_count, int(bool(expected and update_db)))
                self.assertEqual(task.calculate_result.await_count, expected)
                if expected:
                    self.assertEqual(task.result, '[["e", "note"]]')


class WotRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_since_and_cleanup_on_success_and_failure(self):
        keys = Keys.generate()
        pubkey = keys.public_key().to_hex()
        for failure in (False, True):
            with self.subTest(failure=failure):
                client = MagicMock()
                client.add_relay = AsyncMock()
                client.connect = AsyncMock()
                client.fetch_events = AsyncMock(return_value=[])
                client.shutdown = AsyncMock()
                if failure:
                    client.fetch_events.side_effect = RuntimeError("offline")
                with patch.object(wot_utils, "check_and_set_private_key", return_value=keys.secret_key().to_hex()), patch.object(
                        wot_utils, "ClientBuilder") as builder:
                    builder.return_value.authenticator.return_value.build.return_value = client
                    request = wot_utils.get_following([pubkey], max_time_request=3, newer_than_time=100,
                                                     dvm_config=SimpleNamespace(SYNC_DB_RELAY_LIST=[]))
                    if failure:
                        with self.assertRaises(RuntimeError):
                            await request
                    else:
                        graph = await request
                        self.assertIn(pubkey, graph)
                client.connect.assert_awaited_once_with(timedelta(seconds=3))
                self.assertEqual(client.fetch_events.call_args.args[1], timedelta(seconds=3))
                client.shutdown.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
