# DATABASE LOGIC
import sqlite3
import time

from _sqlite3 import Error
from dataclasses import dataclass
from datetime import timedelta
from logging import Filter

from nostr_sdk import Timestamp, Keys, PublicKey, EventBuilder, Metadata, Filter

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


def update_sql_table(db, npub, sats, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        data = (sats, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive, npub)

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
            user = None
            return user
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


def get_or_add_user(db, sender):
    user = get_from_sql_table(db, sender)
    if user is None:
        print("Adding User")
        add_to_sql_table(db, sender, NEW_USER_BALANCE, False, False, None,
                         None, None, Timestamp.now().as_secs())
        user = get_from_sql_table(db, sender)
        print(user)

    return user


def update_user_metadata(db, sender, client):
    user = get_from_sql_table(db, sender)
    try:
        profile_filter = Filter().kind(0).author(sender).limit(1)
        events = client.get_events_of([profile_filter], timedelta(seconds=3))
        if len(events) > 0:
            ev = events[0]
            metadata = Metadata.from_json(ev.content())
            name = metadata.get_display_name()
            if str(name) == "" or name is None:
                user.name = metadata.get_name()
                user.nip05 = metadata.get_nip05()
                user.lud16 = metadata.get_lud16()
    except:
        print("Couldn't get meta information")
    update_sql_table(db, user.npub, user.balance, user.iswhitelisted, user.isblacklisted, user.nip05, user.lud16,
                     user.name, Timestamp.now().as_secs())
    user = get_from_sql_table(db, user.npub)
    return user
