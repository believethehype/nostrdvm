<script>
import { requestProvider } from "webln";
export default {

  methods: {
    async zap() {
      let webln;
      try {
        webln = await requestProvider();
      } catch (err) {
        // Handle users without WebLN
      }

      if (webln) {
        let invoice = await this.createBolt11Lud16("hype@bitcoinfixesthis.org", 1000)
        console.log(invoice)
        let response = await webln.sendPayment(invoice)
        console.log(response)
      }
    },

    async createBolt11Lud16(lud16, amount) {
    let url;
      if (lud16.includes('@')) {  // LNaddress
        const parts = lud16.split('@');
        url = `https://${parts[1]}/.well-known/lnurlp/${parts[0]}`;
    } else {  // No lud16 set or format invalid
        return null;
    }

    try {
        console.log(url);
        const response = await fetch(url);
        const ob = await response.json();
        const callback = ob.callback;
        const amountInSats = parseInt(amount) * 1000;
        const callbackResponse = await fetch(`${callback}?amount=${amountInSats}`);
        const obCallback = await callbackResponse.json();
        return obCallback.pr;
      } catch (e) {
          console.log(`LUD16: ${e}`);
          return null;
      }
    }

  }
}


</script>

<template>


<button class="v-Button" @click="zap()"><svg class="relative w-5 h-5 mr-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
Donate</button>



</template>

<style scoped>


.v-Button {
 @apply bg-black hover:bg-amber-400 focus:ring-purple-950 mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
   height: 24px;


}
</style>