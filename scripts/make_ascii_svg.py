#!/usr/bin/env python3
"""
make_ascii_svg.py
Downsample source-prepped.png to a character grid, map each cell's brightness to
a glyph from a density ramp (bright -> sparse, dark -> dense), and emit a
monochrome SVG that "types" itself: each row wipes left-to-right on a small
top-to-bottom stagger, plays once, and freezes. SMIL animation, so GitHub plays
it inside <img>.
"""

import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "..", "source-prepped.png")
OUT = os.path.join(HERE, "..", "portrait.svg")

# bright (sparse) -> dark (dense). Leading space clears the white background.
RAMP = " .`:-=+*cs#%@"

COLS = 100          # character columns
CHAR_ASPECT = 0.52  # glyph height/width ratio for sampling correction
FONT_PX = 8
LINE_PX = 8         # line pitch (monospace, tight)
CHAR_PX = 4.8       # advance width at FONT_PX for the chosen mono metrics
INK = "#c9d1d9"     # light grey ink on the dark README background
CURSOR = "#39d353"  # green wipe cursor
FONT = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', monospace")

WIPE_DUR = 0.55     # seconds per row wipe
ROW_STAGGER = 0.055 # seconds between rows starting


def to_ascii_rows(path):
    img = Image.open(path).convert("L")
    w, h = img.size
    rows = max(1, int(COLS * (h / w) * CHAR_ASPECT))
    small = img.resize((COLS, rows), Image.BILINEAR)
    px = np.asarray(small, dtype=np.float32)

    n = len(RAMP) - 1
    lines = []
    for r in range(rows):
        chars = []
        for c in range(COLS):
            lum = px[r, c]
            idx = int(round((1.0 - lum / 255.0) * n))
            chars.append(RAMP[idx])
        # trim trailing spaces so rows don't carry empty width
        lines.append("".join(chars).rstrip())
    return lines


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build(lines):
    width = int(COLS * CHAR_PX) + 8
    height = int(len(lines) * LINE_PX) + 10

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
         f'height="{height}" viewBox="0 0 {width} {height}" '
         f'font-family="{FONT}" role="img" aria-label="ASCII portrait">']

    # defs: one animated clip rect per row (SMIL width 0 -> full, freeze)
    p.append("<defs>")
    for i, line in enumerate(lines):
        y = i * LINE_PX
        full = len(line) * CHAR_PX + 2
        begin = round(i * ROW_STAGGER, 3)
        p.append(
            f'<clipPath id="r{i}"><rect x="0" y="{y}" width="0" '
            f'height="{LINE_PX+2}">'
            f'<animate attributeName="width" from="0" to="{full:.1f}" '
            f'dur="{WIPE_DUR}s" begin="{begin}s" fill="freeze" '
            f'calcMode="linear"/></rect></clipPath>'
        )
    p.append("</defs>")

    # rows of text, each clipped by its animated rect
    for i, line in enumerate(lines):
        y = i * LINE_PX + FONT_PX
        if not line:
            continue
        p.append(
            f'<text x="4" y="{y}" font-size="{FONT_PX}px" fill="{INK}" '
            f'xml:space="preserve" clip-path="url(#r{i})" '
            f'style="white-space:pre">{esc(line)}</text>'
        )

    # green cursor block per row: rides the wipe edge, then vanishes
    for i, line in enumerate(lines):
        if not line:
            continue
        y = i * LINE_PX
        full = len(line) * CHAR_PX
        begin = round(i * ROW_STAGGER, 3)
        p.append(
            f'<rect x="4" y="{y}" width="{CHAR_PX:.1f}" height="{FONT_PX}" '
            f'fill="{CURSOR}" opacity="0.9">'
            f'<animate attributeName="x" from="4" to="{4+full:.1f}" '
            f'dur="{WIPE_DUR}s" begin="{begin}s" fill="freeze"/>'
            f'<animate attributeName="opacity" from="0.9" to="0" '
            f'dur="0.12s" begin="{round(begin+WIPE_DUR,3)}s" fill="freeze"/>'
            f'</rect>'
        )

    p.append("</svg>")
    return "\n".join(p)


def main():
    if not os.path.exists(SRC):
        print(f"missing {SRC} — run prep_photo.py first.")
        return
    lines = to_ascii_rows(SRC)
    svg = build(lines)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"Wrote {OUT}: {COLS}x{len(lines)} grid ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
