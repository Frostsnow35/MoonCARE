// Runtime server-address configuration for MoonCARE.
//
// The app can be served in three ways, each with a different way of knowing
// where the backend is:
//   1. One-image Docker deployment (frontend and API on the same origin) ->
//      API_BASE defaults to '/api/v1' and WebSocket is derived from location.
//   2. A separately-hosted frontend with an explicit build-time base ->
//      VITE_API_BASE_URL is an absolute http(s):// origin.
//   3. Capacitor Android APK / mobile browser hitting a server IP ->
//      user sets a "服务器地址" in Profile; it is stored in localStorage and
//      takes priority over the defaults below.
//
// localStorage is used here (not a PWA/Cap storage plugin) so the same code
// path works for the plain browser, the installed PWA and the APK WebView.

const LS_KEY = 'mooncare_server_base'
const DEFAULT_API_BASE = '/api/v1'

export function getStoredServerBase() {
  try {
    return (localStorage.getItem(LS_KEY) || '').trim()
  } catch (e) {
    return ''
  }
}

export function setStoredServerBase(value) {
  try {
    const v = (value || '').trim().replace(/\/+$/, '')
    if (v) {
      localStorage.setItem(LS_KEY, v)
    } else {
      localStorage.removeItem(LS_KEY)
    }
    return v
  } catch (e) {
    return ''
  }
}

// Resolve the API origin (scheme://host[:port]) from a stored server base
// or from the page location. Returns '' when API is same-origin ('/api/v1').
function resolveApiOrigin() {
  const stored = getStoredServerBase()
  if (stored) {
    // stored may be 'http://1.2.3.4:18000' or 'http://1.2.3.4:18000/api/v1'
    return stored.replace(/\/api\/v1\/?$/, '').replace(/\/+$/, '')
  }
  return ''
}

// Full API base used by the axios client.
export function getApiBaseUrl() {
  const origin = resolveApiOrigin()
  if (origin) return `${origin}${DEFAULT_API_BASE}`
  const fromEnv = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE
  return fromEnv.replace(/\/+$/, '')
}

// WebSocket origin derived from the API origin. Same-origin when no server
// base is configured (ws://{location.host}/api/v1/chat/ws).
export function getWsBaseUrl() {
  const origin = resolveApiOrigin()
  if (origin) {
    return origin.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:')
  }
  const explicit = (import.meta.env.VITE_WS_BASE_URL || '').trim()
  if (explicit) {
    return explicit.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:').replace(/\/+$/, '')
  }
  return ''
}

// Absolute base for SSE/WebSocket fetches in views (Chat.vue).
export function getApiBaseForFetch() {
  const origin = resolveApiOrigin()
  if (origin) return `${origin}${DEFAULT_API_BASE}`
  return import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE
}

// Resolve a possibly-relative media URL (e.g. "/media/music/a.mp3") to an
// absolute URL when a remote server base is configured. Returns the URL
// unchanged for same-origin deployments.
export function resolveMediaUrl(url) {
  if (!url) return url
  if (/^https?:\/\//i.test(url)) return url
  const origin = resolveApiOrigin()
  if (origin) return `${origin}${url.startsWith('/') ? '' : '/'}${url}`
  return url
}
