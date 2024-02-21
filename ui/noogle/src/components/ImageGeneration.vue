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
  Nip19Event, Alphabet, Keys, nip04_decrypt, SecretKey
} from "@rust-nostr/nostr-sdk";
import store from '../store';
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";
import {computed, watch} from "vue";
import deadnip89s from "@/components/data/deadnip89s.json";
import {data} from "autoprefixer";
import {requestProvider} from "webln";
import Newnote from "@/components/Newnote.vue";
import amberSignerService from "./android-signer/AndroidSigner";

let dvms =[]
let searching = false



let listener = false

let hasmultipleinputs = false

function showDetails(user) {
   this.$bvModal.show("modal-details");
   this.modalData = user;
}

const sleep = (ms) => {
  return new Promise(resolve => setTimeout(resolve, ms))
}


async function post_note(note){
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

async function schedule(note) {


  let schedule = Timestamp.fromSecs(datetopost.value/1000)
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



async function generate_image(message) {

   try {
     if (message === undefined){
       message = "A purple Ostrich"
     }

     if(store.state.pubkey === undefined){
               miniToastr.showMessage("Please login first", "No pubkey set", VueNotifications.types.warn)
          return
     }

        dvms = []
        store.commit('set_imagedvm_results', dvms)
        let client = store.state.client

        let content = "NIP 90 Image Generation request"
        let kind = 5100
        let tags = [
              ["i", message, "text"]
            ]

        hasmultipleinputs = false
        if (urlinput.value !== "" && urlinput.value.startsWith('http')){
          let imagetag = ["i", urlinput.value, "url"]
          tags.push(imagetag)
          hasmultipleinputs = true
           console.log(urlinput.value)
        }



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
          res = res.id;
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

        store.commit('set_current_request_id_image', requestid)
        //console.log("IMAGE EVENT SENT: " + res.toHex())

        //miniToastr.showMessage("Sent Request to DVMs", "Awaiting results", VueNotifications.types.warn)
        searching = true
        if (!store.state.imagehasEventListener){
           listen()
           store.commit('set_imagehasEventListener', true)
        }
        else{
          console.log("Already has event listener")
        }

      } catch (error) {
        console.log(error);
      }
}

async function  listen() {
    listener = true

    let client = store.state.client
    let pubkey = store.state.pubkey

    const filter = new Filter().kinds([7000, 6100, 6905]).pubkey(pubkey).since(Timestamp.now());
    await client.subscribe([filter]);

    const handle = {
        // Handle event
        handleEvent: async (relayUrl, event) => {
              if (store.state.imagehasEventListener === false){
                return true
              }
            //const dvmname =  getNamefromId(event.author.toHex())
            console.log("Received new event from", relayUrl);
              console.log(event.asJson())
           let resonsetorequest = false
            sleep(1000).then(async () => {
              for (let tag in event.tags) {
                if (event.tags[tag].asVec()[0] === "e") {
                  console.log("IMAGE ETAG: " + event.tags[tag].asVec()[1])
                  console.log("IMAGE LISTEN TO : " + store.state.requestidImage)
                  if (event.tags[tag].asVec()[1] === store.state.requestidImage) {
                    resonsetorequest = true
                  }
                }

              }
              if (resonsetorequest === true) {
                if (event.kind === 7000) {


                  try {
                    console.log("7000: ", event.content);
                    console.log("DVM: " + event.author.toHex())
                    searching = false
                    //miniToastr.showMessage("DVM: " + dvmname, event.content, VueNotifications.types.info)

                    let status = "unknown"
                    let jsonentry = {
                      id: event.author.toHex(),
                      kind: "",
                      status: status,
                      result: "",
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
                        // TODO else request invoice
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
                    if (dvms.filter(i => i.id === jsonentry.id).length === 0) {
                      if (!hasmultipleinputs  ||
                          (hasmultipleinputs && jsonentry.id !==  "04f74530a6ede6b24731b976b8e78fb449ea61f40ff10e3d869a3030c4edc91f")){
                                              // DVM can not handle multiple inputs, straight up censorship until spec is fulfilled or requests are ignored.
                         dvms.push(jsonentry)
                      }

                    }

                    dvms.find(i => i.id === jsonentry.id).status = status

                    store.commit('set_imagedvm_results', dvms)


                  } catch (error) {
                    console.log("Error: ", error);
                  }


                }
                else if (event.kind === 6905) {
                  console.log(event.content)

                }
                else if (event.kind === 6100) {
                  let entries = []
                  console.log("6100:", event.content);

                  //miniToastr.showMessage("DVM: " + dvmname, "Received Results", VueNotifications.types.success)
                  dvms.find(i => i.id === event.author.toHex()).result = event.content
                  dvms.find(i => i.id === event.author.toHex()).status = "finished"
                  store.commit('set_imagedvm_results', dvms)
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

function nextInput(e) {
  const next = e.currentTarget.nextElementSibling;
  if (next) {
    next.focus();

  }
}


    async function copyinvoice(invoice){
       await navigator.clipboard.writeText(invoice)
        window.open("lightning:" + invoice,"_blank")
       miniToastr.showMessage("", "Copied Invoice to clipboard", VueNotifications.types.info)
    }

    async function copyurl(url){
       await navigator.clipboard.writeText(url)
       miniToastr.showMessage("", "Copied link to clipboard", VueNotifications.types.info)
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
              store.commit('set_imagedvm_results', dvms)
        }
        catch(err){
              console.log(err)
              await copyinvoice(invoice)
        }


        //console.log(response)
        //for (const dvm of dvms){
        //  console.log(dvm.bolt11 + "   " + invoice)
        //}


      }


    }

    async function createBolt11Lud16(lud16, amount) {
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

const isModalOpened = ref(false);
const modalcontent = ref("");
const datetopost = ref(Date.now());


const openModal = result => {
  datetopost.value = Date.now();
  isModalOpened.value = true;
  modalcontent.value = result
};
const closeModal = () => {
  isModalOpened.value = false;
  console.log(datetopost.value)
};

const submitHandler = async () => {

 // await post_note(modalcontent)
  await schedule(modalcontent, Timestamp.now())
}



</script>

<!--  font-thin bg-gradient-to-r from-white to-nostr bg-clip-text text-transparent -->

<template>

  <div class="greetings">
   <br>
    <br>
    <h1 class="text-7xl font-black tracking-wide">Noogle</h1>
    <h1 class="text-7xl font-black tracking-wide">Image Generation</h1>
    <h2 class="text-base-200-content text-center tracking-wide text-2xl font-thin ">
    Generate Images, the decentralized way</h2>
    <h3>
     <br>
     <input class="c-Input" autofocus placeholder="A purple ostrich..." v-model="message" @keyup.enter="generate_image(message)" @keydown.enter="nextInput">
     <button class="v-Button"  @click="generate_image(message)">Generate Image</button>
    </h3>
<details class="collapse bg-base " className="advanced" >
  <summary class="collapse-title font-thin bg">Advanced Options</summary>
  <div class="collapse-content font-size-0" className="z-10" id="collapse-settings">
    <div>
          <h4 className="inline-flex flex-none font-thin">Url to existing image:</h4>
    <div className="inline-flex flex-none" style="width: 10px;"></div>
    <input class="c-Input" style="width: 300px;"  placeholder="https://image.nostr.build/image123.jpg"  v-model="urlinput">
    </div>


  </div>
</details>
  </div>
  <br>


          <ModalComponent :isOpen="isModalOpened" @modal-close="closeModal" @submit="submitHandler" name="first-modal">
            <template #header>Share your creation on Nostr  <br> <br></template>

            <template #content>
              <textarea  v-model="modalcontent" className="d-Input" style="height: 300px;">{{modalcontent}}</textarea>






            </template>


            <template #footer>
            <div>



                                <VueDatePicker :min-date="new Date()" :teleport="false" :dark="true" position="right" className="bg-base-200 inline-flex flex-none" style="width: 220px;" v-model="datetopost"></VueDatePicker>

              <button className="v-Button" @click="schedule(modalcontent)"   @click.stop="closeModal"><img width="25px" style="margin-right: 5px" src="../../public/shipyard.ico"/>Schedule Note with Shipyard DVM</button>

               <br>
              or
              <br>
                <button className="v-Button" style="margin-bottom: 0px" @click="post_note(modalcontent)"   @click.stop="closeModal"><img  width="25px" style="margin-right: 5px;" src="../../public/favicon.ico"/>Post Note now</button>
                </div>



            </template>
          </ModalComponent>

  <div class="max-w-5xl relative space-y-3">
    <div class="grid grid-cols-1 gap-6">

        <div className="card w-70 bg-base-100 shadow-xl flex flex-col"   v-for="dvm in store.state.imagedvmreplies"
            :key="dvm.id">




        <div className="card-body">

<div className="playeauthor-wrapper">
  <figure  className="w-20">
       <img className="avatar" :src="dvm.image"  alt="DVM Picture" />
  </figure>


          <h2 className="card-title">{{ dvm.name }}</h2>
  </div>
          <h3 class="fa-cut" >{{ dvm.about }}</h3>



          <div className="card-actions justify-end mt-auto" >

              <div className="tooltip mt-auto" :data-tip="dvm.status">


                <button v-if="dvm.status === 'processing'" className="btn">Processing</button>
                <button v-if="dvm.status === 'finished'" className="btn">Done</button>
                <button v-if="dvm.status === 'paid'" className="btn">Paid, waiting for DVM..</button>
                <button v-if="dvm.status === 'error'" className="btn">Error</button>
                <button v-if="dvm.status === 'payment-required'" className="zap-Button" @click="zap(dvm.bolt11);">{{ dvm.amount/1000 }} Sats</button>


          </div>

        </div>
            <figure className="w-full" >
            <img  v-if="dvm.result" :src="dvm.result"  className="tooltip" data-top='Click to copy url' height="200" alt="DVM Picture" @click="copyurl(dvm.result)"/>
           </figure>
           <div  v-if="dvm.result && store.state.pubkey.toHex() !== Keys.parse('ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e').publicKey.toHex()" >
                 <button @click="openModal('Look what I created on noogle.lol\n\n' +  dvm.result)"  class="w-8 h-8 rounded-full bg-nostr border-white border-1 text-white flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-offset-2  focus:ring-black tooltip" data-top='Share' aria-label="make note" role="button">
                                    <svg  xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-pencil" width="20" height="20" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                                        <path stroke="none" d="M0 0h24v24H0z"></path>
                                        <path d="M4 20h4l10.5 -10.5a1.5 1.5 0 0 0 -4 -4l-10.5 10.5v4"></path>
                                        <line x1="13.5" y1="6.5" x2="17.5" y2="10.5"></line>
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

@media (min-width: 1024px) {

  .greetings h1,
  .greetings h3 {
    text-align: center;
  }
}
</style>
