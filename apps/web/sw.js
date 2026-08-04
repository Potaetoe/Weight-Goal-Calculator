/*
 * Service worker: makes the page installable as an app and keeps it
 * working offline. It handles only the app shell listed below and
 * leaves every other request to the browser.
 *
 * The strategy is network-first with cache fallback, NOT cache-first.
 * This project has already been bitten once by a cache serving stale
 * code (see the cache-buster in dev/selftest.html); a cache-first shell
 * would recreate that bug one layer down, pinning installed users to
 * an old calculator until someone remembered to bump the cache name.
 * Network-first costs one request per load and can never serve stale
 * code while online; the cache only answers when the network cannot.
 *
 * The self-test and its 1.5 MB fixture are not here because they are not
 * in this directory at all - they live in dev/, which is never
 * published. Nothing to strip, and nothing to forget to strip.
 *
 * SHELL must list every file in this directory except sw.js itself.
 * tools/check_web.py enforces that, because the failure mode of
 * forgetting an entry is invisible online and only breaks the installed
 * app offline.
 */

var CACHE = "wgc-shell-v4";
var SHELL = [
  "./",
  "index.html",
  "calc_core.js",
  "install.html",
  "install.js",
  "theme.css",
  "theme.js",
  "manifest.json",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/apple-touch-icon.png"
];
// Cache keys and membership checks use pathnames so that query strings
// (dev/selftest.html loads calc_core.js?t=...) neither miss nor pollute.
var SHELL_PATHS = SHELL.map(function (p) {
  return new URL(p, self.location.href).pathname;
});

self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      return c.addAll(SHELL);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) {
        return k !== CACHE;
      }).map(function (k) {
        return caches.delete(k);
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  var url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  if (SHELL_PATHS.indexOf(url.pathname) === -1) return;

  e.respondWith(
    fetch(e.request).then(function (res) {
      if (res.ok) {
        // Refresh the offline copy on every successful load, keyed by
        // pathname so ?t= cache-busters collapse onto one entry.
        var copy = res.clone();
        e.waitUntil(caches.open(CACHE).then(function (c) {
          return c.put(url.pathname, copy);
        }));
      }
      return res;
    }).catch(function () {
      return caches.match(url.pathname).then(function (hit) {
        if (hit) return hit;
        throw new TypeError("offline and not cached: " + url.pathname);
      });
    })
  );
});
