#!/usr/bin/env python3
"""Generate WakaTime README SVG cards using the user's personal OAuth token.

Only aggregated language/editor/OS data is rendered; no project names or token data
are embedded in the output SVG or README.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TOKEN = (os.getenv('WAKATIME_TOKEN') or os.getenv('WAKATIME_OAUTH_TOKEN') or '').strip()
OUT = Path('assets/stats')
README = Path('README.md')
STAMP = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
DATE_TEXT = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
COLORS = ['#79c0ff', '#f778ba', '#d2a8ff', '#56d364', '#ffa657', '#7ee787']
PALE = '#e6edf3'
DIM = '#9da9bd'


def api(path):
    request = Request('https://wakatime.com/api/v1/users/current/' + path,
                      headers={'Authorization': 'Bearer ' + TOKEN,
                               'Accept': 'application/json',
                               'User-Agent': 'profile-wakatime-stats-svg'})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=45) as response:
                obj = json.load(response)
                if 'data' not in obj:
                    raise ValueError('Malformed WakaTime response (missing data)')
                return obj['data']
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise RuntimeError('WakaTime authentication rejected (HTTP 401/403). Your Actions secret must contain a personal OAuth token with read_stats scope.') from None
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f'WakaTime returned HTTP {exc.code} for {path}') from None
        except (URLError, TimeoutError) as exc:
            if attempt == 2:
                raise RuntimeError('Cannot reach WakaTime API (network/timeout)') from None
        time.sleep(attempt * 3 + 2)
    raise RuntimeError('WakaTime request retries exhausted')


def tag(x, y, value, size=15, color=PALE, weight=400, anchor='start'):
    return (f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial,sans-serif" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'fill="{color}">{escape(str(value))}</text>')


def base(width, height, title, sub):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{escape(title,quote=True)}">',
            '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#17263a"/><stop offset="1" stop-color="#0d1117"/></linearGradient><linearGradient id="line" x1="0" x2="1"><stop stop-color="#79c0ff"/><stop offset="1" stop-color="#f778ba"/></linearGradient></defs>',
            f'<rect width="{width-1}" height="{height-1}" x="0.5" y="0.5" rx="18" fill="url(#bg)" stroke="#394758"/>',
            f'<rect x="24" y="24" width="5" height="27" rx="2.5" fill="#f778ba"/>',
            tag(42, 45, title, 23, PALE, 700),
            tag(25, 69, sub, 12, DIM),
            f'<rect x="24" y="{height-23}" width="{width-48}" height="1" fill="#273548"/>',
            tag(26, height-9, 'WakaTime  |  ' + DATE_TEXT, 11, DIM)]


def end(parts, filename):
    parts.append('</svg>')
    OUT.mkdir(parents=True, exist_ok=True)
    file = OUT / filename
    file.write_text('\n'.join(parts) + '\n', encoding='utf-8')
    print('Generated ' + str(file))


def fmt_hours(seconds):
    hours = max(0, float(seconds or 0)) / 3600
    if hours >= 100:
        return f'{hours:,.0f} h'
    return f'{hours:,.1f} h'


def fmt_clock(seconds):
    mins = round(max(0, float(seconds or 0)) / 60)
    h, m = divmod(mins, 60)
    return f'{h}h {m:02d}m' if h else f'{m}m'


def summary_card(weekly, lifetime):
    parts = base(900, 246, 'WakaTime  /  Coding Dashboard', 'LAST 7 DAYS  ·  IDE activity measured by WakaTime')
    total = weekly.get('total_seconds', 0)
    daily = weekly.get('daily_average', 0)
    life = lifetime.get('total_seconds')
    if life is None:
        # all_time_since_today provides digital/decimal and may lack total_seconds on some accounts.
        life = lifetime.get('decimal', '—')
        if life != '—':
            try:
                life = float(life) * 3600
            except (TypeError, ValueError):
                life = None
    metrics = [('THIS WEEK', fmt_hours(total)), ('DAILY AVERAGE', fmt_clock(daily)),
               ('ALL-TIME CODING', fmt_hours(life) if life is not None else 'N/A')]
    for i, (name, value) in enumerate(metrics):
        x = 25 + i * 288
        parts.append(f'<rect x="{x}" y="88" width="274" height="120" rx="13" fill="#192536" stroke="#35445c"/>')
        parts.append(tag(x+17, 116, name, 12, DIM, 600))
        parts.append(tag(x+17, 166, value, 33, COLORS[i], 700))
        parts.append(f'<rect x="{x+17}" y="185" width="238" height="3" rx="1.5" fill="#2a374a"/>')
        parts.append(f'<rect x="{x+17}" y="185" width="{155 if i==0 else 116 if i==1 else 210}" height="3" rx="1.5" fill="{COLORS[i]}"/>')
    end(parts, 'wakatime-overview.svg')


def horizontal_section(parts, x, top, title, values, max_rows, width=410):
    parts.append(tag(x, top, title, 17, PALE, 700))
    if not values:
        parts.append(tag(x, top+32, 'No activity reported', 13, DIM))
        return
    for i, entry in enumerate(values[:max_rows]):
        y = top+35+i*47
        name = str(entry.get('name', 'Unknown'))
        if len(name) > 25:
            name = name[:24] + '…'
        try:
            pct = max(0.0, min(100.0, float(entry.get('percent') or 0)))
        except (TypeError, ValueError):
            pct = 0
        c = COLORS[i%len(COLORS)]
        parts.append(tag(x, y, name, 13))
        parts.append(tag(x+width, y, fmt_clock(entry.get('total_seconds', 0)) + f'  ·  {pct:.1f}%', 12, DIM, anchor='end'))
        parts.append(f'<rect x="{x}" y="{y+10}" width="{width}" height="7" rx="3.5" fill="#293649"/>')
        if pct:
            parts.append(f'<rect x="{x}" y="{y+10}" width="{max(2, width*pct/100):.1f}" height="7" rx="3.5" fill="{c}"/>')


def detail_card(stats):
    parts = base(900, 440, 'WakaTime  /  Weekly Breakdown', 'LANGUAGES, EDITORS & OPERATING SYSTEMS  ·  Last 7 days')
    horizontal_section(parts, 27, 102, 'Programming languages', stats.get('languages') or [], 5)
    horizontal_section(parts, 469, 102, 'Editors / IDEs', stats.get('editors') or [], 3)
    horizontal_section(parts, 469, 295, 'Operating systems', stats.get('operating_systems') or [], 2)
    end(parts, 'wakatime-breakdown.svg')


def update_readme():
    if not README.exists():
        raise RuntimeError('README.md does not exist')
    readme = README.read_text(encoding='utf-8')
    begin, finish = '<!--START_SECTION:waka-->', '<!--END_SECTION:waka-->'
    if readme.count(begin) != 1 or readme.count(finish) != 1:
        raise RuntimeError('README.md must contain exactly one START_SECTION:waka and END_SECTION:waka marker')
    section = (f'{begin}\n'
               f'![WakaTime Coding Dashboard](./assets/stats/wakatime-overview.svg?v={STAMP})\n\n'
               f'![WakaTime Weekly Breakdown](./assets/stats/wakatime-breakdown.svg?v={STAMP})\n'
               f'{finish}')
    new = re.sub(re.escape(begin) + r'[\s\S]*?' + re.escape(finish), lambda _: section, readme, count=1)
    if new == readme:
        print('README.md: unchanged')
    else:
        README.write_text(new, encoding='utf-8')
        print('Updated README.md WakaTime section and image cache versions')


def main():
    if not TOKEN:
        raise RuntimeError('Missing WakaTime token. Set WAKATIME_OAUTH_TOKEN or WAKATIME_API_KEY in repository secrets.')
    weekly = api('stats/last_7_days')
    lifetime = api('all_time_since_today')
    if not isinstance(weekly, dict) or not isinstance(lifetime, dict):
        raise RuntimeError('Unexpected WakaTime JSON schema')
    summary_card(weekly, lifetime)
    detail_card(weekly)
    update_readme()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('::error::' + str(exc), file=sys.stderr)
        sys.exit(1)
