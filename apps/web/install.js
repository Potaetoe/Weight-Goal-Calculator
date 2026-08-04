/*
 * Shared install-button logic for index.html and install.html - a
 * separate file for the same reason calc_core.js is: two inline
 * copies would drift apart.
 *
 * No URL can trigger a PWA installation directly - every browser
 * requires a user gesture on the page - so a visible button wired to
 * the deferred beforeinstallprompt event is the closest thing to an
 * "install link" the platform permits. Where that event never fires
 * (iOS, Safari, Firefox), the button explains the per-platform route
 * instead.
 */
(function (global) {
  "use strict";

  var standalone = (global.matchMedia &&
      global.matchMedia("(display-mode: standalone)").matches) ||
    global.navigator.standalone === true;
  var iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    // iPadOS reports itself as a Mac; the touch points give it away.
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

  function instructions() {
    if (iOS) {
      return "On iPhone or iPad: open this page in Safari, tap Share, " +
        "then “Add to Home Screen”.";
    }
    return "In Chrome or Edge: use the install icon at the right end " +
      "of the address bar, or the browser menu → “Install " +
      "page as app”. In Safari on a Mac: File → Add to " +
      "Dock. On iPhone or iPad: Share → Add to Home Screen.";
  }

  /* opts:
   *   button - the install button
   *   how    - paragraph for instructions / status text
   *   card   - container revealed when install becomes possible, or
   *            null on a page that shows the button unconditionally
   *   focus  - reveal now, scroll to the button, and focus it (the
   *            ?install landing behaviour)
   */
  function setup(opts) {
    var card = opts.card || null;
    var btn = opts.button;
    var how = opts.how;
    var pending = null;  // the deferred beforeinstallprompt event

    function explain(text) {
      how.textContent = text;
      how.hidden = false;
    }

    if (standalone) {
      // Already running as the installed app. An embedded card stays
      // hidden; a dedicated page says so instead of dangling a button.
      if (!card) {
        btn.hidden = true;
        explain("Already installed — you are using the app " +
          "right now.");
      }
      return;
    }

    if (location.protocol === "file:") {
      // Installation needs an origin; double-clicked local copies
      // keep working as plain pages, exactly as the README promises.
      if (!card) {
        btn.hidden = true;
        explain("Installing needs the hosted page — open the " +
          "site over HTTPS rather than this local file.");
      }
      return;
    }

    // Chromium fires this when the page qualifies for installation.
    // Deferring it to the button replaces the easy-to-miss
    // address-bar icon with a visible one-tap control.
    global.addEventListener("beforeinstallprompt", function (e) {
      e.preventDefault();
      pending = e;
      how.hidden = true;
      if (card) card.hidden = false;
    });

    global.addEventListener("appinstalled", function () {
      pending = null;
      if (card) {
        card.hidden = true;
      } else {
        btn.hidden = true;
        explain("Installed — launch it from your home screen " +
          "or app list.");
      }
    });

    btn.addEventListener("click", function () {
      if (pending) {
        // A deferred event can only prompt() once; if the user
        // dismisses the dialog, later clicks fall through to the
        // instructions (Chromium re-fires beforeinstallprompt when
        // it allows a retry).
        var p = pending;
        pending = null;
        p.prompt();
        return;
      }
      explain(instructions());
    });

    // Where the prompt can never arrive, lead with the instructions
    // rather than making the visitor click to discover them.
    if (!card && iOS) explain(instructions());

    if (opts.focus) {
      if (card) card.hidden = false;
      if (iOS) explain(instructions());
      // Give beforeinstallprompt a beat to arrive first.
      setTimeout(function () {
        btn.scrollIntoView({ block: "center", behavior: "smooth" });
        btn.focus({ preventScroll: true });
      }, 400);
    }
  }

  global.InstallUX = { setup: setup };
})(window);
