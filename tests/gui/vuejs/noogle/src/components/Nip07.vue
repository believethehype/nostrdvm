<template>
  <div>
     <div class="playeauthor-wrapper" v-if="current_user">
        <img class="avatar" @click="sign_out()" :src="this.avatar" alt="" />
         <p>{{ this.current_user }}</p>
     </div>

    <template v-if="!current_user">
      <div className="dropdown">
      <div tabIndex={0} role="button" class="v-Button" >Sign in</div>
      <div tabIndex={0} className="dropdown-content -start-44 z-[1] horizontal card card-compact w-64 p-2 shadow bg-primary text-primary-content">
        <div className="card-body">
          <h3 className="card-title">Nip07 Login</h3>
          <p>Use a Browser Nip07 Extension like getalby or nos2x to login</p>
          <button className="btn" @click="sign_in_nip07()">Nip07 Sign in</button>
        </div>
      </div>
    </div>
      <Nip89></Nip89>
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
  Timestamp, Keys, NostrDatabase, ClientBuilder, ClientZapper, Alphabet
} from "@rust-nostr/nostr-sdk";
import VueNotifications from "vue-notifications";
import store from '../store';
import Nip89 from "@/components/Nip89.vue";
import miniToastr from "mini-toastr";
import deadnip89s from "@/components/data/deadnip89s.json";
let nip89dvms = []
export default {
   data() {
    return {
      current_user: "",
      avatar: "",
      signer: "",

    };
  },
  async mounted() {
     try{
        if (localStorage.getItem('nostr-key-method') === 'nip07')
        {
           await this.sign_in_nip07()
        }
        else {
          await this.sign_in_anon()
        }

        await this.getnip89s()
     }
    catch (error){
       console.log(error);
    }

  },

  methods: {
    async sign_in_anon() {
      try {
         await loadWasmAsync();
         try {
            initLogger(LogLevel.debug());
        } catch (error) {
            console.log(error);
        }

        let keys = Keys.fromSkStr("ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e")
        this.signer = ClientSigner.keys(keys) //TODO store keys
        let client = new ClientBuilder().signer(this.signer).build()

        for (const relay of store.state.relays){
           await client.addRelay(relay);
        }

        const pubkey =  keys.publicKey
        await client.connect();

        /*
        const filter = new Filter().kind(6302).limit(20)
        await client.reconcile(filter);
        const filterl = new Filter().author(pubkey)
        let test = await client.database.query([filterl])
        for (let ev of test){
          console.log(ev.asJson())
        }*/




        store.commit('set_client', client)
        store.commit('set_pubkey', pubkey)
        store.commit('set_hasEventListener', false)
        localStorage.setItem('nostr-key-method', "anon")
        localStorage.setItem('nostr-key', "")
        console.log("Client connected")


      } catch (error) {
        console.log(error);
      }
    },
    async sign_in_nip07() {

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
              console.log("SIGNER: " + this.signer)

            } catch (error) {
            console.log(error);
             this.signer = ClientSigner.keys(Keys.generate())
          }

        let zapper = ClientZapper.webln()
        let client = new ClientBuilder().signer(this.signer).zapper(zapper).build();

        for (const relay of store.state.relays){
                 await client.addRelay(relay);
              }

        const pubkey = await nip07_signer.getPublicKey();
        await client.connect();

        /*
        const filter = new Filter().kind(6302).limit(20)
        await client.reconcile(filter);
        const filterl = new Filter().author(pubkey)
        let test = await client.database.query([filterl])
        for (let ev of test){
          console.log(ev.asJson())
        }*/

        store.commit('set_client', client)
        store.commit('set_pubkey', pubkey)
        store.commit('set_hasEventListener', false)
        localStorage.setItem('nostr-key-method', "nip07")
        localStorage.setItem('nostr-key', "")
        console.log("Client connected")
        await this.get_user_info(pubkey)
        //miniToastr.showMessage("Login successful!", "Logged in as " + this.current_user, VueNotifications.types.success)

      } catch (error) {
        console.log(error);
      }
    },
    async getnip89s(){

        //let keys = Keys.generate()
        let keys = Keys.fromSkStr("ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e")

        let signer = ClientSigner.keys(keys) //TODO store keys
        let client = new ClientBuilder().signer(signer).build()
        //await client.addRelay("wss://nos.lol");
        await client.addRelay("wss://relay.f7z.io")
        await client.addRelay("wss://pablof7z.nostr1.com")
        //await client.addRelay("wss://relay.nostr.net")
        await client.addRelay("wss://relay.nostr.band");
        //await client.addRelay("wss://nostr-pub.wellorder.net")
        await client.connect();

        let dvmkinds = []
        for (let i = 5000; i < 6000; i++) {
          dvmkinds.push((i.toString()))
        }
        console.log(dvmkinds)

        const filter = new Filter().kind(31990).customTag(Alphabet.K, dvmkinds)
        //await client.reconcile(filter);
        //const filterl = new Filter().kind(31990)
        //let evts = await client.database.query([filterl])
        let evts = await client.getEventsOf([filter], 3)
        for (const entry of evts){
          for (const tag in entry.tags){
            if (entry.tags[tag].asVec()[0] === "k")
              if(entry.tags[tag].asVec()[1] >= 5000 && entry.tags[tag].asVec()[1] <= 5999 &&  deadnip89s.filter(i => i.id === entry.id.toHex() ).length === 0) {   // blocklist.indexOf(entry.id.toHex()) < 0){

                console.log(entry.tags[tag].asVec()[1])

                try {

                    let jsonentry = JSON.parse(entry.content)
                      if (jsonentry.picture){
                        jsonentry.image = jsonentry.picture
                      }
                      jsonentry.event = entry.asJson()
                    jsonentry.kind = entry.tags[tag].asVec()[1]
                   nip89dvms.push(jsonentry);
                }
                catch (error){
                  console.log(error)
                }

              }
           }
        }
        store.commit('set_nip89dvms', nip89dvms)

        return nip89dvms


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
      await this.state.client.shutdown();
      localStorage.setItem('nostr-key-method', "")
      localStorage.setItem('nostr-key', "")
      await this.sign_in_anon()
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

.v-Button {
  @apply bg-black  text-center hover:bg-nostr focus:ring-nostr mb-2 inline-flex flex-none items-center rounded-lg border border-nostr px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
  margin-right: 14px;
  height: 44px;
  width: 70px
}

</style>