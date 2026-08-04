/*
 * Weight Goal Calculator - core self-test, the checks themselves
 * ---------------------------------------------------------------
 * Compares calc_core.js against fixture.js, which is generated from
 * calc_core.py by tools/gen_web_fixture.py. Any mismatch is porting
 * drift between the two implementations.
 *
 * No DOM, no I/O: runSelfTest(core, fixture) takes both as arguments and
 * returns a result object. selftest.html renders that in a browser and
 * tools/run_selftest.js runs it headlessly in CI, so the gate that
 * blocks a deploy and the page a human opens are running the same
 * checks. Splitting them into two copies is exactly the kind of quiet
 * drift this file exists to catch.
 */
(function (global) {
  "use strict";

  /* Exact match including NaN === NaN and -0 vs 0. */
  function same(a, b) {
    if (typeof a === "number" && typeof b === "number") {
      if (Number.isNaN(a) && Number.isNaN(b)) return true;
      return a === b;
    }
    return a === b;
  }

  function runSelfTest(C, F) {
    var groups = [];
    var failures = [];

    function check(group, name, actual, expected, ctx) {
      var g = groups[groups.length - 1];
      g.total++;
      if (same(actual, expected)) { g.pass++; return true; }
      g.fail++;
      if (failures.length < 25) {
        failures.push({
          group: group, name: name,
          expected: expected, actual: actual, ctx: ctx
        });
      }
      return false;
    }

    function startGroup(label) {
      groups.push({ label: label, total: 0, pass: 0, fail: 0 });
      return label;
    }

    // -----------------------------------------------------------------
    // 1. Constants
    // -----------------------------------------------------------------
    var g = startGroup("constants");
    Object.keys(F.constants).forEach(function (k) {
      check(g, k, C[k], F.constants[k]);
    });
    Object.keys(F.activity_levels).forEach(function (k) {
      check(g, "activity " + k, C.ACTIVITY_LEVELS[k], F.activity_levels[k]);
    });

    // -----------------------------------------------------------------
    // 1b. Number helpers, tested directly.
    // The plan grid does not reach these: no input in it produces an
    // exact rounding tie, and every value it formats renders the same
    // under Python and naive JS. Without this group, a port could drop
    // round-half-to-even and :g entirely and still show PASS.
    // -----------------------------------------------------------------
    g = startGroup("number helpers (pyRound / fmtG / fmtFixed)");
    F.helpers.py_round.forEach(function (c) {
      check(g, "pyRound(" + c.x + ", " + c.n + ")",
            C.pyRound(c.x, c.n), c.expected, c);
    });
    F.helpers.fmt_g.forEach(function (c) {
      check(g, "fmtG(" + c.x + ")", C.fmtG(c.x), c.expected, c);
    });
    F.helpers.fmt_fixed.forEach(function (c) {
      check(g, "fmtFixed(" + c.x + ", " + c.n + ")",
            C.fmtFixed(c.x, c.n), c.expected, c);
    });
    F.helpers.fmt_thousands.forEach(function (c) {
      check(g, "fmtThousands(" + c.x + ")",
            C.fmtThousands(c.x), c.expected, c);
    });

    // -----------------------------------------------------------------
    // 2. Height conversions
    // -----------------------------------------------------------------
    g = startGroup("ft_in_to_cm / normalize_ft_in");
    F.conversions.ft_in_to_cm.forEach(function (c) {
      var label = c.feet + "ft " + c.inches + "in";
      check(g, label + " -> cm", C.ftInToCm(c.feet, c.inches), c.cm, c);
      var n = C.normalizeFtIn(c.feet, c.inches);
      check(g, label + " -> norm ft", n[0], c.normalized[0], c);
      check(g, label + " -> norm in", n[1], c.normalized[1], c);
    });

    g = startGroup("cm_to_ft_in");
    F.conversions.cm_to_ft_in.forEach(function (c) {
      var r = C.cmToFtIn(c.cm);
      check(g, c.cm + "cm -> ft", r[0], c.feet, c);
      check(g, c.cm + "cm -> in", r[1], c.inches, c);
    });

    // -----------------------------------------------------------------
    // 3. calculatePlan across the full fixture grid
    // -----------------------------------------------------------------
    var PLAN_FIELDS = ["formula", "bmr", "tdee", "direction",
                       "target_calories", "daily_delta", "weeks", "months"];

    g = startGroup("calculatePlan");
    F.plans.forEach(function (c, idx) {
      var got;
      try {
        got = C.calculatePlan(c.i);
      } catch (err) {
        check(g, "case " + idx + " threw", String(err), "(no throw)", c.i);
        return;
      }
      var want = c.o;
      if (!check(g, "case " + idx + " ok", got.ok, want.ok, c.i)) return;

      if (want.ok) {
        PLAN_FIELDS.forEach(function (f) {
          check(g, "case " + idx + " " + f, got[f], want[f], c.i);
        });
        check(g, "case " + idx + " height_cm",
              got.inputs.height_cm, want.height_cm, c.i);
        check(g, "case " + idx + " unit_label",
              got.inputs.unit_label, want.unit_label, c.i);
        if (want.formatted) {
          var lines = C.formatPlan(got);
          check(g, "case " + idx + " formatted line count",
                lines.length, want.formatted.length, c.i);
          want.formatted.forEach(function (want_line, li) {
            check(g, "case " + idx + " formatted[" + li + "]",
                  lines[li], want_line, c.i);
          });
        }
      } else {
        check(g, "case " + idx + " code", got.code, want.code, c.i);
        check(g, "case " + idx + " field", got.field, want.field, c.i);
        check(g, "case " + idx + " title", got.title, want.title, c.i);
        check(g, "case " + idx + " message", got.message, want.message, c.i);
        Object.keys(want.context).forEach(function (k) {
          check(g, "case " + idx + " context." + k,
                got.context[k], want.context[k], c.i);
        });
        check(g, "case " + idx + " context keys",
              Object.keys(got.context).sort().join(","),
              Object.keys(want.context).sort().join(","), c.i);
      }
    });

    // -----------------------------------------------------------------
    // 4. Never throws
    // -----------------------------------------------------------------
    g = startGroup("never throws");
    var junk = ["", " ", "abc", "0", "-1", "1e400", "nan", "inf", "1_0",
                "0x10", "1.5", "999999999", "١٢", "null", "undefined"];
    var checked = 0;
    junk.forEach(function (a) {
      junk.forEach(function (b) {
        ["imperial", "metric"].forEach(function (u) {
          var threw = false;
          try {
            C.calculatePlan({
              unit: u, sex: "female", age: a, height_cm: b, height_ft: b,
              height_in: a, weight: b, goal: a, body_fat: b,
              activity_key: C.ACTIVITY_ORDER[0], pace: a
            });
          } catch (err) { threw = String(err); }
          checked++;
          if (threw !== false) check(g, "threw on " + a + "/" + b, threw, false);
        });
      });
    });
    check(g, "sweep size", checked > 300, true);

    // -----------------------------------------------------------------
    var total = 0, pass = 0, fail = 0;
    groups.forEach(function (x) {
      total += x.total; pass += x.pass; fail += x.fail;
    });

    return {
      total: total, pass: pass, fail: fail,
      planCases: F.plans.length,
      groups: groups, failures: failures
    };
  }

  global.WeightCalcSelfTest = { runSelfTest: runSelfTest };
})(typeof window !== "undefined" ? window : this);
