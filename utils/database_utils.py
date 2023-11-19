# DATABASE LOGIC
import os
import sqlite3
import time

from _sqlite3 import Error
from datetime import timedelta
from logging import Filter

from nostr_sdk import Timestamp, Keys, PublicKey, EventBuilder, Metadata, Filter

from utils import env
from utils.definitions import NEW_USER_BALANCE
from utils.nostr_utils import send_event

def create_sql_table():
    try:
        con = sqlite3.connect(os.getenv(env.USER_DB_PATH))
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


def add_sql_table_column():
    try:
        con = sqlite3.connect(os.getenv(env.USER_DB_PATH))
        cur = con.cursor()
        cur.execute(""" ALTER TABLE users ADD COLUMN lastactive 'integer' """)
        con.close()
    except Error as e:
        print(e)


def add_to_sql_table(npub, sats, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive):
    try:
        con = sqlite3.connect(os.getenv(env.USER_DB_PATH))
        cur = con.cursor()
        data = (npub, sats, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive)
        cur.execute("INSERT or IGNORE INTO users VALUES(?, ?, ?, ?, ?, ?, ?, ?)", data)
        con.commit()
        con.close()
    except Error as e:
        print(e)


def update_sql_table(npub, sats, iswhitelisted, isblacklisted, nip05, lud16, name, lastactive):
    try:
        con = sqlite3.connect(os.getenv(env.USER_DB_PATH))
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


def get_from_sql_table(npub):
    try:
        con = sqlite3.connect(os.getenv(env.USER_DB_PATH))
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE npub=?", (npub,))
        row = cur.fetchone()
        con.close()
        return row

    except Error as e:
        print(e)


def delete_from_sql_table(npub):
    try:
        con = sqlite3.connect(os.getenv(env.USER_DB_PATH))
        cur = con.cursor()
        cur.execute("DELETE FROM users WHERE npub=?", (npub,))
        con.commit()
        con.close()
    except Error as e:
        print(e)


def clean_db():
    try:
        con = sqlite3.connect(os.getenv(env.USER_DB_PATH))
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE npub IS NULL OR npub = '' ")
        rows = cur.fetchall()
        for row in rows:
            print(row)
            delete_from_sql_table(row[0])
        con.close()
        return rows
    except Error as e:
        print(e)


def list_db():
    try:
        con = sqlite3.connect(os.getenv(env.USER_DB_PATH))
        cur = con.cursor()
        cur.execute("SELECT * FROM users ORDER BY sats DESC")
        rows = cur.fetchall()
        for row in rows:
            print(row)
        con.close()
    except Error as e:
        print(e)


def update_user_balance(sender, sats, config=None):
    user = get_from_sql_table(sender)
    if user is None:
        add_to_sql_table(sender, (int(sats) + NEW_USER_BALANCE), False, False,
                         "", "", "", Timestamp.now().as_secs())
        print("NEW USER: " + sender + " Zap amount: " + str(sats) + " Sats.")
    else:
        user = get_from_sql_table(sender)
        print(str(sats))
        nip05 =user[4]
        lud16 = user[5]
        name =  user[6]

        if nip05 is None:
            nip05 = ""
        if lud16 is None:
            lud16 = ""
        if name is None:
            name = ""

        new_balance = int(user[1]) + int(sats)
        update_sql_table(sender, new_balance, user[2], user[3], nip05, lud16, name,
                         Timestamp.now().as_secs())
        print("UPDATE USER BALANCE: " + str(name) + " Zap amount: " + str(sats) + " Sats.")


        if config is not None:
            keys = Keys.from_sk_str(config.PRIVATE_KEY)
            time.sleep(1.0)

            message = ("Added "+ str(sats) + " Sats to balance. New balance is " + str(new_balance) + " Sats. " )


            evt = EventBuilder.new_encrypted_direct_msg(keys, PublicKey.from_hex(sender), message,
                                                        None).to_event(keys)
            send_event(evt, key=keys)


def get_or_add_user(sender):
    user = get_from_sql_table(sender)

    if user is None:
        add_to_sql_table(sender, NEW_USER_BALANCE, False, False, None,
                         None, None, Timestamp.now().as_secs())
        user = get_from_sql_table(sender)
        print(user)

    return user

def update_user_metadata(sender, client):
    user = get_from_sql_table(sender)
    name = user[6]
    lud16 = user[5]
    nip05 = user[4]
    try:
        profile_filter = Filter().kind(0).author(sender).limit(1)
        events = client.get_events_of([profile_filter], timedelta(seconds=3))
        if len(events) > 0:
            ev = events[0]
            metadata = Metadata.from_json(ev.content())
            name = metadata.get_display_name()
            if str(name) == "" or name is None:
                name = metadata.get_name()
                nip05 = metadata.get_nip05()
                lud16 = metadata.get_lud16()
    except:
        print("Couldn't get meta information")
    update_sql_table(user[0], user[1], user[2], user[3], nip05, lud16,
                     name, Timestamp.now().as_secs())
    user = get_from_sql_table(user[0])
    return user
