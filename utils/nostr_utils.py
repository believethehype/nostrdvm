from datetime import timedelta
from nostr_sdk import Keys, Filter, Client, Alphabet, EventId, Options

from utils.definitions import RELAY_LIST


def get_event_by_id(event_id, client=None, config=None):
    is_new_client = False
    if client is None:
        keys = Keys.from_sk_str(config.PRIVATE_KEY)
        client = Client(keys)
        for relay in config.RELAY_LIST:
            client.add_relay(relay)
        client.connect()
        is_new_client = True

    split = event_id.split(":")
    if len(split) == 3:
        id_filter = Filter().author(split[1]).custom_tag(Alphabet.D, [split[2]])
        events = client.get_events_of([id_filter], timedelta(seconds=config.RELAY_TIMEOUT))
    else:
        id_filter = Filter().id(event_id).limit(1)
        events = client.get_events_of([id_filter], timedelta(seconds=config.RELAY_TIMEOUT))
    if is_new_client:
        client.disconnect()
    if len(events) > 0:
        return events[0]
    else:
        return None

def get_referenced_event_by_id(event_id, kinds=None, client=None, config=None):
    if kinds is None:
        kinds = []
    is_new_client = False
    if client is None:
        keys = Keys.from_sk_str(config.PRIVATE_KEY)
        client = Client(keys)
        for relay in config.RELAY_LIST:
            client.add_relay(relay)
        client.connect()
        is_new_client = True
    if kinds is None:
        kinds = []
    if len(kinds) > 0:
        job_id_filter = Filter().kinds(kinds).event(EventId.from_hex(event_id)).limit(1)
    else:
        job_id_filter = Filter().event(EventId.from_hex(event_id)).limit(1)

    events = client.get_events_of([job_id_filter], timedelta(seconds=config.RELAY_TIMEOUT))

    if is_new_client:
        client.disconnect()
    if len(events) > 0:
        return events[0]
    else:
        return None

def send_event(event, client=None, key=None, config=None):
    relays = []
    is_new_client = False

    for tag in event.tags():
        if tag.as_vec()[0] == 'relays':
            relays = tag.as_vec()[1].split(',')

    if client is None:
        print(key.secret_key().to_hex())

        opts = Options().wait_for_send(False).send_timeout(timedelta(seconds=5)).skip_disconnected_relays(True)
        client = Client.with_opts(key, opts)
        for relay in RELAY_LIST:
            client.add_relay(relay)

        client.connect()
        is_new_client = True

    for relay in relays:
        if relay not in RELAY_LIST:
            client.add_relay(relay)
    client.connect()


    event_id = client.send_event(event)

    for relay in relays:
        if relay not in RELAY_LIST:
            client.remove_relay(relay)

    if is_new_client:
        client.disconnect()

    return event_id