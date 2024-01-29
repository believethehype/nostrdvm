<template>

    <div class="max-w-5xl relative space-y-3">
    <div class="grid grid-cols-1 gap-6">

        <div className="card w-70 bg-base-100 shadow-xl flex flex-col"   v-for="dvm in store.state.nip89dvms"
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

             <div className="card-actions justify-end">
        <div className="tooltip" :data-tip="dvm.event">
         <button className="btn" @click="copyDoiToClipboard(dvm.event);">Copy Event</button>
        </div>

        </div>

           </div>

      </div>

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
    Keys() {
      return Keys
    },
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