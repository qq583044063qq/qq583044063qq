#!/usr/bin/env python3
"""Generate standalone SVG cards from GitHub's API (no third-party image services)."""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

USER = os.environ.get("PROFILE_USER", "qq583044063qq")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT = Path("assets/stats")
NOW = datetime.now(timezone.utc)
STAMP = NOW.strftime("%Y-%m-%d %H:%M UTC")

BG = "#0d1117"
PANEL = "#161b22"
BORDER = "#30363d"
WHITE = "#e6edf3"
MUTED = "#8b949e"
BLUE = "#79c0ff"
PINK = "#f778ba"


def request_json(url, payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-profile-stats-svg",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=json.dumps(payload).encode("utf-8") if payload is not None else None,
                  headers=headers, method="POST" if payload is not None else "GET")
    for attempt in range(3):
        try:
            with urlopen(req, timeout=25) as resp:
                return json.load(resp)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f"GitHub API HTTP {exc.code}: {url}") from exc
        except (URLError, TimeoutError) as exc:
            if attempt == 2:
                raise RuntimeError(f"GitHub API request failed: {url}") from exc
        time.sleep(2 ** attempt)
    raise RuntimeError("Unreachable API retry state")


def rest(path):
    return request_json("https://api.github.com" + path)


def fetch_calendar():
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
    try:
        result = request_json("https://api.github.com/graphql", {"query": query, "variables": {"login": USER}})
        if result.get("errors"):
            raise ValueError(str(result["errors"]))
        cal = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        counts = {d["date"]: int(d["contributionCount"])
                  for week in cal["weeks"] for d in week["contributionDays"]}
        return counts, int(cal["totalContributions"])
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        print(f"Warning: contributions calendar unavailable: {exc}")
        return None, None


def get_repositories():
    repositories = []
    for page in range(1, 6):
        batch = rest(f"/users/{quote(USER)}/repos?type=owner&per_page=100&page={page}")
        repositories.extend(repo for repo in batch if not repo.get("fork") and not repo.get("private"))
        if len(batch) < 100:
            break
    return repositories


def language_totals(repositories):
    totals = Counter()
    for repo in repositories:
        if repo.get("archived"):
            continue
        try:
            langs = rest(f"/repos/{quote(repo['full_name'], safe='/')}/languages")
            totals.update({lang: int(size) for lang, size in langs.items()})
        except (RuntimeError, KeyError, ValueError) as exc:
            print(f"Warning: language stats unavailable for {repo.get('full_name')}: {exc}")
    return totals


def base_svg(width, height, title, subtitle):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title, quote=True)}">',
            '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#151b29"/><stop offset="100%" stop-color="#0d1117"/></linearGradient></defs>',
            f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="15" fill="url(#bg)" stroke="{BORDER}"/>',
            f'<rect x="24" y="22" width="5" height="25" rx="2.5" fill="{PINK}"/>',
            f'<text x="39" y="42" font-family="Verdana,Arial,sans-serif" font-size="20" font-weight="700" fill="{WHITE}">{escape(title)}</text>',
            f'<text x="24" y="63" font-family="Verdana,Arial,sans-serif" font-size="11" fill="{MUTED}">{escape(subtitle)}</text>']


def label(x, y, value, size=12, color=MUTED, weight="400", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="Verdana,Arial,sans-serif" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{color}">{escape(str(value))}</text>')


def finish(parts, path):
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Generated {path}")


def stat_card(profile, repos, contributions):
    parts = base_svg(560, 258, "GitHub Overview", f"@{USER}  |  Public account stats")
    stats = [
        ("PUBLIC REPOS", profile.get("public_repos", 0)),
        ("STARS EARNED", sum(int(r.get("stargazers_count", 0)) for r in repos)),
        ("FOLLOWERS", profile.get("followers", 0)),
        ("FORKS", sum(int(r.get("forks_count", 0)) for r in repos)),
        ("CONTRIBUTIONS / YEAR", contributions if contributions is not None else "N/A"),
        ("PUBLIC GISTS", profile.get("public_gists", 0)),
    ]
    for idx, (name, value) in enumerate(stats):
        col, row = idx % 3, idx // 3
        x, y = 24 + 174 * col, 82 + 75 * row
        parts.append(f'<rect x="{x}" y="{y}" width="164" height="65" rx="9" fill="{PANEL}" stroke="#273044"/>')
        parts.append(label(x+12, y+20, name, size=10))
        parts.append(label(x+12, y+49, value, size=23, color=BLUE, weight="700"))
    parts.append(label(24, 242, f"Updated {STAMP}  |  Contributions: rolling 12 months", size=10))
    finish(parts, OUTPUT / "github-stats.svg")


LANG_COLORS = {
    "Python": "#3572a5", "C#": "#9b4f96", "C++": "#f34b7d", "C": "#555555",
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "HTML": "#e34c26", "CSS": "#563d7c",
    "Java": "#b07219", "Rust": "#dea584", "Go": "#00add8", "Shell": "#89e051",
    "PowerShell": "#012456", "Kotlin": "#a97bff", "Lua": "#000080", "Jupyter Notebook": "#da5b0b",
}


def lang_card(languages):
    parts = base_svg(560, 288, "Top Languages", "GitHub language bytes  |  Public non-fork repositories")
    total = sum(languages.values())
    ranked = languages.most_common(6)
    if not total:
        parts.append(label(24, 150, "No language metrics available yet", size=15, color=WHITE))
    else:
        for index, (lang, amount) in enumerate(ranked):
            y = 89 + index * 29
            percent = amount * 100 / total
            color = LANG_COLORS.get(lang, ["#79c0ff", "#f778ba", "#d2a8ff", "#56d364"][index % 4])
            parts.append(f'<rect x="24" y="{y-11}" width="9" height="9" rx="2" fill="{color}"/>')
            parts.append(label(40, y-2, lang, size=12, color=WHITE))
            parts.append(label(535, y-2, f"{percent:.1f}%", size=12, color=WHITE, anchor="end"))
            parts.append(f'<rect x="24" y="{y+3}" width="511" height="5" rx="2.5" fill="#30363d"/>')
            parts.append(f'<rect x="24" y="{y+3}" width="{max(2, 511 * percent / 100):.1f}" height="5" rx="2.5" fill="{color}"/>')
    parts.append(label(24, 273, f"Updated {STAMP}  |  Private repositories not included", size=10))
    finish(parts, OUTPUT / "top-langs.svg")


def activity_card(calendar):
    parts = base_svg(900, 264, "Contribution Activity", "Daily contributions over the last 31 days  |  GitHub GraphQL")
    today = NOW.date()
    days = [today - timedelta(days=30-i) for i in range(31)]
    if calendar is None:
        parts.append(label(36, 144, "Contribution history temporarily unavailable", size=17, color=WHITE))
    else:
        nums = [calendar.get(day.isoformat(), 0) for day in days]
        maximum = max(max(nums), 1)
        total = sum(nums)
        parts.append(label(864, 42, f"{total} contributions", size=13, color=BLUE, weight="700", anchor="end"))
        baseline = 225
        for y in (95, 137, 179, 225):
            parts.append(f'<line x1="40" y1="{y}" x2="868" y2="{y}" stroke="#293241" stroke-dasharray="3 5"/>')
        for i, (day, count) in enumerate(zip(days, nums)):
            x = 45 + 26 * i
            h = 4 if count == 0 else 8 + (count / maximum) * 110
            parts.append(f'<rect x="{x}" y="{baseline-h:.1f}" width="16" height="{h:.1f}" rx="3" fill="{PINK if count else BORDER}"/>')
            if i % 5 == 0 or i == 30:
                parts.append(label(x+8, 247, day.strftime("%b %d"), size=10, anchor="middle"))
    finish(parts, OUTPUT / "activity-graph.svg")


def main():
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN is required. Run with GitHub Actions secrets.GITHUB_TOKEN.")
    profile = rest(f"/users/{quote(USER)}")
    repos = get_repositories()
    languages = language_totals(repos)
    calendar, contributions = fetch_calendar()
    stat_card(profile, repos, contributions)
    lang_card(languages)
    activity_card(calendar)


if __name__ == "__main__":
    main()
