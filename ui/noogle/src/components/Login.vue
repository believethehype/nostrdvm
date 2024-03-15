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
      <div tabIndex={0} className="dropdown-content -start-56 z-[1] horizontal card card-compact w-64 p-2 shadow bg-nostr text-primary-content">
        <div className="card-body">
          <h3 className="card-title">Your account</h3>
          <!--<p>Sign out</p> -->
          <button className="btn" onclick="nwcmodal.showModal()" >Nostr Wallet Connect</button>
           <dialog id="nwcmodal" class="modal">
      <div class="modal-box rounded-3xl inner shadow-lg p-6 flex flex-col items-center transition-all duration-1000 bg-base-600/60  ">
        <h3 class="font-bold text-lg">Connect with Nostr Wallet Connect</h3>
        <br>
          <div class="flex">
              <img class="avatar"  src="/favicon.ico" alt="" />
            <h3 class="text-lg">Noogle</h3>
          </div>
        <p class="py-4">Enter a Nostr Wallet connect string for easier zapping on the page</p>
        <div class="collapse bg-base-200">
  <input type="radio" name="my-accordion-1" />
  <div class="collapse-title text-xl font-medium bg-black/30 flex">
      <img  class="w-12 h-12 mask mask-squircle bg-zinc-700" style="width: 46px; height: 46px" src="/Alby.jpg"/>
     <div style="margin-left: 30px">
           <h3>Alby NWC</h3>
           <h3 class="text-sm text-neutral">Connect with your Alby Wallet</h3>
         </div>

  </div>
          <div class="collapse-content">
            <button style="margin-top: 20px;" @click="connect_alby_nwc()">
            <svg width="211" height="40" viewBox="0 0 211 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="0.5" width="210" height="40" rx="6" fill="url(#paint0_linear_1_148)"/>
            <circle cx="1.575" cy="1.575" r="1.575" transform="matrix(-1 0 0 1 22.1176 13.8575)" fill="black"/>
            <path d="M20.28 15.1963L23.22 18.1363" stroke="black" stroke-width="0.7875"/>
            <circle cx="33.405" cy="15.4325" r="1.575" fill="black"/>
            <path d="M33.6938 15.1963L30.7538 18.1363" stroke="black" stroke-width="0.7875"/>
            <path fill-rule="evenodd" clip-rule="evenodd" d="M20.9896 24.831C20.1407 24.4269 19.6467 23.5194 19.8122 22.5939C20.5225 18.6217 23.4825 15.6425 27.0263 15.6425C30.5786 15.6425 33.5444 18.6362 34.2455 22.6228C34.4085 23.5499 33.9105 24.457 33.0587 24.8578C31.2361 25.7155 29.2003 26.195 27.0525 26.195C24.8824 26.195 22.8267 25.7055 20.9896 24.831Z" fill="#FFDF6F"/>
            <path d="M34.2455 22.6228L33.8577 22.691L34.2455 22.6228ZM33.0587 24.8578L32.8911 24.5016L33.0587 24.8578ZM20.9896 24.831L21.1588 24.4754L20.9896 24.831ZM20.1998 22.6632C20.8861 18.825 23.7231 16.0362 27.0263 16.0362V15.2487C23.242 15.2487 20.1588 18.4184 19.4246 22.5246L20.1998 22.6632ZM27.0263 16.0362C30.3374 16.0362 33.1802 18.8386 33.8577 22.691L34.6333 22.5546C33.9086 18.4337 30.8198 15.2487 27.0263 15.2487V16.0362ZM32.8911 24.5016C31.1198 25.3351 29.1411 25.8012 27.0525 25.8012V26.5887C29.2595 26.5887 31.3524 26.096 33.2264 25.2141L32.8911 24.5016ZM27.0525 25.8012C24.9422 25.8012 22.9442 25.3254 21.1588 24.4754L20.8203 25.1865C22.7092 26.0857 24.8226 26.5887 27.0525 26.5887V25.8012ZM33.8577 22.691C33.9884 23.4343 33.5904 24.1725 32.8911 24.5016L33.2264 25.2141C34.2306 24.7415 34.8287 23.6655 34.6333 22.5546L33.8577 22.691ZM19.4246 22.5246C19.2263 23.6336 19.8196 24.7101 20.8203 25.1865L21.1588 24.4754C20.4618 24.1436 20.0671 23.4052 20.1998 22.6632L19.4246 22.5246Z" fill="black"/>
            <path fill-rule="evenodd" clip-rule="evenodd" d="M22.5042 23.8434C21.8209 23.5652 21.4155 22.8381 21.6523 22.1394C22.3825 19.9844 24.5124 18.425 27.0263 18.425C29.5401 18.425 31.67 19.9844 32.4002 22.1394C32.637 22.8381 32.2317 23.5652 31.5484 23.8434C30.1528 24.4118 28.6261 24.725 27.0263 24.725C25.4264 24.725 23.8997 24.4118 22.5042 23.8434Z" fill="black"/>
            <ellipse cx="28.8375" cy="21.785" rx="1.3125" ry="1.05" fill="white"/>
            <ellipse cx="25.0802" cy="21.7856" rx="1.3125" ry="1.05" fill="white"/>
            <path d="M55.5064 18.1477C55.1712 18.1477 54.9893 17.983 54.87 17.6648C54.4325 16.4659 53.3018 15.8068 51.9893 15.8068C49.9837 15.8068 48.4837 17.358 48.4837 20.1818C48.4837 23.0284 49.9893 24.5568 51.9837 24.5568C53.2905 24.5568 54.4155 23.9148 54.87 22.733C54.9893 22.4091 55.1712 22.25 55.5064 22.25H56.1371C56.5348 22.25 56.7507 22.4943 56.6314 22.8807C56.0405 24.8409 54.2905 26.1591 51.9723 26.1591C48.9496 26.1591 46.7393 23.9034 46.7393 20.1818C46.7393 16.4602 48.9609 14.2045 51.9723 14.2045C54.2166 14.2045 56.0348 15.4148 56.6371 17.517C56.7507 17.9091 56.5348 18.1477 56.1371 18.1477H55.5064ZM62.4197 26.1761C59.9595 26.1761 58.3516 24.375 58.3516 21.6761C58.3516 18.9602 59.9595 17.1591 62.4197 17.1591C64.88 17.1591 66.4879 18.9602 66.4879 21.6761C66.4879 24.375 64.88 26.1761 62.4197 26.1761ZM60.0675 21.6705C60.0675 23.3466 60.8175 24.75 62.4254 24.75C64.022 24.75 64.772 23.3466 64.772 21.6705C64.772 20 64.022 18.5795 62.4254 18.5795C60.8175 18.5795 60.0675 20 60.0675 21.6705ZM70.0831 25.4318C70.0831 25.8011 69.8842 26 69.5149 26H68.9524C68.5831 26 68.3842 25.8011 68.3842 25.4318V17.8409C68.3842 17.4716 68.5831 17.2727 68.9524 17.2727H69.4467C69.8161 17.2727 70.0149 17.4716 70.0149 17.8409V18.6932H70.1229C70.5263 17.767 71.3842 17.1591 72.6967 17.1591C74.4808 17.1591 75.6683 18.2898 75.6683 20.4489V25.4318C75.6683 25.8011 75.4695 26 75.1001 26H74.5376C74.1683 26 73.9695 25.8011 73.9695 25.4318V20.6534C73.9695 19.3864 73.2706 18.6307 72.1172 18.6307C70.9354 18.6307 70.0831 19.4261 70.0831 20.8182V25.4318ZM79.6456 25.4318C79.6456 25.8011 79.4467 26 79.0774 26H78.5149C78.1456 26 77.9467 25.8011 77.9467 25.4318V17.8409C77.9467 17.4716 78.1456 17.2727 78.5149 17.2727H79.0092C79.3786 17.2727 79.5774 17.4716 79.5774 17.8409V18.6932H79.6854C80.0888 17.767 80.9467 17.1591 82.2592 17.1591C84.0433 17.1591 85.2308 18.2898 85.2308 20.4489V25.4318C85.2308 25.8011 85.032 26 84.6626 26H84.1001C83.7308 26 83.532 25.8011 83.532 25.4318V20.6534C83.532 19.3864 82.8331 18.6307 81.6797 18.6307C80.4979 18.6307 79.6456 19.4261 79.6456 20.8182V25.4318ZM91.2706 26.1761C88.6967 26.1761 87.1172 24.4034 87.1172 21.6932C87.1172 19.0114 88.7195 17.1591 91.1513 17.1591C93.1286 17.1591 95.0149 18.392 95.0149 21.5455V21.5795C95.0149 21.9489 94.8161 22.1477 94.4467 22.1477H88.8104C88.8558 23.8295 89.8331 24.7727 91.2876 24.7727C92.0661 24.7727 92.6967 24.5 93.0717 23.9659C93.2649 23.6818 93.4581 23.5511 93.7876 23.6136L94.2876 23.7045C94.674 23.7784 94.8672 24 94.7365 24.2898C94.2024 25.4432 92.9524 26.1761 91.2706 26.1761ZM88.8161 20.875H93.3501C93.3445 19.5398 92.4808 18.5625 91.1626 18.5625C89.782 18.5625 88.8842 19.6364 88.8161 20.875ZM100.576 26.1761C98.0419 26.1761 96.5078 24.3068 96.5078 21.6761C96.5078 19.0114 98.0987 17.1591 100.559 17.1591C102.298 17.1591 103.621 18.0625 104.042 19.4716C104.15 19.8523 103.923 20.0909 103.531 20.0909H102.996C102.667 20.0909 102.491 19.9375 102.349 19.6307C102.053 19.0341 101.457 18.5909 100.587 18.5909C99.1669 18.5909 98.2237 19.767 98.2237 21.6364C98.2237 23.5398 99.1499 24.7386 100.587 24.7386C101.388 24.7386 102.025 24.3636 102.349 23.6989C102.491 23.3977 102.667 23.2386 102.996 23.2386H103.531C103.923 23.2386 104.15 23.4375 104.059 23.767C103.678 25.1875 102.417 26.1761 100.576 26.1761ZM110.052 18.0682C110.052 18.4375 109.853 18.6364 109.484 18.6364H108.262V23.4375C108.262 24.4205 108.756 24.6023 109.308 24.6023H109.364C109.722 24.5909 109.944 24.7102 110.018 25.0625L110.092 25.3864C110.171 25.7386 110.035 26.0114 109.671 26.0682C109.512 26.0909 109.325 26.1136 109.109 26.1136C107.768 26.142 106.558 25.375 106.563 23.7898V18.6364H105.853C105.484 18.6364 105.285 18.4375 105.285 18.0682V17.8409C105.285 17.4716 105.484 17.2727 105.853 17.2727H106.563V15.75C106.563 15.3807 106.762 15.1818 107.131 15.1818H107.694C108.063 15.1818 108.262 15.3807 108.262 15.75V17.2727H109.484C109.853 17.2727 110.052 17.4716 110.052 17.8409V18.0682ZM115.677 17.9148C115.563 17.5227 115.745 17.2727 116.154 17.2727H116.745C117.08 17.2727 117.29 17.4318 117.376 17.7557L118.955 23.6818H119.04L120.626 17.7557C120.711 17.4261 120.921 17.2727 121.256 17.2727H122.012C122.347 17.2727 122.558 17.4318 122.643 17.7557L124.217 23.6534H124.302L125.87 17.7557C125.955 17.4318 126.165 17.2727 126.501 17.2727H127.092C127.501 17.2727 127.683 17.517 127.569 17.9148L125.336 25.5227C125.239 25.8409 125.035 26 124.7 26H123.961C123.626 26 123.415 25.8466 123.325 25.517L121.688 19.6989H121.558L119.921 25.517C119.83 25.8466 119.62 26 119.285 26H118.552C118.217 26 118.012 25.8409 117.915 25.5227L115.677 17.9148ZM130.227 15.9261C129.636 15.9261 129.153 15.4716 129.153 14.9148C129.153 14.358 129.636 13.8977 130.227 13.8977C130.812 13.8977 131.3 14.358 131.3 14.9148C131.3 15.4716 130.812 15.9261 130.227 15.9261ZM129.369 25.4318V17.8409C129.369 17.4716 129.567 17.2727 129.937 17.2727H130.499C130.869 17.2727 131.067 17.4716 131.067 17.8409V25.4318C131.067 25.8011 130.869 26 130.499 26H129.937C129.567 26 129.369 25.8011 129.369 25.4318ZM137.427 18.0682C137.427 18.4375 137.228 18.6364 136.859 18.6364H135.637V23.4375C135.637 24.4205 136.131 24.6023 136.683 24.6023H136.739C137.097 24.5909 137.319 24.7102 137.393 25.0625L137.467 25.3864C137.546 25.7386 137.41 26.0114 137.046 26.0682C136.887 26.0909 136.7 26.1136 136.484 26.1136C135.143 26.142 133.933 25.375 133.938 23.7898V18.6364H133.228C132.859 18.6364 132.66 18.4375 132.66 18.0682V17.8409C132.66 17.4716 132.859 17.2727 133.228 17.2727H133.938V15.75C133.938 15.3807 134.137 15.1818 134.506 15.1818H135.069C135.438 15.1818 135.637 15.3807 135.637 15.75V17.2727H136.859C137.228 17.2727 137.427 17.4716 137.427 17.8409V18.0682ZM141.192 25.4318C141.192 25.8011 140.994 26 140.624 26H140.062C139.692 26 139.494 25.8011 139.494 25.4318V14.9318C139.494 14.5625 139.692 14.3636 140.062 14.3636H140.602C140.971 14.3636 141.17 14.5625 141.17 14.9318V18.6932H141.278C141.687 17.75 142.505 17.1591 143.863 17.1591C145.658 17.1591 146.852 18.2727 146.852 20.4489V25.4318C146.852 25.8011 146.653 26 146.283 26H145.721C145.352 26 145.153 25.8011 145.153 25.4318V20.6534C145.153 19.375 144.454 18.6307 143.283 18.6307C142.073 18.6307 141.192 19.4261 141.192 20.8182V25.4318ZM153.302 26C152.881 26 152.7 25.7386 152.842 25.3466L156.631 14.8182C156.745 14.5114 156.95 14.3636 157.279 14.3636H158.342C158.671 14.3636 158.876 14.5114 158.989 14.8182L162.779 25.3466C162.921 25.7386 162.739 26 162.319 26H161.637C161.308 26 161.097 25.858 160.989 25.5398L160.086 22.9205H155.54L154.631 25.5398C154.523 25.8523 154.313 26 153.984 26H153.302ZM156.052 21.4432H159.575L157.859 16.4773H157.768L156.052 21.4432ZM166.255 25.4318C166.255 25.8011 166.056 26 165.687 26H165.124C164.755 26 164.556 25.8011 164.556 25.4318V14.9318C164.556 14.5625 164.755 14.3636 165.124 14.3636H165.687C166.056 14.3636 166.255 14.5625 166.255 14.9318V25.4318ZM168.677 14.9318C168.677 14.5625 168.876 14.3636 169.245 14.3636H169.808C170.177 14.3636 170.376 14.5625 170.376 14.9318V18.6875H170.478C170.779 18.1477 171.364 17.1591 172.984 17.1591C175.092 17.1591 176.648 18.8239 176.648 21.6534C176.648 24.4773 175.114 26.1705 173.001 26.1705C171.41 26.1705 170.785 25.1989 170.478 24.642H170.336V25.4318C170.336 25.8011 170.137 26 169.768 26H169.245C168.876 26 168.677 25.8011 168.677 25.4318V14.9318ZM170.342 21.6364C170.342 23.4716 171.16 24.7216 172.62 24.7216C174.137 24.7216 174.933 23.3864 174.933 21.6364C174.933 19.9034 174.16 18.6023 172.62 18.6023C171.137 18.6023 170.342 19.8125 170.342 21.6364ZM179.317 29.2727C179.096 29.2727 178.891 29.2557 178.71 29.2273C178.346 29.1705 178.215 28.892 178.317 28.5341L178.414 28.2102C178.516 27.8636 178.744 27.7614 179.102 27.8011C179.744 27.8636 180.198 27.6136 180.539 26.6932L180.749 26.1136L177.789 17.9261C177.647 17.5341 177.829 17.2727 178.249 17.2727H178.886C179.215 17.2727 179.425 17.4261 179.528 17.7386L181.585 24.0455H181.675L183.732 17.7386C183.835 17.4261 184.045 17.2727 184.374 17.2727H185.016C185.437 17.2727 185.613 17.5341 185.471 17.9261L182.113 27.1648C181.607 28.5398 180.721 29.2727 179.317 29.2727Z" fill="black"/>
            <defs>
            <linearGradient id="paint0_linear_1_148" x1="105.5" y1="0" x2="105.5" y2="38.0952" gradientUnits="userSpaceOnUse">
            <stop offset="0.669102" stop-color="#FFDE6E"/>
            <stop offset="1" stop-color="#F8C455"/>
            </linearGradient>
            </defs>
            </svg>

            </button>
            </div>

</div>
<div class="collapse bg-base-200">
  <input type="radio" name="my-accordion-1" />
  <div class="collapse-title text-xl font-medium bg-black/30  flex">
         <img class="w-12 h-12 mask mask-squircle bg-zinc-700" style="width: 46px; height: 46px" src="/Mutiny.png"/>
    <div style="margin-left: 30px">
            <h3> Mutiny Wallet</h3>
           <h3 class="text-sm text-neutral">Connect with your Mutiny Wallet</h3>
         </div>


  </div>

  <div class="collapse-content">
     <p>Add a new Wallet Connection from:</p>
    <ul class="steps steps-vertical">
  <li class="step">Settings</li>
  <li class="step">Wallet Connections</li>
  <li class="step">Add Connection</li><li class="step">copy the connection string.</li>
</ul>
  <textarea class="nwc-Input" style="width: 400px; margin-left: 10px; margin-top: 10px" name="Text1" type="password"   placeholder="nostr+walletconnect://..." cols="40" rows="5"  v-model="this.nwcmutiny"></textarea>
  </div>
</div>
<div class="collapse bg-base-200">
  <input type="radio" name="my-accordion-1" />
  <div class="collapse-title text-xl font-medium transparent bg-black/30 flex">
    <svg width="56" height="56" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-12 h-12 mask mask-squircle"><g clip-path="url(#clip0_1138_8450)"><rect width="56" height="56" rx="16" fill="black"></rect><rect width="56" height="56" fill="url(#paint0_radial_1138_8450)"></rect><rect width="56" height="56" fill="black" fill-opacity="0.9"></rect><path d="M42.7656 23.2125C42.7656 33.8416 32.4114 42.9297 28 42.9297C23.5886 42.9297 13.2344 33.8416 13.2344 23.2125C13.2344 15.0741 19.8452 8.47656 28 8.47656C36.1548 8.47656 42.7656 15.0741 42.7656 23.2125Z" fill="url(#paint1_radial_1138_8450)"></path><path d="M25.5108 47.4784L27.7337 46.747C27.9067 46.6901 28.0933 46.6901 28.2663 46.747L30.4892 47.4784C31.2399 47.7255 31.8928 46.9058 31.4827 46.231L28.7272 41.6978C28.396 41.1528 27.604 41.1528 27.2728 41.6978L24.5173 46.231C24.1072 46.9058 24.7601 47.7255 25.5108 47.4784Z" fill="url(#paint2_radial_1138_8450)"></path><circle cx="28" cy="23.2422" r="5.79688" fill="black" fill-opacity="0.66"></circle></g><defs><radialGradient id="paint0_radial_1138_8450" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(56 56) rotate(-135) scale(79.196 118.441)"><stop stop-color="#6951FA"></stop><stop offset="1" stop-color="#9151FA"></stop></radialGradient><radialGradient id="paint1_radial_1138_8450" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(42.7656 47.5234) rotate(-127.1) scale(48.9566 70.4506)"><stop stop-color="#6951FA"></stop><stop offset="1" stop-color="#9151FA"></stop></radialGradient><radialGradient id="paint2_radial_1138_8450" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(42.7656 47.5234) rotate(-127.1) scale(48.9566 70.4506)"><stop stop-color="#6951FA"></stop><stop offset="1" stop-color="#9151FA"></stop></radialGradient><clipPath id="clip0_1138_8450"><rect width="56" height="56" rx="16" fill="white"></rect></clipPath></defs></svg>
         <div style="margin-left: 30px">
           <h3>Nostr Wallet Connect</h3>
           <h3 class="text-sm text-neutral">Manually connect with NWC string</h3>
         </div>


  </div>
  <div class="collapse-content">
  <textarea class="nwc-Input" style="width: 400px; margin-left: 10px; margin-top: 10px" name="Text1" type="password"  placeholder="nostr+walletconnect://..." cols="40" rows="5"  v-model="this.nwc"></textarea>

  </div>
</div>


        <div class="modal-action">
          <form method="dialog">
            <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
            <!-- if there is a button in form, it will close the modal -->
            <button class="btn" @click="store_nwc()">Save</button>
          </form>
        </div>
      </div>
</dialog>

          <button className="btn" @click="sign_out()">Sign Out</button>
        </div>
      </div>
    </div>
        <!--<p>{{ this.current_user }}</p> -->
     </div>

    <template v-if="!current_user">
      <div className="dropdown">
      <div tabIndex={0} role="button" class="v-Button" >Sign in</div>
      <div tabIndex={0} className="dropdown-content -start-56 z-[1] horizontal card card-compact w-64 p-2 shadow bg-nostr text-primary-content">
        <div className="card-body">
          <h3 className="card-title">Login</h3>
          <p>Use a Browser Nip07 Extension like getalby, nos2x or nsec.app, a nsec or ncryptsec or use Amber on Android to sign-in</p>
         <button className="btn" @click="sign_in_nip07()">Browser Extension</button>
          <button className="btn" @click="sign_in_nostr_login()">Nostr Login</button>

         <template v-if="supports_android_signer">
          <button className="btn" @click="sign_in_amber()">Amber Sign in</button>
        </template>
           <button className="btn" onclick="nsecmodal.showModal()">NSec/NCryptSec</button>
      <dialog id="nsecmodal" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Login with key</h3>
        <p class="py-4">Login with nsec or ncryptsec. Your keys will be stored in your Browser. This is the least recommended sign-in method</p>
        <input class="u-Input" style="margin-left: 10px" type="search" name="user" autofocus  placeholder="nsec.../ncryptsec..." v-model="this.ncryptsec">
        <input v-if="ncryptsec.startsWith('ncryptsec')" class="u-Input" style="margin-left: 10px" type="password" name="user" autofocus  placeholder="password..." v-model="this.pw">

        <div class="modal-action">
          <form method="dialog">
            <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
            <!-- if there is a button in form, it will close the modal -->
            <button class="btn" @click="sign_in_key()">Login</button>
          </form>
        </div>
      </div>
</dialog>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script>
import {
  loadWasmAsync,
  Client,
  Nip07Signer,
  Filter,
  initLogger,
  LogLevel,
  Timestamp,
  Keys,
  NostrDatabase,
  ClientBuilder,
  ClientZapper,
  Alphabet,
  SingleLetterTag,
  Options,
  Duration,
  PublicKey,
  Nip46Signer, NegentropyDirection, NegentropyOptions, NostrSigner
} from "@rust-nostr/nostr-sdk";
import VueNotifications from "vue-notifications";
import store from '../store';
import miniToastr from "mini-toastr";
import deadnip89s from "@/components/data/deadnip89s.json";
import amberSignerService from "./android-signer/AndroidSigner";
import nip49, {decryptwrapper} from "./android-signer/helpers/nip49";
import { init as initNostrLogin  } from "nostr-login"
import { launch as launchNostrLoginDialog } from "nostr-login"
import { logout as logoutNostrLogin } from "nostr-login"
import {parseandreplacenpubs, hasActiveSubscription} from "@/components/helper/Helper.vue"
import {loadNWCObject} from "@/components/helper/Zap.vue"
import {useDark, useToggle} from "@vueuse/core";
import {ref} from "vue";
import {webln} from "@getalby/sdk";
const isDark = useDark();

//const toggleDark = useToggle(isDark);



let nip89dvms = []
const nsec =  ref("");

let logger = false




export default {

  data() {
    return {
      current_user: "",
      avatar: "",
      signer: "",
      supports_android_signer: false,
      ncryptsec: ref(""),
      nwc: ref(""),
      nwcmutiny: ref(""),
      nwcalby: ref(""),
      nwcconnector: ref("user"),

      pw: ref("")


    };
  },

  async mounted() {
    try {



      if (amberSignerService.supported) {
        this.supports_android_signer = true;
      }



      if (localStorage.getItem('nostr-key-method') === 'nip07') {
        await this.sign_in_nip07()
      }
      else if (localStorage.getItem('nostr-key-method') === 'nsec') {
        await this.sign_in_key(localStorage.getItem('localNostrPrivkey'))
      }
      else if (localStorage.getItem('nostr-key-method') === 'nostr-login'){
        console.log(localStorage.getItem('__nostrlogin_nip46'))
        await this.sign_in_nostr_login()
      }

      else if (localStorage.getItem('nostr-key-method') === 'android-signer') {
        let key = ""
        if (localStorage.getItem('nostr-key') !== "") {
          key = localStorage.getItem('nostr-key')
        }
        await this.sign_in_amber(key)
      }


      else {
        await this.sign_in_anon()
      }
    await this.getnip89s()
      let nwc = loadNWCObject()


       if(nwc.connectorType === "alby"){
        this.nwcalby = nwc.nwcUrl
      }
      else if(nwc.connectorType === "user"){
        this.nwc = nwc.nwcUrl
      }
      else if (nwc.connectorType === "mutiny"){
        this.nwcmutiny = nwc.nwcUrl
      }



    } catch (error) {
      console.log(error);
    }
  },

  methods: {

    toggleDark() {
      isDark.value = !isDark.value
      useToggle(isDark);
      console.log(isDark.value)
      if (localStorage.isDark === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    },

    async sign_in_nostr_login() {
      await initNostrLogin({/*options*/})

      // launch signup screen
      if (!localStorage.getItem('__nostrlogin_nip46')){
           await launchNostrLoginDialog({
        /*startScreen: 'signup'*/
      })
      }

      await loadWasmAsync();
      let nip07_signer = new Nip07Signer();
      try {
        this.signer = NostrSigner.nip07(nip07_signer);
        console.log("SIGNER: " + this.signer.toString())




      let opts = new Options().waitForSend(false).connectionTimeout(Duration.fromSecs(5));
      let client = new ClientBuilder().signer(this.signer).opts(opts).build()


      for (const relay of store.state.relays) {
        await client.addRelay(relay);
      }

      const pubkey = await nip07_signer.getPublicKey();
      console.log(pubkey.toBech32())
      await client.connect();


        store.commit('set_client', client)
        store.commit('set_signer', this.signer)
      store.commit('set_pubkey', pubkey)
      store.commit('set_hasEventListener', false)
      localStorage.setItem('nostr-key-method', "nostr-login")
      localStorage.setItem('nostr-key', pubkey.toHex())
      console.log("Client Nip46 connected")
      await this.get_user_info(pubkey)
        this.reconcile_all_profiles(pubkey)
      console.log(pubkey.toBech32())
      //await this.reconcile_all_profiles()



 } catch (error) {
        console.log(error);
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

        let keys = Keys.parse("ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e")
        this.signer = NostrSigner.keys(keys) //TODO store keys
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
        store.commit('set_signer', this.signer)
        store.commit('set_pubkey', pubkey)
        store.commit('set_hasEventListener', false)
        console.log("LOGINANON")
        localStorage.setItem('nostr-key-method', "anon")
        localStorage.setItem('nostr-key', "")
        console.log("Client Anon connected")


      } catch (error) {
        console.log(error);
      }
    },
    async sign_in_key(nsec = "") {
      try {
         await loadWasmAsync();
       if(logger){
            try {
                initLogger(LogLevel.debug());
            } catch (error) {
                console.log(error);
            }
        }
       let key = ""
       if (nsec !== ""){
         key = nsec
       }
       else{
           key = this.ncryptsec
        if(this.ncryptsec.startsWith("ncryptsec")){

          key = nip49.decryptwrapper(this.ncryptsec, this.pw)
        }
       }



        let keys = Keys.parse(key)
        this.signer = NostrSigner.keys(keys)
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
        store.commit('set_signer', this.signer)
        store.commit('set_pubkey', pubkey)
        store.commit('set_hasEventListener', false)
        console.log("LOGIN with Key")
        localStorage.setItem('nostr-key-method', "nsec")
        localStorage.setItem('nostr-key', keys.publicKey.toHex())
        localStorage.setItem('localNostrPrivkey', keys.secretKey.toHex())
        console.log("Client key connected")
        await this.get_user_info(pubkey)
        this.reconcile_all_profiles(pubkey)


      } catch (error) {
        console.log(error);
        miniToastr.showMessage(error)
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
              this.signer = NostrSigner.nip07(nip07_signer);
              console.log("SIGNER: " + this.signer)


            } catch (error) {
            console.log(error);
             this.signer = NostrSigner.keys(Keys.generate())
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
        store.commit('set_signer', this.signer)
        store.commit('set_pubkey', pubkey)
        store.commit('set_hasEventListener', false)
        localStorage.setItem('nostr-key-method', "nip07")
        localStorage.setItem('nostr-key', pubkey.toHex())



        console.log("Client Nip07 connected")
        await this.get_user_info(pubkey)

        this.reconcile_all_profiles(pubkey)
        //await this.reconcile_all_profiles()
        //miniToastr.showMessage("Login successful!", "Logged in as " + this.current_user, VueNotifications.types.success)

      } catch (error) {
        console.log(error);
      }
    },
    async sign_in_nip46() {

      try {

        await loadWasmAsync();



          let connectionstring = ""
          if (localStorage.getItem('nostr-key') !== "" && localStorage.getItem('nostr-key').startsWith("nsecbunker://") ){
            connectionstring = localStorage.getItem('nostr-key')
          }

        if (connectionstring === ""){
              //ADD DEFAULT TEST STRING FOR NOW, USE USER INPUT LATER
              connectionstring = "bunker://7f2d38c4f3cf2070935bad7cab046ad088dcef2de4b0b985f2174ea22a094778?relay=wss://relay.nsec.app"
        }

        if (connectionstring.startsWith("nsecbunker://")){
           connectionstring = connectionstring.replace("nsecbunker://", "")
           let split = connectionstring.split("?relay=")
           let relay_url = split[1]
           let split2 = split[0].split("#")
           let publickey = Keys.parse(split2[0]).publicKey
           let app_keys = Keys.fromPublicKey(PublicKey.parse(split2[1]))


        let nip46_signer = new Nip46Signer(relay_url, app_keys, publickey, Duration.fromSecs(10)) ;
            try{
              this.signer = NostrSigner.nip46(nip46_signer);
              console.log("SIGNER: " + this.signer)


            } catch (error) {
            console.log(error);
             this.signer = NostrSigner.keys(Keys.generate())
          }

        //let zapper = ClientZapper.webln()
        let opts = new Options().waitForSend(false).connectionTimeout(Duration.fromSecs(5));
        let client = new ClientBuilder().signer(this.signer).opts(opts).build()

        await client.addRelay(relay_url)
        for (const relay of store.state.relays){
                 await client.addRelay(relay);
              }

        const pubkey = await nip46_signer.signerPublicKey()
        console.log("PUBKEY : " + pubkey.toBech32())
        await client.connect();

        store.commit('set_client', client)
          store.commit('set_signer', this.signer)
        store.commit('set_pubkey', pubkey)
        store.commit('set_hasEventListener', false)
        localStorage.setItem('nostr-key-method', "nip46")
        localStorage.setItem('nostr-key', connectionstring)
        console.log("Client connected")




          this.reconcile_all_profiles(pubkey)
          await this.get_user_info(pubkey)

        //miniToastr.showMessage("Login successful!", "Logged in as " + this.current_user, VueNotifications.types.success)


     }
        else {
          miniToastr.showMessage("Invalid Nsecbunker url")
        }


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
        this.signer = NostrSigner.keys(keys)
        let opts = new Options().waitForSend(false).connectionTimeout(Duration.fromSecs(5));
        let client = new ClientBuilder().signer(this.signer).opts(opts).build()
        for (const relay of store.state.relays){
          await client.addRelay(relay);
        }
        await client.connect();
        store.commit('set_client', client)
          store.commit('set_signer', this.signer)
        store.commit('set_pubkey', publicKey)
        store.commit('set_hasEventListener', false)
        localStorage.setItem('nostr-key-method', "android-signer")
        localStorage.setItem('nostr-key', hexKey)


           this.reconcile_all_profiles(publicKey)
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
            let keys = Keys.parse("ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e")
            let signer = NostrSigner.keys(keys) //TODO store keys
            let client = new ClientBuilder().signer(signer).build()

            for (const relay of store.state.relays) {
              await client.addRelay(relay);
            }
            await client.connect();



        let dvmkinds = []
        for (let i = 5000; i < 6000; i++) {
          dvmkinds.push((i.toString()))
        }
        //console.log(dvmkinds)

        const filter = new Filter().kind(31990).customTag(SingleLetterTag.lowercase(Alphabet.K), dvmkinds)
        let evts = await client.getEventsOf([filter], Duration.fromSecs(5))

        let dvmkeys = []
        for (let evt of evts){
          for (const tag in evt.tags) {
            if (evt.tags[tag].asVec()[1] >= 5000 && evt.tags[tag].asVec()[1] <= 5999 && deadnip89s.filter(i => i.id === evt.id.toHex()).length === 0) {
              dvmkeys.push(evt.author)
            }
          }

        }

        const filtersubscription = new Filter().kind(37001).authors(dvmkeys)
        let subscription_tiers = await client.getEventsOf([filtersubscription], Duration.fromSecs(5))
        //console.log(subscription_tiers)

        for (const entry of evts){

          for (const tag in entry.tags){
            if (entry.tags[tag].asVec()[0] === "k")
              if(entry.tags[tag].asVec()[1] >= 5000 && entry.tags[tag].asVec()[1] <= 5999 &&  deadnip89s.filter(i => i.id === entry.id.toHex() ).length === 0) {   // blocklist.indexOf(entry.id.toHex()) < 0){



                try {

                    let jsonentry = JSON.parse(entry.content)


                    let susbcrition_tier = subscription_tiers.find(x => x.author.toHex() === entry.author.toHex())


                     let nip88    = {
                        title: "",
                        image: "",
                        amounts: [],
                        zaps: [],
                        perks: [],
                        description: "",
                        eventid: "",
                        event: "",
                        hasActiveSubscription:  false,
                        subscribedUntil:  0,
                        subscriptionId: "",
                          }

                      if (jsonentry.picture){
                        jsonentry.image = jsonentry.picture
                      }

                      if(!jsonentry.amount){
                        jsonentry.amount = ""
                      }
                      if(jsonentry.amount === "subscription"){
                     // if(susbcrition_tier) {
                        const filter = new Filter().kind(37001).author(entry.author)
                        let tiers = await client.getEventsOf([filter], Duration.fromSecs(5))

                        // todo handle multiple tiers
                        if (tiers.length > 0) {
                          let evt = tiers[0]
                          nip88.description = evt.content
                          nip88.eventid = evt.id.toHex()
                          nip88.event = evt.asJson()


                          for (let tag of evt.tags) {
                           if (tag.asVec()[0] === "amount"){
                             let amount = {
                               amount:  tag.asVec()[1],
                               unit: tag.asVec()[2],
                               cadence: tag.asVec()[3]
                             }
                            nip88.amounts.push(amount)

                            }
                            else if(tag.asVec()[0] === "title"){
                               nip88.title = tag.asVec()[1]
                            }
                             else if(tag.asVec()[0] === "image"){
                               nip88.image = tag.asVec()[1]
                            }
                             else if(tag.asVec()[0] === "perk") {
                              nip88.perks.push(tag.asVec()[1])
                            }

                             else if(tag.asVec()[0] === "zap_local"){
                                  let zap = {
                               key:  (tag.asVec()[1] !== "" ? tag.asVec()[1] : PublicKey.parse("npub1nxa4tywfz9nqp7z9zp7nr7d4nchhclsf58lcqt5y782rmf2hefjquaa6q8").toHex()) ,
                               relay: tag.asVec()[2],
                               split: tag.asVec()[3]
                             }

                             // TODO only use first tag for now, add others later.
                            // if(tag.asVec()[1] !== "" ){
                                 nip88.zaps.push(zap)
                            // }


                            }




                          }
                          let subscription_status = await hasActiveSubscription(localStorage.getItem("nostr-key"), evt.id.toHex(), evt.author.toHex(), nip88.amounts)
                          nip88.hasActiveSubscription  = subscription_status.isActive
                          nip88.subscribedUntil = subscription_status.validuntil
                          nip88.subscriptionId = subscription_status.subscriptionId


                          jsonentry.nip88 = nip88
                           console.log(jsonentry.nip88)

                        }
                      }

                      jsonentry.id = entry.author.toHex()
                      jsonentry.about = await parseandreplacenpubs(jsonentry.about)
                      jsonentry.event = entry.asJson()
                      jsonentry.kind = entry.tags[tag].asVec()[1]


                      //jsonentry.nip90Params = JSON.parse(jsonentry.nip90Params)
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
    async reconcile_all_profiles(publicKey) {
    {
      let dbclient = Client
      let keys = Keys.parse("ece3c0aa759c3e895ecb3c13ab3813c0f98430c6d4bd22160b9c2219efc9cf0e")
      let db = NostrDatabase.indexeddb("profiles");
      let signer = NostrSigner.keys(keys) //TODO store keys
      dbclient = new ClientBuilder().signer(signer).database(await db).build()

      await dbclient.addRelay("wss://relay.damus.io");
      await dbclient.connect()
      store.commit('set_dbclient', dbclient)
      let direction = NegentropyDirection.Down;
      let opts = new NegentropyOptions().direction(direction);


      let followings = []
      let followers_filter = new Filter().author(publicKey).kind(3).limit(1)
      let followers = await dbclient.getEventsOf([followers_filter], Duration.fromSecs(5))

    if (followers.length > 0){
          for (let tag of followers[0].tags) {
        if (tag.asVec()[0] === "p") {
          let following = tag.asVec()[1]
          followings.push(PublicKey.fromHex(following))
        }
    }

      }
      console.log("Followings: " + (followings.length).toString())


      let filter = new Filter().kind(0).authors(followings)
      await dbclient.reconcile(filter, opts);

    }
   },
    async get_user_info(pubkey){
        let client = store.state.client
        const profile_filter = new Filter().kind(0).author(pubkey).limit(1)
        let evts = await client.getEventsOf([profile_filter], Duration.fromSecs(5))
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
        else{
           this.current_user = pubkey.toBech32()
           this.avatar = "https://noogle.lol/favicon.ico"

          }
    },


    async sign_out(){
      this.current_user = ""
      if(localStorage.getItem('nostr-key-method') === "nostr-login"){
        await logoutNostrLogin()
      }
      console.log("LOGOUT")
      localStorage.setItem('nostr-key-method', "anon")
      localStorage.setItem('nostr-key', "")

      //await this.state.client.shutdown();
      await this.sign_in_anon()
    },

    async store_nwc(){
      let connector = ""
      let nwc = ""
      if (this.nwcalby.startsWith("nostr")){
        connector = "alby"
        nwc = this.nwcalby
      }
      else if (this.nwcmutiny.startsWith("nostr") ){
        connector = "mutiny"
        nwc = this.nwcmutiny
      }
      else{
        connector = "user"
        nwc  = this.nwc
      }
      localStorage.setItem("nwc", "{\"nwcUrl\":\"" + nwc + "\",\"connectorName\":\""+ connector +"\",\"connectorType\":\"" + connector +"\"}" )
    },


async connect_alby_nwc(){

const alby = webln.NostrWebLNProvider.withNewSecret();
let result = await alby.client.initNWC({
        name: `Noogle`,
      });

 if (result.payload.success){
   this.nwcalby =  alby.client.getNostrWalletConnectUrl(true);
   await this.store_nwc()
 }
},

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


.u-Input {
    @apply bg-base-200 dark:bg-base-200 dark:text-white  focus:ring-white  border border-transparent px-3 py-1.5 text-sm leading-4 text-accent-content transition-colors duration-300  focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;

  width: 220px;
}

.nwc-Input {
    @apply bg-base-200 dark:bg-base-200 dark:text-white  focus:ring-white  border border-white px-3 py-1.5 text-sm leading-4 text-accent-content transition-colors duration-300  focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-gray-900;



}

.modal{
  @apply dark:text-white
}



</style>