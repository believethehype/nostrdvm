import {createStore} from "vuex";
import {Client, NostrSigner, PublicKey} from "@rust-nostr/nostr-sdk";

const store = createStore({
  state () {
    return {
      count: 0,
      test: "hello",
      client: Client,
      signer: NostrSigner,
      dbclient: Client,
      pubkey: PublicKey,
      requestidSearch: String,
      requestidSearchProfile: String,
      requestidImage: String,
      requestidRecommendation: String,
      hasEventListener: false,
      imagehasEventListener: false,
      recommendationehasEventListener: false,
      imagedvmreplies: [],
      nip89dvms: [],
      activesearchdvms: [],
      recommendationhdvms: [],
      results:  [],
      profile_results: [],
      relays: [
          "wss://relay.damus.io",
        "wss://nos.lol",
        "wss://pablof7z.nostr1.com",
        "wss://relay.nostr.net",
        //"wss://relay.nostr.band",
        //"wss://nostr-pub.wellorder.net",
      ],
    }
  },
  mutations: {
    increment (state) {
      state.count++
    },
     set_client (state, client) {
      state.client = client
    },
    set_dbclient (state, dbclient) {
      state.dbclient = dbclient
    },
    set_signer (state, signer) {
      state.signer = signer
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

    set_recommendationEventListener(state, recommendationehasEventListener) {
      state.recommendationehasEventListener = recommendationehasEventListener
    },

    set_nip89dvms(state, nip89dvms) {
      state.nip89dvms.length = 0
      //console.log(nip89dvms)
         let nip89dvmssorted =  nip89dvms.sort(function(a, b) {
          return a.createdAt - b.createdAt;
      });
      //console.log(nip89dvmssorted)
      state.nip89dvms.push.apply(state.nip89dvms, nip89dvmssorted)
    },
    set_current_request_id_search(state, requestid){
      state.requestidSearch = String(requestid)
    },
    set_current_request_profile_id_search(state, requestid){
      state.requestidSearchProfile = String(requestid)
    },
    set_active_search_dvms(state, dvms) {
      state.activesearchdvms.length = 0
      state.activesearchdvms.push.apply(state.activesearchdvms, dvms)
    },
    set_recommendation_dvms(state, dvms) {
      state.recommendationhdvms.length = 0
      state.recommendationhdvms.push.apply(state.recommendationhdvms, dvms)
    },
    set_search_results_profiles(state, items){
      state.profile_results.length = 0
      state.profile_results.push.apply(state.profile_results, items)
    },
    set_current_request_id_image(state, requestid){
       state.requestidImage = requestid
    },
    set_current_request_id_recommendation(state, requestid){
       state.requestidRecommendation = requestid
    },

    set_search_results(state, results){
      state.results.length = 0
      state.results.push.apply(state.results, results)
    },
    set_imagedvm_results(state, results){
      state.imagedvmreplies.length = 0
      state.imagedvmreplies.push.apply(state.imagedvmreplies, results)
    },

  }
})

export default store;