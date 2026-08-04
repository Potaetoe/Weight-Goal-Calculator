# Weight Goal Calculator

Estimate your daily calorie needs and get a realistic timeline toward a
weight goal. Nothing to install, no account, no sign-up.

### 👉 [Open the calculator](https://potaetoe.github.io/Weight-Goal-Calculator/)

```
https://potaetoe.github.io/Weight-Goal-Calculator/
```

Works in any browser, on phone, tablet, or computer.

> **This tool is for entertainment and general informational purposes
> only.** It is not medical advice and is not a substitute for guidance
> from a registered dietitian, nutritionist, or physician. Always consult
> a qualified healthcare professional before making changes to your diet
> or exercise routine, especially if you have any underlying health
> conditions.

---

## Your privacy

- **Nothing you enter is sent anywhere.** All the math happens in your
  browser, on your device.
- **Nothing is stored.** No accounts, no history, no cookies for
  tracking. Close the tab and it's gone.
- The only thing the page ever saves is your theme choice (Pink, Light,
  or Dark), and that stays on your device.
- Once loaded, it **works with no internet connection.**

---

## Install it as an app

You can add the calculator to your phone or desktop so it opens from its
own icon, in its own window, with no address bar — and keeps working
offline.

### 👉 [Open the install page](https://potaetoe.github.io/Weight-Goal-Calculator/install.html)

```
https://potaetoe.github.io/Weight-Goal-Calculator/install.html
```

That page has an **Install this app** button where your browser supports
one, and step-by-step instructions where it doesn't. It's also the link
to send to anyone you want to share the app with.

If you'd rather do it manually:

- **iPhone / iPad:** open the site in Safari, tap **Share** → **Add to
  Home Screen**.
- **Android:** Chrome shows an "Install app" banner, or tap **⋮ menu** →
  **Add to Home screen**.
- **Windows / Mac desktop (Chrome or Edge):** click the install icon at
  the right end of the address bar, or **⋮ menu** → **Cast, save and
  share** → **Install page as app**.

No link can install an app by itself — every browser requires you to tap
a button on the page — so the install page is as close to a one-tap
install as browsers allow.

The installed app updates itself the next time you open it with a
connection, so you're never stuck on an old version.

---

## How to use it

1. **Choose your units** — Imperial (lb, ft/in) or Metric (kg, cm) at the
   top. Switching converts anything you've already typed, so your entries
   keep meaning the same thing.
2. **Select your sex.** This picks which BMR formula variables are used.
   *It's ignored if you fill in body fat %*, because that formula doesn't
   use it.
3. **Enter your age** in years.
4. **Enter your height:**
   - *Imperial:* two boxes — feet and inches. For example `5` ft `9` in.
     Leave inches blank for a round number of feet. The inches box takes
     0–11; whole feet belong in the feet box.
   - *Metric:* one box, in centimetres.
5. **Enter your current weight and your goal weight.**
6. **Enter your activity level** from the dropdown:
   - Sedentary (little/no exercise)
   - Lightly active (1–3 days/week)
   - Moderately active (3–5 days/week)
   - Very active (6–7 days/week)
   - Extremely active (physical job + training)
7. **Body fat % — optional.** Leave it blank and the app uses the
   Mifflin-St Jeor formula. Fill it in and it switches to Katch-McArdle,
   which can be more accurate because it works from lean body mass.
8. **Enter your target pace** — a whole number in the unit you're
   currently using. `1` means 1 lb/week in Imperial and 1 kg/week in
   Metric. **These are not the same speed:** 1 kg/week is about 2.2 times
   faster and needs a much bigger daily deficit.
9. **Tap Calculate.**

### Reading your results

The card below the button shows:

- **BMR** — calories your body burns at complete rest.
- **TDEE** — total calories you burn in a day, including activity.
- **Recommended daily calories** — your target to hit the pace you asked
  for.
- **Estimated timeline** — roughly how long the goal will take at that
  pace.

If your goal weight equals your current weight, there's no timeline —
you just get a maintenance calorie target.

### Themes

Three themes, picked from the chips at the top of the page: **Pink**
(deep plum with pink accents), **Light** (linen and sage), and **Dark**.
Your choice is remembered on your device and applies to both the
calculator and the install page.

---

## When it won't give you a plan

Sometimes the app refuses to produce numbers. That's deliberate — a
confident-looking answer outside the range these formulas are good for
would be worse than no answer.

| Situation | What happens |
| --- | --- |
| The plan would need **under 1,200 kcal/day** | No plan. The app explains why and suggests a slower pace. This is a hard stop, not a warning under a number. |
| **Age under 18** | Declined. These formulas are validated for adults; a calculator is the wrong tool for a minor's weight plan. |
| **Goal weight below a BMI of 18.5** | Declined, and it tells you the approximate lowest goal it will accept at your height. 18.5 is the standard adult underweight threshold. |
| **Inches outside 0–11** | Declined. If you typed a total (say `65`) into the inches box, it tells you what that is in feet and inches. |
| Blank, non-numeric, or zero/negative entries | Declined, with a message naming the problem. |

The 1,200 kcal/day figure is a commonly cited general guideline for
unsupervised dieting, not a personalized medical limit. Clearing it does
not mean a plan is appropriate for you.

---

## Troubleshooting

**Nothing happens when I tap Calculate.**
Look for red text beside the fields — that's where the problem is. Age,
height, current weight, goal weight, and pace all need valid numbers. In
Imperial the feet box must have a value; only inches may be blank. Body
fat % is the only fully optional field.

**I switched to Metric and now it says no plan can be generated.**
The pace box resets to `1` when you switch, and 1 kg/week is a far bigger
daily deficit than 1 lb/week. Try `1` in Imperial instead, or accept that
1 kg/week is aggressive enough that many people's numbers land below the
1,200 kcal floor.

**The install button doesn't appear.**
Not every browser offers one. On iPhone and iPad use Safari's **Share →
Add to Home Screen**; on desktop Safari and Firefox, bookmark the page
instead. The install page lists the steps for your browser.

**I don't have a connection.**
If you've installed the app, it still works. If you're just using the
site in a browser tab, you need a connection the first time you load it.

**The page looks stale or is missing something I expected.**
Pull to refresh on mobile, or press Ctrl+Shift+R (Cmd+Shift+R on Mac) on
desktop.

---

## The science, briefly

- **BMR (Mifflin-St Jeor):**
  - Men: `(10 × weight_kg) + (6.25 × height_cm) − (5 × age) + 5`
  - Women: `(10 × weight_kg) + (6.25 × height_cm) − (5 × age) − 161`
- **BMR (Katch-McArdle, used if you give body fat %):**
  `370 + (21.6 × lean_mass_kg)`, where lean mass = weight × (1 − body
  fat % ÷ 100)
- **TDEE:** `BMR × activity multiplier` (1.2 to 1.9)
- **Calorie target:** TDEE adjusted by a daily surplus or deficit from
  your weekly pace, using the common approximation of ~7,700 kcal per
  kilogram of body weight change.

These are population-level estimates. Individual metabolism varies, and
your actual results will differ — which is exactly why this is framed as
informational rather than prescriptive.

### What the numbers don't account for

- **Timelines assume your maintenance level never changes.** It does —
  TDEE falls as you lose weight, so real timelines usually run longer
  than the estimate.
- **Body composition, medical conditions, medications, pregnancy, and
  eating disorder history are not modelled at all**, and they materially
  change what is safe or appropriate for you.

---

## Also available as a desktop app

There's a Python/tkinter version that runs locally on Windows, macOS, and
Linux. It does the same math and makes the same refusals as the web
version. Setup instructions, the project layout, the test suite, and the
deploy pipeline are all in **[README.dev.md](README.dev.md)**.

Recent changes are listed in [CHANGELOG.md](CHANGELOG.md).

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
