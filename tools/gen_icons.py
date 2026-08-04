#!/usr/bin/env python3
"""
Generate the PWA icons for apps/web/icons/, using only the standard library.

The artwork - a man and a woman standing on a scale - comes from a
vector illustration supplied by the project owner; its SVG path data
is embedded below and recolored to the brand palette: white
silhouettes and a plum scale on the brand pink. This script is a tiny
SVG rasterizer (absolute M/L/C/Z commands only): it flattens the
cubic beziers to polygons, scanline-fills them with the nonzero
winding rule at a supersampled resolution, and box-downsamples for
anti-aliasing. Regenerate after any change:

    python tools/gen_icons.py

Sizes: 192 and 512 for the manifest (declared "any" and "maskable")
and 180 for the apple-touch-icon. The artwork is shrunk slightly
(CONTENT_SCALE) so the tops of the heads sit inside the maskable safe
zone - the source drawing grazes its edge.
"""

import math
import os
import re
import struct
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "apps", "web", "icons")

BG = (0xF4, 0xA6, 0xC6)     # brand pink
WHITE = (0xFF, 0xFF, 0xFF)  # the two figures, and the scale's display
PLUM = (0x5B, 0x42, 0x54)   # the scale

SRC = 1024.0        # coordinate space of the source drawing
CONTENT_SCALE = 0.92  # shrink toward centre to clear the maskable zone

# --- Source path data (SVG "d" strings), grouped by what they become.
# The original colors distinguished shirt/trousers/skin; flattened to
# silhouettes here, the split that matters is scale vs. dots vs. people.

SCALE_BAR = (
    "M261.053 748.755L651.183 748.955L786.021 748.862L829.888 748.798"
    "C837.71 748.788 845.495 748.764 853.323 748.934"
    "C860.179 748.745 866.993 757.12 866.268 763.818"
    "C860.683 815.386 815.063 848.055 766.255 848.034L400.375 847.987"
    "L297.905 848.001C282.289 848.012 266.291 848.348 250.74 847.836"
    "C205.654 846.352 163.24 809.916 159.281 764.219"
    "C158.719 757.724 163.492 749.681 170.578 749.31"
    "C180.724 748.462 191.348 748.798 201.664 748.803L261.053 748.755Z"
)

DOTS = [
    "M446.797 778.535C454.311 776.981 462.08 779.596 467.125 785.378"
    "C472.17 791.16 473.708 799.211 471.15 806.446"
    "C468.591 813.68 462.334 818.975 454.776 820.3"
    "C443.333 822.306 432.398 814.758 430.218 803.347"
    "C428.039 791.936 435.421 780.888 446.797 778.535Z",
    "M570.072 778.786C581.551 776.429 592.753 783.875 595.023 795.371"
    "C597.293 806.868 589.762 818.013 578.249 820.196"
    "C566.858 822.356 555.858 814.923 553.612 803.548"
    "C551.366 792.174 558.715 781.118 570.072 778.786Z",
    "M508.575 778.714C520.048 776.544 531.1 784.113 533.224 795.595"
    "C535.348 807.078 527.734 818.099 516.243 820.177"
    "C504.818 822.242 493.873 814.681 491.762 803.264"
    "C489.65 791.848 497.166 780.872 508.575 778.714Z",
]

FIGURES = [
    # Man: torso and raised arms
    "M326.68 340.522C323.556 365.085 318.295 394.242 314.194 418.856"
    "L308.53 451.175C306.215 464.999 306.751 482.728 289.968 487.368"
    "C283.314 489.141 276.226 488.153 270.31 484.63"
    "C259.791 478.503 257.745 470.004 259.598 458.821"
    "C261.531 447.151 263.512 435.465 265.442 423.793L276.219 357.785"
    "L284.105 309.802C286.279 296.471 286.582 284.133 293.623 272.302"
    "C302.226 258.036 316.191 247.817 332.391 243.933"
    "C343.452 241.22 361.567 242.058 373.391 242.143"
    "C388.825 242.301 404.261 242.376 419.696 242.369"
    "C429.59 242.36 439.484 242.281 449.376 242.133"
    "C465.576 241.937 477.146 240.933 491.551 249.699"
    "C504.874 257.806 513.82 270.154 517.004 285.495"
    "C519.466 297.353 521.075 309.223 523.114 321.081"
    "C528.183 350.728 532.925 380.431 537.341 410.183L543.155 446.989"
    "C544.069 453.084 545.697 461.202 545.525 467.046"
    "C544.675 485.197 524.948 494.786 510.264 483.766"
    "C501.356 477.081 501.71 466.645 500.23 456.475L495.556 424.803"
    "C491.262 396.18 486.124 367.821 481.874 339.145"
    "C481.235 339.418 481.246 339.352 480.85 339.85"
    "C481.247 355.316 481.08 371.143 481.158 386.653"
    "C481.376 413.56 481.446 440.468 481.367 467.376L327.78 467.228"
    "L327.91 386.256C327.15 379.337 328.243 342.995 326.68 340.522Z",
    # Woman: dress
    "M670.127 246.057C672.821 246.187 686.939 246.943 688.916 247.643"
    "L687.646 248.021C687.351 250.04 688.243 266.548 688.494 269.11"
    "C689.611 280.493 689.192 297.567 691.302 308.458"
    "C691.546 309.473 691.751 310.353 691.938 311.386"
    "C690.722 313.434 691.012 314.141 690.556 316.546"
    "C690.114 329.591 690.706 342.939 690.106 356.343"
    "C689.545 368.883 688.544 383.439 688.982 395.863"
    "C689.106 399.405 692.917 410.69 694.095 414.572"
    "C696.394 422.151 698.581 429.764 700.655 437.408"
    "C712.636 480.524 724.912 523.557 737.483 566.505"
    "C664.889 567.061 592.293 567.05 519.699 566.472"
    "C524.111 549.783 529.15 533.1 533.568 516.394"
    "C535.345 509.677 537.69 503.086 539.285 496.301"
    "C541.76 493.756 545.104 491.068 547.417 488.77"
    "C560.12 476.148 553.993 459.276 552.734 443.984"
    "C553.23 439.97 554.6 436.158 555.606 432.239"
    "C557.921 420.892 563.935 406.874 565.225 395.601"
    "C566.229 386.818 564.149 370.778 563.686 361.518"
    "C562.979 345.031 562.606 328.532 562.566 312.03"
    "C562.348 309.292 562.818 308.023 561.686 305.857"
    "C561.832 304.927 561.955 304.349 562.183 303.431"
    "C563.527 297.814 563.876 285.121 564.198 278.957L566.05 247.125"
    "C571.128 246.666 576.17 246.151 581.268 246.008"
    "C610.692 245.992 640.752 246.355 670.127 246.057Z",
    # Woman: neckline
    "M581.268 246.008C610.692 245.992 640.752 246.355 670.127 246.057"
    "C669.92 247.608 669.421 248.723 668.842 250.152"
    "C664.272 261.321 655.46 270.222 644.337 274.903"
    "C624.754 283.136 598.979 277.449 587.447 258.784"
    "C584.916 254.688 583.098 250.451 581.268 246.008Z",
    # Man: legs
    "M324.611 476.535L484.046 476.534L483.476 740.456L424.496 740.43"
    "L424.457 590.25L424.454 531.865"
    "C411.108 531.732 397.762 531.71 384.417 531.799"
    "C383.665 557.331 384.277 585.468 384.306 611.19L384.133 740.415"
    "L324.997 740.396L324.925 590.636"
    "C325.174 552.602 325.07 514.567 324.611 476.535Z",
    # Man: head
    "M397.834 101.711C432.549 98.1215 463.623 123.295 467.316 157.999"
    "C471.01 192.703 445.929 223.853 411.236 227.65"
    "C376.397 231.463 345.085 206.253 341.376 171.402"
    "C337.668 136.551 362.972 105.315 397.834 101.711Z",
    # Woman: head
    "M617.902 101.86C652.569 97.5447 684.165 122.166 688.452 156.837"
    "C692.739 191.508 668.091 223.083 633.417 227.341"
    "C598.783 231.595 567.252 206.982 562.97 172.352"
    "C558.689 137.722 583.275 106.171 617.902 101.86Z",
    # Woman: right arm
    "M691.302 308.458C689.192 297.567 689.611 280.493 688.494 269.11"
    "C688.243 266.548 687.351 250.04 687.646 248.021L688.916 247.643"
    "C703.466 250.708 716.444 257.688 724.812 270.188"
    "C733.569 283.27 736.316 302.594 740.11 317.837L756.032 381.622"
    "L769.26 434.941C773.637 452.478 787.014 483.883 757.336 489.629"
    "C746.857 491.658 735.576 485.187 732.91 474.746"
    "C729.807 462.984 727.086 451.002 724.146 439.192L702.406 352.504"
    "C699.302 340.253 695.621 323.061 691.938 311.386"
    "C691.751 310.353 691.546 309.473 691.302 308.458Z",
    # Woman: left leg
    "M564.754 573.237C582.433 573.171 600.112 573.204 617.791 573.338"
    "C618.754 626.226 617.314 679.434 618.038 732.35"
    "C618.069 734.595 618.194 738.679 617.581 740.625L616.59 740.948"
    "L563.639 740.921L563.658 623.196L563.717 589.652"
    "C563.721 586.452 563.533 576.591 563.953 573.778L564.754 573.237Z",
    # Woman: right leg
    "M636.044 573.136L688.981 573.183L688.98 740.898"
    "C671.627 741.208 653.507 740.963 636.091 740.988L636.044 573.136Z",
    # Woman: left arm
    "M566.05 247.125L564.198 278.957"
    "C563.876 285.121 563.527 297.814 562.183 303.431"
    "C561.955 304.349 561.832 304.927 561.686 305.857"
    "C555.904 326.959 549.332 350.837 542.757 371.649L542.328 373.337"
    "L541.515 372.897L541.645 371.401"
    "C537.862 350.613 535.073 329.506 530.893 308.72"
    "C528.889 298.753 527.517 289.073 524.773 279.191"
    "C531.591 262.101 548.789 251.275 566.05 247.125Z",
]


# ---------------------------------------------------------------------------
# Minimal SVG path parsing (absolute M/L/C/Z only) and flattening
# ---------------------------------------------------------------------------
_TOKEN = re.compile(r"[MLCZ]|-?\d*\.?\d+(?:[eE][+-]?\d+)?")

CURVE_STEPS = 16


def parse_path(d):
    """d string -> list of closed polygons [(x, y), ...] in SRC space."""
    tokens = _TOKEN.findall(d)
    polys = []
    points = []
    cur = (0.0, 0.0)
    i = 0
    while i < len(tokens):
        cmd = tokens[i]
        if cmd == "M":
            if len(points) > 2:
                polys.append(points)
            cur = (float(tokens[i + 1]), float(tokens[i + 2]))
            points = [cur]
            i += 3
        elif cmd == "L":
            cur = (float(tokens[i + 1]), float(tokens[i + 2]))
            points.append(cur)
            i += 3
        elif cmd == "C":
            p1 = (float(tokens[i + 1]), float(tokens[i + 2]))
            p2 = (float(tokens[i + 3]), float(tokens[i + 4]))
            p3 = (float(tokens[i + 5]), float(tokens[i + 6]))
            x0, y0 = cur
            for s in range(1, CURVE_STEPS + 1):
                t = s / float(CURVE_STEPS)
                u = 1.0 - t
                x = (u * u * u * x0 + 3 * u * u * t * p1[0]
                     + 3 * u * t * t * p2[0] + t * t * t * p3[0])
                y = (u * u * u * y0 + 3 * u * u * t * p1[1]
                     + 3 * u * t * t * p2[1] + t * t * t * p3[1])
                points.append((x, y))
            cur = p3
            i += 7
        elif cmd == "Z":
            if len(points) > 2:
                polys.append(points)
            points = []
            i += 1
        else:  # a stray number would mean an unsupported command form
            raise ValueError("unexpected token %r" % cmd)
    if len(points) > 2:
        polys.append(points)
    return polys


def build_edges(d_strings, render_size):
    """Parse, transform into render space, and return edge list."""
    scale = render_size / SRC * CONTENT_SCALE
    off = render_size * (1.0 - CONTENT_SCALE) / 2.0
    edges = []
    for d in d_strings:
        for poly in parse_path(d):
            pts = [(x * scale + off, y * scale + off) for x, y in poly]
            for j in range(len(pts)):
                x0, y0 = pts[j]
                x1, y1 = pts[(j + 1) % len(pts)]
                if y0 != y1:
                    edges.append((x0, y0, x1, y1))
    return edges


def fill_edges(rows, render_size, edges, color):
    """Nonzero-winding scanline fill of `edges` into `rows` (RGB
    bytearrays), one intersection pass per scanline."""
    # Bucket edges by the scanlines they cross, so each row only looks
    # at edges that matter to it.
    buckets = [[] for _ in range(render_size)]
    for e in edges:
        y_lo = max(0, int(math.floor(min(e[1], e[3]) - 0.5)))
        y_hi = min(render_size - 1, int(math.ceil(max(e[1], e[3]) - 0.5)))
        for yy in range(y_lo, y_hi + 1):
            buckets[yy].append(e)

    cbytes = bytes(color)
    for y in range(render_size):
        yc = y + 0.5
        hits = []
        for x0, y0, x1, y1 in buckets[y]:
            if (y0 <= yc < y1) or (y1 <= yc < y0):
                t = (yc - y0) / (y1 - y0)
                hits.append((x0 + t * (x1 - x0), 1 if y1 > y0 else -1))
        if not hits:
            continue
        hits.sort()
        row = rows[y]
        winding = 0
        span_start = 0.0
        for x, direction in hits:
            if winding != 0:
                px0 = max(0, int(math.ceil(span_start - 0.5)))
                px1 = min(render_size - 1, int(math.floor(x - 0.5)))
                if px1 >= px0:
                    row[px0 * 3:(px1 + 1) * 3] = cbytes * (px1 - px0 + 1)
            winding += direction
            if winding != 0 and (winding - direction) == 0:
                span_start = x


# ---------------------------------------------------------------------------
# PNG output
# ---------------------------------------------------------------------------
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


def render(size):
    """Rasterize at a multiple of the target size, then box-downsample
    - that averaging is the anti-aliasing."""
    ss = 2 if size >= 384 else 4
    rs = size * ss

    rows = [bytearray(bytes(BG) * rs) for _ in range(rs)]
    fill_edges(rows, rs, build_edges([SCALE_BAR], rs), PLUM)
    fill_edges(rows, rs, build_edges(DOTS + FIGURES, rs), WHITE)

    out = []
    area = ss * ss
    for y in range(size):
        row = bytearray()
        for x in range(size):
            r = g = b = 0
            for sy in range(ss):
                src = rows[y * ss + sy]
                base = x * ss * 3
                for sx in range(ss):
                    r += src[base + sx * 3]
                    g += src[base + sx * 3 + 1]
                    b += src[base + sx * 3 + 2]
            row += bytes(((r + area // 2) // area,
                          (g + area // 2) // area,
                          (b + area // 2) // area))
        out.append(row)
    return out


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
