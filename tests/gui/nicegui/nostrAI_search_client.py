import asyncio
import json
import time
from datetime import timedelta
from nicegui import run, ui
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, \
    Options, Timestamp, NostrSigner, EventId, Nip19Event, PublicKey

from nostr_dvm.utils import dvmconfig
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key, get_events_by_id
from nostr_dvm.utils.definitions import EventDefinitions, relay_timeout


@ui.page('/', dark=True)
async def init():
    keys = Keys.parse(check_and_set_private_key("test_client"))
    opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=2))
            .skip_disconnected_relays(True))

    signer = NostrSigner.keys(keys)
    client = Client.with_opts(signer, opts)
    relay_list = dvmconfig.DVMConfig.RELAY_LIST

    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()
    data = []

    async def nostr_client_test_search(prompt, users=None, since="", until=""):
        if users is None:
            users = []

        iTag = Tag.parse(["i", prompt, "text"])
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
        await send_event(event, client=client, dvm_config=config)
        return event

    async def handledvm(now, eventid):
        response = False

        feedbackfilter = Filter().pubkey(keys.public_key()).kinds(
            [EventDefinitions.KIND_NIP90_RESULTS_CONTENT_SEARCH]).since(now).event(eventid)
        feedbackfilter2 = Filter().pubkey(keys.public_key()).kinds(
            [EventDefinitions.KIND_FEEDBACK]).since(now).event(eventid)
        lastfeedback = ""
        while not response:
            events = await client.get_events_of([feedbackfilter], relay_timeout)
            fevents = await client.get_events_of([feedbackfilter2], relay_timeout)
            if len(fevents) > 0:
                if lastfeedback != fevents[0].content():
                    for tag in fevents[0].tags():
                        if tag.as_vec()[0] == "status":
                            if tag.as_vec()[1] == "error":
                                with mainrow:
                                    with maincolumn:
                                        ui.notify(fevents[0].content(), type="negative")
                                        lastfeedback = fevents[0].content()
                                        break
                            else:
                                with mainrow:
                                    with maincolumn:
                                        ui.notify(fevents[0].content(), type="info")
                                        lastfeedback = fevents[0].content()
                                        break

            if len(events) == 0:
                response = False
                await asyncio.sleep(1.0)
                continue
            else:
                if events[0].content() == "[]":
                    return []

                event_etags = json.loads(events[0].content())
                event_ids = []
                for etag in event_etags:
                    eventidob = EventId.from_hex(etag[1])
                    event_ids.append(eventidob)

                config = DVMConfig()
                events = await get_events_by_id(event_ids, client, config)
                if events is None:
                    return []

                listui = []
                for event in events:
                    nip19event = Nip19Event(event.id(), event.author(), dvmconfig.DVMConfig.RELAY_LIST)
                    nip19eventid = nip19event.to_bech32()
                    new = {'result': event.content(), 'author': event.author().to_hex(),
                           'eventid': str(event.id().to_hex()),
                           'time': str(event.created_at().to_human_datetime()),
                           'njump': "https://njump.me/" + nip19eventid,
                           'highlighter': "https://highlighter.com/a/" + nip19eventid,
                           'nostrudel': "https://nostrudel.ninja/#/n/" + nip19eventid
                           }
                    listui.append(new)
                    print(event.as_json())
                return listui

    async def search():
        table.visible = False
        now = Timestamp.now()
        taggedusersfrom = [str(word).lstrip('from:') for word in prompt.value.split() if
                           word.startswith('from:')]
        taggedusersto = [str(word).lstrip('to:') for word in prompt.value.split() if word.startswith('to:')]

        search = prompt.value

        tags = []
        for word in taggedusersfrom:
            search = str(search).replace(word, "")
            user_pubkey = PublicKey.from_bech32(word.replace("@", "")).to_hex()
            pTag = Tag.parse(["p", user_pubkey])
            tags.append(pTag.as_vec())
        search = str(search).replace("from:", "").replace("to:", "").replace("@", "").lstrip().rstrip()
        print(search)
        ev = await nostr_client_test_search(search, tags)
        ui.notify('Request sent to DVM, awaiting results..')

        print("Sent: " + ev.as_json())
        print(str(now.to_human_datetime()))
        data.clear()
        # table.clear()
        listui = await run.io_bound(handledvm, now, ev.id())
        ui.notify("Received results from DVM")
        table.clear()
        for element in listui:
            table.add_rows(element)

        table.visible = True
        ui.update(table)
        return

    mainrow = ui.row().style('gap:10em').classes("row-1")
    maincolumn = ui.column().classes("col-1")

    with mainrow:
        with maincolumn:
            ui.label('Noogle Search').classes('text-2xl')
            prompt = ui.input('Search').style('width: 20em')

            ui.button('Search', on_click=search).style('width: 15em')
            columns = [
                {'name': 'result', 'label': 'result', 'field': 'result', 'sortable': True, 'align': 'left', },
                {'name': 'time', 'label': 'time', 'field': 'time', 'sortable': True, 'align': 'left'},
            ]

            table = ui.table(columns=columns, rows=data, row_key='result',
                             pagination={'rowsPerPage': 10, 'sortBy': 'time', 'descending': True, 'page': 1}).style(
                'width: 50em')
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
                                <q-td v-for="col in props.cols" :key="col.name" :props="props" colspan="50%">
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

ui.run(reload=True, port=1234)
