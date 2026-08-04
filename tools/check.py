#!/usr/bin/env python3
"""
Run everything CI runs, locally.

    python tools/check.py

A push to main is a release, so this exists to make "did I break it?"
one command instead of four remembered ones. It runs the same four
checks the deploy workflow gates on, in the same order, and exits
non-zero if any of them fails:

    1. the Python suite
    2. dev/fixture.js still matches core/calc_core.py
    3. apps/web/calc_core.js still matches dev/fixture.js
    4. apps/web is publishable (shell complete, references resolve)

2 and 3 guard opposite directions of the same drift. A stale fixture
would leave the self-test comparing the port against outdated
expectations and reporting a confident PASS, so checking only 3 is worse
than useless.

Needs node for step 3, the same as CI. Without it that step is reported
as skipped and the run fails, rather than passing on three checks out of
four and letting you believe you ran the gate. Opening dev/selftest.html
in a browser runs the same checks out of the same file.
"""

import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(label, argv):
    print("\n=== %s ===" % label, flush=True)
    result = subprocess.run(argv, cwd=REPO)
    return result.returncode == 0


def fixture_is_current():
    """Regenerate the fixture in place and see whether git says it moved.

    Uses git rather than a byte comparison because the fixture contains
    NaN, and any comparison that parses it has to handle NaN != NaN. The
    file is committed, so "did regenerating change it?" is exactly the
    question git already answers.
    """
    print("\n=== dev/fixture.js is current ===", flush=True)
    if subprocess.run(["git", "rev-parse", "--git-dir"], cwd=REPO,
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode != 0:
        print("not a git checkout - cannot tell whether the fixture moved")
        return False

    gen = subprocess.run([sys.executable, "tools/gen_web_fixture.py"],
                         cwd=REPO)
    if gen.returncode != 0:
        return False

    changed = subprocess.run(
        ["git", "diff", "--quiet", "--", "dev/fixture.js"], cwd=REPO
    ).returncode != 0

    if changed:
        print("\ndev/fixture.js changed when regenerated: core/calc_core.py "
              "has moved and the committed fixture is stale. The self-test "
              "would be checking the port against outdated expectations. "
              "Commit the regenerated file.")
        return False

    print("fixture matches the current core/calc_core.py")
    return True


def main():
    results = []

    results.append(("Python suite", run(
        "Python suite",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]
    )))

    results.append(("fixture freshness", fixture_is_current()))

    node = shutil.which("node")
    if node:
        results.append(("browser core self-test", run(
            "browser core self-test", [node, "tools/run_selftest.js"]
        )))
    else:
        print("\n=== browser core self-test ===")
        print("SKIPPED - node is not on PATH. This is the only step that "
              "executes the JavaScript being deployed, so the run below is "
              "reported as failed rather than passing on three checks out "
              "of four.\n"
              "Either install node, or open dev/selftest.html in a browser: "
              "it runs the same checks out of the same file and should "
              "report PASS with zero mismatches.")
        results.append(("browser core self-test", False))

    results.append(("apps/web publishable", run(
        "apps/web publishable", [sys.executable, "tools/check_web.py"]
    )))

    print("\n" + "=" * 52)
    for label, ok in results:
        print("%-40s %s" % (label, "ok" if ok else "FAILED"))
    print("=" * 52)

    if all(ok for _, ok in results):
        print("\nAll checks passed. Safe to push - remember that a push to "
              "main publishes the site.")
        return 0

    print("\nNot safe to push.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
