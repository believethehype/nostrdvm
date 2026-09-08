from datetime import timedelta

from nostr_sdk import EventId, Filter, ReqTarget, SingleLetterTag, SyncDirection, SyncOptions, Timestamp

from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.sdk_utils import merge_events


def engagement_kinds():
    return [EventDefinitions.KIND_NOTE, EventDefinitions.KIND_NIP22_COMMENT,
            EventDefinitions.KIND_REACTION, EventDefinitions.KIND_REPOST, EventDefinitions.KIND_ZAP]


def discovery_sync_filters(since, authors=None, batch_size=500):
    if batch_size < 1:
        raise ValueError("Author batch size must be positive")
    if authors is None:
        return [Filter().kinds(engagement_kinds()).since(since)]
    if not authors:
        raise ValueError("WOT contains no authors; refusing an unrestricted sync")
    return [Filter().kinds(engagement_kinds()).since(since).authors(authors[offset:offset + batch_size])
            for offset in range(0, len(authors), batch_size)]


async def query_engagement(database, event_id: EventId, since: Timestamp):
    parent_filter = Filter().kinds(engagement_kinds()).event(event_id).since(since)
    root_filter = Filter().kind(EventDefinitions.KIND_NIP22_COMMENT).custom_tags(
        SingleLetterTag.from_byte(ord('E')), [event_id.to_hex()]).since(since)
    return merge_events(await database.query(parent_filter), await database.query(root_filter))


async def sync_discovery_database(client, event_filter, label, unsupported_relays=None):
    if unsupported_relays is None:
        unsupported_relays = set()
    summary = None
    sync_relays = None
    if unsupported_relays:
        sync_relays = [relay for relay in await client.relays() if str(relay) not in unsupported_relays]
    try:
        if sync_relays is None or sync_relays:
            summary = await client.sync(event_filter, _with=sync_relays,
                                        opts=SyncOptions().direction(SyncDirection.DOWN))
            for relay, error in summary.failed.items():
                print(f"[{label}] Sync failed for {relay}: {error}")
                if "negentropy not supported" in error.lower():
                    unsupported_relays.add(str(relay))
    except Exception as error:
        print(f"[{label}] Negentropy sync failed: {error}")
    if summary is None or not summary.success or unsupported_relays:
        print(f"[{label}] Trying a regular event fetch with the same database filter")
        events = await client.fetch_events(ReqTarget.auto([event_filter]), timedelta(seconds=30))
        if not events and (summary is None or not summary.success):
            raise RuntimeError(f"[{label}] Sync and fallback fetch returned no events; keeping existing events")
        for event in events:
            await client.database().save_event(event)
        print(f"[{label}] Fallback fetched {len(events)} events (relay limits may truncate results)")
    count = await client.database().count(event_filter)
    received = len(summary.report.received) if summary is not None else 0
    print(f"[{label}] Sync received {received} events; {count} matching events in database")
    return summary
