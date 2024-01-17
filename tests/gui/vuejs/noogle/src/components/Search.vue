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
        items = []
        store.state.results = []
        let client = store.state.client
        let tags = []
        tags.push(Tag.parse(["i", message, "text"]))
        tags.push(Tag.parse(["param", "max_results", "100"]))
        let evt = new EventBuilder(5302, "Search for me", tags)
        let res = await client.sendEventBuilder(evt)
        miniToastr.showMessage("Sent Request to DVMs", "Awaiting results", VueNotifications.types.info)
        if (!listener){
               listen()
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


              for (const evt of events){
                     items.push({ content: evt.content, author: evt.author.toBech32(), authorurl: "https://njump.me/" + evt.author.toBech32(),  indicator: {"time": evt.createdAt.toHumanDatetime()}})
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
    <h1 class="purple">Noogle</h1>
    <h3>
    <div>
          <button class="c-Button"  @click="send_search_request(message)">Search the Nostr
          </button> <input class="c-Input" v-model="message" >
    </div>
<!--
      <a href="https://vitejs.dev/" target="_blank" rel="noopener">Vite</a> +
      <a href="https://vuejs.org/" target="_blank" rel="noopener">Vue 3</a>. -->
    </h3>

  </div>
</template>

<style scoped>

.c-Button {
  height: 50px;
  color: white;
  background: #8e30eb;


}

.c-Input {
  margin: -5px;
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
    text-align: left;
  }
}
</style>
