import asyncio
from concurrent.futures import Future
from datetime import datetime, timezone
from threading import Lock, Thread

from nostr_sdk import Client, Event, Timestamp, uniffi_set_event_loop
from nostr_sdk import nostr_sdk as _sdk_bindings


_callback_lock = Lock()
_callback_loop = None
_callback_thread = None
_sdk_get_event_loop = _sdk_bindings._uniffi_get_event_loop


def _get_sdk_event_loop():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return _sdk_get_event_loop()


def ensure_sdk_callback_loop() -> asyncio.AbstractEventLoop:
    global _callback_loop, _callback_thread
    with _callback_lock:
        if _callback_loop is None or not _callback_loop.is_running() or not _callback_thread.is_alive():
            ready = Future()

            def run_callbacks():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.call_soon(ready.set_result, loop)
                try:
                    loop.run_forever()
                finally:
                    loop.close()

            _callback_thread = Thread(target=run_callbacks, name="nostr-sdk-callbacks", daemon=True)
            _callback_thread.start()
            _callback_loop = ready.result(timeout=5)
        uniffi_set_event_loop(_callback_loop)
        _sdk_bindings._uniffi_get_event_loop = _get_sdk_event_loop
        return _callback_loop


def format_timestamp(timestamp: Timestamp) -> str:
    return datetime.fromtimestamp(timestamp.as_secs(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def merge_events(*event_lists: list[Event]) -> list[Event]:
    events = {event.id().to_hex(): event for event_list in event_lists for event in event_list}
    return sorted(events.values(), key=lambda event: (-event.created_at().as_secs(), event.id().to_hex()))


async def handle_notifications(client: Client, handler):
    stream = client.notifications()
    while True:
        notification = await stream.next()
        if notification is None or notification.is_shutdown():
            return
        if notification.is_new_event():
            await handler.handle(
                notification.relay_url, notification.subscription_id, notification.event
            )
        elif notification.is_message():
            await handler.handle_msg(notification.relay_url, notification.message)
