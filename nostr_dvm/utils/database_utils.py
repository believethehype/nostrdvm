# DATABASE LOGIC
import json
import os
import shutil
import sqlite3
from dataclasses import dataclass
from logging import Filter
from sqlite3 import Error

from nostr_sdk import (
    Filter, Keys, Kind, NostrLmdb, PublicKey, ReqTarget, Timestamp, nip17_make_private_msg_async,
)

from nostr_dvm.utils.definitions import relay_timeout
from nostr_dvm.utils.nostr_utils import send_nip04_dm
from nostr_dvm.utils.sdk_utils import ensure_sdk_callback_loop


@dataclass
class User:
    npub: str
    balance: int
    iswhitelisted: bool
    isblacklisted: bool
    name: str
    nip05: str
    lud16: str
    lastactive: int
    subscribed: int


def create_sql_table(db):
    try:
        import os
        if not os.path.exists(r'db'):
            os.makedirs(r'db')
        if not os.path.exists(r'outputs'):
            os.makedirs(r'outputs')
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute(""" CREATE TABLE IF NOT EXISTS users (
                                            npub text PRIMARY KEY,
                                            sats integer NOT NULL,
                                            iswhitelisted boolean,
                                            isblacklisted boolean,
                                            nip05 text,
                                            lud16 text,
                                            name text,
                                            lastactive integer,
                                            subscribed integer
                                        ); """)
        cur.execute("SELECT name FROM sqlite_master")
        con.close()

    except Error as e:
        print(e)


def add_sql_table_column(db):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute(""" ALTER TABLE users ADD COLUMN subscribed 'integer' """)
        con.close()
    except Error as e:
        print(e)


def add_to_sql_table(db, npub, sats, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive, subscribed):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        data = (npub, sats, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive, subscribed)
        cur.execute("INSERT or IGNORE INTO users VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", data)
        con.commit()
        con.close()
    except Error as e:
        print("Error when Adding to DB: " + str(e))


def update_sql_table(db, npub, balance, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive, subscribed):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        data = (balance, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive, subscribed, npub)

        cur.execute(""" UPDATE users
                  SET sats = ? ,
                      iswhitelisted = ? ,
                      isblacklisted = ? ,
                      nip05 = ? ,
                      lud16 = ? ,
                      name = ? ,
                      lastactive = ?,
                      subscribed = ?
                  WHERE npub = ?""", data)
        con.commit()
        con.close()
    except Error as e:
        print("Error Updating DB: " + str(e))


def get_from_sql_table(db, npub):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE npub=?", (npub,))
        row = cur.fetchone()
        con.close()
        if row is None:
            return None
        else:

            if len(row) < 9:
                add_sql_table_column(db)
                # Migrate 

            return User(npub=row[0], balance=row[1], iswhitelisted=row[2],
                        isblacklisted=row[3], nip05=row[4], lud16=row[5], name=row[6],
                        lastactive=row[7], subscribed=(row[8] or 0) if len(row) >= 9 else 0)

    except Error as e:
        print("Error Getting from DB: " + str(e))


def delete_from_sql_table(db, npub):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("DELETE FROM users WHERE npub=?", (npub,))
        con.commit()
        con.close()
    except Error as e:
        print(e)


def clean_db(db):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE npub IS NULL OR npub = '' ")
        rows = cur.fetchall()
        for row in rows:
            print(row)
            delete_from_sql_table(db, row[0])
        con.close()
        return rows
    except Error as e:
        print(e)


def list_db(db):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("SELECT * FROM users ORDER BY sats DESC")
        rows = cur.fetchall()
        for row in rows:
            print(row)
        con.close()
    except Error as e:
        print(e)


def update_user_fields(db, npub, **fields):
    if not fields or not set(fields) <= {"name", "nip05", "lud16", "lastactive", "subscribed",
                                        "iswhitelisted", "isblacklisted"}:
        raise ValueError("Unsupported user fields")
    connection = sqlite3.connect(db)
    try:
        with connection:
            assignments = ", ".join(f"{field} = ?" for field in fields)
            connection.execute(f"UPDATE users SET {assignments} WHERE npub = ?", (*fields.values(), npub))
    finally:
        connection.close()


def debit_user_balance(db, npub, amount):
    amount = int(amount)
    if amount < 0:
        raise ValueError("Debit amount must not be negative")
    connection = sqlite3.connect(db)
    try:
        with connection:
            cursor = connection.execute(
                "UPDATE users SET sats = sats - ?, lastactive = ? WHERE npub = ? AND sats >= ?",
                (amount, Timestamp.now().as_secs(), npub, amount))
            if cursor.rowcount == 0:
                return None
            return connection.execute("SELECT sats FROM users WHERE npub = ?", (npub,)).fetchone()[0]
    finally:
        connection.close()


def credit_user_balance(db, npub, additional_sats, initial_balance=0, name="", nip05="", lud16=""):
    connection = sqlite3.connect(db)
    try:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO users (npub, sats, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive, subscribed) "
                "VALUES (?, ?, 0, 0, ?, ?, ?, ?, 0) ON CONFLICT(npub) DO NOTHING",
                (npub, initial_balance, nip05, lud16, name, Timestamp.now().as_secs()))
            connection.execute("UPDATE users SET sats = sats + ?, lastactive = ? WHERE npub = ?",
                               (int(additional_sats), Timestamp.now().as_secs(), npub))
            balance = connection.execute("SELECT sats FROM users WHERE npub = ?", (npub,)).fetchone()[0]
        return balance
    finally:
        connection.close()


async def update_user_balance(db, npub, additional_sats, client, config, giftwrap=False):
    user = get_from_sql_table(db, npub)
    if user is None:
        name, nip05, lud16 = await fetch_user_metadata(npub, client)
        credit_user_balance(db, npub, additional_sats, config.NEW_USER_BALANCE, name, nip05, lud16)
        print("Adding User: " + npub + " (" + npub + ")")
    else:
        new_balance = credit_user_balance(db, npub, additional_sats)
        print("Updated user balance for: " + str(user.name) +
              " Zap amount: " + str(additional_sats) + " Sats. New balance: " + str(new_balance) + " Sats")

        if config is not None:
            keys = Keys.parse(config.PRIVATE_KEY)

            message = ("Added " + str(additional_sats) + " Sats to balance. New balance is " + str(
                new_balance) + " Sats.")

            # always send giftwrapped. sorry not sorry.
            #if giftwrap:
            event = await nip17_make_private_msg_async(keys, PublicKey.parse(npub), message)
            await client.send_event(event)
            #else:
            #    await send_nip04_dm(client, message, PublicKey.parse(npub), config)


async def update_user_subscription(npub, subscribed_until, client, dvm_config):
    user = get_from_sql_table(dvm_config.DB, npub)
    if user is None:
        name, nip05, lud16 = await fetch_user_metadata(npub, client)
        add_to_sql_table(dvm_config.DB, npub, dvm_config.NEW_USER_BALANCE, False, False,
                         nip05, lud16, name, Timestamp.now().as_secs(), subscribed_until)
        update_user_fields(dvm_config.DB, npub, subscribed=subscribed_until)
        print("Adding User: " + npub + " (" + npub + ")")
    else:
        user = get_from_sql_table(dvm_config.DB, npub)

        update_user_fields(dvm_config.DB, npub, lastactive=Timestamp.now().as_secs(), subscribed=subscribed_until)
        print("Updated user subscription for: " + str(user.name))


async def get_or_add_user(db, npub, client, config, update=False, skip_meta=False):
    user = get_from_sql_table(db, npub)
    if user is None:
        try:
            if skip_meta:
                name = npub
                nip05 = ""
                lud16 = ""
            else:
                name, nip05, lud16 = await fetch_user_metadata(npub, client)
            print("Adding User: " + npub + " (" + npub + ")")
            add_to_sql_table(db, npub, config.NEW_USER_BALANCE, False, False, nip05,
                             lud16, name, Timestamp.now().as_secs(), 0)
            user = get_from_sql_table(db, npub)
            return user
        except Exception as e:
            print("Error Adding User to DB: " + str(e))
    elif update:
        try:
            name, nip05, lud16 = await fetch_user_metadata(npub, client)
            print("Updating User: " + npub + " (" + npub + ")")
            update_user_fields(db, user.npub, nip05=nip05, lud16=lud16, name=name,
                               lastactive=Timestamp.now().as_secs())
            user = get_from_sql_table(db, npub)
            return user
        except Exception as e:
            print("Error Updating User in DB: " + str(e))

    return user


async def init_db(database, wipe=False, limit=1000, print_filesize=True):
    ensure_sdk_callback_loop()
    print(f"Opening discovery database: {os.path.abspath(database)}")
    # LMDB can't grow smaller, so by using this function we can wipe the database on init to avoid
    # it growing too big. If wipe is set to true, the database will be deleted once the size is above the limit param.
    database_content = database + "/data.mdb"
    if  os.path.isfile(database_content):
        file_stats = os.stat(database_content)
        sizeinmb = file_stats.st_size / (1024 * 1024)
        if print_filesize:
            print("Filesize of database \"" + database + "\": " + str(sizeinmb) + " Mb.")

        if wipe and sizeinmb > limit:
            try:
                shutil.rmtree(database)
                print("Removed database due to large file size. Waiting for resync")
            except OSError as e:
                print("Error: %s - %s." % (e.filename, e.strerror))
    else:
        print("Creating database: " + database)


    return await NostrLmdb.open(database)



async def fetch_user_metadata(npub, client):
    name = ""
    nip05 = ""
    lud16 = ""
    pk = PublicKey.parse(npub)
    print(f"\nGetting profile metadata for {pk.to_bech32()}...")
    profile_filter = Filter().kind(Kind(0)).author(pk).limit(1)
    events = await client.fetch_events(ReqTarget.auto([profile_filter]), relay_timeout)
    events_vec = events
    if len(events_vec) > 0:
        latest_entry = events_vec[0]
        latest_time = 0
        try:
            for entry in events_vec:
                if entry.created_at().as_secs() > latest_time:
                    latest_time = entry.created_at().as_secs()
                    latest_entry = entry
            profile = json.loads(latest_entry.content())
            if profile.get("name"):
                name = profile['name']
            if profile.get("nip05"):
                nip05 = profile['nip05']
            if profile.get("lud16"):
                lud16 = profile['lud16']
        except Exception as e:
            print(e)
    return name, nip05, lud16
