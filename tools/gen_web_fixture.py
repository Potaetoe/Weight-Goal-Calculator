#!/usr/bin/env python3
"""
Generate the cross-check fixture for the web port.

Runs calc_core.py over a wide input grid and records what it returned, as
a JavaScript file the self-test page can load over file:// without
tripping CORS (a .json would need fetch()).

The web core is correct exactly insofar as it reproduces this file. Any
divergence is porting drift.

Regenerate after any change to calc_core.py:
    python tools/gen_web_fixture.py
"""

import itertools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import calc_core as core
from calc_core import RawInputs, calculate_plan

# _format_plan is a staticmethod with no widget access, so importing the
# GUI module here costs nothing but the tkinter import.
try:
    from weight_calculator import WeightCalculatorApp
    FORMAT_PLAN = WeightCalculatorApp._format_plan
except Exception:  # pragma: no cover - tkinter missing
    FORMAT_PLAN = None

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "web", "fixture.js")

ACT = list(core.ACTIVITY_LEVELS)

PLAN_FIELDS = ("formula", "bmr", "tdee", "direction", "target_calories",
               "daily_delta", "weeks", "months")


def outcome_to_dict(o):
    if o.ok:
        d = {"ok": True}
        for f in PLAN_FIELDS:
            d[f] = getattr(o, f)
        d["height_cm"] = o.inputs.height_cm
        d["unit_label"] = o.inputs.unit_label
        # The display lines are user-facing copy; pin them too.
        if FORMAT_PLAN is not None:
            d["formatted"] = FORMAT_PLAN(o)
        return d
    return {
        "ok": False,
        "code": o.code,
        "field": o.field,
        "title": o.title,
        "message": o.message,
        "context": dict(o.context),
    }


def plan_cases():
    """Wide sweep plus targeted edges, mirroring the Python suite."""
    seen = set()
    out = []

    def emit(**kw):
        base = dict(
            unit="imperial", sex="female", age="30",
            height_cm="", height_ft="5", height_in="5",
            weight="180", goal="150", body_fat="",
            activity_key=ACT[0], pace="1",
        )
        base.update(kw)
        key = tuple(sorted(base.items()))
        if key in seen:
            return
        seen.add(key)
        out.append(base)

    # --- imperial sweep ---
    for sex, act, ft, inch, w, g, bf, pace in itertools.product(
        ["female", "male"], [ACT[0], ACT[2], ACT[4]],
        ["5", "6"], ["0", "5", "11"], ["180", "130"], ["150", "180", "200"],
        ["", "22"], ["1", "2"],
    ):
        emit(sex=sex, activity_key=act, height_ft=ft, height_in=inch,
             weight=w, goal=g, body_fat=bf, pace=pace)

    # --- metric sweep ---
    for sex, act, cm, w, g, bf, pace in itertools.product(
        ["female", "male"], [ACT[1], ACT[3]],
        ["165", "178", "190"], ["82", "59", "110"], ["68", "82", "95"],
        ["", "30"], ["1", "2"],
    ):
        emit(unit="metric", sex=sex, activity_key=act, height_cm=cm,
             height_ft="", height_in="", weight=w, goal=g,
             body_fat=bf, pace=pace)

    # --- rejection and boundary edges ---
    edges = [
        {"age": ""}, {"age": "abc"}, {"age": "0"}, {"age": "-5"},
        {"age": "17"}, {"age": "18"}, {"age": "1000"}, {"age": "1001"},
        {"age": "999"}, {"age": " 30 "},
        {"height_ft": ""}, {"height_ft": "abc"}, {"height_ft": "0"},
        {"height_ft": "-5"}, {"height_ft": "0", "height_in": "0"},
        {"height_in": ""}, {"height_in": "12"}, {"height_in": "11.99"},
        {"height_in": "15"}, {"height_in": "-3"}, {"height_in": "65"},
        {"height_ft": "0", "height_in": "65"}, {"height_in": "10.5"},
        {"height_in": "abc"},
        {"weight": ""}, {"weight": "abc"}, {"weight": "0"}, {"weight": "-1"},
        {"goal": ""}, {"goal": "0"}, {"goal": "-1"}, {"goal": "180"},
        {"goal": "180.02"}, {"goal": "180.03"}, {"goal": "179.98"},
        {"goal": "90"}, {"goal": "100", "height_ft": "6"},
        {"body_fat": "0"}, {"body_fat": "0.1"}, {"body_fat": "75"},
        {"body_fat": "74.9"}, {"body_fat": "-1"}, {"body_fat": "abc"},
        {"body_fat": "  22  "}, {"body_fat": "50", "goal": "200"},
        {"pace": ""}, {"pace": "abc"}, {"pace": "0"}, {"pace": "-2"},
        {"pace": "1.5"}, {"pace": "100"}, {"pace": "101"}, {"pace": "  2  "},
        {"pace": "10", "goal": "200"}, {"pace": "500"},
        {"activity_key": "nope"}, {"activity_key": ""},
        {"sex": "other"}, {"unit": "METRIC"}, {"unit": ""},
        # non-finite and odd numerics
        {"age": "inf"}, {"age": "nan"}, {"weight": "inf"}, {"goal": "nan"},
        {"height_in": "nan"}, {"height_in": "inf"}, {"height_ft": "1e400"},
        {"body_fat": "nan"}, {"weight": "1e400"},
        # forms where Python's float()/int() disagree with JS Number()
        {"age": "0x10"}, {"weight": "0x10"}, {"height_ft": "0x10"},
        {"pace": "0x10"}, {"body_fat": "0x10"}, {"goal": "0x10"},
        {"age": "1_0"}, {"weight": "1_80"}, {"pace": "1_0"},
        {"age": "Infinity"}, {"age": "INF"}, {"age": "NaN"},
        {"weight": "+180"}, {"pace": "+2"}, {"height_in": "+5"},
        {"age": "1,000"}, {"weight": "180."}, {"goal": ".5"},
        {"pace": "2."}, {"pace": "0b11"}, {"weight": "1e2"},
        # low-TDEE / floor interactions
        {"age": "90", "height_ft": "5", "height_in": "0", "weight": "95",
         "goal": "95"},
        {"age": "90", "height_ft": "5", "height_in": "0", "weight": "95",
         "goal": "90"},
    ]
    for e in edges:
        emit(**e)
        m = dict(unit="metric", height_cm="178", height_ft="", height_in="",
                 weight="95", goal="85", activity_key=ACT[2])
        m.update(e)
        emit(**m)

    return out


def conversion_cases():
    """ft/in <-> cm helpers, which calculate_plan never exercises."""
    ft_in = []
    for feet, inches in itertools.product(
        [0, 4, 5, 6, 7], [0, 0.5, 5, 10.5, 11, 11.99, 12, 15, 65, -3]
    ):
        ft_in.append({
            "feet": feet, "inches": inches,
            "cm": core.ft_in_to_cm(feet, inches),
            "normalized": list(core.normalize_ft_in(feet, inches)),
        })

    cm = []
    values = [30.48, 152.4, 165.1, 178.0, 182.87, 182.88, 190.5, 200.0]
    values += [c + f for c in range(120, 211, 7) for f in (0.0, 0.3, 0.87, 0.99)]
    for v in values:
        feet, inches = core.cm_to_ft_in(v)
        cm.append({"cm": v, "feet": feet, "inches": inches})

    return {"ft_in_to_cm": ft_in, "cm_to_ft_in": cm}


def helper_cases():
    """Direct tests for the Python-compatible number helpers.

    These exist because the plan grid does not exercise them: no input in
    it produces an exact rounding tie, and every value it formats happens
    to render the same under Python and naive JS. Without this section a
    JS port could drop round-half-to-even and :g entirely and still pass.
    """
    round_vals = [
        (0.25, 1), (0.75, 1), (1.25, 1), (2.25, 1), (-0.25, 1), (-1.25, 1),
        (0.5, 0), (1.5, 0), (2.5, 0), (3.5, 0), (-0.5, 0), (-2.5, 0),
        (0.125, 2), (0.375, 2), (1.005, 2), (0.15, 1), (2.675, 2),
        (11.995, 1), (11.95, 1), (0.05, 1), (1234.5, 0), (1235.5, 0),
    ]
    g_vals = [
        0.0, 1.0, 150.0, 180.5, 0.5, -0.5, 123456.0, 1234567.0, 1234567.5,
        999999.0, 1000000.0, 12345678.0, 0.0001, 0.00001, 0.000001,
        0.000012345, 1e-7, 1e20, -1e20, 3.14159265, 100.0, 65.0,
        float("inf"), float("-inf"), float("nan"),
    ]
    fixed_vals = [
        (0.5, 0), (1.5, 0), (2.5, 0), (-0.5, 0), (136.40755165259944, 0),
        (94.7274664254163, 0), (0.04, 1), (0.05, 1), (0.06, 1),
        (float("inf"), 0), (float("-inf"), 0), (float("nan"), 0),
    ]
    thousands_vals = [
        1200.0, 999.4, 999.5, 1000.5, 1234567.0, -1234.6, 0.0, -0.4,
        1537.341266, 1844.8095192, 2933.375, 499.0, 498.951607,
        float("inf"), float("-inf"), float("nan"),
    ]
    return {
        "py_round": [{"x": x, "n": n, "expected": round(x, n)}
                     for x, n in round_vals],
        "fmt_g": [{"x": x, "expected": "%g" % x} for x in g_vals],
        "fmt_fixed": [{"x": x, "n": n, "expected": ("%%.%df" % n) % x}
                      for x, n in fixed_vals],
        "fmt_thousands": [{"x": x, "expected": "{:,.0f}".format(x)}
                          for x in thousands_vals],
    }


def main():
    cases = []
    for raw in plan_cases():
        cases.append({
            "i": raw,
            "o": outcome_to_dict(calculate_plan(RawInputs(**raw))),
        })

    payload = {
        "generated_from": "calc_core.py",
        "activity_levels": core.ACTIVITY_LEVELS,
        "constants": {
            "KG_PER_LB": core.KG_PER_LB,
            "CM_PER_IN": core.CM_PER_IN,
            "IN_PER_FT": core.IN_PER_FT,
            "CAL_PER_KG_FAT": core.CAL_PER_KG_FAT,
            "WEEKS_PER_MONTH": core.WEEKS_PER_MONTH,
            "MAX_PACE_LB": core.MAX_PACE_LB,
            "MAX_PACE_KG": core.MAX_PACE_KG,
            "CALORIE_FLOOR": core.CALORIE_FLOOR,
            "MIN_AGE": core.MIN_AGE,
            "MAX_AGE": core.MAX_AGE,
            "MIN_GOAL_BMI": core.MIN_GOAL_BMI,
        },
        "helpers": helper_cases(),
        "conversions": conversion_cases(),
        "plans": cases,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    body = json.dumps(payload, indent=1, allow_nan=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("// GENERATED by tools/gen_web_fixture.py - do not edit.\n")
        f.write("// Expected outputs captured from calc_core.py.\n")
        f.write("// NaN/Infinity appear bare; this is JS, where they are valid.\n")
        f.write("window.WEB_FIXTURE = ")
        f.write(body)
        f.write(";\n")

    rejected = sum(1 for c in cases if not c["o"]["ok"])
    print("wrote %s" % os.path.relpath(OUT, REPO))
    print("  plan cases   : %d (%d plans, %d rejections)"
          % (len(cases), len(cases) - rejected, rejected))
    print("  ft_in_to_cm  : %d" % len(payload["conversions"]["ft_in_to_cm"]))
    print("  cm_to_ft_in  : %d" % len(payload["conversions"]["cm_to_ft_in"]))
    h = payload["helpers"]
    print("  helpers      : %d" % sum(len(v) for v in h.values()))
    formatted = sum(1 for c in cases if c["o"].get("formatted"))
    print("  formatted    : %d plan renderings" % formatted)
    if not formatted:
        print("  WARNING: no formatted output captured (tkinter missing?)")
    codes = sorted({c["o"]["code"] for c in cases if not c["o"]["ok"]})
    print("  codes covered: %s" % ", ".join(codes))


if __name__ == "__main__":
    main()
