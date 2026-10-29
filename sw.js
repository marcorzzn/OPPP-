/* Service worker di OverPowerPoint Studio.
 * Cambia CACHE (opp-v1 → opp-v2) ogni volta che modifichi index.html o questo file,
 * altrimenti i browser restano sulla versione in cache.
 */
const CACHE = "opp-v2";
const CORE = [
  "./index.html",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable.png",
  "./icons/apple-touch-icon.png",
  "./effects/manifest.json",
  "./effects/sdk.js",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      await cache.addAll(CORE);
      try {
        const mf = await fetch("./effects/manifest.json").then((r) => r.json());
        const files = (mf.effects || []).map((x) => "./effects/" + x.file);
        if (files.length) await cache.addAll(files);
      } catch (err) {
        console.warn("SW: effetti non in cache", err);
      }
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return; // nessuna cache per URL esterni
  // Il catalogo effetti si aggiorna dal vivo (network-first), così un nuovo
  // effetto compare dopo un refresh anche se il service worker è datato.
  if (url.pathname.endsWith("/effects/manifest.json")) {
    e.respondWith(fetch(e.request).then((r) => (r.ok ? r : caches.match(e.request))));
    return;
  }
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
