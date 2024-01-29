<script>
import Search from "@/components/Search.vue";
import ResultsTable from "@/components/SearchResultTable.vue";
import Nip07 from "@/components/Nip07.vue";
import Donate from "@/components/Donate.vue";

export default {
  name: "Home",
  components: {Donate, Nip07, ResultsTable, Search}
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