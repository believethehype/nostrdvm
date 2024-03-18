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
    begin: int
    end: int
    tier_dtag: str
    zaps: str
    recipe: str
    active: bool


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
                                            begin int,
                                            end int,
                                            tier_dtag text,
                                            zaps text,
                                            recipe text,
                                            active boolean
                                            
                                          
                                        ); """)
        cur.execute("SELECT name FROM sqlite_master")
        con.close()

    except Error as e:
        print(e)


def add_to_subscription_sql_table(db, id, recipient, subscriber, nwc, cadence, amount, begin, end, tier_dtag, zaps,
                                  recipe, active):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        data = (id, recipient, subscriber, nwc, cadence, amount, begin, end, tier_dtag, zaps, recipe, active)
        print(id)
        print(recipient)
        print(subscriber)
        print(nwc)
        cur.execute("INSERT or IGNORE INTO subscriptions VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data)
        con.commit()
        con.close()
    except Error as e:
        print("Error when Adding to DB: " + str(e))


def get_from_subscription__sql_table(db, id):
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
            subscription.begin = row[6]
            subscription.end = row[7]
            subscription.tier_dtag = row[8]
            subscription.zaps = row[9]
            subscription.recipe = row[10]
            subscription.active = row[11]

            return subscription

    except Error as e:
        print("Error Getting from DB: " + str(e))
        return None


def update_subscription_sql_table(db, id, recipient, subscriber, nwc, cadence, amount, begin, end, tier_dtag, zaps,
                                  recipe, active):
    try:
        con = sqlite3.connect(db)
        cur = con.cursor()
        data = (recipient, subscriber, nwc, cadence, amount, begin, end, tier_dtag, zaps, recipe, active, id)

        cur.execute(""" UPDATE subscriptions
                  SET recipient = ? ,
                      subscriber = ? ,
                      nwc = ? ,
                      cadence = ? ,
                      amount = ? ,
                      begin = ? ,
                      end = ?,
                      tier_dtag = ?,
                      zaps = ?,
                      recipe = ?,
                      active = ?

                  WHERE id = ?""", data)
        con.commit()
        con.close()
    except Error as e:
        print("Error Updating DB: " + str(e))




