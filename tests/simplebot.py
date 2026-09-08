import asyncio


from nostr_dvm.utils.nostr_utils import send_nip04_dm
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_sdk import (
    ClientBuilder, Event, Filter, Keys, Kind, KindStandard, LogLevel, RelayUrl, ReqTarget,
    SignerAuthenticator, Timestamp, UnsignedEvent, UnwrappedGift, init_logger, nip04_decrypt,
    nip17_make_private_msg_async,
)

from nostr_dvm.utils.sdk_utils import handle_notifications


async def test():
    init_logger(LogLevel.DEBUG)

    # sk = SecretKey.from_bech32("nsec1ufnus6pju578ste3v90xd5m2decpuzpql2295m3sknqcjzyys9ls0qlc85")
    # keys = Keys(sk)
    # OR
    keys = Keys.parse("nsec1ufnus6pju578ste3v90xd5m2decpuzpql2295m3sknqcjzyys9ls0qlc85")

    sk = keys.secret_key()
    config = DVMConfig()
    config.PRIVATE_KEY = sk.to_hex()
    pk = keys.public_key()
    print(f"Bot public key: {pk.to_bech32()}")

    client = ClientBuilder().authenticator(SignerAuthenticator(keys)).build()
    await client.add_relay(RelayUrl.parse("wss://nostr.mom"))
    await client.add_relay(RelayUrl.parse("wss://nostr.oxtr.dev"))
    await client.connect()

    now = Timestamp.now()

    nip04_filter = Filter().pubkey(pk).kind(Kind(4)).since(now)
    nip59_filter = Filter().pubkey(pk).kind(Kind.from_std(KindStandard.GIFT_WRAP)).limit(0)
    await client.subscribe(ReqTarget.auto([nip04_filter]))
    await client.subscribe(ReqTarget.auto([nip59_filter]))

    class NotificationHandler:
        async def handle(self, relay_url, subscription_id, event: Event):
            print(f"Received new event from {relay_url}: {event.as_json()}")
            if event.kind().as_u16() == 4:
                print("Decrypting NIP04 event")
                try:
                    msg = nip04_decrypt(sk, event.author(), event.content())
                    print(f"Received new msg: {msg}")
                    await send_nip04_dm(client, msg, event.author(), config)


                except Exception as e:
                    print(f"Error during content NIP04 decryption: {e}")
            elif event.kind().as_std() == KindStandard.GIFT_WRAP:
                print("Decrypting NIP59 event")
                try:
                    # Extract rumor
                    unwrapped_gift = await UnwrappedGift.from_gift_wrap_async(keys, event)
                    sender = unwrapped_gift.sender()
                    rumor: UnsignedEvent = unwrapped_gift.rumor()

                    # Check timestamp of rumor
                    if rumor.created_at().as_secs() >= now.as_secs():
                        if rumor.kind().as_std() == KindStandard.PRIVATE_DIRECT_MESSAGE:
                            msg = rumor.content()
                            print(f"Received new msg [sealed]: {msg}")
                            reply = await nip17_make_private_msg_async(keys, sender, f"Echo: {msg}")
                            await client.send_event(reply)
                        else:
                            print(f"{rumor.as_json()}")
                except Exception as e:
                    print(f"Error during content NIP59 decryption: {e}")

        async def handle_msg(self, relay_url, msg):
            var = None

    #await client.handle_notifications(NotificationHandler())

    # To handle notifications and continue with code execution, use:
    asyncio.create_task(handle_notifications(client, NotificationHandler()))
    while True:
        print("lol.")
        await asyncio.sleep(5)


async def async_input():
    while True:
        print("lol")
        await asyncio.sleep(5)


#async def main():
#    await asyncio.gather(asyncio.to_thread(async_input), test())

if __name__ == "__main__":
    asyncio.run(test())
