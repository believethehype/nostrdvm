<script setup>
import Donate from "@/components/Donate.vue";
</script>

<template>
  <div class="three-column-layout">
    <header>

     <!-- <AppLogo />-->

    </header>

    <main>
      <slot />
    </main>

    <aside>
      <slot name="aside" />
      <!-- <AppFooter /> -->
    </aside>
  </div>
</template>

<style scoped lang="scss">
.three-column-layout {
  display: grid;
  grid-template-areas:
    "header"
    "main"
    "aside";

  header {
    grid-area: header;
    margin-top: 30px;
  }
  main {
    grid-area: main;
    margin-top: 10px;
    padding: 20px;

  }
  aside {
    grid-area: aside;
    margin-top: 10px;
    padding: 20px;
  }



  @media (min-width: 768px) {
    grid-template-columns: 1fr 3fr 1fr;
    grid-template-areas: "header main aside";
  }
}
</style>