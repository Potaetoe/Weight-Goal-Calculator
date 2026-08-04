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
| `requirements.txt` | Intentionally empty — see below. |

The split exists so the calculation logic can be tested on its own, and
so it can be reimplemented for other front-ends without untangling it
from tkinter first.

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

## Known limitations

Honest notes about where the model and the current code fall short.

- **Timelines assume your maintenance level never changes.** It does —
  TDEE falls as you lose weight, so real-world timelines run longer than
  the estimate. The app says so in its results, but it does not model
  it.
- **The pace ceiling is far too permissive.** The app currently accepts
  any whole number up to 100 per week in either unit. For weight loss
  the 1,200 kcal floor blocks the absurd cases as a side effect, but a
  wildly unrealistic *gain* target will produce a plan without
  complaint.
- **The pace ceiling is also unit-dependent in the wrong direction.**
  The limit is the same number in both systems, which means the metric
  ceiling is roughly 2.2 times more permissive in real terms.
- **The upper age bound is 1000**, which is plainly a placeholder. Ages
  far outside the normal adult range produce nonsense that is only
  caught indirectly by the calorie floor.
- **Body composition, medical conditions, medications, pregnancy, and
  eating disorder history are not modelled at all** and materially
  change what is safe or appropriate.

The first item is inherent to the model. The middle three are tracked by
tests in `tests/test_calc_core.py` (see `TestKnownWarts`) so that
changing them is a deliberate decision rather than an accident.

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
