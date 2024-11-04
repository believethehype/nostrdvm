<template>
  <div class="max-w-5xl mx-auto flex flex-col gap-8">
    <div class="flex flex-row gap-6 items-center">
      <Logo/>
      <div class="flex flex-col gap-2">
        <h1 class="text-7xl font-black tracking-wide">About</h1>
        <!-- <div class="text-lg text-nostr">
             There are many things that make using and working with DVMs a bit of a magical experience.
         </div> -->
      </div>
    </div>
    <br><br>
    <!-- <div class="grid grid-cols-2 gap-6">
        <div class="card card-compact rounded-box bg-black">
            <div class="card-body !text-base">
                <div class="card-title text-base-100-content font-bold">
                    Global improvements
                </div>

                <p>Once a Nostr app supports DVMs that means that they get immediate access to all features,
                    algorithms, and crazy inventions all DVMs support.</p>

                <p>
                    Don't like your client's default <em>Trending</em> algorithm? Pick from hundreds of different
    algorithms. Your Highlighter client doesn't work well when trying to read an obscure PDF?
    Use a DVM that has better support for it.
                </p>

                <p>
                    You say the spam filtering in your client is too aggressive? or not aggressive enough? Just choose
    from a different spam-filtering DVM!
                </p>
            </div>
        </div>

        <div class="card card-compact rounded-box bg-black">
            <div class="card-body !text-base">
                <div class="card-title text-base-100-content font-bold">
                    Long-tail
                </div>

                <p>Because discoverability of these algorithms is solved by the very use of Nostr, we can easily imagine
                    a future where there are thousands of very specific, very niche and abundantly weird DVMs providing all
                    kinds of obscure functionalities.</p>

                <p>
                    Even if a DVM only had a handful of users, it would still be worth it for its users and for the DVM.
                </p>
            </div>
        </div>

        <div class="card card-compact rounded-box bg-black">
            <div class="card-body !text-base">
                <div class="card-title text-base-100-content font-bold">
                    Reusable results
                </div>

                <p>
                    Every time a Nostr client autotranslates a note, it pings a specific API endpoint to get the
                    result translated.
                </p>

                <p>
                    Over, and over. The same text being translated by each user.
                </p>

                <p>
                    Since Data Vending Machine results are public by default, once a note has been translated,
                    all clients can choose to reuse the same translation.
                </p>
            </div>
        </div>
    </div>-->
  </div>


  <div className="chat chat-start">
    <div className="chat-image avatar">
      <div className="w-10 rounded-full">
        <img alt="Tailwind CSS chat bubble component"
             src="https://daisyui.com/images/stock/photo-1534528741775-53994a69daeb.jpg"/>
      </div>
    </div>
    <div className="chat-bubble">NIP 90 Data Vending Machines can perform multiple tasks leveraging the Nostr
      Protocol.
    </div>
  </div>
  <div className="chat chat-start">
    <div className="chat-image avatar">
      <div className="w-10 rounded-full">
        <img alt="Tailwind CSS chat bubble component"
             src="https://daisyui.com/images/stock/photo-1534528741775-53994a69daeb.jpg"/>
      </div>
    </div>
    <div className="chat-bubble">This Demo Application uses a Kind 5302 event to ask DVMs to search for content on the
      Nostr.
    </div>
  </div>

  <div className="chat chat-start">
    <div className="chat-image avatar">
      <div className="w-10 rounded-full">
        <img alt="Tailwind CSS chat bubble component"
             src="https://daisyui.com/images/stock/photo-1534528741775-53994a69daeb.jpg"/>
      </div>
    </div>
    <div className="chat-bubble">You can add from:npub.... to your search to filter content for a specific user.</div>
  </div>
  <div className="chat chat-start">
    <div className="chat-image avatar">
      <div className="w-10 rounded-full">
        <img alt="Tailwind CSS chat bubble component"
             src="https://daisyui.com/images/stock/photo-1534528741775-53994a69daeb.jpg"/>
      </div>
    </div>
    <div className="chat-bubble">When you're logged in (via getalby or nos2x extension) you can add from:me to search
      content from yourself
    </div>
  </div>
  <div className="chat chat-start">
    <div className="chat-image avatar">
      <div className="w-10 rounded-full">
        <img alt="Tailwind CSS chat bubble component"
             src="https://daisyui.com/images/stock/photo-1534528741775-53994a69daeb.jpg"/>
      </div>
    </div>
    <div className="chat-bubble">This page then combines all the results from available search dvms.</div>
  </div>
  <div className="chat chat-start">
    <div className="chat-image avatar">
      <div className="w-10 rounded-full">
        <img alt="Tailwind CSS chat bubble component"
             src="https://daisyui.com/images/stock/photo-1534528741775-53994a69daeb.jpg"/>
      </div>
    </div>
    <div className="chat-bubble">This way we will be able to decentralize the most centralized thing on the internet.
      Search.
    </div>
  </div>
</template>
<script>
export default {
  name: 'dailyUIdemo',

}


</script>
<style scoped>
h3 {
  margin: 40px 0 0;
}

ul {
  list-style-type: none;
  padding: 0;
}

li {
  display: inline-block;
  margin: 0 10px;
}

a {
  color: #42b983;
}
</style>