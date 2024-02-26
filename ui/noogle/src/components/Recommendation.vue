<script>
import ImageGeneration from "@/components/ImageGeneration.vue";
import Donate from "@/components/Donate.vue";
import RecommendationGeneration from "@/components/RecommendationGeneration.vue";

export default {
  name: "Recommendation",
  components: {RecommendationGeneration}
}
</script>

<template>
  <div class="center">
    <br>
    <RecommendationGeneration/>
    <br>
  </div>
</template>

<style scoped>

.center {
  text-align: center;
  justify-content: center;
}

</style>