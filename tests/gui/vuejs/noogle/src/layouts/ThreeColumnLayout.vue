<script setup>
import Nip07 from "@/components/Nip07.vue";

</script>

<template>





  <div className="navbar bg-base-100">
  <div className="flex-none">
   <!-- <button className="btn btn-square btn-ghost">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="inline-block w-5 h-5 stroke-current"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
    test</button>-->
  </div>
  <div className="flex-1">
    <router-link  class="menu" to="/">Noogle</router-link>
    <router-link class="menu" to="/about">About</router-link>
     <router-link class="menu" to="/nip89">DVMs</router-link>

  <div className="flex-none">


      </div>

  </div>
 <Nip07/>

</div>

  <div class="three-column-layout">
    <header>

     <!-- <AppLogo />-->

    </header>

    <main>



      <router-view />
      <slot />
    </main>

    <aside>
      <slot name="aside" />
      <!-- <AppFooter /> -->
    </aside>
  </div>
</template>

<style scoped lang="scss">
.three-column-layout {
  display: grid;
  grid-template-areas:
    "header"
    "main"
    "aside";

  header {
    grid-area: header;
    margin-top: 30px;
  }
  main {
    grid-area: main;
    margin-top: 10px;
    padding: 20px;

  }
  aside {
    grid-area: aside;
    margin-top: 10px;
    padding: 20px;
  }

.router-link-exact-active{
  color: rgba(255, 255, 255, 0.87);
}


.v-Button {
  @apply bg-black hover:bg-nostr focus:ring-nostr mb-2 inline-flex flex-none items-center rounded-lg border border-nostr px-3 py-1.5 text-sm leading-4 text-white transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;

  height: 44px;
}




  @media (min-width: 768px) {
    grid-template-columns: 1fr 3fr 1fr;
    grid-template-areas: "header main aside";
  }
}
</style>