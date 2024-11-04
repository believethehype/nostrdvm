<script>
import ImageGeneration from "@/components/ImageGeneration.vue";

export default {
  name: "Image",
  components: {ImageGeneration}
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