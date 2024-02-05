<template>
<!--<label class="swap swap-rotate">

  <input type="checkbox" class="theme-controller" value="synthwave"  @click="toggleDark()" />

  <svg class="swap-on fill-current w-10 h-10" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M5.64,17l-.71.71a1,1,0,0,0,0,1.41,1,1,0,0,0,1.41,0l.71-.71A1,1,0,0,0,5.64,17ZM5,12a1,1,0,0,0-1-1H3a1,1,0,0,0,0,2H4A1,1,0,0,0,5,12Zm7-7a1,1,0,0,0,1-1V3a1,1,0,0,0-2,0V4A1,1,0,0,0,12,5ZM5.64,7.05a1,1,0,0,0,.7.29,1,1,0,0,0,.71-.29,1,1,0,0,0,0-1.41l-.71-.71A1,1,0,0,0,4.93,6.34Zm12,.29a1,1,0,0,0,.7-.29l.71-.71a1,1,0,1,0-1.41-1.41L17,5.64a1,1,0,0,0,0,1.41A1,1,0,0,0,17.66,7.34ZM21,11H20a1,1,0,0,0,0,2h1a1,1,0,0,0,0-2Zm-9,8a1,1,0,0,0-1,1v1a1,1,0,0,0,2,0V20A1,1,0,0,0,12,19ZM18.36,17A1,1,0,0,0,17,18.36l.71.71a1,1,0,0,0,1.41,0,1,1,0,0,0,0-1.41ZM12,6.5A5.5,5.5,0,1,0,17.5,12,5.51,5.51,0,0,0,12,6.5Zm0,9A3.5,3.5,0,1,1,15.5,12,3.5,3.5,0,0,1,12,15.5Z"/></svg>

  <svg class="swap-off fill-current w-10 h-10" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M21.64,13a1,1,0,0,0-1.05-.14,8.05,8.05,0,0,1-3.37.73A8.15,8.15,0,0,1,9.08,5.49a8.59,8.59,0,0,1,.25-2A1,1,0,0,0,8,2.36,10.14,10.14,0,1,0,22,14.05,1,1,0,0,0,21.64,13Zm-9.5,6.69A8.14,8.14,0,0,1,7.08,5.22v.27A10.15,10.15,0,0,0,17.22,15.63a9.79,9.79,0,0,0,2.1-.22A8.11,8.11,0,0,1,12.14,19.73Z"/></svg>

</label> -->
  <div>
     <div class="playeauthor-wrapper" v-if="current_user">

        <div className="dropdown">
          <div tabIndex={0} role="button" class="button" >
              <img class="avatar"  :src="this.avatar" alt="" />
          </div>
      <div tabIndex={0} className="dropdown-content -start-44 z-[1] horizontal card card-compact w-64 p-2 shadow bg-primary text-primary-content">
        <div className="card-body">
          <h3 className="card-title">Sign out of your account</h3>
          <!--<p>Sign out</p> -->
          <button className="btn" @click="sign_out()">Sign Out</button>
        </div>
      </div>
    </div>
         <p>{{ this.current_user }}</p>
     </div>

    <template v-if="!current_user">
      <div className="dropdown">
      <div tabIndex={0} role="button" class="v-Button" >Sign in</div>
      <div tabIndex={0} className="dropdown-content -start-44 z-[1] horizontal card card-compact w-64 p-2 shadow bg-primary text-primary-content">
        <div className="card-body">
          <h3 className="card-title">Nip07 Login</h3>
          <p>Use a Browser Nip07 Extension like getalby or nos2x to login or use Amber on Android</p>
         <button className="btn" @click="sign_in_nip07()">Browser Extension</button>
         <template v-if="supports_android_signer">
          <button className="btn" @click="sign_in_amber()">Amber Sign in</button>
        </template>
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
  Timestamp, Keys, NostrDatabase, ClientBuilder, ClientZapper, Alphabet, SingleLetterTag, Options, Duration, PublicKey
} from "@rust-nostr/nostr-sdk";
import VueNotifications from "vue-notifications";
import store from '../store';
import Nip89 from "@/components/Nip89.vue";
import miniToastr from "mini-toastr";
import deadnip89s from "@/components/data/deadnip89s.json";
import amberSignerService from "./android-signer/AndroidSigner";
import {useDark, useToggle} from "@vueuse/core";
const isDark = useDark();
//const toggleDark = useToggle(isDark);



let nip89dvms = []
let logger = true
export default {
   data() {
    return {
      current_user: "",
      avatar: "",
      signer: "",
      supports_android_signer: false,
    };
  },
  async mounted() {
     try{
        if (amberSignerService.supported) {
          this.supports_android_signer = true;
        }
        
        if (localStorage.getItem('nostr-key-method') === 'nip07')
        {
           await this.sign_in_nip07()
        }

        else  if (localStorage.getItem('nostr-key-method') === 'android-signer')
        {
          let key = ""
          if (localStorage.getItem('nostr-key') !== ""){
            key = localStorage.getItem('nostr-key')
          }
          await this.sign_in_amber(key)
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

    toggleDark(){
       isDark.value = !isDark.value
       useToggle(isDark);
       console.log(isDark.value)
      if (localStorage.isDark === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }
    },

    async sign_in_anon() {
      try {
         await loadWasmAsync();
       if(logger){
            try {
                initLogger(LogLevel.debug());
            } catch (error) {
                console.log(error);
            }
        }

        let keys = Keys.fromSkStr("ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e")
        this.signer = ClientSigner.keys(keys) //TODO store keys
        let opts = new Options().waitForSend(false).connectionTimeout(Duration.fromSecs(5));
        let client = new ClientBuilder().signer(this.signer).opts(opts).build()

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

        if(logger){
            try {
                initLogger(LogLevel.debug());
            } catch (error) {
                console.log(error);
            }
        }


        let nip07_signer = new Nip07Signer();
            try{
              this.signer = ClientSigner.nip07(nip07_signer);
              console.log("SIGNER: " + this.signer)


            } catch (error) {
            console.log(error);
             this.signer = ClientSigner.keys(Keys.generate())
          }

        //let zapper = ClientZapper.webln()
        let opts = new Options().waitForSend(false).connectionTimeout(Duration.fromSecs(5));
        let client = new ClientBuilder().signer(this.signer).opts(opts).build()


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
    async sign_in_amber(key="") {
      try {

        await loadWasmAsync();

        if(logger){
            try {
                initLogger(LogLevel.debug());
            } catch (error) {
                console.log(error);
            }
        }

        if (!amberSignerService.supported) {
          alert("android signer not supported")
          return;
        }

        try{
        let hexKey = ""
        if (key === ""){
            hexKey = await amberSignerService.getPublicKey();
        }
        else{
          hexKey = key
        }
        let publicKey = PublicKey.fromHex(hexKey);
        let keys = Keys.fromPublicKey(publicKey)
        this.signer = ClientSigner.keys(keys)
        let opts = new Options().waitForSend(false).connectionTimeout(Duration.fromSecs(5));
        let client = new ClientBuilder().signer(this.signer).opts(opts).build()
        for (const relay of store.state.relays){
          await client.addRelay(relay);
        }
        await client.connect();
        store.commit('set_client', client)
        store.commit('set_pubkey', publicKey)
        store.commit('set_hasEventListener', false)
        localStorage.setItem('nostr-key-method', "android-signer")
        localStorage.setItem('nostr-key', hexKey)
        await this.get_user_info(publicKey)
                }
        catch (error){
          alert(error)
        }

        //miniToastr.showMessage("Login successful!", "Logged in as " + publicKey.toHex(), VueNotifications.types.success)

      } catch (error) {
        console.log(error);
      }
    },
    async getnip89s(){

        //let keys = Keys.generate()
        let keys = Keys.fromSkStr("ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e")

        let signer = ClientSigner.keys(keys) //TODO store keys
        let client = new ClientBuilder().signer(signer).build()
        for (const relay of store.state.relays){
           await client.addRelay(relay);
        }
        await client.connect();

        let dvmkinds = []
        for (let i = 5000; i < 6000; i++) {
          dvmkinds.push((i.toString()))
        }
        //console.log(dvmkinds)

        const filter = new Filter().kind(31990).customTag(SingleLetterTag.lowercase(Alphabet.K), dvmkinds)
        //await client.reconcile(filter);
        //const filterl = new Filter().kind(31990)
        //let evts = await client.database.query([filterl])
        let evts = await client.getEventsOf([filter], 3)
        for (const entry of evts){
          for (const tag in entry.tags){
            if (entry.tags[tag].asVec()[0] === "k")
              if(entry.tags[tag].asVec()[1] >= 5000 && entry.tags[tag].asVec()[1] <= 5999 &&  deadnip89s.filter(i => i.id === entry.id.toHex() ).length === 0) {   // blocklist.indexOf(entry.id.toHex()) < 0){

              //  console.log(entry.tags[tag].asVec()[1])

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
                  //console.log(error)
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
      localStorage.setItem('nostr-key-method', "anon")
      localStorage.setItem('nostr-key', "")
      await this.state.client.shutdown();
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