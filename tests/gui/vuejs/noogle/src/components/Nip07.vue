<template>
  <div>
     <div class="playeauthor-wrapper" v-if="current_user">
        <img class="avatar" :src="this.avatar" alt="" />
         <p>Current User is: {{ this.current_user }}</p>
     </div>
    <template v-if="current_user">
     <button class="b-Button" @click="sign_out()">Sign out</button>
    </template>
    <template v-if="!current_user">
     <button class="c-Button" @click="sign_in()">Sign in</button>
    </template>


  </div>
</template>

<script>
import {
  loadWasmAsync,
  Client,
  ClientSigner,
  Nip07Signer,
  Filter,
  initLogger,
  LogLevel,
  Timestamp, Keys, NostrDatabase, ClientBuilder
} from "@rust-nostr/nostr-sdk";
import VueNotifications from "vue-notifications";
import store from '../store';
import miniToastr from "mini-toastr";

export default {
   data() {
    return {
      current_user: "",
      avatar: "",
      signer: "",

    };
  },
  async mounted() {
    await this.sign_in();
  },

  methods: {
    async sign_in() {

      try {

        await loadWasmAsync();

             try {
                initLogger(LogLevel.debug());
            } catch (error) {
                console.log(error);
            }

        let nip07_signer = new Nip07Signer();
            try{
              this.signer = ClientSigner.nip07(nip07_signer);

            } catch (error) {
            console.log(error);
             this.signer = ClientSigner.keys(Keys.generate())
          }



        let database =  await NostrDatabase.open("test.db")
        let client = new ClientBuilder().database(database).signer(this.signer).build()


        //await client.addRelay("wss://relay.damus.io");
        await client.addRelay("wss://nos.lol");
        await client.addRelay("wss://relay.f7z.io")
        await client.addRelay("wss://pablof7z.nostr1.com")
        //await client.addRelay("wss://relay.nostr.net")
        //await client.addRelay("wss://relay.nostr.band");
        //await client.addRelay("wss://nostr-pub.wellorder.net")

        const pubkey = await nip07_signer.getPublicKey();
        await client.connect();


        const filter = new Filter().kind(6302).limit(20)
        //TODO this next line breaks the code
        //await client.reconcile(filter);
        /*const filterl = new Filter().author(pubkey)
        let test = dbclient.database().query([filterl])
        for (let ev of test){
          console.log(ev.as_json())
        }
        */


        store.commit('set_client', client)
        store.commit('set_pubkey', pubkey)
        console.log("Client connected")



        await this.get_user_info(pubkey)
        miniToastr.showMessage("Login successful!", "Logged in as " + this.current_user, VueNotifications.types.success)





      } catch (error) {
        console.log(error);
      }
    },
    async get_user_info(pubkey){
        let client = store.state.client
        const profile_filter = new Filter().kind(0).author(pubkey).limit(1)
        let evts = await client.getEventsOf([profile_filter], 10)
        console.log("PROFILES:" + evts.length)
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
              this.current_user = profile["name"]
              this.avatar = profile["picture"]

            }
    },

    async sign_out(){
      this.current_user = ""
    }
  },
};
</script>

<style scoped>
.operation-wrapper .operation-icon {
  width: 20px;
  cursor: pointer;
}
.playeauthor-wrapper {
  padding: 5px;
  display: flex;
  align-items: center;
  justify-items: center;
}
.avatar {
  margin-right: 10px;
  display: inline-block;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: inset 0 2px 4px 0 rgb(0 0 0 / 10%);
}

.b-Button {
  height: 30px;
  color: white;
  background: purple;


}

.c-Button {
  height: 30px;
  color: white;
  background: #8e30eb;


}
</style>