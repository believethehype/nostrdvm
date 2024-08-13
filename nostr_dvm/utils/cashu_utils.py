import base64
import json


import requests

from nostr_dvm.utils.database_utils import get_or_add_user
from nostr_dvm.utils.zap_utils import create_bolt11_ln_bits, create_bolt11_lud16

BASE_URL = "https://mint.minibits.cash/Bitcoin"



def parse_cashu(cashu_token: str):
    try:
        prefix = "cashuA"
        assert cashu_token.startswith(prefix), Exception(
            f"Token prefix not valid. Expected {prefix}."
        )
        if not cashu_token.endswith("="):
            cashu_token = str(cashu_token) + "=="
        print(cashu_token)
        token_base64 = cashu_token[len(prefix):].encode("utf-8")
        cashu = json.loads(base64.urlsafe_b64decode(token_base64))
        token = cashu["token"][0]
        proofs = token["proofs"]
        mint = token["mint"]
        total_amount = 0
        for proof in proofs:
            total_amount += proof["amount"]

        return proofs, mint, total_amount, None

    except Exception as e:
        print(e)
        return None, None, None, "Cashu Parser: " + str(e)


async def redeem_cashu(cashu, config, client, required_amount=0, update_self=False) -> (bool, str, int, int):
    proofs, mint, total_amount, message = parse_cashu(cashu)
    if message is not None:
        return False, message, 0, 0

    estimated_fees = max(int(total_amount * 0.02), 3)
    estimated_redeem_invoice_amount = total_amount - estimated_fees

    # Not sure if this the best way to go, we first create an invoice that we send to the mint, we catch the fees
    # for that invoice, and create another invoice with the amount without fees to melt.
    if config.LNBITS_INVOICE_KEY != "":
        invoice, paymenthash = create_bolt11_ln_bits(estimated_redeem_invoice_amount, config)
    else:

        user = await get_or_add_user(db=config.DB, npub=config.PUBLIC_KEY,
                                     client=client, config=config, update=update_self)
        invoice = create_bolt11_lud16(user.lud16, estimated_redeem_invoice_amount)
    print(invoice)
    if invoice is None:
        return False, "couldn't create invoice", 0, 0

    url = mint + "/checkfees"  # Melt cashu tokens at Mint
    json_object = {"pr": invoice}
    headers = {"Content-Type": "application/json; charset=utf-8"}
    request_body = json.dumps(json_object).encode('utf-8')
    request = requests.post(url, data=request_body, headers=headers)
    tree = json.loads(request.text)
    fees = tree["fee"]
    print("Fees on this mint are " + str(fees) + " Sats")
    redeem_invoice_amount = total_amount - fees
    if redeem_invoice_amount < required_amount:
        err = ("Token value (Payment: " + str(total_amount) + " Sats. Fees: " +
               str(fees) + " Sats) below required amount of  " + str(required_amount)
               + " Sats. Cashu token has not been claimed.")
        print("[" + config.NIP89.NAME + "] " + err)
        return False, err, 0, 0

    if config.LNBITS_INVOICE_KEY != "":
        invoice, paymenthash = create_bolt11_ln_bits(redeem_invoice_amount, config)
    else:

        user = await get_or_add_user(db=config.DB, npub=config.PUBLIC_KEY,
                                     client=client, config=config, update=update_self)
        invoice = create_bolt11_lud16(user.lud16, redeem_invoice_amount)
    print(invoice)

    try:
        url = mint + "/melt"  # Melt cashu tokens at Mint
        json_object = {"proofs": proofs, "pr": invoice}
        headers = {"Content-Type": "application/json; charset=utf-8"}
        request_body = json.dumps(json_object).encode('utf-8')
        request = requests.post(url, data=request_body, headers=headers)
        tree = json.loads(request.text)
        print(request.text)
        is_paid = tree["paid"] if tree.get("paid") else False
        print(is_paid)
        if is_paid:
            print("cashu token redeemed")
            return True, "success", redeem_invoice_amount, fees
        else:
            msg = tree.get("detail").split('.')[0].strip() if tree.get("detail") else None
            print(msg)
            return False, msg, redeem_invoice_amount, fees
    except Exception as e:
        print(e)

    return False, "", redeem_invoice_amount, fees
