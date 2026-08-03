#!/usr/bin/env python3
"""
fetch_contributions.py
Scrape the public GitHub contribution calendar (no token, no GraphQL) and write
data/contributions.json with the raw day grid plus derived stats.

GitHub serves the same calendar fragment the profile page uses at:
    https://github.com/users/<username>/contributions
Each day is a <td class="ContributionCalendar-day"> carrying data-date and
data-level; the exact count lives in a matching <tool-tip for="<cell id>">.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GH_USERNAME", "ugurhasan")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")

CELL_ID_RE = re.compile(r"contribution-day-component-(\d+)-(\d+)")
COUNT_RE = re.compile(r"^([\d,]+)\s+contribution")


def fetch_html(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (profile-art bot)",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def parse(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # Map each cell id -> integer count via its tooltip ("No contributions" -> 0).
    counts_by_id = {}
    for tip in soup.select("tool-tip"):
        target = tip.get("for")
        if not target:
            continue
        text = tip.get_text(strip=True)
        m = COUNT_RE.match(text)
        counts_by_id[target] = int(m.group(1).replace(",", "")) if m else 0

    days = []
    for cell in soup.select("td.ContributionCalendar-day"):
        d = cell.get("data-date")
        if not d:
            continue
        cell_id = cell.get("id", "")
        m = CELL_ID_RE.search(cell_id)
        weekday = int(m.group(1)) if m else 0   # 0 = Sunday ... 6 = Saturday
        week = int(m.group(2)) if m else 0      # column index, 0 = oldest week
        days.append({
            "date": d,
            "count": counts_by_id.get(cell_id, 0),
            "level": int(cell.get("data-level", 0)),
            "weekday": weekday,
            "week": week,
        })

    days.sort(key=lambda x: x["date"])

    # Total: prefer GitHub's own headline number, fall back to summing.
    total = sum(x["count"] for x in days)
    h2 = soup.find("h2", id="js-contribution-activity-description")
    if h2:
        m = re.search(r"([\d,]+)\s+contribution", h2.get_text(" ", strip=True))
        if m:
            total = int(m.group(1).replace(",", ""))

    return days, total


def month_labels(days):
    """First week-column index at which each month starts, for the x-axis."""
    labels = []
    seen = set()
    for d in days:
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        key = (dt.year, dt.month)
        if key not in seen:
            seen.add(key)
            labels.append({"week": d["week"], "label": dt.strftime("%b")})
    return labels


def streaks_and_best(days):
    current = longest = run = 0
    for d in days:
        if d["count"] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    # current streak counts back from the most recent day
    for d in reversed(days):
        if d["count"] > 0:
            current += 1
        else:
            break
    best = max(days, key=lambda x: x["count"]) if days else {"date": None, "count": 0}
    return current, longest, best


def monthly_totals(days):
    buckets = {}
    for d in days:
        key = d["date"][:7]  # YYYY-MM
        buckets[key] = buckets.get(key, 0) + d["count"]
    return buckets


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else USERNAME
    html = fetch_html(username)
    days, total = parse(html)
    if not days:
        print("ERROR: no day cells parsed — GitHub markup may have changed.", file=sys.stderr)
        sys.exit(1)

    current, longest, best = streaks_and_best(days)
    data = {
        "username": username,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "weeks": max(d["week"] for d in days) + 1,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "months": month_labels(days),
        "monthly_totals": monthly_totals(days),
        "days": days,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {OUT}: {total} contributions, {len(days)} days, "
          f"streak {current} (best {longest}).")


if __name__ == "__main__":
    main()
