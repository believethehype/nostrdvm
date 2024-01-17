import {createStore} from "vuex";
import {Client, ClientSigner, PublicKey} from "@rust-nostr/nostr-sdk";

const store = createStore({
  state () {
    return {
      count: 0,
      test: "hello",
      client: Client,
      pubkey: PublicKey,
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
     set_pubkey(state, pubkey) {
      state.pubkey = pubkey
    },
    set_search_results(state, results){
      state.results = results
      console.log(state.results)
    }

  }
})

export default store;