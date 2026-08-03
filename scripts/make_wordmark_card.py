#!/usr/bin/env python3
"""
make_wordmark_card.py
Render the word "Ugur" as a 3D ASCII wordmark inside a terminal window and emit
info-card.svg. Letters are defined as stroked vector paths (no font/PIL needed),
sampled onto a monospace character grid: coverage picks a glyph from a density
ramp, and an offset copy of the mask becomes the extruded side wall.

The card types itself on — one row wipe per line, top to bottom, with a green
cursor riding the edge — using SMIL, so GitHub plays it inside <img>.
Set STATIC=1 for a frozen frame (local Quick Look previews).
"""

import math
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "info-card.svg")
STATIC = os.environ.get("STATIC") == "1"

# ---- content ---------------------------------------------------------------
USER = "ugur"
HOST = "github"
TITLEBAR = "ugur@github: ~$ ./wordmark.sh --3d"
COMMAND = "./wordmark.sh --3d"
CAPTION = "Ughur Hasan — Founder @ Applynix · full-stack dev"

# ---- theme -----------------------------------------------------------------
BG = "#0d1117"
BAR = "#161b22"
BORDER = "#30363d"
FACE = "#c9d1d9"     # front face of the letters
SIDE = "#6e7681"     # extruded side wall, one step dimmer
DIM = "#7d8590"      # titlebar / caption
PROMPT = "#58a6ff"   # blue prompt
VAL = "#e6edf3"
CURSOR = "#39d353"   # green wipe cursor
FONT = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', monospace")

WIDTH = 490
BAR_H = 30
PAD_X = 22

# ---- ascii grid ------------------------------------------------------------
FONT_PX = 11
CHAR_PX = 6.6        # monospace advance at FONT_PX (0.6em)
LINE_PX = 12         # line pitch
EM_ROWS = 10         # rows per em (cap height)
PX_PER_EM = EM_ROWS * LINE_PX

STROKE = 0.19        # stroke width in em
SIDE_BEARING = 0.30  # em of air between glyph ink boxes
DEPTH = 1            # extrusion depth in rows, up-and-left
SS = 4               # supersamples per cell axis

# coverage -> face glyph. Dense in the middle, feathering at the edges.
FACE_RAMP = [(0.86, "S"), (0.62, "C"), (0.42, "s"), (0.27, "+")]
SIDE_CHARS = ["+", "`"]   # nearest extrusion step first

WIPE_DUR = 0.5
ROW_STAGGER = 0.085


def arc(cx, cy, rx, ry, a0, a1, n=28):
    """Flatten an elliptical arc (degrees, CCW) into a polyline."""
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


# Each glyph: (list of polylines in em coords with y up / baseline 0, advance).
GLYPHS = {
    "U": ([[(0, 1.0), (0, 0.22)],
           arc(0.39, 0.22, 0.39, 0.22, 180, 360),
           [(0.78, 0.22), (0.78, 1.0)]], 0.78),
    "g": ([arc(0.28, 0.36, 0.28, 0.36, 0, 360),
           [(0.56, 0.72), (0.56, -0.10)],
           arc(0.28, -0.10, 0.28, 0.20, 0, -145)], 0.56),
    "u": ([[(0, 0.72), (0, 0.18)],
           arc(0.30, 0.18, 0.30, 0.18, 180, 360),
           [(0.60, 0.72), (0.60, 0.0)]], 0.60),
    "r": ([[(0, 0.72), (0, 0)],
           arc(0.34, 0.42, 0.34, 0.30, 180, 90)], 0.34),
}


def seg_dist2(px, py, ax, ay, bx, by):
    """Squared distance from a point to a segment."""
    dx, dy = bx - ax, by - ay
    d2 = dx * dx + dy * dy
    t = 0.0 if d2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / d2))
    ex, ey = ax + t * dx - px, ay + t * dy - py
    return ex * ex + ey * ey


def layout(word):
    """Place the word's polylines end to end; return segments and the extents."""
    segs, pen = [], 0.0
    for ch in word:
        polys, adv = GLYPHS[ch]
        for poly in polys:
            for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
                segs.append((x0 + pen, y0, x1 + pen, y1))
        pen += adv + SIDE_BEARING
    width = pen - SIDE_BEARING
    ys = [y for s in segs for y in (s[1], s[3])]
    return segs, width, max(ys), min(ys)


def rasterize(word):
    """Sample the stroked word onto a char grid -> (face, side) glyph rows."""
    segs, w_em, top_em, bot_em = layout(word)
    half = STROKE / 2
    pad = half + 0.04

    cell_w = CHAR_PX / PX_PER_EM       # cell size in em
    cell_h = LINE_PX / PX_PER_EM
    cols = int(math.ceil((w_em + 2 * pad) / cell_w)) + 2 * DEPTH
    rows = int(math.ceil((top_em - bot_em + 2 * pad) / cell_h)) + DEPTH
    x0 = -pad + 2 * DEPTH * cell_w         # room for the extrusion up-left
    y0 = top_em + pad

    half2 = half * half
    cov = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            hits = 0
            for sy in range(SS):
                py = y0 - (r + (sy + 0.5) / SS) * cell_h
                for sx in range(SS):
                    px = x0 + (c + (sx + 0.5) / SS) * cell_w
                    for s in segs:
                        if seg_dist2(px, py, *s) <= half2:
                            hits += 1
                            break
            cov[r][c] = hits / (SS * SS)

    face = [[" "] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            for thr, ch in FACE_RAMP:
                if cov[r][c] >= thr:
                    face[r][c] = ch
                    break

    # side wall: the mask swept up-and-left at ~45deg (cells are half as wide
    # as they are tall, so two columns per row), wherever the face isn't
    side = [[" "] * cols for _ in range(rows)]
    for t in range(1, 2 * DEPTH + 1):
        dc, dr = t, int(t / 2 + 0.5)
        ch = SIDE_CHARS[0] if t <= DEPTH else SIDE_CHARS[1]
        for r in range(rows - dr):
            for c in range(cols - dc):
                if cov[r + dr][c + dc] >= 0.45 and face[r][c] == " " \
                        and side[r][c] == " ":
                    side[r][c] = ch
    return face, side


def trim(face, side):
    """Drop blank rows, then the blank margin columns, so the art centers."""
    rows = [(f, s) for f, s in zip(face, side)
            if any(ch != " " for ch in f + s)]
    inked = [[i for i in range(len(f)) if f[i] != " " or s[i] != " "]
             for f, s in rows]
    left = min(ix[0] for ix in inked if ix)
    out = []
    for (f, s), ix in zip(rows, inked):
        n = ix[-1] + 1 if ix else left
        out.append((f[left:n], s[left:n]))
    return out


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def runs(face, side):
    """Merge the two layers into colored runs of text for one row."""
    out = []
    for f, s in zip(face, side):
        ch, fill = (f, FACE) if f != " " else ((s, SIDE) if s != " " else (" ", None))
        if out and out[-1][0] == fill:
            out[-1][1].append(ch)
        else:
            out.append([fill, [ch]])
    return [(fill, "".join(chars)) for fill, chars in out]


def build(grid):
    art_w = max(len(f) for f, _ in grid) * CHAR_PX
    art_x = round((WIDTH - art_w) / 2)
    art_y = BAR_H + 44
    art_h = len(grid) * LINE_PX
    cap_y = art_y + art_h + 26
    sw_y = cap_y + 18
    height = sw_y + 13 + 20

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
         f'height="{height}" viewBox="0 0 {WIDTH} {height}" font-family="{FONT}" '
         f'role="img" aria-label="ASCII wordmark: Ugur">']

    def fade(delay):
        """(opening attr, child <animate>) for a SMIL fade-in that freezes on."""
        if STATIC:
            return "", ""
        return ' opacity="0"', (f'<animate attributeName="opacity" from="0" '
                                f'to="1" dur="0.45s" begin="{delay}s" '
                                f'fill="freeze"/>')

    # window chrome
    p.append(f'<rect x="1" y="1" width="{WIDTH-2}" height="{height-2}" rx="10" '
             f'fill="{BG}" stroke="{BORDER}"/>')
    p.append(f'<path d="M1 11 a10 10 0 0 1 10 -10 h{WIDTH-22} a10 10 0 0 1 10 10 '
             f'v{BAR_H-10} h-{WIDTH-2} z" fill="{BAR}"/>')
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        p.append(f'<circle cx="{20+i*20}" cy="{BAR_H/2}" r="6" fill="{c}"/>')
    p.append(f'<text x="{WIDTH/2}" y="{BAR_H/2+4}" text-anchor="middle" '
             f'font-size="11" fill="{DIM}">{esc(TITLEBAR)}</text>')

    # prompt line
    op, anim = fade(0.05)
    p.append(f'<text x="{PAD_X}" y="{BAR_H+22}" font-size="12.5" '
             f'fill="{PROMPT}"{op}>'
             f'{esc(USER)}@{esc(HOST)}<tspan fill="{DIM}"> ~ $ </tspan>'
             f'<tspan fill="{VAL}">{esc(COMMAND)}</tspan>{anim}</text>')

    # one animated clip rect per art row (SMIL wipe, freezes at full width)
    if not STATIC:
        p.append("<defs>")
        for i, (f, _) in enumerate(grid):
            full = len(f) * CHAR_PX + 2
            p.append(
                f'<clipPath id="w{i}"><rect x="{art_x}" y="{art_y + i*LINE_PX}" '
                f'width="0" height="{LINE_PX+2}">'
                f'<animate attributeName="width" from="0" to="{full:.1f}" '
                f'dur="{WIPE_DUR}s" begin="{round(i*ROW_STAGGER,3)}s" '
                f'fill="freeze" calcMode="linear"/></rect></clipPath>')
        p.append("</defs>")

    # art rows: one <text> per row, tspan runs for face vs. side wall
    for i, (f, s) in enumerate(grid):
        y = art_y + i * LINE_PX + FONT_PX - 2
        clip = "" if STATIC else f' clip-path="url(#w{i})"'
        spans = "".join(
            esc(txt) if fill is None
            else f'<tspan fill="{fill}">{esc(txt)}</tspan>'
            for fill, txt in runs(f, s))
        p.append(f'<text x="{art_x}" y="{y}" font-size="{FONT_PX}px" '
                 f'fill="{FACE}" xml:space="preserve"{clip} '
                 f'style="white-space:pre">{spans}</text>')

    # green cursor riding each wipe edge, then vanishing
    if not STATIC:
        for i, (f, _) in enumerate(grid):
            begin = round(i * ROW_STAGGER, 3)
            full = len(f) * CHAR_PX
            p.append(
                f'<rect x="{art_x}" y="{art_y + i*LINE_PX}" width="{CHAR_PX:.1f}" '
                f'height="{FONT_PX}" fill="{CURSOR}" opacity="0.85">'
                f'<animate attributeName="x" from="{art_x}" to="{art_x+full:.1f}" '
                f'dur="{WIPE_DUR}s" begin="{begin}s" fill="freeze"/>'
                f'<animate attributeName="opacity" from="0.85" to="0" dur="0.12s" '
                f'begin="{round(begin+WIPE_DUR,3)}s" fill="freeze"/></rect>')

    tail = round(len(grid) * ROW_STAGGER + WIPE_DUR, 2)

    # caption + neofetch swatches, once the wordmark has finished printing
    op, anim = fade(tail)
    p.append(f'<text x="{WIDTH/2}" y="{cap_y}" text-anchor="middle" '
             f'font-size="11.5" fill="{DIM}"{op}>'
             f'{esc(CAPTION)}{anim}</text>')

    swatches = ["#161b22", "#f85149", "#39d353", "#d29922",
                "#58a6ff", "#bc8cff", "#39c5cf", "#e6edf3"]
    sw_x = (WIDTH - len(swatches) * 16 + 3) / 2
    op, anim = fade(round(tail + 0.15, 2))
    p.append(f'<g{op}>{anim}')
    for i, c in enumerate(swatches):
        p.append(f'<rect x="{sw_x + i*16:.1f}" y="{sw_y}" width="13" height="13" '
                 f'rx="2" fill="{c}"/>')
    p.append("</g>")

    p.append("</svg>")
    return "\n".join(p)


def main():
    face, side = rasterize("Ugur")
    grid = trim(face, side)
    svg = build(grid)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"Wrote {OUT}: {max(len(r[0]) for r in grid)}x{len(grid)} grid "
          f"({len(svg)} bytes){' [STATIC]' if STATIC else ''}")


if __name__ == "__main__":
    main()
