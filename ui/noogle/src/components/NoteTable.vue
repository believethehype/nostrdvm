<template>
  <EasyDataTable class="customize-table" header-text-direction="left"  table-class-name="customize-table"
                 :headers="headers"
                 :items="data"
                 :sort-by="sortBy"
                 :sort-type="sortType">
   <template #item-content="{content, author, authorurl, avatar, indicator, links, lud16, id, authorid, zapped, zapAmount, reacted, reactions}">

   <div class="playeauthor-wrapper">


    <img class="avatar" v-if="avatar" :src="avatar" alt="Avatar" onerror="this.src='https://noogle.lol/favicon.ico'" />
     <img class="avatar" v-else src="@/assets/nostr-purple.svg" />

     <a class="purple" :href="authorurl" target="_blank">{{ author }}</a>
    <div class="time">
          {{indicator.time.split("T")[1].split("Z")[0].trim()}}
          {{indicator.time.split("T")[0].split("-")[2].trim()}}.{{indicator.time.split("T")[0].split("-")[1].trim()}}.{{indicator.time.split("T")[0].split("-")[0].trim().slice(2)}}
        </div>
   </div>
<!--.substr(0, 320) + "\u2026"}} -->

       <h3 v-html="StringUtil.parseImages(content)"></h3>
     <!-- <h3>{{StringUtil.parseImages(content)}}</h3> -->
   <!--<p>{{content.substr(0, 320) + "\u2026"}}</p> -->
        <div style="padding: 2px; text-align: left;" >
          <a class="menusmall" :href="links.uri" target="_blank">Client</a>
          <a class="menusmall" :href="links.njump" target="_blank">NJump</a>
         <!--<a class="menusmall" :href="links.highlighter" target="_blank">Highlighter</a> -->
          <a class="menusmall":href="links.nostrudel" target="_blank">Nostrudel</a>

          <div  class="flex" >

          <div  class="flex" style="margin-left: auto; margin-right: 5px;" v-if="!reacted"  @click="react(id, authorid)">
     <div  style="margin-left: auto; margin-right: 5px; float: left;">
         <svg  style="margin-top:4px"  width="14" height="12" xmlns="http://www.w3.org/2000/svg" class="bi bi-heart" fill-rule="evenodd" fill="currentColor" viewBox="0 0 20 25" clip-rule="evenodd"><path d="M12 21.593c-5.63-5.539-11-10.297-11-14.402 0-3.791 3.068-5.191 5.281-5.191 1.312 0 4.151.501 5.719 4.457 1.59-3.968 4.464-4.447 5.726-4.447 2.54 0 5.274 1.621 5.274 5.181 0 4.069-5.136 8.625-11 14.402m5.726-20.583c-2.203 0-4.446 1.042-5.726 3.238-1.285-2.206-3.522-3.248-5.719-3.248-3.183 0-6.281 2.187-6.281 6.191 0 4.661 5.571 9.429 12 15.809 6.43-6.38 12-11.148 12-15.809 0-4.011-3.095-6.181-6.274-6.181"/></svg> </div>
  <div>
    <p style="float: left;">{{reactions}}</p>
  </div>
</div>
            <div  class="flex" v-if="reacted"  style="margin-left: auto; margin-right: 5px;" @click="react(id, authorid)">
     <div  style="margin-left: auto; margin-right: 5px; float: left;">
          <svg   style="margin-top:4px" xmlns="http://www.w3.org/2000/svg" width="14" height="12" class="bi bi-heart fill-nostr" viewBox="0 0 20 25"><path d="M12 4.419c-2.826-5.695-11.999-4.064-11.999 3.27 0 7.27 9.903 10.938 11.999 15.311 2.096-4.373 12-8.041 12-15.311 0-7.327-9.17-8.972-12-3.27z"/></svg> </div>

              <div>
    <p className="text-nostr" style="float: left;">{{reactions}}</p>
  </div>
</div>


<div  class="flex" v-if="!zapped"  @click="zap_local(lud16, id, authorid)">
     <div  style="margin-left: auto; margin-right: 5px; float: left;">
          <svg  style="margin-top:4px" xmlns="http://www.w3.org/2000/svg" width="14" height="16" fill="currentColor" class="bi bi-lightning" viewBox="0 0 16 20">
              <path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641zM6.374 1 4.168 8.5H7.5a.5.5 0 0 1 .478.647L6.78 13.04 11.478 7H8a.5.5 0 0 1-.474-.658L9.306 1z"/>

 </svg> </div>
  <div>
    <p style="float: left;">{{zapAmount/1000}}</p>
  </div>
</div>
<div  class="flex" v-if="zapped" @click="zap_local(lud16, id, authorid)"  >
     <div style="margin-left: auto; margin-right: 5px;">
          <svg style="margin-top:4px" xmlns="http://www.w3.org/2000/svg" width="14" height="16" class="bi bi-lightning fill-amber-400" viewBox="0 0 16 20">
    <path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641z"/>
          </svg></div>
    <div>
    <p style="float: left;" className="text-amber-400">{{zapAmount/1000}}</p>
  </div>
</div>

      </div>
          </div>
     </template>


      </EasyDataTable>
<p></p>
<!-- <p>{{data}}</p> -->

</template>

<script lang="ts" setup>


import type {Header, Item, SortType} from "vue3-easy-data-table";
import store from '../store';
import {types} from "sass";
import Null = types.Null;
import StringUtil from "@/components/helper/string";
import {copyinvoice, createBolt11Lud16, parseandreplacenpubs, zaprequest} from "@/components/helper/Helper.vue";
import {requestProvider} from "webln";
import {Event, EventBuilder, EventId, PublicKey} from "@rust-nostr/nostr-sdk";
import amberSignerService from "@/components/android-signer/AndroidSigner";
import zap, {zap_lud16} from "@/components/helper/Zap.vue";


const props =  defineProps<{
  data: any[]

}>()


const sortBy: String = "index";
const sortType: SortType = "asc";

const headers: Header[] = [
  { text: "Results:", value: "content", fixed: true},
 // { text: "Time", value: "indicator.index", sortable: true, },
];


async function react(eventid, authorid){


   let event_id = EventId.parse(eventid)
    let public_key = PublicKey.parse(authorid);
    let signer = store.state.signer
    let client = store.state.client
        let objects =  (props.data.find(x=> x.id === eventid))
          if (objects !== undefined){
                if(!objects.reacted ){

                   if (localStorage.getItem('nostr-key-method') === 'android-signer') {
                          let draft = {
                            content: "🧡",
                            kind: 7,
                            pubkey: store.state.pubkey.toHex(),
                            tags: [],
                            createdAt: Date.now()
                          };

                          let res = await amberSignerService.signEvent(draft)
                          await client.sendEvent(Event.fromJson(JSON.stringify(res)))
                          let requestid = res.id;
                        }
                   else {
                     let event = EventBuilder.reaction(event_id, public_key, "🧡")
                        let res = await client.sendEventBuilder(event);
                   }

                    objects.reacted = true
                    objects.reactions += 1
                   }

                }

}

async function zap_local(lud16, eventid, authorid){

  let success = await zap_lud16(lud16, eventid, authorid)
  if (success){
     let objects = props.data.find(x=> x.id === eventid)
          if (objects !== undefined){
            objects.zapped = true
            objects.zapAmount += 21000
  }

    }
}


</script>

<style scoped>
.operation-wrapper .operation-icon {
  width: 20px;
  cursor: pointer;
}
.playeauthor-wrapper {
  padding: 6px;
  display: flex;
  align-items: center;
  justify-items: center;
}

.menusmall {
  @apply btn text-gray-600 bg-transparent border-transparent tracking-wide ;


  }

.vue3-easy-data-table__footer.previous-page__click-button{
  height:100px
}

.time {
  padding: 6px;
  display: flex;
  font-size: 1em;
  align-items: center;
  justify-items: center;
}
.avatar {
  margin-right: 10px;
  display: inline-block;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: inset 0 4px 4px 0 rgb(0 0 0 / 10%);
}
.customize-table {
  width: auto;
  --easy-table-border: 2px solid bg-base;
  --easy-table-row-border: 1px solid #000000;

  --easy-table-header-font-size: 14px;
  --easy-table-header-height: 50px;
  --easy-table-header-font-color: bg-accent;
  --easy-table-header-background-color: bg-base;

  --easy-table-header-item-padding: 10px 15px;

  --easy-table-body-even-row-font-color: bg-accenet;
  --easy-table-body-even-row-background-color: bg-base;

  --easy-table-body-row-font-color: bg-accent;
  --easy-table-body-row-background-color: bg-base;
  --easy-table-body-row-height: 50px;
  --easy-table-body-row-font-size: 14px;

  --easy-table-body-row-hover-font-color: bg-accent;
  --easy-table-body-row-hover-background-color: bg-base;

  --easy-table-body-item-padding: 10px 15px;

  --easy-table-footer-background-color: bg-base;
  --easy-table-footer-font-color: bg-accent;
  --easy-table-footer-font-size: 14px;
  --easy-table-footer-padding: 0px 10px;
  --easy-table-footer-height: 50px;

  --easy-table-rows-per-page-selector-width: 70px;
  --easy-table-rows-per-page-selector-option-padding: 10px;
  --easy-table-rows-per-page-selector-z-index: 1;

  --easy-table-scrollbar-track-color: bg-base;
  --easy-table-scrollbar-color: bg-base;
  --easy-table-scrollbar-thumb-color: bg-base;
  --easy-table-scrollbar-corner-color: bg-base;

  --easy-table-loading-mask-background-color: #2d3a4f;
}
</style>