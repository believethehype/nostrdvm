# DATABASE LOGIC
import json
import sqlite3

from sqlite3 import Error
from dataclasses import dataclass
from datetime import timedelta
from logging import Filter

from nostr_sdk import Timestamp, Keys, PublicKey, EventBuilder, Filter, Kind

from nostr_dvm.utils.definitions import relay_timeout
from nostr_dvm.utils.nostr_utils import send_event


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

            user = User
            user.npub = row[0]
            user.balance = row[1]
            user.iswhitelisted = row[2]
            user.isblacklisted = row[3]
            user.nip05 = row[4]
            user.lud16 = row[5]
            user.name = row[6]
            user.lastactive = row[7]
            user.subscribed = row[8]
            if user.subscribed is None:
                user.subscribed = 0

            return user

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


async def update_user_balance(db, npub, additional_sats, client, config, giftwrap=False):
    user = get_from_sql_table(db, npub)
    if user is None:
        name, nip05, lud16 = fetch_user_metadata(npub, client)
        add_to_sql_table(db, npub, (int(additional_sats) + config.NEW_USER_BALANCE), False, False,
                         nip05, lud16, name, Timestamp.now().as_secs(), 0)
        print("Adding User: " + npub + " (" + npub + ")")
    else:
        user = get_from_sql_table(db, npub)
        new_balance = int(user.balance) + int(additional_sats)
        update_sql_table(db, npub, new_balance, user.iswhitelisted, user.isblacklisted, user.nip05, user.lud16,
                         user.name,
                         Timestamp.now().as_secs(), user.subscribed)
        print("Updated user balance for: " + str(user.name) +
              " Zap amount: " + str(additional_sats) + " Sats. New balance: " + str(new_balance) + " Sats")

        if config is not None:
            keys = Keys.parse(config.PRIVATE_KEY)
            # time.sleep(1.0)

            message = ("Added " + str(additional_sats) + " Sats to balance. New balance is " + str(
                new_balance) + " Sats.")

            if giftwrap:
                await client.send_private_msg(PublicKey.parse(npub), message, None)
            else:
                evt = EventBuilder.encrypted_direct_msg(keys, PublicKey.parse(npub), message,
                                                        None).to_event(keys)
                await send_event(evt, client=client, dvm_config=config)


def update_user_subscription(npub, subscribed_until, client, dvm_config):
    user = get_from_sql_table(dvm_config.DB, npub)
    if user is None:
        name, nip05, lud16 = fetch_user_metadata(npub, client)
        add_to_sql_table(dvm_config.DB, npub, dvm_config.NEW_USER_BALANCE, False, False,
                         nip05, lud16, name, Timestamp.now().as_secs(), 0)
        print("Adding User: " + npub + " (" + npub + ")")
    else:
        user = get_from_sql_table(dvm_config.DB, npub)

        update_sql_table(dvm_config.DB, npub, user.balance, user.iswhitelisted, user.isblacklisted, user.nip05,
                         user.lud16,
                         user.name,
                         Timestamp.now().as_secs(), subscribed_until)
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
            update_sql_table(db, user.npub, user.balance, user.iswhitelisted, user.isblacklisted, nip05,
                             lud16, name, Timestamp.now().as_secs(), user.subscribed)
            user = get_from_sql_table(db, npub)
            return user
        except Exception as e:
            print("Error Updating User in DB: " + str(e))

    return user


async def fetch_user_metadata(npub, client):
    name = ""
    nip05 = ""
    lud16 = ""
    pk = PublicKey.parse(npub)
    print(f"\nGetting profile metadata for {pk.to_bech32()}...")
    profile_filter = Filter().kind(Kind(0)).author(pk).limit(1)
    events = await client.get_events_of([profile_filter], relay_timeout)
    if len(events) > 0:
        latest_entry = events[0]
        latest_time = 0
        try:
            for entry in events:
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
