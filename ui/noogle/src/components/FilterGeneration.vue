<script setup>


import {
  Client,
  Duration,
  Event,
  EventBuilder,
  Filter,
  Keys,
  NostrSigner,
  PublicKey,
  Tag,
  Timestamp,
  UnsignedEvent
} from "@rust-nostr/nostr-sdk";
import store from '../store';
import miniToastr from "mini-toastr";
import {onMounted, ref} from "vue";
import {get_user_infos, hasActiveSubscription, sleep} from "../components/helper/Helper.vue"
import {createBolt11Lud16, zap, zaprequest} from "../components/helper/Zap.vue"
import {webln} from "@getalby/sdk";


import amberSignerService from "./android-signer/AndroidSigner";
import StringUtil from "@/components/helper/string.ts";


let dvms =[]
let requestids = []


onMounted(async () => {

  while(store.state.nip89dvms.length === 0){
     await sleep(100)
  }
await addAllContentDVMs()
  console.log(dvms)

})



function set_subscription_props(amount, cadence, dvm) {
  console.log(dvm)
  current_subscription_dvm.value = dvm
  current_subscription_amount.value = amount
  current_subscription_cadence.value = cadence
  current_subscription_nwc.value = ""
  nwcalby.value = ""
  nwcmutiny.value = ""
  nwc.value = ""

}

async function generate_feed(id) {

   if (!localStorage.getItem("nostr-key-method") || localStorage.getItem("nostr-key-method") === "anon"){
    miniToastr.showMessage("Login to use Filter DVMs.", "Not logged in", "error")
    return
  }

  listen()


   try {

        let client = store.state.client
        //console.log(dvms.find(i => i.id === id).encryptionSupported)

        let current_dvm = dvms.find(i => i.id === id)

        let content = "NIP 90 Profile Discovery request"
        let kind = 5301
        let tags = []
        tags.push(["param", "max_results", "200"])
        tags.push(["param", "user", store.state.pubkey.toHex()])

        let res;
        let requestid;

        // for now we only want to use encrypted events for subscribed dvms (might change later, also we dont encrypt on amber because decryption and update doesnt work)
        if(current_dvm.encryptionSupported && current_dvm.nip88 && current_dvm.nip88.hasActiveSubscription && localStorage.getItem('nostr-key-method') !== 'android-signer'  && localStorage.getItem('nostr-key-method') !== 'nostr-login'){

             let  tags_str = []
            for (let tag of tags){

               tags_str.push(tag)
            }

            let params_as_str = JSON.stringify(tags_str)
            //console.log(params_as_str)

              let client = store.state.client
              let signer = store.state.signer


              if (localStorage.getItem('nostr-key-method') === 'android-signer') {

                  // let content = await amberSignerService.nip04Encrypt(id, params_as_str)

                   let ttags = []
                     ttags.push(["p", id])
                     ttags.push(["encrypted"])
                     ttags.push(["client", "noogle"])
                  let draft = {
                    content: "",
                    kind: kind,
                    pubkey: store.state.pubkey.toHex(),
                    tags: ttags,
                    createdAt: Date.now()
                  };

                  res = await amberSignerService.signEvent(draft)
                  await client.sendEvent(Event.fromJson(JSON.stringify(res)))
                  requestid = res.id;
                   requestids.push(requestid)
                  store.commit('set_current_request_id_filter', requestids)
                 /* let evtjson = JSON.stringify(res)
                  let evt = Event.fromJson(evtjson)
                  await client.sendEvent(evt) */

              }
              else{
              let pk = PublicKey.parse(id)
              let content = await signer.nip04Encrypt(pk, params_as_str)

              let tags_t = []
              tags_t.push(Tag.parse(["p", id]))
              tags_t.push(Tag.parse(["encrypted"]))
              tags_t.push(Tag.parse(["client", "noogle"]))



                let evt = new EventBuilder(kind, content, tags_t)
                let unsigned =   evt.toUnsignedEvent(store.state.pubkey)
                try{
                      let sign = await client.signer()
                    let signedEvent = await sign.signEvent(unsigned)
                    requestids.push(signedEvent.id.toHex())
                   store.commit('set_current_request_id_filter', requestids)

                   res = await client.sendEvent(signedEvent)
                    }
                catch(e){
                console.log(e)
                }


              }





        }

        else{
           tags.push(["p", id])
             if (localStorage.getItem('nostr-key-method') === 'android-signer') {
          let draft = {
            content: content,
            kind: kind,
            pubkey: store.state.pubkey.toHex(),
            tags: tags,
            createdAt: Date.now()
          };

          res = await amberSignerService.signEvent(draft)
                requestid = res.id;
               requestids.push(requestid)

                store.commit('set_current_request_id_filter', requestids)
          await client.sendEvent(Event.fromJson(JSON.stringify(res)))


        }
             else {

          let tags_t = []
          for (let tag of tags){
            tags_t.push(Tag.parse(tag))
          }
          let evt = new EventBuilder(kind, content, tags_t)
           let unsigned =   evt.toUnsignedEvent(store.state.pubkey)
               let signedEvent = await (await client.signer()).signEvent(unsigned)
               console.log(signedEvent.id.toHex())
               requestids.push(signedEvent.id.toHex())
               store.commit('set_current_request_id_filter', requestids)
               res = await client.sendEvent(signedEvent)

        }

        }





      } catch (error) {
        console.log(error);
      }
}

async function  listen() {
    let client = store.state.client
    let pubkey = store.state.pubkey

    const filter = new Filter().kinds([7000, 6301]).pubkey(pubkey).since(Timestamp.now());
    await client.subscribe([filter]);

    const handle = {
        // Handle event
        handleEvent: async (relayUrl, subscriptionId, event) => {
           let resonsetorequest = false
            //sleep(1200).then(async () => {
              for (let tag in event.tags) {
                if (event.tags[tag].asVec()[0] === "e") {
                  if (store.state.requestidFilter.includes(event.tags[tag].asVec()[1])){
                    resonsetorequest = true

                  }
                }

              }
              if (resonsetorequest === true) {
                if (event.kind === 7000) {
                  try {
                     console.log("7000: ", event.content);
                     console.log("DVM: " + event.author.toHex())
                    //miniToastr.showMessage("DVM: " + dvmname, event.content, VueNotifications.types.info)
                    dvms.find(i => i.id === event.author.toHex()).laststatusid = event.id.toHex()
                    let ob = dvms.find(i => i.id === event.author.toHex())
                    console.log(ob)
                    let is_encrypted = false
                    let ptag = ""

                    console.log(event.content)
                    for (const tag in event.tags) {
                      if (event.tags[tag].asVec()[0] === "encrypted") {
                        is_encrypted = true
                        console.log("encrypted response")
                      }
                      else if (event.tags[tag].asVec()[0] === "p") {
                        ptag = event.tags[tag].asVec()[1]
                      }
                    }

                    if (is_encrypted){
                      let tags_str = ""
                       if (ptag === store.state.pubkey.toHex()){
                            let signer = store.state.signer
                            if (localStorage.getItem('nostr-key-method') === 'android-signer') {
                              return
                             // tags_str = await amberSignerService.nip04Decrypt(event.author.toHex(), event.content)
                            }
                            else{
                                tags_str = await signer.nip04Decrypt(event.author, event.content)
                            }



                            let params = JSON.parse(tags_str)
                            //console.log(params)
                           // params.push(["p", ptag])
                           // params.push(["encrypted"])
                            let event_as_json = JSON.parse(event.asJson())
                            event_as_json['tags'] = params
                           let content = ""
                           for (const tag in params){
                             if (params[tag][0] === "content"){
                               content = params[tag][1]
                             }
                           }
                            event_as_json['content'] = content
                            event = Event.fromJson(JSON.stringify(event_as_json))
                       }
                        else {
                          console.log("not addressed to us")
                          console.log(ptag)

                          return
                        }
                    }


                    for (const tag in event.tags) {
                      if (event.tags[tag].asVec()[0] === "status") {

                           if (event.content !== "" && (event.tags[tag].asVec()[1] === "processing" || event.tags[tag].asVec()[1] === "subscription-required" ) ) {
                              if(event.tags[tag].asVec().length > 2) {
                               dvms.find(i => i.id === event.author.toHex()).status  = event.tags[tag].asVec()[2]
                              }
                              else{
                                dvms.find(i => i.id === event.author.toHex()).status  = event.content
                              }
                           }
                           else{
                               dvms.find(i => i.id === event.author.toHex()).status = event.tags[tag].asVec()[1]

                           }
                     }

                    if (event.tags[tag].asVec()[0] === "subscribed") {
                      if (Timestamp.fromSecs(parseInt(event.tags[tag].asVec()[1])).asSecs() > Timestamp.now().asSecs()) {
                        dvms.find(i => i.id === event.author.toHex()).subscription = event.tags[tag].asVec()[1]
                      }
                    }

                      if (event.tags[tag].asVec()[0] === "amount") {
                        dvms.find(i => i.id === event.author.toHex()).amount = event.tags[tag].asVec()[1]
                        if (event.tags[tag].asVec().length > 2) {
                          dvms.find(i => i.id === event.author.toHex()).bolt11 = event.tags[tag].asVec()[2]
                        } else {
                          let profiles = await get_user_infos([event.author.toHex()])
                          let created = 0
                          if (profiles.length > 0) {
                            console.log(profiles[0].profile)
                            let current = profiles[0]
                            let lud16 = current.profile.lud16
                            if (lud16 !== null && lud16 !== "") {
                              console.log("LUD16: " + lud16)
                              dvms.find(i => i.id === event.author.toHex()).bolt11 = await zaprequest(lud16, dvms.find(i => i.id === event.author.toHex()).amount, "paid from noogle.lol", event.id.toHex(), event.author.toHex(), store.state.relays)
                              //dvms.find(i => i.id === event.author.toHex()).bolt11 = await createBolt11Lud16(lud16, dvms.find(i => i.id === event.author.toHex()).amount)
                              console.log(dvms.find(i => i.id === event.author.toHex()).bolt11)
                              if (dvms.find(i => i.id === event.author.toHex()).bolt11 === "") {
                                dvms.find(i => i.id === event.author.toHex()).status = "error"

                              }
                            } else {
                              console.log("NO LNURL")
                            }

                          } else {
                            console.log("PROFILE NOT FOUND")
                          }
                        }
                      }
                      store.commit('set_filter_dvms', dvms)
                    }
                  } catch (error) {
                    console.log("Error: ", error);
                  }


                }

                else if (event.kind === 6301) {
                  let entries = []
                  console.log("6301:", event.content);
                    let is_encrypted = false
                    let ptag = ""

                    for (const tag in event.tags) {
                      if (event.tags[tag].asVec()[0] === "encrypted") {
                        is_encrypted = true
                        console.log("encrypted reply")
                      }
                      else if (event.tags[tag].asVec()[0] === "p") {
                        ptag = event.tags[tag].asVec()[1]
                      }
                    }

                    let content = event.content

                    if (is_encrypted){
                      if (ptag === store.state.pubkey.toHex()){
                        let signer = store.state.signer
                         //content = await signer.nip04Decrypt(event.author, event.content)
                         if (localStorage.getItem('nostr-key-method') === 'android-signer') {

                              content = await amberSignerService.nip04Decrypt(event.author.toHex(), event.content)
                            }
                            else{
                               content = await signer.nip04Decrypt(event.author, event.content)
                            }
                      }
                      else {
                        console.log("not addressed to us")
                        return
                      }
                    }


                  if (content === "" || content === "[]" || content === "None" ){
                        let items = []
                        dvms.find(i => i.id === event.author.toHex()).result.length = 0
                        dvms.find(i => i.id === event.author.toHex()).result.push.apply(dvms.find(i => i.id === event.author.toHex()).result, items)
                        dvms.find(i => i.id === event.author.toHex()).status = "finished"
                        store.commit('set_filter_dvms', dvms)
                  }
                  else{

                  let event_ptags = JSON.parse(content)
                  if (event_ptags.length > 0) {
                    for (let ptag of event_ptags) {
                      const eventid = ptag[1]
                      entries.push(eventid)
                      //console.log(eventid)
                    }


                      let items = []
                      let index = 0

                      if (entries.length > 0) {

                        try{


                        let profiles = await get_user_infos(entries)


                        for (let profile of profiles){

                          let name = profile === undefined ? "" : profile["profile"]["name"]
                          let picture = profile === undefined ? "../assets/nostr-purple.svg" : profile["profile"]["picture"]

                          let highlighterurl = "https://highlighter.com/e/" + profile["author"]
                          let njumpurl = "https://njump.me/" + PublicKey.parse(profile["author"]).toBech32()
                           let nostrudelurl = "https://nostrudel.ninja/#/n/" + profile["author"]

                        let isnip05valid = false


                         /* let p = profiles.find(record => record.author === evt.author.toHex())
                          let bech32id = evt.id.toBech32()
                          let nip19 = new Nip19Event(evt.id, evt.author, store.state.relays)
                          let nip19bech32 = nip19.toBech32()
                          let picture = p === undefined ? "../assets/nostr-purple.svg" : p["profile"]["picture"]
                          let name = p === undefined ? bech32id : p["profile"]["name"]
                          let authorid = evt.author.toHex()

                          let nostrudelurl = "https://nostrudel.ninja/#/n/" + bech32id
                          let uri = "nostr:" + bech32id //  nip19.toNostrUri()
                          let lud16 = p === undefined ? "" : (p["profile"] === undefined ? "" : p["profile"]["lud16"])
*/

                          if (items.find(e => e.id === profile["author"]) === undefined) {


                            items.push({
                              id: profile["author"],
                              isnip05valid: isnip05valid,
                              event: profile,
                              author: name,
                              authorid: profile["author"],
                              authorurl: "https://njump.me/" + PublicKey.parse(profile["author"]).toBech32(),
                              links: {
                                "highlighter": highlighterurl,
                                "njump": njumpurl,
                                "nostrudel": nostrudelurl
                              },
                              avatar: picture,
                              index: index,
                              indicator: {"time": profile.createdAt.toHumanDatetime(), "index": index},
                              active:  true,
                            })

                            index = index + 1
                          }

                  }


                       /* if (dvms.find(i => i.id === event.author.toHex()) === undefined) {
                          await addDVM(event)
                          console.log("add dvm because of bug")
                        } */


                        dvms.find(i => i.id === event.author.toHex()).result.length = 0
                        dvms.find(i => i.id === event.author.toHex()).result.push.apply(dvms.find(i => i.id === event.author.toHex()).result, items)
                        dvms.find(i => i.id === event.author.toHex()).status = "finished"
                      }
                         catch(error){
                        console.log(error)}
                      }
                     }
                  store.commit('set_filter_dvms', dvms)
                }
}
              }
          //  })
        },
        // Handle relay message
        handleMsg: async (relayUrl, message) => {
            //console.log("Received message from", relayUrl, message.asJson());
        }
    };

    client.handleNotifications(handle);
}

async function isnip05valid(profile){
         let  isnip05valid = false
          if (profile["profile"]["nip05"] !== undefined && profile["profile"]["nip05"] !== ""){
            try{
              let domain = profile["profile"]["nip05"].split('@')[1]
            let user = profile["profile"]["nip05"].split('@')[0]
            let checknip05url = "https://" + domain + "/.well-known/nostr.json?name=" + user
            //console.log(checknip05url)
            let response = await fetch(checknip05url);
            let data = await response.json();
            let usernpub = data.names[user]
              if (usernpub === profile["author"]){
                isnip05valid = true
              }
            }
            catch (error){
              isnip05valid = false
            }

          }

          return isnip05valid

}
async function addAllContentDVMs() {

  let relevant_dvms = []
  for (const el of store.state.nip89dvms) {
    for (const tag of JSON.parse(el.event).tags) {
      if (tag[0] === "k" && tag[1] === "5301") {
        relevant_dvms.push(PublicKey.parse(el.id))
      }
    }
  }
  let active_dvms = []
  for (let id of relevant_dvms) {
    let jsonentry = {
      id: id.toHex(),
      last_active: 0
    }
    active_dvms.push(jsonentry)

  }

  console.log(active_dvms)

  const filtera = new Filter().authors(relevant_dvms).kinds([6301, 7000])
  let client = store.state.client
  let activities = await client.getEventsOf([filtera], Duration.fromSecs(1))


  //let last_active = 0

  for (let activity of activities) {

    //console.log(activity.createdAt.asSecs())
    if (activity.createdAt.asSecs() > active_dvms.find(x => x.id === activity.author.toHex()).last_active) {
      //last_active = activity.createdAt.asSecs()
      active_dvms.find(x => x.id === activity.author.toHex()).last_active = activity.createdAt.asSecs()
    }
  }

  // console.log(last_active)
  // If DVM hasn't been active for 3 weeks, don't consider it.
  //console.log(active_dvms)
  let final_dvms = []
  for (let element of active_dvms) {
    if (element.last_active > Timestamp.now().asSecs() - 60 * 60 * 24 * 21) {
      final_dvms.push(store.state.nip89dvms.find(x => x.id === element.id))
    }

  for (let el of final_dvms){

    let status = "announced"
    let jsonentry = {
      id: el.id,
      kind: "",
      status: status,
      laststatusid: "",
      result: [],
      name: el.name,
      about: el.about,
      image: el.image,
      amount: el.amount,
      encryptionSupported: el.encryptionSupported,
      cashuAccepted: el.cashuAccepted,
      bolt11: "",
      lud16: el.lud16,
      subscription: "",
      nip88: el.nip88,
       action: el.action
    }


    //console.log(jsonentry)
    if (dvms.filter(i => i.id === jsonentry.id).length === 0) {
      dvms.push(jsonentry)
    }
  }

  store.commit('set_filter_dvms', dvms)
  }

}

async function addDVM(event){
  let status = "unknown"
  let jsonentry = {
    id: event.author.toHex(),
    kind: "",
    status: status,
    result: [],
    name: event.author.toBech32(),
    about: "",
    image: "",
    amount: 0,
    bolt11: "",
    lud16: "",
    subscription: "",
    encryptionSupported: false,
    cashuAccepted: false
  }

  for (const tag in event.tags) {
    if (event.tags[tag].asVec()[0] === "status") {
      status = event.tags[tag].asVec()[1]
    }

    if (event.tags[tag].asVec()[0] === "amount") {
      jsonentry.amount = event.tags[tag].asVec()[1]
      if (event.tags[tag].asVec().length > 2) {
        jsonentry.bolt11 = event.tags[tag].asVec()[2]
      }
        else{
          let profiles = await get_user_infos([event.author.toHex()])
         let created = 0
          if (profiles.length > 0){
           // for (const profile of profiles){
              console.log(profiles[0].profile)
            let current = profiles[0]
            let lud16 = current.profile.lud16
            if (lud16 !== null && lud16 !== ""){
              console.log("LUD16: " +  lud16)
              jsonentry.bolt11 = await createBolt11Lud16(lud16, jsonentry.amount)
              console.log(jsonentry.bolt11)
              if(jsonentry.bolt11 === ""){
               status = "error"
              }
          }
            else {
              console.log("NO LNURL")
            }

        }

          else {
            console.log("PROFILE NOT FOUND")
          }
      }
    }
  }

  //let dvm = store.state.nip89dvms.find(x => JSON.parse(x.event).pubkey === event.author.toHex())
  for (const el of store.state.nip89dvms) {
    if (JSON.parse(el.event).pubkey === event.author.toHex()) {
      jsonentry.name = el.name
      jsonentry.about = el.about
      jsonentry.image = el.image
      jsonentry.lud16 = el.lud16
     jsonentry.encryptionSupported = el.encryptionSupported
     jsonentry.cashuAccepted = el.cashuAccepted
       jsonentry.action = el.action

      console.log(jsonentry)

    }
  }


   if (event.content !== "" && status !== "payment-required" &&  status !== "error" &&  status !== "finished" &&  status !== "paid"){
    status = event.content
  }

  console.log(dvms)
  if (dvms.filter(i => i.id === jsonentry.id).length === 0) {
       dvms.push(jsonentry)
  }


  //dvms.find(i => i.id === jsonentry.id).status = status
  store.commit('set_filter_dvms', dvms)

}

async function cancelSubscription(kind7001, recipent){
        console.log(kind7001)
        console.log(recipent)
        let client = store.state.client
        let res;
        let requestid;
        let content = "Canceled from Noogle"
        let kind = 7002
        let tags = [
              ["p", recipent],
              ["e", kind7001]
            ]

       if (localStorage.getItem('nostr-key-method') === 'android-signer') {
          let draft = {
            content: content,
            kind: kind,
            pubkey: store.state.pubkey.toHex(),
            tags: tags,
            createdAt: Date.now()
          };

          res = await amberSignerService.signEvent(draft)
          await client.sendEvent(Event.fromJson(JSON.stringify(res)))
          requestid = res.id;
          console.log(requestid)
       }
       else{
          let tags_t = []
          for (let tag of tags){
              tags_t.push(Tag.parse(tag))
          }
          let evt = new EventBuilder(kind, content, tags_t)
          res = await client.sendEventBuilder(evt);
          requestid = res.toHex();
          console.log(requestid)

       }

       dvms.find(x => x.nip88.eventid === current_subscription_dvm.value.nip88.eventid).nip88.hasActiveSubscription = true
       dvms.find(x => x.nip88.eventid === current_subscription_dvm.value.nip88.eventid).nip88.expires = true
}

async function subscribe_to_dvm() {

  if (!localStorage.getItem("nostr-key-method") || localStorage.getItem("nostr-key-method") === "anon"){
    miniToastr.showMessage("Login to subscribe to a DVM.", "Not logged in", "error")
    return
  }

  // We only arrive here if no subscription exists, we might create a 7001 if it doesnt exist and we zap it

  let client = store.state.client
  dvms.find(x => x.nip88.eventid === current_subscription_dvm.value.nip88.eventid).status = "Subscribing, this might take up to a minute.."
  store.commit('set_filter_dvms', dvms)


if (current_subscription_dvm.value.nip88.subscriptionId === '' || !current_subscription_dvm.value.nip88.subscriptionId  ) {

  let res;
  let requestid;
  let kind = 7001
  let content = "Subscription from noogle.lol"


  let tags = [
    ["p", current_subscription_dvm.value.id],
    ["e", current_subscription_dvm.value.nip88.eventid],
    ["event", JSON.stringify(current_subscription_dvm.value.nip88.event)],
    ["amount", (current_subscription_amount.value).toString(), "msats", current_subscription_cadence.value],
  ]
  for (let zap of current_subscription_dvm.value.nip88.zaps) {
    console.log(zap.key + " " + zap.split)
    if(zap.key === ""){
      //if Tier allows an empty key, the client might add itself for the zap share here
      zap.key = Keys.parse(store.state.nooglekey).publicKey.toHex()
    }
    let zaptag = ["zap", zap.key, zap.split]
    tags.push(zaptag)
  }

  console.log("Creating 7001 event")
  if (localStorage.getItem('nostr-key-method') === 'android-signer') {
    let draft = {
      content: content,
      kind: kind,
      pubkey: store.state.pubkey.toHex(),
      tags: tags,
      createdAt: Date.now()
    };

    res = await amberSignerService.signEvent(draft)
    await client.sendEvent(Event.fromJson(JSON.stringify(res)))
    requestid = res.id;
    console.log(requestid)

  } else {
    let tags_t = []
    for (let tag of tags) {
      tags_t.push(Tag.parse(tag))
    }
    let evt = new EventBuilder(kind, content, tags_t)
    res = await client.sendEventBuilder(evt);
    requestid = res.toHex()
    console.log(res)
  }

  current_subscription_dvm.value.nip88.subscriptionId = requestid
  console.log(current_subscription_dvm.value.nip88.subscriptionId)

}

  try{
      let nwcdvm = PublicKey.parse(store.state.subscription_verifier_pubkey)
    let key = Keys.parse(store.state.nooglekey)
      console.log(key.publicKey.toHex())
      let nsigner = NostrSigner.keys(key)
      let nclient = new Client(nsigner)

       for (const relay of store.state.relays) {
        await nclient.addRelay(relay)
      }
       await nclient.connect()

      let tags_str = []
      let nwctag = Tag.parse(["param", "nwc", current_subscription_nwc.value])
      tags_str.push(nwctag.asVec())

      let ptag = Tag.parse(["param", "p", store.state.pubkey.toHex()])
      tags_str.push(ptag.asVec())
      let tags_as_str = JSON.stringify(tags_str)

    try{

       let msg =  await (await nclient.signer()).nip04Encrypt(nwcdvm, tags_as_str)
        let tags_t = []
        tags_t.push(Tag.parse(["p", store.state.subscription_verifier_pubkey]))
        tags_t.push(Tag.parse(["encrypted"]))
        tags_t.push(Tag.parse(["client", "noogle"]))
        let evt = new EventBuilder(5906, msg, tags_t)
        console.log(evt)
        let res = await nclient.sendEventBuilder(evt);
           }
    catch (e){
        console.log(e)
    }



      let isSubscribed = false
     let timeout = 0
     let subscription_status
      while (!isSubscribed && timeout < 30){
         dvms.find(x => x.nip88.eventid === current_subscription_dvm.value.nip88.eventid).status = "Subscribing, please wait.."
         await sleep(5000)
         timeout = timeout +1
        subscription_status = await hasActiveSubscription(store.state.pubkey.toHex(), current_subscription_dvm.value.nip88.d, current_subscription_dvm.value.id)
         if (subscription_status["isActive"] === true){
           isSubscribed = true
           dvms.find(x => x.nip88.eventid === current_subscription_dvm.value.nip88.eventid).status = "announced"
         }
      }
      console.log(subscription_status)


       dvms.find(x => x.nip88.eventid === current_subscription_dvm.value.nip88.eventid).nip88.hasActiveSubscription = subscription_status["isActive"]
       dvms.find(x => x.nip88.eventid === current_subscription_dvm.value.nip88.eventid).nip88.expires = false
       dvms.find(x => x.nip88.eventid === current_subscription_dvm.value.nip88.eventid).nip88.subscribedUntil = subscription_status.validUntil


       if (subscription_status["isActive"] === false){
          dvms.find(x => x.nip88.eventid === current_subscription_dvm.value.nip88.eventid).status  = "Timeout, please refresh the page"

       }
    store.commit('set_filter_dvms', dvms)

  }
  catch(error){
      console.log(error)
  }

}

async function zap_local(invoice) {

  let success = await zap(invoice)
  if (success){
    dvms.find(i => i.bolt11 === invoice).status = "paid"
    store.commit('set_filter_dvms', dvms)
  }

}

async function mute_all(results){
  console.log(results)
      let client = store.state.client
    let signer = store.state.signer
    let publicKey = store.state.pubkey

    let mute_filter = new Filter().author(publicKey).kind(10000)
    let mutes = await client.getEventsOf([mute_filter], Duration.fromSecs(5))
    console.log(mutes.length)
    if (mutes.length > 0) {
       let list = mutes[0]
       let id = list.id.toHex()
         try {
            let eventasjson = JSON.parse(list.asJson())
            let content = await (await signer).nip04Decrypt(store.state.pubkey, list.content)
            let jsonObject = JSON.parse(content)
            console.log(content)

           for (let result of results){
          console.log(result)

            let exists = false
            for(let i = 0; i < jsonObject.length; i++)
              {
                if(jsonObject[i][1] === result.authorid)
                {
                 exists = true
                  break;
                }
              }
            if (exists){
             console.log("already muted")
            }
            else{

                jsonObject.push(["p", result.authorid])
                store.state.mutes.push(result.authorid)



              }
            }

             let newcontent = JSON.stringify(jsonObject)
                console.log(newcontent)
                let lol = "[]"
                eventasjson.content = await (await signer).nip04Encrypt(store.state.pubkey, newcontent)
                let newList = new EventBuilder(list.kind, eventasjson.content, list.tags).toUnsignedEvent(store.state.pubkey)

                 try{
                      let signedMuteList = await signer.signEvent(newList)
                      //console.log(signedMuteList.asJson())
                      await client.sendEvent(signedMuteList)
                 }
                 catch (error){
                    console.log("Inner " + error)
                 }

          }
        catch(error){
          console.log(error)
        }
    }
    else{
      // TODO make new mute list
    }


}

async function mute(result) {
    let client = store.state.client
    let signer = store.state.signer
    let publicKey = store.state.pubkey

    let mute_filter = new Filter().author(publicKey).kind(10000)
    let mutes = await client.getEventsOf([mute_filter], Duration.fromSecs(5))
    console.log(mutes.length)
    if (mutes.length > 0) {
       let list = mutes[0]
       let content = ""
         try {
            let eventasjson = JSON.parse(list.asJson())
           try{
            //  console.log(list.content)
            let signer = await store.state.signer
           content = await signer.nip04Decrypt(store.state.pubkey, list.content)
               //    console.log(content)

           }
           catch(error){
              console.log(error)
           }

             let jsonObject = JSON.parse(content)
            let exists = false
            for(let i = 0; i < jsonObject.length; i++)
              {
                if(jsonObject[i][1] === result.authorid)
                {
                 exists = true
                }
              }
            if (exists){
             console.log("already muted")
            }
            else{

                jsonObject.push(["p", result.authorid])
                store.state.mutes.push(result.authorid)
                let newcontent = JSON.stringify(jsonObject)
                console.log(newcontent)
                eventasjson.content = await store.state.signer.nip04Encrypt(store.state.pubkey, newcontent)
                let newList = new EventBuilder(list.kind, eventasjson.content, list.tags).toUnsignedEvent(store.state.pubkey)

                 try{
                      let signedMuteList = await signer.signEvent(newList)
                      //console.log(signedMuteList.asJson())
                      await client.sendEvent(signedMuteList)
                 }
                 catch (error){
                    console.log("Inner " + error)
                 }
              }
          }
        catch(error){
          console.log(error)
        }
    }
    else{
      // TODO make new mute list
    }



}

async function unfollow(result){
  let client = store.state.client
  console.log(result.authorid)
  let found = false
  let element
  for (let em of store.state.contacts){
    if (em.publicKey.toHex() === result.authorid){
      found = true
      element = em
      break
    }

  }
 // let element  = store.state.contacts.find(x => x.publicKey.toHex() === result.authorid)

  if (found){

  console.log(element)
  let index =  store.state.contacts.indexOf(element)
  console.log(index)
  console.log(store.state.contacts.length)

  let rm =  store.state.contacts.splice(index, 1)


  let list = store.state.contacts
  let event = EventBuilder.contactList(list)
  let requestid = await client.sendEventBuilder(event);

  console.log("unfollow logic for "  + result.event.profile.name)
    return true
     }
  else {
    console.log("not found")
    return false
  }
}

async  function store_nwc(){

  if (nwcalby.value.startsWith("nostr")){

    current_subscription_nwc.value  = nwcalby.value
  }
  else if (nwcmutiny.value.startsWith("nostr") ){

    current_subscription_nwc.value  = nwcmutiny.value
  }
  else{

    current_subscription_nwc.value  = nwc.value
  }

}
async function connect_alby_nwc(dvm_name){

const alby = webln.NostrWebLNProvider.withNewSecret();
let result = await alby.client.initNWC({
        name: dvm_name,
      });

 if (result.payload.success){
   nwcalby.value =  alby.client.getNostrWalletConnectUrl(true);
   await store_nwc()
 }
}


defineProps({
  msg: {
    type: String,
    required: false
  },
})






const isModalOpened = ref(false);
const isNWCModalOpened = ref(false);
const modalcontent = ref("");
const nwcmodalcontent = ref("");
const datetopost = ref(Date.now());

const nwc = ref("");
const nwcmutiny = ref("");
const nwcalby= ref("");
const current_subscription_amount = ref(0)
const current_subscription_cadence = ref("")
const current_subscription_dvm = ref(null)
const current_subscription_nwc = ref("")


const openModal = result => {
  datetopost.value = Date.now();
  isModalOpened.value = true;
  modalcontent.value = result
};
const closeModal = () => {
  isModalOpened.value = false;
};

function openNWCModal(zaps, amount, cadence, subscriptionId, evt, eventid, id, p){
  isNWCModalOpened.value = true;
  nwcmodalcontent.value = result
};
const closeNWCModal = () => {
  isNWCModalOpened.value = false;
};

const submitHandler = async () => {
}







</script>

<!--  font-thin bg-gradient-to-r from-white to-nostr bg-clip-text text-transparent -->

<template>

  <div class="greetings">
   <br>
    <br>
    <h1 class="text-7xl font-black tracking-wide">Nostr</h1>
    <h1 class="text-7xl font-black tracking-wide">Profile Filters</h1>
    <!--<h1 class="text-7xl font-black tracking-wide">Filter</h1> -->

    <h2 class="text-base-200-content text-center tracking-wide text-2xl font-thin ">
    Curate your feed with pubkeys you love. And nothing else.</h2>
     <br>
    <div style="text-align: center"  v-if="store.state.filterdvms.length === 0">
          <button  class="v-Button">Loading DVMs <span class="loading loading-infinity loading-md"></span>


    </button>
          </div>
  </div>
  <br>

   <ModalComponent  :isOpen="isModalOpened" @modal-close="closeModal" @submit="submitHandler" name="first-modal">
        <template #header>Summarize Results <br></template>
        <template #content>
          <SummarizationGeneration :events="modalcontent"></SummarizationGeneration>
        </template>
        <template #footer>
        </template>
   </ModalComponent>

  <div class=" relative space-y-3">
    <div class="grid grid-cols-1 gap-6">
        <div className="card w-70 bg-base-100 shadow-xl flex flex-col"   v-for="dvm in dvms"
            :key="dvm.id">
          <div className="card-body">
            <div className="playeauthor-wrapper">
              <figure  className="w-28">
                   <img className="avatar"  v-if="dvm.image" :src="dvm.image"  alt="DVM Picture" />
                   <img class="avatar" v-else src="@/assets/nostr-purple.svg" />
              </figure>
              <h2 className="card-title">{{ dvm.name }}</h2>

              </div>
            <h3 class="fa-cut" v-html="StringUtil.parseHyperlinks(dvm.about)"></h3>
            <div className="card-actions justify-end mt-auto"  >
              <div className="tooltip mt-auto" style="border-width: 0" >


                 <button v-if="dvm.status !== 'finished' && dvm.status !== 'paid' && dvm.status !== 'payment-required' && dvm.status !== 'subscription-required' && dvm.status !== 'subscription-success' && dvm.status !== 'error' && dvm.status !== 'announced'" className="btn">{{dvm.status}}</button>
                  <button v-if="(dvm.status === 'finished'  && !dvm.nip88) || (dvm.status === 'finished' && dvm.nip88 && !dvm.nip88.hasActiveSubscription)" @click="generate_feed(dvm.id)" class="relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-purple-600 to-blue-500 group-hover:from-purple-600 group-hover:to-blue-500 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-blue-300 dark:focus:ring-blue-800">
                  <span class="relative px-5 py-2.5 transition-all ease-in duration-75 bg-white dark:bg-gray-900 rounded-md group-hover:bg-opacity-0">
                  Done, again?
                  </span>
                  </button>
                    <button v-if="dvm.status === 'finished'  && dvm.nip88 && dvm.nip88.hasActiveSubscription" @click="generate_feed(dvm.id);" class="relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-pink-500 to-orange-400 group-hover:from-pink-500 group-hover:to-orange-400 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-pink-200 dark:focus:ring-pink-800">
                  <span class="relative px-5 py-2.5 transition-all ease-in duration-75 bg-white dark:bg-gray-900 rounded-md group-hover:bg-opacity-0">
                  Done, Again?
                  </span>
                  </button>


                  <button v-if="dvm.status === 'paid'" className="btn">Paid, waiting for DVM..</button>
                  <button v-if="dvm.status === 'error'" className="btn">Error</button>

                  <button v-if="dvm.status === 'payment-required'" className="zap-Button" @click="zap_local(dvm.bolt11);">{{ dvm.amount/1000 }} Sats</button>
                  <h3 v-if="dvm.status === 'subscription-required'" className="sub-Button" >Subscription required</h3>


                  <button v-if="dvm.status === 'subscription-success'" className="sub-Button"  @click="generate_feed(dvm.id);">Subscribed. Request job</button>

                 <!-- <button v-if="dvm.status === 'announced'" className="request-Button" @click="generate_feed(dvm.id);">Request</button> -->
                  <button v-if="(dvm.status === 'announced' && !dvm.nip88)" @click="generate_feed(dvm.id);" class="relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-purple-600 to-blue-500 group-hover:from-purple-600 group-hover:to-blue-500 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-blue-300 dark:focus:ring-blue-800">
                  <span class="relative px-5 py-2.5 transition-all ease-in duration-75 bg-white dark:bg-gray-900 rounded-md group-hover:bg-opacity-0">
                  Request
                  </span>
                  </button>

                  <button v-if="dvm.status === 'announced'  && dvm.nip88 && dvm.nip88.hasActiveSubscription" @click="generate_feed(dvm.id);" class="relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-pink-500 to-orange-400 group-hover:from-pink-500 group-hover:to-orange-400 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-pink-200 dark:focus:ring-pink-800">
              <span class="relative px-5 py-2.5 transition-all ease-in duration-75 bg-white dark:bg-gray-900 rounded-md group-hover:bg-opacity-0">
                  Request
                  </span>
                  </button>

                    <button v-if="dvm.status === 'announced'  && dvm.nip88 && !dvm.nip88.hasActiveSubscription"  onclick='subscr.showModal()' class="relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-pink-500 to-orange-400 group-hover:from-pink-500 group-hover:to-orange-400 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-pink-200 dark:focus:ring-pink-800">
                      <span class="relative px-5 py-2.5 transition-all ease-in duration-75 bg-white dark:bg-gray-900 rounded-md group-hover:bg-opacity-0">Subscription
                      </span>
                 </button>

         



               <!--<h3 v-if="dvm.amount.toString().toLowerCase()==='free'" class="bg-nostr btn rounded-full" >{{ "Free" }}</h3> -->


            </div>
            </div>
            <div style="margin-left: auto; margin-right: 3px;">
       <p v-if="!dvm.subscription && dvm.amount.toString().toLowerCase()==='free'" class="badge bg-nostr" >Free</p>
        <p v-if="!dvm.subscription && dvm.amount.toString().toLowerCase()==='flexible'" class="badge bg-nostr2" >Flexible</p>


       <!-- <p v-if="dvm.nip88 && !dvm.nip88.hasActiveSubscription" class="badge text-white bg-gradient-to-br from-pink-500 to-orange-400"  onclick='subscr.showModal()' >Subscription</p> -->

                 <div class="flex">
                   <div class="tooltip" style="border-width: 0">
                       <svg v-if="dvm.encryptionSupported && dvm.nip88" style="margin-left: auto; margin-right: 5px" class="w-4 h-4 text-gray-800 dark:text-white flex" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 22 22">
                            <path d="M18 10v-4c0-3.313-2.687-6-6-6s-6 2.687-6 6v4h-3v14h18v-14h-3zm-5 7.723v2.277h-2v-2.277c-.595-.347-1-.984-1-1.723 0-1.104.896-2 2-2s2 .896 2 2c0 .738-.404 1.376-1 1.723zm-5-7.723v-4c0-2.206 1.794-4 4-4 2.205 0 4 1.794 4 4v4h-8z"/>
                       </svg>
                  <span class="tooltiptext">This DVM uses encrypted communication. Only the DVM can see your request, and only you can see the results. <br> Currently not encrypted when using Amber Signer.</span>
                </div>
                  <button v-if="dvm.nip88 && dvm.nip88.hasActiveSubscription"  onclick='subscr.showModal()' class=" badge relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-pink-500 to-orange-400 group-hover:from-pink-500 group-hover:to-orange-400 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-pink-200 dark:focus:ring-pink-800">
                                  <span class="relative px-5 py-2.5 transition-all ease-in duration-75  rounded-md group-hover:bg-opacity-0">
                                   Subscription</span>
                 </button>


                </div>
        </div>
            <div>
              <div class="playeauthor-wrapper" v-if="dvm.nip88">


                <dialog id="nwc_modal" class="modal">
                  <div class="modal-box rounded-2xl inner shadow-lg p-6 flex flex-col items-center transition-all duration-1000 bg-base-600/60  ">
                <h3 class="font-bold text-lg">Connect with Nostr Wallet Connect</h3>
                <br>
                  <div class="flex">
                      <img class="avatar"  :src="dvm.nip88.image" alt="" />
                    <h3 class="text-lg">{{dvm.nip88.title}}</h3>
                  </div>
                <div>
                   <p  class="py-4">Enter a Nostr Wallet connect to subscribe</p>
                <div class="collapse bg-base-200">
                <input type="radio" name="my-accordion-1" />
                <div class="collapse-title text-xl font-medium bg-black/30 flex">
                    <img  class="w-12 h-12 mask mask-squircle bg-zinc-700" style="width: 46px; height: 46px" src="/Alby.jpg"/>
                   <div style="margin-left: 30px">
                         <h3>Alby NWC</h3>

                         <h3 class="text-sm text-neutral">Connect with your Alby Wallet</h3>
                       </div>

                </div>
                  <div class="collapse-content">
                          <button v-if="!nwcalby.startsWith('nostr')" style="margin-top: 20px;" @click="connect_alby_nwc(dvm.nip88.title)">
                          <svg width="211" height="40" viewBox="0 0 211 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <rect x="0.5" width="210" height="40" rx="6" fill="url(#paint0_linear_1_148)"/>
                          <circle cx="1.575" cy="1.575" r="1.575" transform="matrix(-1 0 0 1 22.1176 13.8575)" fill="black"/>
                          <path d="M20.28 15.1963L23.22 18.1363" stroke="black" stroke-width="0.7875"/>
                          <circle cx="33.405" cy="15.4325" r="1.575" fill="black"/>
                          <path d="M33.6938 15.1963L30.7538 18.1363" stroke="black" stroke-width="0.7875"/>
                          <path fill-rule="evenodd" clip-rule="evenodd" d="M20.9896 24.831C20.1407 24.4269 19.6467 23.5194 19.8122 22.5939C20.5225 18.6217 23.4825 15.6425 27.0263 15.6425C30.5786 15.6425 33.5444 18.6362 34.2455 22.6228C34.4085 23.5499 33.9105 24.457 33.0587 24.8578C31.2361 25.7155 29.2003 26.195 27.0525 26.195C24.8824 26.195 22.8267 25.7055 20.9896 24.831Z" fill="#FFDF6F"/>
                          <path d="M34.2455 22.6228L33.8577 22.691L34.2455 22.6228ZM33.0587 24.8578L32.8911 24.5016L33.0587 24.8578ZM20.9896 24.831L21.1588 24.4754L20.9896 24.831ZM20.1998 22.6632C20.8861 18.825 23.7231 16.0362 27.0263 16.0362V15.2487C23.242 15.2487 20.1588 18.4184 19.4246 22.5246L20.1998 22.6632ZM27.0263 16.0362C30.3374 16.0362 33.1802 18.8386 33.8577 22.691L34.6333 22.5546C33.9086 18.4337 30.8198 15.2487 27.0263 15.2487V16.0362ZM32.8911 24.5016C31.1198 25.3351 29.1411 25.8012 27.0525 25.8012V26.5887C29.2595 26.5887 31.3524 26.096 33.2264 25.2141L32.8911 24.5016ZM27.0525 25.8012C24.9422 25.8012 22.9442 25.3254 21.1588 24.4754L20.8203 25.1865C22.7092 26.0857 24.8226 26.5887 27.0525 26.5887V25.8012ZM33.8577 22.691C33.9884 23.4343 33.5904 24.1725 32.8911 24.5016L33.2264 25.2141C34.2306 24.7415 34.8287 23.6655 34.6333 22.5546L33.8577 22.691ZM19.4246 22.5246C19.2263 23.6336 19.8196 24.7101 20.8203 25.1865L21.1588 24.4754C20.4618 24.1436 20.0671 23.4052 20.1998 22.6632L19.4246 22.5246Z" fill="black"/>
                          <path fill-rule="evenodd" clip-rule="evenodd" d="M22.5042 23.8434C21.8209 23.5652 21.4155 22.8381 21.6523 22.1394C22.3825 19.9844 24.5124 18.425 27.0263 18.425C29.5401 18.425 31.67 19.9844 32.4002 22.1394C32.637 22.8381 32.2317 23.5652 31.5484 23.8434C30.1528 24.4118 28.6261 24.725 27.0263 24.725C25.4264 24.725 23.8997 24.4118 22.5042 23.8434Z" fill="black"/>
                          <ellipse cx="28.8375" cy="21.785" rx="1.3125" ry="1.05" fill="white"/>
                          <ellipse cx="25.0802" cy="21.7856" rx="1.3125" ry="1.05" fill="white"/>
                          <path d="M55.5064 18.1477C55.1712 18.1477 54.9893 17.983 54.87 17.6648C54.4325 16.4659 53.3018 15.8068 51.9893 15.8068C49.9837 15.8068 48.4837 17.358 48.4837 20.1818C48.4837 23.0284 49.9893 24.5568 51.9837 24.5568C53.2905 24.5568 54.4155 23.9148 54.87 22.733C54.9893 22.4091 55.1712 22.25 55.5064 22.25H56.1371C56.5348 22.25 56.7507 22.4943 56.6314 22.8807C56.0405 24.8409 54.2905 26.1591 51.9723 26.1591C48.9496 26.1591 46.7393 23.9034 46.7393 20.1818C46.7393 16.4602 48.9609 14.2045 51.9723 14.2045C54.2166 14.2045 56.0348 15.4148 56.6371 17.517C56.7507 17.9091 56.5348 18.1477 56.1371 18.1477H55.5064ZM62.4197 26.1761C59.9595 26.1761 58.3516 24.375 58.3516 21.6761C58.3516 18.9602 59.9595 17.1591 62.4197 17.1591C64.88 17.1591 66.4879 18.9602 66.4879 21.6761C66.4879 24.375 64.88 26.1761 62.4197 26.1761ZM60.0675 21.6705C60.0675 23.3466 60.8175 24.75 62.4254 24.75C64.022 24.75 64.772 23.3466 64.772 21.6705C64.772 20 64.022 18.5795 62.4254 18.5795C60.8175 18.5795 60.0675 20 60.0675 21.6705ZM70.0831 25.4318C70.0831 25.8011 69.8842 26 69.5149 26H68.9524C68.5831 26 68.3842 25.8011 68.3842 25.4318V17.8409C68.3842 17.4716 68.5831 17.2727 68.9524 17.2727H69.4467C69.8161 17.2727 70.0149 17.4716 70.0149 17.8409V18.6932H70.1229C70.5263 17.767 71.3842 17.1591 72.6967 17.1591C74.4808 17.1591 75.6683 18.2898 75.6683 20.4489V25.4318C75.6683 25.8011 75.4695 26 75.1001 26H74.5376C74.1683 26 73.9695 25.8011 73.9695 25.4318V20.6534C73.9695 19.3864 73.2706 18.6307 72.1172 18.6307C70.9354 18.6307 70.0831 19.4261 70.0831 20.8182V25.4318ZM79.6456 25.4318C79.6456 25.8011 79.4467 26 79.0774 26H78.5149C78.1456 26 77.9467 25.8011 77.9467 25.4318V17.8409C77.9467 17.4716 78.1456 17.2727 78.5149 17.2727H79.0092C79.3786 17.2727 79.5774 17.4716 79.5774 17.8409V18.6932H79.6854C80.0888 17.767 80.9467 17.1591 82.2592 17.1591C84.0433 17.1591 85.2308 18.2898 85.2308 20.4489V25.4318C85.2308 25.8011 85.032 26 84.6626 26H84.1001C83.7308 26 83.532 25.8011 83.532 25.4318V20.6534C83.532 19.3864 82.8331 18.6307 81.6797 18.6307C80.4979 18.6307 79.6456 19.4261 79.6456 20.8182V25.4318ZM91.2706 26.1761C88.6967 26.1761 87.1172 24.4034 87.1172 21.6932C87.1172 19.0114 88.7195 17.1591 91.1513 17.1591C93.1286 17.1591 95.0149 18.392 95.0149 21.5455V21.5795C95.0149 21.9489 94.8161 22.1477 94.4467 22.1477H88.8104C88.8558 23.8295 89.8331 24.7727 91.2876 24.7727C92.0661 24.7727 92.6967 24.5 93.0717 23.9659C93.2649 23.6818 93.4581 23.5511 93.7876 23.6136L94.2876 23.7045C94.674 23.7784 94.8672 24 94.7365 24.2898C94.2024 25.4432 92.9524 26.1761 91.2706 26.1761ZM88.8161 20.875H93.3501C93.3445 19.5398 92.4808 18.5625 91.1626 18.5625C89.782 18.5625 88.8842 19.6364 88.8161 20.875ZM100.576 26.1761C98.0419 26.1761 96.5078 24.3068 96.5078 21.6761C96.5078 19.0114 98.0987 17.1591 100.559 17.1591C102.298 17.1591 103.621 18.0625 104.042 19.4716C104.15 19.8523 103.923 20.0909 103.531 20.0909H102.996C102.667 20.0909 102.491 19.9375 102.349 19.6307C102.053 19.0341 101.457 18.5909 100.587 18.5909C99.1669 18.5909 98.2237 19.767 98.2237 21.6364C98.2237 23.5398 99.1499 24.7386 100.587 24.7386C101.388 24.7386 102.025 24.3636 102.349 23.6989C102.491 23.3977 102.667 23.2386 102.996 23.2386H103.531C103.923 23.2386 104.15 23.4375 104.059 23.767C103.678 25.1875 102.417 26.1761 100.576 26.1761ZM110.052 18.0682C110.052 18.4375 109.853 18.6364 109.484 18.6364H108.262V23.4375C108.262 24.4205 108.756 24.6023 109.308 24.6023H109.364C109.722 24.5909 109.944 24.7102 110.018 25.0625L110.092 25.3864C110.171 25.7386 110.035 26.0114 109.671 26.0682C109.512 26.0909 109.325 26.1136 109.109 26.1136C107.768 26.142 106.558 25.375 106.563 23.7898V18.6364H105.853C105.484 18.6364 105.285 18.4375 105.285 18.0682V17.8409C105.285 17.4716 105.484 17.2727 105.853 17.2727H106.563V15.75C106.563 15.3807 106.762 15.1818 107.131 15.1818H107.694C108.063 15.1818 108.262 15.3807 108.262 15.75V17.2727H109.484C109.853 17.2727 110.052 17.4716 110.052 17.8409V18.0682ZM115.677 17.9148C115.563 17.5227 115.745 17.2727 116.154 17.2727H116.745C117.08 17.2727 117.29 17.4318 117.376 17.7557L118.955 23.6818H119.04L120.626 17.7557C120.711 17.4261 120.921 17.2727 121.256 17.2727H122.012C122.347 17.2727 122.558 17.4318 122.643 17.7557L124.217 23.6534H124.302L125.87 17.7557C125.955 17.4318 126.165 17.2727 126.501 17.2727H127.092C127.501 17.2727 127.683 17.517 127.569 17.9148L125.336 25.5227C125.239 25.8409 125.035 26 124.7 26H123.961C123.626 26 123.415 25.8466 123.325 25.517L121.688 19.6989H121.558L119.921 25.517C119.83 25.8466 119.62 26 119.285 26H118.552C118.217 26 118.012 25.8409 117.915 25.5227L115.677 17.9148ZM130.227 15.9261C129.636 15.9261 129.153 15.4716 129.153 14.9148C129.153 14.358 129.636 13.8977 130.227 13.8977C130.812 13.8977 131.3 14.358 131.3 14.9148C131.3 15.4716 130.812 15.9261 130.227 15.9261ZM129.369 25.4318V17.8409C129.369 17.4716 129.567 17.2727 129.937 17.2727H130.499C130.869 17.2727 131.067 17.4716 131.067 17.8409V25.4318C131.067 25.8011 130.869 26 130.499 26H129.937C129.567 26 129.369 25.8011 129.369 25.4318ZM137.427 18.0682C137.427 18.4375 137.228 18.6364 136.859 18.6364H135.637V23.4375C135.637 24.4205 136.131 24.6023 136.683 24.6023H136.739C137.097 24.5909 137.319 24.7102 137.393 25.0625L137.467 25.3864C137.546 25.7386 137.41 26.0114 137.046 26.0682C136.887 26.0909 136.7 26.1136 136.484 26.1136C135.143 26.142 133.933 25.375 133.938 23.7898V18.6364H133.228C132.859 18.6364 132.66 18.4375 132.66 18.0682V17.8409C132.66 17.4716 132.859 17.2727 133.228 17.2727H133.938V15.75C133.938 15.3807 134.137 15.1818 134.506 15.1818H135.069C135.438 15.1818 135.637 15.3807 135.637 15.75V17.2727H136.859C137.228 17.2727 137.427 17.4716 137.427 17.8409V18.0682ZM141.192 25.4318C141.192 25.8011 140.994 26 140.624 26H140.062C139.692 26 139.494 25.8011 139.494 25.4318V14.9318C139.494 14.5625 139.692 14.3636 140.062 14.3636H140.602C140.971 14.3636 141.17 14.5625 141.17 14.9318V18.6932H141.278C141.687 17.75 142.505 17.1591 143.863 17.1591C145.658 17.1591 146.852 18.2727 146.852 20.4489V25.4318C146.852 25.8011 146.653 26 146.283 26H145.721C145.352 26 145.153 25.8011 145.153 25.4318V20.6534C145.153 19.375 144.454 18.6307 143.283 18.6307C142.073 18.6307 141.192 19.4261 141.192 20.8182V25.4318ZM153.302 26C152.881 26 152.7 25.7386 152.842 25.3466L156.631 14.8182C156.745 14.5114 156.95 14.3636 157.279 14.3636H158.342C158.671 14.3636 158.876 14.5114 158.989 14.8182L162.779 25.3466C162.921 25.7386 162.739 26 162.319 26H161.637C161.308 26 161.097 25.858 160.989 25.5398L160.086 22.9205H155.54L154.631 25.5398C154.523 25.8523 154.313 26 153.984 26H153.302ZM156.052 21.4432H159.575L157.859 16.4773H157.768L156.052 21.4432ZM166.255 25.4318C166.255 25.8011 166.056 26 165.687 26H165.124C164.755 26 164.556 25.8011 164.556 25.4318V14.9318C164.556 14.5625 164.755 14.3636 165.124 14.3636H165.687C166.056 14.3636 166.255 14.5625 166.255 14.9318V25.4318ZM168.677 14.9318C168.677 14.5625 168.876 14.3636 169.245 14.3636H169.808C170.177 14.3636 170.376 14.5625 170.376 14.9318V18.6875H170.478C170.779 18.1477 171.364 17.1591 172.984 17.1591C175.092 17.1591 176.648 18.8239 176.648 21.6534C176.648 24.4773 175.114 26.1705 173.001 26.1705C171.41 26.1705 170.785 25.1989 170.478 24.642H170.336V25.4318C170.336 25.8011 170.137 26 169.768 26H169.245C168.876 26 168.677 25.8011 168.677 25.4318V14.9318ZM170.342 21.6364C170.342 23.4716 171.16 24.7216 172.62 24.7216C174.137 24.7216 174.933 23.3864 174.933 21.6364C174.933 19.9034 174.16 18.6023 172.62 18.6023C171.137 18.6023 170.342 19.8125 170.342 21.6364ZM179.317 29.2727C179.096 29.2727 178.891 29.2557 178.71 29.2273C178.346 29.1705 178.215 28.892 178.317 28.5341L178.414 28.2102C178.516 27.8636 178.744 27.7614 179.102 27.8011C179.744 27.8636 180.198 27.6136 180.539 26.6932L180.749 26.1136L177.789 17.9261C177.647 17.5341 177.829 17.2727 178.249 17.2727H178.886C179.215 17.2727 179.425 17.4261 179.528 17.7386L181.585 24.0455H181.675L183.732 17.7386C183.835 17.4261 184.045 17.2727 184.374 17.2727H185.016C185.437 17.2727 185.613 17.5341 185.471 17.9261L182.113 27.1648C181.607 28.5398 180.721 29.2727 179.317 29.2727Z" fill="black"/>
                          <defs>
                          <linearGradient id="paint0_linear_1_148" x1="105.5" y1="0" x2="105.5" y2="38.0952" gradientUnits="userSpaceOnUse">
                          <stop offset="0.669102" stop-color="#FFDE6E"/>
                          <stop offset="1" stop-color="#F8C455"/>
                          </linearGradient>
                          </defs>
                          </svg>

                          </button>
                         <p style="margin-top: 20px;"  v-if="nwcalby.startsWith('nostr')">Connected to Alby Wallet.</p>
                          </div>
                </div>
                <div class="collapse bg-base-200">
                  <input type="radio" name="my-accordion-1" />
                  <div class="collapse-title text-xl font-medium bg-black/30  flex">
                         <img class="w-12 h-12 mask mask-squircle bg-zinc-700" style="width: 46px; height: 46px" src="/Mutiny.png"/>
                    <div style="margin-left: 30px">
                            <h3> Mutiny Wallet</h3>
                           <h3 class="text-sm text-neutral">Connect with your Mutiny Wallet</h3>
                         </div>
                  </div>

                  <div class="collapse-content">
                     <p>Add a new Wallet Connection from:</p>
                    <ul class="steps steps-vertical">
                  <li class="step">Settings</li>
                  <li class="step">Wallet Connections</li>
                  <li class="step">Add Connection</li><li class="step">copy the connection string.</li>
                </ul>
                  <textarea class="nwc-Input" style="width: auto; margin-left: 10px; margin-top: 10px" name="Text1" type="password"   placeholder="nostr+walletconnect://..." cols="40" rows="5"  v-model="nwcmutiny"></textarea>
                  </div>
                </div>
                <div class="collapse bg-base-200">
                <input type="radio" name="my-accordion-1" />
                <div class="collapse-title text-xl font-medium transparent bg-black/30 flex">
                  <svg width="56" height="56" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-12 h-12 mask mask-squircle"><g clip-path="url(#clip0_1138_8450)"><rect width="56" height="56" rx="16" fill="black"></rect><rect width="56" height="56" fill="url(#paint0_radial_1138_8450)"></rect><rect width="56" height="56" fill="black" fill-opacity="0.9"></rect><path d="M42.7656 23.2125C42.7656 33.8416 32.4114 42.9297 28 42.9297C23.5886 42.9297 13.2344 33.8416 13.2344 23.2125C13.2344 15.0741 19.8452 8.47656 28 8.47656C36.1548 8.47656 42.7656 15.0741 42.7656 23.2125Z" fill="url(#paint1_radial_1138_8450)"></path><path d="M25.5108 47.4784L27.7337 46.747C27.9067 46.6901 28.0933 46.6901 28.2663 46.747L30.4892 47.4784C31.2399 47.7255 31.8928 46.9058 31.4827 46.231L28.7272 41.6978C28.396 41.1528 27.604 41.1528 27.2728 41.6978L24.5173 46.231C24.1072 46.9058 24.7601 47.7255 25.5108 47.4784Z" fill="url(#paint2_radial_1138_8450)"></path><circle cx="28" cy="23.2422" r="5.79688" fill="black" fill-opacity="0.66"></circle></g><defs><radialGradient id="paint0_radial_1138_8450" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(56 56) rotate(-135) scale(79.196 118.441)"><stop stop-color="#6951FA"></stop><stop offset="1" stop-color="#9151FA"></stop></radialGradient><radialGradient id="paint1_radial_1138_8450" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(42.7656 47.5234) rotate(-127.1) scale(48.9566 70.4506)"><stop stop-color="#6951FA"></stop><stop offset="1" stop-color="#9151FA"></stop></radialGradient><radialGradient id="paint2_radial_1138_8450" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(42.7656 47.5234) rotate(-127.1) scale(48.9566 70.4506)"><stop stop-color="#6951FA"></stop><stop offset="1" stop-color="#9151FA"></stop></radialGradient><clipPath id="clip0_1138_8450"><rect width="56" height="56" rx="16" fill="white"></rect></clipPath></defs></svg>
                       <div style="margin-left: 30px">
                         <h3>Nostr Wallet Connect</h3>
                         <h3 class="text-sm text-neutral">Manually connect with NWC string</h3>
                       </div>


                </div>
                <div class="collapse-content">
                <textarea class="nwc-Input" style="width: auto; margin-left: 10px; margin-top: 10px" name="Text1" type="password"  placeholder="nostr+walletconnect://..." cols="40" rows="5"  v-model="nwc"></textarea>

                </div>
              </div>


                <div class="modal-action">
                  <form method="dialog">
                    <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
                    <!-- if there is a button in form, it will close the modal -->
                        <button @click="store_nwc(); subscribe_to_dvm()" class=" relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-pink-500 to-orange-400 group-hover:from-pink-500 group-hover:to-orange-400 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-pink-200 dark:focus:ring-pink-800">
                                <span class="relative px-5 py-2.5 transition-all ease-in duration-75  rounded-md group-hover:bg-opacity-0">
                                Subscribe
                                </span>
                      </button>


                  </form>
                </div>
                </div>

              </div>
                </dialog>

                <dialog id="subscr" class="modal">
                         <div  className="modal-box rounded-3xl inner shadow-lg p-6 flex flex-col items-center transition-all duration-1000 bg-gradient-to-br from-pink-500 to-orange-400 ">
                                 <h3 class="font-bold text-lg">Manage your Subscription</h3>
                              <img style="flex: content; width: 300px" class="w-full" :src="dvm.nip88.image"></img>
                           <div class="grid grid-cols-1 gap-6">
                              <br>
  <div  className="card-body rounded-2xl bg-black/10  ring-2 ring-white">
                                <h3 className="card-title">{{dvm.nip88.title}}</h3>

<br>
                                 <h3 style="text-align: left">{{dvm.nip88.description}}</h3>

                                  <h3 className="card-title">Perks:</h3>
                                  <div v-for="perk in dvm.nip88.perks">
                                  <p  style="text-align: left">- {{perk}}</p>
                                </div>
                              </div>
                                       <div  v-if="dvm.nip88.hasActiveSubscription"  className="card-body rounded-2xl bg-black/10  ring-2 ring-black">
                                   <h3 className="card-title"  v-if="dvm.nip88.hasActiveSubscription && !dvm.nip88.expires ">Subscription renewing at
                  {{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[2].trim()}}.{{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[1].trim()}}.{{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[0].trim().slice(2)}} {{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[1].split("Z")[0].trim()}} GMT</h3>

                                 <h3 className="card-title"  v-if="dvm.nip88.hasActiveSubscription && dvm.nip88.expires ">Subscription expires on
                  {{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[2].trim()}}.{{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[1].trim()}}.{{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[0].trim().slice(2)}} {{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[1].split("Z")[0].trim()}} GMT</h3>

                                         <h3 v-if="dvm.nip88.hasActiveSubscription && dvm.nip88.expires"> Changed your mind? Resubscribe anytime!</h3>
                                         <h3  v-if="dvm.nip88.hasActiveSubscription && dvm.nip88.expires"> The current subscription will then continue with a new Nostr Wallet Connect string</h3>
                                      </div>
                                <div v-if="!dvm.nip88.hasActiveSubscription || dvm.nip88.expires" v-for="amount_item in dvm.nip88.amounts">

                                  <div class="grid grid-cols-1 gap-6">
                                    <div class="card card-compact rounded-box bg-black/30 border-black">
                                        <div class="card-body !text-base">
                                            <div class="card-title text-base-100-content font-bold">
                                                <h3 >Subscribe and pay {{amount_item.cadence}}</h3>
                                                <div class="modal-action" style="margin-right: 5px; margin-left: auto">
                                            <form method="dialog" >
                                              <!-- if there is a button in form, it will close the modal -->

                                                <button className="sub-Button"  @click="set_subscription_props(amount_item.amount, amount_item.cadence, dvm)" onclick='nwc_modal.showModal();'>{{ amount_item.amount/1000 }} Sats</button>

                                            </form>
                                            </div>

                                        </div>
                                    </div>
                               </div>






                                </div>

                              </div>

                                <button class="btn" v-if="!dvm.nip88.expires && dvm.nip88.hasActiveSubscription" @click="set_subscription_props(0, '', dvm); cancelSubscription(dvm.nip88.subscriptionId, dvm.id)"> Cancel Subscription


                                </button>


                                <form method="dialog">
                                    <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
                                  </form>
                            </div>
                            </div>




        </dialog>
             </div>


           <!--  <p v-if="dvm.subscription ==='' && !isNaN(parseInt(dvm.amount)) && dvm.status !=='subscription-required' && dvm.status !=='subscription-success'" class="badge bg-amber" ><div class="flex"><svg style="margin-top:3px" xmlns="http://www.w3.org/2000/svg" width="14" height="16" fill="currentColor" class="bi bi-lightning" viewBox="0 0 16 20">
            <path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641zM6.374 1 4.168 8.5H7.5a.5.5 0 0 1 .478.647L6.78 13.04 11.478 7H8a.5.5 0 0 1-.474-.658L9.306 1z"/></svg> {{dvm.amount/1000}}</div></p>
          -->
            </div>

 <details open v-if="dvm.status === 'finished'" class="collapse bg-base">
              <summary class="collapse-title   "><div class="btn">Show/Hide Results</div></summary>
              <div class="collapse-content font-size-0" className="z-10" id="collapse">
                  <div class="max-w-5xl relative space-y-3">
    <div class="grid grid-cols-1">
      <button v-if="dvm.result.length > 0 && dvm.action === 'mute'" @click="mute_all(dvm.result);dvm.result = []
       store.commit('set_filter_dvms', dvms)"><span class="relative px-5 py-2.5 transition-all ease-in duration-75 bg-white dark:bg-gray-900 rounded-md group-hover:bg-opacity-0">
                Mute All
                  </span></button>
      <br>


                  <div v-for="result in dvm.result">
                    <div v-if="result.active === true">
                       <div v-if="dvm.action === 'mute' && store.state.mutes.find(x => x === result.authorid) === undefined || dvm.action !== 'mute'">
                    <div v-if="result.active === true" className="card w-70 bg-base-200 shadow-xl flex flex-col">

                   <div  className="playeauthor-wrapper" style="margin-left: 10px; margin-top: 10px">
                      <figure  className="w-28">
                           <img className="avatar"  v-if="result.event.profile.picture" :src="result.event.profile.picture"  alt="DVM Picture" />
                           <img class="avatar" v-else src="@/assets/nostr-purple.svg" />
                      </figure>
                     <div>

                        <a  class="purple" :href="result.authorurl" target="_blank">{{ result.event.profile.name }}</a>
                        <a v-if="result.event.profile.nip05 !== undefined && result.event.profile.nip05 !== '' " class="purple" :href="result.authorurl" target="_blank">({{result.event.profile.nip05 }})</a>
                       <!-- <p v-if="isnip05valid(result.event) === true"> Valid</p> -->
                     </div>

                </div>
                     <h2 className="card-body">{{ result.event.profile.about }} </h2>
                      <div className="justify-end mt-auto" style="margin-left: auto; margin-right: 10px; margin-bottom: 10px" >
                        <button v-if="dvm.action === 'unfollow'" class="v-Button" @click="unfollow(result);result.active = false; store.commit('set_filter_dvms', dvms)
"> Unfollow</button>
                         <button v-if="dvm.action === 'mute' && result.active !== false" class="v-Button" @click="result.active = false; store.commit('set_filter_dvms', dvms)
 mute(result)"> Mute</button>
                     </div>


      </div></div>
                      <div v-if="store.state.mutes.find(x => x === result.authorid) === undefined">
                        <br>
                      </div>
                           </div>
                    </div>
                  </div>
                  <!--   <div style=": inline">
                  ({{ result.event.profile.nip05 }})

                     </div> -->



                    </div>
              </div>
            </details>



          </div>
      </div>
    </div>
  </div>
</template>

<style scoped>

.zap-Button{
  @apply btn hover:bg-amber-400 border-amber-400 text-base;
  bottom: 0;
}

.sub-Button{
  @apply btn hover:bg-nostr border-orange-500 text-base;

  bottom: 0;
}

.request-Button{
  @apply btn hover:bg-nostr border-nostr text-base;
  bottom: 0;
}

.v-Button {
  @apply bg-nostr hover:bg-nostr2 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-black px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
   height: 48px;
   margin: 5px;
}

.c-Input {
  @apply bg-base-200 text-accent dark:bg-black dark:text-white  focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-accent-content transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;

  width: 350px;
  height: 48px;

}

.nwc-Input {
    @apply bg-base-200 dark:bg-base-200 dark:text-white  focus:ring-white  border border-white px-3 py-1.5 text-sm leading-4 text-accent-content transition-colors duration-300  focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;



}

.d-Input {
    @apply bg-black hover:bg-gray-900 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
  width: 300px;

  color: white;
  background: black;
}

.playeauthor-wrapper {
  padding: 6px;
  display: flex;
  align-items: center;
  justify-items: center;
}

.logo {
     display: flex;
    width:100%;
    height:125px;
    justify-content: center;
    align-items: center;
}

h3 {
  font-size: 1.0rem;
   text-align: left;
}


.avatar {
  margin-right: auto;
  margin-left: 0px;
  display: inline-block;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: inset 0 4px 4px 0 rgb(0 0 0 / 10%);
}

.greetings h1,
.greetings h3 {
  text-align: left;

}

.center {
  text-align: center;
  justify-content: center;
}

.tooltip {
  position: relative;
  display: inline-block;
  border-bottom: 1px dotted black; /* If you want dots under the hoverable text */
}

/* Tooltip text */
.tooltip .tooltiptext {
   top: -5px;
  right: 105%;
  visibility: hidden;
  width: 200px;
  background-color: black;
  color: #fff;
  text-align: center;
  padding: 5px 0;
  border-radius: 6px;

  /* Position the tooltip text - see examples below! */
  position: absolute;
  z-index: 1;
}

/* Show the tooltip text when you mouse over the tooltip container */
.tooltip:hover .tooltiptext {
  visibility: visible;
}


@media (min-width: 1024px) {

  .greetings h1,
  .greetings h3 {
    text-align: center;
  }
}
</style>
