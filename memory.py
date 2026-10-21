#!/usr/bin/env python3
"""EDGE living memory and feature research ledger. Runs at the end of grade.py; safe to run by hand.

  python3 memory.py                 rebuild memory/log, memory/research.json and memory/summary.md
  python3 memory.py query [filters] sample size and CLV of past reads that match, e.g.
        python3 memory.py query --sport NFL --market total --feature wind=15+
        python3 memory.py query --pattern news-lag --feature timing=early --since 2026-10-01

What it writes
  memory/log/<YYYY-MM>.jsonl  one entry per settled read (pick, lean or pass), keyed by pickId and upserted, never
                              dropped: sport, date, teams, open, close, line taken, fair (projected) number, result,
                              CLV, and the features present when the read was stamped.
  memory/research.json        every candidate feature: sample, mean CLV, t, beat-close rate, last-30-day CLV, and how
                              far it is from grade.py's promotion bar or the retirement bar.
  memory/summary.md           under 30 lines: what has beaten the close recently, what has not, closest to promotion,
                              the largest early-negative slices (still collecting), and data gaps.
                              Read this first in every session.

Rules
  Features are recorded only from data stored before or at the pick (the row's open, the pick's line and time, the
  injury, weather and goalie fields). Nothing after the pick is a feature, so CLV is never explained by itself.
  The test sample is the same one grade.py uses: one entry per pattern, row and side (the pick, else the first lean).
  Rereads and passes are logged but never counted in a feature's CLV.
  Status thresholds come from grade.py (STAGES). This file proposes; it never promotes, retires or changes a pattern.
  A feature that clears the bar is a lead for review, not a rule.
  Posture (Zack, 2026-10-19): EDGE is in its data-collection and learning phase. Negative CLV on early features is
  expected and is logged to learn from; no slice is labeled for retirement here. Statuses: research (too few reads to
  say), early-positive, early-negative (still collecting), at-promotion-bar.
"""

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import grade

ROOT = Path(__file__).resolve().parent
MEM = ROOT / "memory"
LOG = MEM / "log"
RESEARCH = MEM / "research.json"
SUMMARY = MEM / "summary.md"
HYPOTHESES = MEM / "hypotheses.md"
ARCH = ROOT / "ledger" / "archive"
RECENT_DAYS = 30

# Shipped data features: when each began, so coverage is measured only on reads stamped after it. A shipped feature
# at 0 coverage after MIN_READS_FOR_ALARM new reads is breakage (health check), not a quiet gap.
SHIPPED = {"pinAtPick": "2026-10-19T18:00:00Z", "contextAtPick": "2026-10-19T18:00:00Z"}

# When each feature's inputs exist, relative to the pick. Every feature in research.json must be "pre-pick".
FEATURE_TIMING = {
    "pattern": "pre-pick (stamped on the read)", "grade": "pre-pick (stamped)", "confidence": "pre-pick (stamped)",
    "market": "pre-pick (row id)", "timing": "pre-pick (pickedAt vs commence)", "venue": "pre-pick (picked side)",
    "role": "pre-pick (line and price at the pick)", "keyNumber": "pre-pick (line at the pick and fair)",
    "moveBeforePick": "pre-pick (open snapshot vs line at the pick)", "edgeBar": "pre-pick (edge and bar at the pick)",
    "injury": "pre-pick (contextAtPick or the read's reason text only)", "rest": "pre-pick (reason text)",
    "wind": "pre-pick (contextAtPick, or a row forecast whose asOf is before the pick)", "precip": "pre-pick (as wind)",
    "sharpDiv": "pre-pick (open snapshot)", "sharpDivPick": "pre-pick (pinAtPick)",
    "steamBeforePick": "pre-pick (stored snap 30m-6h before the pick vs pinAtPick)",
    "travel": "pre-pick (schedule + stats/team_venues.json)", "travelEdge": "pre-pick (schedule + team venues)",
    "tzShift": "pre-pick (schedule + team venues)",
    "restDays": "pre-pick (schedule)", "restEdge": "pre-pick (schedule)", "shortWeek": "pre-pick (schedule)",
    "sharpGapOpen": "pre-pick (open snapshot)", "sharpGapPick": "pre-pick (pinAtPick)", "bookAtPick": "pre-pick (stamped)",
}
POST_PICK_FIELDS = ["closeLine", "closePrice", "closeNoVig", "clvProb", "clvPoints", "result", "units", "score",
                    "injuryLatest", "weatherLatest", "autopsy"]
MIN_READS_FOR_ALARM = 10
CYCLE_HOURS = 26   # one daily health-check cycle, with slack: still at 0 after this is breakage

# Coverage of every added feature on graded reads: (log field, shipped at, sports in scope or None for all, note).
COVERED = [
    ("pinAtPick", "2026-10-19T18:00:00Z", None, "Pinnacle at the pick"),
    ("contextAtPick", "2026-10-19T18:00:00Z", None, "weather/injury/goalie as stamped"),
    ("sharpDivergenceAtPick", "2026-10-19T18:00:00Z", None, "needs Pinnacle on the same line"),
    ("daysRestHome", None, ("NBA", "NHL", "NCAAF", "NFL"), "schedules in stats/ (NFL from 2026-10-21)"),
    ("sharpDivergence", "2026-10-14T00:00:00Z", None, "Pinnacle at the open"),
    ("pinMoveBeforePick", "2026-10-19T18:15:00Z", None, "needs a stored snap 30m-6h before the pick"),
    ("travelMilesAway", None, ("NBA", "NHL", "NCAAF"), "schedules + team_venues.json; neutral sites skipped"),
]
SNAPS_SHIPPED = "2026-10-19T18:15:00Z"
SNAPS = ROOT / "ledger" / "snaps"
STEAM_MIN, STEAM_MAX_H = 30, 6   # the earlier snapshot must be 30 minutes to 6 hours before the pick
_SNAPROWS = None


def snap_rows():
    """Stored price snapshots by row id, oldest first (ledger/snaps, written by pull.py from 2026-10-19)."""
    global _SNAPROWS
    if _SNAPROWS is None:
        _SNAPROWS = defaultdict(list)
        if SNAPS.exists():
            for path in sorted(SNAPS.glob("*/*.jsonl")):
                for line in path.read_text().splitlines():
                    if line.strip():
                        try:
                            r = json.loads(line)
                            _SNAPROWS[r["id"]].append(r)
                        except (ValueError, KeyError):
                            continue
            for k in _SNAPROWS:
                _SNAPROWS[k].sort(key=lambda r: r.get("t") or "")
    return _SNAPROWS


def pin_no_vig(prices, side):
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in (prices or {})]
    if side not in keys or len(keys) < 2:
        return None
    try:
        import fair as fairlib
        return fairlib.probs({k: prices[k] for k in keys})[side]
    except Exception:  # noqa: BLE001
        return None


def pin_move_before_pick(pick):
    """Pinnacle's no-vig move on the picked side from the last stored snapshot 30 minutes to 6 hours before the pick
    to the pick itself (pinAtPick). Positive: Pinnacle moved toward our side before we took it. Pre-pick only.
    Returns (move, minutes) or (None, None)."""
    side, pin = pick.get("side"), pick.get("pinAtPick") or {}
    if not side or pin.get("noVig") is None or not pick.get("pickedAt"):
        return None, None
    try:
        t = parse(pick["pickedAt"])
    except ValueError:
        return None, None
    earlier = [r for r in snap_rows().get(pick.get("rowId"), []) if r.get("pin") and r.get("t")
               and timedelta(minutes=STEAM_MIN) <= t - parse(r["t"]) <= timedelta(hours=STEAM_MAX_H)]
    if not earlier:
        return None, None
    prev = earlier[-1]
    if pick.get("market") != "h2h" and prev["pin"].get("line") != pin.get("line"):
        return None, None   # a line move: the no-vig numbers are on different lines
    nv = pin_no_vig(prev["pin"].get("p"), side)
    if nv is None:
        return None, None
    return round(pin["noVig"] - nv, 4), round((t - parse(prev["t"])).total_seconds() / 60)


INTERACTION_FIELDS = {
    "sharpDivergenceAtPick": lambda e: e.get("sharpDivergenceAtPick") is not None,
    "steamBeforePick": lambda e: e.get("pinMoveBeforePick") is not None,
    "daysRest": lambda e: e.get("daysRestHome") is not None and e.get("daysRestAway") is not None,
    "contextAtPick": lambda e: bool(e.get("contextAtPick")),   # {} = stamped with nothing to record: not populated
}


def interaction_coverage(graded):
    """Graded reads with at least two of the interaction fields populated (so pair tests across them are possible)."""
    counts = [sum(1 for f in INTERACTION_FIELDS.values() if f(e)) for e in graded]
    return {"fields": list(INTERACTION_FIELDS), "atLeastTwo": sum(1 for c in counts if c >= 2), "graded": len(graded),
            "byField": {k: sum(1 for e in graded if f(e)) for k, f in INTERACTION_FIELDS.items()}}


def snap_writer(now):
    """Snapshot lines written in the last CYCLE_HOURS; 0 after the first cycle is breakage."""
    rows = snap_rows()
    cut = pull_iso(now - timedelta(hours=CYCLE_HOURS))
    recent = [r["t"] for v in rows.values() for r in v if (r.get("t") or "") >= cut]
    late = (now - parse(SNAPS_SHIPPED)).total_seconds() / 3600 > CYCLE_HOURS
    return {"since": SNAPS_SHIPPED, "linesLastCycle": len(recent), "latest": max(recent) if recent else None,
            "rowsWithHistory": sum(1 for v in rows.values() if len(v) >= 2), "alarm": late and not recent}


def pull_iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

# Candidate features EDGE wants to test but does not collect yet. Listed so they stay visible, with what is missing.
# Each note says what it would take to start collecting.
NOT_COLLECTED = {
    "public-pct": "Needs a betting-splits source (Action Network or VSiN pages, or a paid splits API), pulled near the "
                  "open and near kickoff per game. No free API in the stack today.",
    "guru": "Needs a list of X/Reddit accounts and a reader (Reddit API is free with an app key; X API is paid). "
            "Log account, number, time, result; keep after 20 settled calls beat the close (MISSION.md).",
}

SCHEDULES = {"NBA": "nba_games", "NHL": "nhl_games", "NCAAF": "ncaaf_games",
             "NFL": "nfl_schedule"}   # NFL: stats.py saves the ESPN schedule (2026-10-21)
TEAM_ALIAS = {"southern mississippi golden eagles": "southern miss golden eagles",
              "umass minutemen": "massachusetts minutemen"}
_SCHED = {}


def team_key(name):
    import unicodedata
    t = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9 ]", "", t)
    t = re.sub(r" +", " ", t).strip()
    return TEAM_ALIAS.get(t, t)


def schedule(sport):
    """Each team's game start times for a sport, from the schedule files already in stats/. Cached per run."""
    if sport not in _SCHED:
        out = defaultdict(list)
        name = SCHEDULES.get(sport)
        games = (load_json(ROOT / "stats" / f"{name}.json", {}).get("games") or {}) if name else {}
        for g in (games.values() if isinstance(games, dict) else games):
            for side in ("home", "away"):
                if g.get(side) and g.get("date"):
                    out[team_key(g[side])].append(g["date"].replace("Z", ":00Z") if len(g["date"]) == 17 else g["date"])
        for k in out:
            out[k].sort()
        _SCHED[sport] = out
    return _SCHED[sport]


def days_rest(sport, team, commence):
    """Whole days since the team's previous game start, or None when the schedule does not have it."""
    times = schedule(sport).get(team_key(team))
    if not times or not commence:
        return None
    try:
        now = parse(commence)
        prev = [t for t in times if parse(t) < now - timedelta(hours=6)]
        if not prev:
            return None
        # Elapsed time in whole days, not UTC calendar dates: a 7pm ET game is the next UTC day, so UTC dates
        # misbucketed ~25% of NBA/NHL/NCAAF gaps (b2b read as 1day and back). Rounded hours/24 matched the
        # venue-local calendar on all 8,212 stored gaps (2026-10-21). rest_nba.py/edge_stack.py already use UTC-6h.
        return round((now - parse(prev[-1])).total_seconds() / 86400)
    except ValueError:
        return None


_VENUES = None
_GAMES = {}


def team_home(sport, team):
    """Home location from stats/team_venues.json (built by team_venues.py): lat, lon, tz. None if unknown."""
    global _VENUES
    if _VENUES is None:
        _VENUES = load_json(ROOT / "stats" / "team_venues.json", {}).get("teams") or {}
    return (_VENUES.get(sport) or {}).get(team_key(team))


def team_games(sport):
    """Each team's games from the stored schedule: [(start, location team key or None if neutral)], oldest first."""
    if sport not in _GAMES:
        out = defaultdict(list)
        name = SCHEDULES.get(sport)
        games = (load_json(ROOT / "stats" / f"{name}.json", {}).get("games") or {}) if name else {}
        for g in (games.values() if isinstance(games, dict) else games):
            if not (g.get("home") and g.get("away") and g.get("date")):
                continue
            t = g["date"].replace("Z", ":00Z") if len(g["date"]) == 17 else g["date"]
            where = None if g.get("neutral") else team_key(g["home"])
            for side in ("home", "away"):
                out[team_key(g[side])].append((t, where))
        for k in out:
            out[k].sort()
        _GAMES[sport] = out
    return _GAMES[sport]


def miles(a, b):
    import math
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def utc_hours(tz, when):
    from zoneinfo import ZoneInfo
    return when.astimezone(ZoneInfo(tz)).utcoffset().total_seconds() / 3600


def travel(sport, team, commence, home_team):
    """(miles, time zones crossed) from the team's previous game location to this game (at home_team's venue).
    Positive zones: traveled east. None when the schedule, either location, or a neutral site leaves it unknown."""
    if not commence:
        return None, None
    try:
        now = parse(commence)
    except ValueError:
        return None, None
    games = team_games(sport).get(team_key(team)) or []
    this = [w for t, w in games if abs((parse(t) - now).total_seconds()) <= 6 * 3600]
    prev = [(t, w) for t, w in games if parse(t) < now - timedelta(hours=6)]
    if not prev or (this and this[0] is None):
        return None, None
    a = team_home(sport, prev[-1][1]) if prev[-1][1] else None
    b = team_home(sport, home_team)
    if not a or not b:
        return None, None
    return round(miles(a, b)), round(utc_hours(b["tz"], now) - utc_hours(a["tz"], parse(prev[-1][0])), 1)


def travel_bucket(m):
    return None if m is None else "none" if m < 50 else "<500" if m < 500 else "500-1500" if m < 1500 else "1500+"


def rest_bucket(sport, d):
    if d is None:
        return None
    if sport in ("NFL", "NCAAF"):
        return "short" if d < 6 else "normal" if d <= 8 else "long"
    return "b2b" if d <= 1 else "1day" if d == 2 else "2+days"


QB_WORDS = re.compile(r"\bQB\d?\b|quarterback", re.I)
GOALIE_WORDS = re.compile(r"goalie|goaltender", re.I)
REST_WORDS = re.compile(r"back-to-back|\bb2b\b|rest", re.I)


def load_json(path, default):
    try:
        return json.loads(path.read_text()) if path.exists() else default
    except ValueError:
        return default


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def all_rows():
    """Ledger rows plus archived rows, by id. Picked rows leave the ledger after 30 days, so both are needed."""
    rows = {}
    if ARCH.exists():
        for path in sorted(ARCH.glob("*/*.jsonl")):
            if path.name == "kalshi.jsonl":
                continue
            for line in path.read_text().splitlines():
                if line.strip():
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    rows[r.get("id")] = r
    for r in load_json(grade.LEDGER, {"rows": []}).get("rows") or []:
        rows[r.get("id")] = r
    return rows


def side_open_line(row, pick):
    """The open line from the picked side's point of view, or None."""
    snap = row.get("openSnap") or {}
    line = snap.get("line")
    if line is None or pick.get("market") == "h2h":
        return None
    if pick["market"] == "spread":
        return line if pick["side"] == "home" else -line
    return line


def minutes_to_kick(pick):
    try:
        return round((parse(pick["commence"]) - parse(pick["pickedAt"])).total_seconds() / 60)
    except (KeyError, TypeError, ValueError):
        return None


def sharp_divergence(pick, row):
    """Pinnacle minus the print book, no-vig probability of the picked side, at the OPEN (known before the pick).
    Positive: Pinnacle rated our side higher than the print book did. Only when both books show the same line."""
    side = pick.get("side")
    snap = row.get("openSnap") or {}
    books = snap.get("books") or {}
    pin = books.get("pinnacle")
    if not side or not pin:
        return None
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in snap and k in pin]
    if side not in keys or len(keys) < 2:
        return None
    if pick.get("market") != "h2h" and pin.get("line") != snap.get("line"):
        return None
    try:
        import fair as fairlib
        return round(fairlib.probs({k: pin[k] for k in keys})[side] - fairlib.probs({k: snap[k] for k in keys})[side], 4)
    except Exception:  # noqa: BLE001
        return None


def gap_bucket(d):
    """Size of the Pinnacle-vs-print gap, either direction, in no-vig probability."""
    a = abs(d)
    return "<1%" if a < 0.01 else "1-2%" if a < 0.02 else "2%+"


def sharp_divergence_at_pick(pick):
    """Pinnacle minus the print book, no-vig probability of the picked side, in the snapshot the read was priced
    from. Same line only. Stored from 2026-10-19 (pinAtPick)."""
    pin, side, mp = pick.get("pinAtPick") or {}, pick.get("side"), pick.get("marketPrices") or {}
    if not side or "noVig" not in pin or side not in mp:
        return None
    if pick.get("market") != "h2h" and pin.get("line") != pick.get("marketNumber"):
        return None
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in mp and k in (pin.get("prices") or {})]
    if len(keys) < 2:
        return None
    try:
        import fair as fairlib
        return round(pin["noVig"] - fairlib.probs({k: mp[k] for k in keys})[side], 4)
    except Exception:  # noqa: BLE001
        return None


def coverage(picks, now=None):
    """For each field stamped on picks: reads stamped since it shipped, and how many carry it (key present)."""
    now = now or datetime.now(timezone.utc)
    out = {}
    for name, since in SHIPPED.items():
        new = [p for p in picks if p.get("side") and (p.get("pickedAt") or "") >= since]
        have = sum(1 for p in new if p.get(name) is not None)
        late = (now - parse(since)).total_seconds() / 3600 > CYCLE_HOURS
        out[name] = {"since": since, "reads": len(new), "with": have,
                     "alarm": have == 0 and (len(new) >= MIN_READS_FOR_ALARM or (late and len(new) > 0))}
    return out


def graded_coverage(graded, now=None):
    """Each added feature on graded reads in scope since it shipped: 'feature X on N of M graded reads'."""
    now = now or datetime.now(timezone.utc)
    out = []
    for field, since, sports, note in COVERED:
        scope = [e for e in graded if (not since or (e.get("pickedAt") or "") >= since)
                 and (not sports or e.get("sport") in sports)]
        have = sum(1 for e in scope if e.get(field) is not None)
        late = bool(since) and (now - parse(since)).total_seconds() / 3600 > CYCLE_HOURS
        out.append({"field": field, "since": since, "sports": list(sports) if sports else None, "note": note,
                    "graded": len(scope), "with": have, "alarm": late and len(scope) > 0 and have == 0})
    return out


def features(pick, row):
    """Features present when the read was stamped. Keys are stable; values are short labels."""
    f = {"pattern": pick.get("pattern") or "none", "grade": pick.get("grade"), "confidence": pick.get("confidence"),
         "market": pick.get("market")}
    side, market = pick.get("side"), pick.get("market")
    mins = minutes_to_kick(pick)
    if mins is not None:
        hrs = mins / 60
        f["timing"] = "early" if hrs > 48 else "day" if hrs > 6 else "late"
    div = sharp_divergence(pick, row)
    if div is not None:
        f["sharpDiv"] = "pin-for" if div >= 0.01 else "pin-against" if div <= -0.01 else "aligned"
    dp = sharp_divergence_at_pick(pick)
    mv, _ = pin_move_before_pick(pick)
    if mv is not None:
        f["steamBeforePick"] = "toward" if mv >= 0.005 else "away" if mv <= -0.005 else "flat"
    if dp is not None:
        f["sharpDivPick"] = "pin-for" if dp >= 0.01 else "pin-against" if dp <= -0.01 else "aligned"
        f["sharpGapPick"] = gap_bucket(dp)
    if div is not None:
        f["sharpGapOpen"] = gap_bucket(div)
    if side:
        line, price = pick.get("lineAtPick"), pick.get("priceAtPick")
        if market in ("spread", "h2h"):
            f["venue"] = side
        if market == "spread" and isinstance(line, (int, float)):
            f["role"] = "fav" if line < 0 else "dog" if line > 0 else "pk"
            if pick.get("sport") in ("NFL", "NCAAF"):
                lo, hi = sorted((abs(line), abs(pick.get("fair") or line)))
                f["keyNumber"] = abs(line) in (3, 7, 3.5, 7.5, 2.5, 6.5) or any(lo <= k <= hi for k in (3, 7))
        elif market == "h2h" and isinstance(price, (int, float)):
            f["role"] = "fav" if price < 0 else "dog"
        elif market == "total":
            f["role"] = side
        # Line move from the open to the pick, from the picked side's view. "for": the number got better for us
        # before we took it (the market moved away from our side); "against": it moved toward our side first.
        ol = side_open_line(row, pick)
        if ol is not None and isinstance(line, (int, float)):
            gained = (line - ol) if market == "spread" or side == "under" else (ol - line)
            f["moveBeforePick"] = "for" if gained > 0 else "against" if gained < 0 else "none"
        edge, bar = pick.get("edge"), pick.get("bar")
        if isinstance(edge, (int, float)) and bar:
            ratio = edge / bar
            f["edgeBar"] = "<0.5x" if ratio < 0.5 else "0.5-1x" if ratio < 1 else "1-2x" if ratio < 2 else "2x+"
    # Pre-pick only (2026-10-19 audit): the row's injury, goalie and weather fields keep refreshing until kickoff, so
    # they are read only from the copy stamped on the pick (contextAtPick) or from the pick's own reason text.
    ctx = pick.get("contextAtPick") or {}
    inj = []
    text = " ".join(str(x) for x in (ctx.get("injury"), pick.get("reason")) if x)
    if ctx.get("injury") or (pick.get("pattern") == "news-lag" and pick.get("reason")):
        inj.append("any")
    if QB_WORDS.search(text):
        inj.append("qb")
    if ctx.get("goalie") or GOALIE_WORDS.search(text):
        inj.append("goalie")
    if inj:
        f["injury"] = inj
    if REST_WORDS.search(pick.get("reason") or ""):
        f["rest"] = True
    # Days rest from the schedule (known in advance, so pre-pick). Side picks: the picked team, and its rest against
    # the opponent's. Totals: the shorter rest of the two teams.
    sport = pick.get("sport")
    dh = days_rest(sport, row.get("home"), pick.get("commence"))
    da = days_rest(sport, row.get("away"), pick.get("commence"))
    if dh is not None and da is not None:
        if side in ("home", "away"):
            mine, theirs = (dh, da) if side == "home" else (da, dh)
            f["restDays"] = rest_bucket(sport, mine)
            f["restEdge"] = "more" if mine > theirs else "less" if mine < theirs else "even"
        elif side in ("over", "under"):
            f["restDays"] = rest_bucket(sport, min(dh, da))
        if sport in ("NFL", "NCAAF"):
            f["shortWeek"] = (min(dh, da) if side in ("over", "under") else (dh if side == "home" else da)) < 6
    mh, zh = travel(sport, row.get("home"), pick.get("commence"), row.get("home"))
    ma, za = travel(sport, row.get("away"), pick.get("commence"), row.get("home"))
    if mh is not None and ma is not None:
        if side in ("home", "away"):
            mine, theirs, zone = (mh, ma, zh) if side == "home" else (ma, mh, za)
            f["travel"] = travel_bucket(mine)
            f["travelEdge"] = "less" if mine < theirs - 200 else "more" if mine > theirs + 200 else "even"
            f["tzShift"] = "east" if zone >= 1 else "west" if zone <= -1 else "none"
        elif side in ("over", "under"):
            f["travel"] = travel_bucket(max(mh, ma))
    wd = ctx.get("weather") or {}
    if not wd:
        rw = row.get("weatherData") or {}
        if rw.get("asOf") and pick.get("pickedAt") and rw["asOf"] <= pick["pickedAt"]:
            wd = rw   # the row's forecast is still the one that existed at the pick
    if isinstance(wd.get("windMph"), (int, float)):
        w = wd["windMph"]
        f["wind"] = "15+" if w >= 15 else "10-15" if w >= 10 else "<10"
        if wd.get("heavy"):
            f["precip"] = "heavy"
    if pick.get("bookAtPick"):
        f["bookAtPick"] = pick["bookAtPick"]
    return f


def entry(pick, row, counted):
    snap_o, snap_c = row.get("openSnap") or {}, row.get("closeSnap") or {}
    e = {
        "pickId": pick["pickId"], "sport": pick.get("sport"), "date": (pick.get("commence") or "")[:10],
        "event": pick.get("event"), "home": row.get("home"), "away": row.get("away"),
        "market": pick.get("market"), "kind": pick.get("kind", "pick"), "counted": counted,
        "side": pick.get("side"), "pattern": pick.get("pattern"), "grade": pick.get("grade"),
        "openLine": snap_o.get("line"), "openPrices": {k: snap_o[k] for k in ("home", "away", "over", "under", "draw") if k in snap_o},
        "lineAtPick": pick.get("lineAtPick"), "priceAtPick": pick.get("priceAtPick"), "pickedAt": pick.get("pickedAt"),
        "minutesToKick": minutes_to_kick(pick), "sharpDivergence": sharp_divergence(pick, row),
        "pinAtPick": pick.get("pinAtPick"), "sharpDivergenceAtPick": sharp_divergence_at_pick(pick),
        "pinMoveBeforePick": pin_move_before_pick(pick)[0], "pinMoveWindowMin": pin_move_before_pick(pick)[1],
        "travelMilesHome": travel(pick.get("sport"), row.get("home"), pick.get("commence"), row.get("home"))[0],
        "travelMilesAway": travel(pick.get("sport"), row.get("away"), pick.get("commence"), row.get("home"))[0],
        "tzShiftAway": travel(pick.get("sport"), row.get("away"), pick.get("commence"), row.get("home"))[1],
        "tzShiftHome": travel(pick.get("sport"), row.get("home"), pick.get("commence"), row.get("home"))[1],
        "daysRestHome": days_rest(pick.get("sport"), row.get("home"), pick.get("commence")),
        "daysRestAway": days_rest(pick.get("sport"), row.get("away"), pick.get("commence")),
        "fair": pick.get("fair"), "edge": pick.get("edge"), "edgeUnit": pick.get("edgeUnit"), "bar": pick.get("bar"),
        "closeLine": snap_c.get("line"), "closePrice": pick.get("closePrice"), "closeNoVig": pick.get("closeNoVig"),
        "clvProb": pick.get("clvProb"), "clvPoints": pick.get("clvPoints"), "clvEstimated": pick.get("estimated"),
        "result": pick.get("result"), "units": pick.get("units"), "score": row.get("score"),
        "features": features(pick, row),
        "contextAtPick": pick.get("contextAtPick"),
        # Context only, never features: these row fields are the latest values, which can postdate the pick.
        "injuryLatest": row.get("injury") if row.get("injury") != "missing" else None,
        "weatherLatest": row.get("weather") if row.get("weather") != "missing" else None,
        "reason": pick.get("reason"), "falsifier": pick.get("falsifier"), "by": pick.get("by"),
        "notes": pick.get("note"),
    }
    # Post-pick explanation (autopsy.py): why the market moved and what decided the result. Never a feature.
    try:
        import autopsy
        e["autopsy"] = autopsy.autopsy(pick, row, e)
    except Exception as exc:  # noqa: BLE001
        e["autopsy"] = None
        print(f"::warning::autopsy failed for {pick.get('pickId')}: {exc}")
    return e


def tokens(f):
    """Feature tokens used for research and queries, e.g. timing=early, injury=qb."""
    out = []
    for k, v in f.items():
        for val in (v if isinstance(v, list) else [v]):
            if val is None or val is False:
                continue
            out.append(f"{k}={'yes' if val is True else val}")
    return out


def stats(vals):
    n = len(vals)
    mean = sum(vals) / n if n else None
    return {"n": n, "meanClvProb": round(mean, 4) if n else None, "tStat": round(grade.tstat(vals), 2),
            "beatClose": sum(1 for v in vals if v > 0)}


def status_for(n, mean, t, fast=False):
    """Where a feature stands against grade.py's own bars (fast track for gate-passed learned patterns, as in
    grade.py). Never changes a pattern."""
    need = grade.stage_t(n, fast)
    if need is not None and mean is not None and mean > 0 and t >= need:
        return "at-promotion-bar", 0, 0.0
    first_n, first_t = (grade.FAST_TRACK if fast else grade.STAGES)[0]
    label = "research" if n < 8 or mean is None else "early-positive" if mean > 0 else "early-negative"
    return label, max(0, first_n - n), round(max(0.0, (need or first_t) - t), 2)


def build():
    now = datetime.now(timezone.utc)
    picks = load_json(grade.PICKS, {"picks": []}).get("picks") or []
    rows = all_rows()

    first = {}
    for p in sorted(picks, key=lambda p: (p.get("kind", "pick") != "pick", p.get("pickedAt") or "")):
        if p.get("kind", "pick") in ("pick", "lean") and p.get("side"):
            first.setdefault((p.get("pattern"), p.get("rowId"), p.get("side")), p)
    counted_ids = {p["pickId"] for p in first.values()}

    # 1. Log: upsert settled reads by pickId, month by month. Old entries are kept even if picks.json is pruned.
    LOG.mkdir(parents=True, exist_ok=True)
    months = defaultdict(dict)
    for path in LOG.glob("*.jsonl"):
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    e = json.loads(line)
                    months[path.stem][e["pickId"]] = e
                except (ValueError, KeyError):
                    continue
    added = 0
    for p in picks:
        row =rows.get(p.get("rowId")) or {}
        settled = "clvProb" in p or p.get("result") or (row.get("final") and p.get("kind") == "pass")
        if not settled:
            continue
        month = (p.get("commence") or p.get("pickedAt") or "unknown")[:7]
        if p["pickId"] not in months[month]:
            added += 1
        months[month][p["pickId"]] = entry(p, row, p["pickId"] in counted_ids)
    for month, entries in months.items():
        lines = [json.dumps(e, ensure_ascii=False, separators=(",", ":"))
                 for e in sorted(entries.values(), key=lambda e: (e.get("date") or "", e["pickId"]))]
        (LOG / f"{month}.jsonl").write_text("\n".join(lines) + "\n")
    log = [e for m in months.values() for e in m.values()]

    # 2. Research ledger: every feature token across counted, graded reads, overall and per sport.
    cutoff = (now - timedelta(days=RECENT_DAYS)).strftime("%Y-%m-%d")
    graded = [e for e in log if e.get("counted") and isinstance(e.get("clvProb"), (int, float))]
    groups = defaultdict(list)
    for e in graded:
        for tok in tokens(e["features"]):
            if tok.startswith(("market=", "grade=", "confidence=")):
                groups[("ALL", tok)].append(e)
                continue
            groups[("ALL", tok)].append(e)
            groups[(e["sport"], tok)].append(e)
    old = load_json(RESEARCH, {})
    first_seen = {f["key"]: f.get("firstSeen") for f in old.get("features", [])}
    feats = []
    for (sport, tok), es in groups.items():
        vals = [e["clvProb"] for e in es]
        picks_only = [e["clvProb"] for e in es if e["kind"] == "pick"]
        recent = [e["clvProb"] for e in es if (e.get("date") or "") >= cutoff]
        s = stats(vals)
        fast = tok.startswith("pattern=") and grade.gate_passed(tok[8:])
        st, n_short, t_short = status_for(s["n"], s["meanClvProb"], s["tStat"], fast)
        settled = [e for e in es if e.get("result") in ("win", "loss", "push")]
        key = f"{sport}|{tok}"
        feats.append({
            "key": key, "sport": sport, "feature": tok, **s, "status": st,
            "picksN": len(picks_only), "picksMeanClvProb": round(sum(picks_only) / len(picks_only), 4) if picks_only else None,
            "recentN": len(recent), "recentMeanClvProb": round(sum(recent) / len(recent), 4) if recent else None,
            "nShortOfFirstStage": n_short, "tShort": t_short,
            "record": "{}-{}-{}".format(*(sum(1 for e in settled if e["result"] == r) for r in ("win", "loss", "push"))),
            "firstSeen": first_seen.get(key) or now.strftime("%Y-%m-%d"),
        })
    feats.sort(key=lambda f: (f["sport"] != "ALL", f["sport"], f["feature"]))
    new_patterns = sorted({f["feature"][8:] for f in feats if f["feature"].startswith("pattern=") and f["key"] not in first_seen})
    research = {
        "asOf": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rules": (f"Sample: one entry per pattern, row and side (grade.py). Bars from grade.py: promotion at mean CLV > 0 "
                  f"and t >= {grade.STAGES[0][1]} at {grade.STAGES[0][0]}+ (t >= {grade.STAGES[-1][1]} at "
                  f"{grade.STAGES[-1][0]}+). Learning phase: early-negative means still collecting, never a "
                  f"retirement call. A feature at a bar is a lead for review; this file never changes a pattern. "
                  f"Win rate never counts."),
        "gradedReads": len(graded), "loggedReads": len(log),
        "newPatternsThisRun": new_patterns,
        "notCollected": NOT_COLLECTED,
        "coverage": coverage(picks, now),
        "gradedCoverage": graded_coverage(graded, now),
        "snapWriter": snap_writer(now),
        "interactionCoverage": interaction_coverage(graded),
        "featureTiming": FEATURE_TIMING, "postPickFields": POST_PICK_FIELDS,
        "sharpDivergenceCoverage": {"graded": len(graded),
                                    "withData": sum(1 for e in graded if e.get("sharpDivergence") is not None)},
        "features": feats,
    }
    patterns = load_json(grade.LEDGER, {}).get("patterns") or []
    research["flags"] = flags(feats, patterns)
    pstat = {p["id"]: p for p in patterns}
    for f in feats:
        why = why_not_promoted(f, pstat)
        if why:
            f["why_not_promoted"] = why
    research["gradeReliability"] = grade_reliability(graded)
    research["autopsy"] = autopsy_report(graded, feats)
    # Conditional pockets for every early-negative slice with 15+ reads, and for grade A.
    research["pockets"] = []
    for f in feats:
        if f["status"] == "early-negative" and f["n"] >= 15 and not f["feature"].startswith("confidence="):
            best, tested = pocket(slice_entries(graded, f), f["feature"].split("=")[0], with_sport=f["sport"] == "ALL")
            pb, pt = pair_pocket(slice_entries(graded, f), f["feature"].split("=")[0])
            research["pockets"].append({"slice": f["key"], "n": f["n"], "meanClvProb": f["meanClvProb"],
                                        "pocket": best, "tested": tested, "pairPocket": pb, "pairsTested": pt})

    MEM.mkdir(parents=True, exist_ok=True)
    research["hypothesesAdded"] = append_hypotheses(research.get("pockets") or [], now)
    RESEARCH.write_text(json.dumps(research, indent=1) + "\n")
    SUMMARY.write_text(summary(research, now, patterns, graded))
    return {"logged": len(log), "newLogEntries": added, "graded": len(graded), "features": len(feats),
            "newPatterns": new_patterns}


def fmt(f):
    m = f["meanClvProb"]
    r = f["recentMeanClvProb"]
    return (f"{f['sport']} {f['feature']}: n {f['n']}, CLV {m * 100:+.1f}%, t {f['tStat']:+.1f}"
            + (f", last {RECENT_DAYS}d {r * 100:+.1f}% on {f['recentN']}" if r is not None else ""))


GAP_SHORT = {
    "public-pct": "needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack",
    "nfl-rest": "needs stats.py to save the free nflverse schedule (stats/nfl_schedule.json); code only",
    "guru": "needs an account list + reader (Reddit API free, X API paid); log account, number, time, result",
}


def dedupe(features):
    """Drop a cross-sport (ALL) line when one sport holds the whole sample: it would repeat that sport's line."""
    by_key = {(f["sport"], f["feature"]): f for f in features}
    sports = {f["sport"] for f in features} - {"ALL"}
    return [f for f in features if not (f["sport"] == "ALL" and any(
        (by_key.get((s, f["feature"])) or {}).get("n") == f["n"] for s in sports))]


WHY_NOT_N = 30


def why_not_promoted(f, pstat):
    """One line for a feature or slice with n >= WHY_NOT_N that is at or below 0 CLV or short of its bar.
    Learning phase: an explanation, never a retirement call."""
    if f["n"] < WHY_NOT_N or f["status"] == "at-promotion-bar":
        return None
    fast = f["feature"].startswith("pattern=") and grade.gate_passed(f["feature"][8:])
    need = grade.stage_t(f["n"], fast)
    m, t = f["meanClvProb"] or 0.0, f["tStat"]
    if m <= 0:
        why = f"mean CLV {m * 100:+.1f}% is at or below 0; promotion needs mean CLV > 0 and t >= {need}"
    else:
        why = f"mean CLV {m * 100:+.1f}% is positive but t {t:+.1f} is under the t >= {need} bar at n {f['n']}"
    if f["feature"].startswith("pattern="):
        ps = pstat.get(f["feature"][8:])
        first_n = (grade.FAST_TRACK if fast else grade.STAGES)[0][0]
        if ps:
            why += (f"; grade.py promotes on graded full-bar picks only: {ps.get('clvN', 0)} of the "
                    f"{ps.get('nNeeded', 0) + ps.get('clvN', 0)} needed (leans never promote)")
        else:
            why += (f"; every read so far is a lean, so grade.py has no graded full-bar picks for it "
                    f"({first_n} needed; leans never promote)")
    else:
        why += "; a feature slice is research only and is never promoted on its own"
    return why + ". Still collecting."


def flags(features, patterns):
    """Standing observations for every health check. They never change a rule."""
    out = []
    g = {f["feature"][6:]: f for f in features if f["sport"] == "ALL" and f["feature"].startswith("grade=")
         and f["meanClvProb"] is not None}
    if all(k in g for k in "ABC"):
        a, b, c = (g[k]["meanClvProb"] for k in "ABC")
        out.append({"type": "grade-order", "ordered": a > b > c,
                    "A": {"n": g["A"]["n"], "meanClvProb": a}, "B": {"n": g["B"]["n"], "meanClvProb": b},
                    "C": {"n": g["C"]["n"], "meanClvProb": c},
                    "note": "Observation, not a defect: in a working system A > B > C on CLV. Until it is, edge size "
                            "is not yet predicting CLV."})
    return out


POCKET_MIN_N = 8


def pocket_tokens(e, with_sport):
    toks = set(tokens(e.get("features") or {}))
    if with_sport:
        toks.add(f"sport={e.get('sport')}")
    return toks


def pocket(entries, exclude_key, with_sport=True):
    """Inside one slice, the best one-feature sub-slice with mean CLV >= 0 and n >= POCKET_MIN_N.
    Returns (best or None, combinations tested). Many combinations are tested, so a pocket is a lead to keep
    watching, not a finding."""
    groups = defaultdict(list)
    for e in entries:
        for tok in pocket_tokens(e, with_sport):
            if tok.split("=")[0] != exclude_key and not tok.startswith("confidence="):
                groups[tok].append(e["clvProb"])
    tested = [(tok, v) for tok, v in groups.items() if len(v) >= POCKET_MIN_N and len(v) < len(entries)]
    hits = [(tok, v) for tok, v in tested if sum(v) / len(v) >= 0]
    if not hits:
        return None, len(tested)
    tok, v = max(hits, key=lambda h: (sum(h[1]) / len(h[1]), len(h[1])))
    return {"feature": tok, "n": len(v), "meanClvProb": round(sum(v) / len(v), 4), "tStat": round(grade.tstat(v), 2)}, len(tested)


# Pre-defined two-feature interactions tested inside the largest early-negative slices (2026-10-19). Fixed in advance
# so the search stays small; a pair that includes the slice's own feature is skipped.
INTERACTIONS = [("wind", "role"), ("role", "rest"), ("role", "moveBeforePick"), ("timing", "sharpDivPick"),
                ("timing", "sharpGapOpen"), ("venue", "role"), ("injury", "role"), ("edgeBar", "timing")]


def pair_pocket(entries, exclude_key):
    """Best value combination of a pre-defined feature pair inside a slice, with CLV >= 0 and n >= POCKET_MIN_N.
    Returns (best or None, combinations tested)."""
    groups = defaultdict(list)
    for e in entries:
        f = e.get("features") or {}
        for a, b in INTERACTIONS:
            if exclude_key in (a, b) or a not in f or b not in f:
                continue
            va = f[a] if isinstance(f[a], list) else [f[a]]
            vb = f[b] if isinstance(f[b], list) else [f[b]]
            for x in va:
                for y in vb:
                    groups[f"{a}={'yes' if x is True else x} + {b}={'yes' if y is True else y}"].append(e["clvProb"])
    tested = [(k, v) for k, v in groups.items() if len(v) >= POCKET_MIN_N and len(v) < len(entries)]
    hits = [(k, v) for k, v in tested if sum(v) / len(v) >= 0]
    if not hits:
        return None, len(tested)
    k, v = max(hits, key=lambda h: (sum(h[1]) / len(h[1]), len(h[1])))
    return {"feature": k, "n": len(v), "meanClvProb": round(sum(v) / len(v), 4), "tStat": round(grade.tstat(v), 2)}, len(tested)


def grade_order_pockets(graded, min_n=5):
    """Features inside which the grade order holds (A > B > C on CLV, each grade with min_n+ reads)."""
    by = defaultdict(lambda: defaultdict(list))
    for e in graded:
        g = (e.get("features") or {}).get("grade")
        if g not in ("A", "B", "C"):
            continue
        for tok in pocket_tokens(e, True):
            if not tok.startswith(("grade=", "confidence=")):
                by[tok][g].append(e["clvProb"])
    tested, holds = 0, []
    for tok, gs in by.items():
        if all(len(gs[k]) >= min_n for k in "ABC"):
            tested += 1
            m = {k: sum(gs[k]) / len(gs[k]) for k in "ABC"}
            if m["A"] > m["B"] > m["C"]:
                holds.append({"feature": tok, **{k: {"n": len(gs[k]), "meanClvProb": round(m[k], 4)} for k in "ABC"}})
    holds.sort(key=lambda h: -(h["A"]["meanClvProb"] - h["C"]["meanClvProb"]))
    return holds, tested


RELIABILITY_WINDOW = 50


def grade_reliability(graded, window=RELIABILITY_WINDOW):
    """Diagnostic: on the last `window` graded reads (by pick time), mean CLV by grade and whether A > B > C."""
    last = sorted(graded, key=lambda e: e.get("pickedAt") or "")[-window:]
    out = {"window": len(last), "from": (last[0].get("pickedAt") if last else None)}
    for g in "ABC":
        v = [e["clvProb"] for e in last if (e.get("features") or {}).get("grade") == g]
        out[g] = {"n": len(v), "meanClvProb": round(sum(v) / len(v), 4) if v else None}
    m = [out[g]["meanClvProb"] for g in "ABC"]
    out["ordered"] = None if None in m else m[0] > m[1] > m[2]
    return out


def slice_entries(graded, f):
    return [e for e in graded if (f["sport"] == "ALL" or e.get("sport") == f["sport"])
            and f["feature"] in pocket_tokens(e, False)]


def pocket_line(best, tested, inside):
    if best is None:
        return f"  > no conditional pocket found in current features ({tested} combos tested inside {inside})"
    return (f"  > pocket: {best['feature']} inside {inside}: n {best['n']}, CLV {best['meanClvProb'] * 100:+.1f}%, "
            f"t {best['tStat']:+.1f} (best of {tested} tested; a lead to watch)")


def combo_key(*parts):
    """Order-free name for a feature combination: 'role=dog inside moveBeforePick=none' and the reverse are one."""
    toks = sorted({t.strip() for p in parts for t in p.split(" + ")})
    return " + ".join(toks)


def append_hypotheses(pockets, now):
    """Append each neutral-or-positive pocket the first time its combination is seen. Rows already in the file are
    never edited or removed. A single pocket inside a slice is the slice plus the feature; a pair pocket is the pair.
    Leads to watch only: nothing is promoted from this file."""
    if not HYPOTHESES.exists():
        return 0
    text = HYPOTHESES.read_text()
    have = set()
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[0][:4].isdigit():
            have.add(combo_key(cells[1].split(": ", 1)[-1]) if ": " in cells[1] else combo_key(cells[1]))
            have.add(cells[1])
    rows = []
    # A cross-sport (ALL) pocket whose whole sample is one sport is the same lead as that sport's row: keep the sport's.
    sport_ns = set()
    for p in pockets:
        sport, slice_tok = p["slice"].split("|", 1)
        if sport != "ALL":
            for kind, bb in (("single", p.get("pocket")), ("pair", p.get("pairPocket"))):
                if bb:
                    sport_ns.add((combo_key(slice_tok, bb["feature"]) if kind == "single" else combo_key(bb["feature"]), bb["n"]))
    for p in pockets:
        sport, slice_tok = p["slice"].split("|", 1)
        for kind, b, tested in (("single", p.get("pocket"), p.get("tested")), ("pair", p.get("pairPocket"), p.get("pairsTested"))):
            if not b or b["meanClvProb"] < 0:
                continue
            combo = combo_key(slice_tok, b["feature"]) if kind == "single" else combo_key(b["feature"])
            if sport == "ALL" and (combo, b["n"]) in sport_ns:
                continue
            name = combo if sport == "ALL" else f"{sport}: {combo}"
            if name in have or combo_key(name) in have:
                continue
            have.add(name)
            note = (f"found inside {sport} {slice_tok} (best of {tested} {'pairs' if kind == 'pair' else 'features'} tested); "
                    "small sample, may share reads with other rows")
            rows.append(f"| {now.strftime('%Y-%m-%d')} | {name} | {b['n']} | {b['meanClvProb'] * 100:+.1f}% | {note} |")
    if rows:
        HYPOTHESES.write_text(text.rstrip("\n") + "\n" + "\n".join(rows) + "\n")
    return len(rows)


def summary(research, now, patterns, graded):
    feats = dedupe([f for f in research["features"] if not f["feature"].startswith(("grade=", "confidence="))])
    pstat = {p["id"]: p for p in patterns}
    leads = sorted([f for f in feats if f["feature"].startswith("pattern=") and f["status"] == "early-positive"],
                   key=lambda f: -f["n"])
    # Largest samples first, not the worst t: the point is where the most is being learned, not what to cut.
    neg = sorted([f for f in feats if f["status"] == "early-negative" and not f["feature"].startswith("confidence=")],
                 key=lambda f: -f["n"])[:3]
    other = [f for f in feats if f["n"] >= 8 and f["recentN"] >= 8 and not f["feature"].startswith(("pattern=", "market="))]
    top2 = sorted([f for f in other if f["recentMeanClvProb"] > 0], key=lambda f: -f["recentMeanClvProb"])[:2]
    low2 = sorted([f for f in other if f["recentMeanClvProb"] < 0], key=lambda f: f["recentMeanClvProb"])[:2]
    lines = [f"# What EDGE is learning ({now.strftime('%Y-%m-%d %H:%M')}Z)",
             "Phase: data collection and learning. Samples are small and key features are still being added. "
             "Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.",
             f"{research['gradedReads']} graded reads counted, {research['loggedReads']} logged. CLV is mean clvProb. "
             "Patterns move only by grade.py.",
             "Early positive leads (one of many being tested; no acceleration):"]
    for f in leads[:3]:
        ps = pstat.get(f["feature"][8:]) or {}
        need = (f"; grade.py needs {ps.get('nNeeded', '?')} more graded full-bar picks (has {ps.get('clvN', 0)}), "
                f"t >= {ps.get('tNeeded', '?')}") if ps else ""
        lines.append(f"- {fmt(f)}{need}")
    if not leads:
        lines.append("- none yet")
    lines.append("Early negative, still collecting (largest samples):")
    for i, f in enumerate(neg):
        lines.append(f"- {fmt(f)}")
        ents = slice_entries(graded, f)
        best, tested = pocket(ents, f["feature"].split("=")[0], with_sport=f["sport"] == "ALL")
        line = pocket_line(best, tested, f["feature"])
        if i < 3:
            pb, pt = pair_pocket(ents, f["feature"].split("=")[0])
            line += (f" | pair: {pb['feature']} n {pb['n']}, CLV {pb['meanClvProb'] * 100:+.1f}% (best of {pt})" if pb
                     else f" | pair: none ({pt} pair combos tested)")
        lines.append(line)
    if not neg:
        lines.append("- none")
    go = next((x for x in research["flags"] if x["type"] == "grade-order"), None)
    if go:
        txt = ", ".join(f"{k} {go[k]['meanClvProb'] * 100:+.1f}% on {go[k]['n']}" for k in "ABC")
        lines.append(f"Observation: {'grades rank A > B > C' if go['ordered'] else 'edge size is not yet predicting CLV'}"
                     f" ({txt}).")
        gr = research.get("gradeReliability") or {}
        if gr.get("window"):
            verdict = {True: "A > B > C holds", False: "order still wrong", None: "a grade is missing"}[gr["ordered"]]
            lines.append(f"  > last {gr['window']} graded reads: " + ", ".join(
                f"{k} {gr[k]['meanClvProb'] * 100:+.1f}% on {gr[k]['n']}" if gr[k]["meanClvProb"] is not None
                else f"{k} none" for k in "ABC") + f" ({verdict}; diagnostic only)")
        ga = [e for e in graded if (e.get("features") or {}).get("grade") == "A"]
        best, tested = pocket(ga, "grade")
        lines.append(pocket_line(best, tested, "grade A"))
        holds, tested = grade_order_pockets(graded)
        if holds:
            h = holds[0]
            lines.append(f"  > order holds inside {h['feature']}: " + ", ".join(
                f"{k} {h[k]['meanClvProb'] * 100:+.1f}% on {h[k]['n']}" for k in "ABC")
                + f" ({len(holds)} of {tested} features tested)")
        else:
            lines.append(f"  > grade order holds inside no feature yet ({tested} tested with 5+ reads per grade)")
    lines += autopsy_lines(research.get("autopsy") or {})
    free_gaps = [f"- {k}: {GAP_SHORT[k]}" for k in ("nfl-rest",) if k in research["notCollected"]]
    if free_gaps:
        lines += ["Data gaps, free (building next):"] + free_gaps
    lines.append("Data gaps, waiting on a source: " + "; ".join(
        f"{k} ({GAP_SHORT[k]})" for k in ("public-pct", "guru") if k in research["notCollected"]))
    lines.append("Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):")
    sw = research.get("snapWriter") or {}
    if sw:
        lines.append(f"- {'BREAKAGE: ' if sw['alarm'] else ''}snaps: {sw['linesLastCycle']} price snapshots stored in the last "
                     f"{CYCLE_HOURS}h, latest {sw['latest'][5:16].replace('T', ' ') + 'Z' if sw['latest'] else 'none'}, "
                     f"{sw['rowsWithHistory']} games with 2+ (late steam, since {sw['since'][5:16].replace('T', ' ')}Z)")
    new = research.get("coverage") or {}
    for c in research.get("gradedCoverage") or []:
        scope = f" {'/'.join(c['sports'])}" if c["sports"] else ""
        since = f" since {c['since'][5:16].replace('T', ' ')}Z" if c["since"] else ""
        stamped = new.get(c["field"])
        tail = f"; {stamped['with']} of {stamped['reads']} new reads stamped" if stamped else ""
        alarm = c["alarm"] or (stamped or {}).get("alarm")
        lines.append(f"- {'BREAKAGE: ' if alarm else ''}{c['field']} on {c['with']} of {c['graded']} graded{scope} reads"
                     f"{since}{tail} ({c['note']})")
    ic = research.get("interactionCoverage") or {}
    if ic:
        lines.append(f"Interaction coverage: {ic['atLeastTwo']} graded reads have at least two of "
                     f"({', '.join(ic['fields'])}) populated.")
    sc = scanner_line()
    if sc:
        lines.insert(3, sc)
    return "\n".join(lines[:30]) + "\n"


def scanner_line():
    """One line on the strategy scanner (scan.py): what it is tracking and how its live reads are doing on CLV."""
    store = load_json(ROOT / "stats" / "scan" / "strategies.json", {})
    S = store.get("strategies") or {}
    if not S:
        return None
    tracking = [s for s in S.values() if s.get("status") == "tracking"]
    log = []
    for path in sorted(LOG.glob("*.jsonl")):
        log += [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    mine = [e for e in log if str(e.get("pattern") or "").startswith("scan-") and e.get("counted")
            and isinstance(e.get("clvProb"), (int, float))]
    clv = f", mean CLV {sum(e['clvProb'] for e in mine) / len(mine) * 100:+.1f}%" if mine else ""
    new = sum(1 for s in tracking if (s.get("firstFound") or "")[:10] == (store.get("asOf") or "")[:10])
    return (f"Scanner (scan.py, {(store.get('asOf') or '')[5:16].replace('T', ' ')}Z): {len(tracking)} strategies tracking "
            f"from {store.get('tests', 0)} hypotheses ({new} new this run); {len(mine)} graded scan reads{clv}. "
            "Shadow only; grade.py decides promotion.")


CAUSE_ORDER = ["news-after-pick", "sharps-against-at-pick", "sharps-against-at-open", "bet-into-steam", "late-move",
               "number-off", "unknown"]
VERDICTS = ["right-and-rewarded", "right-but-unlucky", "lucky-win", "market-was-right", "push"]


def autopsy_report(graded, feats):
    """Post-pick explanations across counted, graded reads (autopsy.py). Explains; never promotes or retires.
    Each loss-to-the-close cause points at the pre-pick feature that could have warned us, with that feature's CLV:
    the feature, not the cause, is what gets tested."""
    have = [e for e in graded if (e.get("autopsy") or {}).get("market")]
    by_feat = {f["key"]: f for f in feats}
    lost = [e for e in have if e["autopsy"]["market"]["clv"] == "lost"]
    causes = {}
    for c in CAUSE_ORDER:
        es = [e for e in lost if e["autopsy"]["market"]["cause"] == c]
        if not es:
            continue
        sports = defaultdict(int)
        pats = defaultdict(int)
        for e in es:
            sports[e["sport"]] += 1
            pats[e.get("pattern") or "none"] += 1
        pre = es[0]["autopsy"]["market"].get("prePickFeature")
        pf = by_feat.get(f"ALL|{pre}") if pre else None
        causes[c] = {**stats([e["clvProb"] for e in es]), "share": round(len(es) / len(lost), 3),
                     "bySport": dict(sorted(sports.items(), key=lambda kv: -kv[1])),
                     "topPatterns": dict(sorted(pats.items(), key=lambda kv: -kv[1])[:5]),
                     "prePickFeature": pre,
                     "prePickFeatureClv": {k: pf[k] for k in ("n", "meanClvProb", "tStat", "status")} if pf else None}
    for_us = [e for e in have if e["autopsy"]["market"]["cause"] == "news-for-us"]
    games = [e for e in have if (e["autopsy"].get("game") or {}).get("verdict")]
    verdicts = {}
    for v in VERDICTS:
        es = [e for e in games if e["autopsy"]["game"]["verdict"] == v]
        if es:
            verdicts[v] = {**stats([e["clvProb"] for e in es])}
    tags = defaultdict(lambda: {"n": 0, "inVerdict": defaultdict(int)})
    for e in games:
        for t in e["autopsy"]["game"].get("tags") or []:
            tags[t]["n"] += 1
            tags[t]["inVerdict"][e["autopsy"]["game"]["verdict"]] += 1
    return {
        "note": ("Post-pick. Causes explain why reads lost to the close; verdicts and tags explain results. Nothing here "
                 "is a feature or a rule: a cause becomes testable only through its pre-pick feature."),
        "graded": len(graded), "withAutopsy": len(have),
        "causeKnown": sum(1 for e in lost if e["autopsy"]["market"]["cause"] != "unknown"),
        "lostToClose": len(lost), "beatClose": len(have) - len(lost), "newsForUs": len(for_us),
        "lossCauses": causes,
        "verdicts": verdicts,
        "withBox": sum(1 for e in games if e["autopsy"]["game"].get("boxSourced")),
        "varianceTags": {k: {"n": v["n"], "inVerdict": dict(v["inVerdict"])}
                         for k, v in sorted(tags.items(), key=lambda kv: -kv[1]["n"])},
    }


def autopsy_lines(rep):
    """Two summary lines: why reads lost to the close, and process vs result."""
    if not rep or not rep.get("withAutopsy"):
        return []
    lc = rep.get("lossCauses") or {}
    parts = [f"{c} {v['n']} ({v['meanClvProb'] * 100:+.1f}%)" for c, v in lc.items()]
    out = [f"Why reads lost to the close (autopsy, post-pick; {rep['lostToClose']} of {rep['withAutopsy']}, cause known on "
           f"{rep['causeKnown']}): " + ", ".join(parts)]
    vd = rep.get("verdicts") or {}
    unlucky = [k.split(":")[0] for k, v in (rep.get("varianceTags") or {}).items()
               if k.endswith(":hurt") and v["inVerdict"].get("right-but-unlucky")][:3]
    out.append("Process vs result: " + ", ".join(f"{k} {v['n']}" for k, v in vd.items())
               + (f"; right-but-unlucky losses hurt most by {', '.join(unlucky)}" if unlucky else "")
               + " (results are noise at this sample; CLV decides)")
    return out


def query(a):
    log = []
    for path in sorted(LOG.glob("*.jsonl")):
        log += [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    hits = []
    for e in log:
        if not e.get("counted") or not isinstance(e.get("clvProb"), (int, float)):
            continue
        if a.sport and e.get("sport") != a.sport.upper():
            continue
        if a.market and e.get("market") != a.market:
            continue
        if a.pattern and e.get("pattern") != a.pattern:
            continue
        if a.since and (e.get("date") or "") < a.since:
            continue
        au = e.get("autopsy") or {}
        if a.cause and (au.get("market") or {}).get("cause") != a.cause:
            continue
        if a.verdict and (au.get("game") or {}).get("verdict") != a.verdict:
            continue
        if a.tag and not any(t == a.tag or t.startswith(a.tag + ":") for t in (au.get("game") or {}).get("tags") or []):
            continue
        toks = set(tokens(e.get("features") or {}))
        if all(f in toks for f in a.feature or []):
            hits.append(e)
    vals = [e["clvProb"] for e in hits]
    res = [e for e in hits if e.get("result") in ("win", "loss", "push")]
    out = {"filters": {k: v for k, v in vars(a).items() if v and k != "cmd"}, **stats(vals),
           "record": "{}-{}-{}".format(*(sum(1 for e in res if e["result"] == r) for r in ("win", "loss", "push"))),
           "examples": [f"{e['date']} {e['event']} {e['market']} {e['side']} {e['lineAtPick']} "
                        f"CLV {e['clvProb'] * 100:+.1f}%" for e in hits[-5:]]}
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(description="EDGE living memory")
    sub = ap.add_subparsers(dest="cmd")
    q = sub.add_parser("query")
    q.add_argument("--sport")
    q.add_argument("--market", choices=["spread", "total", "h2h"])
    q.add_argument("--pattern")
    q.add_argument("--feature", action="append", help="key=value, repeatable: timing=early, injury=qb, wind=15+")
    q.add_argument("--since", help="YYYY-MM-DD")
    q.add_argument("--cause", help="autopsy cause (post-pick explanation): news-after-pick, sharps-against-at-pick, ...")
    q.add_argument("--verdict", help="autopsy verdict: right-but-unlucky, lucky-win, market-was-right, ...")
    q.add_argument("--tag", help="autopsy variance tag, e.g. overtime or overtime:hurt")
    a = ap.parse_args()
    if a.cmd == "query":
        query(a)
    else:
        print(json.dumps(build()))


if __name__ == "__main__":
    main()
