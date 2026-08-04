#!/usr/bin/env python3
"""
Generate the PWA icons for web/icons/, using only the standard library.

Draws a gauge - white dial on the app's pastel pink, plum needle - and
writes flat RGB PNGs. The palette matches web/index.html. Regenerate
after changing the design:

    python tools/gen_icons.py

Sizes: 192 and 512 for the manifest (declared "any" and "maskable" -
the artwork stays inside the inner 80% safe zone, so a mask cannot
clip it) and 180 for the apple-touch-icon.
"""

import math
import os
import struct
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "web", "icons")

BG = (0xF4, 0xA6, 0xC6)    # --primary
DIAL = (0xFF, 0xFF, 0xFF)
PLUM = (0x5B, 0x42, 0x54)  # --text


def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path, size, rows):
    """rows: one bytearray of RGB triples per scanline."""
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(_chunk(b"IHDR",
                       struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)))
        f.write(_chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(_chunk(b"IEND", b""))


def seg_dist(px, py, ax, ay, bx, by):
    """Distance from point (px, py) to the segment (ax, ay)-(bx, by)."""
    vx, vy = bx - ax, by - ay
    t = ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def cov(d):
    """Signed distance in pixels -> pixel coverage, a 1px-wide ramp.

    This is the anti-aliasing: a pixel whose centre sits on the shape
    edge blends 50/50 instead of snapping to one side.
    """
    return max(0.0, min(1.0, 0.5 - d))


def mix(base, top, a):
    return tuple(round(b + (t - b) * a) for b, t in zip(base, top))


def render(size):
    n = float(size)
    cx = cy = n / 2.0
    dial_r = 0.30 * n
    needle_w = 0.032 * n
    hub_r = 0.048 * n
    # Needle sits at "mid-reading", the way an analog scale looks in use.
    ang = math.radians(-50.0)
    nx = cx + math.cos(ang) * dial_r * 0.66
    ny = cy + math.sin(ang) * dial_r * 0.66

    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            px, py = x + 0.5, y + 0.5
            c = BG
            c = mix(c, DIAL, cov(math.hypot(px - cx, py - cy) - dial_r))
            c = mix(c, PLUM, cov(seg_dist(px, py, cx, cy, nx, ny)
                                 - needle_w / 2.0))
            c = mix(c, PLUM, cov(math.hypot(px - cx, py - cy) - hub_r))
            row += bytes(c)
        rows.append(row)
    return rows


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, size in (("icon-192.png", 192),
                       ("icon-512.png", 512),
                       ("apple-touch-icon.png", 180)):
        path = os.path.join(OUT_DIR, name)
        write_png(path, size, render(size))
        print("wrote %s (%d bytes)"
              % (os.path.relpath(path, REPO), os.path.getsize(path)))


if __name__ == "__main__":
    main()
