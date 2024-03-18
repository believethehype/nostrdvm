import {createStore} from "vuex";
import {Client, NostrSigner, PublicKey} from "@rust-nostr/nostr-sdk";

const store = createStore({
  state () {
    return {
      count: 0,
      client: Client,
      signer: NostrSigner,
      dbclient: Client,
      pubkey: PublicKey,
      nooglekey: "ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e",
      subscription_verifier_pubkey: "5b5c045ecdf66fb540bdf2049fe0ef7f1a566fa427a4fe50d400a011b65a3a7e",
      requestidSearch: String,
      requestidSearchProfile: String,
      requestidImage: String,
      requestidRecommendation: String,
      requestidSummarization: String,
      hasEventListener: false,
      imagehasEventListener: false,
      recommendationehasEventListener: false,
      summarizationhasEventListener: false,
      imagedvmreplies: [],
      nip89dvms: [],
      activesearchdvms: [],
      recommendationdvms: [],
      summarizationdvms: [],
      results:  [],
      profile_results: [],
      relays: [
          "wss://relay.damus.io",
        "wss://nos.lol",
        "wss://pablof7z.nostr1.com",
        "wss://relay.nostr.net"
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

    set_summariarizationEventListener(state, summarizationhasEventListener) {
      state.summarizationhasEventListener = summarizationhasEventListener
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

    set_current_request_id_summarization(state, requestid){
      state.requestidSummarization = String(requestid)
    },

    set_current_request_profile_id_search(state, requestid){
      state.requestidSearchProfile = String(requestid)
    },
    set_active_search_dvms(state, dvms) {
      state.activesearchdvms.length = 0
      state.activesearchdvms.push.apply(state.activesearchdvms, dvms)
    },
    set_recommendation_dvms(state, dvms) {
      state.recommendationdvms.length = 0
      state.recommendationdvms.push.apply(state.recommendationdvms, dvms)
    },

    set_summarization_dvms(state, dvms) {
      state.summarizationdvms.length = 0
      state.summarizationdvms.push.apply(state.summarizationdvms, dvms)
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