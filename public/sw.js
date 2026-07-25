// Per Actum service worker: precaches the entire site (all chapters as RSC
// payloads plus the app shell) so reading works fully offline.
// __BUILD_VERSION__ is stamped by scripts/build-sw.mjs after `next build`.
const VERSION = "__BUILD_VERSION__";
const CACHE = `peractum-${VERSION}`;
const PRECACHE_MANIFEST = "/sw-precache.json";
const FILL_BATCH = 24;

function stripSearch(url) {
  const u = new URL(url, self.location.origin);
  u.search = "";
  return u.toString();
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      await cache.add(new Request("/", { cache: "reload" }));
      await self.skipWaiting();
    })()
  );
});

// Activation must stay fast: fetch events from claimed pages are queued
// until it finishes, so awaiting the full precache here would blank every
// page until the whole site downloaded. The fill runs from the pages'
// "fill" message instead, which also resumes interrupted fills.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(
        names
          .filter((n) => n.startsWith("peractum-") && n !== CACHE)
          .map((n) => caches.delete(n))
      );
      await self.clients.claim();
    })()
  );
});

// Pages re-post this on every load so an interrupted fill resumes.
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "fill") {
    event.waitUntil(fillPrecache());
  }
});

let filling = false;
async function fillPrecache() {
  if (filling) return;
  if (navigator.connection && navigator.connection.saveData) return;
  filling = true;
  try {
    const res = await fetch(PRECACHE_MANIFEST, { cache: "no-cache" });
    if (!res.ok) return;
    const { files } = await res.json();
    const cache = await caches.open(CACHE);
    for (let i = 0; i < files.length; i += FILL_BATCH) {
      const batch = files.slice(i, i + FILL_BATCH);
      await Promise.all(
        batch.map(async (path) => {
          if (await cache.match(path)) return;
          try {
            const response = await fetch(path);
            if (response.ok) await cache.put(path, response);
          } catch {
            // Offline or flaky network: a later fill message retries.
          }
        })
      );
    }
  } finally {
    filling = false;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(handleNavigation(request));
  } else {
    event.respondWith(handleAsset(request));
  }
});

// HTML documents: network first so deploys show up immediately, cache as
// offline fallback. Unvisited deep links fall back to the home shell.
async function handleNavigation(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(stripSearch(request.url), response.clone());
    return response;
  } catch {
    const cached = await cache.match(request, { ignoreSearch: true });
    if (cached) return cached;
    const home = await cache.match("/");
    return home || Response.error();
  }
}

// Everything else (RSC .txt payloads, hashed /_next/static assets, fonts,
// icons): cache first. The cache is versioned per deploy, so within one
// version every asset is immutable.
async function handleAsset(request) {
  const cached = await caches.match(request, { ignoreSearch: true });
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(CACHE);
    cache.put(stripSearch(request.url), response.clone());
  }
  return response;
}
