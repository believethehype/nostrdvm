<script>

import {requestProvider} from "webln";
import store from "@/store";
import {copyinvoice, fetchAsync} from "@/components/helper/Helper.vue";
import {EventBuilder, EventId, PublicKey, Tag} from "@rust-nostr/nostr-sdk";
import {bech32} from "bech32";
import {webln} from "@getalby/sdk";

import amberSignerService from "@/components/android-signer/AndroidSigner";
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";




async function zap_nwc(invoice){


    const nwc = new webln.NostrWebLNProvider({
        nostrWalletConnectUrl: loadNWCUrl(),
      }); // loadNWCUrl is some function to get the NWC URL from some (encrypted) storage


      // connect to the relay
      await nwc.enable();

      // now you can send payments by passing in the invoice
  try{
     const response = await nwc.sendPayment(invoice);
      console.log(response)
      return true
  }
  catch (error){
    miniToastr.showMessage(error, "This didn't work", VueNotifications.types.error)
    console.log(error)
     return false
  }

    }


export function loadNWCObject() {
      if (localStorage.getItem("nwc")){
          if(JSON.parse(localStorage.getItem("nwc")).nwcUrl.startsWith("nostr+walletconnect://")){
             return JSON.parse(localStorage.getItem("nwc"))
          }

      }
      return null
}

function loadNWCUrl() {
      if (localStorage.getItem("nwc")){
          if(JSON.parse(localStorage.getItem("nwc")).nwcUrl.startsWith("nostr+walletconnect://")){
             return JSON.parse(localStorage.getItem("nwc")).nwcUrl
          }

      }
      return ""
}

export async function zap(invoice){
  let nwcstring = loadNWCUrl()
  if (nwcstring.startsWith("nostr+walletconnect://"))
  {
    return zap_nwc(invoice)
  }
  else{
    let webln;

        //this.dvmpaymentaddr =  `https://chart.googleapis.com/chart?cht=qr&chl=${invoice}&chs=250x250&chld=M|0`;

    try {
      webln = await requestProvider();
    } catch (err) {
        await copyinvoice(invoice)
    }

    if (webln) {
      try{
           let response = await webln.sendPayment(invoice)
           return true
      }
      catch(err){
            console.log(err)
            await copyinvoice(invoice)

      }
    }
  }

   return false
}

export async function zap_lud16(lud16, eventid, authorid){
  if(lud16 !== null && lud16 !== ""){
  let invoice = await zaprequest(lud16, 21 , "with love from noogle.lol", eventid, authorid, store.state.relays)

   let nwcstring = loadNWCUrl()
  if (nwcstring.startsWith("nostr+walletconnect://"))
  {
    return zap_nwc(invoice)
  }

  else{
      let webln;
    try {
      webln = await requestProvider();
    } catch (err) {
      if (invoice === null){
        invoice = await createBolt11Lud16(lud16, 21)
      }

      await copyinvoice(invoice)


    }
    if (webln) {
      try {
        let response = await webln.sendPayment(invoice)
        if (response.preimage != null && response.preimage !== "") {
          return true
        }
      }

    catch(err){
          console.log(err)
          await copyinvoice(invoice)

    }
  }
  }


   return false
}
}

  export async function zaprequest(lud16, amount, content, zapped_evt_id, zapped_usr_id, relay_list){
    let url = ""

  console.log(lud16)
  console.log(zapped_evt_id)


  let zapped_user_id = PublicKey.parse(zapped_usr_id).toHex()
  let zapped_event_id = EventId.parse(zapped_evt_id).toHex()


    if (lud16 !== "" && lud16.toString().includes('@')){
    url = `https://${lud16.split('@')[1]}/.well-known/lnurlp/${lud16.split('@')[0]}`;
      console.log(url)
    }
    else{
       return null
    }
    try{

        let ob = await fetchAsync(url)
        let callback = ob["callback"]
        console.log(callback)


        const urlBytes = new TextEncoder().encode(url);
        const encoded_lnurl = bech32.encode('lnurl', bech32.toWords(urlBytes), 1023);


           const amount_tag = ['amount', (amount * 1000).toString()];
           let relays = ['relays']
           relays.push.apply(relays, relay_list)
           //let  relays_tag = Tag.parse(relays);

           const lnurl_tag = ['lnurl', encoded_lnurl];

        let tags = []
        let p_tag = ['p', zapped_user_id]
        if (zapped_event_id !== null){
            let e_tag = ['e', zapped_event_id]
            tags = [amount_tag, relays, p_tag, e_tag, lnurl_tag]
        }

        else{
            tags = [amount_tag, relays, p_tag, lnurl_tag]
        }
       /*if (zaptype === "private") {
          const key_str = keys.secret_key().to_hex() + zapped_event.id().to_hex() + zapped_event.created_at().as_secs().toString();
          const encryption_key = sha256(key_str).toString('hex');
          const zap_request = new EventBuilder(9733, content, [p_tag, e_tag]).to_event(keys).as_json();
          keys = Keys.parse(encryption_key);
          const encrypted_content = enrypt_private_zap_message(zap_request, keys.secret_key(), zapped_event.author());
          const anon_tag = Tag.parse(['anon', encrypted_content]);
          tags.push(anon_tag);
          content = "";
        } */



        let signer = store.state.signer
        let zap_request = ""

        if (localStorage.getItem('nostr-key-method') === 'android-signer') {
            let draft = {
              content: content,
              kind: 9734,
              pubkey: store.state.pubkey.toHex(),
              tags: tags,
              createdAt: Date.now()
            };

            let res = await amberSignerService.signEvent(draft)
            zap_request = JSON.stringify(res)
            //await sleep(3000)

          }
       else {
            let tags_t = []
            for (let tag of tags){
              tags_t.push(Tag.parse(tag))
            }
            let noteevent =  new EventBuilder(9734, content, tags_t).toUnsignedEvent(store.state.pubkey)
            let signedEvent = await signer.signEvent(noteevent)
            zap_request = signedEvent.asJson()
       }

   try{

         const queryString = `amount=${(amount * 1000).toString()}&nostr=${encodeURIComponent(zap_request)}&lnurl=${encoded_lnurl}`;

          console.log(queryString)
        let ob = await fetchAsync(`${callback}?${queryString}`)
        return ob["pr"]
          }
      catch(e){
        console.log(e)
      }
    }
    catch(error){

      console.log("ZAP REQUEST: " + error)
  }



        return null
}
export async function createBolt11Lud16(lud16, amount) {
  if (lud16 === null || lud16 === "") {
    return null;
  }

  let url;
  if (lud16.includes('@')) {  // LNaddress
    const parts = lud16.split('@');
    url = `https://${parts[1]}/.well-known/lnurlp/${parts[0]}`;
  } else {  // No lud16 set or format invalid
    return null;
  }

  try {
    console.log(url);
    const response = await fetch(url);
    const ob = await response.json();
    const callback = ob.callback;
    const amountInSats = parseInt(amount) * 1000;
    const callbackResponse = await fetch(`${callback}?amount=${amountInSats}`);
    const obCallback = await callbackResponse.json();
    return obCallback.pr;
  } catch (e) {
    console.log(`LUD16: ${e}`);
    return null;
  }

}
</script>

<template>

</template>

<style scoped>

</style>