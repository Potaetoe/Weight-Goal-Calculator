# Weight Goal Calculator

A small desktop app that estimates your daily calorie needs and gives a
realistic timeline toward a weight goal. It has a pastel pink GUI, runs
fully offline, and stores nothing — no accounts, no tracking, no internet
connection required.

> **This tool is for entertainment and general informational purposes
> only.** It is not medical advice and is not a substitute for guidance
> from a registered dietitian, nutritionist, or physician. Always consult
> a qualified healthcare professional before making changes to your diet
> or exercise routine, especially if you have any underlying health
> conditions.

---

## What this app does

- Calculates your **BMR** (Basal Metabolic Rate — calories burned at
  rest) using the **Mifflin-St Jeor** equation, which performs well
  across a wide range of body sizes.
- Optionally uses the **Katch-McArdle** formula instead, if you know
  your body fat percentage — this can be more accurate since it's based
  on lean body mass.
- Calculates your **TDEE** (Total Daily Energy Expenditure) by factoring
  in your activity level.
- Recommends a daily calorie target based on a weight gain or loss goal
  and a weekly pace you enter.
- Estimates how many weeks/months it will take to reach your goal at
  that pace.
- Supports both **imperial** (lb, ft + in) and **metric** (kg, cm)
  units, converting your entries when you switch between them.
- **Refuses to produce a plan** in several situations rather than
  handing you a confident-looking number it shouldn't stand behind. See
  [What the calculator will refuse to do](#what-the-calculator-will-refuse-to-do).

---

## For the person setting this up: how to use this README

This README is written so you can paste it into an AI assistant (like
Claude, ChatGPT, or similar) along with the question **"walk me through
installing and running this"**, and the assistant should be able to
guide you step by step, even if you've never used Python before.

If you're doing it yourself without an AI assistant, just follow the
steps below in order. They are written for complete beginners — skip
ahead if you already know a step.

---

## Project layout

| File | What it is |
| --- | --- |
| `weight_calculator.py` | The tkinter GUI. Collects the form, displays results. Contains no arithmetic. |
| `calc_core.py` | All the math and every accept/reject decision. Imports no GUI code and does no I/O. |
| `tests/` | Test suite (standard library `unittest`, no pytest needed). |
| `Run Weight Calculator.bat` | Windows double-click launcher. |
| `web/` | Browser version — see [The web version](#the-web-version). |
| `tools/gen_web_fixture.py` | Regenerates the fixture the web version is checked against. |
| `tools/gen_icons.py` | Regenerates the app icons in `web/icons/`. |
| `requirements.txt` | Intentionally empty — see below. |
| `CHANGELOG.md` | Notable changes, newest first. |

The split exists so the calculation logic can be tested on its own, and
so it can be reimplemented for other front-ends without untangling it
from tkinter first.

---

## The web version

`web/index.html` is the same calculator in a browser. **Open it by
double-clicking — there is no build step, no npm, and no server.** It
works from a `file://` path or any static host, and like the desktop app
it sends nothing anywhere and stores nothing.

| File | What it is |
| --- | --- |
| `web/index.html` | The page: markup, styling, and form wiring. |
| `web/calc_core.js` | Port of `calc_core.py`. Same formulas, bounds, validation order, rejection codes, and copy. |
| `web/fixture.js` | Generated expected-output data captured from the Python core. Do not edit by hand. |
| `web/selftest.html` | Open it to check `calc_core.js` against `fixture.js`. |
| `web/manifest.json` | App metadata that makes the page installable. |
| `web/sw.js` | Service worker: offline support for the installed app. |
| `web/icons/` | Generated app icons — regenerate with `tools/gen_icons.py`. |

### Installing it as an app

When the page is served over HTTPS (the GitHub Pages deployment
qualifies), browsers offer to install it as a standalone app — its own
icon and window, no address bar, and it keeps working with no
connection:

- **Chrome / Edge on desktop:** click the install icon at the right
  end of the address bar, or *⋮ menu → Cast, save and share → Install
  page as app*.
- **Android:** Chrome shows an "Install app" banner, or use *⋮ menu →
  Add to Home screen*.
- **iOS / iPadOS:** in Safari, tap *Share → Add to Home Screen*.

The installed app updates itself the next time it is opened with a
connection — the service worker always prefers the network and only
falls back to its cached copy offline, so it can never pin you to a
stale version. Opening `index.html` from a `file://` path is
unaffected: the service worker never registers there, and the page
behaves exactly as before.

The self-test is deliberately excluded from offline support — it is a
development tool, and caching its 1.5 MB fixture would multiply the
installed footprint roughly 30×.

### Verifying the port

The web core is correct exactly insofar as it reproduces `fixture.js`.
Open `web/selftest.html` in a browser; it should report **PASS** with
zero mismatches across ~27,000 checks — every formula, every rejection
message, every rendered results line, and the number-formatting helpers.

If you change `calc_core.py`, regenerate the fixture and re-check:

```bash
python tools/gen_web_fixture.py
```

Then reopen `selftest.html`. A red FAIL with a list of mismatches means
the two implementations have drifted apart.

### Why the core is a separate file

`calc_core.js` is loaded with a `<script src>` rather than pasted inline,
so the app and the self-test run *the same code*. Inlining it would mean
two copies, and a copy that quietly drifts is exactly what the self-test
exists to catch.

### Deploying

`.github/workflows/deploy.yml` publishes `web/` to GitHub Pages on every
push to `main`. A visitor downloads about 50 KB — the page, the core,
and the app manifest and icons. The 1.5 MB `fixture.js` is only fetched
by someone who opens the self-test.

**One-time setup:** in the repository's *Settings → Pages*, set **Source**
to **GitHub Actions**. Until that's done the deploy step fails with a
"Pages is not enabled" error while the verification step still passes.

The workflow refuses to deploy unless the Python suite passes *and*
`web/fixture.js` matches what `calc_core.py` currently produces. That
second check is the point of the pipeline: a stale fixture would leave
the published self-test comparing `calc_core.js` against outdated
expectations, so it could show a confident green PASS while the two
implementations had actually drifted apart.

It also clones with full history, because `tests/test_equivalence.py`
skips rather than fails when the commit it replays isn't reachable — a
shallow clone would turn that test into a silent no-op.

### Differences from the desktop app

Behaviour is identical — same numbers, same refusals. Presentation
differs where the desktop conventions don't suit a web page:

- Errors appear **beside the field** that caused them instead of in a
  modal dialog, and when several numeric fields are wrong at once the
  page marks each one rather than showing a single combined message.
- The results area announces itself to screen readers when it updates.
- The page follows your system light/dark preference.

---

## Requirements

- **Python 3.8 or newer.** This app uses only Python's standard library
  (specifically `tkinter` for the GUI) — there is nothing to install via
  `pip` for the app itself.
- **Tkinter**, which usually comes bundled with Python, but on some Linux
  distributions it needs to be installed separately (see below).

There are no other dependencies, no API keys, and no internet connection
needed to run this app.

---

## Installation & Setup

### Step 1 — Check if Python is already installed

Open a terminal (Command Prompt or PowerShell on Windows, Terminal on
macOS/Linux) and run:

```bash
python3 --version
```

If that doesn't work on Windows, try:

```bash
python --version
```

You should see something like `Python 3.11.4`. If the version is **3.8
or higher**, you're good — skip to Step 3.

If you get an error like "command not found" or "not recognized," you
need to install Python first — go to Step 2.

### Step 2 — Install Python (if needed)

- **Windows:** Download the installer from
  [python.org/downloads](https://www.python.org/downloads/). During
  installation, **check the box that says "Add Python to PATH"** before
  clicking Install — this step trips up most beginners if skipped.
- **macOS:** Download the installer from
  [python.org/downloads](https://www.python.org/downloads/), or if you
  have [Homebrew](https://brew.sh) installed, run `brew install python`.
- **Linux (Debian/Ubuntu and derivatives):**
  ```bash
  sudo apt update
  sudo apt install python3 python3-tk
  ```
- **Linux (Fedora):**
  ```bash
  sudo dnf install python3 python3-tkinter
  ```
- **Linux (Arch):**
  ```bash
  sudo pacman -S python tk
  ```

After installing, close and reopen your terminal, then re-run the Step 1
check.

### Step 3 — Confirm tkinter is available

Run this command:

```bash
python3 -m tkinter
```

A tiny test window should pop up. If it does, close it — you're set. If
you get an error mentioning `tkinter` or `_tkinter`, install it for your
OS:

- **Windows/macOS official installer:** tkinter should already be
  included. If it's missing, reinstall Python from python.org and make
  sure you don't deselect "tcl/tk and IDLE" during install.
- **Debian/Ubuntu:** `sudo apt install python3-tk`
- **Fedora:** `sudo dnf install python3-tkinter`
- **Arch:** `sudo pacman -S tk`

### Step 4 — Get the project files

If you're cloning from GitHub:

```bash
git clone <this-repo-url>
cd <repo-folder-name>
```

Or if you downloaded a ZIP from GitHub, extract it and open a terminal
inside the extracted folder.

### Step 5 — (Optional) Create a virtual environment

Not required since there are no external dependencies, but it's good
practice if you plan to extend the app later:

```bash
python3 -m venv venv
```

Activate it:

- **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
- **Windows (cmd):** `venv\Scripts\activate.bat`
- **macOS/Linux:** `source venv/bin/activate`

### Step 6 — Install dependencies

```bash
pip install -r requirements.txt
```

This will complete instantly and do nothing, since the app has no
external dependencies — `requirements.txt` is included for completeness
and so the project plays nicely with standard tooling.

### Step 7 — Run the app

```bash
python3 weight_calculator.py
```

(On Windows, if `python3` doesn't work, use `python weight_calculator.py`
instead.)

**On Windows you can also just double-click `Run Weight Calculator.bat`**
in the project folder. It finds Python for you and opens the app with no
console window behind it. If Python isn't installed, it says so instead
of flashing and vanishing.

A pastel pink window titled "Weight Goal Calculator" should open.

---

## Running the tests

The test suite uses only the standard library, so if you can run the
app, you can run the tests. From the project folder:

```bash
python3 -m unittest discover -s tests -t .
```

You should see a row of dots and `OK` at the end. For a list of every
test name as it runs, add `-v`.

`tests/test_equivalence.py` compares the current code against an earlier
version of the app pulled from git history. It **skips** rather than
fails if that history isn't available (for example, in a shallow clone
or a plain ZIP download), so `OK` on its own doesn't guarantee it ran —
use `-v` if you want to confirm.

---

## How to use the app

1. Choose your unit system (Imperial or Metric) at the top. Switching
   converts anything you've already typed, so your entries keep meaning
   the same thing.
2. Select your sex — this determines which BMR formula variables are
   used. **Note:** this setting is ignored if you fill in body fat %,
   because the Katch-McArdle formula doesn't use it.
3. Enter your age.
4. Enter your height:
   - **Imperial:** two boxes, feet and inches — for example `5` ft `9`
     in. Leave the inches box blank for a round number of feet. The
     inches box takes 0–11; whole feet belong in the feet box.
   - **Metric:** a single box in centimetres.
5. Enter your current weight and goal weight.
6. **Optional:** enter your body fat percentage if you know it. If you
   leave this blank, the app uses the Mifflin-St Jeor formula. If you
   provide it, the app switches to Katch-McArdle, which can be more
   accurate since it accounts for lean body mass directly.
7. Select your activity level from the dropdown.
8. Enter your target pace — a whole number in the unit you're currently
   using, so `1` means 1 lb per week in Imperial and 1 kg per week in
   Metric. **These are not the same speed:** 1 kg/week is roughly 2.2
   times faster than 1 lb/week, and requires a much larger daily
   deficit.
9. Click **Calculate**.
10. Your results — BMR, TDEE, recommended daily calories, and estimated
    timeline — will appear in the card below the button.

If your goal weight equals your current weight, the app skips the
timeline and simply recommends a maintenance calorie target.

---

## What the calculator will refuse to do

The app declines to generate a plan in these cases. This is deliberate:
producing a confident number outside the range the underlying formulas
are good for would be worse than producing nothing.

| Situation | What happens |
| --- | --- |
| The plan would need **under 1,200 kcal/day** | No plan is generated. The results area explains why and suggests a slower pace. This is a hard stop, not a warning printed under a number. |
| **Age under 18** | Rejected. Mifflin-St Jeor and the activity multipliers are validated for adults; a calculator is the wrong tool for a minor's weight plan. |
| **Goal weight below a BMI of 18.5** | Rejected, with the approximate lowest goal the app will accept at your height. 18.5 is the standard adult underweight threshold. |
| **Inches outside 0–11** | Rejected. If you typed a total (say `65`) into the inches box, the message tells you what that is in feet and inches. |
| Blank or non-numeric entries, or values at or below zero | Rejected with a message naming the problem. |

The 1,200 kcal/day figure is a commonly cited general guideline for
unsupervised dieting, not a personalized medical limit. Clearing it does
not mean a plan is appropriate for you.

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'tkinter'"**
Tkinter isn't installed for your Python. See Step 3 above for OS-specific
fixes.

**The window opens but looks tiny, cut off, or fonts look wrong**
This can happen on some Linux window managers or with display scaling.
Try resizing the window — it's resizable and scrollable. If text is
still cut off, your system's default font set may not include
"Verdana"; the app will fall back to a default system font automatically
on most platforms.

**"command not found: python3" on Windows**
Use `python` instead of `python3`. If neither works, Python wasn't added
to PATH during installation — reinstall Python and check the "Add Python
to PATH" box.

**Nothing happens when I click Calculate**
Check that age, height, current weight, goal weight, and pace are all
filled in with valid numbers (no letters or symbols). In Imperial, the
feet box must have a value — only the inches box may be left blank. Body
fat % is the only fully optional field.

**I switched to Metric and now it says no plan can be generated**
The pace box resets to `1` when you switch units, which means 1 kg per
week — a far larger daily deficit than 1 lb per week. Try a pace of `1`
in Imperial, or accept that a 1 kg/week target is aggressive enough that
many people's numbers fall below the 1,200 kcal floor.

**I get a "Permission denied" error on macOS/Linux**
Try running with `python3 weight_calculator.py` rather than
`./weight_calculator.py`, or make the file executable first:
```bash
chmod +x weight_calculator.py
```

---

## The science, briefly

- **BMR (Mifflin-St Jeor):**
  - Men: `(10 × weight_kg) + (6.25 × height_cm) − (5 × age) + 5`
  - Women: `(10 × weight_kg) + (6.25 × height_cm) − (5 × age) − 161`
- **BMR (Katch-McArdle, used if body fat % is provided):**
  `370 + (21.6 × lean_mass_kg)`, where lean mass = weight × (1 − body
  fat % ÷ 100)
- **TDEE:** `BMR × activity multiplier` (1.2 to 1.9 depending on
  activity level)
- **Calorie target:** TDEE adjusted by a daily surplus/deficit derived
  from your chosen weekly pace, using the common approximation of
  ~7,700 kcal per kilogram of body weight change.

These are population-level estimates. Individual metabolism varies, and
actual results will differ from person to person — this is exactly why
the app is framed as informational rather than prescriptive.

---

## Design decisions and limitations

### Deliberately permissive input bounds

The app is intentionally light on guardrails beyond the ones listed
above. If you are reading the source and these look like oversights,
they aren't — they're chosen, and the tests in
`tests/test_calc_core.py` (see `TestDesignedBounds`) pin them so they
don't drift in either direction.

- **The pace ceiling is 100 per week** in whichever unit is active. The
  1,200 kcal/day floor is the real constraint on weight *loss*; a large
  weight *gain* target will produce a plan without complaint.
- **The pace ceiling is the same number in both unit systems**, so in
  real terms the metric ceiling is roughly 2.2× more permissive. The
  ceiling is a plain entry limit, not a unit-normalized one.
- **The upper age bound is 1000.** Ages far outside the normal adult
  range are caught by the calorie floor rather than by the age check.

The design view is that the 1,200 kcal floor, the BMI floor on goal
weight, and the 18+ age minimum are the limits worth enforcing, and that
past those the tool should do the arithmetic it was asked for rather
than second-guess the person using it. Combined with the disclaimer, the
risk is understood and accepted.

### Limitations of the model itself

- **Timelines assume your maintenance level never changes.** It does —
  TDEE falls as you lose weight, so real-world timelines run longer than
  the estimate. The app says so in its results, but it does not model
  it.
- **Body composition, medical conditions, medications, pregnancy, and
  eating disorder history are not modelled at all** and materially
  change what is safe or appropriate.

---

## License

MIT — see `LICENSE`. Do whatever you want with it, just don't blame the
author if you ignore the disclaimer and something goes sideways.

---

## Disclaimer (again, because it matters)

This software provides general estimates for entertainment and
informational purposes only. It is **not** medical, dietary, or
nutritional advice. It does not account for individual medical
conditions, medications, metabolic disorders, pregnancy, eating disorder
history, or other factors that can significantly change safe and
appropriate calorie targets. Always consult a registered dietitian,
nutritionist, or physician before making changes to your diet, exercise,
or weight management plan.
