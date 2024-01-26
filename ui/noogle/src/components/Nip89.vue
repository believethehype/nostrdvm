<template>
</template>

<script>
import {
  ClientSigner,
  Filter,
  Keys, ClientBuilder, Alphabet
} from "@rust-nostr/nostr-sdk";
import store from '../store';
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
        await this.getnip89s()
     }
    catch (error){
       console.log(error);
    }

  },

  methods: {
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


        const filter = new Filter().kind(31990).customTag(Alphabet.K, dvmkinds)
        //await client.reconcile(filter);
        //const filterl = new Filter().kind(31990)
        //let evts = await client.database.query([filterl])
        let evts = await client.getEventsOf([filter], 3)
        for (const entry of evts){
          for (const tag in entry.tags){
            if (entry.tags[tag].asVec()[0] === "k")

              if(entry.tags[tag].asVec()[1] >= 5000 && entry.tags[tag].asVec()[1] <= 5999 &&  deadnip89s.filter(i => i.id === entry.id.toHex() ).length === 0) {   // blocklist.indexOf(entry.id.toHex()) < 0){
                try {
                    let jsonentry = JSON.parse(entry.content)
                      if (jsonentry.picture){
                        jsonentry.image = jsonentry.picture
                      }
                    jsonentry.event = entry.asJson()
                    jsonentry.createdAt = entry.createdAt.asSecs()
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

  },
};
</script>

<style scoped>

</style>