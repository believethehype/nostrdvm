# DATABASE LOGIC
import json
import sqlite3
import time

from _sqlite3 import Error
from dataclasses import dataclass
from datetime import timedelta
from logging import Filter

from nostr_sdk import Timestamp, Keys, PublicKey, EventBuilder, Metadata, Filter, Options, Client

from utils.definitions import NEW_USER_BALANCE
from utils.nostr_utils import send_event


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


def create_sql_table(db):
    try:
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
                                            lastactive integer
                                        ); """)
        cur.execute("SELECT name FROM sqlite_master")
        con.close()

    except Error as e:
        print(e)


def add_sql_table_column(db):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute(""" ALTER TABLE users ADD COLUMN lastactive 'integer' """)
        con.close()
    except Error as e:
        print(e)


def add_to_sql_table(db, npub, sats, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        data = (npub, sats, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive)
        cur.execute("INSERT or IGNORE INTO users VALUES(?, ?, ?, ?, ?, ?, ?, ?)", data)
        con.commit()
        con.close()
    except Error as e:
        print(e)


def update_sql_table(db, npub, balance, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        data = (balance, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive, npub)

        cur.execute(""" UPDATE users
                  SET sats = ? ,
                      iswhitelisted = ? ,
                      isblacklisted = ? ,
                      nip05 = ? ,
                      lud16 = ? ,
                      name = ? ,
                      lastactive = ?
                  WHERE npub = ?""", data)
        con.commit()
        con.close()
    except Error as e:
        print(e)


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
            user = User
            user.npub = row[0]
            user.balance = row[1]
            user.iswhitelisted = row[2]
            user.isblacklisted = row[3]
            user.nip05 = row[4]
            user.lud16 = row[5]
            user.name = row[6]
            user.lastactive = row[7]

            return user

    except Error as e:
        print(e)


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


def update_user_balance(db, sender, sats, client, config):
    user = get_from_sql_table(db, sender)
    if user is None:
        add_to_sql_table(db, sender, (int(sats) + NEW_USER_BALANCE), False, False,
                         "", "", "", Timestamp.now().as_secs())
        print("NEW USER: " + sender + " Zap amount: " + str(sats) + " Sats.")
    else:
        user = get_from_sql_table(db, sender)
        print(str(sats))

        if user.nip05 is None:
            user.nip05 = ""
        if user.lud16 is None:
            user.lud16 = ""
        if user.name is None:
            user.name = ""

        new_balance = int(user.balance) + int(sats)
        update_sql_table(db, sender, new_balance, user.iswhitelisted, user.isblacklisted, user.nip05, user.lud16,
                         user.name,
                         Timestamp.now().as_secs())
        print("UPDATE USER BALANCE: " + str(user.name) + " Zap amount: " + str(sats) + " Sats.")

        if config is not None:
            keys = Keys.from_sk_str(config.PRIVATE_KEY)
            time.sleep(1.0)

            message = ("Added " + str(sats) + " Sats to balance. New balance is " + str(new_balance) + " Sats. ")

            evt = EventBuilder.new_encrypted_direct_msg(keys, PublicKey.from_hex(sender), message,
                                                        None).to_event(keys)
            send_event(evt, client=client, dvm_config=config)


def get_or_add_user(db, npub, client):
    user = get_from_sql_table(db, npub)
    if user is None:
        name, nip05, lud16 = fetch_user_metadata(npub, client)
        print("Adding User: " + npub + " (" + npub + ")")
        add_to_sql_table(db, npub, NEW_USER_BALANCE, False, False, nip05,
                         lud16, name, Timestamp.now().as_secs())
        user = get_from_sql_table(db, npub)
        return user

    return user


def fetch_user_metadata(npub, client):
    name = ""
    nip05 = ""
    lud16 = ""

    # Get metadata
    pk = PublicKey.from_hex(npub)
    print(f"\nGetting profile metadata for {pk.to_bech32()}...")
    filter = Filter().kind(0).author(pk).limit(1)
    events = client.get_events_of([filter], timedelta(seconds=3))
    if len(events) > 0:
        latest_entry = events[0]
        newest = 0
        for entry in events:
            if entry.created_at().as_secs() > newest:
                newest = entry.created_at().as_secs()
                latest_entry = entry

        print(latest_entry.content())
        profile = json.loads(latest_entry.content())
        if profile.get("name"):
            name = profile['name']
        if profile.get("nip05"):
            nip05 = profile['nip05']
        if profile.get("lud16"):
            lud16 = profile['lud16']

    return name, nip05, lud16


def fetch_user_metadata2(sender, client) -> (str, str, str):
    name = ""
    nip05 = ""
    lud16 = ""
    try:
        pk = PublicKey.from_hex(sender)
        print(f"\nGetting profile metadata for {pk.to_bech32()}...")
        profile_filter = Filter().kind(0).author(pk).limit(1)
        events = client.get_events_of([profile_filter], timedelta(seconds=1))
        if len(events) > 0:
            ev = events[0]
            metadata = Metadata.from_json(ev.content())
            name = metadata.get_display_name()
            if str(name) == "" or name is None:
                name = metadata.get_name()
            nip05 = metadata.get_nip05()
            lud16 = metadata.get_lud16()
        else:
            print("Profile not found")
            return name, nip05, lud16

    except:
        print("Couldn't get meta information")

    return name, nip05, lud16
