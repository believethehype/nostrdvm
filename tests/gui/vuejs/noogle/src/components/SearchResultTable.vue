<template>
  <EasyDataTable class="customize-table" alternating  header-text-direction="left" expand  v-if="store.state.results.length != 0" table-class-name="customize-table"
    :headers="headers"
    :items="store.state.results">
   <template #item-content="{ content, author, authorurl, avatar, indicator, links}">
   <div class="playeauthor-wrapper">
      <img class="avatar" :src="avatar" alt="" />
         <a class="purple" :href="authorurl" target="_blank">{{ author }}</a>
     <div class="time"  :data-tip="indicator.time">
          {{indicator.time.split("T")[1].split("Z")[0].trim()}}
          {{indicator.time.split("T")[0].split("-")[2].trim()}}.{{indicator.time.split("T")[0].split("-")[1].trim()}}.{{indicator.time.split("T")[0].split("-")[0].trim().slice(2)}}
        </div>
   </div>

     <p>{{content.substr(0, 320) + "\u2026"}}</p>
        <div style="padding: 2px; text-align: left;" >
          <a class="menusmall" :href="links.uri" target="_blank">Nostr Client</a>
          <a class="menusmall" :href="links.njump" target="_blank">NJump</a>
          <a class="menusmall" :href="links.highlighter" target="_blank">Highlighter</a>
          <!-- <a class="menusmall":href="links.nostrudel" target="_blank">Nostrudel</a> -->
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



import type { Header, Item } from "vue3-easy-data-table";
import store from '../store';


const headers: Header[] = [
  { text: "Results:", value: "content", fixed:true},
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
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: inset 0 4px 4px 0 rgb(0 0 0 / 10%);
}
.customize-table {

  --easy-table-border: 1px solid #000000;
  --easy-table-row-border: 1px solid #000000;

  --easy-table-header-font-size: 14px;
  --easy-table-header-height: 50px;
  --easy-table-header-font-color: #c1cad4;
  --easy-table-header-background-color: #242424;

  --easy-table-header-item-padding: 10px 15px;

  --easy-table-body-even-row-font-color: #fff;
  --easy-table-body-even-row-background-color: #242424;

  --easy-table-body-row-font-color: #c0c7d2;
  --easy-table-body-row-background-color: #242424;
  --easy-table-body-row-height: 50px;
  --easy-table-body-row-font-size: 14px;

  --easy-table-body-row-hover-font-color: #FFFFFF;
  --easy-table-body-row-hover-background-color: #242424;

  --easy-table-body-item-padding: 10px 15px;

  --easy-table-footer-background-color: #242424;
  --easy-table-footer-font-color: #c0c7d2;
  --easy-table-footer-font-size: 14px;
  --easy-table-footer-padding: 0px 10px;
  --easy-table-footer-height: 50px;

  --easy-table-rows-per-page-selector-width: 70px;
  --easy-table-rows-per-page-selector-option-padding: 10px;
  --easy-table-rows-per-page-selector-z-index: 1;


  --next-page__click-button : #c0c7d2;





  --easy-table-scrollbar-track-color: #2d3a4f;
  --easy-table-scrollbar-color: #2d3a4f;
  --easy-table-scrollbar-thumb-color: #4c5d7a;;
  --easy-table-scrollbar-corner-color: #2d3a4f;

  --easy-table-loading-mask-background-color: #2d3a4f;
}
</style>