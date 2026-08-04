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

from calc_core import (
    ACTIVITY_LEVELS,
    MAX_PACE_KG,
    MAX_PACE_LB,
    RawInputs,
    calculate_plan,
    cm_to_ft_in,
    ft_in_to_cm,
    kg_to_lb,
    lb_to_kg,
)

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

# Rejection codes the results card renders inline. Everything else is a
# modal error dialog, matching the pre-refactor behavior.
RESULTS_CARD_CODES = {"CALORIE_FLOOR"}


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

        # Height. Two layouts share one grid cell: feet+inches for
        # imperial, a single cm box for metric. _update_unit_labels swaps
        # which one is mapped.
        self.height_label = ttk.Label(form, text="Height:", style="Card.TLabel")
        self.height_label.grid(row=2, column=0, sticky="w", pady=6)

        self.height_imperial_frame = ttk.Frame(form, style="Card.TFrame")
        self.height_imperial_frame.grid(row=2, column=1, sticky="w")
        self.height_ft_entry = ttk.Entry(self.height_imperial_frame, width=4)
        self.height_ft_entry.pack(side="left")
        ttk.Label(
            self.height_imperial_frame, text=" ft ", style="Card.TLabel"
        ).pack(side="left")
        self.height_in_entry = ttk.Entry(self.height_imperial_frame, width=4)
        self.height_in_entry.pack(side="left")
        ttk.Label(
            self.height_imperial_frame, text=" in", style="Card.TLabel"
        ).pack(side="left")

        self.height_metric_frame = ttk.Frame(form, style="Card.TFrame")
        self.height_metric_frame.grid(row=2, column=1, sticky="w")
        self.height_cm_entry = ttk.Entry(self.height_metric_frame, width=8)
        self.height_cm_entry.pack(side="left")
        ttk.Label(
            self.height_metric_frame, text=" cm", style="Card.TLabel"
        ).pack(side="left")

        # Imperial is the startup unit, so hide the metric pair.
        self.height_metric_frame.grid_remove()

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

    @staticmethod
    def _set_entry(entry, text):
        entry.delete(0, tk.END)
        entry.insert(0, text)

    def _height_to_metric(self):
        """[C5] ft+in -> cm. Leaves cm blank if feet is blank/unparseable."""
        try:
            feet = float(self.height_ft_entry.get().strip())
        except ValueError:
            return
        inches_raw = self.height_in_entry.get().strip()
        try:
            inches = float(inches_raw) if inches_raw else 0.0
        except ValueError:
            return
        self._set_entry(
            self.height_cm_entry, f"{round(ft_in_to_cm(feet, inches), 1):g}"
        )

    def _height_to_imperial(self):
        """[C5] cm -> ft+in, with the 12-inch carry handled in the core."""
        try:
            cm = float(self.height_cm_entry.get().strip())
        except ValueError:
            return
        feet, inches = cm_to_ft_in(cm)
        self._set_entry(self.height_ft_entry, f"{feet:g}")
        self._set_entry(self.height_in_entry, f"{inches:g}")

    def _update_unit_labels(self):
        new_unit = self.unit_var.get()

        # [C5] Convert existing values so a toggle can't silently reinterpret
        # 165 lb as 165 kg. Rounded to one decimal for readability.
        if new_unit != self._prev_unit:
            if new_unit == "metric":
                self._height_to_metric()
                self._convert_entry(self.weight_entry, lambda v: round(lb_to_kg(v), 1))
                self._convert_entry(self.goal_entry, lambda v: round(lb_to_kg(v), 1))
                self.height_imperial_frame.grid_remove()
                self.height_metric_frame.grid()
            else:
                self._height_to_imperial()
                self._convert_entry(self.weight_entry, lambda v: round(kg_to_lb(v), 1))
                self._convert_entry(self.goal_entry, lambda v: round(kg_to_lb(v), 1))
                self.height_metric_frame.grid_remove()
                self.height_imperial_frame.grid()
            # Pace is a small integer with different ceilings per unit;
            # converting it produces confusing rounding, so reset to default.
            self.pace_entry.delete(0, tk.END)
            self.pace_entry.insert(0, "1")
            self._prev_unit = new_unit

        if new_unit == "imperial":
            self.weight_label.config(text="Current weight (lb):")
            self.goal_label.config(text="Goal weight (lb):")
            self.pace_label.config(text="Target pace (lb/week):")
            self.pace_hint.config(text=f" whole number, 1-{MAX_PACE_LB}")
        else:
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
        """Collect the form, hand it to the core, present what comes back.

        All arithmetic and every accept/reject decision lives in
        calc_core.calculate_plan. This method only moves values in and
        renders values out.
        """
        outcome = calculate_plan(
            RawInputs(
                unit=self.unit_var.get(),
                sex=self.sex_var.get(),
                age=self.age_entry.get(),
                height_cm=self.height_cm_entry.get(),
                height_ft=self.height_ft_entry.get(),
                height_in=self.height_in_entry.get(),
                weight=self.weight_entry.get(),
                goal=self.goal_entry.get(),
                body_fat=self.bodyfat_entry.get(),
                activity_key=self.activity_var.get(),
                pace=self.pace_entry.get(),
            )
        )

        if not outcome.ok:
            if outcome.code in RESULTS_CARD_CODES:
                self.results_label.config(text=outcome.message)
            else:
                messagebox.showerror(outcome.title, outcome.message)
            return

        self.results_label.config(text="\n".join(self._format_plan(outcome)))

    # ------------------------------------------------------------------
    # Presentation
    # ------------------------------------------------------------------
    @staticmethod
    def _format_plan(plan):
        """Turn a Plan into display lines. Pure formatting, no math."""
        unit_label = plan.inputs.unit_label

        lines = [
            f"Formula used: {plan.formula}",
            f"BMR (calories your body burns at rest): {plan.bmr:,.0f} kcal/day",
            f"TDEE (calories burned with activity): {plan.tdee:,.0f} kcal/day",
            "",
        ]

        if plan.direction == "maintain":
            lines.append(
                f"You're already at your goal weight. Eat around "
                f"{plan.tdee:,.0f} kcal/day to maintain."
            )
            return lines

        verb = "gain" if plan.direction == "gain" else "lose"
        noun = "surplus" if plan.direction == "gain" else "deficit"
        lines.append(
            f"To {verb} weight at {plan.inputs.pace} {unit_label}/week, aim for about "
            f"{plan.target_calories:,.0f} kcal/day."
        )
        lines.append(
            f"That's a daily {noun} of "
            f"~{plan.daily_delta:,.0f} kcal vs. your maintenance level."
        )
        lines.append("")
        lines.append(
            f"Estimated time to reach {plan.inputs.goal:g} {unit_label} from "
            f"{plan.inputs.weight:g} {unit_label}: "
            f"~{round(plan.weeks, 1)} weeks (~{round(plan.months, 1)} months)."
        )
        lines.append("")
        lines.append(
            "Note: this timeline assumes your maintenance level stays constant. "
            "It falls as you lose weight, so real-world timelines run longer."
        )
        return lines


if __name__ == "__main__":
    app = WeightCalculatorApp()
    app.mainloop()
