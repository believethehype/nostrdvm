<script>
import {defineComponent} from 'vue'
import store from "@/store";
import amberSignerService from "@/components/android-signer/AndroidSigner";
import {Duration, Event, EventBuilder, EventId, Filter, Keys, PublicKey, Tag, Timestamp} from "@rust-nostr/nostr-sdk";
import miniToastr from "mini-toastr/mini-toastr";
import VueNotifications from "vue-notifications";

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




export const sleep = (ms) => {
  return new Promise(resolve => setTimeout(resolve, ms))
}


 export  async function copyinvoice(invoice){
       await navigator.clipboard.writeText(invoice)
        window.open("lightning:" + invoice,"_blank")
        miniToastr.showMessage("", "Copied Invoice to clipboard", VueNotifications.types.info)
    }

 export async function copyurl(url){
       await navigator.clipboard.writeText(url)
       miniToastr.showMessage("", "Copied link to clipboard", VueNotifications.types.info)
    }



export async function parseandreplacenpubs(note){

  const myArray = note.split(" ");
  let finalnote = ""
  for (let word in myArray){
    if(myArray[word].startsWith("nostr:npub")){
      //console.log(myArray[word])
      let pk = PublicKey.parse(myArray[word].replace("nostr:", ""))
       //console.log(pk.toBech32())
       let profiles = await get_user_infos([pk])
      //console.log(profiles[0].profile.nip05)
      myArray[word] = profiles[0].profile.nip05 // replace with nip05 for now

         // <href>='https://njump.com/'>test[0].profile.nip05</href>test[0].profile.nip05
    }
    finalnote = finalnote + myArray[word] + " "

  }

  return finalnote.trimEnd()
}

export async function createBolt11Lud16(lud16, amount) {
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