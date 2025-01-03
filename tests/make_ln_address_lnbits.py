from nostr_dvm.utils.zap_utils import make_ln_address_nostdress_manual_lnbits

name = ""
invoice_key = ""
npub = ""
nostdress_domain = ""
lnbits_domain = "https://demo.lnbits.com"

lnaddress, pin = make_ln_address_nostdress_manual_lnbits("_", invoice_key, npub, nostdress_domain, lnbits_domain, pin = " ", currentname= " ")
print(lnaddress)
print(pin)
