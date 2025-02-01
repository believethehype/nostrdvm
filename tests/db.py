from threading import Thread

from nostr_sdk import Keys, Filter, ClientBuilder, NostrDatabase, SyncOptions, init_logger, LogLevel

init_logger(LogLevel.INFO)
keys = Keys.parse("nsec1ufnus6pju578ste3v90xd5m2decpuzpql2295m3sknqcjzyys9ls0qlc85")
print(keys.public_key().to_bech32())



async def reconcile_db():
    # Create/open SQLite database
    database = NostrDatabase.lmdb("nostr.db")

    # NOT AVAILABLE ON WINDOWS AT THE MOMENT!
    # Create/open nostrdb database
    # database = NostrDatabase.ndb("ndb")

    client = ClientBuilder().database(database).build()

    await client.add_relay("wss://relay.damus.io")
    await client.add_relay("wss://atl.purplerelay.com")
    await client.connect()

    # Negentropy reconciliation
    f = Filter().author(keys.public_key())
    opts = SyncOptions()
    await client.sync(f, opts)

    await do_some_work()

async def do_some_work():
    database = NostrDatabase.lmdb("nostr.db")
    f = Filter().author(keys.public_key()).limit(10)
    events = await database.query(f)

    for event in events.to_vec():
        print(event.as_json())

nostr_dvm_thread = Thread(target=reconcile_db)
nostr_dvm_thread.start()
