<script setup>


import {
  Client,
  Filter,
  Timestamp,
  Event,
  Metadata,
  PublicKey,
  EventBuilder,
  Tag,
  EventId,
  Nip19Event,
  Alphabet,
  Keys,
  nip04_decrypt,
  SecretKey,
  Duration,
  SingleLetterTag,
  NostrSigner,
  nip44_encrypt,
  NIP44Version
} from "@rust-nostr/nostr-sdk";
import store from '../store';
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";
import {computed, onMounted, watch} from "vue";
import deadnip89s from "@/components/data/deadnip89s.json";
import {data} from "autoprefixer";
import {requestProvider} from "webln";
import Newnote from "@/components/Newnote.vue";
import SummarizationGeneration from "@/components/SummarizationGeneration.vue"
import {post_note, schedule, copyurl, copyinvoice, sleep, getEvents, get_user_infos, get_zaps, get_reactions, nextInput, getEventsOriginalOrder, parseandreplacenpubsName} from "../components/helper/Helper.vue"
import {zap, createBolt11Lud16, zaprequest} from "../components/helper/Zap.vue"

import amberSignerService from "./android-signer/AndroidSigner";
import StringUtil from "@/components/helper/string.ts";


let dvms =[]


onMounted(async () => {

  while(store.state.nip89dvms.length === 0){
     await sleep(100)
  }
await addAllContentDVMs()
  console.log(dvms)

})

const current_subscription_amount = ref("")
const current_subscription_cadence = ref("")
const current_subscription_dvm = ref(null)
const current_subscription_nwc = ref("")

function set_subscription_props(amount, cadence, dvm) {
  this.current_subscription_amount = amount
  this.current_subscription_cadence = cadence
  this.current_subscription_dvm = dvm
  this.nwcalby = ""
  this.nwcmutiny = ""
  this.nwc = ""

}

async function generate_feed(id) {

   try {


        //dvms = []
        //store.commit('set_recommendation_dvms', dvms)

        let client = store.state.client

        let content = "NIP 90 Content Discovery request"
        let kind = 5300
        let tags = []
        tags.push(["p", id])
        let res;
        let requestid;

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

        }
        else {

          let tags_t = []
          for (let tag of tags){
            tags_t.push(Tag.parse(tag))
          }
          let evt = new EventBuilder(kind, content, tags_t)
          res = await client.sendEventBuilder(evt);


          requestid = res.toHex();
        }

        store.commit('set_current_request_id_recommendation', requestid)
        if (!store.state.recommendationehasEventListener){
           store.commit('set_recommendationEventListener', true)
           listen()

        }
        else{
          console.log("Already has event listener")
        }

      } catch (error) {
        console.log(error);
      }
}

async function  listen() {
    let client = store.state.client
    let pubkey = store.state.pubkey

    const filter = new Filter().kinds([7000, 6300]).pubkey(pubkey).since(Timestamp.now());
    await client.subscribe([filter]);

    const handle = {
        // Handle event
        handleEvent: async (relayUrl, event) => {
             /* if (store.state.recommendationehasEventListener === false){
                return true
              }*/
            //const dvmname =  getNamefromId(event.author.toHex())
          //console.log("Received new event from", relayUrl);
          //console.log(event.asJson())
           let resonsetorequest = false
            sleep(1200).then(async () => {
              for (let tag in event.tags) {
                if (event.tags[tag].asVec()[0] === "e") {
                  //console.log(event.tags[tag].asVec()[1])
                  //console.log(test)
                  if (event.tags[tag].asVec()[1] ===  store.state.requestidRecommendation) {
                    resonsetorequest = true

                  }
                }

              }
              if (resonsetorequest === true) {
                if (event.kind === 7000) {
                  try {
                    console.log("7000: ", event.content);
                   // console.log("DVM: " + event.author.toHex())
                    //miniToastr.showMessage("DVM: " + dvmname, event.content, VueNotifications.types.info)
                    dvms.find(i => i.id === event.author.toHex()).laststatusid = event.id.toHex()
                    for (const tag in event.tags) {
                      if (event.tags[tag].asVec()[0] === "status") {

                           if (event.content !== "" && event.tags[tag].asVec()[1] === "processing") {
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
                          let profiles = await get_user_infos([event.author])
                          let created = 0
                          if (profiles.length > 0) {
                            // for (const profile of profiles){
                            console.log(profiles[0].profile)
                            let current = profiles[0]
                            // if (profiles[0].profile.createdAt > created){
                            //     created = profile.profile.createdAt
                            //     current = profile
                            //   }


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
                      store.commit('set_recommendation_dvms', dvms)
                    }
                  } catch (error) {
                    console.log("Error: ", error);
                  }


                }

                else if (event.kind === 6300) {
                  let entries = []
                  //console.log("6300:", event.content);

                  let event_etags = JSON.parse(event.content)
                  if (event_etags.length > 0) {
                    for (let etag of event_etags) {
                      const eventid = EventId.fromHex(etag[1]).toHex()
                      entries.push(eventid)
                    }
                    const events = await getEventsOriginalOrder(entries)
                    let authors = []

                   for (const evt of events) {
                      try{
                      authors.push(evt.author)
                          }
                          catch(error){
                        //console.log(error)
                     }

                    }


                      if (authors.length > 0) {

                        try{

                        let profiles = await get_user_infos(authors)

                            let ids = []
                            for (let evt of events){
                              try {ids.push(evt.id)}
                              catch(error){
                                console.log(error)
                              }

                            }
                          let zaps = await get_zaps(ids)
                        let items = []
                        let index = 0
                        for (const evt of events) {
                            if(!evt){
                            continue
                          }
                          let p = profiles.find(record => record.author === evt.author.toHex())
                          let bech32id = evt.id.toBech32()
                          let nip19 = new Nip19Event(evt.id, evt.author, store.state.relays)
                          let nip19bech32 = nip19.toBech32()
                          let picture = p === undefined ? "../assets/nostr-purple.svg" : p["profile"]["picture"]
                          let name = p === undefined ? bech32id : p["profile"]["name"]
                          let authorid = evt.author.toHex()
                          let highlighterurl = "https://highlighter.com/e/" + nip19bech32
                          let njumpurl = "https://njump.me/" + nip19bech32
                          let nostrudelurl = "https://nostrudel.ninja/#/n/" + bech32id
                          let uri = "nostr:" + bech32id //  nip19.toNostrUri()
                          let lud16 = p === undefined ? "" : (p["profile"] === undefined ? "" : p["profile"]["lud16"])


                          if (items.find(e => e.id === evt.id.toHex()) === undefined) {

                            let react = zaps.find(x => x.id === evt.id.toHex())
                            items.push({
                              id: evt.id.toHex(),
                              content: await parseandreplacenpubsName(evt.content),
                              author: name,
                              authorid: authorid,
                              authorurl: "https://njump.me/" + evt.author.toBech32(),
                              links: {
                                "uri": uri,
                                "highlighter": highlighterurl,
                                "njump": njumpurl,
                                "nostrudel": nostrudelurl
                              },
                              avatar: picture,
                              index: index,
                              indicator: {"time": evt.createdAt.toHumanDatetime(), "index": index},
                              lud16: lud16,
                              zapped: react.zappedbyUser,
                              zapAmount: react.amount,
                              reacted: react.reactedbyUser,
                              reactions: react.reactions,

                            })
                            index = index + 1
                          }

                        }
                        if (dvms.find(i => i.id === event.author.toHex()) === undefined) {
                          await addDVM(event)
                          console.log("add dvm because of bug")
                        }


                        dvms.find(i => i.id === event.author.toHex()).result.length = 0
                        dvms.find(i => i.id === event.author.toHex()).result.push.apply(dvms.find(i => i.id === event.author.toHex()).result, items)
                        dvms.find(i => i.id === event.author.toHex()).status = "finished"
                      }
                         catch(error){
                        console.log(error)}
                      }
                     }
                  store.commit('set_recommendation_dvms', dvms)
                }

              }
            })
        },
        // Handle relay message
        handleMsg: async (relayUrl, message) => {
            //console.log("Received message from", relayUrl, message.asJson());
        }
    };

    client.handleNotifications(handle);
}

async function addAllContentDVMs() {

  let relevant_dvms = []
  for (const el of store.state.nip89dvms) {
    for (const tag of JSON.parse(el.event).tags) {
      if (tag[0] === "k" && tag[1] === "5300") {
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

  const filtera = new Filter().authors(relevant_dvms).kinds([6300, 7000])
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
      bolt11: "",
      lud16: el.lud16,
      subscription: "",
      nip88: el.nip88
    }


    //console.log(jsonentry)
    if (dvms.filter(i => i.id === jsonentry.id).length === 0) {
      dvms.push(jsonentry)
    }
  }

  store.commit('set_recommendation_dvms', dvms)
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
    subscription: ""
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
          let profiles = await get_user_infos([event.author])
         let created = 0
          if (profiles.length > 0){
           // for (const profile of profiles){
              console.log(profiles[0].profile)
            let current = profiles[0]
             // if (profiles[0].profile.createdAt > created){
             //     created = profile.profile.createdAt
             //     current = profile
             //   }


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
  store.commit('set_recommendation_dvms', dvms)

}


async function cancelSubscription(kind7001, recipent){
        console.log(kind7001)
        console.log(recipent)
        let content = "Canceled from Noogle"
        let kind = 7002
        let tags = [
              ["p", recipent],
              ["e", kind7001]
            ]
        let tags_t = []
        for (let tag of tags){
            tags_t.push(Tag.parse(tag))
          }
          let evt = new EventBuilder(kind, content, tags_t)
          let client = store.state.client
          let res = await client.sendEventBuilder(evt);
          let requestid = res.toHex();

       dvms.find(x => x.nip88.eventid === this.current_subscription_dvm.nip88.eventid).nip88.hasActiveSubscription = true
       dvms.find(x => x.nip88.eventid === this.current_subscription_dvm.nip88.eventid).nip88.expires = true



}



async function subscribe_to_dvm() {

  if (!localStorage.getItem("nostr-key-method") || localStorage.getItem("nostr-key-method") === "anon"){
    miniToastr.showMessage("Login to subscribe to a DVM.", "Not logged in", "error")
    return
  }

  // We only arrive here if no subscription exists, we might create a 7001 if it doesnt exist and we zap it
   let client = store.state.client

  console.log(this.current_subscription_dvm.nip88)
  console.log(this.current_subscription_nwc)
 // console.log(JSON.stringify(dvm.event))
  console.log(this.current_subscription_amount)
    console.log(this.current_subscription_cadence)
 // console.log(dvm.p)


  if (this.current_subscription_dvm.nip88.subscriptionId === ""){
    console.log("Creating 7001 event")
    let tags = [
        Tag.parse([ "p", this.current_subscription_dvm.id]),
         Tag.parse([ "e" , this.current_subscription_dvm.nip88.eventid]),
         Tag.parse([ "event", JSON.stringify(this.current_subscription_dvm.nip88.event)]),
         Tag.parse([ "amount", (this.current_subscription_amount).toString(), "msats", this.current_subscription_cadence]),
        // Zap-splits todo order and splits
        // Tag.parse([ "zap", authorid, "19" ]), // 95%
        // Tag.parse([ "zap", "fa984bd7dbb282f07e16e7ae87b26a2a7b9b90b7246a44771f0cf5ae58018f52", "1" ]), // 5% to client developer where subscription was created
    ]

    console.log(this.current_subscription_dvm.nip88.zaps)

    for(let zap of this.current_subscription_dvm.nip88.zaps){
      let zaptag = Tag.parse([ "zap", zap.key, zap.split])
      tags.push(zaptag)
    }
/*


 */



      let evt = new EventBuilder(7001, "Subscription from noogle.lol", tags)
      let res = await client.sendEventBuilder(evt);
      console.log(res)
      this.current_subscription_dvm.nip88.subscriptionId = res.toHex()

  }

 /* let overallsplit = 0
  for (let zap of this.current_subscription_dvm.nip88.zaps){
    overallsplit += parseInt(zap.split)
  }
  for (let zap of this.current_subscription_dvm.nip88.zaps) {
    let profiles = await get_user_infos([PublicKey.parse(zap.key)])
    if (profiles.length > 0) {
      let current = profiles[0]
      let lud16 = current.profile.lud16
      let splitted_amount = Math.floor((zap.split / overallsplit) * this.current_subscription_amount / 1000)
      console.log(splitted_amount)
      console.log(overallsplit)
      console.log(this.current_subscription_dvm.nip88.subscriptionId)
    }

  } */

  try{
        let receiver = PublicKey.parse(store.state.subscription_verifier_pubkey)
     /*if (this.current_subscription_dvm.nip88.p !== ""){
        receiver = PublicKey.parse(this.current_subscription_dvm.nip88.p)
      }*/
      let signer = NostrSigner.keys(Keys.parse(store.state.nooglekey))
      let nclient = new Client(signer)

       for (const relay of store.state.relays) {
        await nclient.addRelay(relay);
      }
       await nclient.connect()

      let encnwc = nip44_encrypt(SecretKey.parse(store.state.nooglekey), PublicKey.parse(store.state.subscription_verifier_pubkey),
      this.current_subscription_nwc, NIP44Version.V2)

      let content = {
        "subscribe_event":  this.current_subscription_dvm.nip88.subscriptionId,
        "nwc": encnwc,
        "cadence" : this.current_subscription_cadence,
        "overall_amount" : this.current_subscription_amount,
        "tier_dtag" : this.current_subscription_dvm.nip88.d,
        "recipient" : this.current_subscription_dvm.id,
        "subscriber" : store.state.pubkey.toHex(),
        "zaps" : this.current_subscription_dvm.nip88.zaps



      }

       // TODO this is only for viewing, check event (happens on page reload now)
       let subscribeduntil = Timestamp.now().asSecs()
       if (this.current_subscription_cadence === "daily"){
         subscribeduntil = Timestamp.now().asSecs() + 60*60*24
       }
       else if (this.current_subscription_cadence === "weekly"){
         subscribeduntil = Timestamp.now().asSecs() + 60*60*24 * 7
       }
        else if (this.current_subscription_cadence === "monthly"){
         subscribeduntil = Timestamp.now().asSecs() + 60*60*24 * 31
       }
        else if (this.current_subscription_cadence === "yearly"){
         subscribeduntil = Timestamp.now().asSecs() + 60*60*24 * 365
       }
    console.log(content)
      let msg = JSON.stringify(content)
      console.log(msg)
      let id = await nclient.sendDirectMsg(receiver, msg)
      console.log(id)

       dvms.find(x => x.nip88.eventid === this.current_subscription_dvm.nip88.eventid).nip88.hasActiveSubscription = true
       dvms.find(x => x.nip88.eventid === this.current_subscription_dvm.nip88.eventid).nip88.expires = false
       dvms.find(x => x.nip88.eventid === this.current_subscription_dvm.nip88.eventid).nip88.subscribedUntil = subscribeduntil


  }
  catch(error){
      console.log(error)
  }


      //TODO send info to Subscription service
      /*
         let invoice = await zaprequest(lud16, splitted_amount, "paid for " + cadence + " from noogle.lol", activesubscriptioneventid, dvmid, store.state.relays)
          console.log(invoice)
          await zapSubscription(invoice)
      }
  }

*/




      // next, the dvm should listen to these 7001 events addressed to it and (or rather 9735 tagging the 7001 and the subscription should be considered valid for both)


}

async function zapSubscription(invoice) {
  let webln;

    //this.dvmpaymentaddr =  `https://chart.googleapis.com/chart?cht=qr&chl=${invoice}&chs=250x250&chld=M|0`;
    //this.dvminvoice = invoice
  try {
    webln = await requestProvider();
  } catch (err) {
      await copyinvoice(invoice)
  }

  if (webln) {
    try{
         let response = await webln.sendPayment(invoice)

         //dvms.find(i => i.bolt11 === invoice).status = "paid"
         // store.commit('set_recommendation_dvms', dvms)
    }
    catch(err){
          console.log(err)
          await copyinvoice(invoice)
    }
  }
}

async function zap_local(invoice) {

  let success = await zap(invoice)
  if (success){
    dvms.find(i => i.bolt11 === invoice).status = "paid"
    store.commit('set_recommendation_dvms', dvms)
  }

}



    async  function store_nwc(){

      if (this.nwcalby.startsWith("nostr")){

        this.current_subscription_nwc  = this.nwcalby
      }
      else if (this.nwcmutiny.startsWith("nostr") ){

        this.current_subscription_nwc  = this.nwcmutiny
      }
      else{

        this.current_subscription_nwc  = this.nwc
      }

    }


async function connect_alby_nwc(){

const alby = webln.NostrWebLNProvider.withNewSecret();
let result = await alby.client.initNWC({
        name: `Noogle`,
      });

 if (result.payload.success){
   this.nwcalby =  alby.client.getNostrWalletConnectUrl(true);
   await this.store_nwc()
 }
}


defineProps({
  msg: {
    type: String,
    required: false
  },
})

import { ref } from "vue";
import ModalComponent from "../components/Newnote.vue";
import VueDatePicker from "@vuepic/vue-datepicker";
import {timestamp} from "@vueuse/core";
import NoteTable from "@/components/NoteTable.vue";
import {webln} from "@getalby/sdk";



const isModalOpened = ref(false);
const isNWCModalOpened = ref(false);
const modalcontent = ref("");
const nwcmodalcontent = ref("");
const datetopost = ref(Date.now());

const nwc = ref("");
const nwcmutiny = ref("");
const  nwcalby= ref("");
const  hasNWC= ref("");
const  nwcconnector= ref("user");


const openModal = result => {
  datetopost.value = Date.now();
  isModalOpened.value = true;



  //let resevents = ""
  //for (let evt of result){
   // resevents = resevents + "nostr:" + (evt.id.toBech32()) + "\n"
  //}
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






</script>

<!--  font-thin bg-gradient-to-r from-white to-nostr bg-clip-text text-transparent -->

<template>

  <div class="greetings">
   <br>
    <br>
    <h1 class="text-7xl font-black tracking-wide">Noogle</h1>
    <h1 class="text-7xl font-black tracking-wide">Content</h1>
    <h1 class="text-7xl font-black tracking-wide">Discovery</h1>

    <h2 class="text-base-200-content text-center tracking-wide text-2xl font-thin ">
    Algorithms, but you are the one in control.</h2>
    <h3>
     <br>
      <div class="align-content-center">
             <button v-if="store.state.recommendationdvms.length === 0" class="v-Button">Loading DVMs..</button>

      </div>

    </h3>
  </div>
  <br>

       <ModalComponent  :isOpen="isModalOpened" @modal-close="closeModal" @submit="submitHandler" name="first-modal">
            <template #header>Summarize Results <br></template>
            <template #content>

              <SummarizationGeneration :events="modalcontent"></SummarizationGeneration>





            </template>

            <template #footer>
              <!-- <div>
                <VueDatePicker :min-date="new Date()" :teleport="false" :dark="true" position="right" className="bg-base-200 inline-flex flex-none" style="width: 220px;" v-model="datetopost"></VueDatePicker>
               <button className="v-Button" @click="schedule(modalcontent, datetopost)"   @click.stop="closeModal"><img width="25px" style="margin-right: 5px" src="../../public/shipyard.ico"/>Schedule Note with Shipyard DVM</button>
                 <br>
                or
                <br>
                  <button className="v-Button" style="margin-bottom: 0px" @click="post_note(modalcontent)"   @click.stop="closeModal"><img  width="25px" style="margin-right: 5px;" src="../../public/favicon.ico"/>Post Note now</button>
              </div> -->
            </template>
          </ModalComponent>






  <div class=" relative space-y-3">
    <div class="grid grid-cols-1 gap-6">

        <div className="card w-70 bg-base-100 shadow-xl flex flex-col"   v-for="dvm in store.state.recommendationdvms"
            :key="dvm.id">




        <div className="card-body">

<div className="playeauthor-wrapper">
  <figure  className="w-20">
       <img className="avatar"  v-if="dvm.image" :src="dvm.image"  alt="DVM Picture" />
       <img class="avatar" v-else src="@/assets/nostr-purple.svg" />
  </figure>


          <h2 className="card-title">{{ dvm.name }}</h2>
  </div>
          <h3 class="fa-cut" v-html="StringUtil.parseHyperlinks(dvm.about)"></h3>


          <div className="card-actions justify-end mt-auto" >

              <div className="tooltip mt-auto">


               <button v-if="dvm.status !== 'finished' && dvm.status !== 'paid' && dvm.status !== 'payment-required' && dvm.status !== 'subscription-required' && dvm.status !== 'subscription-success' && dvm.status !== 'error' && dvm.status !== 'announced'" className="btn">{{dvm.status}}</button>
                <button v-if="dvm.status === 'finished'  && !dvm.nip88 ||(dvm.nip88 && !dvm.nip88.hasActiveSubscription)" @click="generate_feed(dvm.id)" class="relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-purple-600 to-blue-500 group-hover:from-purple-600 group-hover:to-blue-500 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-blue-300 dark:focus:ring-blue-800">
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
                <button v-if="dvm.status === 'announced' && !dvm.nip88 ||(dvm.nip88 && !dvm.nip88.hasActiveSubscription)" @click="generate_feed(dvm.id);" class="relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-purple-600 to-blue-500 group-hover:from-purple-600 group-hover:to-blue-500 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-blue-300 dark:focus:ring-blue-800">
                <span class="relative px-5 py-2.5 transition-all ease-in duration-75 bg-white dark:bg-gray-900 rounded-md group-hover:bg-opacity-0">
                Request
                </span>
                </button>

                <button v-if="dvm.status === 'announced'  && dvm.nip88 && dvm.nip88.hasActiveSubscription" @click="generate_feed(dvm.id);" class="relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-pink-500 to-orange-400 group-hover:from-pink-500 group-hover:to-orange-400 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-pink-200 dark:focus:ring-pink-800">
            <span class="relative px-5 py-2.5 transition-all ease-in duration-75 bg-white dark:bg-gray-900 rounded-md group-hover:bg-opacity-0">
                Request
                </span>
                </button>

             <!--<h3 v-if="dvm.amount.toString().toLowerCase()==='free'" class="bg-nostr btn rounded-full" >{{ "Free" }}</h3> -->


          </div>




        </div>

  <div style="margin-left: auto; margin-right: 3px;">
   <p v-if="!dvm.subscription && dvm.amount.toString().toLowerCase()==='free'" class="badge bg-nostr" >Free</p>
    <p v-if="!dvm.subscription && dvm.amount.toString().toLowerCase()==='flexible'" class="badge bg-nostr2" >Flexible</p>
    <p v-if="dvm.nip88" class="badge text-white bg-gradient-to-br from-pink-500 to-orange-400">Subscription</p>

    </div>
          <div>
      <div class="playeauthor-wrapper" v-if="dvm.nip88">


       <button v-if="!dvm.nip88.hasActiveSubscription"  onclick='subscr.showModal()' class="relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-pink-500 to-orange-400 group-hover:from-pink-500 group-hover:to-orange-400 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-pink-200 dark:focus:ring-pink-800">
            <span class="relative px-5 py-2.5 transition-all ease-in duration-75 bg-white dark:bg-gray-900 rounded-md group-hover:bg-opacity-0">Subscription
            </span>
       </button>
        <button v-if="dvm.nip88.hasActiveSubscription"  onclick='subscr.showModal()' class=" relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-pink-500 to-orange-400 group-hover:from-pink-500 group-hover:to-orange-400 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-pink-200 dark:focus:ring-pink-800">
                        <span class="relative px-5 py-2.5 transition-all ease-in duration-75  rounded-md group-hover:bg-opacity-0">
                        Active Subscription
                        </span>
       </button>




        <dialog id="nwc_modal" class="modal">
      <div class="modal-box rounded-3xl inner shadow-lg p-6 flex flex-col items-center transition-all duration-1000 bg-base-600/60  ">
        <h3 class="font-bold text-lg">Connect with Nostr Wallet Connect</h3>
        <br>
          <div class="flex">
              <img class="avatar"  :src="dvm.nip88.image" alt="" />
            <h3 class="text-lg">{{dvm.nip88.title}}</h3>
          </div>
        <div v-if="!this.hasNWC">
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
            <button v-if="!nwcalby.startsWith('nostr')" style="margin-top: 20px;" @click="connect_alby_nwc()">
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
          <textarea class="nwc-Input" style="width: 400px; margin-left: 10px; margin-top: 10px" name="Text1" type="password"   placeholder="nostr+walletconnect://..." cols="40" rows="5"  v-model="this.nwcmutiny"></textarea>
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
        <textarea class="nwc-Input" style="width: 400px; margin-left: 10px; margin-top: 10px" name="Text1" type="password"  placeholder="nostr+walletconnect://..." cols="40" rows="5"  v-model="this.nwc"></textarea>

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
                      <img style="flex: content" :src="dvm.nip88.image"></img>
                      <div class="glass" className="card-body">

                        <h3 className="card-title">{{dvm.nip88.title}}</h3>

                         <h3 style="text-align: left">{{dvm.nip88.description}}</h3>
                              <br>
                          <h3 className="card-title">Perks:</h3>
                          <div v-for="perk in dvm.nip88.perks">
                          <p  style="text-align: left">{{perk}}</p>


                        </div>
                        <br>
                           <h3 v-if="dvm.nip88.hasActiveSubscription && !dvm.nip88.expires ">Subscription renewing at
          {{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[2].trim()}}.{{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[1].trim()}}.{{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[0].trim().slice(2)}} {{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[1].split("Z")[0].trim()}} GMT</h3>

                         <h3 v-if="dvm.nip88.hasActiveSubscription && dvm.nip88.expires ">Subscription expires on
          {{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[2].trim()}}.{{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[1].trim()}}.{{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[0].split("-")[0].trim().slice(2)}} {{Timestamp.fromSecs(parseInt(dvm.nip88.subscribedUntil)).toHumanDatetime().split("T")[1].split("Z")[0].trim()}} GMT</h3>
                       <h3 v-if="dvm.nip88.hasActiveSubscription && dvm.nip88.expires"> Changed your mind? Resubscribe! The current subscription will continue with a new NWC string</h3>
                        <div v-if="!dvm.nip88.hasActiveSubscription || dvm.nip88.expires" v-for="amount_item in dvm.nip88.amounts">
                          <br>
                            <h3 >Subscribe and pay {{amount_item.cadence}}</h3>


                          <div class="modal-action">
                          <form method="dialog">
                            <!-- if there is a button in form, it will close the modal -->

                              <button className="sub-Button" @click="set_subscription_props(amount_item.amount, amount_item.cadence, dvm)" onclick='nwc_modal.showModal();'>{{ amount_item.amount/1000 }} Sats</button>

                          </form>

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

      <!--  <div v-if="dvm.nip88.hasActiveSubscription" className="dropdown" >
                    <div tabIndex={0} role="button" >
                      <button class=" relative inline-flex items-center justify-center p-0.5 mb-2 me-2 overflow-hidden text-sm font-medium text-gray-900 rounded-lg group bg-gradient-to-br from-pink-500 to-orange-400 group-hover:from-pink-500 group-hover:to-orange-400 hover:text-white dark:text-white focus:ring-4 focus:outline-none focus:ring-pink-200 dark:focus:ring-pink-800">
                        <span class="relative px-5 py-2.5 transition-all ease-in duration-75  rounded-md group-hover:bg-opacity-0">
                        Active Subscription
                        </span>
                        </button>
                                               <p  class=" text-sm sub-Button text-orange-400"> Active Subscription </p>

                    </div>
                    <div  style="z-index: 10000" tabIndex={0} className="dropdown-content start-12 z-[1] horizontal card card-compact w-96 p-2 shadow bg-orange-500 text-primary-content">
                      <img style="flex: content" :src="dvm.nip88.image"></img>
                      <div class="glass" className="card-body">

                        <h3 className="card-title">{{dvm.nip88.title}}</h3>

                         <h3 style="text-align: left">{{dvm.nip88.description}}</h3>
                        <br>
                        <h3 className="card-title">Perks:</h3>
                        <div v-for="perk in dvm.nip88.perks">
                          <p  style="text-align: left">{{perk}}</p>


                        </div>
 <br>

                       <div v-for="index in dvm.nip88.amounts">
                          <br>
                            <h3 >Subscribe and pay {{index.cadence}}</h3>
                          <button className="sub-Button" @click="subscribe(dvm.lud16, index.amount, index.cadence, dvm.event, dvm.eventid, dvm.id)">{{ index.amount/1000 }} Sats</button>

                        </div>

                       <br>
                        <button class="btn">Unsubscribe (todo)</button>

                      </div>
                    </div>
                  </div> -->

      </div>



                <!--    <div tabIndex={0}  role="button" class="Button" >
                      <p v-if="dvm.subscription!==''" class="text-sm  text-gray-600 rounded" >Subscription active until
          {{Timestamp.fromSecs(parseInt(dvm.subscription)).toHumanDatetime().split("T")[0].split("-")[2].trim()}}.{{Timestamp.fromSecs(parseInt(dvm.subscription)).toHumanDatetime().split("T")[0].split("-")[1].trim()}}.{{Timestamp.fromSecs(parseInt(dvm.subscription)).toHumanDatetime().split("T")[0].split("-")[0].trim().slice(2)}} {{Timestamp.fromSecs(parseInt(dvm.subscription)).toHumanDatetime().split("T")[1].split("Z")[0].trim()}}</p>
                    </div> -->
                <!--  <div tabIndex={0} style="z-index: 100000;" className="dropdown-content -start-56 z-[1] horizontal card card-compact w-64 p-2 shadow bg-orange-500 text-primary-content">
                  <div className="card-body">
                    <h3 className="card-title">Subscribe for a day</h3>

                    <button className="sub-Button" @click="subscribe(dvm.lud16, 1, dvm.amount/1000, dvm.laststatusid, dvm.id)">{{ dvm.amount/1000 }} Sats</button>

                      <h3 className="card-title">Subscribe for a month</h3>

                    <button className="sub-Button" @click="subscribe(dvm.lud16, 30, dvm.amount/1000, dvm.laststatusid, dvm.id)">{{ 30 * dvm.amount/1000 }} Sats</button>
                  </div>
                </div>
              </div>-->
   <p v-if="dvm.amount.toString()===''" ></p>

   <p v-if="dvm.subscription ==='' && !isNaN(parseInt(dvm.amount)) && dvm.status !=='subscription-required' && dvm.status !=='subscription-success'" class="badge bg-amber" ><div class="flex"><svg style="margin-top:3px" xmlns="http://www.w3.org/2000/svg" width="14" height="16" fill="currentColor" class="bi bi-lightning" viewBox="0 0 16 20">
  <path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641zM6.374 1 4.168 8.5H7.5a.5.5 0 0 1 .478.647L6.78 13.04 11.478 7H8a.5.5 0 0 1-.474-.658L9.306 1z"/></svg> {{dvm.amount/1000}}</div></p>
  </div>



    <details open v-if="dvm.status === 'finished'" class="collapse bg-base">
  <summary class="collapse-title   "><div class="btn">Show/Hide Results</div></summary>
  <div class="collapse-content font-size-0" className="z-10" id="collapse">

     <NoteTable  :data="dvm.result"  ></NoteTable>


    </div>
</details>



     <div data-tip="Make Summarization"   v-if="dvm.status === 'finished' && store.state.pubkey.toHex() !== Keys.parse(store.state.nooglekey).publicKey.toHex()" >
                 <button @click="openModal(dvm.result)"  class="w-8 h-8 rounded-full bg-nostr border-white border-1 text-white flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-offset-2  focus:ring-black tooltip" data-top='Share' aria-label="make note" role="button">
   <svg class="w-4 h-4 text-gray-800 dark:text-white" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
    <path d="M9 19V.352A3.451 3.451 0 0 0 7.5 0a3.5 3.5 0 0 0-3.261 2.238A3.5 3.5 0 0 0 2.04 6.015a3.518 3.518 0 0 0-.766 1.128c-.042.1-.064.209-.1.313a3.34 3.34 0 0 0-.106.344 3.463 3.463 0 0 0 .02 1.468A4.016 4.016 0 0 0 .3 10.5l-.015.036a3.861 3.861 0 0 0-.216.779A3.968 3.968 0 0 0 0 12a4.032 4.032 0 0 0 .107.889 4 4 0 0 0 .2.659c.006.014.015.027.021.041a3.85 3.85 0 0 0 .417.727c.105.146.219.284.342.415.072.076.148.146.225.216.1.091.205.179.315.26.11.081.2.14.308.2.02.013.039.028.059.04v.053a3.506 3.506 0 0 0 3.03 3.469 3.426 3.426 0 0 0 4.154.577A.972.972 0 0 1 9 19Zm10.934-7.68a3.956 3.956 0 0 0-.215-.779l-.017-.038a4.016 4.016 0 0 0-.79-1.235 3.417 3.417 0 0 0 .017-1.468 3.387 3.387 0 0 0-.1-.333c-.034-.108-.057-.22-.1-.324a3.517 3.517 0 0 0-.766-1.128 3.5 3.5 0 0 0-2.202-3.777A3.5 3.5 0 0 0 12.5 0a3.451 3.451 0 0 0-1.5.352V19a.972.972 0 0 1-.184.546 3.426 3.426 0 0 0 4.154-.577A3.506 3.506 0 0 0 18 15.5v-.049c.02-.012.039-.027.059-.04.106-.064.208-.13.308-.2s.214-.169.315-.26c.077-.07.153-.14.225-.216a4.007 4.007 0 0 0 .459-.588c.115-.176.215-.361.3-.554.006-.014.015-.027.021-.041.087-.213.156-.434.205-.659.013-.057.024-.115.035-.173.046-.237.07-.478.073-.72a3.948 3.948 0 0 0-.066-.68Z"/>
</svg>
                               </button>

          </div>
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
  margin-right: 10px;
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


@media (min-width: 1024px) {

  .greetings h1,
  .greetings h3 {
    text-align: center;
  }
}
</style>
