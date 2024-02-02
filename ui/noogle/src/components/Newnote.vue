<script setup>
import { ref } from "vue";
import {onClickOutside} from '@vueuse/core'
import store from "@/store.js";
import {EventBuilder, nip04_encrypt, Tag, Timestamp} from "@rust-nostr/nostr-sdk";

const props = defineProps({
  isOpen: Boolean,
});

const emit = defineEmits(["modal-close"]);

const target = ref(null)
onClickOutside(target, ()=>emit('modal-close'))

async function schedule(time) {
  time = time + 1000 * 60 * 60 //for testing move 1 hour to future, replace with actual time later.

  let draft = {
    content: "Test",
    kind: 1,
    pubkey: store.state.pubkey.toHex(),
    tags: [],
    createdAt: Date.now()
  };

  let stringifyiedevent = Event.fromJson(JSON.stringify(draft))
  let contenttags = []
  contenttags.push(Tag.parse(["i", stringifyiedevent, "text"]))
  contenttags.push(Tag.parse(["param", "relays", "wss://now.lol"]))
  let client = store.state.client
  client.nip04_encrypt()
  //nip04_encrypt() contenttags.toString()

  let tags_t = []
  tags_t.push(Tag.parse(["p", "fa984bd7dbb282f07e16e7ae87b26a2a7b9b90b7246a44771f0cf5ae58018f52"]))
  tags_t.push(Tag.parse(["encrypted"]))

  let evt = new EventBuilder(5905, content, tags_t)
  evt.customCreatedAt(Timestamp.fromSecs())

  let res = await client.sendEventBuilder(evt);


}

</script>

<template>
  <div v-if="isOpen" class="modal-mask">
    <div class="modal-wrapper">
      <div class="modal-container" ref="target">
        <div class="modal-header">
          <slot name="header"> default header </slot>
        </div>
        <div class="modal-body">
          <slot name="content"> default content </slot>
        </div>
        <div class="modal-footer">
          <slot name="footer">
            <div>
              <button @click.stop="emit('modal-close')">Submit</button>
              <button @click.stop="schedule(Date.now())">Schedule</button>
            </div>
          </slot>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  z-index: 9998;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
}
.modal-container {
  @apply bg-base-100;
  width: 400px;
  margin: 200px auto;
  padding: 20px 30px;
  border-radius: 2px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.33);
}

</style>