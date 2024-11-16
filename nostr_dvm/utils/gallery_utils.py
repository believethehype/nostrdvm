from nostr_sdk import Keys, EventBuilder, Kind

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
