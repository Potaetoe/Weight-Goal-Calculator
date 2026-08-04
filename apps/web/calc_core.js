/*
 * Weight Goal Calculator - pure calculation core (web port)
 * ---------------------------------------------------------
 * A direct port of calc_core.py. Same formulas, same bounds, same
 * validation order, same rejection codes and copy.
 *
 * No DOM access, no I/O. calculatePlan(rawInputs) returns a plan or a
 * rejection; it never throws and never displays anything.
 *
 * Correctness is defined as "reproduces web/fixture.js", which is
 * generated from the Python implementation. Open dev/selftest.html to
 * check.
 *
 * DISCLAIMER: For entertainment and general informational purposes only.
 * Not medical advice. See README.md.
 *
 * ---------------------------------------------------------------------
 * WHY THERE ARE py* HELPERS BELOW
 *
 * Python and JavaScript disagree about numbers in ways that would show up
 * as wrong output, not as errors:
 *
 *   Number("")      -> 0          Python float("")     -> error
 *   Number("0x10")  -> 16         Python float("0x10") -> error
 *   Number("inf")   -> NaN        Python float("inf")  -> inf
 *   (0.25).toFixed(1) -> "0.3"    Python round(0.25,1) -> 0.2
 *   String(Infinity) -> "Infinity"  Python f"{inf:g}"  -> "inf"
 *
 * pyFloat / pyInt / pyRound / fmtG / fmtFixed / fmtThousands exist to
 * close those gaps. Do not replace them with the JS built-ins.
 * ---------------------------------------------------------------------
 */
(function (global) {
  "use strict";

  // -------------------------------------------------------------------
  // Constants
  // -------------------------------------------------------------------
  var ACTIVITY_LEVELS = {
    "Sedentary (little/no exercise)": 1.2,
    "Lightly active (1-3 days/week)": 1.375,
    "Moderately active (3-5 days/week)": 1.55,
    "Very active (6-7 days/week)": 1.725,
    "Extremely active (physical job + training)": 1.9
  };
  // Insertion order matters for the dropdown; keep an explicit list.
  var ACTIVITY_ORDER = [
    "Sedentary (little/no exercise)",
    "Lightly active (1-3 days/week)",
    "Moderately active (3-5 days/week)",
    "Very active (6-7 days/week)",
    "Extremely active (physical job + training)"
  ];

  var KG_PER_LB = 0.45359237;
  var CM_PER_IN = 2.54;
  var IN_PER_FT = 12;
  var CAL_PER_KG_FAT = 7700;
  var WEEKS_PER_MONTH = 4.345;

  var MAX_PACE_LB = 100;
  var MAX_PACE_KG = 100;
  var CALORIE_FLOOR = 1200;
  var MIN_AGE = 18;
  var MAX_AGE = 1000;
  var MIN_GOAL_BMI = 18.5;

  var IMPERIAL = "imperial";
  var METRIC = "metric";

  // -------------------------------------------------------------------
  // Python-compatible parsing and formatting
  // -------------------------------------------------------------------

  /* Mirrors Python float(str): tolerates surrounding whitespace and
   * underscores between digits, accepts inf/-inf/nan case-insensitively,
   * rejects "", hex, and anything else. Returns NaN only when Python
   * would return nan; throws a sentinel for what Python would reject. */
  var PARSE_ERROR = {};

  function pyFloat(text) {
    var s = String(text).trim();
    if (s === "") throw PARSE_ERROR;
    // Python allows 1_000.5; underscores must sit between digits.
    if (s.indexOf("_") !== -1) {
      if (!/^[+-]?\d(_?\d)*(\.\d(_?\d)*)?([eE][+-]?\d(_?\d)*)?$/.test(s)) {
        throw PARSE_ERROR;
      }
      s = s.replace(/_/g, "");
    }
    var lower = s.toLowerCase();
    var sign = 1;
    if (lower[0] === "+" || lower[0] === "-") {
      sign = lower[0] === "-" ? -1 : 1;
      lower = lower.slice(1);
    }
    if (lower === "inf" || lower === "infinity") return sign * Infinity;
    if (lower === "nan") return NaN;
    if (!/^(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(lower)) throw PARSE_ERROR;
    return sign * Number(lower);
  }

  /* Mirrors Python int(str): whitespace tolerated, no decimal point. */
  function pyInt(text) {
    var s = String(text).trim();
    if (s === "") throw PARSE_ERROR;
    if (s.indexOf("_") !== -1) {
      if (!/^[+-]?\d(_?\d)*$/.test(s)) throw PARSE_ERROR;
      s = s.replace(/_/g, "");
    }
    if (!/^[+-]?\d+$/.test(s)) throw PARSE_ERROR;
    return parseInt(s, 10);
  }

  /* Mirrors Python round(x, n): half-to-even on exact ties.
   * JS toFixed rounds ties away from zero (0.25 -> "0.3" where Python
   * gives 0.2), so ties are handled separately. Everything else goes
   * through toFixed, which rounds the true binary value correctly.
   *
   * Detecting the tie is the subtle part. Testing `x * 10^n` for a .5
   * remainder reports FALSE ties: 0.15 is really 0.1499999...,  but
   * 0.15 * 10 rounds to exactly 1.5, so that test would round it up to
   * 0.2 where Python gives 0.1. Instead scale to one digit further and
   * require the scaling to be lossless - only a value that is exactly a
   * decimal ending in 5 at position n+1 survives that. */
  function pyRound(x, n) {
    if (!isFinite(x)) return x;
    var negative = x < 0 || Object.is(x, -0);
    var a = Math.abs(x);
    // At this magnitude the value is already integral and toFixed
    // switches to exponential notation, so there is nothing to round.
    if (a >= 1e21) return x;

    // Every double has a terminating decimal expansion. toFixed(100)
    // spells enough of it to tell a real tie from a near-miss:
    //   0.25 -> "0.2500000...0"       digits after position n are zero
    //   0.05 -> "0.0500000...0277..." they are not
    // Only the first is a tie. Scaling arithmetic cannot tell these
    // apart because both land on the same double once multiplied.
    var s = a.toFixed(100);
    var frac = s.slice(s.indexOf(".") + 1);
    var isTie = n < frac.length && frac.charAt(n) === "5" &&
      /^0*$/.test(frac.slice(n + 1));

    if (isTie) {
      var p = Math.pow(10, n);
      var fl = Math.floor(a * p);
      var even = (fl % 2 === 0) ? fl : fl + 1;
      var res = even / p;
      // Python keeps the sign: round(-0.5) is -0.0, not 0.0.
      if (negative) return res === 0 ? -0 : -res;
      return res;
    }
    return parseFloat(x.toFixed(n));
  }

  function nonFiniteWord(x) {
    if (Number.isNaN(x)) return "nan";
    if (x === Infinity) return "inf";
    if (x === -Infinity) return "-inf";
    return null;
  }

  /* Python f"{x:.Nf}". Python keeps a negative sign even when the
   * result rounds to zero: "%.0f" % -0.4 is "-0", not "0". JS toFixed
   * drops it, so the sign is applied by hand. */
  function fmtFixed(x, n) {
    var word = nonFiniteWord(x);
    if (word !== null) return word;
    var r = pyRound(x, n);
    var negative = r < 0 || Object.is(r, -0) ||
      (r === 0 && (x < 0 || Object.is(x, -0)));
    return (negative ? "-" : "") + Math.abs(r).toFixed(n);
  }

  /* Python f"{x:,.0f}" */
  function fmtThousands(x) {
    var word = nonFiniteWord(x);
    if (word !== null) return word;
    var rounded = pyRound(x, 0);
    var sign = rounded < 0 || Object.is(rounded, -0) ? "-" : "";
    var digits = Math.abs(rounded).toFixed(0);
    return sign + digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  /* Python str(float): an integral float keeps its ".0", so str(30.0)
   * is "30.0" where JS String(30) gives "30". Used for the week/month
   * figures, which are interpolated bare in the results copy. */
  function fmtFloat(x) {
    var word = nonFiniteWord(x);
    if (word !== null) return word;
    if (Number.isInteger(x) && Math.abs(x) < 1e16) return x.toFixed(1);
    return String(x);
  }

  /* Python f"{x:g}": 6 significant digits, trailing zeros stripped.
   * Exponent form when the decimal exponent is < -4 or >= the precision
   * (6) - so 1e-4 prints as 0.0001 but 1e-5 prints as 1e-05.
   * The exponent comes from toExponential rather than Math.log10, which
   * can land a digit off at exact powers of ten. */
  function fmtG(x) {
    var word = nonFiniteWord(x);
    if (word !== null) return word;
    if (x === 0) return "0";
    var exp = parseInt(x.toExponential().split("e")[1], 10);
    var s;
    if (exp < -4 || exp >= 6) {
      s = x.toExponential(5);
      var parts = s.split("e");
      var mant = parts[0].replace(/\.?0+$/, "");
      var e = parseInt(parts[1], 10);
      var esign = e < 0 ? "-" : "+";
      var eabs = String(Math.abs(e));
      if (eabs.length < 2) eabs = "0" + eabs;
      return mant + "e" + esign + eabs;
    }
    s = x.toPrecision(6);
    if (s.indexOf(".") !== -1) s = s.replace(/\.?0+$/, "");
    return s;
  }

  // -------------------------------------------------------------------
  // Unit conversion
  // -------------------------------------------------------------------
  function lbToKg(lb) { return lb * KG_PER_LB; }
  function kgToLb(kg) { return kg / KG_PER_LB; }
  function inToCm(inches) { return inches * CM_PER_IN; }
  function cmToIn(cm) { return cm / CM_PER_IN; }

  function ftInToCm(feet, inches) {
    return inToCm(feet * IN_PER_FT + inches);
  }

  /* cm -> [whole feet, inches], rounded for display. Rounding happens
   * here so the 12-inch carry is handled in one place: 182.87 cm must
   * report 6 ft 0.0 in, never 5 ft 12.0 in. */
  function cmToFtIn(cm, inchDecimals) {
    if (inchDecimals === undefined) inchDecimals = 1;
    var totalInches = cmToIn(cm);
    var feet = Math.floor(totalInches / IN_PER_FT);
    var inches = pyRound(totalInches - feet * IN_PER_FT, inchDecimals);
    if (inches >= IN_PER_FT) {
      feet += 1;
      inches = pyRound(inches - IN_PER_FT, inchDecimals);
    }
    return [feet, inches];
  }

  /* Fold an overflowing inches value into feet: (5, 15) -> (6, 3). */
  function normalizeFtIn(feet, inches) {
    var totalInches = feet * IN_PER_FT + inches;
    var wholeFeet = Math.floor(totalInches / IN_PER_FT);
    return [wholeFeet, totalInches - wholeFeet * IN_PER_FT];
  }

  // -------------------------------------------------------------------
  // Formulas
  // -------------------------------------------------------------------
  function bmrMifflinStJeor(weightKg, heightCm, age, sex) {
    var base = 10 * weightKg + 6.25 * heightCm - 5 * age;
    return sex === "male" ? base + 5 : base - 161;
  }

  function bmrKatchMcArdle(weightKg, bodyFatPct) {
    var leanMassKg = weightKg * (1 - bodyFatPct / 100);
    return 370 + 21.6 * leanMassKg;
  }

  function tdeeFromBmr(bmr, activityFactor) { return bmr * activityFactor; }

  function bmi(weightKg, heightCm) {
    var heightM = heightCm / 100.0;
    return weightKg / (heightM * heightM);
  }

  function weightForBmi(targetBmi, heightCm) {
    var heightM = heightCm / 100.0;
    return targetBmi * (heightM * heightM);
  }

  function dailyCalorieDelta(kgPerWeek) {
    return (kgPerWeek * CAL_PER_KG_FAT) / 7;
  }

  // -------------------------------------------------------------------
  // Outcome constructors
  // -------------------------------------------------------------------
  function reject(code, field, title, message, context) {
    return {
      ok: false,
      code: code,
      field: field,
      title: title,
      message: message,
      context: context || {}
    };
  }

  // -------------------------------------------------------------------
  // Entry point
  // -------------------------------------------------------------------
  /* raw: {unit, sex, age, height_cm, height_ft, height_in, weight, goal,
   *       body_fat, activity_key, pace} - all strings.
   *
   * The validation order below mirrors calc_core.py exactly and is
   * load-bearing: it decides which error a user sees when more than one
   * field is wrong. Do not rearrange it casually. */
  function calculatePlan(raw) {
    var isImperial = raw.unit === IMPERIAL;
    var age, weight, goal, heightFt, heightIn, heightCm;

    try {
      age = pyFloat(raw.age);
      weight = pyFloat(raw.weight);
      goal = pyFloat(raw.goal);
      if (isImperial) {
        // Blank inches means a round number of feet, which is normal to
        // type. Blank feet is not - that's a missing input.
        heightFt = pyFloat(raw.height_ft);
        heightIn = String(raw.height_in).trim() ? pyFloat(raw.height_in) : 0.0;
        heightCm = ftInToCm(heightFt, heightIn);
      } else {
        heightFt = null;
        heightIn = null;
        heightCm = pyFloat(raw.height_cm);
      }
    } catch (e) {
      if (e !== PARSE_ERROR) throw e;
      return reject(
        "INVALID_NUMBER", "age", "Missing or invalid input",
        "Please enter valid numbers for age, height, current weight, " +
        "and goal weight."
      );
    }

    if (age <= 0 || heightCm <= 0 || weight <= 0 || goal <= 0) {
      return reject("NON_POSITIVE", "age", "Invalid input",
        "All values must be greater than zero.");
    }

    // Inches is a component, not a total: 0-11.99, with 12 rolling into
    // the feet field. Rejected rather than silently normalized.
    if (isImperial && !(heightIn >= 0 && heightIn < IN_PER_FT)) {
      var message = "The inches box takes 0 to " + (IN_PER_FT - 1) +
        "; whole feet go in the feet box.";
      var ctx = { height_ft: heightFt, height_in: heightIn };
      if (heightIn >= IN_PER_FT && isFinite(heightFt + heightIn)) {
        var norm = normalizeFtIn(heightFt, heightIn);
        message += "\n\n" + fmtG(heightFt) + " ft " + fmtG(heightIn) +
          " in is " + fmtG(norm[0]) + " ft " + fmtG(norm[1]) + " in.";
        ctx.suggested_ft = norm[0];
        ctx.suggested_in = norm[1];
      }
      return reject("HEIGHT_INCHES_RANGE", "height_in",
        "Inches out of range", message, ctx);
    }

    // Mifflin-St Jeor and the activity multipliers are adult figures.
    if (age < MIN_AGE || age > MAX_AGE) {
      return reject("AGE_RANGE", "age", "Age out of range",
        "This calculator supports ages " + MIN_AGE + "-" + MAX_AGE + ".\n\n" +
        "The formulas it uses are validated for adults only. If you are " +
        "under 18, please speak with a doctor or a registered dietitian " +
        "rather than using a calculator.",
        { min_age: MIN_AGE, max_age: MAX_AGE });
    }

    var unitLabel = isImperial ? "lb" : "kg";
    var weightKg = isImperial ? lbToKg(weight) : weight;
    var goalKg = isImperial ? lbToKg(goal) : goal;

    // Goal weight sanity check against a BMI floor.
    var goalBmi = bmi(goalKg, heightCm);
    if (goalBmi < MIN_GOAL_BMI) {
      var minGoalKg = weightForBmi(MIN_GOAL_BMI, heightCm);
      var minGoalDisplay = isImperial ? kgToLb(minGoalKg) : minGoalKg;
      return reject("GOAL_BMI", "goal", "Goal weight out of range",
        "A goal of " + fmtG(goal) + " " + unitLabel + " at your height " +
        "falls below a BMI of " + MIN_GOAL_BMI + ", the standard adult " +
        "underweight threshold.\n\n" +
        "This calculator will not generate a plan below roughly " +
        fmtFixed(minGoalDisplay, 0) + " " + unitLabel + ".\n\n" +
        "If you believe a lower target is right for you, that is a " +
        "conversation for a physician or registered dietitian.",
        {
          goal_bmi: goalBmi,
          min_goal_bmi: MIN_GOAL_BMI,
          min_goal_kg: minGoalKg,
          min_goal_display: minGoalDisplay
        });
    }

    // Optional body fat % -> chooses the BMR formula.
    var bodyFatRaw = String(raw.body_fat).trim();
    var bodyFatPct = null;
    var formula, bmrValue;
    if (bodyFatRaw) {
      try {
        bodyFatPct = pyFloat(bodyFatRaw);
      } catch (e2) {
        if (e2 !== PARSE_ERROR) throw e2;
        return reject("BODY_FAT_INVALID", "body_fat", "Invalid input",
          "Body fat % must be a number, or leave it blank.");
      }
      if (!(bodyFatPct > 0 && bodyFatPct < 75)) {
        return reject("BODY_FAT_RANGE", "body_fat", "Invalid input",
          "Body fat % should be a realistic value between 0 and 75.");
      }
      formula = "Katch-McArdle";
      bmrValue = bmrKatchMcArdle(weightKg, bodyFatPct);
    } else {
      formula = "Mifflin-St Jeor";
      bmrValue = bmrMifflinStJeor(weightKg, heightCm, age, raw.sex);
    }

    if (!Object.prototype.hasOwnProperty.call(ACTIVITY_LEVELS, raw.activity_key)) {
      return reject("ACTIVITY_INVALID", "activity_key", "Invalid input",
        "Please choose an activity level from the list.");
    }

    var tdee = tdeeFromBmr(bmrValue, ACTIVITY_LEVELS[raw.activity_key]);

    // Weekly pace: whole number, read in the active display unit.
    var pace;
    try {
      pace = pyInt(String(raw.pace).trim());
    } catch (e3) {
      if (e3 !== PARSE_ERROR) throw e3;
      return reject("PACE_INVALID", "pace", "Invalid pace",
        "Target pace must be a whole number.");
    }

    if (pace <= 0) {
      return reject("PACE_NON_POSITIVE", "pace", "Invalid pace",
        "Target pace must be greater than zero.");
    }

    var maxPace = isImperial ? MAX_PACE_LB : MAX_PACE_KG;
    if (pace > maxPace) {
      return reject("PACE_RANGE", "pace", "Pace out of range",
        "Maximum supported pace is " + maxPace + " " + unitLabel +
        " per week.\n\n" +
        "Faster rates fall outside the range this calculator's model " +
        "is valid for and would produce unreliable results.",
        { max_pace: maxPace });
    }

    var kgPerWeek = isImperial ? lbToKg(pace) : pace;
    var dailyDelta = dailyCalorieDelta(kgPerWeek);

    var weightDiffKg = goalKg - weightKg;  // positive = gain
    var direction, targetCalories, weeks;

    if (Math.abs(weightDiffKg) < 0.01) {
      direction = "maintain";
      targetCalories = tdee;
      weeks = 0.0;
    } else if (weightDiffKg > 0) {
      direction = "gain";
      targetCalories = tdee + dailyDelta;
      weeks = weightDiffKg / kgPerWeek;
    } else {
      direction = "lose";
      targetCalories = tdee - dailyDelta;
      weeks = Math.abs(weightDiffKg) / kgPerWeek;
    }

    // Hard floor. Blocks the plan rather than annotating it.
    if (direction !== "maintain" && targetCalories < CALORIE_FLOOR) {
      return reject("CALORIE_FLOOR", "pace", "No plan generated",
        "No plan generated.\n\n" +
        "The selected pace would require intake below " +
        fmtThousands(CALORIE_FLOOR) + " kcal/day for your inputs, which " +
        "is outside the range this tool will produce a plan for.\n\n" +
        "Try a slower pace, or speak with a healthcare provider.",
        {
          calorie_floor: CALORIE_FLOOR,
          target_calories: targetCalories,
          tdee: tdee
        });
    }

    return {
      ok: true,
      inputs: {
        unit: raw.unit,
        sex: raw.sex,
        age: age,
        height_cm: heightCm,
        height_ft: heightFt,
        height_in: heightIn,
        weight: weight,
        goal: goal,
        body_fat_pct: bodyFatPct,
        activity_key: raw.activity_key,
        pace: pace,
        unit_label: unitLabel
      },
      formula: formula,
      bmr: bmrValue,
      tdee: tdee,
      direction: direction,
      target_calories: targetCalories,
      daily_delta: dailyDelta,
      weeks: weeks,
      months: weeks / WEEKS_PER_MONTH
    };
  }

  // -------------------------------------------------------------------
  // Presentation - mirrors WeightCalculatorApp._format_plan
  // -------------------------------------------------------------------
  function formatPlan(plan) {
    var unitLabel = plan.inputs.unit_label;
    var lines = [
      "Formula used: " + plan.formula,
      "BMR (calories your body burns at rest): " +
        fmtThousands(plan.bmr) + " kcal/day",
      "TDEE (calories burned with activity): " +
        fmtThousands(plan.tdee) + " kcal/day",
      ""
    ];

    if (plan.direction === "maintain") {
      lines.push("You're already at your goal weight. Eat around " +
        fmtThousands(plan.tdee) + " kcal/day to maintain.");
      return lines;
    }

    var verb = plan.direction === "gain" ? "gain" : "lose";
    var noun = plan.direction === "gain" ? "surplus" : "deficit";
    lines.push("To " + verb + " weight at " + plan.inputs.pace + " " +
      unitLabel + "/week, aim for about " +
      fmtThousands(plan.target_calories) + " kcal/day.");
    lines.push("That's a daily " + noun + " of ~" +
      fmtThousands(plan.daily_delta) + " kcal vs. your maintenance level.");
    lines.push("");
    lines.push("Estimated time to reach " + fmtG(plan.inputs.goal) + " " +
      unitLabel + " from " + fmtG(plan.inputs.weight) + " " + unitLabel +
      ": ~" + fmtFloat(pyRound(plan.weeks, 1)) + " weeks (~" +
      fmtFloat(pyRound(plan.months, 1)) + " months).");
    lines.push("");
    lines.push("Note: this timeline assumes your maintenance level stays " +
      "constant. It falls as you lose weight, so real-world timelines " +
      "run longer.");
    return lines;
  }

  // -------------------------------------------------------------------
  global.WeightCalcCore = {
    ACTIVITY_LEVELS: ACTIVITY_LEVELS,
    ACTIVITY_ORDER: ACTIVITY_ORDER,
    KG_PER_LB: KG_PER_LB,
    CM_PER_IN: CM_PER_IN,
    IN_PER_FT: IN_PER_FT,
    CAL_PER_KG_FAT: CAL_PER_KG_FAT,
    WEEKS_PER_MONTH: WEEKS_PER_MONTH,
    MAX_PACE_LB: MAX_PACE_LB,
    MAX_PACE_KG: MAX_PACE_KG,
    CALORIE_FLOOR: CALORIE_FLOOR,
    MIN_AGE: MIN_AGE,
    MAX_AGE: MAX_AGE,
    MIN_GOAL_BMI: MIN_GOAL_BMI,
    IMPERIAL: IMPERIAL,
    METRIC: METRIC,

    pyFloat: pyFloat,
    pyInt: pyInt,
    pyRound: pyRound,
    fmtG: fmtG,
    fmtFloat: fmtFloat,
    fmtFixed: fmtFixed,
    fmtThousands: fmtThousands,

    lbToKg: lbToKg,
    kgToLb: kgToLb,
    inToCm: inToCm,
    cmToIn: cmToIn,
    ftInToCm: ftInToCm,
    cmToFtIn: cmToFtIn,
    normalizeFtIn: normalizeFtIn,

    bmrMifflinStJeor: bmrMifflinStJeor,
    bmrKatchMcArdle: bmrKatchMcArdle,
    tdeeFromBmr: tdeeFromBmr,
    bmi: bmi,
    weightForBmi: weightForBmi,
    dailyCalorieDelta: dailyCalorieDelta,

    calculatePlan: calculatePlan,
    formatPlan: formatPlan
  };
})(typeof window !== "undefined" ? window : this);
