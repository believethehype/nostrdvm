<script>
import ImageGeneration from "@/components/ImageGeneration.vue";
import Donate from "@/components/Donate.vue";

export default {
  name: "Home",
  components: {Donate, ImageGeneration}
}
</script>

<template>
  <div class="center">
    <br>
    <ImageGeneration/>
    <br>
  </div>
</template>

<style scoped>

.center {
  text-align: center;
  justify-content: center;
}

</style>