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
  Nip19Event
} from "@rust-nostr/nostr-sdk";
import store from '../store';
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";
import searchdvms from './data/searchdvms.json'
import {computed} from "vue";
import countries from "@/components/data/countries.json";
import deadnip89s from "@/components/data/deadnip89s.json";

let items = []

let listener = false




async function send_search_request(message) {
   try {
     if (message === undefined){
       message = "Nostr"
     }

     if(store.state.pubkey === undefined){
               miniToastr.showMessage("Please login first", "No pubkey set", VueNotifications.types.warn)
          return
     }
        items = []
        store.commit('set_search_results', items)
        let client = store.state.client
        let tags = []
        let users = [];

        const taggedUsersFrom = message.split(' ')
          .filter(word => word.startsWith('from:'))
          .map(word => word.replace('from:', ''));

        // search
        let search = message;

        // tags

        for (let word of taggedUsersFrom) {
          search = search.replace(word, "");
          if(word === "me"){
            word = store.state.pubkey.toBech32()
          }
          const userPubkey = PublicKey.fromBech32(word.replace("@", "")).toHex()
          const pTag = Tag.parse(["p", userPubkey]);
          users.push(pTag.asVec());
        }

        message = search.replace(/from:|to:|@/g, '').trim();
        console.log(search);

        tags.push(Tag.parse(["i", message, "text"]))
        tags.push(Tag.parse(["param", "max_results", "150"]))
        tags.push(Tag.parse(['param', 'users', JSON.stringify(users)]))

        let evt = new EventBuilder(5302, "NIP 90 Search request", tags)
        let res = await client.sendEventBuilder(evt)
        store.commit('set_current_request_id_search', res.toHex())
        console.log("SEARCH EVENT SENT: " + res.toHex())
        miniToastr.showMessage("Sent Request to DVMs", "Awaiting results", VueNotifications.types.warn)
        if (!store.state.hasEventListener){
               listen()
           store.commit('set_hasEventListener', true)
        }
        else{
          console.log("Already has event listener")
        }

        console.log(res)


      } catch (error) {
        console.log(error);
      }
}

async function getEvents(eventids) {
  const event_filter = new Filter().ids(eventids)
  let client = store.state.client
  return await client.getEventsOf([event_filter], 5)
}

async function get_user_infos(pubkeys){
        let profiles = []
        let client = store.state.client
        const profile_filter = new Filter().kind(0).authors(pubkeys)
        let evts = await client.getEventsOf([profile_filter], 10)
        console.log("PROFILES:" + evts.length)
        for (const entry of evts){
          try{
            let contentjson = JSON.parse(entry.content)
            profiles.push({profile: contentjson, author: entry.author.toHex(), createdAt: entry.createdAt});
          }
          catch(error){
            console.log("error")
          }

        }

        return profiles

    }

async function  listen() {
    listener = true
    let client = store.state.client
    let pubkey = store.state.pubkey

    const filter = new Filter().kinds([7000, 6302]).pubkey(pubkey).since(Timestamp.now());
    await client.subscribe([filter]);

    const handle = {
        // Handle event
        handleEvent: async (relayUrl, event) => {
              if (store.state.hasEventListener === false){
                return true
              }
            const dvmname =  getNamefromId(event.author.toHex())
            console.log("Received new event from", relayUrl);
            let resonsetorequest = false
            for (let tag in event.tags) {
              if (event.tags[tag].asVec()[0] === "e") {
                //console.log("SEARCH ETAG: " + event.tags[tag].asVec()[1])
                // console.log("SEARCH LISTEN TO : " + store.state.requestidSearch)
                if (event.tags[tag].asVec()[1] ===  store.state.requestidSearch) {
                  resonsetorequest = true
                }
              }

            }
          if(resonsetorequest){

            if (event.kind === 7000) {
                try {
                    console.log("7000: ", event.content);
                    console.log("DVM: " + event.author.toHex())
                    miniToastr.showMessage("DVM: " + dvmname, event.content, VueNotifications.types.info)
                } catch (error) {
                    console.log("Error: ", error);
                }
            }
            else if(event.kind === 6302) {
              let entries = []
              console.log("6302:", event.content);

              miniToastr.showMessage("DVM: " + dvmname, "Received Results", VueNotifications.types.success)
               let event_etags = JSON.parse(event.content)
                for (let etag of event_etags){
                  const eventid = EventId.fromHex(etag[1])
                  entries.push(eventid)
                }
                const events = await getEvents(entries)
                let authors = []
                for (const evt of events){
                    authors.push(evt.author)
                }
             let profiles = await get_user_infos(authors)


              for (const evt of events){
                     let p = profiles.find( record => record.author === evt.author.toHex())
                      let bech32id = evt.id.toBech32()
                      let nip19 = new Nip19Event(event.id, event.author, store.state.relays)
                      let nip19bech32 = nip19.toBech32()
                      let picture = p === undefined ? "../assets/nostr-purple.svg" : p["profile"]["picture"]
                      let name = p === undefined ? bech32id : p["profile"]["name"]
                      let highlighterurl = "https://highlighter.com/a/" + bech32id
                      let njumpurl = "https://njump.me/" + bech32id
                      let nostrudelurl = "https://nostrudel.ninja/#/n/" + bech32id
                      let uri =  "nostr:" + bech32id //  nip19.toNostrUri()

                      if (items.find(e => e.id.toHex() === evt.id.toHex())  === undefined) {
                          items.push({id:evt.id,  content: evt.content, author: name, authorurl: "https://njump.me/" + evt.author.toBech32(), links: {"uri": uri, "highlighter": highlighterurl, "njump": njumpurl, "nostrudel": nostrudelurl} , avatar: picture,  indicator: {"time": evt.createdAt.toHumanDatetime()}})
                      }


                }
               console.log("Events from" + event.author.toHex())
               console.log(items)
               store.commit('set_search_results', items)
            }
              }
        },
        // Handle relay message
        handleMsg: async (relayUrl, message) => {
            //console.log("Received message from", relayUrl, message.asJson());
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

function nextInput(e) {
  const next = e.currentTarget.nextElementSibling;
  if (next) {
    next.focus();

  }
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
    <h2 class="text-base-200-content text-center tracking-wide text-2xl font-thin">
    Search the Nostr with Data Vending Machines</h2>
    <h3>
     <br>
     <input class="c-Input" autofocus placeholder="Search..." v-model="message"  @keyup.enter="send_search_request(message)" @keydown.enter="nextInput">
     <button class="v-Button"  @click="send_search_request(message)">Search the Nostr</button>
    </h3>

  </div>
</template>

<style scoped>

.v-Button {
  @apply bg-nostr hover:bg-nostr2 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-black px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
   height: 48px;
   margin: 5px;
}

.c-Input {
    @apply bg-black hover:bg-gray-900 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;

  width: 350px;
  height: 48px;
  color: white;
  background: black;
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

.greetings h1,
.greetings h3 {
  text-align: center;

}

@media (min-width: 1024px) {

  .greetings h1,
  .greetings h3 {
    text-align: center;
  }
}
</style>
