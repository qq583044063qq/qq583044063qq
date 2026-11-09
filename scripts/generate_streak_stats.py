#!/usr/bin/env python3
"""Generate a self-hosted GitHub contribution-streak SVG, then refresh README URL.

Uses the same GitHub GraphQL contribution calendar as the existing profile stats
script. No external SVG service, third-party dependencies, or extra secrets.
"""

from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER = os.environ.get("PROFILE_USER", "qq583044063qq")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
NOW = datetime.now(timezone.utc)
OUT = Path("assets/stats/contribution-streak.svg")
README = Path("README.md")

WHITE = "#e6edf3"
MUTED = "#8b949e"
BORDER = "#30363d"
BLUE = "#79c0ff"
PINK = "#f778ba"
ORANGE = "#ffa657"


def read_calendar():
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing")
    query = """query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }"""
    req = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-streak-svg",
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urlopen(req, timeout=30) as res:
                body = json.load(res)
            if body.get("errors"):
                raise RuntimeError("GitHub GraphQL returned errors; check token permissions")
            cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            counts = {date.fromisoformat(d["date"]): int(d["contributionCount"])
                      for w in cal["weeks"] for d in w["contributionDays"]}
            if not counts:
                raise RuntimeError("Contribution calendar is empty")
            return counts, int(cal["totalContributions"])
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == 2 or (isinstance(exc, HTTPError) and exc.code not in (429, 500, 502, 503, 504)):
                raise RuntimeError(f"GitHub GraphQL unavailable (HTTP/network error: {getattr(exc, 'code', '?')})") from None
            time.sleep(2 ** attempt)
    raise RuntimeError("No GitHub GraphQL response")


def streak_metrics(counts, total, today=None):
    """Current streak permits a zero-contribution today if yesterday was active.

    Longest is necessarily scoped to GitHub's rolling 12-month calendar.
    """
    today = today or NOW.date()
    anchor = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
    current = 0
    day = anchor
    while counts.get(day, 0) > 0:
        current += 1
        day -= timedelta(days=1)

    longest = run = 0
    for day in sorted(d for d in counts if d <= today):
        if counts[day] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return current, longest, total


def text(x, y, value, size=14, color=MUTED, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="Arial,Verdana,sans-serif" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'fill="{color}">{escape(str(value))}</text>')


def render_svg(counts, metrics):
    current, longest, total = metrics
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="264" viewBox="0 0 900 264" role="img" aria-label="GitHub Contribution Streak">',
        '<title>GitHub Contribution Streak</title>',
        '<desc>Contribution counts and consecutive-day streaks from the GitHub contribution calendar over a rolling 12-month period.</desc>',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#151b29"/><stop offset="100%" stop-color="#0d1117"/></linearGradient></defs>',
        f'<rect x="0.5" y="0.5" width="899" height="263" rx="15" fill="url(#bg)" stroke="{BORDER}"/>',
        f'<rect x="24" y="22" width="5" height="25" rx="2.5" fill="{PINK}"/>',
        text(39, 42, "Contribution Streak", 20, WHITE, 700),
        text(24, 63, "GitHub contribution calendar  |  rolling 12 months", 11),
    ]
    for x, title, num, color in [
        (24, "CURRENT STREAK", current, ORANGE),
        (310, "LONGEST STREAK (12 MO)", longest, PINK),
        (596, "TOTAL CONTRIBUTIONS (12 MO)", total, BLUE),
    ]:
        parts.append(f'<rect x="{x}" y="82" width="280" height="107" rx="10" fill="#161b22" stroke="#283344"/>')
        parts.append(text(x+18, 107, title, 12))
        parts.append(text(x+18, 162, f"{num:,}", 42, color, 700))
        parts.append(text(x+146, 162, "days" if x != 596 else "events", 12, MUTED))

    # Last-31-days activity strip, for continuity with the existing cards.
    today = NOW.date()
    days = [today - timedelta(days=30-i) for i in range(31)]
    max_count = max(1, *(counts.get(d, 0) for d in days))
    parts.append(text(24, 215, "LAST 31 DAYS", 10))
    for i, day in enumerate(days):
        n = counts.get(day, 0)
        # Right-aligned row of 31 heatmap cells.
        x = 217 + 21 * i
        strength = n / max_count
        color = ORANGE if n and strength > .55 else PINK if n else BORDER
        parts.append(f'<rect x="{x}" y="204" width="14" height="14" rx="3" fill="{color}"/>')
    parts.append(text(24, 245, f"Updated {NOW.strftime('%Y-%m-%d %H:%M UTC')}  |  Today may count after GitHub refreshes", 10))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def refresh_readme():
    source = README.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if "![GitHub Streak](" in line]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one README GitHub Streak image, found {len(matches)}")
    version = NOW.strftime("%Y%m%d%H%M%S")
    lines[matches[0]] = f"![GitHub Streak](./assets/stats/contribution-streak.svg?v={version})\n"
    README.write_text("".join(lines), encoding="utf-8")


def main():
    counts, total = read_calendar()
    metrics = streak_metrics(counts, total)
    svg = render_svg(counts, metrics)
    # Ensure README is compatible *before* writing generated assets.
    source = README.read_text(encoding="utf-8")
    if source.count("![GitHub Streak](") != 1:
        raise RuntimeError("README GitHub Streak image not found or ambiguous")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    refresh_readme()
    print(f"Created {OUT}: current={metrics[0]}, longest(12mo)={metrics[1]}, total(12mo)={metrics[2]}")


if __name__ == "__main__":
    main()
