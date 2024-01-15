<script setup>
import {Client, Filter, Timestamp, Event, Metadata, PublicKey, EventBuilder, Tag, EventId} from "@rust-nostr/nostr-sdk";
import store from '../store';

let items = []
async function get_some_stuff(message) {
   try {
     if (message === undefined){
       message = "Nostr"
     }

        //console.log( store.state.test + " " + message)
        const filter = new Filter().kind(1).limit(20).search(message);
         //console.log('filter', filter.asJson());
    let client = store.state.client
    let events = await client.getEventsOf([filter], 3);
    //console.log(events.length)
     let items = []
    for (const e of events) {
          let name = e.pubkey.toBech32()
          let nip05 = ""
          let lud16 = ""
          let picture = ""
          //console.log(e.pubkey.toHex())
          const profile_filter = new Filter().kind(0).author(e.pubkey).limit(1)
          let evts = await client.getEventsOf([profile_filter], 5)
          if (evts.length > 0){
               let latest_entry = evts[0]
               let latest_time = 0

                for (const entry of evts){
                   if (entry.createdAt.asSecs() > latest_time){
                      latest_time = entry.createdAt.asSecs();
                      latest_entry = entry
                   }
                }

                let profile =  JSON.parse(latest_entry.content);
                name = profile["name"]
                picture = profile["picture"]

              }



          items.push({ content: e.content, author: name, authorurl: "https://njump.me/" + e.pubkey.toBech32(), avatar:
                picture, indicator: {"time": e.createdAt.toHumanDatetime()}})
            //console.log(e.asJson())
          }
          store.commit('set_search_results', items)

        //await client.publishTextNote("Test from Rust Nostr SDK JavaScript bindings with NIP07 signer!", []);
      } catch (error) {
        console.log(error);
      }
}

async function send_search_request(message) {
   try {
     if (message === undefined){
       message = "Nostr"
     }
        items = []
        let client = store.state.client
        let tags = []
        tags.push(Tag.parse(["i", message, "text"]))
        let evt = new EventBuilder(5302, "Search for me", tags)
        let res = await client.sendEventBuilder(evt)
        console.log(res)
        await this.listen()

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
    let client = store.state.client

    const filter = new Filter().kinds([7000, 6302]).since(Timestamp.now());
    await client.subscribe([filter]);

    const handle = {
        // Handle event
        handleEvent: async (relayUrl, event) => {
            console.log("Received new event from", relayUrl);
            if (event.kind === 7000) {
                try {
                    console.log("7000:", event.content);


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
               let event_etags = JSON.parse(event.content)
                for (let etag of event_etags){
                  const eventid = EventId.fromHex(etag[1])
                  entries.push(eventid)
                }
                const events = await getEvents(entries)
                for (const evt of events){
                     items.push({ content: evt.content, author: evt.author.toHex(), indicator: {"time": evt.createdAt.toHumanDatetime()}})
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
