from datetime import timedelta
from pathlib import Path

import dotenv
from nostr_sdk import PublicKey, Timestamp, Event, HandleNotification, Alphabet, Filter, SingleLetterTag, Kind


import asyncio
import argparse

from nostr_dvm.utils import dvmconfig
from nostr_dvm.utils.dvmconfig import DVMConfig
from nostr_dvm.utils.nut_wallet_utils import NutZapWallet
from nostr_dvm.utils.print_utils import bcolors


# Run with params for test functions or set the default here
parser = argparse.ArgumentParser(description='Nutzaps')
parser.add_argument("--mint", type=bool, default=False)
parser.add_argument("--zap", type=bool, default=True)
parser.add_argument("--melt", type=bool, default=False)
args = parser.parse_args()


async def test(relays, mints):

    nutzap_wallet = NutZapWallet()
    update_wallet_info = False  # leave this on false except when you manually changed relays/mints/keys
    client, keys = await nutzap_wallet.client_connect(relays)
    set_profile = False  # Attention, this overwrites your current profile if on True, do not set if you use an non-test account

    if set_profile:
        lud16 = "hype@bitcoinfixesthis.org" #overwrite with your ln address
        await nutzap_wallet.set_profile("Test", "I'm a nutsack test account", lud16, "https://i.nostr.build/V4FwExrV5aXHNm70.jpg", client, keys)

        # Test 1 Config: Mint Tokens
    mint_to_wallet = args.mint  # Test function to mint 5 sats on the mint in your list with given index below
    mint_index = 0  # Index of mint in mints list to mint a token
    mint_amount = 10  # Amount to mint

    # Test 2 Config: Send Nutzap
    send_test = args.zap  # Send a Nutzap
    send_zap_amount = 3
    send_zap_message = "From my nutsack"
    send_reveiver = "npub139nfkqamy53j7vce9lw6w7uwxm3a8zrwnd2m836tj5y3aytv37vqygz42j" #     keys.public_key().to_bech32()  # This is ourself, for testing purposes,  some other people to nutzap:  #npub1nxa4tywfz9nqp7z9zp7nr7d4nchhclsf58lcqt5y782rmf2hefjquaa6q8 # dbth  #npub1l2vyh47mk2p0qlsku7hg0vn29faehy9hy34ygaclpn66ukqp3afqutajft # pablof7z
    send_zapped_event = None  # None, or zap an event like this: Nip19Event.from_nostr_uri("nostr:nevent1qqsxq59mhz8s6aj9jzltcmqmmv3eutsfcpkeny2x755vdu5dtq44ldqpz3mhxw309ucnydewxqhrqt338g6rsd3e9upzp75cf0tahv5z7plpdeaws7ex52nmnwgtwfr2g3m37r844evqrr6jqvzqqqqqqyqtxyr6").event_id().to_hex()

    # Test 3 Config: Melt to ln address
    melt = args.melt
    melt_amount = 6


    print("PrivateKey: " + keys.secret_key().to_bech32() + " PublicKey: " + keys.public_key().to_bech32())
    # See if we already have a wallet and fetch it
    nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)

    # If we have a wallet but want to maually update the info..
    if nut_wallet is not None and update_wallet_info:
        await nutzap_wallet.update_nut_wallet(nut_wallet, mints, client, keys)
        await nutzap_wallet.announce_nutzap_info_event(nut_wallet, client, keys)

    # If we don't have a wallet, we create one, fetch it and announce our info
    if nut_wallet is None:
        await nutzap_wallet.create_new_nut_wallet(mints, relays, client, keys, "Test", "My Nutsack")
        nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)
        if nut_wallet is not None:
            await nutzap_wallet.announce_nutzap_info_event(nut_wallet, client, keys)
        else:
            print("Couldn't fetch wallet, please restart and see if it is there")

    # Test 1: We mint to our own wallet
    if mint_to_wallet:
        await nutzap_wallet.mint_cashu(nut_wallet, mints[mint_index], client, keys, mint_amount)
        nut_wallet = await nutzap_wallet.get_nut_wallet(client, keys)

    # Test 2: We send a nutzap to someone (can be ourselves)
    if send_test:
        zapped_event_id_hex = send_zapped_event
        zapped_user_hex = PublicKey.parse(send_reveiver).to_hex()

        await nutzap_wallet.send_nut_zap(send_zap_amount, send_zap_message, nut_wallet, zapped_event_id_hex, zapped_user_hex, client,
                           keys)

    #Test 3: Melt back to lightning:
    if melt:
        # you can overwrite the lu16 and/or npub, otherwise it's fetched from the profile (set it once by setting set_profile to True)
        lud16 = None
        npub = None
        await nutzap_wallet.melt_cashu(nut_wallet, mints[mint_index], melt_amount, client, keys, lud16, npub)
        await nutzap_wallet.get_nut_wallet(client, keys)


if __name__ == '__main__':
    env_path = Path('.env')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')

    show_history = True

    asyncio.run(test(DVMConfig().NUTZAP_RELAYS, DVMConfig().NUZAP_MINTS))
