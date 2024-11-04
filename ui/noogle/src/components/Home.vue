<script>
import Search from "@/components/Search.vue";
import ResultsTable from "@/components/SearchResultTable.vue";
import ProfileResultsTable from "@/components/ProfileResultTable.vue";

export default {
  name: "Home",
  components: {ProfileResultsTable, ResultsTable, Search}


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