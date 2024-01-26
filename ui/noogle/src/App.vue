<script setup>
import Home from './components/Home.vue'
import ThreeColumnLayout from "./layouts/ThreeColumnLayout.vue";
import Nip07 from "@/components/Nip07.vue";
</script>

<template>


  <main>
    <ThreeColumnLayout>
      <template #aside>

    </template>
    </ThreeColumnLayout>


  </main>
</template>

<style>
header {
  line-height: 1.5;
}



@media (min-width: 768px) {
  header {
    display: flex;
    place-items: center;

  }

  .logo {
    margin: 0 2rem 0 0;
  }

  header .wrapper {
    display: flex;
    place-items: flex-start;
    flex-wrap: wrap;
  }
}
</style>
