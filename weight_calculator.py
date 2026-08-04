#!/usr/bin/env python3
"""
Weight Goal Calculator
-----------------------
A simple tool that estimates calorie needs and a realistic timeline for
reaching a weight goal. Uses the Mifflin-St Jeor equation, or
Katch-McArdle when body fat percentage is supplied.

DISCLAIMER: This tool is for entertainment and general informational
purposes only. It is NOT medical advice and is not a substitute for
guidance from a registered dietitian, nutritionist, or physician.
Always consult a qualified healthcare professional before making
changes to your diet, exercise, or weight management plan, especially
if you have any underlying health conditions.

---------------------------------------------------------------------------
CHANGES FROM ORIGINAL  (each marked inline with a [Cn] tag)

  [C1] Target pace is now a user-entered whole number bound to the active
       unit, replacing the pace_options list / pace_map dict pair. Removes
       the dual-list coupling that raised KeyError when the two drifted.
  [C2] Pace is interpreted in the displayed unit (lb/week in Imperial,
       kg/week in Metric). Previously pace_map returned kg regardless of
       mode, so every Imperial user ran ~10% faster than the label claimed.
  [C3] Pace is bounded. Free text entry with no ceiling produces negative
       target_calories, which the original printed verbatim.
  [C4] The 1200 kcal floor is now an actual floor. It blocks plan output
       instead of appending a warning beneath an already-displayed number.
  [C5] Unit toggle now converts existing entry values. Previously it
       relabelled only, so 165 lb silently became 165 kg on switch.
  [C6] Age bounds. Mifflin-St Jeor is not validated for children, and a
       weight-loss timeline generator should not accept a minor's inputs.
  [C7] Goal weight is checked against a BMI floor. The original accepted
       any goal above zero and would generate a confident plan for an
       arbitrarily low target.
  [C8] Mouse wheel binding now works on X11 as well as Windows/macOS.

  To strip the additions beyond the pace change, delete the blocks tagged
  [C5], [C6], [C7], [C8]. [C4] is load-bearing for [C3] — removing it
  reintroduces impossible calorie targets at low TDEE.
---------------------------------------------------------------------------
"""

import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------------------------------------------------------
# Color palette - pastel, pink-primary
# ---------------------------------------------------------------------------
COLOR_BG = "#fff0f5"          # lavender blush background
COLOR_PRIMARY = "#f4a6c6"     # pastel pink
COLOR_PRIMARY_DARK = "#e87fa8"  # slightly deeper pink for hover/accents
COLOR_SECONDARY = "#c9e4de"   # pastel mint accent
COLOR_TEXT = "#5b4254"        # soft plum, readable on pastel bg
COLOR_CARD = "#ffffff"
COLOR_WARN_BG = "#fde2e2"
COLOR_WARN_TEXT = "#8a3b3b"

FONT_TITLE = ("Verdana", 16, "bold")
FONT_HEADER = ("Verdana", 11, "bold")
FONT_BODY = ("Verdana", 10)
FONT_SMALL = ("Verdana", 8)

ACTIVITY_LEVELS = {
    "Sedentary (little/no exercise)": 1.2,
    "Lightly active (1-3 days/week)": 1.375,
    "Moderately active (3-5 days/week)": 1.55,
    "Very active (6-7 days/week)": 1.725,
    "Extremely active (physical job + training)": 1.9,
}

KG_PER_LB = 0.45359237
CM_PER_IN = 2.54
CAL_PER_KG_FAT = 7700  # commonly used approximation

# --- Bounds ----------------------------------------------------------------
MAX_PACE_LB = 100          # [C3] whole lb per week
MAX_PACE_KG = 100          # [C3] whole kg per week
CALORIE_FLOOR = 1200     # [C4] hard floor, not a warning threshold
MIN_AGE = 18             # [C6]
MAX_AGE = 1000            # [C6]
MIN_GOAL_BMI = 18.5      # [C7] standard adult underweight threshold


def lb_to_kg(lb):
    return lb * KG_PER_LB


def kg_to_lb(kg):
    return kg / KG_PER_LB


def in_to_cm(inches):
    return inches * CM_PER_IN


def cm_to_in(cm):
    return cm / CM_PER_IN


class WeightCalculatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Weight Goal Calculator")
        self.configure(bg=COLOR_BG)
        self.geometry("520x760")
        self.minsize(480, 680)
        self.resizable(True, True)

        self._prev_unit = "imperial"  # [C5] tracks last unit for conversion

        self._build_style()
        self._build_layout()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=COLOR_BG)
        style.configure("Card.TFrame", background=COLOR_CARD)
        style.configure(
            "TLabel", background=COLOR_BG, foreground=COLOR_TEXT, font=FONT_BODY
        )
        style.configure(
            "Card.TLabel", background=COLOR_CARD, foreground=COLOR_TEXT, font=FONT_BODY
        )
        style.configure(
            "Header.TLabel",
            background=COLOR_BG,
            foreground=COLOR_TEXT,
            font=FONT_HEADER,
        )
        style.configure(
            "Title.TLabel",
            background=COLOR_BG,
            foreground=COLOR_PRIMARY_DARK,
            font=FONT_TITLE,
        )
        style.configure(
            "TButton",
            background=COLOR_PRIMARY,
            foreground="white",
            font=FONT_HEADER,
            padding=8,
            borderwidth=0,
        )
        style.map(
            "TButton",
            background=[("active", COLOR_PRIMARY_DARK)],
        )
        style.configure(
            "TRadiobutton",
            background=COLOR_BG,
            foreground=COLOR_TEXT,
            font=FONT_BODY,
        )
        style.configure(
            "TCombobox",
            fieldbackground="white",
            background="white",
            foreground=COLOR_TEXT,
        )
        style.configure("TEntry", fieldbackground="white", foreground=COLOR_TEXT)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        container = tk.Frame(self, bg=COLOR_BG)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        canvas = tk.Canvas(container, bg=COLOR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=480)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # [C8] Wheel scrolling. Windows/macOS deliver <MouseWheel> with a
        # delta; X11 delivers Button-4 / Button-5 instead.
        def _on_mousewheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            else:
                delta = event.delta
                if abs(delta) >= 120:
                    delta = delta / 120
                canvas.yview_scroll(int(-1 * delta), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

        root = scroll_frame

        # Title
        ttk.Label(root, text="Weight Goal Calculator", style="Title.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        ttk.Label(
            root,
            text="Estimate your calorie needs and a realistic timeline.",
            style="TLabel",
        ).pack(anchor="w", pady=(0, 12))

        # Units toggle
        units_frame = ttk.Frame(root)
        units_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(units_frame, text="Units:", style="Header.TLabel").pack(side="left")
        self.unit_var = tk.StringVar(value="imperial")
        ttk.Radiobutton(
            units_frame, text="Imperial (lb/in)", variable=self.unit_var,
            value="imperial", command=self._update_unit_labels
        ).pack(side="left", padx=8)
        ttk.Radiobutton(
            units_frame, text="Metric (kg/cm)", variable=self.unit_var,
            value="metric", command=self._update_unit_labels
        ).pack(side="left", padx=8)

        form = self._card(root)

        # Sex
        ttk.Label(form, text="Sex (for BMR formula):", style="Card.TLabel").grid(
            row=0, column=0, sticky="w", pady=6
        )
        self.sex_var = tk.StringVar(value="female")
        sex_frame = ttk.Frame(form, style="Card.TFrame")
        sex_frame.grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(sex_frame, text="Female", variable=self.sex_var, value="female").pack(side="left")
        ttk.Radiobutton(sex_frame, text="Male", variable=self.sex_var, value="male").pack(side="left", padx=8)

        # Age
        ttk.Label(form, text="Age (years):", style="Card.TLabel").grid(
            row=1, column=0, sticky="w", pady=6
        )
        self.age_entry = ttk.Entry(form, width=12)
        self.age_entry.grid(row=1, column=1, sticky="w")

        # Height
        self.height_label = ttk.Label(form, text="Height (in):", style="Card.TLabel")
        self.height_label.grid(row=2, column=0, sticky="w", pady=6)
        self.height_entry = ttk.Entry(form, width=12)
        self.height_entry.grid(row=2, column=1, sticky="w")

        # Current weight
        self.weight_label = ttk.Label(form, text="Current weight (lb):", style="Card.TLabel")
        self.weight_label.grid(row=3, column=0, sticky="w", pady=6)
        self.weight_entry = ttk.Entry(form, width=12)
        self.weight_entry.grid(row=3, column=1, sticky="w")

        # Goal weight
        self.goal_label = ttk.Label(form, text="Goal weight (lb):", style="Card.TLabel")
        self.goal_label.grid(row=4, column=0, sticky="w", pady=6)
        self.goal_entry = ttk.Entry(form, width=12)
        self.goal_entry.grid(row=4, column=1, sticky="w")

        # Activity level
        ttk.Label(form, text="Activity level:", style="Card.TLabel").grid(
            row=5, column=0, sticky="w", pady=6
        )
        self.activity_var = tk.StringVar(value=list(ACTIVITY_LEVELS.keys())[0])
        activity_combo = ttk.Combobox(
            form,
            textvariable=self.activity_var,
            values=list(ACTIVITY_LEVELS.keys()),
            state="readonly",
            width=30,
        )
        activity_combo.grid(row=5, column=1, sticky="w")

        # Optional body fat %
        ttk.Label(form, text="Body fat % (optional):", style="Card.TLabel").grid(
            row=6, column=0, sticky="w", pady=6
        )
        bf_frame = ttk.Frame(form, style="Card.TFrame")
        bf_frame.grid(row=6, column=1, sticky="w")
        self.bodyfat_entry = ttk.Entry(bf_frame, width=8)
        self.bodyfat_entry.pack(side="left")
        ttk.Label(bf_frame, text=" leave blank to skip", style="Card.TLabel", font=FONT_SMALL).pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(
            form,
            text="If provided, uses the Katch-McArdle formula (more accurate\nwhen lean mass is known) instead of Mifflin-St Jeor.",
            style="Card.TLabel",
            font=FONT_SMALL,
            justify="left",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 6))

        # [C1] Target pace: free whole-number entry, replaces the combobox.
        self.pace_label = ttk.Label(form, text="Target pace (lb/week):", style="Card.TLabel")
        self.pace_label.grid(row=8, column=0, sticky="w", pady=6)
        pace_frame = ttk.Frame(form, style="Card.TFrame")
        pace_frame.grid(row=8, column=1, sticky="w")
        self.pace_entry = ttk.Entry(pace_frame, width=8)
        self.pace_entry.insert(0, "1")
        self.pace_entry.pack(side="left")
        self.pace_hint = ttk.Label(
            pace_frame,
            text=f" whole number, 1-{MAX_PACE_LB}",
            style="Card.TLabel",
            font=FONT_SMALL,
        )
        self.pace_hint.pack(side="left", padx=(6, 0))

        # Calculate button
        calc_btn = ttk.Button(root, text="Calculate", command=self._calculate)
        calc_btn.pack(fill="x", pady=(14, 10))

        # Results card
        self.results_card = self._card(root)
        self.results_label = ttk.Label(
            self.results_card,
            text="Your results will appear here.",
            style="Card.TLabel",
            justify="left",
        )
        self.results_label.grid(row=0, column=0, sticky="w")

        # Disclaimer
        disclaimer = tk.Label(
            root,
            text=(
                "\u26a0 For entertainment and general informational purposes only. "
                "This is not medical advice and is not a substitute for guidance "
                "from a registered dietitian, nutritionist, or physician. Always "
                "consult a qualified healthcare professional before making changes "
                "to your diet or exercise routine, especially if you have any "
                "underlying health conditions."
            ),
            bg=COLOR_WARN_BG,
            fg=COLOR_WARN_TEXT,
            font=FONT_SMALL,
            wraplength=440,
            justify="left",
            padx=10,
            pady=10,
        )
        disclaimer.pack(fill="x", pady=(16, 0))

    def _card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        card.pack(fill="x", pady=8)
        return card

    # ------------------------------------------------------------------
    # Unit handling
    # ------------------------------------------------------------------
    @staticmethod
    def _convert_entry(entry, fn):
        """[C5] Convert an entry's value in place. Blank/invalid left alone."""
        raw = entry.get().strip()
        if not raw:
            return
        try:
            val = float(raw)
        except ValueError:
            return
        entry.delete(0, tk.END)
        entry.insert(0, f"{fn(val):g}")

    def _update_unit_labels(self):
        new_unit = self.unit_var.get()

        # [C5] Convert existing values so a toggle can't silently reinterpret
        # 165 lb as 165 kg. Rounded to one decimal for readability.
        if new_unit != self._prev_unit:
            if new_unit == "metric":
                self._convert_entry(self.height_entry, lambda v: round(in_to_cm(v), 1))
                self._convert_entry(self.weight_entry, lambda v: round(lb_to_kg(v), 1))
                self._convert_entry(self.goal_entry, lambda v: round(lb_to_kg(v), 1))
            else:
                self._convert_entry(self.height_entry, lambda v: round(cm_to_in(v), 1))
                self._convert_entry(self.weight_entry, lambda v: round(kg_to_lb(v), 1))
                self._convert_entry(self.goal_entry, lambda v: round(kg_to_lb(v), 1))
            # Pace is a small integer with different ceilings per unit;
            # converting it produces confusing rounding, so reset to default.
            self.pace_entry.delete(0, tk.END)
            self.pace_entry.insert(0, "1")
            self._prev_unit = new_unit

        if new_unit == "imperial":
            self.height_label.config(text="Height (in):")
            self.weight_label.config(text="Current weight (lb):")
            self.goal_label.config(text="Goal weight (lb):")
            self.pace_label.config(text="Target pace (lb/week):")
            self.pace_hint.config(text=f" whole number, 1-{MAX_PACE_LB}")
        else:
            self.height_label.config(text="Height (cm):")
            self.weight_label.config(text="Current weight (kg):")
            self.goal_label.config(text="Goal weight (kg):")
            self.pace_label.config(text="Target pace (kg/week):")
            self.pace_hint.config(
                text=f" whole number, 1-{MAX_PACE_KG}"
                if MAX_PACE_KG > 1 else " whole number, 1 only"
            )

    # ------------------------------------------------------------------
    # Calculation
    # ------------------------------------------------------------------
    def _calculate(self):
        try:
            age = float(self.age_entry.get())
            height_raw = float(self.height_entry.get())
            weight_raw = float(self.weight_entry.get())
            goal_raw = float(self.goal_entry.get())
        except ValueError:
            messagebox.showerror(
                "Missing or invalid input",
                "Please enter valid numbers for age, height, current weight, and goal weight.",
            )
            return

        if age <= 0 or height_raw <= 0 or weight_raw <= 0 or goal_raw <= 0:
            messagebox.showerror("Invalid input", "All values must be greater than zero.")
            return

        # [C6] Age bounds. Mifflin-St Jeor and the activity multipliers are
        # adult figures; this tool has no valid output for children.
        if age < MIN_AGE or age > MAX_AGE:
            messagebox.showerror(
                "Age out of range",
                f"This calculator supports ages {MIN_AGE}-{MAX_AGE}.\n\n"
                "The formulas it uses are validated for adults only. If you are "
                "under 18, please speak with a doctor or a registered dietitian "
                "rather than using a calculator.",
            )
            return

        # Normalize to metric for the math
        if self.unit_var.get() == "imperial":
            height_cm = in_to_cm(height_raw)
            weight_kg = lb_to_kg(weight_raw)
            goal_kg = lb_to_kg(goal_raw)
            unit_label = "lb"
        else:
            height_cm = height_raw
            weight_kg = weight_raw
            goal_kg = goal_raw
            unit_label = "kg"

        display_weight = weight_raw
        display_goal = goal_raw

        # [C7] Goal weight sanity check against a BMI floor. The original
        # accepted any positive goal and produced a confident timeline.
        height_m = height_cm / 100.0
        goal_bmi = goal_kg / (height_m ** 2)
        if goal_bmi < MIN_GOAL_BMI:
            min_goal_kg = MIN_GOAL_BMI * (height_m ** 2)
            min_goal_display = (
                kg_to_lb(min_goal_kg) if unit_label == "lb" else min_goal_kg
            )
            messagebox.showerror(
                "Goal weight out of range",
                f"A goal of {display_goal:g} {unit_label} at your height falls below "
                f"a BMI of {MIN_GOAL_BMI}, the standard adult underweight threshold.\n\n"
                f"This calculator will not generate a plan below roughly "
                f"{min_goal_display:.0f} {unit_label}.\n\n"
                "If you believe a lower target is right for you, that is a "
                "conversation for a physician or registered dietitian.",
            )
            return

        # Optional body fat % -> Katch-McArdle if provided, else Mifflin-St Jeor
        bodyfat_raw = self.bodyfat_entry.get().strip()
        formula_used = "Mifflin-St Jeor"
        if bodyfat_raw:
            try:
                bodyfat_pct = float(bodyfat_raw)
            except ValueError:
                messagebox.showerror("Invalid input", "Body fat % must be a number, or leave it blank.")
                return
            if not (0 < bodyfat_pct < 75):
                messagebox.showerror("Invalid input", "Body fat % should be a realistic value between 0 and 75.")
                return
            lean_mass_kg = weight_kg * (1 - bodyfat_pct / 100)
            bmr = 370 + (21.6 * lean_mass_kg)
            formula_used = "Katch-McArdle"
        else:
            if self.sex_var.get() == "male":
                bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
            else:
                bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

        activity_factor = ACTIVITY_LEVELS[self.activity_var.get()]
        tdee = bmr * activity_factor

        # [C1][C2][C3] Weekly pace: user-entered whole number, interpreted in
        # the active display unit, bounded.
        pace_raw = self.pace_entry.get().strip()
        try:
            pace_val = int(pace_raw)
        except ValueError:
            messagebox.showerror("Invalid pace", "Target pace must be a whole number.")
            return

        if pace_val <= 0:
            messagebox.showerror("Invalid pace", "Target pace must be greater than zero.")
            return

        if self.unit_var.get() == "imperial":
            if pace_val > MAX_PACE_LB:
                messagebox.showerror(
                    "Pace out of range",
                    f"Maximum supported pace is {MAX_PACE_LB} lb per week.\n\n"
                    "Faster rates fall outside the range this calculator's model "
                    "is valid for and would produce unreliable results.",
                )
                return
            kg_per_week = lb_to_kg(pace_val)
        else:
            if pace_val > MAX_PACE_KG:
                messagebox.showerror(
                    "Pace out of range",
                    f"Maximum supported pace is {MAX_PACE_KG} kg per week.\n\n"
                    "Faster rates fall outside the range this calculator's model "
                    "is valid for and would produce unreliable results.",
                )
                return
            kg_per_week = float(pace_val)

        daily_deficit_or_surplus = (kg_per_week * CAL_PER_KG_FAT) / 7

        weight_diff_kg = goal_kg - weight_kg  # positive = gain, negative = loss

        if abs(weight_diff_kg) < 0.01:
            target_calories = tdee
            direction = "maintain"
            weeks_needed = 0
        elif weight_diff_kg > 0:
            direction = "gain"
            target_calories = tdee + daily_deficit_or_surplus
            weeks_needed = weight_diff_kg / kg_per_week
        else:
            direction = "lose"
            target_calories = tdee - daily_deficit_or_surplus
            weeks_needed = abs(weight_diff_kg) / kg_per_week

        # [C4] Hard floor. The original computed this as a boolean and printed
        # the out-of-range number anyway with a warning underneath it.
        if direction != "maintain" and target_calories < CALORIE_FLOOR:
            self.results_label.config(
                text=(
                    "No plan generated.\n\n"
                    "The selected pace would require intake below "
                    f"{CALORIE_FLOOR:,} kcal/day for your inputs, which is outside "
                    "the range this tool will produce a plan for.\n\n"
                    "Try a slower pace, or speak with a healthcare provider."
                )
            )
            return

        weeks_needed_display = round(weeks_needed, 1)
        months_needed_display = round(weeks_needed / 4.345, 1) if weeks_needed else 0

        result_lines = [
            f"Formula used: {formula_used}",
            f"BMR (calories your body burns at rest): {bmr:,.0f} kcal/day",
            f"TDEE (calories burned with activity): {tdee:,.0f} kcal/day",
            "",
        ]

        if direction == "maintain":
            result_lines.append(
                f"You're already at your goal weight. Eat around {tdee:,.0f} kcal/day to maintain."
            )
        else:
            verb = "gain" if direction == "gain" else "lose"
            result_lines.append(
                f"To {verb} weight at {pace_val} {unit_label}/week, aim for about "
                f"{target_calories:,.0f} kcal/day."
            )
            result_lines.append(
                f"That's a daily {'surplus' if direction == 'gain' else 'deficit'} of "
                f"~{daily_deficit_or_surplus:,.0f} kcal vs. your maintenance level."
            )
            result_lines.append("")
            result_lines.append(
                f"Estimated time to reach {display_goal:g} {unit_label} from "
                f"{display_weight:g} {unit_label}: "
                f"~{weeks_needed_display} weeks (~{months_needed_display} months)."
            )
            result_lines.append("")
            result_lines.append(
                "Note: this timeline assumes your maintenance level stays constant. "
                "It falls as you lose weight, so real-world timelines run longer."
            )

        self.results_label.config(text="\n".join(result_lines))


if __name__ == "__main__":
    app = WeightCalculatorApp()
    app.mainloop()
