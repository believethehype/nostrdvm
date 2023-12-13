# ADMINISTRARIVE DB MANAGEMENT

from nostr_sdk import Keys, PublicKey, Client

from nostr_dvm.utils.database_utils import get_from_sql_table, list_db, delete_from_sql_table, update_sql_table, \
    get_or_add_user, clean_db
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nip89_utils import nip89_announce_tasks, fetch_nip89_paramters_for_deletion
from nostr_dvm.utils.nostr_utils import update_profile


class AdminConfig:
    REBROADCAST_NIP89: bool = False
    UPDATE_PROFILE: bool = False
    DELETE_NIP89: bool = False
    WHITELISTUSER: bool = False
    UNWHITELISTUSER: bool = False
    BLACKLISTUSER: bool = False
    DELETEUSER: bool = False
    LISTDATABASE: bool = False
    ClEANDB: bool = False

    USERNPUB: str = ""
    LUD16: str = ""

    EVENTID: str = ""
    PRIVKEY: str = ""


def admin_make_database_updates(adminconfig: AdminConfig = None, dvmconfig: DVMConfig = None, client: Client = None):
    # This is called on start of Server, Admin function to manually whitelist/blacklist/add balance/delete users
    if adminconfig is None or dvmconfig is None:
        return

    if not isinstance(adminconfig, AdminConfig):
        return

    if ((
            adminconfig.WHITELISTUSER is True or adminconfig.UNWHITELISTUSER is True or adminconfig.BLACKLISTUSER is True or adminconfig.DELETEUSER is True)
            and adminconfig.USERNPUB == ""):
        return

    if adminconfig.UPDATE_PROFILE and (dvmconfig.NIP89 is None):
        return

    if adminconfig.DELETE_NIP89 and (adminconfig.EVENTID == "" or adminconfig.EVENTID == ""):
        return

    db = dvmconfig.DB

    if str(adminconfig.USERNPUB).startswith("npub"):
        publickey = PublicKey.from_bech32(adminconfig.USERNPUB).to_hex()
    else:
        publickey = adminconfig.USERNPUB

    if adminconfig.WHITELISTUSER:
        user = get_or_add_user(db, publickey, client=client, config=dvmconfig)
        update_sql_table(db, user.npub, user.balance, True, False, user.nip05, user.lud16, user.name, user.lastactive)
        user = get_from_sql_table(db, publickey)
        print(str(user.name) + " is whitelisted: " + str(user.iswhitelisted))

    if adminconfig.UNWHITELISTUSER:
        user = get_from_sql_table(db, publickey)
        update_sql_table(db, user.npub, user.balance, False, False, user.nip05, user.lud16, user.name, user.lastactive)

    if adminconfig.BLACKLISTUSER:
        user = get_from_sql_table(db, publickey)
        update_sql_table(db, user.npub, user.balance, False, True, user.nip05, user.lud16, user.name, user.lastactive)

    if adminconfig.DELETEUSER:
        delete_from_sql_table(db, publickey)

    if adminconfig.ClEANDB:
        clean_db(db)

    if adminconfig.LISTDATABASE:
        list_db(db)

    if adminconfig.REBROADCAST_NIP89:
        nip89_announce_tasks(dvmconfig, client=client)

    if adminconfig.DELETE_NIP89:
        event_id = adminconfig.EVENTID
        keys = Keys.from_sk_str(
            adminconfig.PRIVKEY)  # Private key from sender of Event (e.g. the key of an nip89 announcement you want to delete)
        fetch_nip89_paramters_for_deletion(keys, event_id, client, dvmconfig)

    if adminconfig.UPDATE_PROFILE:
        update_profile(dvmconfig, client, lud16=adminconfig.LUD16)
