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
  Timestamp
} from "@rust-nostr/nostr-sdk";
import VueNotifications from "vue-notifications";
import store from '../store';

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
  notifications: {
    showSuccessMsg: {
      type: VueNotifications.types.success,
      title: 'Login',
      message: 'That\'s the success!'
    },
    showInfoMsg: {
      type: VueNotifications.types.info,
      title: 'Hey you',
      message: 'Here is some info for you'
    },
    showWarnMsg: {
      type: VueNotifications.types.warn,
      title: 'Wow, man',
      message: 'That\'s the kind of warning'
    },
    showErrorMsg: {
      type: VueNotifications.types.error,
      title: 'Wow-wow',
      message: 'That\'s the error'
    }
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
        this.signer = ClientSigner.nip07(nip07_signer);

        let client = new Client(this.signer);

        //await client.addRelay("wss://relay.damus.io");
        //await client.addRelay("wss://nos.lol");
        await client.addRelay("wss://relay.nostr.band");
        await client.addRelay("wss://nostr-pub.wellorder.net")

        const pubkey = await nip07_signer.getPublicKey()
        await client.connect();


        store.commit('set_client', client)
        console.log("Client connected")

        await this.get_user_info(pubkey)

        //this.current_user =  (await nip07_signer.getPublicKey()).toBech32()
        //console.log( this.current_user)
        this.showSuccessMsg()



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