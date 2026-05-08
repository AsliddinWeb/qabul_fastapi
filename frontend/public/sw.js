// XIU Qabul — Service Worker
// Strategy:
//   - Static assets (Vite hashes filenames) → cache-first
//   - SPA navigations           → network-first, fallback to cached index.html
//   - API requests              → network only (never cache)
//   - Other resources           → stale-while-revalidate

const VERSION = 'xiu-v1'
const STATIC_CACHE  = `${VERSION}-static`
const RUNTIME_CACHE = `${VERSION}-runtime`
const APP_SHELL = '/app/'

const PRECACHE_URLS = [
  '/app/',
  '/app/index.html',
  '/app/favicon.svg',
  '/app/site.webmanifest',
  '/app/android-chrome-192x192.png',
  '/app/android-chrome-512x512.png',
  '/app/apple-touch-icon.png',
]

// ---------- Install ----------
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((c) => c.addAll(PRECACHE_URLS).catch(() => {}))
      .then(() => self.skipWaiting()),
  )
})

// ---------- Activate ----------
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== STATIC_CACHE && k !== RUNTIME_CACHE)
          .map((k) => caches.delete(k)),
      ),
    ).then(() => self.clients.claim()),
  )
})

// ---------- Fetch ----------
self.addEventListener('fetch', (event) => {
  const req = event.request
  if (req.method !== 'GET') return

  const url = new URL(req.url)

  // Never cache API / media — always go to network
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/media/')) {
    return  // let the browser do its default network fetch
  }

  // SPA navigations — network-first, fallback to cached app shell
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone()
          caches.open(RUNTIME_CACHE).then((c) => c.put(req, copy)).catch(() => {})
          return res
        })
        .catch(() => caches.match(APP_SHELL).then((r) => r || caches.match('/app/index.html'))),
    )
    return
  }

  // Static assets (hashed filenames in /app/assets/...) → cache-first
  if (url.pathname.startsWith('/app/assets/') || /\.(?:js|css|woff2?|ttf|otf|eot|svg|png|jpg|jpeg|gif|ico|webp)$/.test(url.pathname)) {
    event.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached
        return fetch(req).then((res) => {
          if (res && res.status === 200 && res.type === 'basic') {
            const copy = res.clone()
            caches.open(STATIC_CACHE).then((c) => c.put(req, copy)).catch(() => {})
          }
          return res
        }).catch(() => cached || Response.error())
      }),
    )
    return
  }

  // Other GETs: stale-while-revalidate
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req).then((res) => {
        if (res && res.status === 200) {
          const copy = res.clone()
          caches.open(RUNTIME_CACHE).then((c) => c.put(req, copy)).catch(() => {})
        }
        return res
      }).catch(() => cached)
      return cached || network
    }),
  )
})

// ---------- Skip waiting on demand (from page) ----------
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting()
})
