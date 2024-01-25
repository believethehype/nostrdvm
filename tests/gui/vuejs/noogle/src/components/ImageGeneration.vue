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
  Nip19Event, Alphabet
} from "@rust-nostr/nostr-sdk";
import store from '../store';
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";
import searchdvms from './data/searchdvms.json'
import {computed, watch} from "vue";
import countries from "@/components/data/countries.json";
import deadnip89s from "@/components/data/deadnip89s.json";
import {data} from "autoprefixer";
import {requestProvider} from "webln";

let dvms =[]
let searching = false

let listener = false



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
        let tags = []
        console.log(message)
        tags.push(Tag.parse(["i", message, "text"]))

        let evt = new EventBuilder(5100, "NIP 90 Image Generation request", tags)
        let res = await client.sendEventBuilder(evt)
        miniToastr.showMessage("Sent Request to DVMs", "Awaiting results", VueNotifications.types.warn)
        searching = true
        if (!store.state.imagehasEventListener){
               listen()
           store.commit('set_imagehasEventListener', true)
        }
        else{
          console.log("Already has event listener")
        }

        console.log(res)


      } catch (error) {
        console.log(error);
      }
}

async function  listen() {
    listener = true
    let client = store.state.client
    let pubkey = store.state.pubkey

    const filter = new Filter().kinds([7000, 6100]).pubkey(pubkey).since(Timestamp.now());
    await client.subscribe([filter]);

    const handle = {
        // Handle event
        handleEvent: async (relayUrl, event) => {
              if (store.state.imagehasEventListener === false){
                return true
              }
            //const dvmname =  getNamefromId(event.author.toHex())
            console.log("Received new event from", relayUrl);
            if (event.kind === 7000) {
                try {
                    console.log("7000: ", event.content);
                    console.log("DVM: " + event.author.toHex())
                    searching = false
                    //miniToastr.showMessage("DVM: " + dvmname, event.content, VueNotifications.types.info)

                  let status = "unknown"
                   let jsonentry = {id: event.author.toHex(), kind: "", status: status, result: "", name: event.author.toBech32(), about: "", image: "", amount: 0, bolt11: ""}

                   for (const tag in event.tags){
                     if (event.tags[tag].asVec()[0] === "status"){
                       status = event.tags[tag].asVec()[1]
                     }

                            if (event.tags[tag].asVec()[0] === "amount"){
                                jsonentry.amount = event.tags[tag].asVec()[1]
                              if (event.tags[tag].asVec().length > 2){
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
                  if (dvms.filter(i => i.id === jsonentry.id ).length === 0){
                      dvms.push(jsonentry)
                  }


                  dvms.find(i => i.id === jsonentry.id).status = status

                  store.commit('set_imagedvm_results', dvms)



                } catch (error) {
                    console.log("Error: ", error);
                }
            }
            else if(event.kind === 6100) {
              let entries = []
              console.log("6100:", event.content);

              //miniToastr.showMessage("DVM: " + dvmname, "Received Results", VueNotifications.types.success)
              dvms.find(i => i.id === event.author.toHex()).result = event.content
              dvms.find(i => i.id === event.author.toHex()).status = "finished"
              store.commit('set_imagedvm_results', dvms)
            }
        },
        // Handle relay message
        handleMsg: async (relayUrl, message) => {
            //console.log("Received message from", relayUrl, message.asJson());
        }
    };

    client.handleNotifications(handle);
}




function nextInput(e) {
  const next = e.currentTarget.nextElementSibling;
  if (next) {
    next.focus();

  }
}

    async function zap(invoice) {
      let webln;

        //this.dvmpaymentaddr =  `https://chart.googleapis.com/chart?cht=qr&chl=${invoice}&chs=250x250&chld=M|0`;
        //this.dvminvoice = invoice


      try {
        webln = await requestProvider();
      } catch (err) {
          await this.copyinvoice(invoice)
      }

      if (webln) {

        let response = await webln.sendPayment(invoice)
        console.log(response)
        for (const dvm of dvms){
          console.log(dvm.bolt11 + "   " + invoice)
        }

        dvms.find(i => i.bolt11 === invoice).status = "paid"
        store.commit('set_imagedvm_results', dvms)
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



</script>



<template>

  <div class="greetings">
   <br>
    <br>
    <h1 class="text-7xl font-black tracking-wide">Noogle</h1>
    <h1 class="text-7xl font-black tracking-wide">Image Generation</h1>
    <h2 class="text-base-200-content text-center tracking-wide text-2xl font-thin">
    Generate Images, the decentralized way</h2>
    <h3>
     <br>
     <input class="c-Input" autofocus placeholder="A purple Ostrich..." v-model="message" @keyup.enter="generate_image(message)" @keydown.enter="nextInput">
     <button class="v-Button"  @click="generate_image(message)">Generate Image</button>
    </h3>

  </div>
  <br>

  <div class="max-w-5xl relative space-y-3">
    <div class="grid grid-cols-2 gap-6">
        <div className="card w-70 bg-base-100 shadow-xl flex flex-col"   v-for="dvm in store.state.imagedvmreplies"
            :key="dvm.id">

        <figure class="w-full">
          <img v-if="dvm.result" :src="dvm.result" height="200" alt="DVM Picture" />
          <img v-if="!dvm.result" :src="dvm.image" height="200" alt="DVM Picture" />
        </figure>


        <div className="card-body">
          <h2 className="card-title">{{ dvm.name }}</h2>
          <h3 >{{ dvm.about }}</h3>



          <div className="card-actions justify-end mt-auto" >

              <div className="tooltip mt-auto" :data-tip="dvm.card ">


                <button v-if="dvm.status === 'processing'" className="btn">Processing</button>
                <button v-if="dvm.status === 'finished'" className="btn">Done</button>
                <button v-if="dvm.status === 'paid'" className="btn">Paid, waiting for DVM..</button>
                <button v-if="dvm.status === 'error'" className="btn">Error</button>
                <button v-if="dvm.status === 'payment-required'" className="zap-Button" @click="zap(dvm.bolt11);">{{ dvm.amount/1000 }} Sats</button>


          </div>

        </div>
           </div>
          <br>
      </div>
    </div>
  </div>


</template>

<style scoped>

.zap-Button{
  @apply btn hover:bg-amber-400;
  bottom: 0;
}

.v-Button {
  @apply bg-nostr hover:bg-nostr2 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-black px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
   height: 48px;
   margin: 5px;
}

.c-Input {
    @apply bg-black hover:bg-gray-900 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;

  width: 350px;
  height: 48px;
  color: white;
  background: black;
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
