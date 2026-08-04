#!/usr/bin/env python3
"""
Weight Goal Calculator - pure calculation core
----------------------------------------------
No UI, no I/O, no imports beyond the standard library's typing helpers.
Every function here is deterministic: same inputs, same outputs, no side
effects. This is what makes the logic testable, and what a future web
port re-implements.

The single entry point is `calculate_plan(RawInputs) -> Plan | Rejection`.
Failures are returned as data (`Rejection`), never raised and never
displayed - the caller decides how to present them.

DISCLAIMER: This tool is for entertainment and general informational
purposes only. It is NOT medical advice. See README.md.

---------------------------------------------------------------------------
NOTE ON VALIDATION ORDER

`calculate_plan` parses and validates in a single pass, in the exact order
the original UI did. That order is load-bearing: body fat is parsed after
the goal-BMI check, and pace after that. Reordering into a clean
parse-then-validate split would change which error a user sees when more
than one field is wrong. If you want that split, make it a deliberate
change with tests, not a side effect of refactoring.
---------------------------------------------------------------------------
"""

import math
from dataclasses import dataclass, field
from typing import Mapping, Optional, Union

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ACTIVITY_LEVELS = {
    "Sedentary (little/no exercise)": 1.2,
    "Lightly active (1-3 days/week)": 1.375,
    "Moderately active (3-5 days/week)": 1.55,
    "Very active (6-7 days/week)": 1.725,
    "Extremely active (physical job + training)": 1.9,
}

KG_PER_LB = 0.45359237
CM_PER_IN = 2.54
IN_PER_FT = 12
CAL_PER_KG_FAT = 7700  # commonly used approximation
WEEKS_PER_MONTH = 4.345

# --- Bounds ----------------------------------------------------------------
MAX_PACE_LB = 100          # [C3] whole lb per week
MAX_PACE_KG = 100          # [C3] whole kg per week
CALORIE_FLOOR = 1200     # [C4] hard floor, not a warning threshold
MIN_AGE = 18             # [C6]
MAX_AGE = 1000            # [C6]
MIN_GOAL_BMI = 18.5      # [C7] standard adult underweight threshold

IMPERIAL = "imperial"
METRIC = "metric"


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------
def lb_to_kg(lb):
    return lb * KG_PER_LB


def kg_to_lb(kg):
    return kg / KG_PER_LB


def in_to_cm(inches):
    return inches * CM_PER_IN


def cm_to_in(cm):
    return cm / CM_PER_IN


def ft_in_to_cm(feet, inches):
    """Feet + inches -> centimetres. Inches may be fractional (5 ft 10.5 in)."""
    return in_to_cm(feet * IN_PER_FT + inches)


def cm_to_ft_in(cm, inch_decimals=1):
    """Centimetres -> (whole feet, inches), rounded for display.

    Rounding happens here, not at the call site, because rounding inches
    independently can produce 12 (e.g. 182.87 cm -> 5 ft 12.0 in). This
    carries that into the feet component so the pair is always valid.
    """
    total_inches = cm_to_in(cm)
    feet = int(total_inches // IN_PER_FT)
    inches = round(total_inches - feet * IN_PER_FT, inch_decimals)
    if inches >= IN_PER_FT:
        feet += 1
        inches = round(inches - IN_PER_FT, inch_decimals)
    return feet, inches


def normalize_ft_in(feet, inches):
    """Fold an overflowing inches value into feet: (5, 15) -> (6, 3)."""
    total_inches = feet * IN_PER_FT + inches
    whole_feet = int(total_inches // IN_PER_FT)
    return whole_feet, total_inches - whole_feet * IN_PER_FT


# ---------------------------------------------------------------------------
# Formulas
# ---------------------------------------------------------------------------
def bmr_mifflin_st_jeor(weight_kg, height_cm, age, sex):
    """Mifflin-St Jeor. `sex` is "male" or anything else (treated female)."""
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    return base + 5 if sex == "male" else base - 161


def bmr_katch_mcardle(weight_kg, body_fat_pct):
    """Katch-McArdle, driven by lean mass. Sex-independent by design."""
    lean_mass_kg = weight_kg * (1 - body_fat_pct / 100)
    return 370 + (21.6 * lean_mass_kg)


def tdee_from_bmr(bmr, activity_factor):
    return bmr * activity_factor


def bmi(weight_kg, height_cm):
    height_m = height_cm / 100.0
    return weight_kg / (height_m ** 2)


def weight_for_bmi(target_bmi, height_cm):
    height_m = height_cm / 100.0
    return target_bmi * (height_m ** 2)


def daily_calorie_delta(kg_per_week):
    """Daily surplus/deficit implied by a weekly rate of change."""
    return (kg_per_week * CAL_PER_KG_FAT) / 7


# ---------------------------------------------------------------------------
# Input / output types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RawInputs:
    """Unparsed form values, exactly as a UI would hand them over.

    Height arrives in whichever pair of fields the active unit uses:
    `height_cm` in metric, `height_ft` + `height_in` in imperial. The
    unused field(s) are ignored rather than validated, so a UI can leave
    stale text in a hidden widget without consequence.
    """
    unit: str            # "imperial" | "metric"
    sex: str             # "male" | "female"
    age: str
    height_cm: str       # metric only
    height_ft: str       # imperial only
    height_in: str       # imperial only; blank is treated as 0
    weight: str
    goal: str
    body_fat: str        # blank means "skip, use Mifflin-St Jeor"
    activity_key: str    # a key of ACTIVITY_LEVELS
    pace: str


@dataclass(frozen=True)
class Inputs:
    """Parsed, validated inputs.

    Weight and goal are kept in *display* units with metric properties
    deriving what the math needs. Height is the exception: it is stored
    canonically as `height_cm` because imperial height has two display
    components, with `height_ft`/`height_in` carried alongside purely so a
    UI can round-trip the form. Both are None in metric.
    """
    unit: str
    sex: str
    age: float
    height_cm: float
    height_ft: Optional[float]
    height_in: Optional[float]
    weight: float
    goal: float
    body_fat_pct: Optional[float]
    activity_key: str
    pace: int

    @property
    def is_imperial(self):
        return self.unit == IMPERIAL

    @property
    def unit_label(self):
        return "lb" if self.is_imperial else "kg"

    @property
    def weight_kg(self):
        return lb_to_kg(self.weight) if self.is_imperial else self.weight

    @property
    def goal_kg(self):
        return lb_to_kg(self.goal) if self.is_imperial else self.goal

    @property
    def pace_kg_per_week(self):
        # [C2] Pace is interpreted in the displayed unit.
        return lb_to_kg(self.pace) if self.is_imperial else float(self.pace)

    @property
    def activity_factor(self):
        return ACTIVITY_LEVELS[self.activity_key]


@dataclass(frozen=True)
class Plan:
    """A successful calculation. Numbers only - formatting is the UI's job."""
    inputs: Inputs
    formula: str                 # "Mifflin-St Jeor" | "Katch-McArdle"
    bmr: float
    tdee: float
    direction: str               # "gain" | "lose" | "maintain"
    target_calories: float
    daily_delta: float           # magnitude of the surplus/deficit
    weeks: float                 # 0 when maintaining
    months: float

    ok = True


@dataclass(frozen=True)
class Rejection:
    """A refusal to produce a plan, as data.

    `code` is the stable identifier to branch on. `title`/`message` are
    default copy a caller may use or ignore; `context` carries the numbers
    embedded in that copy so tests and alternate UIs don't parse strings.
    """
    code: str
    field: str
    title: str
    message: str
    context: Mapping[str, float] = field(default_factory=dict)

    ok = False


Outcome = Union[Plan, Rejection]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def calculate_plan(raw):
    """Parse, validate, and compute. Returns a Plan or a Rejection.

    See the module docstring: the validation order here mirrors the
    original UI exactly and should not be rearranged casually.
    """
    # --- Core numerics ----------------------------------------------------
    is_imperial = raw.unit == IMPERIAL

    try:
        age = float(raw.age)
        weight = float(raw.weight)
        goal = float(raw.goal)
        if is_imperial:
            # Blank inches means a round number of feet, which is a normal
            # thing to type. Blank feet is not - that's a missing input.
            height_ft = float(raw.height_ft)
            height_in = float(raw.height_in) if raw.height_in.strip() else 0.0
            height_cm = ft_in_to_cm(height_ft, height_in)
        else:
            height_ft = height_in = None
            height_cm = float(raw.height_cm)
    except ValueError:
        return Rejection(
            code="INVALID_NUMBER",
            field="age",
            title="Missing or invalid input",
            message=(
                "Please enter valid numbers for age, height, current weight, "
                "and goal weight."
            ),
        )

    if age <= 0 or height_cm <= 0 or weight <= 0 or goal <= 0:
        return Rejection(
            code="NON_POSITIVE",
            field="age",
            title="Invalid input",
            message="All values must be greater than zero.",
        )

    # Inches is a component, not a total: 0-11.99, with 12 rolling into
    # the feet field. Rejected rather than silently normalized, so "5 ft
    # 65 in" can't quietly become 10 ft 5 in behind the user's back.
    if is_imperial and not (0 <= height_in < IN_PER_FT):
        message = (
            f"The inches box takes 0 to {IN_PER_FT - 1}; whole feet go in "
            f"the feet box."
        )
        context = {"height_ft": height_ft, "height_in": height_in}
        # Only normalize when there is a real overflow to fold in. A
        # negative has no useful suggestion, and nan/inf can't be folded
        # at all - normalize_ft_in would raise on int(nan).
        if height_in >= IN_PER_FT and math.isfinite(height_ft + height_in):
            norm_ft, norm_in = normalize_ft_in(height_ft, height_in)
            message += (
                f"\n\n{height_ft:g} ft {height_in:g} in is "
                f"{norm_ft:g} ft {norm_in:g} in."
            )
            context["suggested_ft"] = norm_ft
            context["suggested_in"] = norm_in
        return Rejection(
            code="HEIGHT_INCHES_RANGE",
            field="height_in",
            title="Inches out of range",
            message=message,
            context=context,
        )

    # [C6] Age bounds. Mifflin-St Jeor and the activity multipliers are
    # adult figures; this tool has no valid output for children.
    if age < MIN_AGE or age > MAX_AGE:
        return Rejection(
            code="AGE_RANGE",
            field="age",
            title="Age out of range",
            message=(
                f"This calculator supports ages {MIN_AGE}-{MAX_AGE}.\n\n"
                "The formulas it uses are validated for adults only. If you are "
                "under 18, please speak with a doctor or a registered dietitian "
                "rather than using a calculator."
            ),
            context={"min_age": MIN_AGE, "max_age": MAX_AGE},
        )

    unit_label = "lb" if is_imperial else "kg"
    weight_kg = lb_to_kg(weight) if is_imperial else weight
    goal_kg = lb_to_kg(goal) if is_imperial else goal

    # [C7] Goal weight sanity check against a BMI floor.
    goal_bmi = bmi(goal_kg, height_cm)
    if goal_bmi < MIN_GOAL_BMI:
        min_goal_kg = weight_for_bmi(MIN_GOAL_BMI, height_cm)
        min_goal_display = kg_to_lb(min_goal_kg) if is_imperial else min_goal_kg
        return Rejection(
            code="GOAL_BMI",
            field="goal",
            title="Goal weight out of range",
            message=(
                f"A goal of {goal:g} {unit_label} at your height falls below "
                f"a BMI of {MIN_GOAL_BMI}, the standard adult underweight "
                f"threshold.\n\n"
                f"This calculator will not generate a plan below roughly "
                f"{min_goal_display:.0f} {unit_label}.\n\n"
                "If you believe a lower target is right for you, that is a "
                "conversation for a physician or registered dietitian."
            ),
            context={
                "goal_bmi": goal_bmi,
                "min_goal_bmi": MIN_GOAL_BMI,
                "min_goal_kg": min_goal_kg,
                "min_goal_display": min_goal_display,
            },
        )

    # --- Optional body fat % -> chooses the BMR formula -------------------
    body_fat_raw = raw.body_fat.strip()
    body_fat_pct = None
    if body_fat_raw:
        try:
            body_fat_pct = float(body_fat_raw)
        except ValueError:
            return Rejection(
                code="BODY_FAT_INVALID",
                field="body_fat",
                title="Invalid input",
                message="Body fat % must be a number, or leave it blank.",
            )
        if not (0 < body_fat_pct < 75):
            return Rejection(
                code="BODY_FAT_RANGE",
                field="body_fat",
                title="Invalid input",
                message=(
                    "Body fat % should be a realistic value between 0 and 75."
                ),
            )
        formula = "Katch-McArdle"
        bmr = bmr_katch_mcardle(weight_kg, body_fat_pct)
    else:
        formula = "Mifflin-St Jeor"
        bmr = bmr_mifflin_st_jeor(weight_kg, height_cm, age, raw.sex)

    # Unreachable from a readonly dropdown, but a bad key would otherwise
    # surface as a raw KeyError from deep inside the math.
    if raw.activity_key not in ACTIVITY_LEVELS:
        return Rejection(
            code="ACTIVITY_INVALID",
            field="activity_key",
            title="Invalid input",
            message="Please choose an activity level from the list.",
        )

    tdee = tdee_from_bmr(bmr, ACTIVITY_LEVELS[raw.activity_key])

    # --- [C1][C2][C3] Weekly pace ----------------------------------------
    try:
        pace = int(raw.pace.strip())
    except ValueError:
        return Rejection(
            code="PACE_INVALID",
            field="pace",
            title="Invalid pace",
            message="Target pace must be a whole number.",
        )

    if pace <= 0:
        return Rejection(
            code="PACE_NON_POSITIVE",
            field="pace",
            title="Invalid pace",
            message="Target pace must be greater than zero.",
        )

    max_pace = MAX_PACE_LB if is_imperial else MAX_PACE_KG
    if pace > max_pace:
        return Rejection(
            code="PACE_RANGE",
            field="pace",
            title="Pace out of range",
            message=(
                f"Maximum supported pace is {max_pace} {unit_label} per week.\n\n"
                "Faster rates fall outside the range this calculator's model "
                "is valid for and would produce unreliable results."
            ),
            context={"max_pace": max_pace},
        )

    kg_per_week = lb_to_kg(pace) if is_imperial else float(pace)
    daily_delta = daily_calorie_delta(kg_per_week)

    # --- Direction, target, timeline --------------------------------------
    weight_diff_kg = goal_kg - weight_kg  # positive = gain, negative = loss

    if abs(weight_diff_kg) < 0.01:
        direction = "maintain"
        target_calories = tdee
        weeks = 0.0
    elif weight_diff_kg > 0:
        direction = "gain"
        target_calories = tdee + daily_delta
        weeks = weight_diff_kg / kg_per_week
    else:
        direction = "lose"
        target_calories = tdee - daily_delta
        weeks = abs(weight_diff_kg) / kg_per_week

    # [C4] Hard floor. Blocks the plan rather than annotating it.
    if direction != "maintain" and target_calories < CALORIE_FLOOR:
        return Rejection(
            code="CALORIE_FLOOR",
            field="pace",
            title="No plan generated",
            message=(
                "No plan generated.\n\n"
                "The selected pace would require intake below "
                f"{CALORIE_FLOOR:,} kcal/day for your inputs, which is outside "
                "the range this tool will produce a plan for.\n\n"
                "Try a slower pace, or speak with a healthcare provider."
            ),
            context={
                "calorie_floor": CALORIE_FLOOR,
                "target_calories": target_calories,
                "tdee": tdee,
            },
        )

    return Plan(
        inputs=Inputs(
            unit=raw.unit,
            sex=raw.sex,
            age=age,
            height_cm=height_cm,
            height_ft=height_ft,
            height_in=height_in,
            weight=weight,
            goal=goal,
            body_fat_pct=body_fat_pct,
            activity_key=raw.activity_key,
            pace=pace,
        ),
        formula=formula,
        bmr=bmr,
        tdee=tdee,
        direction=direction,
        target_calories=target_calories,
        daily_delta=daily_delta,
        weeks=weeks,
        months=weeks / WEEKS_PER_MONTH,
    )
