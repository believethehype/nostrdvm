import json
import time
from datetime import timedelta
from pathlib import Path
from nicegui import run, ui
import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, nip04_decrypt, \
    nip04_encrypt, Options, Timestamp, ZapRequestData

from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip89_utils import nip89_fetch_events_pubkey
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key
from nostr_dvm.utils.definitions import EventDefinitions

keys = Keys.from_sk_str(check_and_set_private_key("test_client"))
opts = (Options().wait_for_send(False).send_timeout(timedelta(seconds=2))
        .skip_disconnected_relays(True))

client = Client.with_opts(keys, opts)
relay_list = ["wss://relay.damus.io", "wss://nostr-pub.wellorder.net"]
##"wss://nos.lol", "wss://nostr.wine",
# "wss://relay.nostfiles.dev", "wss://nostr.mom", "wss://nostr.oxtr.dev", "wss://relay.nostr.bg",
# "wss://relay.f7z.io", "wss://pablof7z.nostr1.com", "wss://purplepag.es", "wss://nos.lol",
# "wss://relay.snort.social", "wss://offchain.pub/",
# "wss://nostr-pub.wellorder.net"
for relay in relay_list:
    client.add_relay(relay)
client.connect()

dvm_filter = (Filter().pubkey(keys.public_key()).kinds([EventDefinitions.KIND_NIP90_RESULT_GENERATE_IMAGE,
                                                        EventDefinitions.KIND_FEEDBACK]))  # public events
client.subscribe([dvm_filter])


def nostr_client_test_image(prompt):
    iTag = Tag.parse(["i", prompt, "text"])
    outTag = Tag.parse(["output", "image/png;format=url"])
    paramTag1 = Tag.parse(["param", "size", "1024x1024"])
    tTag = Tag.parse(["t", "bitcoin"])

    bidTag = Tag.parse(['bid', str(1000 * 1000), str(1000 * 1000)])
    relaysTag = Tag.parse(['relays', "wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                           "wss://nostr-pub.wellorder.net"])
    alttag = Tag.parse(["alt", "This is a NIP90 DVM AI task to generate an Image"])
    event = EventBuilder(EventDefinitions.KIND_NIP90_GENERATE_IMAGE, str("Generate an Image."),
                         [iTag, outTag, tTag, paramTag1, bidTag, relaysTag, alttag]).to_event(keys)

    config = DVMConfig
    config.RELAY_LIST = relay_list
    send_event(event, client=client, dvm_config=config)
    return event.as_json()


def nostr_client_test_image_private(prompt, cashutoken):
    keys = Keys.from_sk_str(check_and_set_private_key("test_client"))
    receiver_keys = Keys.from_sk_str(check_and_set_private_key("replicate_sdxl"))

    # TODO more advanced logic, more parsing, params etc, just very basic test functions for now

    relay_list = ["wss://relay.damus.io", "wss://blastr.f7z.xyz", "wss://relayable.org",
                  "wss://nostr-pub.wellorder.net"]
    i_tag = Tag.parse(["i", prompt, "text"])
    outTag = Tag.parse(["output", "image/png;format=url"])
    paramTag1 = Tag.parse(["param", "size", "1024x1024"])
    pTag = Tag.parse(["p", receiver_keys.public_key().to_hex()])

    bid = str(50 * 1000)
    bid_tag = Tag.parse(['bid', bid, bid])
    relays_tag = Tag.parse(["relays", json.dumps(relay_list)])
    alt_tag = Tag.parse(["alt", "Super secret test"])
    cashu_tag = Tag.parse(["cashu", cashutoken])

    encrypted_params_string = json.dumps([i_tag.as_vec(), outTag.as_vec(), paramTag1.as_vec(), bid_tag.as_vec(),
                                          relays_tag.as_vec(), alt_tag.as_vec(), cashu_tag.as_vec()])

    encrypted_params = nip04_encrypt(keys.secret_key(), receiver_keys.public_key(),
                                     encrypted_params_string)

    encrypted_tag = Tag.parse(['encrypted'])
    nip90request = EventBuilder(EventDefinitions.KIND_NIP90_GENERATE_IMAGE, encrypted_params,
                                [pTag, encrypted_tag]).to_event(keys)
    client = Client(keys)
    for relay in relay_list:
        client.add_relay(relay)
    client.connect()
    config = DVMConfig
    send_event(nip90request, client=client, dvm_config=config)
    return nip90request.as_json()


class NotificationHandler(HandleNotification):
    def handle(self, relay_url, event):
        # print(f"Received new event from {relay_url}: {event.as_json()}")
        if event.kind() == 7000:

            try:
                # testlabel2.text = str(event.as_json())
                new = {'key': str(event.pubkey().to_hex()), 'value': event.kind()}
                # table.visible = True
                table.add_rows(new)
                # with ui.row().style('gap:10em'):
                #    with ui.column():
                #        ui.label(event.as_json()).classes('text-2xl').add_slot(".", "with container_element")
                print("[Nostr Client]: " + event.as_json())
            except Exception as e:
                print(e)

        elif 6000 < event.kind() < 6999:
            print("[Nostr Client]: " + event.as_json())
            print("[Nostr Client]: " + event.content())

        elif event.kind() == 4:
            dec_text = nip04_decrypt(keys.secret_key(), event.pubkey(), event.content())
            print("[Nostr Client]: " + f"Received new msg: {dec_text}")

        elif event.kind() == 9735:
            print("[Nostr Client]: " + f"Received new zap:")
            print(event.as_json())

    def handle_msg(self, relay_url, msg):
        pass
        # print(msg)
        # return


async def generate_image():
    # image.source = 'https://dummyimage.com/600x400/ccc/000000.png&text=building+image...'
    table.clear()
    now = Timestamp.now()
    status.text = "Request sent."
    ev = nostr_client_test_image(prompt.value)
    print(ev)
    # ev = await run.cpu_bound(nostr_client_test_image, prompt=prompt.value)

    timeout = 5
    applied_time = 0
    try:
        feedbackfilter = Filter().pubkey(keys.public_key()).kinds([EventDefinitions.KIND_FEEDBACK]).since(now)
        time.sleep(2.0)
        events = client.get_events_of([feedbackfilter], timedelta(seconds=3))
        for event in events:
            nip89info = print_dvm_info(client, event.pubkey().to_hex(), 5100)
            if nip89info is None:
                name = event.pubkey().to_hex()
            else:
                name = nip89info["name"]

            new = {'key': name, 'value': event.kind()}
            table.add_rows(new)
            # print("I GOT THIS:" + event.as_json())

        # client.handle_notifications(NotificationHandler())
        ui.timer(interval=1, callback=lambda: ui.update(table))
        # client.handle_notifications(NotificationHandler())
        # while applied_time < timeout:
        #    status.text = "Event sent.. waiting for replies"
        #    ui.update(status)

        #    print("looking for events..")
        #    time.sleep(1.0)
        #    ui.update(table)
        #    applied_time += 1.0

        # feedbackfilter = Filter().pubkey(keys.public_key()).kinds([EventDefinitions.KIND_FEEDBACK]).since(Timestamp.from_secs())
        # events = client.get_events_of([feedbackfilter], timedelta(seconds=5))
        # for event in events:
        #    print("I GOT THIS:" + event.as_json())
    except Exception as e:
        print(e)


def print_dvm_info(client, pubkey, kind):
    nip89content_str = nip89_fetch_events_pubkey(client, pubkey, kind)
    print(nip89content_str)
    if nip89content_str is not None:
        nip89content = json.loads(nip89content_str)

        return nip89content


if __name__ in {"__main__", "__mp_main__"}:
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    with ui.row().style('gap:10em').classes("row-1"):
        with ui.column().classes("col-1"):
            ui.label('NostrAI Test Page').classes('text-2xl')
            status = ui.label('Test Page, under construction').classes('text-s')
            prompt = ui.input('prompt').style('width: 20em')
            ui.button('Generate', on_click=generate_image).style('width: 15em')
            # image = ui.image().style('width: 60em')
            columns = [
                {'name': 'key', 'label': 'key', 'field': 'key', 'sortable': True},
                {'name': 'value', 'label': 'value', 'field': 'value', 'sortable': True},
            ]
            data = []

            with ui.table(columns, rows=data).classes('w-full bordered') as table:
                # table.visible = False

                table.add_slot(f'body-cell-value', """
                    <q-td :props="props">
                        <q-btn @click="$parent.$emit('action', props)" icon="send" flat />
                    </q-td>
                """)
                table.on('action', lambda msg: print(msg))
            # testlabel2 = ui.table(columns=columns, rows=rows, row_key='name')
            # testlabel2 = ui.label('Result').classes('text-2xl')
            # testlabel2.bind_text_from(model, 'status')

    # t1 = threading.Thread(target=nostr_client).start()
    ui.run(reload=True, port=1234)
