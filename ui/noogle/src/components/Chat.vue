<script>
import ImageGeneration from "@/components/ChatGeneration.vue";
import Donate from "@/components/Donate.vue";

export default {
  name: "Image",
  components: {ImageGeneration}
}
</script>

<template>
  <div class="center">
    <br>
    <ChatGeneration/>
    <br>
  </div>
</template>

<style scoped>

.center {
  text-align: center;
  justify-content: center;
}

</style>