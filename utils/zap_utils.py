# LIGHTNING FUNCTIONS
import json

import requests
from Crypto.Cipher import AES
from bech32 import bech32_decode, convertbits
from nostr_sdk import PublicKey, nostr_sdk


def parse_bolt11_invoice(invoice):
    def get_index_of_first_letter(ip):
        index = 0
        for c in ip:
            if c.isalpha():
                return index
            else:
                index = index + 1
        return len(ip)

    remaining_invoice = invoice[4:]
    index = get_index_of_first_letter(remaining_invoice)
    identifier = remaining_invoice[index]
    number_string = remaining_invoice[:index]
    number = float(number_string)
    if identifier == 'm':
        number = number * 100000000 * 0.001
    elif identifier == 'u':
        number = number * 100000000 * 0.000001
    elif identifier == 'n':
        number = number * 100000000 * 0.000000001
    elif identifier == 'p':
        number = number * 100000000 * 0.000000000001

    return int(number)

def create_bolt11_ln_bits(sats, config):
    url = config.LNBITS_URL + "/api/v1/payments"
    data = {'out': False, 'amount': sats, 'memo': "Nostr-DVM"}
    headers = {'X-API-Key': config.LNBITS_INVOICE_KEY, 'Content-Type': 'application/json', 'charset': 'UTF-8'}
    try:
        res = requests.post(url, json=data, headers=headers)
        obj = json.loads(res.text)
        return obj["payment_request"], obj["payment_hash"]
    except Exception as e:
        print(e)
        return None

def check_bolt11_ln_bits_is_paid(payment_hash, config):
    url = config.LNBITS_URL + "/api/v1/payments/" + payment_hash
    headers = {'X-API-Key': config.LNBITS_INVOICE_KEY, 'Content-Type': 'application/json', 'charset': 'UTF-8'}
    try:
        res = requests.get(url, headers=headers)
        obj = json.loads(res.text)
        return obj["paid"]
    except Exception as e:
        #print("Exception checking invoice is paid:" + e)
        return None


# DECRYPT ZAPS
def check_for_zapplepay(sender, content):
    try:
        # Special case Zapplepay
        if sender == PublicKey.from_bech32("npub1wxl6njlcgygduct7jkgzrvyvd9fylj4pqvll6p32h59wyetm5fxqjchcan").to_hex():
            real_sender_bech32 = content.replace("From: nostr:", "")
            sender = PublicKey.from_bech32(real_sender_bech32).to_hex()
        return sender

    except Exception as e:
        print(e)
        return sender


def decrypt_private_zap_message(msg, privkey, pubkey):
    shared_secret = nostr_sdk.generate_shared_key(privkey, pubkey)
    if len(shared_secret) != 16 and len(shared_secret) != 32:
        return "invalid shared secret size"
    parts = msg.split("_")
    if len(parts) != 2:
        return "invalid message format"
    try:
        _, encrypted_msg = bech32_decode(parts[0])
        encrypted_bytes = convertbits(encrypted_msg, 5, 8, False)
        _, iv = bech32_decode(parts[1])
        iv_bytes = convertbits(iv, 5, 8, False)
    except Exception as e:
        return e
    try:
        cipher = AES.new(bytearray(shared_secret), AES.MODE_CBC, bytearray(iv_bytes))
        decrypted_bytes = cipher.decrypt(bytearray(encrypted_bytes))
        plaintext = decrypted_bytes.decode("utf-8")
        decoded = plaintext.rsplit("}", 1)[0] + "}"  # weird symbols at the end
        return decoded
    except Exception as ex:
        return str(ex)

