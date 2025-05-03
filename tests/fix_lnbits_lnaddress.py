import os
from pathlib import Path
import dotenv
from nostr_dvm.utils.zap_utils import make_ln_address_nostdress, create_lnbits_wallet, add_key_to_env_file


def playground():
    # change the idenftier to the dvm you want to update.
    # This will create a new lnbits wallet and update the lnaddress to it
    # This is for existing dvms
    identifier = "discovery_content_gm"
    check_and_set_ln_bits_keys_force_new(identifier, os.getenv("DVM_PRIVATE_KEY_BOT_" + identifier.upper()))



def check_and_set_ln_bits_keys(identifier, npub):
    if not os.getenv("LNBITS_INVOICE_KEY_" + identifier.upper()):
        invoicekey, adminkey, walletid, success = create_lnbits_wallet(identifier)

        add_key_to_env_file("LNBITS_INVOICE_KEY_" + identifier.upper(), invoicekey)
        add_key_to_env_file("LNBITS_ADMIN_KEY_" + identifier.upper(), adminkey)
        add_key_to_env_file("LNBITS_WALLET_ID_" + identifier.upper(), walletid)

        lnaddress = ""
        pin = ""
        if os.getenv("NOSTDRESS_DOMAIN") and success != "failed":
            print(os.getenv("NOSTDRESS_DOMAIN"))
            lnaddress, pin = make_ln_address_nostdress(identifier, npub, " ", os.getenv("NOSTDRESS_DOMAIN"), identifier)
        add_key_to_env_file("LNADDRESS_" + identifier.upper(), lnaddress)
        add_key_to_env_file("LNADDRESS_PIN_" + identifier.upper(), pin)

        return invoicekey, adminkey, walletid, lnaddress
    else:
        return (os.getenv("LNBITS_INVOICE_KEY_" + identifier.upper()),
                os.getenv("LNBITS_ADMIN_KEY_" + identifier.upper()),
                os.getenv("LNBITS_WALLET_ID_" + identifier.upper()),
                os.getenv("LNADDRESS_" + identifier.upper()))



def check_and_set_ln_bits_keys_force_new(identifier, npub):
        #FORCE UPDATE THE CONFIG; INSTALL NEW WALLET
        invoicekey, adminkey, walletid, success = create_lnbits_wallet(identifier)

        add_key_to_env_file("LNBITS_INVOICE_KEY_" + identifier.upper(), invoicekey)
        add_key_to_env_file("LNBITS_ADMIN_KEY_" + identifier.upper(), adminkey)
        add_key_to_env_file("LNBITS_WALLET_ID_" + identifier.upper(), walletid)

        lnaddress = ""
        if os.getenv("NOSTDRESS_DOMAIN") and success != "failed":
            print(os.getenv("NOSTDRESS_DOMAIN"))
            lnaddress, pin = make_ln_address_nostdress(identifier, npub, os.getenv("LNADDRESS_PIN_" + identifier.upper()), os.getenv("NOSTDRESS_DOMAIN"), identifier)
        add_key_to_env_file("LNADDRESS_" + identifier.upper(), lnaddress)
        add_key_to_env_file("LNADDRESS_PIN_" + identifier.upper(), pin)

        return invoicekey, adminkey, walletid, lnaddress



if __name__ == '__main__':
    env_path = Path('.env')
    if not env_path.is_file():
        with open('.env', 'w') as f:
            print("Writing new .env file")
            f.write('')
    if env_path.is_file():
        print(f'loading environment from {env_path.resolve()}')
        dotenv.load_dotenv(env_path, verbose=True, override=True)
    else:
        raise FileNotFoundError(f'.env file not found at {env_path} ')
    playground()
