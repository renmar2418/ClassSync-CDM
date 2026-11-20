// ClassSync PWA Offline Service Worker (RFC 5545, Schedulable Caching, D-12 Empathetic Offline)
const SHELL_CACHE = 'classsync-shell-v1';
const DATA_CACHE = 'classsync-data-v1';

const STATIC_SHELL_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/fonts/InterVariable.woff2',
  '/branding/cdm-seal.png',
  '/branding/classsync-logo-assets/classsync-horizontal-light.png',
  '/branding/classsync-logo-assets/classsync-full-light.png',
  '/branding/classsync-logo-assets/classsync-ribbon-mark.png',
  '/branding/classsync-logo-assets/classsync-icon-32.png',
  '/branding/classsync-logo-assets/classsync-icon-48.png',
  '/branding/classsync-logo-assets/classsync-icon-192.png',
  '/branding/classsync-logo-assets/classsync-icon-512.png',
];

// 1. Installation: Pre-cache static shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then((cache) => cache.addAll(STATIC_SHELL_ASSETS).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

// 2. Activation: Purge stale caches
self.addEventListener('activate', (event) => {
  const currentCaches = [SHELL_CACHE, DATA_CACHE];
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (!currentCaches.includes(key)) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 3. Routing Strategies
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // A. Dynamic Attendance & Real-Time SSE Streams: Network-Only (NEVER CACHE)
  if (
    url.pathname.startsWith('/api/v1/presence/') ||
    event.request.headers.get('Accept')?.includes('text/event-stream')
  ) {
    event.respondWith(fetch(event.request));
    return;
  }

  // B. Timetable & Academic Read Operations: Stale-While-Revalidate with Timeout
  if (
    url.pathname.startsWith('/api/v1/scheduling/') ||
    url.pathname.startsWith('/api/v1/academic/')
  ) {
    event.respondWith(
      caches.open(DATA_CACHE).then(async (cache) => {
        const cachedResponse = await cache.match(event.request);

        // Fetch from network with 2.5-second timeout for sluggish campus Wi-Fi
        const fetchPromise = Promise.race([
          fetch(event.request)
            .then((networkResponse) => {
              if (networkResponse.ok) {
                cache.put(event.request, networkResponse.clone());
              }
              return networkResponse;
            })
            .catch(() => null),
          new Promise((resolve) => setTimeout(() => resolve(null), 2500)),
        ]);

        const networkResult = await fetchPromise;
        if (networkResult) {
          return networkResult;
        }

        // Network failed or timed out: Return cached response if available
        if (cachedResponse) {
          const headers = new Headers(cachedResponse.headers);
          headers.set('X-ClassSync-Offline', 'true');
          return new Response(cachedResponse.body, {
            status: cachedResponse.status,
            statusText: cachedResponse.statusText,
            headers,
          });
        }

        // Neither network nor cache: Return plain-language offline JSON (Decision Log D-12)
        return new Response(
          JSON.stringify({
            offline: true,
            error: true,
            user_message: '🟢 Offline Mode • Showing your saved schedule. Reconnecting to campus Wi-Fi...',
          }),
          {
            status: 503,
            headers: {
              'Content-Type': 'application/json',
              'X-ClassSync-Offline': 'true',
            },
          }
        );
      })
    );
    return;
  }

  // C. Static Shell Assets, Fonts, & Images: Cache-First
  if (
    STATIC_SHELL_ASSETS.includes(url.pathname) ||
    url.pathname.startsWith('/fonts/') ||
    url.pathname.startsWith('/branding/') ||
    url.pathname.match(/\.(woff2|png|svg|ico|css|js)$/)
  ) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((networkResponse) => {
          if (networkResponse.ok) {
            caches.open(SHELL_CACHE).then((cache) => cache.put(event.request, networkResponse.clone()));
          }
          return networkResponse;
        });
      })
    );
    return;
  }

  // D. SPA Navigation Fallback: Network-First with fallback to index.html
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match('/index.html'))
    );
    return;
  }

  // Default: Network Fetch
  event.respondWith(fetch(event.request));
});
