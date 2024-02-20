<template>
  <EasyDataTable style="margin-top: 450px"
 class="customize-table" header-text-direction="left" hide-rows-per-page="true"  rows-per-page="10" v-if="store.state.profile_results.length != 0 && router.currentRoute.value.path == '/'" table-class-name="customize-table"
    :headers="headers"
    :items="store.state.profile_results" >
   <template #item-content="{ author, authorurl, avatar}">
   <div class="playeauthor-wrapper" >

     <img class="avatar" v-if="avatar" :src="avatar" alt="Avatar" onerror="this.src='https://noogle.lol/favicon.ico'" />
     <img class="avatar" v-else src="@/assets/nostr-purple.svg" />

         <a class="white" :href="authorurl" target="_blank">{{ author }}</a>



        </div>

   <!--   <p>{{content}}</p> -->
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


</template>

<script lang="ts" setup>


import type {Header, Item, SortType} from "vue3-easy-data-table";
import store from '../store';
import router from "../router";


const headers: Header[] = [
  { text: "Relevant Profiles:", value: "content", fixed:true},
 // { text: "Time", value: "indicator.time", sortable: true, },
];




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
  @apply btn text-gray-600 bg-transparent border-transparent tracking-wide;


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
  width: 20px;
  height: 20px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: inset 0 4px 4px 0 rgb(0 0 0 / 10%);
}
.customize-table {
  width:auto;
  --easy-table-border: 3px solid #000000;
  --easy-table-row-border: 0px;

  --easy-table-header-font-size: 14px;
  --easy-table-header-height: 20px;
  --easy-table-header-font-color: bg-accent;
  --easy-table-header-background-color: bg-base;

  --easy-table-header-item-padding: 10px 15px;

  --easy-table-body-even-row-font-color: bg-accenet;
  --easy-table-body-even-row-background-color: bg-base;

  --easy-table-body-row-font-color: bg-accents;
  --easy-table-body-row-background-color: bg-base;
  --easy-table-body-row-height: 20px;
  --easy-table-body-row-font-size: 14px;

  --easy-table-body-row-hover-font-color: bg-accent;
  --easy-table-body-row-hover-background-color: bg-base;

  --easy-table-body-item-padding: 10px 15px;

  --easy-table-footer-background-color: bg-base;
  --easy-table-footer-font-color: bg-accent;
  --easy-table-footer-font-size: 14px;
  --easy-table-footer-padding: 10px 10px;
  --easy-table-footer-height: 20px;

  --easy-table-rows-per-page-selector-width: 60px;
  --easy-table-rows-per-page-selector-option-padding: 10px;
  --easy-table-rows-per-page-selector-z-index: 1;

 --easy-table-scrollbar-track-color: bg-base;
  --easy-table-scrollbar-color: bg-base;
  --easy-table-scrollbar-thumb-color: bg-base;
  --easy-table-scrollbar-corner-color: bg-base;

  --easy-table-loading-mask-background-color: #2d3a4f;
}
</style>