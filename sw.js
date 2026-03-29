self.addEventListener("install", () => {
  console.log("PWA Installed");
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
