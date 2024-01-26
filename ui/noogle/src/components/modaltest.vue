<script>
import store from "@/store.js";

export default {
  name: "modaltest",
  computed: {
    store() {
      return store
    }
  },
  data() {
    return {
        users: [],
		isModalVisible: false,
		userModal: {},
    }
},
  methods:{
    openModal(user) {
	  this.userModal = user;
    this.isModalVisible = true;
},
  }
}




</script>

<template>
<div v-for="user in store.state.nip89dvms" :key="user.id">
	<button @click="openModal(user)">open modal</button>
</div>

<Modal v-show="isModalVisible" @close="closeModal">
  <p>TEST</p>
</Modal>
</template>

<style scoped>

</style>