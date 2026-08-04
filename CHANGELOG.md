# Changelog

Notable changes to the Weight Goal Calculator, newest first. Dates are
commit dates. The web version deploys to GitHub Pages on every push to
`main`, so entries there go live immediately.

## 2026-08-04 — Dedicated install page, install card moved to the top

### Added
- `web/install.html` — a standalone page whose only job is
  installation: app icon, one-line description, a single **Install
  this app** button, and a link back to the in-browser calculator.
  This is the URL to send people.
- `web/install.js` — the install-button logic, extracted so
  `index.html` and `install.html` share one copy instead of drifting
  (the same reasoning as `calc_core.js`).

### Changed
- The calculator page's install card moved from below the results to
  the top of the page, above the form.
- Service worker shell now includes the install page and shared
  script (cache bumped to `wgc-shell-v2`).
- Deploy workflow's asset guard now also requires `install.html` and
  `install.js`.

## 2026-08-04 — In-page install button and ?install share link

### Added
- An **Install this app** card on the web page. When the browser
  offers one-tap install (Chromium's `beforeinstallprompt`), the
  button opens the native install dialog; everywhere else it shows
  per-platform instructions (iOS gets the Share → Add to Home Screen
  steps directly). Hidden when already running as an installed app
  and on `file://`, where installing isn't possible.
- A shareable install link: appending `?install` to the page URL
  reveals the card, scrolls it into view, and focuses the button — as
  close to an "install link" as browsers permit, since installation
  always requires a tap on the page.
- README — documented the button and the `?install` link.

## 2026-08-04 — Installable app (PWA)

### Added
- `web/manifest.json` — app metadata (name, standalone display, theme
  colors, icons) that lets browsers install the page as a standalone
  app with its own icon and window.
- `web/sw.js` — service worker providing offline support for the
  installed app. Network-first with cache fallback, so it can never
  serve stale code while online; the ~46 KB app shell is precached and
  everything else (including the 1.5 MB self-test fixture) is
  deliberately left uncached.
- `web/icons/` — generated app icons (192, 512, and a 180 px
  apple-touch-icon): a scale dial drawn in the app's palette, sized
  inside the maskable safe zone.
- `tools/gen_icons.py` — regenerates those icons using only the
  standard library, keeping the project's zero-dependency rule.
- `web/index.html` — manifest, icon, and theme-color links, plus
  service worker registration that only runs on HTTPS or localhost.
  Opening the file directly (`file://`) is unchanged: no registration
  is attempted and the page behaves exactly as before.
- README — "Installing it as an app" section with per-platform install
  instructions (Chrome/Edge, Android, iOS).

### Changed
- Deploy workflow's asset guard now also requires the manifest, the
  service worker, the icons, and the manifest link in `index.html`
  before publishing.

## 2026-08-04 — Web error placement fix

### Fixed
- In Imperial mode, an invalid inches box ("abc", or a negative value
  dragging total height below zero) highlighted and focused the age
  field instead of the height row. Height is now judged the way the
  core parses it — feet plus inches as one value.
- In Metric mode, a height error set focus and `aria-invalid` on the
  hidden feet box, so focus silently went nowhere and screen readers
  got no announcement. Both lookups now skip inputs hidden with the
  inactive unit variant.

## 2026-08-04 — Web version and deploy pipeline

### Added
- `web/index.html` + `web/calc_core.js` — the calculator as a static
  browser page: no build step, no server, nothing sent or stored. The
  JS core is a line-for-line port of `calc_core.py` with the same
  formulas, bounds, validation order, rejection codes, and copy.
- `web/selftest.html` + `web/fixture.js` — self-test comparing the JS
  core against ~27,000 expected outputs captured from the Python core,
  covering every formula, rejection message, and rendered results
  line. `tools/gen_web_fixture.py` regenerates the fixture.
- `.github/workflows/deploy.yml` — publishes `web/` to GitHub Pages on
  every push to `main`, but only after the Python suite passes and the
  committed fixture is confirmed current, so the deployed self-test
  can never pass against stale expectations.

## 2026-08-03 — Core split and test suite

### Changed
- All math and accept/reject decisions extracted from the tkinter GUI
  into `calc_core.py`, a pure, dependency-free module returning plans
  or typed rejections as data.
- Imperial height entry split into separate feet and inches boxes,
  with out-of-range inches rejected (and the folded ft/in equivalent
  suggested) rather than silently normalized.

### Added
- `tests/` — 104-test suite (standard library `unittest`), including
  an equivalence test replaying the pre-refactor implementation from
  git history, and pinned design bounds documented in the README.

## 2026-06-30 — v1.0.0

### Added
- Initial release: tkinter desktop calculator with Mifflin-St Jeor and
  Katch-McArdle BMR, TDEE from activity level, calorie targets and
  timelines for a weekly pace, imperial/metric units with entry
  conversion, a 1,200 kcal/day hard floor, an 18+ age minimum, and a
  BMI 18.5 floor on goal weight.
