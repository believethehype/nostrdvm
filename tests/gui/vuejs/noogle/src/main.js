import './assets/main.css'
import { createApp } from 'vue'

import App from './App.vue'
import store from './store';

import Vue3EasyDataTable from 'vue3-easy-data-table';
import 'vue3-easy-data-table/dist/style.css';

//This is all for notifications
import VueNotifications from 'vue-notifications'
import miniToastr from 'mini-toastr'
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




createApp(App).use(VueNotifications, options).use(store).component('EasyDataTable', Vue3EasyDataTable).mount('#app')
