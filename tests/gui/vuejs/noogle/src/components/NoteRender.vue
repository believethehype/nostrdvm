<script setup>

import {EventId, Filter, PublicKey} from "@rust-nostr/nostr-sdk";
import store from '../store';
import {computed, onMounted, ref, watch} from "vue";

const props = defineProps({
  content: {
    type: String,
    required: true
  },
   author: {
    type: String,
    required: true
  },
   avatar: {
    type: String,
    required: true
  },
   authorurl: {
    type: String,
    required: true
  },
})


async function getEvent(eventid){
  const event_filter = new Filter().id(EventId.fromHex(eventid)).limit(1)
  let  client = store.state.client
  let evts = await client.getEventsOf([event_filter], 5)
  return evts[0]
}


async function parseContent(pubkey) {
  let name = PublicKey.fromHex(pubkey).toBech32()
  let nip05 = ""
  let lud16 = ""
  let picture = ""
  const profile_filter = new Filter().kind(0).author(PublicKey.fromHex(pubkey)).limit(1)
  let  client = store.state.client
  let evts = await client.getEventsOf([profile_filter], 5)
  console.log("PROFILES:" + evts.length)
  if (evts.length > 0) {
    let latest_entry = evts[0]
    let latest_time = 0

    for (const entry of evts) {
      if (entry.createdAt.asSecs() > latest_time) {
        latest_time = entry.createdAt.asSecs();
        latest_entry = entry
      }
    }

    let profile = JSON.parse(latest_entry.content);
    name = profile["name"]
    picture = profile["picture"]
    console.log(picture)
    return name

  }
}

async function get_user_info(pubkey){
        let client = store.state.client
        const profile_filter = new Filter().kind(0).author(PublicKey.fromHex(pubkey)).limit(1)
        let evts = await client.getEventsOf([profile_filter], 10)
        console.log("PROFILES:" + evts.length)
        if (evts.length > 0){
             let latest_entry = evts[0]
             let latest_time = 0

              for (const entry of evts){
                 if (entry.createdAt.asSecs() > latest_time){
                    latest_time = entry.createdAt.asSecs();
                    latest_entry = entry
                 }
              }

              return JSON.parse(latest_entry.content);

            }
    }

const content_placeholder = ref()
const author_placeholder = ref()
const author_image_placeholder = ref()

onMounted(async () => {


   content_placeholder.value = "Event not found"
   author_placeholder.value = ""
   author_image_placeholder.value = ""


      content_placeholder.value = props.content //TODO furher parse content
  console.log(props.author)
      const profile = await get_user_info(props.author)
      console.log(profile)
      author_placeholder.value = profile["name"]
      author_image_placeholder.value = profile["picture"]

})



</script>

<template><div class="playeauthor-wrapper">
        <img class="avatar" :src="author_image_placeholder" alt="" />
         <a :href="author_placeholder">{{ author_placeholder}}</a>  </div>
 <p>{{ content_placeholder }}</p>






</template>

<style scoped>
.operation-wrapper .operation-icon {
  width: 20px;
  cursor: pointer;
}
.playeauthor-wrapper {
  padding: 5px;
  display: flex;
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
  box-shadow: inset 0 2px 4px 0 rgb(0 0 0 / 10%);
}
</style>
