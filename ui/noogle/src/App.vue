<script setup>
import ThreeColumnLayout from "./layouts/ThreeColumnLayout.vue";
import ProfileResultsTable from "@/components/ProfileResultTable.vue";
import router from "@/router/index.js";



</script>

<template>
  <link rel="search" type="application/opensearchdescription+xml" href="/opensearch.xml" title="Noogle Search" />


  <main>
    <ThreeColumnLayout>
  <template #aside>

    <ProfileResultsTable style="margin-top: 450px"/>
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
