export {};

interface ExtendableEvent extends Event {
  waitUntil(fn: Promise<unknown>): void;
}

interface FetchEvent extends Event {
  request: Request;
  respondWith(r: Response | Promise<Response>): void;
}

interface ServiceWorkerGlobalScopeLike {
  addEventListener(type: 'install', listener: (event: ExtendableEvent) => void): void;
  addEventListener(type: 'activate', listener: (event: ExtendableEvent) => void): void;
  addEventListener(type: 'fetch', listener: (event: FetchEvent) => void): void;
  skipWaiting(): Promise<void>;
  clients: {
    claim(): Promise<void>;
  };
}

const sw = self as unknown as ServiceWorkerGlobalScopeLike;

const SHELL_CACHE = 'classsync-shell-v1';
const DATA_CACHE = 'classsync-data-v1';

const STATIC_SHELL_ASSETS: string[] = [
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

// 1. Service Worker Installation: Pre-cache static shell
sw.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => {
      return cache.addAll(STATIC_SHELL_ASSETS).catch(() => {
        // Tolerant to missing optional mock asset binaries during development
      });
    }).then(() => {
      return sw.skipWaiting();
    })
  );
});

// 2. Service Worker Activation: Purge stale caches
sw.addEventListener('activate', (event: ExtendableEvent) => {
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
    }).then(() => {
      return sw.clients.claim();
    })
  );
});

// 3. Routing Strategies
sw.addEventListener('fetch', (event: FetchEvent) => {
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
          new Promise<null>((resolve) => setTimeout(() => resolve(null), 2500)),
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
      fetch(event.request).catch(() => {
        return caches.match('/index.html') as Promise<Response>;
      })
    );
    return;
  }

  // Default: Network Fetch
  event.respondWith(fetch(event.request));
});
