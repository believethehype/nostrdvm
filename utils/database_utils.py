# DATABASE LOGIC
import json
import sqlite3
import time

from _sqlite3 import Error
from dataclasses import dataclass
from datetime import timedelta
from logging import Filter

from nostr_sdk import Timestamp, Keys, PublicKey, EventBuilder, Filter
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
        print("Error when Adding to DB: " + str(e))


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


def update_user_balance(db, npub, additional_sats, client, config):
    user = get_from_sql_table(db, npub)
    if user is None:
        name, nip05, lud16 = fetch_user_metadata(npub, client)
        add_to_sql_table(db, npub, (int(additional_sats) + config.NEW_USER_BALANCE), False, False,
                         nip05, lud16, name, Timestamp.now().as_secs())
        print("Adding User: " + npub + " (" + npub + ")")
    else:
        user = get_from_sql_table(db, npub)
        new_balance = int(user.balance) + int(additional_sats)
        update_sql_table(db, npub, new_balance, user.iswhitelisted, user.isblacklisted, user.nip05, user.lud16,
                         user.name,
                         Timestamp.now().as_secs())
        print("Updated user balance for: " + str(user.name) +
              " Zap amount: " + str(additional_sats) + " Sats. New balance: " + str(new_balance) +" Sats")

        if config is not None:
            keys = Keys.from_sk_str(config.PRIVATE_KEY)
            time.sleep(1.0)

            message = ("Added " + str(additional_sats) + " Sats to balance. New balance is " + str(new_balance) + " Sats.")

            evt = EventBuilder.new_encrypted_direct_msg(keys, PublicKey.from_hex(npub), message,
                                                        None).to_event(keys)
            send_event(evt, client=client, dvm_config=config)


def get_or_add_user(db, npub, client, config):
    user = get_from_sql_table(db, npub)
    if user is None:
        try:
            name, nip05, lud16 = fetch_user_metadata(npub, client)
            print("Adding User: " + npub + " (" + npub + ")")
            add_to_sql_table(db, npub, config.NEW_USER_BALANCE, False, False, nip05,
                             lud16, name, Timestamp.now().as_secs())
            user = get_from_sql_table(db, npub)
            return user
        except Exception as e:
            print("Error Adding User to DB: " + str(e))

    return user

def fetch_user_metadata(npub, client):
    name = ""
    nip05 = ""
    lud16 = ""
    pk = PublicKey.from_hex(npub)
    print(f"\nGetting profile metadata for {pk.to_bech32()}...")
    profile_filter = Filter().kind(0).author(pk).limit(1)
    events = client.get_events_of([profile_filter], timedelta(seconds=5))
    if len(events) > 0:
        latest_entry = events[0]
        latest_time = 0
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
    return name, nip05, lud16
