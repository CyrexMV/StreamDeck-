// Minimaler Service Worker – nötig, damit Android TabDeck als App installieren kann.
// Es wird bewusst nichts zwischengespeichert: TabDeck funktioniert nur mit Verbindung zum PC.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
