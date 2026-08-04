#!/usr/bin/env node
/*
 * Headless runner for web/selftest.html's checks.
 * ------------------------------------------------
 * Runs calc_core.js against fixture.js with no browser, and exits
 * non-zero on any mismatch, so CI can block a deploy on it.
 *
 * WHY THIS EXISTS
 *
 * The deploy pipeline used to verify the Python side and the freshness
 * of fixture.js, then publish web/ without ever executing a line of the
 * JavaScript. That caught calc_core.py drifting away from fixture.js,
 * but not calc_core.js drifting away from it - the direction the
 * self-test is actually for. A broken port could go green and ship, and
 * the only thing standing in the way was somebody remembering to open
 * selftest.html by hand.
 *
 * The checks are NOT reimplemented here. They live in web/selftest.js
 * and this file only loads and reports them, so the CI gate and the
 * page a human opens can never disagree about what passing means.
 *
 * Usage:  node tools/run_selftest.js
 */
"use strict";

var fs = require("fs");
var path = require("path");

var WEB = path.join(__dirname, "..", "web");
var SCRIPTS = ["calc_core.js", "fixture.js", "selftest.js"];

// All three are plain <script> files that hang their exports off
// `window`. Handing each one a shared object under that name runs them
// unmodified - no build step, no module wrapper, and no second copy of
// anything that could drift from what the browser loads.
var win = {};
SCRIPTS.forEach(function (name) {
  var file = path.join(WEB, name);
  var src;
  try {
    src = fs.readFileSync(file, "utf8");
  } catch (err) {
    console.error("::error file=web/" + name + "::cannot read " + file +
                  " (" + err.message + ")");
    process.exit(2);
  }
  try {
    new Function("window", src)(win);
  } catch (err) {
    console.error("::error file=web/" + name + "::failed to evaluate: " +
                  err.stack);
    process.exit(2);
  }
});

if (!win.WeightCalcCore || !win.WEB_FIXTURE || !win.WeightCalcSelfTest) {
  // A file loaded but did not export what it should - a rename or a
  // botched refactor. Fail loudly rather than reporting zero checks.
  console.error("::error::web/ scripts loaded but did not define the " +
                "expected globals (WeightCalcCore, WEB_FIXTURE, " +
                "WeightCalcSelfTest)");
  process.exit(2);
}

var result = win.WeightCalcSelfTest.runSelfTest(
  win.WeightCalcCore, win.WEB_FIXTURE
);

function pad(s, n) {
  s = String(s);
  return s.length >= n ? s : s + new Array(n - s.length + 1).join(" ");
}
function padLeft(s, n) {
  s = String(s);
  return s.length >= n ? s : new Array(n - s.length + 1).join(" ") + s;
}

console.log(pad("group", 46) + padLeft("checks", 10) + padLeft("mismatches", 13));
result.groups.forEach(function (g) {
  console.log(pad(g.label, 46) + padLeft(g.total.toLocaleString("en-US"), 10) +
              padLeft(g.fail.toLocaleString("en-US"), 13));
});
console.log("");

if (result.fail === 0) {
  console.log("PASS - " + result.total.toLocaleString("en-US") +
              " checks, 0 mismatches (" +
              result.planCases.toLocaleString("en-US") + " plan cases)");
  process.exit(0);
}

console.log("First " + result.failures.length + " mismatches:\n");
result.failures.forEach(function (f) {
  console.log(f.group + " :: " + f.name);
  console.log("  expected: " + JSON.stringify(f.expected));
  console.log("  actual  : " + JSON.stringify(f.actual));
  if (f.ctx) console.log("  input   : " + JSON.stringify(f.ctx));
  console.log("");
});

console.error("::error file=web/calc_core.js::" +
  result.fail.toLocaleString("en-US") + " of " +
  result.total.toLocaleString("en-US") + " self-test checks mismatched. " +
  "web/calc_core.js disagrees with web/fixture.js, which is generated " +
  "from calc_core.py - the two implementations have drifted apart.");
process.exit(1);
