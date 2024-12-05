import asyncio
import hashlib
from datetime import timedelta
from io import BytesIO
from urllib.request import urlopen
import re
import mimetypes
import os


from PIL import Image
import numpy
from nostr_sdk import Keys, EventBuilder, Kind, Client, NostrSigner, Filter, EventId, Tag, PublicKey
from blurhash import  encode
import requests
from urllib.parse import urlparse


from nostr_dvm.utils.nostr_utils import send_event
from nostr_dvm.utils.print_utils import bcolors


async def gallery_announce_list(tags, dvm_config, client):
    keys = Keys.parse(dvm_config.NIP89.PK)
    content = ""
    event = EventBuilder(Kind(10011), content).tags(tags).sign_with_keys(keys)
    eventid = await send_event(event, client=client, dvm_config=dvm_config)

    print(
        bcolors.BLUE + "[" + dvm_config.NIP89.NAME + "] Announced Gallery for " + dvm_config.NIP89.NAME + " (EventID: " + str(
            eventid.to_hex()) + ")" + bcolors.ENDC)


async def convert_nip93_to_nip68(private_key, relay_list, user_to_import_npub=None, startindex=0):
    keys = Keys.parse(private_key)
    if user_to_import_npub is None:
        user_to_import_npub = keys.public_key().to_hex()
    
    client = Client(NostrSigner.keys(keys))
    for relay in relay_list:
        await client.add_relay(relay)
    await client.connect()

    nip93_filter = Filter().kind(Kind(1163)).author(PublicKey.parse(user_to_import_npub))

    events =  await client.fetch_events([nip93_filter], timedelta(5))

    events_vec = events.to_vec()
    reversed_events_vec = reversed(events_vec)
    counter = -1
    for event in reversed_events_vec:
        counter += 1
        if counter < startindex:
            continue

        image_url = ""
        content = ""
        m = ""
        x = ""
        dim = ""
        blurhash = ""
        size = ""
        for tag in event.tags().to_vec():
            if tag.as_vec()[0] == "url":
                image_url = tag.as_vec()[1]
            elif tag.as_vec()[0] == "m":
                m = tag.as_vec()[1]
            elif tag.as_vec()[0] == "x":
                x = tag.as_vec()[1]
            elif tag.as_vec()[0] == "dim":
                dim = tag.as_vec()[1]
            elif tag.as_vec()[0] == "blurhash":
                blurhash = tag.as_vec()[1]
            elif tag.as_vec()[0] == "e":
                eventid = tag.as_vec()[1]
                if len(tag.as_vec()) == 3:
                    relay_hint = tag.as_vec()[2]
                    try:
                        await client.connect_relay(relay_hint)
                    except Exception as e:
                        print(relay_hint)
                e_filter = Filter().id(EventId.parse(eventid)).limit(1)
                content_events = await client.fetch_events([e_filter], timedelta(5))
                if len(content_events.to_vec()) > 0:
                    content_event = content_events.to_vec()[0]
                    content =  re.sub(r'^https?:\/\/.*[\r\n]*', '', content_event.content(), flags=re.MULTILINE).rstrip()

        var = input("Convert and post this image? (y(es)/n(o)/d(elete): " + image_url + " Content: " + content + "\n")
        if var == "d" or var == "delete":
            delete_event = EventBuilder.delete([event.id()]).sign_with_keys(keys)
            result = await client.send_event(delete_event)
            print(result.output)


        elif var == "y" or var == "yes":
            try:
                response = requests.get(image_url)
                img = Image.open(BytesIO(response.content)).convert("RGB")

                if blurhash == "":
                    blurhash = encode(numpy.array(img))
                if dim == "":
                    width, height = img.size
                    dim = str(width) + "x" + str(height)
                if m == "":
                    m, _ = mimetypes.guess_type(image_url)
                if size == "":
                    try:
                        d = urlopen(image_url)
                        size = str(d.info()['Content-Length'])
                    except Exception:
                        size = ""
                if x == "":
                    e = BytesIO(response.content)

                    a = urlparse(image_url)
                    print(os.path.basename(a.path))
                    with open(os.path.basename(a.path), "wb") as f:
                        f.write(e.getbuffer())
                    h = hashlib.sha256()
                    with open(os.path.basename(a.path), 'rb') as file:
                        while True:
                            # Reading is buffered, so we can read smaller chunks.
                            chunk = file.read(h.block_size)
                            if not chunk:
                                break
                            h.update(chunk)
                    x_old = x
                    x = h.hexdigest()

            except Exception as e:
                print(e)


            print("Image: " + image_url + " Content: " + content + " m: " + m + " x: " + x + " dim: " + dim + " size: " + size + " blurhash: " + blurhash)

            imeta_tag = Tag.parse(["imeta", "url " + image_url, "m " + m, "alt " + content, "x " + x, "size " + size, "blurhash " + blurhash  ])
            x_tag = Tag.parse(["x", x])
            alt_tag = Tag.parse(["alt", "List of pictures"])
            m_tag = Tag.parse(["m", m])
            tags = [alt_tag, imeta_tag, x_tag, m_tag]
            nip68event = EventBuilder(Kind(20), content).tags(tags).sign_with_keys(keys)
            print(nip68event)

            await client.send_event(nip68event)




if __name__ == '__main__':
    private_key = "nsec..."

    RELAY_LIST = ["wss://relay.primal.net",
                  "wss://relay.damus.io",
                  "wss://relay.nostrplebs.com",
                  "wss://nostr.mom",
                  "wss://nostr.oxtr.dev",
                  "wss://relay.nostr.band"
                  ]
    startindex = 0
    asyncio.run(convert_nip93_to_nip68(private_key, RELAY_LIST, startindex))
