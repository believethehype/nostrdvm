<template>
  <EasyDataTable class="customize-table" header-text-direction="left"  table-class-name="customize-table"
                 :headers="headers"
                 :items="data"
                 :sort-by="sortBy"
                 :sort-type="sortType">
   <template #item-content="{content, author, authorurl, avatar, indicator, links, lud16, id, authorid}">

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
   <!--<p>{{content.substr(0, 320) + "\u2026"}}</p> -->
        <div style="padding: 2px; text-align: left;" >
          <a class="menusmall" :href="links.uri" target="_blank">Client</a>
          <a class="menusmall" :href="links.njump" target="_blank">NJump</a>
         <!--<a class="menusmall" :href="links.highlighter" target="_blank">Highlighter</a> -->
          <a class="menusmall":href="links.nostrudel" target="_blank">Nostrudel</a>


       <!--<div style="margin-left: auto; margin-right: 10px;" class=" justify-end mt-auto" @click="zap(lud16, id.toHex(), authorid)">
          <svg style="margin-top:3px" xmlns="http://www.w3.org/2000/svg" width="14" height="16" fill="currentColor" class="bi bi-lightning" viewBox="0 0 16 20">
  <path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641zM6.374 1 4.168 8.5H7.5a.5.5 0 0 1 .478.647L6.78 13.04 11.478 7H8a.5.5 0 0 1-.474-.658L9.306 1z"/></svg></div>-->

      </div>
     </template>
    <!--<template #expand="item">
      <div style="padding: 15px; text-align: left;" >
          <a class="menu" :href="item.links.uri" target="_blank">Nostr Client</a>
          <a class="menu" :href="item.links.njump" target="_blank">NJump</a>
          <a class="menu" :href="item.links.highlighter" target="_blank">Highlighter</a>
          <a class="menu":href="item.links.nostrudel" target="_blank">Nostrudel</a>
      </div>
    </template> -->


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
defineProps<{
  data?: []

}>()

const sortBy: String = "index";
const sortType: SortType = "asc";

const headers: Header[] = [
  { text: "Results:", value: "content", fixed: true},
 // { text: "Time", value: "indicator.index", sortable: true, },
];


async function zap(lud16, id, authorid){
  //let invoice = await zaprequest(lud16, 21 , "with love from noogle.lol", id, authorid, store.state.relays)  //Not working yet
  if(lud16 != Null && lud16 != ""){


    let invoice = await createBolt11Lud16(lud16, 21)
     let webln;
    try {
      webln = await requestProvider();
    } catch (err) {
        await copyinvoice(invoice)
    }
    if (webln) {
      try{
           let response = await webln.sendPayment(invoice)

      }
      catch(err){
            console.log(err)
            await copyinvoice(invoice)
      }
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
  --easy-table-border: 2px solid #000000;
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