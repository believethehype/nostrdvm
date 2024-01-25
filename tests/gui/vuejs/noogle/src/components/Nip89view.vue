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
import {Alphabet, ClientBuilder, ClientSigner, Filter, Keys, NostrDatabase, Tag} from "@rust-nostr/nostr-sdk";
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";

import deadnip89s from './data/deadnip89s.json'





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

    },

  setup() {

  }
}
</script>