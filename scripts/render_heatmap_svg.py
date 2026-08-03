#!/usr/bin/env python3
"""
render_heatmap_svg.py
Turn data/contributions.json into an animated SVG: the classic 53x7 calendar of
rounded boxes that reveal diagonally (top-left -> bottom-right), play once, then
freeze. CSS keyframe animations run because GitHub renders the file via <img>.
"""

import json
import os
from datetime import datetime

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data", "contributions.json")
OUT = os.path.join(HERE, "..", "contrib-heatmap.svg")

# GitHub-style green ramp, level 0..4
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

CELL = 12          # box pitch (size + gap)
BOX = 10           # box side
RADIUS = 2
PAD_L = 30         # room for weekday labels
PAD_T = 22         # room for month labels
PAD_R = 16
PAD_B = 44         # room for legend + footer

FG = "#7d8590"     # muted label grey
FG_BRIGHT = "#e6edf3"
FONT = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', monospace")

WEEKDAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}  # weekday index -> label (0=Sun)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build():
    with open(DATA) as f:
        data = json.load(f)

    weeks = data["weeks"]
    days = data["days"]

    grid_w = weeks * CELL
    width = PAD_L + grid_w + PAD_R
    height = PAD_T + 7 * CELL + PAD_B

    # Diagonal reveal: delay grows with (week + weekday). Normalize so the whole
    # thing finishes in ~2.6s regardless of width.
    max_diag = weeks + 6
    total_reveal = 2.6

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="{FONT}" role="img" '
        f'aria-label="{esc(data["username"])} GitHub contribution heatmap">'
    )

    # ---- styles + keyframes -------------------------------------------------
    parts.append(f"""<style>
    .box {{ opacity: 0; transform: translateY(-3px) scale(.6);
            transform-box: fill-box; transform-origin: center;
            animation: pop .45s ease-out forwards; }}
    @keyframes pop {{ to {{ opacity: 1; transform: translateY(0) scale(1); }} }}
    .lbl {{ fill: {FG}; font-size: 9px; opacity: 0;
            animation: fade .6s ease forwards; animation-delay: 2.0s; }}
    .foot {{ fill: {FG_BRIGHT}; font-size: 12px; font-weight: 600; opacity: 0;
             animation: fade .7s ease forwards; animation-delay: 2.7s; }}
    .legend {{ fill: {FG}; font-size: 9px; opacity: 0;
               animation: fade .6s ease forwards; animation-delay: 2.7s; }}
    @keyframes fade {{ to {{ opacity: 1; }} }}
    </style>""")

    # ---- month labels -------------------------------------------------------
    for m in data["months"]:
        x = PAD_L + m["week"] * CELL
        if x < PAD_L + grid_w - 12:  # skip a clipped trailing label
            parts.append(f'<text class="lbl" x="{x}" y="{PAD_T-8}">{esc(m["label"])}</text>')

    # ---- weekday labels -----------------------------------------------------
    for wd, label in WEEKDAY_LABELS.items():
        y = PAD_T + wd * CELL + BOX - 1
        parts.append(f'<text class="lbl" x="0" y="{y}">{label}</text>')

    # ---- day boxes ----------------------------------------------------------
    for d in days:
        x = PAD_L + d["week"] * CELL
        y = PAD_T + d["weekday"] * CELL
        color = PALETTE[min(d["level"], 4)]
        delay = round((d["week"] + d["weekday"]) / max_diag * total_reveal, 3)
        title = (f'{d["count"]} contribution' + ("s" if d["count"] != 1 else "")
                 + f' on {d["date"]}')
        parts.append(
            f'<rect class="box" x="{x}" y="{y}" width="{BOX}" height="{BOX}" '
            f'rx="{RADIUS}" fill="{color}" style="animation-delay:{delay}s">'
            f'<title>{esc(title)}</title></rect>'
        )

    # ---- legend (Less [] [] [] [] [] More) ----------------------------------
    legend_y = PAD_T + 7 * CELL + 16
    lx = width - PAD_R - (len(PALETTE) * CELL) - 74
    parts.append(f'<text class="legend" x="{lx}" y="{legend_y+9}">Less</text>')
    for i, c in enumerate(PALETTE):
        bx = lx + 30 + i * CELL
        parts.append(f'<rect class="legend" x="{bx}" y="{legend_y}" width="{BOX}" '
                     f'height="{BOX}" rx="{RADIUS}" fill="{c}"/>')
    parts.append(f'<text class="legend" x="{lx + 30 + len(PALETTE)*CELL + 4}" '
                 f'y="{legend_y+9}">More</text>')

    # ---- footer -------------------------------------------------------------
    foot = f'{data["total"]:,} contributions in the last year'
    parts.append(f'<text class="foot" x="{PAD_L}" y="{legend_y+9}">{esc(foot)}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    svg = build()
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"Wrote {OUT} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
