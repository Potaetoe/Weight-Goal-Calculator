#!/usr/bin/env python3
"""
Original-vs-refactored equivalence oracle.

Loads the pre-refactor weight_calculator.py out of git, drives its
`_calculate` with a fake `self` that captures whatever it would have shown
the user, and compares that against the calc_core + _format_plan path over
a large input grid.

This is migration scaffolding, not a permanent test. Its job is to prove
the extraction in step 1 changed nothing. Once the web port is done and
the Tk app is gone, delete this file - the characterization tests in
test_calc_core.py and test_formatting.py are the durable ones.

Skips (rather than fails) when git, the pinned commit, or tkinter isn't
available, so a clone without full history still runs a green suite.

KNOWN INTENTIONAL DIFFERENCES
  1. An unrecognized activity key used to escape as a bare KeyError from
     `ACTIVITY_LEVELS[...]`. It now returns an ACTIVITY_INVALID
     rejection. Unreachable from the readonly dropdown.
  2. Imperial height is now entered as feet + inches rather than total
     inches. The grid below still expresses heights the baseline's way
     and `to_raw_inputs` decomposes them, so equivalent heights must
     still produce identical output. Inputs the baseline cannot express
     at all (e.g. "5 ft 15 in") are covered in test_calc_core.py
     instead - there is nothing here to compare them against.
"""

import importlib.util
import itertools
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The commit holding the pre-refactor single-file implementation.
BASELINE_COMMIT = "38817cea5817d4e6a381b81f2cb458e5a7755f4b"

try:
    from apps.desktop import weight_calculator as new_wc
    from core import calc_core
    HAVE_TK = True
except Exception:  # pragma: no cover - environment dependent
    HAVE_TK = False


def _load_baseline():
    """Fetch and import the pre-refactor module, or return None."""
    try:
        src = subprocess.check_output(
            ["git", "show", "%s:weight_calculator.py" % BASELINE_COMMIT],
            cwd=REPO, stderr=subprocess.DEVNULL,
        ).decode("utf-8")
    except Exception:
        return None

    path = os.path.join(tempfile.mkdtemp(prefix="wgc_baseline_"),
                        "baseline_weight_calculator.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    spec = importlib.util.spec_from_file_location("wgc_baseline", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module


BASELINE = _load_baseline() if HAVE_TK else None


class _Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class _Label:
    def __init__(self):
        self.text = None

    def config(self, text=None, **kw):
        self.text = text


class _CapturingMessagebox:
    def __init__(self):
        self.calls = []

    def showerror(self, title, message):
        self.calls.append((title, message))


class _FakeApp:
    """Stands in for the Tk app so the original _calculate can run
    without a display."""

    def __init__(self, c):
        self.age_entry = _Value(c["age"])
        self.height_entry = _Value(c["height"])
        self.weight_entry = _Value(c["weight"])
        self.goal_entry = _Value(c["goal"])
        self.bodyfat_entry = _Value(c["body_fat"])
        self.pace_entry = _Value(c["pace"])
        self.unit_var = _Value(c["unit"])
        self.sex_var = _Value(c["sex"])
        self.activity_var = _Value(c["activity_key"])
        self.results_label = _Label()


def run_baseline(c):
    mb = _CapturingMessagebox()
    BASELINE.messagebox = mb
    app = _FakeApp(c)
    try:
        BASELINE.WeightCalculatorApp._calculate(app)
    except Exception as e:
        return ("CRASH", type(e).__name__)
    if mb.calls:
        return ("DIALOG",) + mb.calls[0]
    return ("RESULTS", app.results_label.text)


def to_raw_inputs(c):
    """Translate a baseline case (single `height` field) into the current
    RawInputs shape.

    Imperial heights are decomposed into whole feet plus remaining inches,
    which is exactly the same physical height - so any output difference
    is a real regression, not an artifact of the field split. Values that
    don't parse as a number are passed through to height_ft untouched so
    both sides produce the same INVALID_NUMBER rejection.
    """
    height = c["height"]
    if c["unit"] == "imperial":
        try:
            total_in = float(height)
        except ValueError:
            height_cm, height_ft, height_in = "", height, ""
        else:
            feet = int(total_in // 12)
            height_cm = ""
            height_ft = "%g" % feet
            height_in = "%g" % (total_in - feet * 12)
    else:
        height_cm, height_ft, height_in = height, "", ""

    fields = {k: v for k, v in c.items() if k != "height"}
    fields.update(height_cm=height_cm, height_ft=height_ft, height_in=height_in)
    return calc_core.RawInputs(**fields)


def run_refactored(c):
    try:
        outcome = calc_core.calculate_plan(to_raw_inputs(c))
    except Exception as e:
        return ("CRASH", type(e).__name__)
    if not outcome.ok:
        if outcome.code in new_wc.RESULTS_CARD_CODES:
            return ("RESULTS", outcome.message)
        return ("DIALOG", outcome.title, outcome.message)
    return ("RESULTS",
            "\n".join(new_wc.WeightCalculatorApp._format_plan(outcome)))


ACT = list(calc_core.ACTIVITY_LEVELS) if HAVE_TK else []

# `height` is a single field here because that is the baseline's shape;
# to_raw_inputs() splits it for the current core.
BASE = dict(unit="imperial", sex="female", age="30", height="65",
            weight="180", goal="150", body_fat="", activity_key="", pace="1")


def cases():
    for unit, sex, act in itertools.product(
        ["imperial", "metric"], ["female", "male"], [ACT[0], ACT[2], ACT[4]]
    ):
        if unit == "imperial":
            hs, ws, gs = ["65", "70"], ["180", "130"], ["150", "180", "90"]
        else:
            hs, ws, gs = ["165", "178"], ["82", "59"], ["68", "82", "41"]
        for h, w, g, bf, pace in itertools.product(
            hs, ws, gs, ["", "22", "0", "80", "abc"], ["1", "2", "3", "101"]
        ):
            c = dict(BASE)
            c.update(unit=unit, sex=sex, activity_key=act, height=h,
                     weight=w, goal=g, body_fat=bf, pace=pace)
            yield c

    edges = [
        {"age": ""}, {"age": "abc"}, {"age": "0"}, {"age": "-5"},
        {"age": "17"}, {"age": "18"}, {"age": "1000"}, {"age": "1001"},
        {"height": ""}, {"weight": "abc"}, {"goal": "0"}, {"goal": "-1"},
        {"pace": ""}, {"pace": "0"}, {"pace": "-2"}, {"pace": "1.5"},
        {"pace": "100"}, {"pace": "  2  "}, {"body_fat": "  22  "},
        {"body_fat": "75"}, {"body_fat": "74.9"}, {"body_fat": "-1"},
        {"goal": "180"}, {"goal": "180.001"},
        {"weight": "110", "goal": "100", "height": "72"},
        {"age": "80", "weight": "100", "goal": "95", "height": "60",
         "pace": "2"},
        {"unit": "METRIC"}, {"sex": "other"},
    ]
    for e in edges:
        for unit_kw in [
            {},
            {"unit": "metric", "height": "165", "weight": "82", "goal": "68"},
        ]:
            c = dict(BASE, activity_key=ACT[0])
            c.update(unit_kw)
            c.update(e)
            yield c


@unittest.skipUnless(HAVE_TK, "tkinter not available")
@unittest.skipIf(BASELINE is None,
                 "pre-refactor baseline %s not reachable" % BASELINE_COMMIT[:7])
class TestRefactorPreservedBehavior(unittest.TestCase):
    def test_outputs_match_across_input_grid(self):
        compared = 0
        mismatches = []
        for c in cases():
            before, after = run_baseline(c), run_refactored(c)
            if before != after:
                mismatches.append((c, before, after))
            compared += 1

        self.assertGreater(compared, 2000, "grid shrank unexpectedly")

        report = "\n\n".join(
            "INPUT: %r\n  BASELINE: %r\n  CURRENT : %r" % m
            for m in mismatches[:5]
        )
        self.assertEqual(
            mismatches, [],
            "%d of %d cases diverged from the pre-refactor behavior:\n\n%s"
            % (len(mismatches), compared, report),
        )

    def test_activity_key_guard_is_the_only_intended_difference(self):
        c = dict(BASE, activity_key="not a real activity level")
        self.assertEqual(run_baseline(c), ("CRASH", "KeyError"))
        kind, title, message = run_refactored(c)
        self.assertEqual(kind, "DIALOG")
        self.assertEqual(title, "Invalid input")
        self.assertIn("activity level", message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
