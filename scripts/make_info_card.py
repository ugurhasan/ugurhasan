#!/usr/bin/env python3
"""
make_info_card.py
Hand-author a neofetch-style info card SVG: a terminal window whose body is
key/value rows that fade + slide in line by line. Set STATIC=1 for a frozen
frame (local Quick Look previews).

Superseded in the README by make_wordmark_card.py (the ASCII "Ugur" wordmark),
which owns info-card.svg — this one writes info-card-rows.svg so the two can
coexist. Swap the <img> src in README.md to bring the rows back.

Edit the ROWS / HEADER below to change the content — this is the one file that
tells the story your numbers can't.
"""

import os

OUT = os.path.join(os.path.dirname(__file__), "..", "info-card-rows.svg")
STATIC = os.environ.get("STATIC") == "1"

# ---- content ---------------------------------------------------------------
USER = "ugur"
HOST = "github"
TITLEBAR = "ugur@github: ~$ ./whoami.sh"

# (key, value) — keep values short so nothing wraps.
ROWS = [
    ("Name",     "Ughur Hasan"),
    ("Now",      "Founder @ Applynix (AI agency)"),
    ("Also",     "Building Rialtoo (startup)"),
    ("Focus",    "Full-stack — React / Next.js"),
    ("Stack",    "TS · Node · Spring Boot · Flask"),
    ("Data",     "Postgres · MongoDB · Supabase"),
    ("Infra",    "Docker · Vercel · Cloudflare · Railway"),
    ("Studying", "BSc Computer Science @ IU"),
    ("Loc",      "Germany"),
    ("Motto",    "Tech guy building brands."),
]

# ---- theme -----------------------------------------------------------------
BG = "#0d1117"
BAR = "#161b22"
BORDER = "#30363d"
KEY = "#39d353"      # green accent for keys (matches heatmap)
VAL = "#e6edf3"      # bright value text
DIM = "#7d8590"      # titlebar text
PROMPT = "#58a6ff"   # blue prompt
FONT = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', monospace")

WIDTH = 490
BAR_H = 30
ROW_H = 26
PAD_X = 22
BODY_TOP = BAR_H + 28
KEY_W = 88            # column width for keys
HEIGHT = BODY_TOP + len(ROWS) * ROW_H + 44

# neofetch color squares
SWATCHES = ["#161b22", "#f85149", "#39d353", "#d29922",
            "#58a6ff", "#bc8cff", "#39c5cf", "#e6edf3"]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build():
    p = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT}" role="img" '
        f'aria-label="Info card for {esc(USER)}@{esc(HOST)}">'
    )

    anim = "" if STATIC else """
    .line { opacity: 0; transform: translateX(-6px);
            animation: slidein .5s ease forwards; }
    @keyframes slidein { to { opacity: 1; transform: translateX(0); } }
    .prompt-line { opacity: 0; animation: fade .4s ease forwards; }
    @keyframes fade { to { opacity: 1; } }
    """
    static_css = ".line,.prompt-line{opacity:1;}" if STATIC else ""
    p.append(f"<style>{anim}{static_css}</style>")

    # window
    p.append(f'<rect x="1" y="1" width="{WIDTH-2}" height="{HEIGHT-2}" rx="10" '
             f'fill="{BG}" stroke="{BORDER}"/>')
    p.append(f'<path d="M1 11 a10 10 0 0 1 10 -10 h{WIDTH-22} a10 10 0 0 1 10 10 '
             f'v{BAR_H-10} h-{WIDTH-2} z" fill="{BAR}"/>')
    # traffic lights
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        p.append(f'<circle cx="{20+i*20}" cy="{BAR_H/2}" r="6" fill="{c}"/>')
    p.append(f'<text x="{WIDTH/2}" y="{BAR_H/2+4}" text-anchor="middle" '
             f'font-size="11" fill="{DIM}">{esc(TITLEBAR)}</text>')

    # a faux prompt line at the top of the body
    p.append(f'<text class="prompt-line" x="{PAD_X}" y="{BAR_H+22}" font-size="12.5" '
             f'fill="{PROMPT}" style="animation-delay:.05s">'
             f'{esc(USER)}@{esc(HOST)}<tspan fill="{DIM}"> ~ $ </tspan>'
             f'<tspan fill="{VAL}">cat about.txt</tspan></text>')

    # rows
    for i, (k, v) in enumerate(ROWS):
        y = BODY_TOP + i * ROW_H + 14
        delay = 0.25 + i * 0.14
        style = "" if STATIC else f' style="animation-delay:{delay:.2f}s"'
        p.append(f'<g class="line"{style}>')
        p.append(f'<text x="{PAD_X}" y="{y}" font-size="13" fill="{KEY}" '
                 f'font-weight="600">{esc(k)}</text>')
        p.append(f'<text x="{PAD_X+KEY_W-14}" y="{y}" font-size="13" fill="{DIM}">~</text>')
        p.append(f'<text x="{PAD_X+KEY_W}" y="{y}" font-size="13" fill="{VAL}">'
                 f'{esc(v)}</text>')
        p.append('</g>')

    # neofetch color swatches at the bottom
    sw_y = HEIGHT - 28
    sw = len(SWATCHES) * 16
    delay = 0.25 + len(ROWS) * 0.14
    style = "" if STATIC else f' style="animation-delay:{delay:.2f}s"'
    p.append(f'<g class="line"{style}>')
    for i, c in enumerate(SWATCHES):
        p.append(f'<rect x="{PAD_X + i*16}" y="{sw_y}" width="13" height="13" '
                 f'rx="2" fill="{c}"/>')
    p.append('</g>')

    p.append("</svg>")
    return "\n".join(p)


def main():
    svg = build()
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"Wrote {OUT} ({len(svg)} bytes){' [STATIC]' if STATIC else ''}")


if __name__ == "__main__":
    main()
