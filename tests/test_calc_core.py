#!/usr/bin/env python3
"""
Characterization tests for calc_core.

These PIN CURRENT BEHAVIOR. Some of it is deliberately permissive by
product decision rather than by accident - see TestDesignedBounds, which
locks those choices down so that changing them has to be a decision
someone makes on purpose, with a failing test to acknowledge.

Expected numbers are hard-coded golden values, not re-derivations of the
formulas. A test that recomputes `10*w + 6.25*h - 5*a + 5` and compares
it to the implementation of `10*w + 6.25*h - 5*a + 5` proves nothing.

Run from the repo root:
    python -m unittest discover -s tests -t .

Stdlib only - no pytest, matching the project's zero-dependency stance.
"""

import itertools
import unittest

import core.calc_core as core
from core.calc_core import Plan, RawInputs, Rejection, calculate_plan

ACT = list(core.ACTIVITY_LEVELS)
SEDENTARY = ACT[0]        # 1.2
MODERATE = ACT[2]         # 1.55


def raw(**overrides):
    """A valid imperial baseline: 30f, 5'5", 180lb -> 150lb at 1 lb/week.

    5 ft 5 in is 65 in, the height this fixture used before height was
    split into two fields - so the golden BMR/TDEE values below are
    unchanged by that split, which is the point.
    """
    base = dict(
        unit="imperial", sex="female", age="30",
        height_cm="", height_ft="5", height_in="5",
        weight="180", goal="150", body_fat="", activity_key=SEDENTARY,
        pace="1",
    )
    base.update(overrides)
    return RawInputs(**base)


def metric(**overrides):
    """A valid metric baseline: 35m, 178cm, 95kg -> 85kg at 1 kg/week."""
    base = dict(
        unit="metric", sex="male", age="35",
        height_cm="178", height_ft="", height_in="",
        weight="95", goal="85", body_fat="", activity_key=MODERATE,
        pace="1",
    )
    base.update(overrides)
    return RawInputs(**base)


class TestUnitConversions(unittest.TestCase):
    def test_known_values(self):
        self.assertAlmostEqual(core.lb_to_kg(180), 81.6466266, places=7)
        self.assertAlmostEqual(core.kg_to_lb(100), 220.46226218, places=7)
        self.assertAlmostEqual(core.in_to_cm(65), 165.1, places=10)
        self.assertAlmostEqual(core.cm_to_in(165.1), 65.0, places=10)

    def test_round_trips(self):
        for v in (0.5, 1, 65, 180, 999.9):
            self.assertAlmostEqual(core.kg_to_lb(core.lb_to_kg(v)), v, places=9)
            self.assertAlmostEqual(core.cm_to_in(core.in_to_cm(v)), v, places=9)

    def test_constants(self):
        # Pinned because the whole model hangs off them.
        self.assertEqual(core.KG_PER_LB, 0.45359237)
        self.assertEqual(core.CM_PER_IN, 2.54)
        self.assertEqual(core.IN_PER_FT, 12)
        self.assertEqual(core.CAL_PER_KG_FAT, 7700)
        self.assertEqual(core.WEEKS_PER_MONTH, 4.345)


class TestHeightConversions(unittest.TestCase):
    def test_ft_in_to_cm(self):
        self.assertAlmostEqual(core.ft_in_to_cm(5, 5), 165.1, places=9)
        self.assertAlmostEqual(core.ft_in_to_cm(6, 0), 182.88, places=9)
        self.assertAlmostEqual(core.ft_in_to_cm(0, 12), 30.48, places=9)

    def test_ft_in_to_cm_agrees_with_total_inches(self):
        # The split must not change the arithmetic: 5'5" is still 65 in.
        for feet, inches in [(5, 5), (6, 0), (4, 11), (5, 10.5)]:
            self.assertAlmostEqual(
                core.ft_in_to_cm(feet, inches),
                core.in_to_cm(feet * 12 + inches),
                places=9,
            )

    def test_fractional_inches(self):
        self.assertAlmostEqual(core.ft_in_to_cm(5, 10.5), 179.07, places=9)

    def test_cm_to_ft_in(self):
        self.assertEqual(core.cm_to_ft_in(165.1), (5, 5.0))
        self.assertEqual(core.cm_to_ft_in(182.88), (6, 0.0))
        self.assertEqual(core.cm_to_ft_in(152.4), (5, 0.0))

    def test_cm_to_ft_in_carries_instead_of_reporting_12_inches(self):
        # 182.87 cm is 71.996 in. Rounding inches alone gives 5 ft 12.0 in,
        # which is not a height anyone writes.
        feet, inches = core.cm_to_ft_in(182.87)
        self.assertEqual((feet, inches), (6, 0.0))
        self.assertLess(inches, 12)

    def test_cm_to_ft_in_never_returns_12_or_more_inches(self):
        for cm in range(30, 251):
            for frac in (0.0, 0.3, 0.87, 0.99):
                _, inches = core.cm_to_ft_in(cm + frac)
                self.assertTrue(0 <= inches < 12, "%s -> %s in" % (cm + frac, inches))

    def test_height_round_trip(self):
        for feet, inches in [(5, 5), (6, 2), (4, 11), (5, 0)]:
            cm = core.ft_in_to_cm(feet, inches)
            self.assertEqual(core.cm_to_ft_in(cm), (feet, float(inches)))

    def test_normalize_ft_in(self):
        self.assertEqual(core.normalize_ft_in(5, 15), (6, 3))
        self.assertEqual(core.normalize_ft_in(5, 12), (6, 0))
        self.assertEqual(core.normalize_ft_in(0, 65), (5, 5))
        self.assertEqual(core.normalize_ft_in(5, 5), (5, 5))


class TestFormulas(unittest.TestCase):
    def test_mifflin_st_jeor_male(self):
        self.assertAlmostEqual(
            core.bmr_mifflin_st_jeor(95, 178, 35, "male"), 1892.5, places=6
        )

    def test_mifflin_st_jeor_female(self):
        self.assertAlmostEqual(
            core.bmr_mifflin_st_jeor(95, 178, 35, "female"), 1726.5, places=6
        )

    def test_male_female_offset_is_166(self):
        m = core.bmr_mifflin_st_jeor(80, 170, 40, "male")
        f = core.bmr_mifflin_st_jeor(80, 170, 40, "female")
        self.assertAlmostEqual(m - f, 166.0, places=9)

    def test_any_non_male_sex_is_treated_as_female(self):
        # Pins the `else` branch: the formula has two cases, not three.
        f = core.bmr_mifflin_st_jeor(80, 170, 40, "female")
        for sex in ("other", "nonbinary", "", "MALE"):
            self.assertAlmostEqual(
                core.bmr_mifflin_st_jeor(80, 170, 40, sex), f, places=9
            )

    def test_katch_mcardle(self):
        self.assertAlmostEqual(
            core.bmr_katch_mcardle(81.6466266, 22), 1745.5823649568, places=6
        )

    def test_katch_mcardle_ignores_sex_by_design(self):
        # Katch-McArdle takes no sex argument. This documents that the
        # sex radio is intentionally inert when body fat % is supplied.
        self.assertEqual(len(core.bmr_katch_mcardle.__code__.co_varnames[:2]), 2)

    def test_tdee(self):
        self.assertAlmostEqual(core.tdee_from_bmr(1892.5, 1.55), 2933.375, places=6)

    def test_activity_factors(self):
        self.assertEqual(
            list(core.ACTIVITY_LEVELS.values()), [1.2, 1.375, 1.55, 1.725, 1.9]
        )

    def test_bmi(self):
        self.assertAlmostEqual(core.bmi(82, 165), 30.1193755739, places=8)

    def test_weight_for_bmi_inverts_bmi(self):
        self.assertAlmostEqual(
            core.weight_for_bmi(core.bmi(82, 165), 165), 82.0, places=9
        )

    def test_daily_calorie_delta(self):
        self.assertAlmostEqual(core.daily_calorie_delta(1.0), 1100.0, places=9)
        self.assertAlmostEqual(
            core.daily_calorie_delta(core.lb_to_kg(1)), 498.951607, places=6
        )


class TestInputsProperties(unittest.TestCase):
    def _inputs(self, unit, **kw):
        base = dict(
            unit=unit, sex="female", age=30.0, height_cm=165.1,
            height_ft=5.0, height_in=5.0, weight=180.0,
            goal=150.0, body_fat_pct=None, activity_key=SEDENTARY, pace=1,
        )
        base.update(kw)
        return core.Inputs(**base)

    def test_imperial_conversions(self):
        i = self._inputs("imperial")
        self.assertTrue(i.is_imperial)
        self.assertEqual(i.unit_label, "lb")
        self.assertAlmostEqual(i.height_cm, 165.1, places=9)
        self.assertAlmostEqual(i.weight_kg, 81.6466266, places=7)
        self.assertAlmostEqual(i.goal_kg, 68.0388555, places=7)
        self.assertAlmostEqual(i.pace_kg_per_week, 0.45359237, places=9)

    def test_height_cm_is_stored_not_derived(self):
        # Unlike weight/goal, height is canonical in cm - there is no
        # unit-dependent reinterpretation of it on the Inputs object.
        imp = self._inputs("imperial", height_cm=165.1)
        met = self._inputs("metric", height_cm=165.1,
                           height_ft=None, height_in=None)
        self.assertEqual(imp.height_cm, met.height_cm)

    def test_metric_is_passthrough(self):
        i = self._inputs("metric", height_cm=178.0, height_ft=None,
                         height_in=None, weight=95.0, goal=85.0)
        self.assertFalse(i.is_imperial)
        self.assertEqual(i.unit_label, "kg")
        self.assertEqual(i.height_cm, 178.0)
        self.assertEqual(i.weight_kg, 95.0)
        self.assertEqual(i.goal_kg, 85.0)
        self.assertEqual(i.pace_kg_per_week, 1.0)

    def test_unknown_unit_string_falls_back_to_metric(self):
        # Only the exact string "imperial" selects imperial. Pinning this
        # because the fallback is silent.
        i = self._inputs("IMPERIAL")
        self.assertFalse(i.is_imperial)
        self.assertEqual(i.weight_kg, 180.0)

    def test_activity_factor_lookup(self):
        self.assertEqual(self._inputs("metric").activity_factor, 1.2)

    def test_inputs_are_frozen(self):
        i = self._inputs("imperial")
        with self.assertRaises(Exception):
            i.weight = 200


class TestSuccessfulPlans(unittest.TestCase):
    def assertPlan(self, outcome):
        self.assertIsInstance(outcome, Plan)
        self.assertTrue(outcome.ok)
        return outcome

    def test_imperial_loss_female(self):
        p = self.assertPlan(calculate_plan(raw()))
        self.assertEqual(p.formula, "Mifflin-St Jeor")
        self.assertEqual(p.direction, "lose")
        self.assertAlmostEqual(p.bmr, 1537.341266, places=5)
        self.assertAlmostEqual(p.tdee, 1844.8095192, places=5)
        self.assertAlmostEqual(p.target_calories, 1345.8579122, places=5)
        self.assertAlmostEqual(p.daily_delta, 498.951607, places=5)
        self.assertAlmostEqual(p.weeks, 30.0, places=6)
        self.assertAlmostEqual(p.months, 6.9044879171, places=6)

    def test_imperial_loss_male_differs_by_166_in_bmr(self):
        f = self.assertPlan(calculate_plan(raw(sex="female")))
        m = self.assertPlan(calculate_plan(raw(sex="male")))
        self.assertAlmostEqual(m.bmr - f.bmr, 166.0, places=6)
        self.assertAlmostEqual(m.bmr, 1703.341266, places=5)

    def test_imperial_gain(self):
        p = self.assertPlan(calculate_plan(raw(goal="200")))
        self.assertEqual(p.direction, "gain")
        # Gain adds the delta to TDEE; loss subtracts it.
        self.assertAlmostEqual(p.target_calories, 2343.7611262, places=5)
        self.assertAlmostEqual(p.weeks, 20.0, places=6)

    def test_maintain(self):
        p = self.assertPlan(calculate_plan(raw(goal="180")))
        self.assertEqual(p.direction, "maintain")
        self.assertAlmostEqual(p.target_calories, p.tdee, places=9)
        self.assertEqual(p.weeks, 0.0)
        self.assertEqual(p.months, 0.0)

    def test_maintain_still_reports_a_daily_delta(self):
        # daily_delta is computed from pace regardless of direction, so it
        # is non-zero even when maintaining. The UI simply doesn't show it.
        p = self.assertPlan(calculate_plan(raw(goal="180")))
        self.assertAlmostEqual(p.daily_delta, 498.951607, places=5)

    def test_body_fat_switches_to_katch_mcardle(self):
        p = self.assertPlan(calculate_plan(raw(body_fat="22")))
        self.assertEqual(p.formula, "Katch-McArdle")
        self.assertAlmostEqual(p.bmr, 1745.5823649568, places=5)
        self.assertEqual(p.inputs.body_fat_pct, 22.0)

    def test_body_fat_makes_sex_irrelevant(self):
        f = self.assertPlan(calculate_plan(raw(body_fat="22", sex="female")))
        m = self.assertPlan(calculate_plan(raw(body_fat="22", sex="male")))
        self.assertEqual(f.bmr, m.bmr)

    def test_metric_loss(self):
        p = self.assertPlan(calculate_plan(metric()))
        self.assertEqual(p.direction, "lose")
        self.assertAlmostEqual(p.bmr, 1892.5, places=6)
        self.assertAlmostEqual(p.tdee, 2933.375, places=6)
        self.assertAlmostEqual(p.target_calories, 1833.375, places=6)
        self.assertAlmostEqual(p.daily_delta, 1100.0, places=6)
        self.assertAlmostEqual(p.weeks, 10.0, places=9)
        self.assertAlmostEqual(p.months, 2.3014959724, places=6)

    def test_metric_gain(self):
        p = self.assertPlan(calculate_plan(metric(goal="105")))
        self.assertEqual(p.direction, "gain")
        self.assertAlmostEqual(p.target_calories, 4033.375, places=6)

    def test_plan_echoes_parsed_inputs(self):
        p = self.assertPlan(calculate_plan(raw()))
        self.assertEqual(p.inputs.age, 30.0)
        self.assertEqual(p.inputs.weight, 180.0)
        self.assertEqual(p.inputs.goal, 150.0)
        self.assertEqual(p.inputs.pace, 1)
        self.assertEqual(p.inputs.unit_label, "lb")
        self.assertIsNone(p.inputs.body_fat_pct)

    def test_whitespace_is_tolerated(self):
        p = self.assertPlan(
            calculate_plan(raw(age=" 30 ", pace="  1  ", body_fat="  22  "))
        )
        self.assertEqual(p.formula, "Katch-McArdle")
        self.assertEqual(p.inputs.pace, 1)

    def test_higher_activity_raises_tdee_not_bmr(self):
        a = self.assertPlan(calculate_plan(raw(activity_key=ACT[0])))
        b = self.assertPlan(calculate_plan(raw(activity_key=ACT[4])))
        self.assertEqual(a.bmr, b.bmr)
        self.assertGreater(b.tdee, a.tdee)
        self.assertAlmostEqual(b.tdee / a.tdee, 1.9 / 1.2, places=9)


class TestRejections(unittest.TestCase):
    def assertRejects(self, outcome, code, field=None):
        self.assertIsInstance(outcome, Rejection)
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.code, code)
        if field is not None:
            self.assertEqual(outcome.field, field)
        # Every rejection must carry presentable copy.
        self.assertTrue(outcome.title)
        self.assertTrue(outcome.message)
        return outcome

    def test_blank_and_non_numeric_core_fields(self):
        for kw in [{"age": ""}, {"age": "abc"}, {"height_ft": ""},
                   {"weight": "x"}, {"goal": ""}, {"goal": "1,000"}]:
            self.assertRejects(calculate_plan(raw(**kw)), "INVALID_NUMBER")

    def test_non_positive_core_fields(self):
        for kw in [{"age": "0"}, {"age": "-1"}, {"height_ft": "0", "height_in": "0"},
                   {"weight": "-5"}, {"goal": "0"}]:
            self.assertRejects(calculate_plan(raw(**kw)), "NON_POSITIVE")

    def test_age_below_minimum(self):
        r = self.assertRejects(calculate_plan(raw(age="17")), "AGE_RANGE", "age")
        self.assertEqual(r.context["min_age"], 18)

    def test_age_above_maximum(self):
        self.assertRejects(calculate_plan(raw(age="1001")), "AGE_RANGE", "age")

    def test_goal_below_bmi_floor(self):
        r = self.assertRejects(
            calculate_plan(raw(height_ft="6", height_in="0", weight="150", goal="100")),
            "GOAL_BMI", "goal",
        )
        self.assertAlmostEqual(r.context["goal_bmi"], 13.5622989900, places=7)
        self.assertAlmostEqual(r.context["min_goal_kg"], 61.87342464, places=7)
        self.assertAlmostEqual(r.context["min_goal_display"], 136.4075516526, places=6)
        self.assertEqual(r.context["min_goal_bmi"], 18.5)

    def test_body_fat_non_numeric(self):
        self.assertRejects(
            calculate_plan(raw(body_fat="abc")), "BODY_FAT_INVALID", "body_fat"
        )

    def test_body_fat_out_of_range(self):
        for v in ("0", "-1", "75", "100"):
            self.assertRejects(
                calculate_plan(raw(body_fat=v)), "BODY_FAT_RANGE", "body_fat"
            )

    def test_unknown_activity_key(self):
        # Unreachable from the readonly dropdown; guarded so it surfaces as
        # a rejection rather than a raw KeyError.
        self.assertRejects(
            calculate_plan(raw(activity_key="nope")), "ACTIVITY_INVALID"
        )

    def test_pace_non_numeric_or_fractional(self):
        for v in ("", "abc", "1.5", "0.5"):
            self.assertRejects(calculate_plan(raw(pace=v)), "PACE_INVALID", "pace")

    def test_pace_non_positive(self):
        for v in ("0", "-1"):
            self.assertRejects(
                calculate_plan(raw(pace=v)), "PACE_NON_POSITIVE", "pace"
            )

    def test_pace_above_ceiling(self):
        r = self.assertRejects(calculate_plan(raw(pace="101")), "PACE_RANGE", "pace")
        self.assertEqual(r.context["max_pace"], 100)

    def test_calorie_floor_blocks_the_plan(self):
        r = self.assertRejects(
            calculate_plan(metric(weight="82", goal="68", pace="2")),
            "CALORIE_FLOOR", "pace",
        )
        self.assertEqual(r.context["calorie_floor"], 1200)
        self.assertLess(r.context["target_calories"], 1200)
        # The floor blocks rather than annotates: no plan comes back.
        self.assertNotIsInstance(r, Plan)

    def test_calorie_floor_message_is_self_contained(self):
        # The UI renders this one into the results card using `message`
        # alone, so the message must stand on its own without the title.
        r = calculate_plan(metric(weight="82", goal="68", pace="2"))
        self.assertTrue(r.message.startswith("No plan generated."))

    def test_maintain_bypasses_the_calorie_floor(self):
        # direction == "maintain" skips the floor check, so a very low TDEE
        # can still return a plan at maintenance.
        # 95 lb at 60 in is BMI 18.55, so it clears the goal-BMI floor.
        p = calculate_plan(
            raw(age="90", height_ft="5", height_in="0", weight="95", goal="95")
        )
        self.assertIsInstance(p, Plan)
        self.assertEqual(p.direction, "maintain")
        self.assertAlmostEqual(p.tdee, 926.8953018, places=6)
        self.assertLess(p.tdee, core.CALORIE_FLOOR)

    def test_rejections_carry_a_context_mapping(self):
        r = calculate_plan(raw(age="17"))
        self.assertIsInstance(dict(r.context), dict)
        r2 = calculate_plan(raw(age="abc"))
        self.assertEqual(dict(r2.context), {})


class TestBoundaries(unittest.TestCase):
    """Exact edges. These are where off-by-one regressions land."""

    def test_age_boundaries_are_inclusive(self):
        self.assertIsInstance(calculate_plan(raw(age="18")), Plan)
        self.assertIsInstance(calculate_plan(raw(age="1000")), Rejection)
        self.assertEqual(calculate_plan(raw(age="17")).code, "AGE_RANGE")
        self.assertEqual(calculate_plan(raw(age="1001")).code, "AGE_RANGE")

    def test_body_fat_bounds_are_exclusive(self):
        # Goal is a *gain* here so the low BMR that a 74.9% body fat figure
        # implies can't trip the calorie floor and mask the boundary.
        self.assertEqual(
            calculate_plan(raw(goal="200", body_fat="0")).code, "BODY_FAT_RANGE"
        )
        self.assertEqual(
            calculate_plan(raw(goal="200", body_fat="75")).code, "BODY_FAT_RANGE"
        )
        self.assertIsInstance(calculate_plan(raw(goal="200", body_fat="0.1")), Plan)
        self.assertIsInstance(calculate_plan(raw(goal="200", body_fat="74.9")), Plan)

    def test_pace_ceiling_is_inclusive(self):
        # pace=100 passes the entry ceiling, then dies on the calorie
        # floor. The ceiling and the floor are separate limits and only
        # the floor is unit-aware. See TestDesignedBounds.
        self.assertEqual(calculate_plan(raw(pace="100")).code, "CALORIE_FLOOR")
        self.assertEqual(calculate_plan(raw(pace="101")).code, "PACE_RANGE")

    def test_maintain_tolerance_is_0_01_kg(self):
        self.assertEqual(calculate_plan(raw(goal="180")).direction, "maintain")
        self.assertEqual(calculate_plan(raw(goal="180.02")).direction, "maintain")
        self.assertEqual(calculate_plan(raw(goal="180.03")).direction, "gain")
        self.assertEqual(calculate_plan(raw(goal="179.98")).direction, "maintain")

    def test_goal_exactly_at_bmi_floor_is_accepted(self):
        # 18.5 BMI at 178cm = 58.6154 kg. The check is strict `<`.
        at_floor = core.weight_for_bmi(18.5, 178)
        self.assertIsInstance(
            calculate_plan(metric(goal="%.6f" % (at_floor + 0.001), pace="1")), Plan
        )
        self.assertEqual(
            calculate_plan(metric(goal="%.6f" % (at_floor - 0.01))).code, "GOAL_BMI"
        )


class TestValidationOrder(unittest.TestCase):
    """The order of checks is load-bearing: it decides which error a user
    sees when several fields are wrong at once. calc_core's docstring says
    so; these tests make it true."""

    def test_parse_errors_precede_range_errors(self):
        self.assertEqual(calculate_plan(raw(age="abc", height_ft="0")).code,
                         "INVALID_NUMBER")

    def test_non_positive_precedes_age_range(self):
        self.assertEqual(calculate_plan(raw(age="-5")).code, "NON_POSITIVE")

    def test_age_precedes_goal_bmi(self):
        self.assertEqual(
            calculate_plan(raw(age="12", height_ft="6", goal="100")).code, "AGE_RANGE"
        )

    def test_goal_bmi_precedes_body_fat(self):
        self.assertEqual(
            calculate_plan(raw(height_ft="6", goal="100", body_fat="abc")).code,
            "GOAL_BMI",
        )

    def test_body_fat_precedes_pace(self):
        self.assertEqual(
            calculate_plan(raw(body_fat="abc", pace="abc")).code, "BODY_FAT_INVALID"
        )

    def test_pace_parse_precedes_pace_range(self):
        self.assertEqual(calculate_plan(raw(pace="abc")).code, "PACE_INVALID")

    def test_pace_range_precedes_calorie_floor(self):
        self.assertEqual(calculate_plan(raw(pace="500")).code, "PACE_RANGE")


class TestDesignedBounds(unittest.TestCase):
    """Deliberate design decisions, pinned against accidental change.

    The bounds below are wide on purpose. The author has decided the tool
    should stay permissive and let the 1,200 kcal floor be the only hard
    stop on the loss side; the risk is understood and accepted. Do not
    "fix" these because they look like oversights - they aren't, and
    these tests exist to catch a silent tightening as much as a silent
    loosening.

    If a change here is ever wanted, it's a product decision, not a bug
    fix. Update these tests in the same commit.
    """

    def test_max_age_is_1000(self):
        # Intentionally wide. An age of 999 clears the age check and
        # drives Mifflin-St Jeor to a negative BMR; the calorie floor is
        # what stops a plan being produced, not the age bound.
        self.assertEqual(core.MAX_AGE, 1000)
        r = calculate_plan(raw(age="999"))
        self.assertEqual(r.code, "CALORIE_FLOOR")
        self.assertLess(r.context["tdee"], 0)

    def test_pace_ceilings_are_the_same_number_in_both_units(self):
        # By design: the ceiling is a plain entry limit, not a
        # unit-normalized one. In real terms that makes metric ~2.2x more
        # permissive, which is accepted.
        self.assertEqual(core.MAX_PACE_LB, core.MAX_PACE_KG)
        self.assertAlmostEqual(
            core.lb_to_kg(core.MAX_PACE_LB) / core.MAX_PACE_KG, 0.45359237, places=9
        )

    def test_gain_pace_is_bounded_only_by_the_entry_ceiling(self):
        # The 1200 kcal floor constrains deficits, not surpluses. A large
        # gain pace produces a plan, by design.
        p = calculate_plan(raw(goal="200", pace="10"))
        self.assertIsInstance(p, Plan)
        self.assertEqual(p.direction, "gain")
        self.assertGreater(p.target_calories, 6800)

    def test_pace_default_of_1_means_different_speeds_per_unit(self):
        # The UI resets pace to "1" on unit toggle, so the same user gets
        # 1 lb/week in imperial and 1 kg/week in metric. Documented in the
        # README rather than smoothed over.
        imp = calculate_plan(raw(weight="180", goal="150", pace="1"))
        met = calculate_plan(
            raw(unit="metric", height_cm="165.1", weight="81.6", goal="68", pace="1")
        )
        self.assertIsInstance(imp, Plan)
        self.assertEqual(met.code, "CALORIE_FLOOR")

    def test_maintain_tolerance_is_unit_dependent(self):
        # abs(diff_kg) < 0.01 is applied in kg, so the imperial dead zone
        # is ~0.022 lb wide and the metric one is 0.01 kg.
        self.assertEqual(calculate_plan(raw(goal="180.02")).direction, "maintain")
        self.assertEqual(
            calculate_plan(metric(weight="82", goal="82.02")).direction, "gain"
        )

    def test_timeline_ignores_falling_tdee(self):
        # Linear model: weeks = diff / pace, with TDEE held constant. The
        # UI discloses this in a footnote rather than modelling it.
        p = calculate_plan(raw(weight="180", goal="150", pace="1"))
        self.assertAlmostEqual(p.weeks, 30.0, places=6)


class TestHeightInput(unittest.TestCase):
    """The imperial ft+in pair and the metric cm box."""

    def test_feet_and_inches_match_the_old_total_inches_behavior(self):
        # 5'5" must produce exactly what height="65" produced before the
        # split. This is the whole safety property of the change.
        p = calculate_plan(raw(height_ft="5", height_in="5"))
        self.assertAlmostEqual(p.inputs.height_cm, 165.1, places=9)
        self.assertAlmostEqual(p.bmr, 1537.341266, places=5)

    def test_blank_inches_is_treated_as_zero(self):
        blank = calculate_plan(raw(height_ft="6", height_in=""))
        explicit = calculate_plan(raw(height_ft="6", height_in="0"))
        self.assertAlmostEqual(blank.inputs.height_cm, 182.88, places=9)
        self.assertEqual(blank.bmr, explicit.bmr)

    def test_blank_feet_is_a_missing_input(self):
        # Unlike inches, feet has no sensible default.
        self.assertEqual(
            calculate_plan(raw(height_ft="", height_in="5")).code,
            "INVALID_NUMBER",
        )

    def test_fractional_inches_accepted(self):
        p = calculate_plan(raw(height_ft="5", height_in="10.5"))
        self.assertAlmostEqual(p.inputs.height_cm, 179.07, places=9)

    def test_inches_of_12_or_more_rejected_with_a_suggestion(self):
        r = calculate_plan(raw(height_ft="5", height_in="15"))
        self.assertEqual(r.code, "HEIGHT_INCHES_RANGE")
        self.assertEqual(r.field, "height_in")
        self.assertEqual(r.context["suggested_ft"], 6)
        self.assertEqual(r.context["suggested_in"], 3)
        self.assertIn("6 ft 3 in", r.message)

    def test_total_inches_typed_into_the_inches_box_is_guided(self):
        # Someone used to the old single field types 65 into "in".
        r = calculate_plan(raw(height_ft="0", height_in="65"))
        self.assertEqual(r.code, "HEIGHT_INCHES_RANGE")
        self.assertEqual(r.context["suggested_ft"], 5)
        self.assertEqual(r.context["suggested_in"], 5)

    def test_inches_exactly_12_is_rejected(self):
        self.assertEqual(
            calculate_plan(raw(height_ft="5", height_in="12")).code,
            "HEIGHT_INCHES_RANGE",
        )

    def test_inches_just_under_12_is_accepted(self):
        self.assertIsInstance(
            calculate_plan(raw(height_ft="5", height_in="11.99")), Plan
        )

    def test_negative_inches_rejected_without_a_suggestion(self):
        r = calculate_plan(raw(height_ft="5", height_in="-3"))
        self.assertEqual(r.code, "HEIGHT_INCHES_RANGE")
        # A negative has no useful normalization to suggest.
        self.assertNotIn(" is ", r.message)

    def test_zero_height_is_non_positive(self):
        self.assertEqual(
            calculate_plan(raw(height_ft="0", height_in="0")).code, "NON_POSITIVE"
        )
        self.assertEqual(
            calculate_plan(raw(height_ft="0", height_in="")).code, "NON_POSITIVE"
        )

    def test_negative_feet_is_non_positive(self):
        self.assertEqual(
            calculate_plan(raw(height_ft="-5", height_in="0")).code, "NON_POSITIVE"
        )

    def test_metric_reads_cm_and_ignores_the_imperial_pair(self):
        # Stale text left in hidden widgets must not affect the result.
        clean = calculate_plan(metric(height_cm="178"))
        stale = calculate_plan(
            metric(height_cm="178", height_ft="99", height_in="abc")
        )
        self.assertEqual(clean.bmr, stale.bmr)
        self.assertIsNone(stale.inputs.height_ft)
        self.assertIsNone(stale.inputs.height_in)

    def test_imperial_ignores_a_stale_cm_value(self):
        clean = calculate_plan(raw(height_cm=""))
        stale = calculate_plan(raw(height_cm="999"))
        self.assertEqual(clean.bmr, stale.bmr)

    def test_imperial_plan_echoes_both_height_components(self):
        p = calculate_plan(raw(height_ft="5", height_in="5"))
        self.assertEqual(p.inputs.height_ft, 5.0)
        self.assertEqual(p.inputs.height_in, 5.0)

    def test_inches_range_is_checked_after_non_positive(self):
        # 0 ft 0 in is a missing height, not an inches-range problem.
        self.assertEqual(
            calculate_plan(raw(height_ft="0", height_in="0")).code, "NON_POSITIVE"
        )

    def test_inches_range_is_checked_before_age_range(self):
        self.assertEqual(
            calculate_plan(raw(age="12", height_ft="5", height_in="15")).code,
            "HEIGHT_INCHES_RANGE",
        )

    def test_metric_never_hits_the_inches_check(self):
        # height_in is meaningless in metric; a bad value there is inert.
        self.assertIsInstance(calculate_plan(metric(height_in="15")), Plan)


class TestNeverRaises(unittest.TestCase):
    """calculate_plan is the whole public surface. It must always return
    an outcome, never raise - the UI has no except clause around it."""

    def test_broad_input_sweep(self):
        odd = ["", " ", "abc", "0", "-1", "1e400", "nan", "inf", "1_0",
               "0x10", "1.5", "999999999", "١٢"]
        checked = 0
        for age, height, weight, goal, bf, pace, unit in itertools.product(
            odd[:6], odd[:5], odd[:5], odd[:5], ["", "22", "abc"],
            ["1", "abc", "0"], ["imperial", "metric"],
        ):
            # The same junk goes into every height field, so both the
            # metric and imperial parse paths see it.
            outcome = calculate_plan(RawInputs(
                unit=unit, sex="female", age=age, height_cm=height,
                height_ft=height, height_in=height, weight=weight,
                goal=goal, body_fat=bf, activity_key=SEDENTARY, pace=pace,
            ))
            self.assertIsInstance(outcome, (Plan, Rejection))
            checked += 1
        self.assertGreater(checked, 1000)

    def test_inf_and_nan_do_not_crash(self):
        for v in ("inf", "-inf", "nan", "1e400"):
            for fld in ("age", "height_ft", "height_in", "weight", "goal",
                        "body_fat"):
                outcome = calculate_plan(raw(**{fld: v}))
                self.assertIsInstance(outcome, (Plan, Rejection))
            outcome = calculate_plan(metric(height_cm=v))
            self.assertIsInstance(outcome, (Plan, Rejection))


if __name__ == "__main__":
    unittest.main(verbosity=2)
