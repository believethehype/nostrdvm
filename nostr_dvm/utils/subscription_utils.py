import sqlite3
from dataclasses import dataclass
from sqlite3 import Error


@dataclass
class Subscription:
    id: str
    recipent: str
    subscriber: str
    nwc: str
    cadence: str
    amount: int
    unit: str
    begin: int
    end: int
    tier_dtag: str
    zaps: str
    recipe: str
    active: bool
    lastupdate: int
    tier: str


def create_subscription_sql_table(db):
    try:
        import os
        if not os.path.exists(r'db'):
            os.makedirs(r'db')
        if not os.path.exists(r'outputs'):
            os.makedirs(r'outputs')
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute(""" CREATE TABLE IF NOT EXISTS subscriptions (
                                            id text PRIMARY KEY,
                                            recipient text,
                                            subscriber  text,
                                            nwc text NOT NULL,
                                            cadence text,
                                            amount int,
                                            unit text,
                                            begin int,
                                            end int,
                                            tier_dtag text,
                                            zaps text,
                                            recipe text,
                                            active boolean,
                                            lastupdate int,
                                            tier text
                                            
                                          
                                        ); """)
        cur.execute("SELECT name FROM sqlite_master")
        con.close()

    except Error as e:
        print(e)


def add_to_subscription_sql_table(db, id, recipient, subscriber, nwc, cadence, amount, unit, begin, end, tier_dtag, zaps,
                                  recipe, active, lastupdate, tier):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        data = (id, recipient, subscriber, nwc, cadence, amount, unit, begin, end, tier_dtag, zaps, recipe, active, lastupdate, tier)
        print(id)
        print(recipient)
        print(subscriber)
        print(nwc)
        cur.execute("INSERT or IGNORE INTO subscriptions VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data)
        con.commit()
        con.close()
    except Error as e:
        print("Error when Adding to DB: " + str(e))


def get_from_subscription_sql_table(db, id):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("SELECT * FROM subscriptions WHERE id=?", (id,))
        row = cur.fetchone()
        con.close()
        if row is None:
            return None
        else:
            subscription = Subscription
            subscription.id = row[0]
            subscription.recipent = row[1]
            subscription.subscriber = row[2]
            subscription.nwc = row[3]
            subscription.cadence = row[4]
            subscription.amount = row[5]
            subscription.unit = row[6]
            subscription.begin = row[7]
            subscription.end = row[8]
            subscription.tier_dtag = row[9]
            subscription.zaps = row[10]
            subscription.recipe = row[11]
            subscription.active = row[12]
            subscription.lastupdate = row[13]
            subscription.tier = row[14]

            return subscription

    except Error as e:
        print("Error Getting from DB: " + str(e))
        return None


def get_all_subscriptions_from_sql_table(db):
    try:
        con = sqlite3.connect(db)
        cursor = con.cursor()

        sqlite_select_query = """SELECT * from subscriptions"""
        cursor.execute(sqlite_select_query)
        records = cursor.fetchall()
        subscriptions = []
        for row in records:
            subscriptions.append(Subscription(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14]))
        cursor.close()
        return subscriptions

    except sqlite3.Error as error:
        print("Failed to read data from sqlite table", error)
    finally:
        if con:
            con.close()
            #print("The SQLite connection is closed")

def delete_from_subscription_sql_table(db, id):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("DELETE FROM subscriptions WHERE id=?", (id,))
        con.commit()
        con.close()
    except Error as e:
        print(e)

def update_subscription_sql_table(db, id, recipient, subscriber, nwc, cadence, amount, unit, begin, end, tier_dtag, zaps,
                                  recipe, active, lastupdate, tier):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        data = (recipient, subscriber, nwc, cadence, amount, unit, begin, end, tier_dtag, zaps, recipe, active, lastupdate, tier, id)

        cur.execute(""" UPDATE subscriptions
                  SET recipient = ? ,
                      subscriber = ? ,
                      nwc = ? ,
                      cadence = ? ,
                      amount = ? ,
                      unit = ? ,
                      begin = ? ,
                      end = ?,
                      tier_dtag = ?,
                      zaps = ?,
                      recipe = ?,
                      active = ?,
                      lastupdate = ?,
                      tier = ?

                  WHERE id = ?""", data)
        con.commit()
        con.close()
    except Error as e:
        print("Error Updating DB: " + str(e))




