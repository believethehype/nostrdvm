from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.nostr_utils import send_event
from nostr_dvm.utils.print_utils import bcolors
from nostr_sdk import Tag, Keys, EventBuilder, Timestamp


async def beat(dvm_config, client, frequency=300):
    status_tag = Tag.parse(["status", "My heart keeps beating like a hammer"])
    d_tag = Tag.parse(["d", dvm_config.NIP89.DTAG])
    expiration_tag = Tag.parse(["expiration", str(Timestamp.now().as_secs() + frequency)])

    tags = [status_tag, d_tag, expiration_tag]
    keys = Keys.parse(dvm_config.NIP89.PK)
    content = "Alive and kicking"

    event = EventBuilder(EventDefinitions.KIND_HEARTBEAT, content).tags(tags).sign_with_keys(keys)

    response_status = await send_event(event, client=client, dvm_config=dvm_config, broadcast=True)


    print(bcolors.BRIGHT_RED + "[" + dvm_config.NIP89.NAME + "] Sent heartbeat for " + dvm_config.NIP89.NAME +  ". Success: " + str(response_status.success) + " Failed: " + str(response_status.failed) + " EventID: "
          + response_status.id.to_hex() + " / " + response_status.id.to_bech32())
