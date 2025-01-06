LPimport asyncio

from nostr_sdk import Tag, Keys, EventBuilder, Kind, NostrSigner, Client

from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key
from nostr_dvm.utils.print_utils import bcolors

import json, requests
from datetime import timedelta
from nostr_sdk import Client, Kind, Alphabet, SingleLetterTag, Filter, init_logger, LogLevel, \
    NostrDatabase, ClientBuilder, SyncOptions, SyncDirection

init_logger(LogLevel.ERROR)


async def create_gif_collection(keys, title, dtag):
    d_tag = Tag.parse(["d", dtag])
    title_tag = Tag.parse(["title", title])

    emoji_tags = []

    name = "laserliotta"
    url = "https://image.nostr.build/33259988b8ebf536ca776e44855ffa02b04b4a24e938d399cd697b613231b866.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "laserliottafancy"
    url = "https://image.nostr.build/433c192f63b323e75dd07719914d92db52971eec2748578cce2f6203d3d1db09.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "sadparty"
    url = "https://image.nostr.build/9c4bd2f74db36bb43dce81eef3e4ab4a17826d692064fef301bf454c242b91d5.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "myman"
    url = "https://image.nostr.build/a46c1ba19db20c7da03013fb5e22dd48b5d0fa623fb91ac5aa26ac6b9c82c18d.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "impressiveverynice"
    url = "https://image.nostr.build/040da2afb53d2a473c65ba47dd6b8ff445dd5ceaafcc0bb1c9cf762728f46942.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "itshappening"
    url = "https://image.nostr.build/958a96fe082f0c964c670a481787658a2b30aefbeaec8c995d6a1f1a20261125.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "noooooo"
    url = "https://image.nostr.build/05ea0ead2022f42cbb6746d964c7251eba3c5f6739cd67baa0f7d0c8e9d7341a.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "wtfmatrix"
    url = "https://image.nostr.build/4068c71068d446b6c6f873f8862edd7a4058e43fc3ea94375817abf0825742d4.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "gfy"
    url = "https://image.nostr.build/b6a2266f5ae940ac848d3be3161e42d207d73fdd5a9c5e15ddffb486d5612ac0.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "gfy_finger"
    url = "https://image.nostr.build/9cf4e3bca4bf1dc800f66ece16fed508c2a8d5e9f7da3ada2096fae8b319f62f.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))


    name = "lasereyesboys"
    url = "https://image.nostr.build/cce26068644c845788cf4ab6bf504e854928268658a47190bc8625f6b2793262.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "evenharder"
    url = "https://image.nostr.build/6444edef288bde5d02325dc1fe9c31de918fc10c56bf6c7b6bf4972de784773b.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "spiderman"
    url = "https://image.nostr.build/9ed54bc4e56ff6aac88a0c7a8e13e9eb6f7fbd5633fed789e1a30669b5b0c838.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name ="homerdisappear"
    url = "https://image.nostr.build/2335af37d6e262a8c41edbdd1017581ca5dda6c3cb5b14ee30edb62aa443968f.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "disagree"
    url = "https://image.nostr.build/6d492eec5b82d4e5d7343a3c553cba618182cba572a4e3d43c162d2d9221d863.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "sus"
    url = "https://image.nostr.build/45443c70a51e51b71de1a8e6b2b832a73bd18dcc2441c2fbf95f277104f0af44.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "waiting"
    url = "https://image.nostr.build/9d3c1b27545f35e1736476021f7fb5276903ad1b332fd9670513536359cbeea9.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))

    name = "wellwaiting"
    url = "https://image.nostr.build/3bd94b4065f122f6ae5d76774e6b3534b6c9f291b65a411cc4af47e8b4896abd.gif"
    emoji_tags.append(Tag.parse(["emoji", name, url]))


    keys = Keys.parse(keys)
    event = EventBuilder(Kind(30030), "").tags([d_tag, title_tag] + emoji_tags).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
    # We add the relays we defined above and told our DVM we would want to receive events to.
    for relay in DVMConfig().ANNOUNCE_RELAY_LIST:
        await client.add_relay(relay)
    # We connect the client
    await client.connect()

    eventid = await send_event(event, client=client, dvm_config=DVMConfig())

    print(
        bcolors.BLUE + "[" + "Gif Collection" + "] Announced (" + eventid.id.to_nostr_uri() +
        " Hex: " + eventid.id.to_hex() + ")" + bcolors.ENDC)


async def delete_gif_collection(keys, eid: str, dtag: str):
    keys = Keys.parse(keys)
    e_tag = Tag.parse(["e", eid])
    a_tag = Tag.parse(
        ["a", "30030:" + keys.public_key().to_hex() + ":" + dtag])
    event = EventBuilder(Kind(5), "").tags([e_tag, a_tag]).sign_with_keys(keys)

    client = Client(NostrSigner.keys(keys))
    # We add the relays we defined above and told our DVM we would want to receive events to.
    for relay in DVMConfig().RELAY_LIST:
        await client.add_relay(relay)
    # We connect the client
    await client.connect()

    eventid = await send_event(event, client, DVMConfig())
    print(
        bcolors.BLUE + "[" + "Reaction" + "] deleted (" + eventid.id.to_nostr_uri() +
        " Hex: " + eventid.id.to_hex() + ")" + bcolors.ENDC)



if __name__ == "__main__":

    keys =  "yournsec" #check_and_set_private_key("test_client")

    asyncio.run(create_gif_collection(keys=keys, title="DBTH's gif collection", dtag="dbth"))

    #event id of collection you want to delete
    #eventid = "da05cefc512ad43363f84131343f5d2a80303ea3b9368b9ad7f010e07db37d90"
    # asyncio.run(delete_gif_collection(keys=keys, eid=eventid,  dtag="ThugAmy"))
