from nostr_sdk import Tag, Keys, EventBuilder

from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.nostr_utils import send_event
from nostr_dvm.utils.print import bcolors


async def nip65_announce_relays(dvm_config, client):
    tags = []

    for relay in dvm_config.RELAY_LIST:
        r_tag = Tag.parse(["r", relay])
        tags.append(r_tag)

    keys = Keys.parse(dvm_config.NIP89.PK)
    content = ""

    event = EventBuilder(EventDefinitions.KIND_RELAY_ANNOUNCEMENT, content, tags).to_event(keys)
    eventid = await send_event(event, client=client, dvm_config=dvm_config, blastr=True)
    if (eventid is not None):
        print(
            bcolors.BLUE + "[" + dvm_config.NIP89.NAME + "] Announced NIP 65 for " + dvm_config.NIP89.NAME + " (EventID: " + str(
                eventid.id.to_hex()) + ")" + bcolors.ENDC)
    else:
        print(
            bcolors.RED + "[" + dvm_config.NIP89.NAME + "] Could not announce NIP 65 for " + dvm_config.NIP89.NAME + bcolors.ENDC)
