import {createStore} from "vuex";
import {Client, NostrSigner, PublicKey} from "@rust-nostr/nostr-sdk";

const store = createStore({
    state() {
        return {
            count: 0,
            client: Client,
            signer: NostrSigner,
            dbclient: Client,
            pubkey: PublicKey,
            followings: [],
            contacts: [],
            mutes: [],
            nooglekey: import.meta.env.VITE_NOOGLE_PK,
            subscription_verifier_pubkey: import.meta.env.VITE_SUBSCRIPTIPON_VERIFIER_PUBKEY,
            requestidSearch: String,
            requestidSearch2: String,
            requestidSearchProfile: String,
            requestidImage: [],
            requestidRecommendation: [],
            requestidChat: [],
            requestidSummarization: [],
            requestidFilter: [],
            imagedvmreplies: [],
            chatdvmreplies: [],
            nip89dvms: [],
            activesearchdvms: [],
            recommendationdvms: [],
            filterdvms: [],
            summarizationdvms: [],
            results: [],
            profile_results: [],
            relays: ["wss://relay.primal.net",
                "wss://nostr.mom", "wss://nostr.oxtr.dev",
                "wss://relay.nostr.net"
            ],
        }
    },
    mutations: {
        increment(state) {
            state.count++
        },
        set_client(state, client) {
            state.client = client
        },
        set_dbclient(state, dbclient) {
            state.dbclient = dbclient
        },
        set_signer(state, signer) {
            state.signer = signer
        },
        set_pubkey(state, pubkey) {
            state.pubkey = pubkey
        },
        set_followings(state, items) {
            state.followings.length = 0
            state.followings.push.apply(state.followings, items)
        },
        set_contacts(state, items) {
            state.contacts.length = 0
            state.contacts.push.apply(state.contacts, items)
        },


        set_mutes(state, items) {
            state.mutes.length = 0
            state.mutes.push.apply(state.mutes, items)
        },

        set_nip89dvms(state, nip89dvms) {
            state.nip89dvms.length = 0
            //console.log(nip89dvms)
            let nip89dvmssorted = nip89dvms.sort(function (a, b) {
                return a.createdAt - b.createdAt;
            });
            //console.log(nip89dvmssorted)
            state.nip89dvms.push.apply(state.nip89dvms, nip89dvmssorted)
        },
        set_current_request_id_search(state, requestid) {
            state.requestidSearch = String(requestid)
        },

        set_current_request_id_search2(state, requestid2) {
            state.requestidSearch2 = String(requestid2)
        },


        set_current_request_id_summarization(state, requestid) {
            state.requestidSummarization.length = 0
            state.requestidSummarization.push.apply(state.requestidSummarization, requestid)
        },

        set_current_request_id_filter(state, requestid) {
            state.requestidFilter.length = 0
            state.requestidFilter.push.apply(state.requestidFilter, requestid)
        },
        set_current_request_profile_id_search(state, requestid) {
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

        set_filter_dvms(state, dvms) {
            state.filterdvms.length = 0
            state.filterdvms.push.apply(state.filterdvms, dvms)
        },

        set_summarization_dvms(state, dvms) {
            state.summarizationdvms.length = 0
            state.summarizationdvms.push.apply(state.summarizationdvms, dvms)
        },
        set_search_results_profiles(state, items) {
            state.profile_results.length = 0
            state.profile_results.push.apply(state.profile_results, items)
        },
        set_current_request_id_image(state, requestid) {
            state.requestidImage.length = 0
            state.requestidImage.push.apply(state.requestidImage, requestid)
        },
        set_current_request_id_recommendation(state, requestid) {
            state.requestidRecommendation.length = 0
            state.requestidRecommendation.push.apply(state.requestidRecommendation, requestid)
        },
        set_current_request_id_chat(state, requestid) {
            state.requestidChat.length = 0
            state.requestidChat.push.apply(state.requestidChat, requestid)

        },


        set_search_results(state, results) {
            state.results.length = 0
            state.results.push.apply(state.results, results)
        },
        set_imagedvm_results(state, results) {
            state.imagedvmreplies.length = 0
            state.imagedvmreplies.push.apply(state.imagedvmreplies, results)
        },

        set_chat_dvm_results(state, results) {
            state.chatdvmreplies.length = 0
            state.chatdvmreplies.push.apply(state.chatdvmreplies, results)
        },


    }
})

export default store;