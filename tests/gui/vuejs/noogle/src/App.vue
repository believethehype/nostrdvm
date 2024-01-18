<script setup>
import Home from './components/Home.vue'
import ThreeColumnLayout from "./layouts/ThreeColumnLayout.vue";
import Nip07 from "@/components/Nip07.vue";
</script>

<template>


  <main>
    <ThreeColumnLayout>
      <Home></Home>

      <template #aside>
          <Nip07/>
    </template>
    </ThreeColumnLayout>

  </main>
</template>

<style>
header {
  line-height: 1.5;
}

.logo {
  display: block;
  margin: 0 auto 2rem;
}

@media (min-width: 1024px) {
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
