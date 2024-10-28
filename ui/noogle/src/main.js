//import './assets/main.css'
import { createApp } from 'vue'

import App from './App.vue'
import store from './store';
import "./app.css"

import 'vue3-easy-data-table/dist/style.css';
import router from './router'
import Vue3EasyDataTable from 'vue3-easy-data-table';

import VueDatePicker from '@vuepic/vue-datepicker';
import '@vuepic/vue-datepicker/dist/main.css'








//This is all for notifications
import VueNotifications from "vue-notifications";
import miniToastr from 'mini-toastr'
import { registerSW } from 'virtual:pwa-register'

registerSW({ immediate: true })

miniToastr.init()


function toast ({title, message, type, timeout, cb}) {
  return miniToastr[type](message, title, timeout, cb)
}

const options = {
  success: toast,
  error: toast,
  info: toast,
  warn: toast
}
//This is all for notifications end

createApp(App)
    .use(VueNotifications, options)
    .use(store)
    .use(router)

    .component('EasyDataTable', Vue3EasyDataTable)
    .component('VueDatePicker', VueDatePicker)
    .mount('#app')
