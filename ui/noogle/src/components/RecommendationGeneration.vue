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
  Nip19Event, Alphabet, Keys, nip04_decrypt, SecretKey, Duration
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
import {post_note, schedule, copyurl, copyinvoice, sleep, getEvents, get_user_infos, get_zaps, nextInput, createBolt11Lud16, getEventsOriginalOrder, parseandreplacenpubsName} from "../components/helper/Helper.vue"
import amberSignerService from "./android-signer/AndroidSigner";
import StringUtil from "@/components/helper/string.ts";


let dvms =[]


onMounted(async () => {

  while(store.state.nip89dvms.length === 0){
     await sleep(100)
  }
await addAllContentDVMs()
console.log("mount")
  console.log(dvms)

})


async function generate_feed(id) {

   try {
     if(store.state.pubkey === undefined || localStorage.getItem('nostr-key-method') === "anon"){
               miniToastr.showMessage("Some algorithms may need your profile to give personalized recommendations. Sign-in for a better experience.", "Not signed in.", VueNotifications.types.warn)

     }

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
          console.log("Received new event from", relayUrl);
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
                    for (const tag in event.tags) {
                      if (event.tags[tag].asVec()[0] === "status") {
                        dvms.find(i => i.id === event.author.toHex()).status = event.tags[tag].asVec()[1]
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
                              dvms.find(i => i.id === event.author.toHex()).bolt11 = await createBolt11Lud16(lud16, dvms.find(i => i.id === event.author.toHex()).amount)
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
                        console.log(error)
                     }

                    }


                      if (authors.length > 0) {

                        try{

                        let profiles = await get_user_infos(authors)

                            let ids = []
                            for (let evt of events){
                               ids.push(evt.id)
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
                              zapped: zaps.find(x => x.id === evt.id.toHex()).zappedbyUser,
                              zapAmount: zaps.find(x => x.id === evt.id.toHex()).amount

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


const urlinput = ref("");


async function addAllContentDVMs() {

  let relevent_dvms = []
  for (const el of store.state.nip89dvms) {
    for (const tag of JSON.parse(el.event).tags) {
      if (tag[0] === "k" && tag[1] === "5300") {
        relevent_dvms.push(PublicKey.parse(el.id))
      }
    }
  }
  let active_dvms = []
  for (let id of relevent_dvms) {
    let jsonentry = {
      id: id.toHex(),
      last_active: 0
    }
    active_dvms.push(jsonentry)

  }

  console.log(active_dvms)

  const filtera = new Filter().authors(relevent_dvms).kinds([6300, 7000])
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
  // If DVM hasnt been active for 3 weeks, don't consider it.
  console.log(active_dvms)
  let final_dvms = []
  for (let element of active_dvms) {
    if (element.last_active > Timestamp.now().asSecs() - 60 * 60 * 24 * 7) {
      final_dvms.push(store.state.nip89dvms.find(x => x.id === element.id))
    }

  for (let el of final_dvms){

    let status = "announced"
    let jsonentry = {
      id: el.id,
      kind: "",
      status: status,
      result: [],
      name: el.name,
      about: el.about,
      image: el.image,
      amount: el.amount,
      bolt11: ""
    }


    console.log(jsonentry)
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
    bolt11: ""
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
    if (JSON.parse(el.event).pubkey === event.author.toHex().toString()) {
      jsonentry.name = el.name
      jsonentry.about = el.about
      jsonentry.image = el.image

      console.log(jsonentry)

    }
  }


   if (event.content !== "" && status !== "payment-required" &&  status !== "error" &&  status !== "finished" &&  status !== "paid"){
    status = event.content
  }
  jsonentry.status = status
  console.log(dvms)
  if (dvms.filter(i => i.id === jsonentry.id).length === 0) {
       dvms.push(jsonentry)
  }


  //dvms.find(i => i.id === jsonentry.id).status = status
  store.commit('set_recommendation_dvms', dvms)

}




async function zap(invoice) {
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
         dvms.find(i => i.bolt11 === invoice).status = "paid"
          store.commit('set_recommendation_dvms', dvms)
    }
    catch(err){
          console.log(err)
          await copyinvoice(invoice)
    }
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



const isModalOpened = ref(false);
const modalcontent = ref("");
const datetopost = ref(Date.now());


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




const submitHandler = async () => {

}




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


               <button v-if="dvm.status !== 'finished' && dvm.status !== 'paid' && dvm.status !== 'payment-required' && dvm.status !== 'error' && dvm.status !== 'announced'"   className="btn">{{dvm.status}}</button>
                <button v-if="dvm.status === 'finished'" class="bg-base-200 text-bg-base200" @click="generate_feed(dvm.id)" className="btn">Done</button>
                <button v-if="dvm.status === 'paid'" className="btn">Paid, waiting for DVM..</button>
                <button v-if="dvm.status === 'error'" className="btn">Error</button>

                <button v-if="dvm.status === 'payment-required'" className="zap-Button" @click="zap(dvm.bolt11);">{{ dvm.amount/1000 }} Sats</button>
                <button v-if="dvm.status === 'announced'" className="request-Button" @click="generate_feed(dvm.id);">Request</button>


             <!--<h3 v-if="dvm.amount.toString().toLowerCase()==='free'" class="bg-nostr btn rounded-full" >{{ "Free" }}</h3> -->


          </div>




        </div>

         <!--       <div v-if="dvm.result.length > 0" class="collapse bg-base-200">
        <input type="checkbox" class="peer" />
        <div class="collapse-title bg-primary text-primary-content peer-checked:bg-secondary peer-checked:text-secondary-content">
          Click me to show/hide content
        </div>
        <div class="collapse-content bg-primary text-primary-content peer-checked:bg-base-200 peer-checked:text-accent">

        </div>
</div> -->

  <!-- <details open ></details> -->

  <div style="margin-left: auto; margin-right: 10px;">
   <p v-if="dvm.amount.toString().toLowerCase()==='free'" class="text-sm text-gray-600 rounded" >Free</p>
   <p v-if="dvm.amount.toString().toLowerCase()==='subscription'" class="bg-orange-500 label rounded-full" >{{ dvm.amount/1000 }}</p>
   <p v-if="dvm.amount.toString()===''" ></p>
   <p v-if="!isNaN(parseInt(dvm.amount))" class="text-sm  text-gray-600 rounded" ><div class="flex"><svg style="margin-top:3px" xmlns="http://www.w3.org/2000/svg" width="14" height="16" fill="currentColor" class="bi bi-lightning" viewBox="0 0 16 20">
  <path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641zM6.374 1 4.168 8.5H7.5a.5.5 0 0 1 .478.647L6.78 13.04 11.478 7H8a.5.5 0 0 1-.474-.658L9.306 1z"/></svg> {{dvm.amount/1000}}</div></p>
  </div>



    <details open v-if="dvm.status === 'finished'" class="collapse bg-base">
  <summary class="collapse-title   "><div class="btn">Show/Hide Results</div></summary>
  <div class="collapse-content font-size-0" className="z-10" id="collapse">

     <NoteTable  :data="dvm.result"  ></NoteTable>


    </div>
</details>



     <div data-tip="Make Summarization"   v-if="dvm.status === 'finished' && store.state.pubkey.toHex() !== Keys.parse('ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e').publicKey.toHex()" >
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
