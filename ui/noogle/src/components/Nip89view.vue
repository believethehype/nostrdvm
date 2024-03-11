<template>
<div class="grid gap-6 ">
    <div className="card w-70 bg-base-200 shadow-xl"   v-for="dvm in store.state.nip89dvms"
        :key="dvm.id">
   <br>
    <h2 className="card-title justify-center">{{ dvm.name }}</h2>
      <div className="card-body">

  <div style="margin-left: auto; margin-right: 10px;">
   <p v-if="dvm.amount.toString().toLowerCase()==='free'" class="text-sm  text-gray-600 rounded" >Free</p>
    <p v-if="dvm.amount.toString().toLowerCase()==='flexible'" class="text-sm text-gray-600 rounded" >Flexible</p>

   <p v-if="dvm.amount.toString().toLowerCase()==='subscription'" class="text-sm  text-orange-400 rounded">Subscription</p>
   <p v-if="dvm.amount.toString()===''" ></p>
   <p v-if="!isNaN(parseInt(dvm.amount))" class="text-sm  text-gray-600 rounded" ><div class="flex"><svg style="margin-top:3px" xmlns="http://www.w3.org/2000/svg" width="14" height="16" fill="currentColor" class="bi bi-lightning" viewBox="0 0 16 20">
  <path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641zM6.374 1 4.168 8.5H7.5a.5.5 0 0 1 .478.647L6.78 13.04 11.478 7H8a.5.5 0 0 1-.474-.658L9.306 1z"/></svg> {{dvm.amount/1000}}</div></p>
  </div>


        <div className="playeauthor-wrapper flex align-top">
            <figure  className="w-40">
                 <img className="avatar" :src="dvm.image"  alt="DVM Picture" />
            </figure>
        </div>


        <br>
         <h3 class="fa-cut" >Kind: {{ dvm.kind }}</h3>

          <h3 class="fa-cut" v-html="StringUtil.parseHyperlinks(dvm.about)"></h3>
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
import {Alphabet, ClientBuilder, NostrSigner, Filter, Keys, NostrDatabase, Tag} from "@rust-nostr/nostr-sdk";
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";
import StringUtil from "@/components/helper/string.ts";

import deadnip89s from './data/deadnip89s.json'

export default {
  computed: {
    StringUtil() {
      return StringUtil
    },
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
<style scoped>


</style>
