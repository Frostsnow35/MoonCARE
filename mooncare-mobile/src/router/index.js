import { createRouter, createWebHashHistory } from 'vue-router'

import BleMonitor from '../views/BleMonitor.vue'
import Login from '../views/Login.vue'
import Settings from '../views/Settings.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'ble', component: BleMonitor },
    { path: '/login', name: 'login', component: Login },
    { path: '/settings', name: 'settings', component: Settings },
  ],
})

export default router
