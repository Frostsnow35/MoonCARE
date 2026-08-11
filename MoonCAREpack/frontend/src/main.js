import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/main.css'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 初始化认证状态
const authStore = useAuthStore()
authStore.initializeAuth()

app.mount('#app')

// PWA: register Service Worker only in production builds and on secure-ish
// origins. Browsers require HTTPS (or localhost) for SW registration; over
// plain-IP HTTP this is a no-op and the app still works as a normal web app.
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((reg) => console.log('[PWA] Service worker registered:', reg.scope))
      .catch((err) => console.warn('[PWA] Service worker registration skipped:', err.message))
  })
}
