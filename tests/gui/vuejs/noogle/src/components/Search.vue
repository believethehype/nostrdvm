<script setup>
import {Client, Filter, Timestamp, Event, Metadata, PublicKey, EventBuilder, Tag, EventId} from "@rust-nostr/nostr-sdk";
import store from '../store';
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";

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
        store.state.results = []
        let client = store.state.client
        let tags = []
        let users = [];

        const taggedUsersFrom = message.split(' ')
          .filter(word => word.startsWith('from:'))
          .map(word => word.replace('from:', ''));

        // search
        let search = message;

        // tags

        for (const word of taggedUsersFrom) {
          search = search.replace(word, "");
          const userPubkey = PublicKey.fromBech32(word.replace("@", "")).toHex()
          const pTag = Tag.parse(["p", userPubkey]);
          users.push(pTag.asVec());
        }

        message = search.replace(/from:|to:|@/g, '').trim();
        console.log(search);

        tags.push(Tag.parse(["i", message, "text"]))
        tags.push(Tag.parse(["param", "max_results", "100"]))
        tags.push(Tag.parse(['param', 'users', JSON.stringify(users)]))

        let evt = new EventBuilder(5302, "NIP 90 Search request", tags)
        let res = await client.sendEventBuilder(evt)
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
          profiles.push({profile: JSON.parse(entry.content), author: entry.author.toHex(), createdAt: entry.createdAt});
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
            console.log("Received new event from", relayUrl);
            if (event.kind === 7000) {
                try {
                    console.log("7000:", event.content);
                    miniToastr.showMessage("DVM replied", event.content, VueNotifications.types.info)


                    //if (content === "stop") {
                    //    return true
                    //}
                } catch (error) {
                    console.log("Error: ", error);
                }
            }
            else if(event.kind === 6302) {
              let entries = []
              console.log("6302:", event.content);
              miniToastr.showMessage("DVM replied", "Received Results", VueNotifications.types.success)
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
                      let picture = p === undefined ? "../assets/nostr-purple.svg" : p["profile"]["picture"]
                      let name = p === undefined ? bech32id : p["profile"]["name"]
                      let highlighterurl = "https://highlighter.com/a/" + bech32id
                      let njumpurl = "https://njump.me/" + bech32id
                      let nostrudelurl = "https://nostrudel.ninja/#/n/" + evt.id.toBech32()
                      items.push({ content: evt.content, author: name, authorurl: "https://njump.me/" + evt.author.toBech32(), links: {"highlighter": highlighterurl, "njump": njumpurl, "nostrudel": nostrudelurl} , avatar: picture,  indicator: {"time": evt.createdAt.toHumanDatetime()}})



                }

               store.commit('set_search_results', items)
            }
        },
        // Handle relay message
        handleMsg: async (relayUrl, message) => {
            //console.log("Received message from", relayUrl, message.asJson());
        }
    };

    client.handleNotifications(handle);
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

      <h1
				class="text-center text-5xl md:text-6xl font-extrabold tracking-wider sm:text-start sm:text-6xl lg:text-8xl">
				<span class="bg">Noogle</span>

			</h1>
       <h2 class="text-base-200-content text-center text-2xl font-thin sm:text-start">
				Search the Nostr with Data Vending Machines
			</h2>

    <h3>

      <br>
          <input class="c-Input" v-model="message">
          <button class="v-Button"  @click="send_search_request(message)">Search the Nostr
          </button>

<!--
      <a href="https://vitejs.dev/" target="_blank" rel="noopener">Vite</a> +
      <a href="https://vuejs.org/" target="_blank" rel="noopener">Vue 3</a>. -->
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


  width: 400px;
  height: 48px;
   color: white;
  background: black;
}

h1 {

  font-weight: 500;
  font-size: 2.6rem;
  position: relative;
  top: -10px;
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
