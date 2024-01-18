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

<button class="c-Button" @click="zap()">Donate</button>
</template>

<style scoped>
.c-Button {
  height: 20px;
  color: white;
  background: #000000;
}
</style>