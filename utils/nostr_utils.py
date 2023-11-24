from datetime import timedelta
from nostr_sdk import Filter, Client, Alphabet, EventId, Event, PublicKey


def get_event_by_id(event_id: str, client: Client, config=None) -> Event | None:
    split = event_id.split(":")
    if len(split) == 3:
        pk = PublicKey.from_hex(split[1])
        id_filter = Filter().author(pk).custom_tag(Alphabet.D, [split[2]])
        events = client.get_events_of([id_filter], timedelta(seconds=config.RELAY_TIMEOUT))
    else:
        if str(event_id).startswith('note'):
            event_id = EventId.from_bech32(event_id)
        else:
            event_id = EventId.from_hex(event_id)

        id_filter = Filter().id(event_id).limit(1)
        events = client.get_events_of([id_filter], timedelta(seconds=config.RELAY_TIMEOUT))
    if len(events) > 0:
        return events[0]
    else:
        return None


def get_referenced_event_by_id(event_id, client, dvm_config, kinds) -> Event | None:
    if kinds is None:
        kinds = []

    if len(kinds) > 0:
        job_id_filter = Filter().kinds(kinds).event(EventId.from_hex(event_id)).limit(1)
    else:
        job_id_filter = Filter().event(EventId.from_hex(event_id)).limit(1)

    events = client.get_events_of([job_id_filter], timedelta(seconds=dvm_config.RELAY_TIMEOUT))

    if len(events) > 0:
        return events[0]
    else:
        return None


def send_event(event: Event, client: Client, dvm_config) -> EventId:
    relays = []

    for tag in event.tags():
        if tag.as_vec()[0] == 'relays':
            relays = tag.as_vec()[1].split(',')

    for relay in relays:
        if relay not in dvm_config.RELAY_LIST:
            client.add_relay(relay)

    event_id = client.send_event(event)

    for relay in relays:
        if relay not in dvm_config.RELAY_LIST:
            client.remove_relay(relay)

    return event_id
