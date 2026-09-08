from nostr_sdk import ClientBuilder, ReqTarget, SignerAuthenticator
import re
from datetime import timedelta

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Nostr", description="Get notes from Nostr for a given key", dependencies=["nostr_sdk==0.45.1"])

@mcp.tool()
async def get_nostr_notes(npub: str, limit: int) -> str:
    from nostr_sdk import Client, Keys, NostrSigner, Filter, Kind, PublicKey, RelayUrl

    keys = Keys.parse("e318cb3e6ac163814dd297c2c7d745faacfbc2a826eb4f6d6c81430426a83c2b")
    client = ClientBuilder().authenticator(SignerAuthenticator(keys)).build()

    relay_list = ["wss://nostr.oxtr.dev",
                  "wss://relay.primal.net",
                  ]

    for relay in relay_list:
        await client.add_relay(RelayUrl.parse(relay))


    await client.connect()

    f = Filter().kind(Kind(1)).author(PublicKey.parse(npub)).limit(limit)
    events = await client.fetch_events(ReqTarget.auto([f]), timedelta(5))

    index = 1
    notes = ""
    for event in events:
        try:
            pattern = r"[^a-zA-Z0-9\s.!?:,-/]"
            cleaned_string = re.sub(pattern, "", event.content())
            notes = notes + str(index) + ". " +  cleaned_string + "\n"
            index += 1
        except Exception as e:
            print(e)

    return notes
