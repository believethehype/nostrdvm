# ADMINISTRARIVE DB MANAGEMENT
import time

from nostr_sdk import Keys, EventBuilder, PublicKey

from utils.database_utils import get_from_sql_table, list_db, delete_from_sql_table, update_sql_table, \
    get_or_add_user, clean_db
from utils.nip89_utils import nip89_announce_tasks
from utils.nostr_utils import send_event


def admin_make_database_updates(config=None, client=None):
    # This is called on start of Server, Admin function to manually whitelist/blacklist/add balance/delete users
    dvmconfig = config

    rebroadcast_nip89 = False
    cleandb = False
    listdatabase = False
    deleteuser = False
    whitelistuser = False
    unwhitelistuser = False
    blacklistuser = False
    addbalance = False
    additional_balance = 50

    # publickey = PublicKey.from_bech32("npub1...").to_hex()
    # use this if you have the npub
    publickey = "asd123"
    #use this if you have hex

    if whitelistuser:
        user = get_or_add_user(publickey)
        update_sql_table(user.npub, user.balance, True, False, user.nip05, user.lud16, user.name, user.lastactive)
        user = get_from_sql_table(publickey)
        print(str(user.name) + " is whitelisted: " + str(user.iswhitelisted))

    if unwhitelistuser:
        user = get_from_sql_table(publickey)
        update_sql_table(user.npub, user.balance, False, False, user.nip05, user.lud16, user.name, user.lastactive)

    if blacklistuser:
        user = get_from_sql_table(publickey)
        update_sql_table(user.npub, user.balance, False, True, user.nip05, user.lud16, user.name, user.lastactive)

    if addbalance:
        user = get_from_sql_table(publickey)
        update_sql_table(user[0], (int(user.balance) + additional_balance), user.iswhitelisted, user.isblacklisted, user.nip05, user.lud16, user.name, user.lastactive)
        time.sleep(1.0)
        message = str(additional_balance) + " Sats have been added to your balance. Your new balance is " + str(
            (int(user.balance) + additional_balance)) + " Sats."
        keys = Keys.from_sk_str(config.PRIVATE_KEY)
        evt = EventBuilder.new_encrypted_direct_msg(keys, PublicKey.from_hex(publickey), message,
                                                    None).to_event(keys)
        send_event(evt, key=keys)

    if deleteuser:
        delete_from_sql_table(publickey)

    if cleandb:
        clean_db()

    if listdatabase:
        list_db()

    if rebroadcast_nip89:
        nip89_announce_tasks(dvmconfig)
