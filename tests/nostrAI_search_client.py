import asyncio
import json
import time
from datetime import timedelta
from pathlib import Path
from nicegui import run, ui
import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, nip04_decrypt, \
    nip04_encrypt, Options, Timestamp, ZapRequestData, ClientSigner, EventId, Nip19Event, PublicKey

from nostr_dvm.utils import dvmconfig
from nostr_dvm.utils.database_utils import fetch_user_metadata
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip89_utils import nip89_fetch_events_pubkey
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key, get_event_by_id, get_events_by_id
from nostr_dvm.utils.definitions import EventDefinitions

keys = Keys.from_sk_str(check_and_set_private_key("test_client"))
opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=2))
        .skip_disconnected_relays(True))

signer = ClientSigner.keys(keys)
client = Client.with_opts(signer, opts)
relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org", "wss://nostr-pub.wellorder.net"]

for relay in relay_list:
    client.add_relay(relay)
client.connect()

dvm_filter = (Filter().pubkey(keys.public_key()).kinds([EventDefinitions.KIND_NIP90_RESULTS_CONTENT_SEARCH,
                                                        EventDefinitions.KIND_FEEDBACK]))  # public events
client.subscribe([dvm_filter])


def nostr_client_test_search(prompt, users=None, since="", until=""):
    if users is None:
        users = []

    iTag = Tag.parse(["i", prompt, "text"])
    # outTag = Tag.parse(["output", "text/plain"])
    userTag = Tag.parse(['param', 'users', json.dumps(users)])
    sinceTag = Tag.parse(['param', 'since', since])
    untilTag = Tag.parse(['param', 'until', until])
    maxResultsTag = Tag.parse(['param', 'max_results', "100"])

    relaysTag = Tag.parse(['relays', "wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to search content"])

    tags = [iTag, relaysTag, alttag, maxResultsTag]
    if users:
        tags.append(userTag)
    if since != "":
        tags.append(sinceTag)
    if until != "":
        tags.append(untilTag)
    event = EventBuilder(EventDefinitions.KIND_NIP90_CONTENT_SEARCH, str("Search.."),
                         tags).to_event(keys)

    config = DVMConfig
    config.RELAY_LIST = relay_list
    send_event(event, client=client, dvm_config=config)
    return event.as_json()


def handledvm(now):
    response = False

    signer = ClientSigner.keys(keys)
    cli = Client.with_opts(signer, opts)
    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]

    for relay in relay_list:
        cli.add_relay(relay)
    cli.connect()

    feedbackfilter = Filter().pubkey(keys.public_key()).kinds(
        [EventDefinitions.KIND_NIP90_RESULTS_CONTENT_SEARCH]).since(now)
    feedbackfilter2 = Filter().pubkey(keys.public_key()).kinds(
        [EventDefinitions.KIND_FEEDBACK]).since(now)
    events = []
    fevents = []
    while not response:
        events = cli.get_events_of([feedbackfilter], timedelta(seconds=3))
        fevents = cli.get_events_of([feedbackfilter2], timedelta(seconds=3))
        if len(fevents) > 0:
            print(fevents[0].content())
           # ui.notify(fevents[0].content())
        if len(events) == 0:
            response = False
            time.sleep(1.0)
            continue
        else:
            event_etags = json.loads(events[0].content())
            event_ids = []
            for etag in event_etags:
                eventidob = EventId.from_hex(etag[1])
                event_ids.append(eventidob)

            config = DVMConfig()
            events = get_events_by_id(event_ids, cli, config)
            print("HELLO")
            listui = []
            for event in events:
                nip19event = Nip19Event(event.id(), event.pubkey(), dvmconfig.DVMConfig.RELAY_LIST)
                nip19eventid = nip19event.to_bech32()
                new = {'result': event.content(), 'author': event.pubkey().to_hex(),
                       'eventid': str(event.id().to_hex()),
                       'time': str(event.created_at().to_human_datetime()),
                       'njump': "https://njump.me/" + nip19eventid,
                       'highlighter': "https://highlighter.com/a/" + nip19eventid,
                       'nostrudel': "https://nostrudel.ninja/#/n/" + nip19eventid
                       }
                listui.append(new)
                print(event.as_json())
            # ui.update(table)
            response = True
            cli.disconnect()
            cli.shutdown()
            return listui

async def search():

    table.visible = False
    now = Timestamp.now()
    taggedusersfrom = [str(word).lstrip('from:@') for word in prompt.value.split() if word.startswith('from:@')]
    taggedusersto = [str(word).lstrip('to:@') for word in prompt.value.split() if word.startswith('to:@')]

    search = prompt.value
    tags = []
    for word in taggedusersfrom:
        search = str(search).replace(word, "")
        user_pubkey = PublicKey.from_bech32(word).to_hex()
        pTag = ["p", user_pubkey]
        tags.append(pTag)
    search = str(search).replace("from:@", "").replace("to:@", "").lstrip().rstrip()

    ev = nostr_client_test_search(search, tags)
    ui.notify('Request sent to DVM, awaiting results..')

    print("Sent: " + ev)
    listui = []
    print(str(now.to_human_datetime()))
    data.clear()
    table.clear()
    listui = await run.cpu_bound(handledvm, now)
    ui.notify("Received results from DVM")

    for element in listui:
        table.add_rows(element)

    table.visible = True
    ui.update(table)
    return


if __name__ in {"__main__", "__mp_main__"}:
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    with ui.row().style('gap:10em').classes("row-1"):
        with ui.column().classes("col-1"):
            ui.label('NostrAI Search Page').classes('text-2xl')
            prompt = ui.input('Search').style('width: 20em')
            ui.button('Search', on_click=search).style('width: 15em')
            # image = ui.image().style('width: 60em')
            columns = [
                {'name': 'result', 'label': 'result', 'field': 'result', 'sortable': True, 'align': 'left', },
                {'name': 'time', 'label': 'time', 'field': 'time', 'sortable': True, 'align': 'left'},
                # {'name': 'eventid', 'label': 'eventid', 'field': 'eventid', 'sortable': True, 'align': 'left'},
            ]
            data = []

            # table = ui.table(columns, rows=data).classes('w-full bordered')
            table = ui.table(columns=columns, rows=data, row_key='result',
                             pagination={'rowsPerPage': 10, 'sortBy': 'time', 'descending': True, 'page': 1}).style(
                'width: 80em')
            table.add_slot('header', r'''
                <q-tr :props="props">
                    <q-th auto-width />
                    <q-th v-for="col in props.cols" :key="col.name" :props="props">
                        {{ col.label }}
                    </q-th>
                </q-tr>
            ''')
            table.add_slot('body', r'''
                <q-tr :props="props">
                    <q-td auto-width>
                        <q-btn size="sm" color="accent" round dense
                            @click="props.expand = !props.expand"
                            :icon="props.expand ? 'remove' : 'add'" />
                    </q-td>
                    <q-td v-for="col in props.cols" :key="col.name" :props="props" width="200px">
                        {{ col.value }}
                    </q-td>
                </q-tr>
                <q-tr v-show="props.expand" :props="props">
                    <q-td colspan="50%">
                        <a v-bind:href="props.row.njump">Njump </a>
                        <a v-bind:href="props.row.highlighter">Highlighter </a>
                        <a v-bind:href="props.row.nostrudel">NoStrudel</a>
                    </q-td>
                </q-tr>
            ''')

            table.on('action', lambda msg: print(msg))
            table.visible = False

    # t1 = threading.Thread(target=nostr_client).start()
    ui.run(reload=True, port=1234)
