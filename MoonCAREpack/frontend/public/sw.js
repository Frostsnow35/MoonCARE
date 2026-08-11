/* MoonCARE PWA Service Worker
 *
 * Scope: static shell caching only. Never cache API responses, chat content,
 * diary text, or user privacy data. The app is served by FastAPI at the same
 * origin, so we use a relative scope ("/") and cache the app shell.
 *
 * Strategy:
 *  - "app shell" (index.html + hashed /assets/*) -> cache-first (offline start)
 *  - everything else -> network-first, fall back to cache for GET navigations
 */

const CACHE_NAME = 'mooncare-shell-v1'
const SHELL_ASSETS = ['/', '/manifest.json', '/icons/icon-192.png', '/icons/icon-512.png']
const API_PREFIX = '/api/'

/* Install: precache shell */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .catch((err) => {
        // A missing asset (e.g. during dev) must not block install.
        console.warn('[SW] precache warning:', err)
      })
      .then(() => self.skipWaiting())
  )
})

/* Activate: remove old caches */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  )
})

/* Fetch: never intercept /api/* */
self.addEventListener('fetch', (event) => {
  const req = event.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)
  if (url.origin !== self.location.origin) return
  if (url.pathname.startsWith(API_PREFIX)) return

  // Hashed build assets: cache-first (immutable).
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.match(req).then((cached) => cached || fetch(req).then((res) => {
        const copy = res.clone()
        caches.open(CACHE_NAME).then((c) => c.put(req, copy))
        return res
      }))
    )
    return
  }

  // Navigations and other same-origin GETs: network-first, fallback to cache.
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone()
          caches.open(CACHE_NAME).then((c) => c.put(req, copy))
        }
        return res
      })
      .catch(() => caches.match(req).then((cached) => cached || caches.match('/')))
  )
})
