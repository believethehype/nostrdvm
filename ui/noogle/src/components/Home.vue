<script>
import Search from "@/components/Search.vue";
import ResultsTable from "@/components/SearchResultTable.vue";
import Donate from "@/components/Donate.vue";

export default {
  name: "Home",
  components: {Donate, ResultsTable, Search}
}

</script>

<template>


  <div class="center">
    <br>
    <Search/>
    <br>
    <ResultsTable/>
  </div>
</template>

<style scoped>

.center {
  text-align: center;
  justify-content: center;
}

</style>