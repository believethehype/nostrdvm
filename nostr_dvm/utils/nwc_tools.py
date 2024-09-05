import json
import os
from datetime import timedelta

import requests
from nostr_sdk import Keys, PublicKey, Client, nip04_encrypt, EventBuilder, Tag, NostrSigner, Filter, Timestamp, \
    NostrWalletConnectUri, Nwc

from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nostr_utils import check_and_set_private_key
from nostr_dvm.utils.zap_utils import zaprequest


async def nwc_zap(connectionstr, bolt11, keys, externalrelay=None):
    uri = NostrWalletConnectUri.parse(connectionstr)

    # Initialize NWC client
    nwc = Nwc(uri)

    info = await nwc.get_info()
    print(info)

    balance = await nwc.get_balance()
    print(f"Balance: {balance} MilliSats")

    event_id = await nwc.pay_invoice(bolt11)
    print("NWC event: " + event_id)
    return event_id


def parse_connection_str(connectionstring):
    split = connectionstring.split("?")
    targetpubkey = split[0].split(":")[1].replace("//", "")
    split2 = split[1].split("&")
    relay = split2[0].split("=")[1]
    relay = relay.replace("%3A%2F%2F", "://")
    secret = split2[1].split("=")[1]
    return targetpubkey, relay, secret


def make_nwc_account(identifier, nwcdomain):
    pubkey = Keys.parse(os.getenv("DVM_PRIVATE_KEY_" + identifier.upper())).public_key().to_hex()
    data = {
        'name': identifier,
        'host': os.getenv("LNBITS_HOST"),
        'key': os.getenv("LNBITS_ADMIN_KEY_" + identifier.upper()),
        'pubkey': pubkey,
    }

    try:
        url = nwcdomain
        header = {"content-type": "application/json"}
        res = requests.post(url, headers=header, json=data)
        obj = json.loads(res.text)
        if obj['params']['connectionURI'] != "Users already exists":
            return obj['params']['connectionURI']
        else:
            return ""

    except Exception as e:
        print(e)
        return ""


async def nwc_test(nwc_server):
    connectionstring = make_nwc_account("test", nwc_server + "/api/new")
    print(connectionstring)
    #  TODO Store the connection string in a db, use here if you already have one
    # connectionstring = "nostr+walletconnect:..."
    if connectionstring != "":
        # we use the keys from a test user
        keys = Keys.parse(check_and_set_private_key("test"))

        # we zap npub1nxa4tywfz9nqp7z9zp7nr7d4nchhclsf58lcqt5y782rmf2hefjquaa6q8's profile 21 sats and say Cool stuff
        pubkey = PublicKey.from_bech32("npub1nxa4tywfz9nqp7z9zp7nr7d4nchhclsf58lcqt5y782rmf2hefjquaa6q8")
        bolt11 = zaprequest("hype@bitcoinfixesthis.org", 21, "Cool Stuff", None,
                            pubkey, keys, DVMConfig.RELAY_LIST)

        await nwc_zap(connectionstring, bolt11, keys)
