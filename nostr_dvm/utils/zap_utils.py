# LIGHTNING/ZAP FUNCTIONS
import json
import os
import urllib.parse
from pathlib import Path

import bech32
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from bech32 import bech32_decode, convertbits, bech32_encode
from nostr_sdk import PublicKey, SecretKey, Event, EventBuilder, Tag, Keys, generate_shared_key, Kind, \
    Timestamp

from nostr_dvm.utils.nostr_utils import get_event_by_id, check_and_decrypt_own_tags
from hashlib import sha256
import dotenv

# TODO tor connection to lnbits
# proxies = {
#    'http': 'socks5h://127.0.0.1:9050',
#    'https': 'socks5h://127.0.0.1:9050'
# }

proxies = {}


async def parse_zap_event_tags(zap_event, keys, name, client, config):
    zapped_event = None
    invoice_amount = 0
    anon = False
    message = ""
    sender = zap_event.author()
    for tag in zap_event.tags():
        if tag.as_vec()[0] == 'bolt11':
            invoice_amount = parse_amount_from_bolt11_invoice(tag.as_vec()[1])
        elif tag.as_vec()[0] == 'e':
            zapped_event = await get_event_by_id(tag.as_vec()[1], client=client, config=config)
            zapped_event = check_and_decrypt_own_tags(zapped_event, config)
        elif tag.as_vec()[0] == 'p':
            p_tag = tag.as_vec()[1]
        elif tag.as_vec()[0] == 'description':
            zap_request_event = Event.from_json(tag.as_vec()[1])
            sender = check_for_zapplepay(zap_request_event.author().to_hex(),
                                         zap_request_event.content())
            for z_tag in zap_request_event.tags():
                if z_tag.as_vec()[0] == 'anon':
                    if len(z_tag.as_vec()) > 1:
                        # print("[" + name + "] Private Zap received.")
                        decrypted_content = decrypt_private_zap_message(z_tag.as_vec()[1],
                                                                        keys.secret_key(),
                                                                        zap_request_event.author())
                        decrypted_private_event = Event.from_json(decrypted_content)
                        if decrypted_private_event.kind().as_u64() == 9733:
                            sender = decrypted_private_event.author().to_hex()
                            message = decrypted_private_event.content()
                            # if message != "":
                            #    print("Zap Message: " + message)
                    else:
                        anon = True
                        print(
                            "[" + name + "] Anonymous Zap received. Unlucky, I don't know from whom, and never will")

    return invoice_amount, zapped_event, sender, message, anon


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


def create_bolt11_ln_bits(sats: int, config) -> (str, str):
    if config.LNBITS_URL == "":
        return None, None
    url = config.LNBITS_URL + "/api/v1/payments"
    data = {'out': False, 'amount': sats, 'memo': "Nostr-DVM " + config.NIP89.NAME}
    headers = {'X-API-Key': config.LNBITS_INVOICE_KEY, 'Content-Type': 'application/json', 'charset': 'UTF-8'}
    try:
        res = requests.post(url, json=data, headers=headers)
        obj = json.loads(res.text)
        if obj.get("payment_request") and obj.get("payment_hash"):
            return obj["payment_request"], obj["payment_hash"]  #
        else:
            print("LNBITS: " + res.text)
            return None, None
    except Exception as e:
        print("LNBITS: " + str(e))
        return None, None


def create_bolt11_lud16(lud16, amount):
    if lud16.startswith("LNURL") or lud16.startswith("lnurl"):
        url = decode_bech32(lud16)
        print(url)
    elif '@' in lud16:  # LNaddress
        url = 'https://' + str(lud16).split('@')[1] + '/.well-known/lnurlp/' + str(lud16).split('@')[0]
    else:  # No lud16 set or format invalid
        return None
    try:
        print(url)
        response = requests.get(url)
        ob = json.loads(response.content)
        callback = ob["callback"]
        response = requests.get(callback + "?amount=" + str(int(amount) * 1000))
        ob = json.loads(response.content)
        return ob["pr"]
    except Exception as e:
        print("LUD16: " + e)
        return None


def create_lnbits_account(name):
    if os.getenv("LNBITS_ADMIN_ID") is None or os.getenv("LNBITS_ADMIN_ID") == "":
        print("No admin id set, no wallet created.")
        return "", "", "", "", "failed"
    data = {
        'admin_id': os.getenv("LNBITS_ADMIN_ID"),
        'wallet_name': name,
        'user_name': name,
    }
    try:
        json_object = json.dumps(data)
        url = os.getenv("LNBITS_HOST") + '/usermanager/api/v1/users'
        print(url)
        headers = {'X-API-Key': os.getenv("LNBITS_ADMIN_KEY"), 'Content-Type': 'application/json', 'charset': 'UTF-8'}
        r = requests.post(url, data=json_object, headers=headers, proxies=proxies)
        walletjson = json.loads(r.text)
        print(walletjson)
        if walletjson.get("wallets"):
            return walletjson['wallets'][0]['inkey'], walletjson['wallets'][0]['adminkey'], walletjson['wallets'][0][
                'id'], walletjson['id'], "success"
    except:
        print("error creating wallet")
        return "", "", "", "", "failed"


def check_bolt11_ln_bits_is_paid(payment_hash: str, config):
    url = config.LNBITS_URL + "/api/v1/payments/" + payment_hash
    headers = {'X-API-Key': config.LNBITS_INVOICE_KEY, 'Content-Type': 'application/json', 'charset': 'UTF-8'}
    try:
        res = requests.get(url, headers=headers, proxies=proxies)
        obj = json.loads(res.text)
        if obj.get("paid"):
            return obj["paid"]
        else:
            return False
    except Exception as e:
        return None


def pay_bolt11_ln_bits(bolt11: str, config):
    url = config.LNBITS_URL + "/api/v1/payments"
    data = {'out': True, 'bolt11': bolt11}
    headers = {'X-API-Key': config.LNBITS_ADMIN_KEY, 'Content-Type': 'application/json', 'charset': 'UTF-8'}
    try:
        res = requests.post(url, json=data, headers=headers)
        obj = json.loads(res.text)
        if obj.get("payment_hash"):
            return obj["payment_hash"]
        else:
            return "Error"
    except Exception as e:
        print("LNBITS: " + str(e))
        return "Error"


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


def enrypt_private_zap_message(message, privatekey, publickey):
    # Generate a random IV
    shared_secret = generate_shared_key(privatekey, publickey)
    iv = os.urandom(16)

    # Encrypt the message
    cipher = AES.new(bytearray(shared_secret), AES.MODE_CBC, bytearray(iv))
    utf8message = message.encode('utf-8')
    padded_message = pad(utf8message, AES.block_size)
    encrypted_msg = cipher.encrypt(padded_message)

    encrypted_msg_bech32 = bech32_encode("pzap", convertbits(encrypted_msg, 8, 5, True))
    iv_bech32 = bech32_encode("iv", convertbits(iv, 8, 5, True))
    return encrypted_msg_bech32 + "_" + iv_bech32


def decrypt_private_zap_message(msg: str, privkey: SecretKey, pubkey: PublicKey):
    shared_secret = generate_shared_key(privkey, pubkey)
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


def decode_bech32(encoded_lnurl):
    # Decode the bech32 encoded string
    hrp, data = bech32.bech32_decode(encoded_lnurl)

    if hrp != 'lnurl':
        raise ValueError("Invalid human-readable part (hrp)")

    # Convert the data back from 5-bit words to 8-bit bytes
    decoded_bytes = bech32.convertbits(data, 5, 8, False)

    # Convert the bytes back to a string
    decoded_url = bytes(decoded_bytes).decode('utf-8')

    return decoded_url


def zaprequest(lud16: str, amount: int, content, zapped_event, zapped_user, keys, relay_list, zaptype="public"):
    print(lud16)
    print(str(amount))
    print(content)
    if lud16.startswith("LNURL") or lud16.startswith("lnurl"):
        url = decode_bech32(lud16)
    elif '@' in lud16:  # LNaddress
        url = 'https://' + str(lud16).split('@')[1] + '/.well-known/lnurlp/' + str(lud16).split('@')[0]
    else:  # No lud16 set or format invalid
        return None
    try:
        response = requests.get(url)
        ob = json.loads(response.content)
        callback = ob["callback"]
        print(ob["callback"])


        #encoded_lnurl = lnurl.encode(url)

        url_bytes = url.encode()
        encoded_lnurl = bech32.bech32_encode('lnurl', bech32.convertbits(url_bytes, 8, 5))

        amount_tag = Tag.parse(['amount', str(amount * 1000)])
        relays_tag = Tag.parse(['relays', str(relay_list)])
        lnurl_tag = Tag.parse(['lnurl', encoded_lnurl])
        if zapped_event is not None:
            p_tag = Tag.parse(['p', zapped_event.author().to_hex()])
            e_tag = Tag.parse(['e', zapped_event.id().to_hex()])
            tags = [amount_tag, relays_tag, p_tag, e_tag, lnurl_tag]
        else:
            p_tag = Tag.parse(['p', zapped_user.to_hex()])
            tags = [amount_tag, relays_tag, p_tag, lnurl_tag]

        if zaptype == "private":
            if zapped_event is not None:
                key_str = keys.secret_key().to_hex() + zapped_event.id().to_hex() + str(
                    zapped_event.created_at().as_secs())

            else:
                key_str = keys.secret_key().to_hex() + str(Timestamp.now().as_secs())

            encryption_key = sha256(key_str.encode('utf-8')).hexdigest()
            tags = [p_tag]
            if zapped_event is not None:
                tags.append(e_tag)
            zap_request = EventBuilder(Kind(9733), content,
                                       tags).to_event(keys).as_json()
            keys = Keys.parse(encryption_key)
            if zapped_event is not None:
                encrypted_content = enrypt_private_zap_message(zap_request, keys.secret_key(), zapped_event.author())
            else:
                encrypted_content = enrypt_private_zap_message(zap_request, keys.secret_key(), zapped_user)

            anon_tag = Tag.parse(['anon', encrypted_content])
            tags.append(anon_tag)
            content = ""

        zap_request = EventBuilder(Kind(9734), content,
                                   tags).to_event(keys).as_json()

        response = requests.get(callback + "?amount=" + str(int(amount) * 1000) + "&nostr=" + urllib.parse.quote_plus(
            zap_request) + "&lnurl=" + encoded_lnurl)
        ob = json.loads(response.content)
        return ob["pr"]

    except Exception as e:
        print("ZAP REQUEST: " + str(e))
        return None


def get_price_per_sat(currency):
    import requests

    url = "https://openapiv1.coinstats.app/coins/bitcoin"
    params = {"skip": 0, "limit": 1, "currency": currency}
    price_currency_per_sat = 0.0004
    if os.getenv("COINSTATSOPENAPI_KEY"):

        header = {'accept': 'application/json', 'X-API-KEY': os.getenv("COINSTATSOPENAPI_KEY")}
        try:
            response = requests.get(url, headers=header, params=params)
            response_json = response.json()

            bitcoin_price = response_json["price"]
            price_currency_per_sat = bitcoin_price / 100000000.0
        except:
            price_currency_per_sat = 0.0004

    return price_currency_per_sat


def make_ln_address_nostdress(identifier, npub, pin, nostdressdomain):
    print(os.getenv("LNBITS_INVOICE_KEY_" + identifier.upper()))
    data = {
        'name': identifier,
        'domain': nostdressdomain,
        'kind': "lnbits",
        'host': os.getenv("LNBITS_HOST"),
        'key': os.getenv("LNBITS_INVOICE_KEY_" + identifier.upper()),
        'pin': pin,
        'npub': npub,
        'currentname': " "
    }

    try:
        url = "https://" + nostdressdomain + "/api/easy/"
        res = requests.post(url, data=data)
        print(res.text)
        obj = json.loads(res.text)

        if obj.get("ok"):
            return identifier + "@" + nostdressdomain, obj["pin"]
    except Exception as e:
        print(e)
        return "", ""


def check_and_set_ln_bits_keys(identifier, npub):
    if not os.getenv("LNBITS_INVOICE_KEY_" + identifier.upper()):
        invoicekey, adminkey, walletid, userid, success = create_lnbits_account(identifier)
        add_key_to_env_file("LNBITS_INVOICE_KEY_" + identifier.upper(), invoicekey)
        add_key_to_env_file("LNBITS_ADMIN_KEY_" + identifier.upper(), adminkey)
        add_key_to_env_file("LNBITS_USER_ID_" + identifier.upper(), userid)
        add_key_to_env_file("LNBITS_WALLET_ID_" + identifier.upper(), userid)

        lnaddress = ""
        pin = ""
        if os.getenv("NOSTDRESS_DOMAIN") and success != "failed":
            print(os.getenv("NOSTDRESS_DOMAIN"))
            lnaddress, pin = make_ln_address_nostdress(identifier, npub, " ", os.getenv("NOSTDRESS_DOMAIN"))
        add_key_to_env_file("LNADDRESS_" + identifier.upper(), lnaddress)
        add_key_to_env_file("LNADDRESS_PIN_" + identifier.upper(), pin)

        return invoicekey, adminkey, userid, walletid, lnaddress
    else:
        return (os.getenv("LNBITS_INVOICE_KEY_" + identifier.upper()),
                os.getenv("LNBITS_ADMIN_KEY_" + identifier.upper()),
                os.getenv("LNBITS_USER_ID_" + identifier.upper()),
                os.getenv("LNBITS_WALLET_ID_" + identifier.upper()),
                os.getenv("LNADDRESS_" + identifier.upper()))


def add_key_to_env_file(value, oskey):
    env_path = Path('.env')
    if env_path.is_file():
        dotenv.load_dotenv(env_path, verbose=True, override=True)
        dotenv.set_key(env_path, value, oskey)
