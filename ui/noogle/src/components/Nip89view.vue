<template>

    <div class="flex flex-row gap-6 items-center">
        <Logo />
        <div class="flex flex-col gap-2">
            <h1 class="text-7xl font-black tracking-wide">About</h1>
              <h2 class="text-4xl font-black tracking-wide">Nostr NIP 90 Data Vending Machines</h2>
          <div class="text-lg text-default">
                There are many things that make using DVMs a bit of a magical experience.
            </div>
        </div>
    </div>
<br><br>
    <div class="grid grid-cols-1 gap-6">
     <!--    <div class="card card-compact rounded-box bg-black/30">
            <div class="card-body !text-base">
                <div class="card-title text-base-100-content font-bold">
                    Global improvements
                </div>
                <p>
                    Once a Nostr app supports DVMs that means that they get immediate access to all features,
                    algorithms, and crazy inventions <em>all</em> DVMs support.</p>
                <p>
                    Don't like your client's default <em>Trending</em> algorithm? Pick from hundreds of different
                    algorithms. Your Highlighter client doesn't work well when trying to read an obscure PDF?
                    Use a DVM that has better support for it.
                </p>
                <p>
                    You say the spam filtering in your client is too aggressive? or not aggressive enough? Just choose
                    from a different spam-filtering DVM!
                </p>
            </div>
        </div>

        <div class="card card-compact rounded-box bg-black/30">
            <div class="card-body !text-base">
                <div class="card-title text-base-100-content font-bold">
                    Long-tail
                </div>
                <p>
                    Because discoverability of these algorithms is solved by the very use of Nostr, we can easily imagine
                    a future where there are thousands of very specific, very niche and abundantly weird DVMs providing all
                    kinds of obscure functionalities.
                </p>
                <p>
                    Even if a DVM only had a handful of users, it would still be worth it for its users and for the DVM.
                </p>
            </div>
        </div>

        <div class="card card-compact rounded-box bg-black/30">
            <div class="card-body !text-base">
                <div class="card-title text-base-100-content font-bold">
                    Reusable results
                </div>
                <p>
                    Every time a Nostr client autotranslates a note, it pings a specific API endpoint to get the
                    result translated.
                </p>
                <p>
                    Over, and over. The same text being translated by each user.
                </p>
                <p>
                    Since Data Vending Machine results are public by default, once a note has been translated,
                    all clients can choose to reuse the same translation.
                </p>
            </div>
        </div> -->
          <div class="card card-compact rounded-box bg-black/30">
            <div class="card-body !text-base">
                <div class="card-title text-base-100-content font-bold">
                  What is this?
                </div>
              <p>Data Vending Machines are data-processing tools on top of th Nostr protocol.
                </p>
                 <p>
                You give them some data, a few sats, and they give you back some data.</p>
                <p>
                    This page is just a demo client, showcasing a variety of DVM use-cases. Search Content, Search Profiles, Discover Content, Summarize events, Generate Images, Schedule Notes.
                    There's an ever growing number of tasks added to the protocol.
                </p>
                <p>
                   These DVMs are not running or being hosted on this site. Instead, the DVMs communicate via Nostr and are available to any App or Client that wants to interact with them.
                    Want your app or website to support any of these tasks? See NIP90
                </p>
                <p>
                   A List of all DVMs that have a NIP89 announcement is available below, ordered by latest announcement.
                </p>
            </div>
        </div>
    </div>

<br><br>

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
