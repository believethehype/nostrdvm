
<template>
  <EasyDataTable class="customize-table" header-text-direction="left"  table-class-name="customize-table"
                 :headers="headers"
                 :items="data"
                 :sort-by="sortBy"
                 :sort-type="sortType">


        <!--<template #expand="item">
      <div style="padding: 15px">
        <input class="c-Input" v-model="message">
         <button class="v-Button" v-if="!item.replied" @click="reply(item.id, item.author, message)">Reply</button>
         <button class="btn" v-if="item.replied" >Replied</button>
      </div>
    </template> -->
   <template #item-content="{content, author, authorurl, avatar, indicator, links, lud16, id, authorid, zapped, zapAmount, reacted, reactions, boosts, boosted, event, replied}">

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


  <div  class="flex" style="margin-right: 5px;" v-if="!reacted"  @click="react(id, authorid, event)">
     <div  style="margin-right: 5px;">
         <svg  style="margin-top:4px"  width="14" height="12" xmlns="http://www.w3.org/2000/svg" class="bi bi-heart" fill-rule="evenodd" fill="currentColor" viewBox="0 0 20 25" clip-rule="evenodd"><path d="M12 21.593c-5.63-5.539-11-10.297-11-14.402 0-3.791 3.068-5.191 5.281-5.191 1.312 0 4.151.501 5.719 4.457 1.59-3.968 4.464-4.447 5.726-4.447 2.54 0 5.274 1.621 5.274 5.181 0 4.069-5.136 8.625-11 14.402m5.726-20.583c-2.203 0-4.446 1.042-5.726 3.238-1.285-2.206-3.522-3.248-5.719-3.248-3.183 0-6.281 2.187-6.281 6.191 0 4.661 5.571 9.429 12 15.809 6.43-6.38 12-11.148 12-15.809 0-4.011-3.095-6.181-6.274-6.181"/></svg>
     </div>


  <div>
    <p style="float: left;">{{reactions}}</p>
  </div>
  </div>
  <div  class="flex" v-if="reacted"  style="margin-right: 5px;" @click="react(id, authorid, event)">
     <div  style="margin-left: auto; margin-right: 5px; float: left;">
          <svg   style="margin-top:4px" xmlns="http://www.w3.org/2000/svg" width="14" height="12" class="bi bi-heart fill-red-500" viewBox="0 0 20 25"><path d="M12 4.419c-2.826-5.695-11.999-4.064-11.999 3.27 0 7.27 9.903 10.938 11.999 15.311 2.096-4.373 12-8.041 12-15.311 0-7.327-9.17-8.972-12-3.27z"/></svg> </div>

              <div>
    <p className="text-red-500" style="float: left;">{{reactions}}</p>
  </div>
  </div>
  <div  class="flex" v-if="lud16 != null && lud16 != '' && !zapped" style="margin-right: 5px;"  @click="zap_local(lud16, id, authorid)">
     <div  style="margin-left: auto; margin-right: 5px; float: left;">
          <svg  style="margin-top:4px" xmlns="http://www.w3.org/2000/svg" width="14" height="16" fill="currentColor" class="bi bi-lightning" viewBox="0 0 16 20">
              <path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641zM6.374 1 4.168 8.5H7.5a.5.5 0 0 1 .478.647L6.78 13.04 11.478 7H8a.5.5 0 0 1-.474-.658L9.306 1z"/>

  </svg> </div>
  <div>
    <p style="float: left;">{{zapAmount/1000}}</p>
  </div>
  </div>
  <div  class="flex" v-if="lud16 != null && lud16 != '' && zapped"  style="margin-right: 5px;"  @click="zap_local(lud16, id, authorid)"  >
     <div style="margin-left: auto; margin-right: 5px;">
          <svg style="margin-top:4px" xmlns="http://www.w3.org/2000/svg" width="14" height="16" class="bi bi-lightning fill-amber-400" viewBox="0 0 16 20">
    <path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641z"/>
          </svg></div>
    <div>
    <p style="float: left;" className="text-amber-400">{{zapAmount/1000}}</p>
  </div>
  </div>
  <div  class="flex" v-if="!boosted"  @click="boost(id, authorid, event)">
  <div  style="margin-left: auto; margin-right: 5px; float: left;">
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="28" viewBox="0 0 20 34"><path class="bi" fill="currentColor" d="M19 7a1 1 0 0 0-1-1h-8v2h7v5h-3l3.969 5L22 13h-3zM5 17a1 1 0 0 0 1 1h8v-2H7v-5h3L6 6l-4 5h3z"/></svg>     </div>

  <div>
  <p  style="float: left;">{{boosts}}</p>
  </div>
  </div>
  <div  class="flex" v-if="boosted"  @click="boost(id, authorid, event)">
  <div  style="margin-left: auto; margin-right: 5px; float: left;">
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="28" viewBox="0 0 20 34">
    <path class="bi fill-green-700" d="M19 7a1 1 0 0 0-1-1h-8v2h7v5h-3l3.969 5L22 13h-3zM5 17a1 1 0 0 0 1 1h8v-2H7v-5h3L6 6l-4 5h3z"/>
  </svg>     </div>

  <div>
  <p className="text-green-700" style="float: left;">{{boosts}}</p>
  </div>
  </div>
  <details>
    <summary class="" style="  margin-right: 5px">

    <div style="margin-right: 5px; margin-left: 10px;margin-top: 4px"> <svg id="Capa_1"   fill="currentColor" height="14" viewBox="0 0 600 600" xmlns="http://www.w3.org/2000/svg"><g>
      <g id="ad">
<path d="m113.241 463.222-4.3-88.312c-68.332-36.05-108.941-95.703-108.941-160.522 0-52.154 26.017-101.029 73.259-137.619 46.512-36.024 108.215-55.864 173.741-55.864s127.229 19.84 173.742 55.865c47.242 36.59 73.259 85.465 73.259 137.619s-26.017 101.03-73.259 137.621c-46.512 36.023-108.215 55.863-173.742 55.863-1.889 0-3.843-.021-6.01-.067l-113.406 63.371c-9.113 4.959-14.343-.411-14.343-7.955zm133.759-423.021c-125.556 0-227.703 78.141-227.703 174.189 0 58.936 38.629 113.466 103.33 145.859 3.116 1.56 5.148 4.679 5.317 8.159l3.814 78.334 102.12-57.064c1.514-.852 3.232-1.275 4.968-1.222 3.108.084 5.698.124 8.152.124 125.556 0 227.703-78.141 227.703-174.188s-102.144-174.191-227.701-174.191z"/>      </g></g></svg> </div>

    </summary>



    <div class="collapse-content font-size-0" className="z-10" id="collapse">
    <textarea class="c-Input"  style="width: auto;  margin-left: -100px" v-model="message"></textarea>
<br>
    <button class="v-Button" v-if="!replied" @click="reply(id, author, message); message=''">Reply</button>
    <button class="btn" v-if="replied" >Replied</button>

    </div>
  </details>

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
import {copyinvoice, parseandreplacenpubs, } from "@/components/helper/Helper.vue";
import {requestProvider} from "webln";
import {Event, EventBuilder, EventId, PublicKey, Tag} from "@rust-nostr/nostr-sdk";
import amberSignerService from "@/components/android-signer/AndroidSigner";
import {zap, zap_lud16, createBolt11Lud16, zaprequest} from "@/components/helper/Zap.vue";
import {ref} from "vue";

const props =  defineProps<{
  data: any[]

}>()


const sortBy: String = "index";
const sortType: SortType = "asc";

const headers: Header[] = [
  { text: "Results:", value: "content", fixed: true},
 // { text: "Time", value: "indicator.index", sortable: true, },
];

const message = ref("");
async function react(eventid, authorid, evt){


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
                            tags: [["e", eventid]],
                            createdAt: Date.now()
                          };
                        let res = await amberSignerService.signEvent(draft)
                        await client.sendEvent(Event.fromJson(JSON.stringify(res)))
                        let requestid = res.id;
                        }
                   else {
                        let event = EventBuilder.reaction(evt, "🧡")
                        let requestid = await client.sendEventBuilder(event);
                   }

                    objects.reacted = true
                    objects.reactions += 1
                    console.log("reacted")
                   }

                }

}
async function reply (eventid, authorid, message){

   console.log(eventid)
    let signer = store.state.signer
    let client = store.state.client
        let objects =  (props.data.find(x=> x.id === eventid))
          if (objects !== undefined){

                   if (localStorage.getItem('nostr-key-method') === 'android-signer') {
                       let draft = {
                            content: message,
                            kind: 1,
                            pubkey: store.state.pubkey.toHex(),
                            tags: [["e", eventid]],
                            createdAt: Date.now()
                          };
                        let res = await amberSignerService.signEvent(draft)
                        await client.sendEvent(Event.fromJson(JSON.stringify(res)))
                        let requestid = res.id;
                        }
                   else {
                        let tags = [Tag.parse(["e", eventid])]
                        let event = EventBuilder.textNote(message, tags)

                       let requestid = await client.sendEventBuilder(event);
                         console.log(requestid.toHex())
                   }
                    objects.replied = true

                    console.log("replied")
                   }



}
async function boost(eventid, authorid, evt){

// TODO
   let event_id = EventId.parse(eventid)
    let public_key = PublicKey.parse(authorid);
    let signer = store.state.signer
    let client = store.state.client
        let objects =  (props.data.find(x=> x.id === eventid))
          if (objects !== undefined){
                if(!objects.boosted ){

                    console.log(evt.asJson())
                     let relay = "wss://relay.damus.io"
                     for (let tag of evt.tags){
                       if (tag.asVec()[0] == "relays"){
                         console.log(tag.asVec()[1])
                       }

                     }

                   if (localStorage.getItem('nostr-key-method') === 'android-signer') {

                       let draft = {
                            content: evt.asJson(),
                            kind: 6,
                            pubkey: store.state.pubkey.toHex(),
                            tags: [["e", eventid]],
                            createdAt: Date.now()
                          };
                        let res = await amberSignerService.signEvent(draft)
                        await client.sendEvent(Event.fromJson(JSON.stringify(res)))
                        let requestid = res.id;
                        }
                   else {
                        let event = EventBuilder.repost(evt)
                        let requestid = await client.sendEventBuilder(event);
                   }

                    objects.boosted = true
                    objects.boosts += 1



                    //props.data.push.apply(props.data.find(x=> x.id === eventid), objects)

                    console.log("boosted")
                   }

                }

}

async function zap_local(lud16, eventid, authorid) {
  if (lud16 == undefined || lud16 == ""){
      console.log("User has no lightning address")
    return
  }


  let success = await zap_lud16(lud16, eventid, authorid)
  try {
    if (success) {
      let objects = props.data.find(x => x.id === eventid)
      console.log(objects)
      if (objects !== undefined) {
        objects.zapped = true
        objects.zapAmount += 21000
        let index = props.data.indexOf(x => x.id === eventid)
        props.data[index] = objects

        console.log("zapped")
      }
    }
     }
    catch (error)
      {
        console.log(error)
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

.c-Input {
    @apply bg-base-200 text-accent dark:bg-black dark:text-white  focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-accent-content transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
height: 180px;

margin-top: 15px;


}

.v-Button {
  @apply bg-nostr hover:bg-nostr2 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-black px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
   height: 48px;
 margin-left: 10px;
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