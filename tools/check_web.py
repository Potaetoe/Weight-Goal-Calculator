#!/usr/bin/env python3
"""
Check that apps/web is internally consistent and safe to publish.

    python tools/check_web.py

Replaces a hand-maintained list of twelve `test -f` lines in the deploy
workflow. That list had the flaw every hand-maintained list has: it only
knew about files somebody remembered to add to it, so a new page could
ship uncached and a renamed one could ship broken.

Two checks, both derived from what is actually in the directory:

1. The service worker's SHELL lists every file in apps/web (except
   sw.js itself, which the browser fetches directly). Both directions
   are failures:
     - a file missing from SHELL is not cached, so the installed app
       breaks offline - invisible online, which is why nobody notices
     - a SHELL entry with no file behind it makes cache.addAll() reject,
       and a rejected install means no offline support at all

2. Every local href/src in the HTML resolves to a file that exists. A
   rename that misses one reference publishes a page that 404s its own
   stylesheet or core and renders a dead form.
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(REPO, "apps", "web")

# Fetched by the browser before any cache exists, so it is never a
# member of the shell it defines.
NOT_IN_SHELL = {"sw.js"}


def files_on_disk():
    """Every file under apps/web, as posix paths relative to it."""
    found = set()
    for root, _dirs, names in os.walk(WEB):
        for name in names:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, WEB).replace(os.sep, "/")
            found.add(rel)
    return found


def shell_entries():
    """The SHELL array from sw.js, minus the "./" directory alias.

    Parsed rather than imported because sw.js is a service worker, not a
    module - and a regex over a literal array is honest about how little
    is being read here.
    """
    src = open(os.path.join(WEB, "sw.js"), encoding="utf-8").read()
    match = re.search(r"var SHELL = \[(.*?)\];", src, re.S)
    if not match:
        sys.exit("could not find the SHELL array in sw.js - has it been "
                 "renamed? This check is worthless if it silently finds "
                 "nothing, so it fails instead.")
    entries = re.findall(r'"([^"]+)"', match.group(1))
    if not entries:
        sys.exit("sw.js declares an empty SHELL - refusing to pass")
    # "./" is index.html under another name; the directory index is not a
    # separate file to look for on disk.
    return set(entries) - {"./"}


def html_references():
    """(page, target) for every local href/src in apps/web's HTML."""
    refs = []
    for name in sorted(os.listdir(WEB)):
        if not name.endswith(".html"):
            continue
        text = open(os.path.join(WEB, name), encoding="utf-8").read()
        # Strip comments first: the note in index.html's footer mentions
        # dev/selftest.html, which deliberately does not exist here.
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        for target in re.findall(r'(?:href|src)="([^"]+)"', text):
            if re.match(r"^(?:https?:)?//|^mailto:|^#|^data:", target):
                continue
            refs.append((name, target.split("?", 1)[0].split("#", 1)[0]))
    return refs


def main():
    problems = []

    on_disk = files_on_disk() - NOT_IN_SHELL
    shell = shell_entries()

    for missing in sorted(on_disk - shell):
        problems.append(
            "%s is in apps/web but not in sw.js's SHELL, so the installed "
            "app will not have it offline" % missing)

    for stale in sorted(shell - on_disk):
        problems.append(
            "sw.js's SHELL lists %s, which does not exist - cache.addAll() "
            "will reject and the service worker will fail to install"
            % stale)

    for page, target in html_references():
        if not os.path.exists(os.path.join(WEB, target.replace("/", os.sep))):
            problems.append("%s references %s, which does not exist"
                            % (page, target))

    if problems:
        for p in problems:
            print("::error file=apps/web/sw.js::%s" % p)
        print("\napps/web FAILED %d check(s)" % len(problems))
        return 1

    print("apps/web OK - %d files, all in the shell, all references resolve"
          % len(on_disk))
    return 0


if __name__ == "__main__":
    sys.exit(main())
