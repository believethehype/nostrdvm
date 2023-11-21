# ADMINISTRARIVE DB MANAGEMENT
import time

from nostr_sdk import Keys, EventBuilder, PublicKey

from utils.database_utils import get_from_sql_table, list_db, delete_from_sql_table, update_sql_table, \
    get_or_add_user, clean_db
from utils.nip89_utils import nip89_announce_tasks
from utils.nostr_utils import send_event

class AdminConfig:
    REBROADCASTNIP89: bool = False

def admin_make_database_updates(config=None, client=None):
    # This is called on start of Server, Admin function to manually whitelist/blacklist/add balance/delete users
    dvmconfig = config
    db = config.DB

    rebroadcast_nip89 = False
    cleandb = False
    listdatabase = False
    deleteuser = False
    whitelistuser = False
    unwhitelistuser = False
    blacklistuser = False


    # publickey = PublicKey.from_bech32("npub1...").to_hex()
    # use this if you have the npub
    publickey = "asd123"
    #use this if you have hex

    if whitelistuser:
        user = get_or_add_user(db, publickey)
        update_sql_table(db, user.npub, user.balance, True, False, user.nip05, user.lud16, user.name, user.lastactive)
        user = get_from_sql_table(db, publickey)
        print(str(user.name) + " is whitelisted: " + str(user.iswhitelisted))

    if unwhitelistuser:
        user = get_from_sql_table(db, publickey)
        update_sql_table(db, user.npub, user.balance, False, False, user.nip05, user.lud16, user.name, user.lastactive)

    if blacklistuser:
        user = get_from_sql_table(db, publickey)
        update_sql_table(db, user.npub, user.balance, False, True, user.nip05, user.lud16, user.name, user.lastactive)

    if deleteuser:
        delete_from_sql_table(db, publickey)

    if cleandb:
        clean_db(db)

    if listdatabase:
        list_db(db)

    if rebroadcast_nip89:
        nip89_announce_tasks(dvmconfig)
