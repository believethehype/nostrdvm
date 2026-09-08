import asyncio
from nostr_sdk import (
    ClientBuilder, EventBuilder, Keys, Kind, LogLevel, Proxy, RelayUrl, SignerAuthenticator,
    init_logger,
)


async def main():
    init_logger(LogLevel.INFO)

    keys = Keys.generate()
    print(keys.public_key().to_bech32())

    signer = keys
    client = ClientBuilder().authenticator(SignerAuthenticator(signer)).proxy(Proxy.onion("127.0.0.1:9050")).build()
    await client.add_relay(RelayUrl.parse("ws://oxtrdevav64z64yb7x6rjg4ntzqjhedm5b5zjqulugknhzr46ny2qbad.onion"))
    await client.add_relay(RelayUrl.parse("ws://2jsnlhfnelig5acq6iacydmzdbdmg7xwunm4xl6qwbvzacw4lwrjmlyd.onion"))
    await client.connect()

    event = EventBuilder(Kind(1), "Hello from rust-nostr Python bindings!").finalize(keys)
    res = await client.send_event(event)
    print("Event sent:")
    print(f" hex:    {res.id.to_hex()}")
    print(f" bech32: {res.id.to_bech32()}")
    print(f" Successfully sent to:    {res.success}")
    print(f" Failed to send to: {res.failed}")


if __name__ == '__main__':
    asyncio.run(main())
