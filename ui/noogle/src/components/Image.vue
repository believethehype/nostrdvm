<script>
import ImageGeneration from "@/components/ImageGeneration.vue";
import Nip07 from "@/components/Nip07.vue";
import Donate from "@/components/Donate.vue";

export default {
  name: "Home",
  components: {Donate, Nip07, ImageGeneration}
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