// Service worker di OverPowerPoint Studio.
// Strategia: cache-first per il guscio dell'app (funziona offline dopo la prima visita),
// network-first per il catalogo degli effetti così i nuovi effetti compaiono appena online.
const CACHE = "opp-v3";
const CORE = [
  "./",
  "./index.html",
  "./manifest.json",
  "./favicon.ico",
  "./icons/favicon-32.png",
  "./icons/logo.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable.png",
  "./icons/apple-touch-icon.png",
  "./effects/manifest.json",
  "./effects/sdk.js",
  "./effects/poster-vintage.html",
  "./effects/split-image.html",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((c) => c.addAll(CORE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Catalogo effetti: prova prima la rete così si vedono subito gli effetti nuovi.
  if (url.pathname.endsWith("/effects/manifest.json")) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req)),
    );
    return;
  }

  // Tutto il resto: cache-first con aggiornamento in background.
  event.respondWith(
    caches.match(req).then((hit) => {
      const net = fetch(req)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => hit);
      return hit || net;
    }),
  );
});
