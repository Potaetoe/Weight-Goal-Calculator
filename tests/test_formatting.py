#!/usr/bin/env python3
"""
Characterization tests for the presentation layer.

`WeightCalculatorApp._format_plan` is a staticmethod that takes a Plan and
returns display lines - no widgets, no window, no mainloop. That makes the
user-visible copy testable without a display.

These strings are the contract a web port has to reproduce, which is the
main reason they're pinned this precisely.

Skipped entirely if tkinter is unavailable (importing weight_calculator
pulls it in), so the suite still runs on a headless box.
"""

import inspect
import re
import unittest

import core.calc_core as core
from core.calc_core import RawInputs, calculate_plan

try:
    from apps.desktop import weight_calculator as wc
    HAVE_TK = True
except Exception:  # pragma: no cover - environment dependent
    HAVE_TK = False

ACT = list(core.ACTIVITY_LEVELS)


def declared_rejection_codes():
    """Every rejection code calc_core can return, read out of its source.

    Derived rather than listed, because a hand-maintained list has the
    exact staleness problem it would be there to prevent: someone adds a
    Rejection and forgets to update it. The `code="..."` literals are the
    one place that cannot fall out of sync with the code.

    If the source ever stops spelling codes as double-quoted literals,
    this returns an empty set and the routing test below fails loudly
    rather than quietly checking nothing.
    """
    return set(re.findall(r'code="([A-Z_]+)"', inspect.getsource(core)))


def plan(**overrides):
    base = dict(
        unit="imperial", sex="female", age="30",
        height_cm="", height_ft="5", height_in="5",
        weight="180", goal="150", body_fat="", activity_key=ACT[0], pace="1",
    )
    base.update(overrides)
    outcome = calculate_plan(RawInputs(**base))
    assert outcome.ok, "fixture should produce a plan, got %r" % (outcome,)
    return outcome


@unittest.skipUnless(HAVE_TK, "tkinter not available")
class TestFormatPlan(unittest.TestCase):
    def test_loss_output(self):
        self.assertEqual(
            wc.WeightCalculatorApp._format_plan(plan()),
            [
                "Formula used: Mifflin-St Jeor",
                "BMR (calories your body burns at rest): 1,537 kcal/day",
                "TDEE (calories burned with activity): 1,845 kcal/day",
                "",
                "To lose weight at 1 lb/week, aim for about 1,346 kcal/day.",
                "That's a daily deficit of ~499 kcal vs. your maintenance level.",
                "",
                "Estimated time to reach 150 lb from 180 lb: "
                "~30.0 weeks (~6.9 months).",
                "",
                "Note: this timeline assumes your maintenance level stays "
                "constant. It falls as you lose weight, so real-world "
                "timelines run longer.",
            ],
        )

    def test_gain_uses_surplus_wording(self):
        lines = wc.WeightCalculatorApp._format_plan(plan(goal="200"))
        self.assertIn("To gain weight at 1 lb/week", lines[4])
        self.assertIn("daily surplus of", lines[5])

    def test_maintain_output_is_short(self):
        lines = wc.WeightCalculatorApp._format_plan(plan(goal="180"))
        self.assertEqual(len(lines), 5)
        self.assertEqual(
            lines[4],
            "You're already at your goal weight. Eat around 1,845 kcal/day "
            "to maintain.",
        )
        # No timeline block when maintaining.
        self.assertFalse(any("Estimated time" in ln for ln in lines))

    def test_metric_labels(self):
        lines = wc.WeightCalculatorApp._format_plan(
            plan(unit="metric", age="35", height_cm="178", weight="95",
                 goal="85", sex="male", activity_key=ACT[2])
        )
        self.assertIn("1 kg/week", lines[4])
        self.assertIn("to reach 85 kg from 95 kg", lines[7])

    def test_katch_mcardle_is_named_in_output(self):
        lines = wc.WeightCalculatorApp._format_plan(plan(body_fat="22"))
        self.assertEqual(lines[0], "Formula used: Katch-McArdle")

    def test_thousands_separators_and_rounding(self):
        # kcal figures use `,.0f`; weeks/months use round(x, 1).
        lines = wc.WeightCalculatorApp._format_plan(
            plan(unit="metric", age="35", height_cm="178", weight="95",
                 goal="85", sex="male", activity_key=ACT[2])
        )
        self.assertIn("2,933 kcal/day", lines[2])
        self.assertIn("~10.0 weeks (~2.3 months)", lines[7])

    def test_goal_and_weight_use_general_format(self):
        # `:g` drops trailing zeros: 150.0 renders as "150", not "150.0".
        lines = wc.WeightCalculatorApp._format_plan(plan(goal="150.0"))
        self.assertIn("to reach 150 lb from 180 lb", lines[7])

    def test_blank_line_positions(self):
        lines = wc.WeightCalculatorApp._format_plan(plan())
        self.assertEqual([i for i, ln in enumerate(lines) if ln == ""], [3, 6, 8])


@unittest.skipUnless(HAVE_TK, "tkinter not available")
class TestRejectionRouting(unittest.TestCase):
    """Which rejections render inline vs. as a modal dialog."""

    def test_only_calorie_floor_renders_in_the_results_card(self):
        self.assertEqual(wc.RESULTS_CARD_CODES, {"CALORIE_FLOOR"})

    def test_every_other_code_routes_to_a_dialog(self):
        seen = set()
        for kw in [{"age": "abc"}, {"age": "0"}, {"age": "17"},
                   {"height_ft": "6", "goal": "100"}, {"height_in": "15"},
                   {"body_fat": "abc"}, {"body_fat": "80"}, {"pace": "abc"},
                   {"pace": "0"}, {"pace": "101"}, {"activity_key": "nope"}]:
            base = dict(
                unit="imperial", sex="female", age="30",
                height_cm="", height_ft="5", height_in="5",
                weight="180", goal="150", body_fat="", activity_key=ACT[0],
                pace="1",
            )
            base.update(kw)
            outcome = calculate_plan(RawInputs(**base))
            self.assertFalse(outcome.ok)
            self.assertNotIn(outcome.code, wc.RESULTS_CARD_CODES)
            seen.add(outcome.code)

        # The actual guard: every code calc_core declares has to be
        # accounted for, either by an input above that provokes it (and
        # is therefore checked to route to a dialog) or by the inline
        # set. Add a rejection to calc_core without deciding how it
        # reaches the user and this fails, naming the orphan.
        declared = declared_rejection_codes()
        routed = seen | wc.RESULTS_CARD_CODES
        self.assertEqual(
            routed, declared,
            "rejection codes with no routing decision: %s; "
            "codes routed but no longer in calc_core: %s"
            % (sorted(declared - routed) or "none",
               sorted(routed - declared) or "none"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
