<template>
<div class="grid gap-6 ">
    <div className="card w-70 bg-base-100 shadow-xl"   v-for="dvm in store.state.nip89dvms"
        :key="dvm.id">
   <br>
    <h2 className="card-title justify-center">{{ dvm.name }}</h2>
      <div className="card-body">
        <div className="playeauthor-wrapper flex align-top">
            <figure  className="w-40">
                 <img className="avatar" :src="dvm.image"  alt="DVM Picture" />
            </figure>
        </div>
        <br>
          <h3 class="fa-cut" >{{ dvm.about }}</h3>
          <div className="card-actions justify-end mt-auto" >
             <div className="card-actions justify-end">
                <button className="btn" @click="copyDoiToClipboard(dvm.event);">Copy Event Json</button>
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