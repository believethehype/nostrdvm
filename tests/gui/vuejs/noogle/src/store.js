import {createStore} from "vuex";
import {Client} from "@rust-nostr/nostr-sdk";

const store = createStore({
  state () {
    return {
      count: 0,
      test: "hello",
      client: Client,
      results:  []
    }
  },
  mutations: {
    increment (state) {
      state.count++
    },
     set_client (state, client) {
      state.client = client
    },
    set_search_results(state, results){
      state.results = results
      console.log(state.results)
    }

  }
})

export default store;