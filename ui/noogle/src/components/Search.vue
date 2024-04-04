<script setup>


import {
  Client,
  Filter,
  Timestamp,
  Event,
  Metadata,
  PublicKey,
  EventBuilder,
  Tag,
  EventId,
  Nip19Event,
  Alphabet,
  ClientBuilder,
  Keys,
  NostrDatabase,
  NegentropyOptions,
  NegentropyDirection,
  Duration
} from "@rust-nostr/nostr-sdk";
import store from '../store';
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";
import {computed, onMounted, ref} from "vue";
import deadnip89s from "@/components/data/deadnip89s.json";
import amberSignerService from "./android-signer/AndroidSigner";
import VueDatePicker from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css'
import {post_note, schedule, copyurl, copyinvoice, sleep, getEvents, get_user_infos, nextInput} from "../components/helper/Helper.vue"
import StringUtil from "@/components/helper/string.ts";


let items = []
let profiles = []
let dvms =[]

const message = ref("");
const fromuser = ref("");


let usernames = []


const datefrom = ref(new Date().setFullYear(new Date().getFullYear() - 1));
const dateto = ref(Date.now());


onMounted(async () => {
  let urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has('q')) {
    message.value = urlParams.get('q')
    await sleep(1000)
    await send_search_request(message.value)
  }

 await sleep(2000)

})

async function send_search_request(msg) {

   if (!store.state.hasEventListener){
          store.commit('set_hasEventListener', true)
          listen()

      }
      else{
        console.log("Already has event listener")
      }
   try {
     if (msg === undefined){
       msg = "Nostr"
     }

     if(store.state.pubkey === undefined){
               miniToastr.showMessage("Please login first", "No pubkey set", VueNotifications.types.warn)
          return
     }
        items = []
        profiles = []
        dvms =[]
        store.commit('set_search_results', items)
        store.commit('set_search_results_profiles', profiles)
        let client = store.state.client

        let users = [];

        const taggedUsersFrom = msg.split(' ')
          .filter(word => word.startsWith('from:'))
          .map(word => word.replace('from:', ''));

        // search
        let search = msg;
        for (let word of taggedUsersFrom) {
          search = search.replace(word, "");
          if(word === "me"){
            word = store.state.pubkey.toBech32()

          }
          const userPubkey = PublicKey.fromBech32(word.replace("@", "")).toHex()
          const pTag = Tag.parse(["p", userPubkey]);
          users.push(pTag.asVec());
        }

        if (fromuser.value !== ""){
           const userPubkey = PublicKey.fromBech32(fromuser.value.replace("@", "")).toHex()
           const pTag = Tag.parse(["p", userPubkey]);
            users.push(pTag.asVec());
        }

        msg = search.replace(/from:|to:|@/g, '').trim();
        console.log(search);

        let content = "NIP 90 Search request"
        let kind = 5302
        let kind_profiles = 5303
        let tags = [
              ["i", msg, "text"],
              ["param", "max_results", "150"],
              ["param", "since", ((datefrom.value/1000).toFixed(0))],
              ["param", "until", ((dateto.value/1000).toFixed(0))],
              ['param', 'users', JSON.stringify(users)]
            ]

        let res;
        let requestid;
        let requestid_profile;
        if (localStorage.getItem('nostr-key-method') === 'android-signer') {
          let draft = {
            content: content,
            kind: kind,
            pubkey: store.state.pubkey.toHex(),
            tags: tags,
            createdAt: Date.now()
          };

          res = await amberSignerService.signEvent(draft)
          await client.sendEvent(Event.fromJson(JSON.stringify(res)))
          requestid = res.id;
          res = res.id;
        }

        else {
          let tags_t = []
          for (let tag of tags){
            tags_t.push(Tag.parse(tag))
          }
          let evt = new EventBuilder(kind, content, tags_t)
          let evt_profiles = new EventBuilder(kind_profiles, "Profile Search request",  [Tag.parse(["i", msg, "text"]),  Tag.parse(["param", "max_results", "500"])])
          try{
             let res1 = await client.sendEventBuilder(evt_profiles)
             requestid_profile = res1.toHex()
             res = await client.sendEventBuilder(evt)
             requestid = res.toHex()
          }
          catch(error){
            console.log(error)
          }
        }

        store.commit('set_current_request_id_search', requestid)
        store.commit('set_current_request_profile_id_search', requestid_profile)


        console.log(res)
      } catch (error) {
        console.log(error);
      }
}

async function  listen() {
    let client = store.state.client
    let pubkey = store.state.pubkey
    let originale = [store.state.requestidSearch]

    const filter = new Filter().kinds([7000, 6302, 6303]).pubkey(pubkey).since(Timestamp.now());
    await client.subscribe([filter]);

    const handle = {
        // Handle event
        handleEvent: async (relayUrl, subscriptionId, event) => {
             /* if (store.state.hasEventListener === false){
                return true
              }*/
            console.log("Received new event from", relayUrl);
            let resonsetorequest = false

            sleep(500).then(async () => {

              for (let tag in event.tags) {
                if (event.tags[tag].asVec()[0] === "e") {
                  if (event.tags[tag].asVec()[1] === store.state.requestidSearch || event.tags[tag].asVec()[1] === store.state.requestidSearchProfile) {
                    resonsetorequest = true
                  }
                }

              }

              if (resonsetorequest) {

                if (event.kind === 7000) {
                  try {
                    console.log("7000: ", event.content);
                    console.log("DVM: " + event.author.toHex())

                    let status = "unknown"
                    let jsonentry = {
                      id: event.author.toHex(),
                      kind: "",
                      status: status,
                      result: "",
                      name: event.author.toBech32(),
                      about: "",
                      image: "",
                      amount: 0,
                      bolt11: ""
                    }

                    for (const tag in event.tags) {
                      if (event.tags[tag].asVec()[0] === "status") {
                        status = event.tags[tag].asVec()[1]
                        if (event.tags[tag].asVec().length > 2) {
                          jsonentry.about = event.tags[tag].asVec()[2]
                        }
                      }

                      if (event.tags[tag].asVec()[0] === "amount") {
                        jsonentry.amount = event.tags[tag].asVec()[1]
                        if (event.tags[tag].asVec().length > 2) {
                          jsonentry.bolt11 = event.tags[tag].asVec()[2]
                        }
                        // TODO else request invoice
                      }
                    }

                    //let dvm = store.state.nip89dvms.find(x => JSON.parse(x.event).pubkey === event.author.toHex())
                    for (const el of store.state.nip89dvms) {
                      if (JSON.parse(el.event).pubkey === event.author.toHex().toString()) {
                        jsonentry.name = el.name
                        jsonentry.about = event.content
                        jsonentry.image = el.image
                        console.log(jsonentry)

                      }
                    }
                    if (dvms.filter(i => i.id === jsonentry.id).length === 0) {
                      dvms.push(jsonentry)
                    }

                    dvms.find(i => i.id === jsonentry.id).status = status
                    if (status === "error") {
                      const index = dvms.indexOf((dvms.find(i => i.id === event.author.toHex())));
                      if (index > -1) {
                        dvms.splice(index, 1);
                      }
                    }

                    store.commit('set_active_search_dvms', dvms)
                    console.log(store.state.activesearchdvms)

                  } catch (error) {
                    console.log("Error: ", error);
                  }
                }

                else if (event.kind === 6302) {
                  let entries = []
                  console.log("6302:", event.content);
                  try{
                  let event_etags = JSON.parse(event.content)
                  if (event_etags.length > 0) {
                    for (let etag of event_etags) {
                      const eventid = EventId.parse(etag[1]).toHex() //a bit unnecessary
                      entries.push(eventid)
                    }
                    const events = await getEvents(entries)
                    let authors = []
                    for (const evt of events) {
                      authors.push(evt.author)
                    }
                    if (authors.length > 0) {
                      let profiles = await get_user_infos(authors)
                      for (const evt of events) {
                        let p = profiles.find(record => record.author === evt.author.toHex())
                        let bech32id = evt.id.toBech32()
                        let nip19 = new Nip19Event(evt.id, evt.author, store.state.relays)
                        let nip19bech32 = nip19.toBech32()
                        let picture = p === undefined ? "../assets/nostr-purple.svg" : p["profile"]["picture"]
                        let name = p === undefined ? bech32id : p["profile"]["name"]
                        let highlighterurl = "https://highlighter.com/e/" +  nip19bech32
                        let njumpurl = "https://njump.me/" + nip19bech32
                        let nostrudelurl = "https://nostrudel.ninja/#/n/" + bech32id
                        let uri = "nostr:" + bech32id //  nip19.toNostrUri()

                        if (items.find(e => e.id.toHex() === evt.id.toHex()) === undefined) {
                          items.push({
                            id: evt.id,
                            content: evt.content,
                            author: name,
                            authorurl: "https://njump.me/" + evt.author.toBech32(),
                            links: {
                              "uri": uri,
                              "highlighter": highlighterurl,
                              "njump": njumpurl,
                              "nostrudel": nostrudelurl
                            },
                            avatar: picture,
                            indicator: {"time": evt.createdAt.toHumanDatetime()}
                          })
                        }
                      }
                    }
                  }

                  const index = dvms.indexOf((dvms.find(i => i.id === event.author.toHex())));
                  if (index > -1) {
                    dvms.splice(index, 1);
                  }

                  store.commit('set_active_search_dvms', dvms)
                  console.log("Events from" + event.author.toHex())
                  store.commit('set_search_results', items)
                     }
                catch{

                  }
                }


                else if (event.kind === 6303) {
                  let entries = []
                  console.log("6303:", event.content);

                  let event_ptags = JSON.parse(event.content)
                  let authors = []
                  if (event_ptags.length > 0) {
                    for (let ptag of event_ptags) {
                        authors.push(PublicKey.parse(ptag[1]))
                    }

                    if (authors.length > 0) {
                      let infos = await get_user_infos(authors)

                      for (const profile of infos) {
                        //console.log(profile["author"])
                        if (profiles.findIndex(e => e.id === profile["author"]) === -1 && profile["profile"]["name"] !== "" ) {
                          profiles.push({
                            id: profile["author"],
                            content: profile["profile"],
                            author: profile["profile"]["name"],
                            authorurl: "https://njump.me/" +PublicKey.parse(profile["author"]).toBech32(),
                            avatar: profile["profile"]["picture"]
                          })
                        }
                      }
                    }
                  }


                  const index = dvms.indexOf((dvms.find(i => i.id === event.author.toHex())));
                  if (index > -1) {
                    dvms.splice(index, 1);
                  }

                  store.commit('set_active_search_dvms', dvms)
                  store.commit('set_search_results_profiles', profiles)
                }
              }
            })
        },
        // Handle relay message
        handleMsg: async (relayUrl, message) => {
            //console.log(`Received message from ${relayUrl} ${message.asJson()}`);
        }
    };

    client.handleNotifications(handle);
}


function getNamefromId(id){
  let elements = searchdvms.filter(i => i.id === id)
  if (elements.length === 0){
    return id
  }
  else return elements[0].name
}


async function checkuser(msg){
  usernames = []
    let profiles = await get_user_from_search(msg)
    for (let profile of profiles){
      usernames.push(profile)
    }
}

async function get_user_from_search(name){
        name = "\"name\":" + name
        if (store.state.dbclient.database === undefined){
          console.log("not logged in, not getting profile suggestions")
          return []
        }
        let client = store.state.dbclient
        let profiles = []
        let filter1 = new Filter().kind(0)
         let evts = await client.database.query([filter1])
 console.log(evts.length)
      for (const entry of evts){
          try{

               let contentjson = JSON.parse(entry.content)
            console.log(entry.content)
            profiles.push({profile: contentjson, author: entry.author.toBech32(), createdAt: entry.createdAt});


          }
          catch(error){
            console.log(error)
          }
        }
        return profiles
    }

defineProps({
  msg: {
    type: String,
    required: false
  },
})

</script>

<template>

    <div class="greetings">
      <img alt="Nostr logo" class="logo" src="../assets/nostr-purple.svg" />
      <br>
      <h1 class="text-7xl font-black tracking-wide">Noogle</h1>
      <h2 class="text-base-200-content text-center tracking-wide text-2xl">
      Search the Nostr with Data Vending Machines</h2>
      <h3>
        <br>
        <input class="c-Input" type="search" name="s" autofocus placeholder="Search..." v-model="message"   @keyup.enter="send_search_request(message)" @keydown.enter="nextInput">
        <button class="v-Button"  @click="send_search_request(message)">Search the Nostr</button>
      </h3>

    <details class="collapse bg-base " className="advanced" >
  <summary class="collapse-title font-thin bg">Advanced Options</summary>
  <div class="collapse-content font-size-0" className="z-10" id="collapse-settings">

    <div>
    <h4 className="inline-flex flex-none font-thin">by: </h4>
       <div className="inline-flex flex-none" style="width: 10px;"></div>
        <input list="users" id="user" class="u-Input" style="margin-left: 10px" type="search" name="user" autofocus  placeholder="npub..." v-model="fromuser" @input="checkuser(fromuser)">

     <datalist id="users">
          <option v-for="profile in usernames" :value="profile.author">
            {{profile.profile.name + ' (' + profile.profile.nip05 + ')'}}

          </option>
      </datalist>
    </div>
  </div>


      <div className="inline-flex flex-none" style="width: 20px;"></div>

    <div>
          <h4 className="inline-flex flex-none font-thin">from:</h4>
    <div className="inline-flex flex-none" style="width: 10px;"></div>
    <VueDatePicker :teleport="true" :dark="true" position="left" className="bg-base-200 inline-flex flex-none" style="width: 220px;" v-model="datefrom"></VueDatePicker>
    </div>

    <div className="inline-flex flex-none" style="width: 20px;"></div>
    <div>
      <h4 className="inline-flex font-thin ">until: </h4>
    <div className="inline-flex flex-none" style="width: 10px;"></div>
    <VueDatePicker :teleport="true" :dark="true" position="left" className="bg-base-200 inline-flex flex-none" style="width: 220px;" v-model="dateto"></VueDatePicker>
    </div>
</details>
    </div>
    <div class="max-w-5xl relative space-y-3">
      <div class="grid grid-cols-1 gap-6">
        <div className="card w-30 h-60 bg-base-100 shadow-xl"  v-for="dvm in store.state.activesearchdvms"
                  :key="dvm.name">
                 <div className="card-body">
                <div class="grid grid-cols-1 gap-6">

                <div className="col-end-1">
                  <h2 className="card-title">{{ dvm.name }}</h2>
                  <figure v-if="dvm.image!==''" className="w-40"><img className="h-30" :src="dvm.image" alt="DVM Picture" /></figure>
                </div>

                <div className="col-end-2 w-auto card-body">
                    <h3 class="fa-cut" v-html="StringUtil.parseHyperlinks(dvm.about)"></h3>

                   <div><br>
                   <span className="loading loading-dots loading-lg" ></span>
                </div>
                </div>
            </div>
          </div>
        </div>
      </div>
    </div>

</template>

<style scoped>

.v-Button {
  @apply bg-nostr hover:bg-nostr2 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-black px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
   height: 48px;
   margin: 5px;
}

.c-Input {
    @apply bg-base-200 text-accent dark:bg-black dark:text-white  focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-accent-content transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;

  width: 350px;
  height: 48px;

}

.u-Input {
    @apply bg-base-200 text-accent dark:bg-base-200 dark:text-white  focus:ring-white  border border-transparent px-3 py-1.5 text-sm leading-4 text-accent-content transition-colors duration-300  focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;

  width: 220px;
  height: 35px;


}

.logo {
     display: flex;
    width:100%;
    height:125px;
    justify-content: center;
    align-items: center;
}

h3 {
  font-size: 1.2rem;
}

h4 {
  font-size: 1.0rem;
}

.greetings h1,
.greetings h3 {
  text-align: center;


}



@media (min-width: 1000px) {

  .greetings h1,
  .greetings h3 {
    text-align: center;
  }
}
</style>
