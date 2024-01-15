<script setup>
import Search from './components/Search.vue'
import Nip07 from './components/Nip07.vue'
import ResultsTable from "@/components/ResultTable.vue";
</script>

<template>


  <main>

      <img alt="Nostr logo" class="logo" src="./assets/nostr-purple.svg" width="125" height="125" />
      <Search/>
      <br>
      <ResultsTable></ResultsTable>
     <Nip07>
     </Nip07>

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
    padding-right: calc(var(--section-gap) / 2);
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
