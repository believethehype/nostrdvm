<script>
import { requestProvider } from "webln";
import miniToastr from "mini-toastr";
import VueNotifications from "vue-notifications";
import {PublicKey, ZapDetails, ZapEntity, ZapType} from "@rust-nostr/nostr-sdk";
import store from "@/store.js";
import {data} from "autoprefixer";


export default {

 data() {
    return {
      dvmlnaddress:  "hype@bitcoinfixesthis.org",
      dvmpaymentaddr:  "",
      dvminvoice: "",
      nostrsdklnaddress: "yuki@getalby.com",
      nostrsdkpaymentaddr: "",
      nostrsdkinvoice: "",
      amount: 1000
    }},

  methods: {
   async  handleZap(){
    try {
      let pk = PublicKey.fromBech32("npub1nxa4tywfz9nqp7z9zp7nr7d4nchhclsf58lcqt5y782rmf2hefjquaa6q8");
      let entity = ZapEntity.publicKey(pk);
      let details = new ZapDetails(ZapType.Private).message("Zap for Rust Nostr!");
      await store.state.client.zap(entity, 1000, details);
    } catch (error) {
        console.log(error)
    }
  },

    async copyinvoice(invoice){
       await navigator.clipboard.writeText(invoice)
        window.open("lightning:" + invoice,"_blank")
       miniToastr.showMessage("", "Copied Invoice to clipboard", VueNotifications.types.info)
    },

    async zap(lnaddress, amount) {
      let webln;
      let invoice = await this.createBolt11Lud16(lnaddress, amount)
      if (lnaddress === this.nostrsdklnaddress){
         this.nostrsdkpaymentaddr = `https://chart.googleapis.com/chart?cht=qr&chl=${invoice}&chs=250x250&chld=M|0`;
         this.nostrsdkinvoice = invoice
      }
      else{
        this.dvmpaymentaddr =  `https://chart.googleapis.com/chart?cht=qr&chl=${invoice}&chs=250x250&chld=M|0`;
        this.dvminvoice = invoice
      }

      try {
        webln = await requestProvider();
      } catch (err) {
          await this.copyinvoice(invoice)
      }

      if (webln) {
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
        }
    catch (e) {
            console.log(`LUD16: ${e}`);
            return null;
      }
    }
  }
}

</script>

<template>
  <div className="dropdown dropdown-top">
    <div tabIndex={0} role="button"  class="v-Button"><svg class="relative  w-5 h-5 mr-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>Donate</div>
      <div tabIndex={0} className="dropdown-content z-[1] -start-20 card card-compact w-64 p-2 shadow bg-primary text-primary-content">
        <div className="card-body">
          <div>
            <p>Sats:</p><input  class="c-Input" v-model="amount" placeholder="1000">
          </div>

          <h3 className="card-title">Donate to Noogle</h3>
            <button class="v-Button2" @click="zap(this.dvmlnaddress, amount)"><svg class="relative w-5 h-5 mr-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>Donate</button>
            <img v-if="this.dvmpaymentaddr" alt="Invoice" width="250"  :src=this.dvmpaymentaddr @click="this.copyinvoice(this.dvminvoice)" />

          <h3 className="card-title">Donate to NostrSDK</h3>
            <button class="v-Button2" @click="zap(this.nostrsdklnaddress, amount)"><svg class="relative w-5 h-5 mr-2 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>Donate</button>
            <img v-if="this.nostrsdkpaymentaddr" alt="Invoice" width="250"  :src=this.nostrsdkpaymentaddr @click="this.copyinvoice(this.nostrsdkinvoice)" />
        </div>
    </div>
  </div>
</template>

<style scoped>

.v-Button {
 @apply  tracking-wide bg-black hover:bg-amber-400 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
   height: 24px;
}
.v-Button2 {
 @apply  tracking-wide bg-black hover:bg-amber-400 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
}

.c-Input {
    @apply bg-black hover:bg-gray-900 focus:ring-white mb-2 inline-flex flex-none items-center rounded-lg border border-transparent px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;
    color: white;
    background: black;
}

</style>