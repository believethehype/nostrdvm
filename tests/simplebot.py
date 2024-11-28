import asyncio

from nostr_sdk import Client, NostrSigner, Keys, Event, UnsignedEvent, Filter, \
    HandleNotification, Timestamp, nip04_decrypt, UnwrappedGift, init_logger, LogLevel, Kind, KindEnum

from nostr_dvm.utils.nostr_utils import send_nip04_dm


async def test():
    init_logger(LogLevel.DEBUG)

    # sk = SecretKey.from_bech32("nsec1ufnus6pju578ste3v90xd5m2decpuzpql2295m3sknqcjzyys9ls0qlc85")
    # keys = Keys(sk)
    # OR
    keys = Keys.parse("nsec1ufnus6pju578ste3v90xd5m2decpuzpql2295m3sknqcjzyys9ls0qlc85")

    sk = keys.secret_key()
    pk = keys.public_key()
    print(f"Bot public key: {pk.to_bech32()}")

    client = Client(NostrSigner.keys(keys))

    await client.add_relay("wss://relay.damus.io")
    await client.add_relay("wss://nostr.mom")
    await client.add_relay("wss://nostr.oxtr.dev")
    await client.connect()

    now = Timestamp.now()

    nip04_filter = Filter().pubkey(pk).kind(Kind.from_enum(KindEnum.ENCRYPTED_DIRECT_MESSAGE())).since(now)
    nip59_filter = Filter().pubkey(pk).kind(Kind.from_enum(KindEnum.GIFT_WRAP())).limit(0)
    await client.subscribe([nip04_filter, nip59_filter], None)

    class NotificationHandler(HandleNotification):
        async def handle(self, relay_url, subscription_id, event: Event):
            print(f"Received new event from {relay_url}: {event.as_json()}")
            if event.kind().as_enum() == KindEnum.ENCRYPTED_DIRECT_MESSAGE():
                print("Decrypting NIP04 event")
                try:
                    msg = nip04_decrypt(sk, event.author(), event.content())
                    print(f"Received new msg: {msg}")
                    await send_nip04_dm(client, msg, event.author(), sk)


                except Exception as e:
                    print(f"Error during content NIP04 decryption: {e}")
            elif event.kind().as_enum() == KindEnum.GIFT_WRAP():
                print("Decrypting NIP59 event")
                try:
                    # Extract rumor
                    unwrapped_gift = UnwrappedGift.from_gift_wrap(NostrSigner(keys), event)
                    sender = unwrapped_gift.sender()
                    rumor: UnsignedEvent = unwrapped_gift.rumor()

                    # Check timestamp of rumor
                    if rumor.created_at().as_secs() >= now.as_secs():
                        if rumor.kind().as_enum() == KindEnum.PRIVATE_DIRECT_MESSAGE():
                            msg = rumor.content()
                            print(f"Received new msg [sealed]: {msg}")
                            await client.send_private_msg(sender, f"Echo: {msg}", None)
                        else:
                            print(f"{rumor.as_json()}")
                except Exception as e:
                    print(f"Error during content NIP59 decryption: {e}")

        async def handle_msg(self, relay_url, msg):
            var = None

    #await client.handle_notifications(NotificationHandler())

    # To handle notifications and continue with code execution, use:
    asyncio.create_task(client.handle_notifications(NotificationHandler()))
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