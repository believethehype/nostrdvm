import asyncio
import json
from pathlib import Path

import dotenv
from nostr_sdk import Keys, Client, Tag, EventBuilder, Filter, HandleNotification, Timestamp, nip04_decrypt, \
    nip44_encrypt, Nip44Version, NostrSigner, Event, Kind, init_logger, LogLevel

from nostr_dvm.utils.definitions import EventDefinitions
from nostr_dvm.utils.nip89_utils import nip89_fetch_all_dvms_by_kind
from nostr_dvm.utils.nostr_utils import send_event, check_and_set_private_key

relay_list = ["wss://nostr.oxtr.dev", "wss://relay.nostrdvm.com"]


async def nostr_client_test_mcp_get_tools(dvm_pubkey):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    outTag = Tag.parse(["output", "application/json"])
    cTag = Tag.parse(["c", "list-tools"])
    alttag = Tag.parse(["alt", "This is a NIP90 Request to contact MCP server"])
    relaysTag = Tag.parse(['relays'] + relay_list)
    ptag = Tag.parse(["p", dvm_pubkey])

    event = EventBuilder(EventDefinitions.KIND_NIP90_MCP, str("MCP request")).tags(
                         [ptag, outTag, alttag, cTag, relaysTag]).sign_with_keys(keys)


    client = Client(NostrSigner.keys(keys))

    for relay in relay_list:
        await client.add_relay(relay)

    await client.connect()

    result = await client.send_event(event)
    print(result)
    return result


async def nostr_client_test_mcp_execute_tool(tool_name, tool_parameters, dvm_pubkey):
    keys = Keys.parse(check_and_set_private_key("test_client"))

    outTag = Tag.parse(["output", "application/json"])
    cTag = Tag.parse(["c", "execute-tool"])
    alttag = Tag.parse(["alt", "This is a NIP90 Request to contact MCP server"])
    relaysTag = Tag.parse(['relays'] + relay_list)
    ptag = Tag.parse(["p", dvm_pubkey])

    payload = {"name": tool_name,
                "parameters": json.loads(tool_parameters)
               }

    event = EventBuilder(EventDefinitions.KIND_NIP90_MCP, json.dumps(payload)).tags(
                         [ptag, outTag, alttag, cTag, relaysTag]).sign_with_keys(keys)


    client = Client(NostrSigner.keys(keys))

    for relay in relay_list:
        await client.add_relay(relay)

    await client.connect()

    result = await client.send_event(event)
    print(result)
    return result




async def nostr_client():


    init_logger(LogLevel.INFO)
    keys = Keys.parse(check_and_set_private_key("test_client"))

    pk = keys.public_key()
    print(f"Bot public key: {pk.to_bech32()}")

    signer = NostrSigner.keys(keys)
    client = Client(signer)

    await client.add_relay("wss://relay.damus.io")
    await client.add_relay("wss://nostr.mom")
    await client.add_relay("wss://nostr.oxtr.dev")
    await client.add_relay("wss://relay.nostrdvm.com")
    await client.connect()

    now = Timestamp.now()

    mcp_filter = Filter().pubkey(pk).kind(Kind(6910)).limit(0)
    await client.subscribe(mcp_filter, None)

    print("Existing MCP DVMS:")
    nip89s = await nip89_fetch_all_dvms_by_kind(client, 5910)
    for announcement in nip89s:
        print(announcement.as_json())



    dvm_pubkey = "85a319f3084cd23d3534d0ab2ddb80454df5dbd296d688257b4a336ed571d36a"

    #await nostr_client_test_mcp_get_tools(dvm_pubkey=dvm_pubkey)

    await nostr_client_test_mcp_execute_tool(tool_name="get-crypto-price", tool_parameters=json.dumps({"symbol": "BTC"}), dvm_pubkey=dvm_pubkey)
    #await nostr_client_test_mcp_execute_tool(tool_name="echo_tool", tool_parameters={"message": "Hello"}, dvm_pubkey=dvm_pubkey)

    #await nostr_client_test_mcp_get_tools(dvm_pubkey=dvm_pubkey)
    #await nostr_client_test_mcp_execute_tool(tool_name="extract", tool_parameters={"url": "https://en.wikipedia.org/wiki/Nostr"}, dvm_pubkey=dvm_pubkey)


    class NotificationHandler(HandleNotification):
        async def handle(self, relay_url, subscription_id, event: Event):
            print(f"Received new event from {relay_url}: {event.as_json()}")

            if event.kind().as_u16() == 6910:
                print(event.content() + "\n")



        async def handle_msg(self, relay_url, msg):
            _var = None

    await client.handle_notifications(NotificationHandler())


if __name__ == '__main__':

    env_path = Path('../../.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    asyncio.run(nostr_client())
