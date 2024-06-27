from nostr_sdk import Tag, Keys, EventBuilder, Kind

from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.nostr_utils import send_event
from nostr_dvm.utils.print import bcolors


async def gallery_announce_list(tags, dvm_config, client):


    keys = Keys.parse(dvm_config.NIP89.PK)
    content = ""
    event = EventBuilder(Kind(10011), content, tags).to_event(keys)
    eventid = await send_event(event, client=client, dvm_config=dvm_config, blastr=True)

    print(bcolors.BLUE + "[" + dvm_config.NIP89.NAME + "] Announced Gallery for " + dvm_config.NIP89.NAME +" (EventID: " + str(eventid.to_hex()) +")" + bcolors.ENDC)
