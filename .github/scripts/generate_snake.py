#!/usr/bin/env python3
"""Render a Snake game from a GitHub contribution graph.

The snake plays a real, winnable game of Snake over your contribution grid:
it hunts every commit cell sparse-to-dense with BFS pathfinding, never crosses
its own body, grows one segment per cell eaten, fades a gradient from a bright
head to a dim tail, and tallies the commits it eats. Pure animated SVG (CSS +
no JS), so it renders anywhere GitHub shows an image. Data comes from the
public GitHub profile contribution calendar.
"""
# Adapted from dahan8473/snake-and-commits at
# 4ec3eec8531727c9679cd9f8e1c7d60ba1dc7b23. Local change: normalize partial
# calendar weeks by weekday before solving/rendering. See LICENSE.snake-and-commits.
import re
import urllib.parse
import urllib.request
from bisect import bisect_right
from collections import deque
from datetime import date
from html.parser import HTMLParser

CELL, GAP = 11, 3
PITCH = CELL + GAP
MX, MTOP, MBOT = 16, 26, 30
STEPS_PER_SEC = 10
PAUSE_STEPS = 26
BASE_LEN = 3

MONTHS = ["", "jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]

# Dark green contribution ramp and snake colors used by the profile image.
THEME = dict(
    levels=["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
    head="#b7ffd0",
    ramp=[(1, "#8affc1"), (4, "#39d353"), (10, "#26a641"), (21, "#006d32")],
    text="#7d8590",
)


class ProfileCalendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.counts = {}
        self.tooltip = None
        self.tooltip_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "ContributionCalendar-day" in attrs.get("class", "").split():
            self.cells[attrs["id"]] = (
                int(attrs["data-ix"]), attrs["data-date"], int(attrs["data-level"]),
            )
        elif tag == "tool-tip" and attrs.get("for") in self.cells:
            self.tooltip = attrs["for"]
            self.tooltip_text = []

    def handle_data(self, data):
        if self.tooltip is not None:
            self.tooltip_text.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.tooltip is not None:
            match = re.match(r"^(No|[0-9,]+) contributions? on ", "".join(self.tooltip_text).strip())
            if match:
                count = match[1]
                self.counts[self.tooltip] = 0 if count == "No" else int(count.replace(",", ""))
            self.tooltip = None


def fetch_weeks(user):
    login = urllib.parse.quote(user, safe="")
    req = urllib.request.Request(
        f"https://github.com/users/{login}/contributions",
        headers={"User-Agent": "profile-contribution-snake", "Accept-Language": "en"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        calendar = ProfileCalendar()
        calendar.feed(response.read().decode("utf-8"))
        calendar.close()

    if not calendar.cells or calendar.cells.keys() != calendar.counts.keys():
        raise ValueError("GitHub profile calendar is missing contribution cells or counts.")

    weeks = {}
    for cell_id, (column, day, level) in calendar.cells.items():
        weeks.setdefault(column, []).append({
            "date": day,
            "contributionCount": calendar.counts[cell_id],
            "contributionLevel": level,
        })
    return [
        {"contributionDays": sorted(days, key=lambda day: day["date"])}
        for _, days in sorted(weeks.items())
    ]


def calendar_grid(weeks):
    """Return 7-row contribution and count grids, with Sunday at row zero.

    GitHub omits days outside its displayed calendar from partial weeks.
    Place returned days by their actual weekday and leave omitted
    days empty, so pathfinding and rendering both use the same complete grid.
    """
    grid, counts = [], []
    for week in weeks:
        levels = [0] * 7
        week_counts = [0] * 7
        for day in week["contributionDays"]:
            row = (date.fromisoformat(day["date"]).weekday() + 1) % 7
            levels[row] = day["contributionLevel"]
            week_counts[row] = day["contributionCount"]
        grid.append(levels)
        counts.append(week_counts)
    return grid, counts


def solve(grid, cap=999):
    """Real Snake rules: head never enters an occupied cell; BFS to the nearest
    (sparse-first) commit cell avoiding the body; chase the tail when boxed in.
    Returns route, eats, growth steps, final length, uneaten count."""
    ncols = len(grid)

    def neighbors(cr):
        c, r = cr
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if 0 <= nc < ncols and 0 <= nr < len(grid[nc]):
                yield (nc, nr)

    def bfs(start_, goal, blocked):
        if start_ == goal:
            return [start_]
        qq, seen = deque([(start_, [start_])]), {start_}
        while qq:
            cur, path = qq.popleft()
            for nb in neighbors(cur):
                if nb in seen or (nb in blocked and nb != goal):
                    continue
                if nb == goal:
                    return path + [nb]
                seen.add(nb)
                qq.append((nb, path + [nb]))
        return None

    remaining = {(c, r) for c in range(ncols) for r in range(len(grid[c])) if grid[c][r] > 0}
    start = min(remaining, key=lambda cr: cr[0] * 10 + abs(cr[1] - 3)) if remaining else (0, 3)
    body = deque([start])
    occupied = {start}
    route, eats, growth = [start], [], []

    def allowed():
        return BASE_LEN + len(growth)

    def eat(cell):
        remaining.discard(cell)
        eats.append((len(route) - 1, cell))
        if BASE_LEN + len(growth) < cap:
            growth.append(len(route) - 1)

    def step_to(cell):
        route.append(cell)
        body.append(cell)
        occupied.add(cell)
        if cell in remaining:
            eat(cell)
        while len(body) > allowed():
            occupied.discard(body.popleft())

    if start in remaining:
        eat(start)

    def safe(cell):
        if len(body) < 8:
            return True
        grows = cell in remaining
        occ = set(occupied)
        occ.add(cell)
        b0 = body[0]
        if not grows and len(body) + 1 > allowed():
            occ.discard(body[0])
            b0 = body[1] if len(body) > 1 else cell
        return bfs(cell, b0, occ - {b0, cell}) is not None

    stuck = 0
    while remaining and len(route) < 4000:
        head = body[-1]
        blocked = occupied - {head}
        path = None
        for cand in sorted(remaining, key=lambda cr: grid[cr[0]][cr[1]] * 8 +
                           abs(cr[0] - head[0]) + abs(cr[1] - head[1]))[:24]:
            p = bfs(head, cand, blocked)
            if p and len(p) > 1:
                path = p
                break
        if path:
            aborted = False
            for cell in path[1:]:
                if not safe(cell):
                    aborted = True
                    break
                step_to(cell)
            if not aborted:
                stuck = 0
                continue
        stuck += 1
        if stuck > 400:
            break
        head = body[-1]
        blocked = occupied - {head}
        tail = body[0]
        tp = bfs(head, tail, blocked - {tail})
        nxt = None
        if tp and len(tp) > 1 and tp[1] not in occupied and safe(tp[1]):
            nxt = tp[1]
        else:
            free = [nb for nb in neighbors(head) if nb not in occupied]
            pool = [nb for nb in free if safe(nb)] or free
            if pool:
                nxt = max(pool, key=lambda cr: sum(1 for n in neighbors(cr) if n not in occupied))
        if nxt is None:
            break
        step_to(nxt)
    return route, eats, growth, len(remaining)


def render(grid, counts, months, route, eats, growth, generated_at=None):
    t = THEME
    ncols = len(grid)
    n = len(route)
    total = n + PAUSE_STEPS
    dur = total / STEPS_PER_SEC

    def pct(s):
        return round(s / total * 100, 3)

    def xy(c, r):
        return MX + c * PITCH, MTOP + r * PITCH

    def length_at(s):
        return BASE_LEN + bisect_right(growth, s)

    intervals, open_iv, prev = {}, {}, set()
    for s in range(n):
        bod = set(route[max(0, s - length_at(s) + 1): s + 1])
        for cell in bod - prev:
            open_iv[cell] = s
        for cell in prev - bod:
            intervals.setdefault(cell, []).append((open_iv.pop(cell), s))
        prev = bod
    for cell, st in open_iv.items():
        intervals.setdefault(cell, []).append((st, total))

    eaten_step = {cell: s for s, cell in eats}
    css, body = [], []
    for c in range(ncols):
        for r in range(len(grid[c])):
            x, y = xy(c, r)
            base = t["levels"][grid[c][r]]
            ivs = intervals.get((c, r), [])
            cls = f"c{c}_{r}"
            body.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{base}"/>')
            if not ivs:
                continue
            stops = [(0.0, base)]
            for a, b in ivs:
                post = base if (c, r) not in eaten_step or eaten_step[(c, r)] > b else t["levels"][0]
                pa = pct(a)
                stops += [(max(pa - .05, 0), None), (pa, t["head"])]
                for age, col in t["ramp"]:
                    if a + age < b:
                        stops.append((pct(a + age), col))
                if b < total:
                    pb = pct(b)
                    stops += [(max(pb - .05, 0), None), (pb, post)]
            frames, last = [], base
            for p, col in stops:
                col = last if col is None else col
                frames.append(f"{p}% {{ fill:{col}; }}")
                last = col
            frames.append(f"100% {{ fill:{last}; }}")
            css.append(f"@keyframes k{cls} {{ {' '.join(frames)} }}\n.{cls} {{ animation:k{cls} {dur:.1f}s linear infinite; }}")

    for c, label in months:
        x, _ = xy(c, 0)
        body.append(f'<text class="lab" x="{x}" y="14">{label}</text>')

    lx = MX + ncols * PITCH - GAP - 5 * (CELL + 3) - 62
    ly = MTOP + 7 * PITCH + 8
    body.append(f'<text class="lab" x="{lx-30}" y="{ly+9}">less</text>')
    for i in range(5):
        body.append(f'<rect x="{lx+i*(CELL+3)}" y="{ly}" width="{CELL}" height="{CELL}" rx="2.5" fill="{t["levels"][i]}"/>')
    body.append(f'<text class="lab" x="{lx+5*(CELL+3)+8}" y="{ly+9}">more</text>')

    if generated_at:
        contributions = sum(map(sum, counts))
        body.append(f'<text class="lab" x="{MX}" y="{ly+9}">{contributions:,} contributions</text>')

    w = MX * 2 + ncols * PITCH - GAP
    h = MTOP + 7 * PITCH - GAP + MBOT
    mono = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"
    timestamp = f' data-generated-at="{generated_at}"' if generated_at else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"{timestamp}>
  <style>
    .lab {{ font-family:{mono}; font-size:9.5px; fill:{t['text']}; }}
    @media (prefers-reduced-motion) {{ * {{ animation:none !important; }} }}
    {chr(10).join(css)}
  </style>
  {chr(10).join('  ' + b for b in body)}
</svg>
"""


def build_svg(weeks, generated_at=None):
    grid, counts = calendar_grid(weeks)
    months, seen = [], None
    for c, w in enumerate(weeks):
        m = int(w["contributionDays"][0]["date"].split("-")[1])
        if m != seen:
            months.append((c, MONTHS[m]))
            seen = m
    if months and months[0][0] == 0 and len(months) > 1 and months[1][0] <= 2:
        months = months[1:]

    for cap in (48, 40, 34, 28, 24, 20, 16, 12):
        route, eats, growth, left = solve(grid, cap)
        if left == 0:
            break

    return render(grid, counts, months, route, eats, growth, generated_at)
