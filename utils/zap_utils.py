# LIGHTNING FUNCTIONS
import json
import urllib.parse

import requests
from Crypto.Cipher import AES
from bech32 import bech32_decode, convertbits, bech32_encode
from nostr_sdk import nostr_sdk, PublicKey, SecretKey, Event, EventBuilder, Tag
from utils.dvmconfig import DVMConfig
from utils.nostr_utils import get_event_by_id
import lnurl


def parse_amount_from_bolt11_invoice(bolt11_invoice: str) -> int:
    def get_index_of_first_letter(ip):
        index = 0
        for c in ip:
            if c.isalpha():
                return index
            else:
                index = index + 1
        return len(ip)

    remaining_invoice = bolt11_invoice[4:]
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


def parse_zap_event_tags(zap_event, keys, name, client, config):
    zapped_event = None
    invoice_amount = 0
    anon = False
    sender = zap_event.pubkey()

    for tag in zap_event.tags():
        if tag.as_vec()[0] == 'bolt11':
            invoice_amount = parse_amount_from_bolt11_invoice(tag.as_vec()[1])
        elif tag.as_vec()[0] == 'e':
            zapped_event = get_event_by_id(tag.as_vec()[1], client=client, config=config)
        elif tag.as_vec()[0] == 'description':
            zap_request_event = Event.from_json(tag.as_vec()[1])
            sender = check_for_zapplepay(zap_request_event.pubkey().to_hex(),
                                         zap_request_event.content())
            for z_tag in zap_request_event.tags():
                if z_tag.as_vec()[0] == 'anon':
                    if len(z_tag.as_vec()) > 1:
                        print("[" + name + "] Private Zap received.")
                        decrypted_content = decrypt_private_zap_message(z_tag.as_vec()[1],
                                                                        keys.secret_key(),
                                                                        zap_request_event.pubkey())
                        decrypted_private_event = Event.from_json(decrypted_content)
                        if decrypted_private_event.kind() == 9733:
                            sender = decrypted_private_event.pubkey().to_hex()
                            message = decrypted_private_event.content()
                            if message != "":
                                print("Zap Message: " + message)
                    else:
                        anon = True
                        print(
                            "[" + name + "] Anonymous Zap received. Unlucky, I don't know from whom, and never will")

    return invoice_amount, zapped_event, sender, anon


def create_bolt11_ln_bits(sats: int, config: DVMConfig) -> (str, str):
    url = config.LNBITS_URL + "/api/v1/payments"
    data = {'out': False, 'amount': sats, 'memo': "Nostr-DVM " + config.NIP89.name}
    headers = {'X-API-Key': config.LNBITS_INVOICE_KEY, 'Content-Type': 'application/json', 'charset': 'UTF-8'}
    try:
        res = requests.post(url, json=data, headers=headers)
        obj = json.loads(res.text)
        return obj["payment_request"], obj["payment_hash"]
    except Exception as e:
        print("LNBITS: " + str(e))
        return None, None


def check_bolt11_ln_bits_is_paid(payment_hash: str, config: DVMConfig):
    url = config.LNBITS_URL + "/api/v1/payments/" + payment_hash
    headers = {'X-API-Key': config.LNBITS_INVOICE_KEY, 'Content-Type': 'application/json', 'charset': 'UTF-8'}
    try:
        res = requests.get(url, headers=headers)
        obj = json.loads(res.text)
        return obj["paid"]
    except Exception as e:
        return None


def pay_bolt11_ln_bits(bolt11: str, config: DVMConfig):
    url = config.LNBITS_URL + "/api/v1/payments"
    data = {'out': True, 'bolt11': bolt11}
    headers = {'X-API-Key': config.LNBITS_ADMIN_KEY, 'Content-Type': 'application/json', 'charset': 'UTF-8'}
    try:
        res = requests.post(url, json=data, headers=headers)
        obj = json.loads(res.text)
        return obj["payment_hash"]
    except Exception as e:
        print("LNBITS: " + str(e))
        return None, None


# DECRYPT ZAPS
def check_for_zapplepay(pubkey_hex: str, content: str):
    try:
        # Special case Zapplepay
        if (pubkey_hex == PublicKey.from_bech32("npub1wxl6njlcgygduct7jkgzrvyvd9fylj4pqvll6p32h59wyetm5fxqjchcan")
                .to_hex()):
            real_sender_bech32 = content.replace("From: nostr:", "")
            pubkey_hex = PublicKey.from_bech32(real_sender_bech32).to_hex()
        return pubkey_hex

    except Exception as e:
        print(e)
        return pubkey_hex


def decrypt_private_zap_message(msg: str, privkey: SecretKey, pubkey: PublicKey):
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


def zap(lud16: str, amount: int, zap_type, content, recipient_pubkey, zapped_event, keys, dvm_config):
    if lud16.startswith("LNURL") or lud16.startswith("lnurl"):
        url = lnurl.decode(lud16)
    elif '@' in lud16: #LNaddress
        url = 'https://' + str(lud16).split('@')[1] + '/.well-known/lnurlp/' + str(lud16).split('@')[0]
    else:  # No lud16 set or format invalid
        return None
    try:
        response = requests.get(url)
        ob = json.loads(response.content)
        callback = ob["callback"]
        encoded_lnurl = lnurl.encode(url)
        amount_tag = Tag.parse(['amount', str(amount * 1000)])
        relays_tag = Tag.parse(['relays', str(dvm_config.RELAY_LIST)])
        p_tag = Tag.parse(['p', recipient_pubkey])
        e_tag = Tag.parse(['e', zapped_event])
        lnurl_tag = Tag.parse(['lnurl', encoded_lnurl])

        zap_request = EventBuilder(9734, content,
                                   [amount_tag, relays_tag, p_tag, e_tag, lnurl_tag]).to_event(keys).as_json()

        response = requests.get(callback + "?amount=" + str(int(amount) * 1000) + "&nostr=" + urllib.parse.quote_plus(
                zap_request) + "&lnurl=" + encoded_lnurl)
        ob = json.loads(response.content)
        return ob["pr"]

    except Exception as e:
        print(e)
        return None