<template>

  <div class="max-w-5xl relative space-y-3">
    <div v-if="store.state.nip89dvms.length === 0">
      <p>Loading Nip89s.. </p>
       <span className="loading loading-dots loading-lg"  ></span>
    </div>
    <div class="grid grid-cols-2 gap-6">
        <div className="card w-70 bg-base-100 shadow-xl"  v-for="dvm in store.state.nip89dvms"
            :key="dvm.name">
        <figure><img :src="dvm.image" alt="DVM Picture" /></figure>
        <div className="card-body">
          <h2 className="card-title">{{ dvm.name }}</h2>
          <p>  {{ dvm.about }}</p>
           <p>Kind: {{ dvm.kind }}</p>
          <div className="card-actions justify-end">
        <div className="tooltip" :data-tip="dvm.event">
         <button className="btn" @click="copyDoiToClipboard(dvm.event);">Copy Event</button>
        </div>
          </div>
        </div>
          <br>
      </div>
            </div>



    </div>

</template>

<script>

import '../app.css'
import store from "@/store.js";
import {ClientBuilder, ClientSigner, Filter, Keys, NostrDatabase, Tag} from "@rust-nostr/nostr-sdk";
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";

import deadnip89s from './data/deadnip89s.json'

async function getnip89s(){

        //let keys = Keys.generate()
        let keys = Keys.fromSkStr("ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e")

        let signer = ClientSigner.keys(keys) //TODO store keys
        let database =  await NostrDatabase.open("nip89.db")
        let client = new ClientBuilder().database(database).signer(signer).build()
        //await client.addRelay("wss://nos.lol");
        await client.addRelay("wss://relay.f7z.io")
        await client.addRelay("wss://pablof7z.nostr1.com")
        //await client.addRelay("wss://relay.nostr.net")
        await client.addRelay("wss://relay.nostr.band");
        //await client.addRelay("wss://nostr-pub.wellorder.net")
        await client.connect();


        const filter = new Filter().kind(31990)
        //await client.reconcile(filter);
        //const filterl = new Filter().kind(31990)
        //let evts = await client.database.query([filterl])
        let evts = await client.getEventsOf([filter], 3)
        for (const entry of evts){
          for (const tag in entry.tags){
            if (entry.tags[tag].asVec()[0] === "k")
              console.log(entry.id.toHex())
              if(entry.tags[tag].asVec()[1] >= 5000 && entry.tags[tag].asVec()[1] <= 5999 &&  deadnip89s.filter(i => i.id === entry.id.toHex() ).length === 0) {   // blocklist.indexOf(entry.id.toHex()) < 0){

                console.log(entry.tags[tag].asVec()[1])

                try {

                    let jsonentry = JSON.parse(entry.content)
                      if (jsonentry.picture){
                        jsonentry.image = jsonentry.picture
                      }
                      jsonentry.event = entry.asJson()
                    jsonentry.kind = entry.tags[tag].asVec()[1]
                   nip89dvms.push(jsonentry);
                }
                catch (error){
                  console.log(error)
                }

              }
           }
        }
        store.commit('set_nip89dvms', nip89dvms)

        return nip89dvms


    }
let nip89dvms = []


export default {
  computed: {
    store() {
      return store
    }
  },
  methods: {
  copyDoiToClipboard (doi) {
    navigator.clipboard.writeText(doi)
    miniToastr.showMessage("", "Copied Nip89 Event to clipboard", VueNotifications.types.info)

  },
  },


async mounted(){
      await getnip89s()



    },

  setup() {

  }
}
</script>