<script>
import {defineComponent} from 'vue'
import store from "@/store";
import amberSignerService from "@/components/android-signer/AndroidSigner";
import {
  Alphabet,
  Duration,
  Event,
  EventBuilder,
  EventId,
  Filter,
  Keys,
  PublicKey,
  SingleLetterTag,
  Tag,
  Timestamp
} from "@rust-nostr/nostr-sdk";
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

export async function fetchAsync (url) {
  let response = await fetch(url);
  let data = await response.json();
  return data;
}



export async function hasActiveSubscription(pubkeystring, tiereventid, tierauthorid, amounts) {
 console.log("Checking for subscription")
  let client = store.state.client
  let subscriptionstatus = {
    isActive: false,
    validuntil: 0,
    subscriptionId: "",
  }

  let event7001id = EventId
  console.log(pubkeystring)
  // look if user has 7001 event, and if 7001 has been canceled by 7002
  const filter = new Filter().kind(7001).author(PublicKey.parse(pubkeystring)).pubkey(PublicKey.parse(tierauthorid)).event(EventId.parse(tiereventid)) //only get latest with these conditions
  let evts = await client.getEventsOf([filter], Duration.fromSecs(5))
  console.log(evts)
  if (evts.length > 0) {

    //console.log("7001: " + evts[0].asJson())
    let checkispaid = []
    for (let tag of evts[0].tags){
      /*if (tag.asVec()[0] === "e"){
        console.log("sanity check")
           const filtercheck = new Filter().kind(37001).id(EventId.parse(tag.asVec()[1])).limit(1)  // get latest with these conditons   # customTag(SingleLetterTag.lowercase(Alphabet.A), [eventid])
           let sanityevents = await client.getEventsOf([filtercheck], Duration.fromSecs(5))
          if (sanityevents.length === 0){
             subscriptionstatus.isActive = false
             return subscriptionstatus
          }
          else{console.log(sanityevents[0].asJson())
          }
      } */

      if (tag.asVec()[0] === "zap"){
        checkispaid.push(tag)
      }
    }

     let splitids = []
    for (let tag of checkispaid){
      splitids.push(PublicKey.parse(tag.asVec()[1]))
      console.log(tag.asVec())
    }
    if (checkispaid.length === 0){
        subscriptionstatus.isActive = false
        return subscriptionstatus
    }

    for (let evt in evts){
      event7001id = evts[0].id
    }

    event7001id = evts[0].id

    const filter = new Filter().kind(7002).pubkey(PublicKey.parse(tierauthorid)).event(event7001id).limit(1)  // get latest with these conditons   # customTag(SingleLetterTag.lowercase(Alphabet.A), [eventid])
    let cancelevts = await client.getEventsOf([filter], Duration.fromSecs(5))
    if (cancelevts.length > 0) {
      if (cancelevts[0].createdAt.asSecs() > evts[0].createdAt.asSecs()) {
        console.log("A subscription exists, but has been canceled")
        subscriptionstatus.isActive = false
        subscriptionstatus.subscriptionId = event7001id.toHex()
        return subscriptionstatus
      }
      }
    else {
      console.log("A subscription exists, checking payment status")




      const zapfilter = new Filter().kind(9735).pubkeys(splitids).event(event7001id).limit(checkispaid.length)
      let zapevents = await client.getEventsOf([zapfilter], Duration.fromSecs(5))
      if (zapevents.length > 0) {
        console.log(zapevents)
        let timeofourlastzap = 0

          let overallamount = 0

          let overall = 0
          for (let tag of checkispaid){
            let split = parseInt(tag.asVec()[2])
            overall += split
          }
        for(let zapevent of zapevents) {


          if (zapevent.createdAt.asSecs() > timeofourlastzap) {
            timeofourlastzap = zapevent.createdAt.asSecs()
          }

            for (let tag of zapevent.tags) {
              if (tag.asVec()[0] === "description") {

                let event9734 = Event.fromJson(tag.asVec()[1])


                for (let tag of event9734.tags) {
                  if (tag.asVec()[0] === "amount") {
                    let amount = parseInt(tag.asVec()[1])
                    console.log("AMOUNT: " + amount)
                    overallamount = overallamount + amount
                  }
                }
              }
          }
        }


                let entry
                for (let index in amounts){
                 if(parseInt(amounts[index].amount) === overallamount ){
                   entry = amounts[index]
                 }
                }

                if(!entry){
                  console.log("Undefined amount")
                   subscriptionstatus.isActive = false
                   subscriptionstatus.subscriptionId = event7001id.toHex()
                   //subscriptionstatus.validuntil = zapevent.createdAt.asSecs() + 24*60*60
                   return subscriptionstatus
                }
                else{
                     console.log(entry.amount + " " + entry.cadence)
                     if (entry.cadence === "daily"){
                       if (timeofourlastzap + 24*60*60 > Timestamp.now().asSecs()){
                           console.log("A daily subscription exists, and is active")
                           subscriptionstatus.isActive = true
                           subscriptionstatus.subscriptionId = event7001id.toHex()
                           subscriptionstatus.validuntil = timeofourlastzap + 24*60*60
                          return subscriptionstatus

                       }
                     }
                     else if (entry.cadence === "monthly"){
                       if (timeofourlastzap + 31*24*60*60 > Timestamp.now().asSecs()){
                           console.log("A monthly subscription exists, and is active")
                           subscriptionstatus.isActive = true
                           subscriptionstatus.subscriptionId = event7001id.toHex()
                           subscriptionstatus.validuntil = timeofourlastzap + 31*24*60*60
                          return subscriptionstatus

                       }
                     }
                       else if (entry.cadence === "yearly"){
                       if (timeofourlastzap + 366*24*60*60 > Timestamp.now().asSecs()){
                           console.log("A yearly subscription exists, and is active")
                           subscriptionstatus.isActive = true
                           subscriptionstatus.subscriptionId = event7001id.toHex()
                           subscriptionstatus.validuntil = timeofourlastzap + 366*24*60*60
                          return subscriptionstatus

                       }
                     }





            /*else if (tag.asVec()[0] === "bolt11"){
              let lnurl = tag.asVec()[1]
                console.log(lnurl)
            } */





      }
        // todo check that subscription is within the range



      } else {
        console.log("A subscription exists, but no payment has been made")
        subscriptionstatus.isActive = false
        subscriptionstatus.subscriptionId = event7001id.toHex()
        return subscriptionstatus
      }

    }

}

  else {
    console.log("No subscription exists")
    subscriptionstatus.isActive = false
    return subscriptionstatus
  }
}









</script>

<template>

</template>

<style scoped>

</style>