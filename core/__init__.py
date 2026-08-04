"""The calculation core, shared by every front-end.

`calc_core.py` owns all the arithmetic and every accept/reject decision.
It imports no UI code and does no I/O, which is what lets the tests, the
fixture generator, and the desktop app all use the same module without
dragging tkinter along.

The browser port lives at apps/web/calc_core.js rather than here: it has
to be served from the site root, and keeping it inside apps/web is what
lets the deploy publish that directory untouched.
"""
