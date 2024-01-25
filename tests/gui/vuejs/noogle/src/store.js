import {createStore} from "vuex";
import {Client, ClientSigner, PublicKey} from "@rust-nostr/nostr-sdk";

const store = createStore({
  state () {
    return {
      count: 0,
      test: "hello",
      client: Client,
      pubkey: PublicKey,
      hasEventListener: false,
      imagehasEventListener: false,
      imagedvmreplies: [],
      nip89dvms: [],
      results:  [],
      relays: ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.f7z.io", "wss://pablof7z.nostr1.com", "wss://relay.nostr.net", "wss://relay.nostr.net", "wss://relay.nostr.band", "wss://nostr-pub.wellorder.net"],
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
    set_hasEventListener(state, hasEventListener) {
      state.hasEventListener = hasEventListener
    },
    set_imagehasEventListener(state, imagehasEventListener) {
      state.imagehasEventListener = imagehasEventListener
    },
    set_nip89dvms(state, nip89dvms) {
      state.nip89dvms.length = 0
      state.nip89dvms.push.apply(state.nip89dvms, nip89dvms)
    },
    set_search_results(state, results){
      state.results.length = 0
      state.results.push.apply(state.results, results)
    },
    set_imagedvm_results(state, results){
      state.imagedvmreplies.length = 0
      state.imagedvmreplies.push.apply(state.imagedvmreplies, results)
      //state.results = []

          //[].push.apply(state.results, results)

    }

  }
})

export default store;