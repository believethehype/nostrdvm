<script>
import {defineComponent} from 'vue'
import store from "@/store";
import amberSignerService from "@/components/android-signer/AndroidSigner";
import {Duration, Event, EventBuilder, EventId, Filter, Keys, PublicKey, Tag, Timestamp} from "@rust-nostr/nostr-sdk";
import miniToastr from "mini-toastr/mini-toastr";
import VueNotifications from "vue-notifications";
import {bech32} from "bech32";



export default defineComponent({
  name: "posting"
})

export async function post_note(note){
   let client = store.state.client
   let tags = []

   if (localStorage.getItem('nostr-key-method') === 'android-signer') {
    const draft = {
      content: note,
      kind: 1,
      pubkey: store.state.pubkey.toHex(),
      tags: tags,
      createdAt: Date.now()
    };
    const eventJson = await amberSignerService.signEvent(draft);
    await client.sendEvent(Event.fromJson(JSON.stringify(eventJson)));
   }
   else
   {
    await client.publishTextNote(note, tags);
   }
}

export async function schedule(note, datetopost) {


  let schedule = Timestamp.fromSecs(datetopost/1000)
  let humandatetime = schedule.toHumanDatetime()
      let time = humandatetime.split("T")[1].split("Z")[0].trim()
     let date = humandatetime.split("T")[0].split("-")[2].trim() + "." + humandatetime.split("T")[0].split("-")[1].trim() + "." + humandatetime.split("T")[0].split("-")[0].trim().slice(2)

   console.log("Date: " + date + " Time: "+ time )

  let client = store.state.client
  let signer = store.state.signer

  let noteevent = EventBuilder.textNote(note, []).customCreatedAt(schedule).toUnsignedEvent(store.state.pubkey)
  let signedEvent = await signer.signEvent(noteevent)

  let stringifiedevent = signedEvent.asJson()

  let tags_str = []
  let tag = Tag.parse(["i", stringifiedevent, "text"])
  tags_str.push(tag.asVec())
  let tags_as_str = JSON.stringify(tags_str)


  let content = await signer.nip04Encrypt(PublicKey.parse("85c20d3760ef4e1976071a569fb363f4ff086ca907669fb95167cdc5305934d1"), tags_as_str)

  let tags_t = []
  tags_t.push(Tag.parse(["p", "85c20d3760ef4e1976071a569fb363f4ff086ca907669fb95167cdc5305934d1"]))
  tags_t.push(Tag.parse(["encrypted"]))
  tags_t.push(Tag.parse(["client", "noogle"]))


  let evt = new EventBuilder(5905, content, tags_t)
  console.log(evt)
  let res = await client.sendEventBuilder(evt);
  console.log(res)
  miniToastr.showMessage("Note scheduled for " + ("Date: " + date + " Time: "+ time ))


}

export async function getEvents(eventids) {
  let ids = []
  for (let eid of eventids){
    ids.push(EventId.parse(eid))
  }
  const event_filter = new Filter().ids(ids)
  let client = store.state.client
  return await client.getEventsOf([event_filter], Duration.fromSecs(5))

}
export async function getEventsOriginalOrder(eventids) {
  let ids = []
  for (let eid of eventids){
    ids.push(EventId.parse(eid))
  }
  const event_filter = new Filter().ids(ids)
  let client = store.state.client
  let results =  await client.getEventsOf([event_filter], Duration.fromSecs(5))
  /*console.log(results.length)
  for (let e of results){
    console.log(e.id.toHex())
  } */

  let final = []
  for (let f of eventids){
    let note = results.find(value => value.id.toHex() === f)
    //console.log(note)
    final.push(note)
  }

  return final
}


export function nextInput(e) {
  const next = e.currentTarget.nextElementSibling;
  if (next) {
    next.focus();

  }
}

export async function get_user_infos(pubkeys){
        let profiles = []
        let client = store.state.client
        const profile_filter = new Filter().kind(0).authors(pubkeys)
        let evts = await client.getEventsOf([profile_filter],  Duration.fromSecs(10))

        for (const entry of evts){
          try{
            let contentjson = JSON.parse(entry.content)
             //console.log(contentjson)
            profiles.push({profile: contentjson, author: entry.author.toHex(), createdAt: entry.createdAt});
          }
          catch(error){
            console.log("error")
          }

        }

        return profiles

    }
export async function get_zaps(ids){
        let zapsandreactions = []

        for (let id of ids){
            zapsandreactions.push({
             id: id.toHex(),
             amount: 0,
              reactions: 0,
            zappedbyUser: false,
            reactedbyUser: false,})
        }

        let client = store.state.client
        const zap_filter = new Filter().kinds([9735, 7]).events(ids)
        let evts = await client.getEventsOf([zap_filter],  Duration.fromSecs(10))

        for (const entry of evts){
          try{
            //let contentjson = JSON.parse(entry.content)
            if (entry.kind === 9735){
              for (let tag of entry.tags) {
                if (tag.asVec()[0] === "description") {
                  let request = JSON.parse(tag.asVec()[1])
                  let etag = ""
                  let amount = 0
                  for (let tg of request.tags) {
                    if (tg[0] === "amount") {
                      amount = parseInt(tg[1])
                    }
                    if (tg[0] === "e") {
                      etag = tg[1]
                      //console.log(request.pubkey)
                      if (request.pubkey === localStorage.getItem("nostr-key")) {
                        zapsandreactions.find(x => x.id === etag).zappedbyUser = true
                      }
                    }
                  }

                  zapsandreactions.find(x => x.id === etag).amount += amount
                }
                }
            }
              else if (entry.kind === 7) {
                  for (let tag of entry.tags) {

                    if (tag.asVec()[0] === "e") {
                      if (entry.author.toHex() === localStorage.getItem("nostr-key")) {
                        zapsandreactions.find(x => x.id === tag.asVec()[1]).reactedbyUser = true
                      }
                      zapsandreactions.find(x => x.id === tag.asVec()[1]).reactions += 1

                    }
                  }


                }


             //console.log(contentjson)
            //zaps.push({profile: contentjson, author: entry.author.toHex(), createdAt: entry.createdAt});
          }
          catch(error){
            //console.log(error)
          }

        }

        //console.log(zapsandreactions)

        return zapsandreactions

    }

export async function get_reactions(ids){
        let reactions = []
        let jsonentry = {}
        for (let id of ids){
            reactions.push({
             id: id.toHex(),
             amount: 0,
             ReactedbyUser: false,})
        }

        let client = store.state.client
        const zap_filter = new Filter().kind(7).events(ids)
        let evts = await client.getEventsOf([zap_filter],  Duration.fromSecs(10))

        for (const entry of evts){
          try{
            //let contentjson = JSON.parse(entry.content)

            for (let tag of entry.tags){

              if (tag.asVec()[0] === "e") {
                console.log(entry.pubkey )
                if(entry.pubkey === localStorage.getItem("nostr-key")){
                  reactions.find(x=> x.id === tag.asVec()[1]).ReactedbyUser = true
                }
                reactions.find(x=> x.id ===  tag.asVec()[1]).amount += 1

              }
            }
             //console.log(contentjson)
            //zaps.push({profile: contentjson, author: entry.author.toHex(), createdAt: entry.createdAt});
          }
          catch(error){
            console.log("error")
          }

        }

        console.log(reactions)

        return reactions

    }



export const sleep = (ms) => {
  return new Promise(resolve => setTimeout(resolve, ms))
}


 export  async function copyinvoice(invoice){

        window.open("lightning:" + invoice,"_blank")
    await navigator.clipboard.writeText(invoice)
        miniToastr.showMessage("", "Copied Invoice to clipboard", VueNotifications.types.info)
    }

 export async function copyurl(url){
       await navigator.clipboard.writeText(url)
       miniToastr.showMessage("", "Copied link to clipboard", VueNotifications.types.info)
    }



export async function parseandreplacenpubs(note){
  note = note.replace("\n", " ")
  const myArray = note.split(" ");
  let finalnote = ""
  for (let word in myArray){

    if(myArray[word].startsWith("nostr:npub")){

  console.log(myArray[word])
       //console.log(pk.toBech32())
      try{
        let pk = PublicKey.parse(myArray[word].replace("nostr:", ""))
        let profiles = await get_user_infos([pk])
        console.log(profiles)
        //console.log(profiles[0].profile.nip05)
        myArray[word] = profiles[0].profile.nip05 // replace with nip05 for now
      }
      catch{

      }
    }
    finalnote = finalnote + myArray[word] + " "

  }

  return finalnote.trimEnd()
}


export async function parseandreplacenpubsName(note){

  const myArray = note.split(/\n | \r | /);
  let finalnote = ""
  for (let word in myArray){

        if (myArray[word].startsWith("https")){
          myArray[word] = myArray[word] + "\n"
        }

      if(myArray[word].startsWith("nostr:note")){
               myArray[word] =  "<a class='purple' target=\"_blank\" href='https://njump.me/" + myArray[word].replace("nostr:", "")+ "'>" +myArray[word].replace("nostr:", "") + "</a> "
      }
     else  if(myArray[word].startsWith("nostr:nevent")){
               myArray[word] =  "<a class='purple' target=\"_blank\" href='https://njump.me/" + myArray[word].replace("nostr:", "")+ "'>" +myArray[word].replace("nostr:", "") + "</a> "
      }


    else if(myArray[word].startsWith("nostr:npub")){
      //console.log(myArray[word])

       //console.log(pk.toBech32())
      try{
        let pk = PublicKey.parse(myArray[word].replace("nostr:", ""))
        let profiles = await get_user_infos([pk])
        //console.log(profiles[0].profile.nip05)

       // myArray[word] =  "<a class='purple' target=\"_blank\"  href=\"https://njump.com/" + myArray[word].replace("nostr:", "") +" \">" + profiles[0].profile.name + "</a> "
       myArray[word] =  "<a class='purple' target=\"_blank\" href='https://njump.me/" + myArray[word].replace("nostr:", "")+ "'>" + profiles[0].profile.name + "</a> "


          //  profiles[0].profile.name // replace with nip05 for now
      }
      catch{

      }
    }
    finalnote = finalnote + myArray[word] + " "

  }

  return finalnote.trimEnd()
}

async function fetchAsync (url) {
  let response = await fetch(url);
  let data = await response.json();
  return data;
}



export async function zaprequest(lud16, amount, content, zapped_event_id, zapped_user_id, relay_list){
    let url = ""

  console.log(lud16)
  console.log(PublicKey.parse(zapped_user_id).toBech32())
  console.log(EventId.parse(zapped_event_id).toBech32())
    console.log(zapped_event_id)


  zapped_user_id = PublicKey.parse(zapped_user_id).toHex()
  zapped_event_id = EventId.parse(zapped_event_id).toHex()

 //overwrite for debug
  //lud16 = "hype@bitcoinfixesthis.org"
  //zapped_user_id = PublicKey.parse("npub1nxa4tywfz9nqp7z9zp7nr7d4nchhclsf58lcqt5y782rmf2hefjquaa6q8").toHex()
  //zapped_event_id = EventId.parse("note1xsw95cp4ynelxdujd3xrh6kmre3y0lk699xn09z52mjenmktdllq9vtwyn").toHex()





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
        console.log("HELLO" + e)
      }
    }
    catch(error){
      console.log("ZAP REQUEST: " + error)
  }



        return null
}
export async function createBolt11Lud16(lud16, amount) {
  if (lud16 === null || lud16 === ""){
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
        }
    catch (e) {
            console.log(`LUD16: ${e}`);
            return null;
      }

  }


</script>

<template>

</template>

<style scoped>

</style>