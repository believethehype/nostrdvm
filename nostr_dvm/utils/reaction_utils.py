import asyncio

from nostr_sdk import Tag, Keys, EventBuilder, Kind, NostrSigner, Client

from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key
from nostr_dvm.utils.print import bcolors


async def create_reaction(keys, title, dtag):
    d_tag = Tag.parse(["d", dtag])
    title_tag = Tag.parse(["title", title])

    emoji_tags = []

    # add more if you want
    name = "ThugAmy"
    url = "https://image.nostr.build/ccc229cbe11f5a13a1cc7fd24e13ac53fc78f287ecce0d9a674807e2e20f6fd5.png"
    emoji_tag1 = Tag.parse(["emoji", name, url])
    emoji_tags.append(emoji_tag1)



    keys = Keys.parse(keys)
    content = ""
    event = EventBuilder(Kind(30030), content, [d_tag, title_tag] + emoji_tags).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    # We add the relays we defined above and told our DVM we would want to receive events to.
    for relay in DVMConfig().RELAY_LIST:
        await client.add_relay(relay)
    # We connect the client
    await client.connect()

    eventid = await send_event(event, client=client, dvm_config=DVMConfig())

    print(
        bcolors.BLUE + "[" + "Reaction" + "] Announced (" + eventid.id.to_nostr_uri() +
        " Hex: " + eventid.id.to_hex() + ")" + bcolors.ENDC)


async def delete_reaction(keys, eid: str, dtag: str):
    keys = Keys.parse(keys)
    e_tag = Tag.parse(["e", eid])
    a_tag = Tag.parse(
        ["a", "30030:" + keys.public_key().to_hex() + ":" + dtag])
    event = EventBuilder(Kind(5), "", [e_tag, a_tag]).to_event(keys)

    signer = NostrSigner.keys(keys)
    client = Client(signer)
    # We add the relays we defined above and told our DVM we would want to receive events to.
    for relay in DVMConfig().RELAY_LIST:
        await client.add_relay(relay)
    # We connect the client
    await client.connect()

    eventid = await send_event(event, client, DVMConfig())
    print(
        bcolors.BLUE + "[" + "Reaction" + "] deleted (" + eventid.id.to_nostr_uri() +
        " Hex: " + eventid.id.to_hex() + ")" + bcolors.ENDC)


keys = check_and_set_private_key("test_client")
eventid = "da05cefc512ad43363f84131343f5d2a80303ea3b9368b9ad7f010e07db37d90"

asyncio.run(create_reaction(keys=keys, title="ThugAmy", dtag="ThugAmy"))
#asyncio.run(delete_reaction(keys=keys, eid=eventid,  dtag="ThugAmy"))