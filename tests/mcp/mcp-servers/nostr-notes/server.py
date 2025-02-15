import re
from datetime import timedelta

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Nostr", description="Get notes from Nostr for a given key", dependencies=["nostr_sdk==0.39.0"])

@mcp.tool()
async def get_nostr_notes(npub: str, limit: int) -> str:
    from nostr_sdk import Client, Keys, NostrSigner, Filter, Kind, PublicKey

    keys = Keys.parse("e318cb3e6ac163814dd297c2c7d745faacfbc2a826eb4f6d6c81430426a83c2b")
    client = Client(NostrSigner.keys(keys))

    relay_list = ["wss://relay.damus.io",
                  "wss://nostr.oxtr.dev",
                  "wss://relay.primal.net",
                  ]

    for relay in relay_list:
        await client.add_relay(relay)


    await client.connect()

    f = Filter().kind(Kind(1)).author(PublicKey.parse(npub)).limit(limit)
    events = await client.fetch_events(f, timedelta(5))

    index = 1
    notes = ""
    for event in events.to_vec():
        try:
            pattern = r"[^a-zA-Z0-9\s.!?:,-/]"
            cleaned_string = re.sub(pattern, "", event.content())
            notes = notes + str(index) + ". " +  cleaned_string + "\n"
            index += 1
        except Exception as e:
            print(e)

    return notes

