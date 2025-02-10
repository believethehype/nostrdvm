import json

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Nostr", dependencies=["nostr_dvm==1.1.0"])

@mcp.resource("echo://{message}")
def echo_resource(message: str) -> str:
    """Echo a message as a resource"""
    return f"Resource echo: {message}"



@mcp.tool()
async def get_mcp_dvm_tool() -> str:
    """Fetch Tools from Data Vending Machines"""

    from nostr_sdk import Keys, NostrSigner, Client
    from nostr_dvm.utils.nip89_utils import nip89_fetch_all_dvms_by_kind
    from nostr_dvm.utils.nostr_utils import check_and_set_private_key

    keys = Keys.parse(check_and_set_private_key("test_client"))

    signer = NostrSigner.keys(keys)
    client = Client(signer)

    await client.add_relay("wss://relay.damus.io")
    await client.add_relay("wss://nostr.mom")
    await client.add_relay("wss://nostr.oxtr.dev")
    await client.add_relay("wss://relay.nostrdvm.com")
    await client.connect()
    nip89s = await nip89_fetch_all_dvms_by_kind(client, 5910)
    tools = []
    for announcement in nip89s:
        print(announcement.as_json()["tools"])
        tools.append(announcement.as_json()["tools"])

    return str(tools)



@mcp.prompt()
def echo_prompt(message: str) -> str:
    """Create an echo prompt"""
    return f"Please process this message: {message}"