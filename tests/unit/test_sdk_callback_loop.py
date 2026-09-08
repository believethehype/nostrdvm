import asyncio
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

from nostr_sdk import EventBuilder, Keys, Kind, nostr_sdk as bindings

from nostr_dvm.utils.database_utils import init_db
from nostr_dvm.utils.sdk_utils import ensure_sdk_callback_loop


class SdkCallbackLoopTests(unittest.TestCase):
    def test_callback_loop_survives_temporary_application_loops(self):
        async def initialize():
            application_loop = asyncio.get_running_loop()
            callback_loop = ensure_sdk_callback_loop()
            self.assertIs(bindings._uniffi_get_event_loop(), application_loop)
            return application_loop, callback_loop

        first_application, first_callback = asyncio.run(initialize())
        second_application, second_callback = asyncio.run(initialize())
        self.assertTrue(first_application.is_closed())
        self.assertTrue(second_application.is_closed())
        self.assertIs(first_callback, second_callback)
        self.assertIsNot(first_application, first_callback)
        self.assertTrue(first_callback.is_running())
        self.assertFalse(first_callback.is_closed())

    def test_concurrent_dvms_share_one_callback_loop(self):
        def start_dvm(worker):
            async def initialize():
                return ensure_sdk_callback_loop()

            return asyncio.run(initialize())

        with ThreadPoolExecutor(max_workers=4) as executor:
            loops = list(executor.map(start_dvm, range(8)))
        self.assertTrue(all(loop is loops[0] for loop in loops))
        self.assertTrue(loops[0].is_running())

    def test_database_callback_from_thread_without_event_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            async def initialize():
                database = await init_db(directory, print_filesize=False)
                event = EventBuilder(Kind(1), "offline callback test").finalize(Keys.generate())
                await database.save_event(event)
                return database, event.id(), await database.check_id(event.id())

            database, event_id, expected = asyncio.run(initialize())

            def rust_thread_callback():
                with self.assertRaises(RuntimeError):
                    asyncio.get_running_loop()
                loop = bindings._uniffi_get_event_loop()
                result = asyncio.run_coroutine_threadsafe(database.check_id(event_id), loop)
                return result.result(timeout=3)

            with ThreadPoolExecutor(max_workers=1) as executor:
                result = executor.submit(rust_thread_callback).result(timeout=5)
            self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
