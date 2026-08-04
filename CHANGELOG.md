# Changelog

Notable changes to the Weight Goal Calculator, newest first. Dates are
commit dates. Every push to `main` publishes the site, so web entries go
live as soon as they land.

## 2026-08-04 — Dropped the /preview/ deployment

### Removed
- The `/preview/` build. Deploys are now root-only: one branch, one
  build, `web/` minus the self-test.

### Notes
- Once the branch split was gone, preview and production shipped from
  the same push — so the "look at it before it's live" value it was
  originally justified by no longer existed.
- What remained was narrower than it looked. Android install testing
  works locally (Chrome DevTools USB port forwarding makes a forwarded
  `localhost` a secure context), service workers and install prompts
  fire on `localhost`, and every path in this app is relative so a
  subpath proves nothing the root doesn't. The only genuine gap was
  installing the PWA from a real iPhone, which isn't something this
  project does.
- `web/selftest.html` is unchanged and stays in the repository for local
  use. The `<!-- dev-only -->` markers stay too — they are still what
  keeps the footer link out of the deployed page.

## 2026-08-04 — Collapsed to one branch, two builds

### Changed
- The deploy workflow builds both targets from the pushed commit rather
  than checking out two branches. `/` is the product with the self-test
  stripped; `/preview/` is the same source untouched. The split that
  mattered was always build-time, never branch-time.
- The workflow triggers on `main` only.

### Removed
- The `development` branch, along with the cross-branch checkout, the
  merge ritual, and the branch-drift class of bug — a `sw.js` comment had
  already auto-merged into a false statement without producing a
  conflict, which is exactly the failure a split invites.

### Notes
- The preview survives because it covers what localhost cannot: PWA
  install from a real phone (a LAN address over plain http is not a
  secure context) and a shareable pre-release link. Everything else is
  testable locally — every path in the app is relative, so it behaves
  identically at any prefix, and `localhost` is a secure context, so the
  service worker registers there.
- **A push is now a release.** The tradeoff accepted: no staging of
  unreleased work where others can see it. Bring a second branch back if
  and when that is actually needed.
- What protects production is the gate — 104 Python tests, fixture
  freshness, and 27,402 self-test checks, all before any deploy — not the
  number of branches.

## 2026-08-04 — Two-branch pipeline: production from main, preview from development

### Added
- The deploy workflow now runs on pushes to `development` as well as
  `main`, and publishes both from the one Pages site: the root is built
  from `main` with the self-test stripped, and `/preview/` is built from
  `development` with everything intact. Work on `development` is now
  testable on real HTTPS — service worker, PWA install, the genuine
  Pages environment — without touching what visitors see.
- The verification gate (Python suite, fixture freshness, headless
  self-test) now runs on `development` pushes too. Before this, work on
  that branch had no CI at all and was first checked on the way into
  production.
- `<meta name="robots" content="noindex">` is injected into every
  preview page at build time. Staging shouldn't be indexed.

### Changed
- The difference between the two builds is now entirely build-time.
  Both branches carry the same source; the production build removes the
  self-test files and any `<!-- dev-only -->` blocks that link to them.
  Nothing about the split lives in branch contents, so `development` and
  `main` never conflict over these files and merges stay clean.
- The calculator footer's "Core self-test" link is wrapped in those
  markers rather than deleted: present on the preview, stripped from
  production.

### Notes
- Pages serves one site per repository and each deploy replaces it
  wholesale, so a preview cannot be published without also republishing
  the root. Every deploy therefore rebuilds both, always taking the root
  from `main` and the preview from `development` regardless of which
  branch triggered it. A `development` push republishes a root identical
  to what is already live.

## 2026-08-04 — The self-test is no longer published

### Changed
- The deploy job now stages a copy of `web/` with `selftest.html`,
  `selftest.js` and `fixture.js` removed, and publishes that. The
  self-test is developer tooling: `fixture.js` alone is 1.5 MB against
  roughly 50 KB for the whole app, so shipping it multiplied the site's
  weight ~30× to serve a page no visitor had a reason to open. The
  files stay in version control and the verify job still runs them —
  unshipping the harness is not the same as deleting it.
- The staging step fails the deploy if any of the three survive the
  copy, or if a published page still links to one, so a live 404 can't
  slip through.

### Removed
- The calculator footer's "Core self-test" link, which pointed at a
  page that is no longer deployed. (Reinstated behind `<!-- dev-only -->`
  markers by the entry above, which publishes it to the preview and
  strips it from production.)

## 2026-08-04 — CI now runs the browser self-test; a test that wasn't testing

### Added
- `tools/run_selftest.js` runs the browser core's self-test headlessly
  under Node, and the deploy workflow now blocks on it. The pipeline
  previously verified the Python side and the freshness of
  `web/fixture.js`, then published `web/` without ever executing a
  line of the JavaScript: that caught `calc_core.py` drifting away
  from the fixture, but not `calc_core.js` drifting away from it —
  the direction the self-test is actually for. A broken port could go
  green and ship, with nothing between it and users but somebody
  remembering to open `selftest.html` by hand.
- `web/selftest.js` holds the checks themselves, now shared by that
  page and the CI runner. Same reasoning as `calc_core.js` being a
  `<script src>` and not inline copy: two copies of the checks could
  disagree about what "PASS" means. Check counts are unchanged —
  27,402 across 1,478 plan cases.

### Fixed
- `tests/test_formatting.py`'s rejection-routing test now derives the
  set of codes from `calc_core.py`'s source instead of asserting two
  hardcoded counts. Its comment claimed it guarded against a rejection
  code being added without a routing decision; it could not — `seen`
  was built from a fixed list of eleven inputs, so a twelfth code left
  both counts unchanged and the test still passed. It now names the
  orphaned code and fails.

## 2026-08-04 — Theme selector moved to the top, on both pages

### Changed
- The theme chips (Pink / Light / Dark) moved from the calculator's
  footer to the top of the page, right-aligned above the title — and
  the install page now has the same selector, where before it only
  followed the choice made elsewhere.
- The picker logic moved into `web/theme.js`, shared by both pages
  (same anti-drift reasoning as `install.js`); service worker shell
  updated accordingly (cache `wgc-shell-v3`), deploy guard requires
  the new file.

### Removed
- The install page's footer "Open the calculator" link — redundant
  with the "Use it in your browser" link in the card above it.

### Added
- Both footers now note the site was co-developed with Claude,
  Anthropic's AI.

## 2026-08-04 — New app icon

### Changed
- The app icon is now a man and a woman standing together on a scale,
  from a vector illustration supplied by the project owner, recolored
  to the brand palette: white silhouettes and a plum scale on the
  brand pink. Replaces the gauge dial.
- `tools/gen_icons.py` is now a tiny SVG rasterizer (still standard
  library only): the illustration's path data is embedded in the
  script and rendered via bézier flattening, nonzero-winding scanline
  fill, and supersampled anti-aliasing, so the icons remain
  reproducible from the repo. The artwork is scaled slightly inward
  to clear the maskable safe zone.

## 2026-08-04 — Quieter pages: collapsed instructions, no empty results card

### Changed
- The install page's step-by-step instructions are now collapsed
  behind a native disclosure (`<details>`); the platform dropdown and
  steps appear only after clicking "Step-by-step instructions".
- The calculator's results card no longer sits empty on the page —
  it appears the first time Calculate is clicked (for a plan, a
  calorie-floor refusal, or the fix-the-field hint) and stays from
  then on.

## 2026-08-04 — Page redesign: themes, footer navigation, warning moved

### Added
- Three selectable themes on the calculator page, picked from chip
  buttons in the footer: **Pink** (the default — the deep plum with
  pink accents that was previously the dark-mode palette), **Light**
  (natural linen/stone neutrals with a muted sage accent —
  deliberately not bright), and **Dark** (a standard neutral web
  dark: near-black surfaces, gray text, blue accent). With no choice
  made, a light-preferring system gets Light and everything else
  gets Pink; a choice is saved on the device (`localStorage`, the
  only thing the site stores) and applied before first paint so
  there is no flash. The install page follows the saved theme too.
  The old bright pastel palette is retired.
- Footer navigation on both pages: the calculator links to the
  install page and the self-test; the install page links back to the
  calculator.

### Changed
- The medical-disclaimer warning moved from the top of the calculator
  page to the bottom, above the footer.
- The browser-chrome color (`theme-color`) now tracks the selected
  palette.

### Removed
- The "Get the app" install card no longer appears on the calculator
  page — installation now lives on `install.html`, reachable from the
  footer. `?install` links redirect there, so previously shared URLs
  keep working.

## 2026-08-04 — Word-for-word install steps on the install page

### Added
- `web/install.html` now carries a "Step-by-step instructions"
  dropdown listing each platform — Chrome and Edge on a computer,
  Android Chrome, iPhone/iPad Safari, iPhone/iPad Chrome (iOS 16.4+,
  detected via its CriOS user agent), Mac Safari, and Firefox — with
  the exact, word-for-word taps and clicks for each, quoting the
  browser's own menu labels. The visitor's platform is preselected
  from the user agent; the dropdown covers everyone else. Firefox's
  entry honestly says desktop Firefox cannot install web apps and
  points at the alternatives.

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
