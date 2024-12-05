<template>

  <div class="flex flex-row gap-6 items-center">
    <Logo/>
    <div class="flex flex-col gap-2">
      <h1 class="text-7xl font-black tracking-wide">About</h1>
      <h2 class="text-4xl font-black tracking-wide">Nostr NIP 90 Data Vending Machines</h2>
      <div class="text-lg text-default">
        <!--    There are many things that make using DVMs a bit of a magical experience. -->
      </div>
    </div>
  </div>
  <br><br>

  <div class="card card-compact rounded-box bg-black/30">
    <div class="card-body">
      <div class="card-title text-base-100-content font-bold">
        What is this?
      </div>
      <p>Data Vending Machines are data-processing tools on top of the Nostr protocol.
      </p>
      <p>
        You give them some data, sometimes a few sats, and they give you back some data.</p>
      <p>
        This page is just a demo client, showcasing a variety of DVM use-cases. Search Content, Search Profiles, Content
        Discovery, Summarization of events, Image Generation, Scheduling Notes.

      </p>
      <p>
        There's an ever growing number of tasks added to the protocol. The current list of tasks can be found <a
          class="purple" href="https://www.data-vending-machines.org/" target="_blank">here</a>.
      </p>
      <p>
        These DVMs are not running or being hosted on this site. Instead, the DVMs communicate via Nostr and are
        available to any App or Client that wants to interact with them.
        Want your app or website to support any of these tasks? See <a class="purple" href="https://github.com/nostr-protocol/nips/blob/master/90.md"
                                                                       target="_blank">NIP90</a>
        for more details.
      </p>
      <p>
        Got interested in building your own DVM and provide it to the whole world? There's OpenSource frameworks to
        start with, for example <a class="purple" href="https://github.com/believethehype/nostrdvm" target="_blank">NostrDVM</a>
        in Python.
      </p>

      <p>
        A List of all DVMs that have a NIP89 announcement is available below, ordered by latest announcement.
      </p>
    </div>

  </div>


  <br><br>

  <div class="grid gap-5">
    <div v-for="dvm in store.state.nip89dvms" :key="dvm.id" className="card  bg-base-200 shadow-xl"
         style="height: 300px">
      <!--   -->


      <!-- <div class="card bg-base-100 shadow-xl image-full"  style="height: 400px">
        <figure><img v-if="dvm.image"  :src="dvm.image"    style=" width: 100%; object-fit: cover;"
       :alt="dvm.name" onerror="this.src='https://noogle.lol/favicon.ico'"/></figure>
        <div class="card-body">
             <div style="margin-left: auto; margin-right: 10px;">
         <p v-if="dvm.amount.toString().toLowerCase()==='free'" class="badge bg-nostr">Free</p>
          <p v-if="dvm.amount.toString().toLowerCase()==='flexible'" class="badge bg-nostr2" >Flexible</p>

         <p v-if="dvm.amount.toString().toLowerCase()==='subscription'" class="badge bg-orange-500">Subscription</p>
         <p v-if="dvm.amount.toString()===''" ></p>
         <p v-if="!isNaN(parseInt(dvm.amount))" class="text-sm  text-gray-600 rounded" ><div class="flex"><svg style="margin-top:3px" xmlns="http://www.w3.org/2000/svg" width="14" height="16" fill="currentColor" class="bi bi-lightning" viewBox="0 0 16 20">
        <path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641zM6.374 1 4.168 8.5H7.5a.5.5 0 0 1 .478.647L6.78 13.04 11.478 7H8a.5.5 0 0 1-.474-.658L9.306 1z"/></svg> {{dvm.amount/1000}}</div></p>
        </div>
          <div class="">


          <h2 class="card-title">{{ dvm.name }}</h2>
          <h3 class="fa-cut text-gray" >Kind: {{ dvm.kind }}</h3>

                <h3 class="fa-cut" v-html="StringUtil.parseHyperlinks(dvm.about)"></h3>

                </div>
            <div class="card-actions justify-end ">
           <button className="btn " style="margin-bottom: 10px" @click="copyDoiToClipboard(dvm.event);">Copy Event Json</button>
          </div>
        </div>
      </div> -->


      <div class="card card-side bg-black/20 shadow-xl" style="height: 300px">


        <figure style="max-width: 20%; flex:  fit-content; background-size: cover;">
          <img v-if="dvm.picture" :alt="dvm.name" :src="dvm.picture" onerror="this.src='https://noogle.lol/favicon.ico'"
               style=" width: 90%; object-fit: cover;"/>
        </figure>
        <div class="card-body">
          <div style="margin-left: auto; margin-right: 10px;">
            <p v-if="dvm.amount.toString().toLowerCase()==='free'" class="badge bg-nostr">Free</p>
            <p v-if="dvm.amount.toString().toLowerCase()==='flexible'" class="badge bg-nostr2">Flexible</p>
            <p v-if="dvm.subscription" class="badge text-white bg-gradient-to-br from-pink-500 to-orange-400">
              Subscription</p>

            <p v-if="dvm.amount.toString()===''"></p>
            <p v-if="!isNaN(parseInt(dvm.amount))" class="text-sm  text-gray-600 rounded">
              <div class="flex">
                <svg class="bi bi-lightning" fill="currentColor" height="16" style="margin-top:3px"
                     viewBox="0 0 16 20" width="14" xmlns="http://www.w3.org/2000/svg">
                  <path
                      d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641zM6.374 1 4.168 8.5H7.5a.5.5 0 0 1 .478.647L6.78 13.04 11.478 7H8a.5.5 0 0 1-.474-.658L9.306 1z"/>
                </svg>
                {{ dvm.amount / 1000 }}
              </div>
            </p>
          </div>
          <h2 class="card-title">{{ dvm.name }}</h2>
          <h3 class="text-gray">Kind: {{ dvm.kind }}</h3>

          <h4 v-if="dvm.about !== null" class="fa-cut" style="max-width: 200px" v-html="dvm.about"></h4>
          <div class="card-actions justify-end">
            <button className="btn" @click="copyDoiToClipboard(dvm.event);">Copy Event Json</button>
          </div>
        </div>
      </div>


      <!--
       <h2 className="card-title justify-center">{{ dvm.name }}</h2>
         <div className="card-body">




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

                   <button className="btn glass" @click="copyDoiToClipboard(dvm.event);">Copy Event Json</button>
               </div>
             </div>
         </div>-->
    </div>
  </div>
</template>

<script>

import '../app.css'
import store from "@/store.js";
import {Keys} from "@rust-nostr/nostr-sdk";
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";
import StringUtil from "@/components/helper/string.ts";

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
    copyDoiToClipboard(doi) {
      navigator.clipboard.writeText(doi)
      miniToastr.showMessage("", "Copied Nip89 Event to clipboard", VueNotifications.types.info)

    },
  },


  async mounted() {

  },

  setup() {

  }
}
</script>
<style scoped>
donate {

  position: fixed;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);;
  grid-area: footer;
  width: 100vw;
  height: 32px;

  z-index: 10;
  text-align: center;
}
</style>
