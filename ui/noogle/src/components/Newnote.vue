<script setup>
import {ref} from "vue";
import {onClickOutside} from '@vueuse/core'

const props = defineProps({
  isOpen: Boolean,
});

const emit = defineEmits(["modal-close"]);

const target = ref(null)
onClickOutside(target, () => emit('modal-close'))


</script>

<template>
  <div v-if="isOpen" class="modal-mask">
    <div class="modal-wrapper">
      <div ref="target" class="modal-container">
        <div class="modal-header">
          <slot name="header"> default header</slot>
        </div>
        <div class="modal-body">
          <slot name="content"> default content</slot>
        </div>
        <div class="modal-footer">
          <slot name="footer">
            <div>
              <button @click.stop="emit('modal-close')"></button>
              <button @click.stop="schedule(Date.now())"></button>
            </div>
          </slot>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-mask {


  max-height: 100%;
  overflow-y: scroll;
  position: fixed;
  z-index: 9998;
  top: 0;
  left: 0;
  width: 100%;

  background-color: rgba(0, 0, 0, 0.5);
}

.modal-container {
  @apply bg-base-200;

  margin: 15% auto;
  padding: 20px 30px;
  border-radius: 2px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.33);
}


</style>