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
import {computed, watch} from "vue";
import deadnip89s from "@/components/data/deadnip89s.json";
import {data} from "autoprefixer";
import {requestProvider} from "webln";
import Newnote from "@/components/Newnote.vue";
import {post_note, schedule, copyurl, copyinvoice, sleep, nextInput} from "../components/helper/Helper.vue"
import amberSignerService from "./android-signer/AndroidSigner";
import { ref } from "vue";
import ModalComponent from "../components/Newnote.vue";
import VueDatePicker from "@vuepic/vue-datepicker";
import {timestamp} from "@vueuse/core";
import NoteTable from "@/components/NoteTable.vue";

let dvms =[]
async function summarizefeed(eventids) {

   try {
     if(store.state.pubkey === undefined || localStorage.getItem('nostr-key-method') === "anon"){
               miniToastr.showMessage("In order to receive personalized recommendations, sign-in first.", "Not signed in.", VueNotifications.types.warn)
          return
     }

        dvms = []

        store.commit('set_summarization_dvms', dvms)
        let client = store.state.client
        let content = "NIP 90 Content Discovery request"
        let kind = 5001

         let tags = []
         for (const tag of eventids){
           try{
              tags.push(["i", tag.id.toHex(), "event"])
           }
           catch{}
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
        }
        else {

          let tags_t = []
          for (let tag of tags){
            tags_t.push(Tag.parse(tag))
          }
          let evt = new EventBuilder(kind, content, tags_t)
          res = await client.sendEventBuilder(evt);
          requestid = res.toHex();
          console.log(res)


        }

        store.commit('set_current_request_id_summarization', requestid)
        if (!store.state.summarizationhasEventListener){
           listen()
           store.commit('set_summariarizationEventListener', true)
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

    const filter = new Filter().kinds([7000, 6001]).pubkey(pubkey).since(Timestamp.now());
    await client.subscribe([filter]);

    const handle = {
        // Handle event
        handleEvent: async (relayUrl, event) => {
              if (store.state.summarizationhasEventListener === false){
                return true
              }
            //const dvmname =  getNamefromId(event.author.toHex())
            console.log("Received new event from", relayUrl);
              console.log(event.asJson())
           let resonsetorequest = false
            sleep(1000).then(async () => {
              for (let tag in event.tags) {
                if (event.tags[tag].asVec()[0] === "e") {

                  if (event.tags[tag].asVec()[1] === store.state.requestidSummarization) {
                    resonsetorequest = true
                  }
                }

              }
              if (resonsetorequest === true) {
                if (event.kind === 7000) {


                  try {
                    console.log("7000: ", event.content);
                    console.log("DVM: " + event.author.toHex())

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

                         dvms.push(jsonentry)
                    }
                    /*if (event.content !== ""){
                      status = event.content
                    }*/

                    dvms.find(i => i.id === jsonentry.id).status = status
                    store.commit('set_summarization_dvms', dvms)

                  } catch (error) {
                    console.log("Error: ", error);
                  }


                }


                 else if (event.kind === 6001){
                   console.log(event.content)
                    dvms.find(i => i.id === event.author.toHex()).result = event.content
                    dvms.find(i => i.id === event.author.toHex()).status = "finished"
                    store.commit('set_summarization_dvms', dvms)
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
          store.commit('set_summarization_dvms', dvms)
    }
    catch(err){
          console.log(err)
          await copyinvoice(invoice)
    }

  }


}


defineProps({
  events: {
    type: Array,
    required: false
  },
})



const isModalOpened = ref(false);
const modalcontent = ref("");
const datetopost = ref(Date.now());


const openModal = result => {
  datetopost.value = Date.now();
  isModalOpened.value = true;
  modalcontent.value = resevents
};
const closeModal = () => {
  isModalOpened.value = false;
};


const ttest = result => {

  summarizefeed(result)
}

const submitHandler = async () => {


}



</script>

<!--  font-thin bg-gradient-to-r from-white to-nostr bg-clip-text text-transparent -->

<template>

  <div class="greetings">
    <h1 class="text-7xl font-black tracking-wide">Noogle</h1>
    <h3 class="text-7xl font-black tracking-wide">Summarization</h3>

    <h3>
     <br>
     <button class="v-Button"  @click="summarizefeed($props.events)">Summarize Results</button>
    </h3>

  </div>
  <br>
<div class="overflow-y-auto scrollbar w-full" style="max-height: 60pc">


  <div class=" relative space-y-3">
    <div class="grid grid-cols-1 gap-4 "  >

        <div className="card w-70 bg-base-100 shadow-xl"   v-for="dvm in store.state.summarizationdvms"
            :key="dvm.id">




        <div className="card-body">

<div className="playeauthor-wrapper">
  <figure  className="w-20">
       <img className="avatar"  v-if="dvm.image" :src="dvm.image"  alt="DVM Picture" />
       <img class="avatar" v-else src="@/assets/nostr-purple.svg" />
  </figure>


          <h2 className="card-title">{{ dvm.name }}</h2>
  </div>
          <h3 class="fa-cut" >{{ dvm.about }}</h3>



          <div className="card-actions justify-end mt-auto" >

              <div className="tooltip mt-auto" :data-tip="dvm.status">


                <button v-if="dvm.status !== 'finished' && dvm.status !== 'paid' && dvm.status !== 'payment-required' && dvm.status !== 'error'"  className="btn">{{dvm.status}}</button>
                <button v-if="dvm.status === 'finished'" className="btn">Done</button>
                <button v-if="dvm.status === 'paid'" className="btn">Paid, waiting for DVM..</button>
                <button v-if="dvm.status === 'error'" className="btn">Error</button>
                <button v-if="dvm.status === 'payment-required'" className="zap-Button" @click="zap(dvm.bolt11);">{{ dvm.amount/1000 }} Sats</button>


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


    <details v-if="dvm.status === 'finished'" class="collapse bg-base">
  <summary class="collapse-title  "><div class="btn">Show/Hide Results</div></summary>
  <div class="collapse-content font-size-0" className="z-10" id="collapse">

     <p>{{dvm.result}}</p>


    </div>
</details>


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
