<template>

    <div class="max-w-xs relative space-y-3">

      <ul>
        <div className="card w-96 bg-base-100 shadow-xl"  v-for="dvm in Nip89DVMS"
            :key="dvm.name">
        <figure><img :src="dvm.image" alt="DVM Picture" /></figure>
        <div className="card-body">
          <h2 className="card-title">{{ dvm.name }}</h2>
          <p>  {{ dvm.about }}</p>
          <div className="card-actions justify-end">
            <button className="btn btn-primary">Buy Now</button>
          </div>
        </div>
      </div>
      </ul>

      <p
        v-if="selectedCountry"
        class="text-lg pt-2 absolute"
      >
        You have selected: <span class="font-semibold">{{ selectedCountry }}</span>
      </p>
    </div>

</template>

<script>
import countries from './data/countries.json'
import {ref, computed, onMounted} from 'vue'
import '../app.css'
import store from "@/store.js";
import {Filter} from "@rust-nostr/nostr-sdk";

async function getnip89s(){

        let client = store.state.client
        const filter = new Filter().kind(31990)
        let evts = await client.getEventsOf([filter], 10)
        for (const entry of evts){
          console.log(entry.content)
          try {
              let jsonentry = JSON.parse(entry.content)
                if (jsonentry.picture){
                  jsonentry.image = jsonentry.picture
                }
             nip89dvms.push(jsonentry);
          }
          catch (error){
            console.log(error)
          }

        }

        return nip89dvms

    }
let nip89dvms = []
export default {

async mounted(){
      nip89dvms = await getnip89s()

    },

  setup() {





  const Nip89DVMS = computed(() => {
      console.log(nip89dvms)
      return nip89dvms;
    });

    const selectCountry = (country) => {
      selectedCountry.value = country
    }

    let selectedCountry = ref('')

    return {
      countries,
      Nip89DVMS,
      selectCountry,
      selectedCountry
    }
  }
}
</script>