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
from nostr_sdk import (
    ClientBuilder, EventBuilder, EventId, Filter, Keys, Kind, PublicKey, RelayUrl, ReqTarget,
    SignerAuthenticator, Tag,
)
from blurhash import  encode
import requests
from urllib.parse import urlparse


from nostr_dvm.utils.nostr_utils import send_event, print_send_result
from nostr_dvm.utils.print_utils import bcolors


async def gallery_announce_list(tags, dvm_config, client):
    keys = Keys.parse(dvm_config.NIP89.PK)
    content = ""
    event = EventBuilder(Kind(10011), content).tags(tags).finalize(keys)
    eventid = await send_event(event, client=client, dvm_config=dvm_config)

    print(
        bcolors.BLUE + "[" + dvm_config.NIP89.NAME + "] Announced Gallery for " + dvm_config.NIP89.NAME + " (EventID: " + str(
            eventid.to_hex()) + ")" + bcolors.ENDC)


async def convert_nip93_to_nip68(private_key, relay_list, user_to_import_npub=None, startindex=0):
    keys = Keys.parse(private_key)
    if user_to_import_npub is None:
        user_to_import_npub = keys.public_key().to_hex()
    
    client = ClientBuilder().authenticator(SignerAuthenticator(keys)).build()
    for relay in relay_list:
        await client.add_relay(RelayUrl.parse(relay))
    await client.connect()

    nip93_filter = Filter().kind(Kind(1163)).author(PublicKey.parse(user_to_import_npub))

    events =  await client.fetch_events(ReqTarget.auto([nip93_filter]), timedelta(5))

    events_vec = events
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
        for tag in event.tags():
            if tag.to_vec()[0] == "url":
                image_url = tag.to_vec()[1]
            elif tag.to_vec()[0] == "m":
                m = tag.to_vec()[1]
            elif tag.to_vec()[0] == "x":
                x = tag.to_vec()[1]
            elif tag.to_vec()[0] == "dim":
                dim = tag.to_vec()[1]
            elif tag.to_vec()[0] == "blurhash":
                blurhash = tag.to_vec()[1]
            elif tag.to_vec()[0] == "e":
                eventid = tag.to_vec()[1]
                if len(tag.to_vec()) == 3:
                    relay_hint = tag.to_vec()[2]
                    try:
                        await client.connect_relay(RelayUrl.parse(relay_hint))
                    except Exception as e:
                        print(relay_hint)
                e_filter = Filter().id(EventId.parse(eventid)).limit(1)
                content_events = await client.fetch_events(ReqTarget.auto([e_filter]), timedelta(5))
                content_events_vec = content_events
                if len(content_events_vec) > 0:
                    content_event = content_events_vec[0]
                    content =  re.sub(r'^https?:\/\/.*[\r\n]*', '', content_event.content(), flags=re.MULTILINE).rstrip()

        var = input("Convert and post this image? (y(es)/n(o)/d(elete): " + image_url + " Content: " + content + "\n")
        if var == "d" or var == "delete":
            delete_event = EventBuilder(Kind(5), "").tags([Tag.event(event.id())]).finalize(keys)
            response_status = await client.send_event(delete_event)
            print_send_result(response_status)



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
            nip68event = EventBuilder(Kind(20), content).tags(tags).finalize(keys)
            print(nip68event)

            await client.send_event(nip68event)




if __name__ == '__main__':
    private_key = "nsec..."

    RELAY_LIST = ["wss://relay.primal.net",
                  "wss://relay.nostrplebs.com",
                  "wss://nostr.mom",
                  "wss://nostr.oxtr.dev",
                  ]
    startindex = 0
    asyncio.run(convert_nip93_to_nip68(private_key, RELAY_LIST, startindex))
