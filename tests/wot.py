import asyncio
import json
from datetime import timedelta
import os
import csv
import networkx as nx

import pandas as pd

import warnings

from nostr_dvm.utils.definitions import relay_timeout

warnings.filterwarnings('ignore')

from nostr_sdk import  Options, Keys, NostrSigner, Filter, PublicKey, Kind, \
    SyncOptions, SyncDirection, ClientBuilder, NostrDatabase


# init_logger(LogLevel.INFO)
async def getmetadata(npub):
    name = ""
    nip05 = ""
    lud16 = ""
    try:
        pk = PublicKey.parse(npub)
    except:
        return "", "", ""
    keys = Keys.parse("nsec1zmzllu40a7mr7ztl78uwfwslnp0pn0pww868adl05x52d4la237s6m8qfj")
    client = ClientBuilder().signer(keys).build()
    await client.add_relay("wss://relay.damus.io")
    #await client.add_relay("wss://relay.primal.net")
    await client.add_relay("wss://purplepag.es")
    await client.connect()

    profile_filter = Filter().kind(Kind(0)).author(pk).limit(1)
    event_struct = await client.fetch_events([profile_filter], relay_timeout)
    events = event_struct.to_vec()
    if len(events) > 0:
        try:
            profile = json.loads(events[0].content())
            if profile.get("name"):
                name = profile['name']
            if profile.get("nip05"):
                nip05 = profile['nip05']
            if profile.get("lud16"):
                lud16 = profile['lud16']
        except Exception as e:
            print(e)
    await client.shutdown()
    return name, nip05, lud16


async def sync_db():
    keys = Keys.parse("nsec1zmzllu40a7mr7ztl78uwfwslnp0pn0pww868adl05x52d4la237s6m8qfj")
    database = NostrDatabase.lmdb("db/nostr_followlists.db")
    cli = ClientBuilder().signer(keys).database(database).build()

    await cli.add_relay("wss://relay.damus.io")  # TODO ADD MORE
    # await cli.add_relay("wss://relay.primal.net")  # TODO ADD MORE
    await cli.connect()

    filter1 = Filter().kind(Kind(3))

    # filter = Filter().author(keys.public_key())
    print("Syncing Profile Database.. this might take a while..")
    dbopts = SyncOptions().direction(SyncDirection.DOWN)
    await cli.sync(filter1, dbopts)
    print("Done Syncing Profile Database.")
    await cli.shutdown()


async def analyse_users(user_ids=None):
    if user_ids is None:
        user_ids = []
    try:
        user_keys = []
        for npub in user_ids:
            try:
                user_keys.append(PublicKey.parse(npub))
            except Exception as e:
                print(npub)
                print(e)

        database = NostrDatabase.lmdb("db/nostr_followlists.db")
        followers_filter = Filter().authors(user_keys).kind(Kind(3))
        followers = await database.query([followers_filter])
        allfriends = []
        if len(followers) > 0:
            for follower in followers:
                frens = []
                for tag in follower.tags().to_vec():
                    if tag.as_vec()[0] == "p":
                        frens.append(tag.as_vec()[1])
                allfriends.append(Friend(follower.author().to_hex(), frens))

            return allfriends
        else:
            print("no followers")
            return []
    except Exception as e:
        print(e)
        return []


class Friend(object):
    def __init__(self, user_id, friends):
        self.user_id = user_id
        self.friends = friends


def write_to_csv(friends, file="friends222.csv"):
    with open(file, 'a') as f:
        writer = csv.writer(f)
        friendcounter = 0
        for friend in friends:
            print(friendcounter)
            friendcounter += 1
            for fren in friend.friends:
                row = [friend.user_id, fren]
                writer.writerow(row)


def main(user_key, depth, update_db, create_csv, get_profile=False, remove_followings_from_set=False):
    file = "db/friends223.csv"
    # make sure key is in hex format

    if create_csv:
        # clear previous file
        try:
            print("Deleting existing file, creating new one")
            os.remove(file)
        except:
            print("Creating new file")
        # sync the database, this might take a while if it's empty or hasn't been updated in a long time
        if update_db:
            asyncio.run(sync_db())

        user_id = PublicKey.parse(user_key).to_hex()
        user_friends_level1 = asyncio.run(analyse_users([user_id]))
        friendlist = []
        for npub in user_friends_level1[0].friends:
            friendlist.append(npub)
        me = Friend(user_id, friendlist)

        write_to_csv([me], file)

        # for every npub we follow, we look at the npubs they follow (this might take a while)
        if depth >= 2:
            friendlist2 = []
            for friend in user_friends_level1:
                for npub in friend.friends:
                    friendlist2.append(npub)

            user_friends_level2 = asyncio.run(analyse_users(friendlist2))
            write_to_csv(user_friends_level2, file)
            if depth >= 3:
                friendlist3 = []
                for friend in user_friends_level2:
                    for npub in friend.friends:
                        friendlist3.append(npub)
                print(len(friendlist3))
                user_friends_level3 = asyncio.run(analyse_users(friendlist3))
                write_to_csv(user_friends_level3, file)

    df = pd.read_csv(file, sep=',')
    df.info()
    df.tail()

    G_fb = nx.read_edgelist(file, delimiter=",", create_using=nx.DiGraph(), nodetype=str)
    print(G_fb)
    pr = nx.pagerank(G_fb)
    # Use this to find people your followers follow
    if remove_followings_from_set:
        user_id = PublicKey.parse(user_key).to_hex()
        user_friends_level1 = asyncio.run(analyse_users([user_id]))
        friendlist = []
        for npub in user_friends_level1[0].friends:
            friendlist.append(npub)

        sorted_nodes = sorted([(node, pagerank) for node, pagerank in pr.items() if node not in friendlist],
                              key=lambda x: pr[x[0]],
                              reverse=True)[:50]
    else:
        sorted_nodes = sorted([(node, pagerank) for node, pagerank in pr.items()], key=lambda x: pr[x[0]],
                              reverse=True)[:50]

    for node in sorted_nodes:
        try:
            pk = PublicKey.parse(node[0]).to_bech32()
        except:
            pk = node[0]

        if get_profile:
            name, nip05, lud16 = asyncio.run(getmetadata(node[0]))
            print(name + " (" + pk + ") " + "," + str(node[1]))
        else:
            print(pk + "," + str(node[1]))


#user_id = "99bb5591c9116600f845107d31f9b59e2f7c7e09a1ff802e84f1d43da557ca64" #dbth
#user_id = "npub1gcxzte5zlkncx26j68ez60fzkvtkm9e0vrwdcvsjakxf9mu9qewqlfnj5z" #vitor
user_id = "npub1l2vyh47mk2p0qlsku7hg0vn29faehy9hy34ygaclpn66ukqp3afqutajft" #pablo
fetch_profiles = True
create_csv = True
remove_followings_from_set = True
depth = 2
update_db = False
main(user_id, depth, update_db, create_csv, fetch_profiles, remove_followings_from_set)
