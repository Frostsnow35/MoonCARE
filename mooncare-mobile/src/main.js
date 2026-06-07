import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/main.css'
import { useAuthStore } from './stores/auth'
import { getApiBaseUrl } from './services/apiConfig'

// #region debug-point B:module-start
window.__MC_DBG?.('B', 'src/main.js:module-start', '[DEBUG] main module start', {
  hash: window.location.hash,
  path: window.location.pathname,
})
// #endregion

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function showStartupError(error) {
  const message = error?.stack || error?.message || String(error || '未知错误')
  console.error('[MoonCARE startup error]', error)
  // #region debug-point D:startup-error
  window.__MC_DBG?.('D', 'src/main.js:showStartupError', '[DEBUG] startup error surfaced', {
    message: String(message).slice(0, 500),
  })
  // #endregion

  const root = document.getElementById('app')
  if (!root) return

  root.innerHTML = `
    <div style="min-height:100vh;padding:24px;background:#fff1f5;color:#111827;font-family:sans-serif;">
      <div style="max-width:420px;margin:48px auto;background:#fff;border:1px solid #fecdd3;border-radius:18px;padding:20px;box-shadow:0 16px 40px rgba(244,63,94,.12);">
        <div style="font-size:18px;font-weight:800;margin-bottom:8px;">MoonCARE 启动失败</div>
        <div style="font-size:13px;color:#64748b;line-height:1.6;margin-bottom:12px;">应用启动时遇到运行错误。请把下面这段错误发给开发者。</div>
        <pre style="white-space:pre-wrap;word-break:break-word;background:#fff1f2;border:1px solid #fecdd3;border-radius:12px;padding:12px;color:#be123c;font-size:12px;line-height:1.5;max-height:360px;overflow:auto;">${escapeHtml(message)}</pre>
      </div>
    </div>
  `
}

window.addEventListener('error', (event) => {
  // #region debug-point D:window-error
  window.__MC_DBG?.('D', 'src/main.js:window-error', '[DEBUG] window error', {
    message: event.message || '',
  })
  // #endregion
  showStartupError(event.error || event.message)
})

window.addEventListener('unhandledrejection', (event) => {
  // #region debug-point D:unhandled-rejection
  window.__MC_DBG?.('D', 'src/main.js:unhandledrejection', '[DEBUG] unhandled rejection', {
    reason: String(event.reason?.message || event.reason || '').slice(0, 500),
  })
  // #endregion
  showStartupError(event.reason)
})

try {
  const app = createApp(App)
  const pinia = createPinia()

  app.config.errorHandler = (error) => {
    showStartupError(error)
  }

  router.onError((error) => {
    showStartupError(error)
  })

  app.use(pinia)
  app.use(router)

  const authStore = useAuthStore()
  authStore.initializeAuth()
  void getApiBaseUrl()

  await router.isReady()
  // #region debug-point B:router-ready
  window.__MC_DBG?.('B', 'src/main.js:router-ready', '[DEBUG] router is ready before mount', {
    hash: window.location.hash,
    path: window.location.pathname,
  })
  // #endregion

  app.mount('#app')
  // #region debug-point B:mount-complete
  window.__MC_DBG?.('B', 'src/main.js:mount-complete', '[DEBUG] app mounted', {
    hash: window.location.hash,
    rootChildren: document.getElementById('app')?.childElementCount || 0,
  })
  requestAnimationFrame(() => {
    window.__MC_DBG?.('C', 'src/main.js:first-raf', '[DEBUG] first animation frame', {
      appHtmlLength: document.getElementById('app')?.innerHTML?.length || 0,
      bodyBackground: getComputedStyle(document.body).backgroundColor,
    })
  })
  // #endregion
} catch (error) {
  showStartupError(error)
}
