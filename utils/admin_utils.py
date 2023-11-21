# ADMINISTRARIVE DB MANAGEMENT
import time

from nostr_sdk import Keys, EventBuilder, PublicKey

from utils.database_utils import get_from_sql_table, list_db, delete_from_sql_table, update_sql_table, \
    get_or_add_user, clean_db
from utils.dvmconfig import DVMConfig
from utils.nip89_utils import nip89_announce_tasks
from utils.nostr_utils import send_event

class AdminConfig:
    REBROADCASTNIP89: bool = False
    WHITELISTUSER: bool = False
    UNWHITELISTUSER: bool = False
    BLACKLISTUSER: bool = False
    DELETEUSER: bool = False
    LISTDATABASE: bool = False
    ClEANDB: bool = False
    USERNPUB: str = ""

def admin_make_database_updates(adminconfig: AdminConfig = None, dvmconfig: DVMConfig = None, client=None):
    # This is called on start of Server, Admin function to manually whitelist/blacklist/add balance/delete users
    if adminconfig is None or dvmconfig is None:
        return

    if not isinstance(adminconfig, AdminConfig):
        return

    if ((adminconfig.WHITELISTUSER is True or adminconfig.UNWHITELISTUSER is True or adminconfig.BLACKLISTUSER is True or adminconfig.DELETEUSER is True)
            and adminconfig.USERNPUB == ""):
        return


    db = dvmconfig.DB

    rebroadcast_nip89 = adminconfig.REBROADCASTNIP89
    cleandb = adminconfig.ClEANDB
    listdatabase = adminconfig.LISTDATABASE
    deleteuser = adminconfig.DELETEUSER
    whitelistuser = adminconfig.WHITELISTUSER
    unwhitelistuser = adminconfig.UNWHITELISTUSER
    blacklistuser = adminconfig.BLACKLISTUSER

    if adminconfig.USERNPUB != "":
        if str(adminconfig.USERNPUB).startswith("npub"):
            publickey = PublicKey.from_bech32(adminconfig.USERNPUB).to_hex()
        else:
            publickey = adminconfig.USERNPUB


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
        nip89_announce_tasks(dvmconfig, client=client)
