from datetime import timedelta
from pathlib import Path

import dotenv
import nostr_sdk
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, Timestamp, nip04_decrypt, \
    nip04_encrypt, EventId, Options, PublicKey, Event, ClientSigner

from nostr_dvm.utils import definitions, dvmconfig
from nostr_dvm.utils.nostr_utils import check_and_set_private_key


relay_list = dvmconfig.DVMConfig.RELAY_LIST
keys = Keys.from_sk_str(check_and_set_private_key("test_client"))
wait_for_send = False
skip_disconnected_relays = True
opts = (Options().wait_for_send(wait_for_send).send_timeout(timedelta(seconds=5))
        .skip_disconnected_relays(skip_disconnected_relays))

signer = ClientSigner.KEYS(keys)
client = Client.with_opts(signer, opts)

for relay in relay_list:
    client.add_relay(relay)
client.connect()


def test_referred_events(event_id, kinds=None):

    if kinds is None:
        kinds = []

    if len(kinds) > 0:
        job_id_filter = Filter().kinds(kinds).event(EventId.from_hex(event_id))
    else:
        job_id_filter = Filter().event(EventId.from_hex(event_id))

    events = client.get_events_of([job_id_filter], timedelta(seconds=5))

    if len(events) > 0:
        for event in events:
            print(event.as_json())
        return events[0]
    else:
        print("None")
        return None


def test_all_reposts_by_user_since_days(pubkey, days):
    since_seconds = int(days) * 24 * 60 * 60
    dif = Timestamp.now().as_secs() - since_seconds
    since = Timestamp.from_secs(dif)

    filter = Filter().author(PublicKey.from_hex(pubkey)).kinds([6]).since(since)
    events = client.get_events_of([filter], timedelta(seconds=5))

    if len(events) > 0:
        for event in events:
            print(event.as_json())
        return events[0]
    else:
        print("None")
        return None



if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    # works
    test_referred_events("c70fbd4dbaad22c427d4359981d3bdddd3971ed1a38227ca2f8e5e760f58103c", definitions.EventDefinitions.ANY_RESULT)

    #shows kind 7000 reaction but not kind 6300 result (d05e7ae9271fe2d8968cccb67c01e3458dbafa4a415e306d49b22729b088c8a1)
    test_referred_events("5635e5dd930b3c831f6ab1e348bb488f3c9aca2f13190e93ab5e5e1e1ba1835e", None)

    bech32evnt = EventId.from_hex("5635e5dd930b3c831f6ab1e348bb488f3c9aca2f13190e93ab5e5e1e1ba1835e").to_bech32()
    print(bech32evnt)

    nostruri = EventId.from_hex("5635e5dd930b3c831f6ab1e348bb488f3c9aca2f13190e93ab5e5e1e1ba1835e").to_nostr_uri()
    print(nostruri)


