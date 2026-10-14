#!/usr/bin/env python3
"""EDGE college football line back-fill from CollegeFootballData (CFBD).

  python3 cfbd.py           fill closing (and opening, when given) lines on stored NCAAF games that have none
  python3 cfbd.py --dry     show what would be filled, write nothing

Why: ESPN keeps NCAAF lines for about the last ten months, so stats_more.py has no lines for the
older part of its 430-day window. Without lines the NCAAF model cannot learn how much of its gap
from the market to trust (k). CFBD has lines back to 2013.

Key: CFBD_API_KEY (free tier: 1,000 calls a month; this uses two calls per season). With no key it
exits without doing anything. The key is never written to a file.
Only games with no lines, or with no closing spread, are touched. ESPN lines always win.
Provider order: DraftKings, then consensus, then the first provider listed. Spreads are the
home line (negative = home favoured), the same sign ESPN uses.
"""

import difflib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "stats" / "ncaaf_games.json"
API = "https://api.collegefootballdata.com/lines?year={year}&seasonType={stype}"
PROVIDERS = ("draftkings", "consensus")


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower().replace("&", "and"))


def get(url, key):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}", "Accept": "application/json",
                                               "User-Agent": "EDGE desk"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def pick(lines):
    by = {norm(l.get("provider")): l for l in lines or []}
    for p in PROVIDERS:
        if p in by and by[p].get("spread") is not None:
            return by[p]
    return next((l for l in lines or [] if l.get("spread") is not None), None)


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def field(d, *names):
    for n in names:
        if n in d:
            return d[n]
    return None


def same_team(espn_name, cfbd_name):
    """ESPN uses 'Ohio State Buckeyes', CFBD uses 'Ohio State'."""
    a, b = norm(espn_name), norm(cfbd_name)
    return bool(b) and (a.startswith(b) or difflib.SequenceMatcher(None, a[:len(b) + 4], b).ratio() >= 0.85)


def main(dry=False):
    key = os.environ.get("CFBD_API_KEY", "").strip()
    if not key:
        print(json.dumps({"cfbd": "skipped", "why": "CFBD_API_KEY is not set"}))
        return
    store = json.loads(STORE.read_text())
    games = store["games"]
    need = [g for g in games.values() if g.get("final") and not ((g.get("lines") or {}).get("spreadClose") is not None)]
    if not need:
        print(json.dumps({"cfbd": "nothing to fill"}))
        return
    seasons = sorted({int(g["date"][:4]) - (1 if int(g["date"][5:7]) < 7 else 0) for g in need})
    cfbd, calls = [], 0
    for year in seasons:
        for stype in ("regular", "postseason"):
            try:
                cfbd += get(API.format(year=year, stype=stype), key)
                calls += 1
            except Exception as exc:  # noqa: BLE001
                print("cfbd", year, stype, exc)
    by_day = {}
    for c in cfbd:
        start = field(c, "startDate", "start_date") or ""
        by_day.setdefault(start[:10], []).append(c)
    filled = 0
    for g in need:
        cands = by_day.get(g["date"][:10], [])
        if not cands:   # late kickoffs are the next day in UTC
            d = datetime.fromisoformat(g["date"].replace("Z", "+00:00")).astimezone(timezone.utc)
            cands = [c for day, cs in by_day.items() for c in cs if abs((datetime.fromisoformat(day) - d.replace(tzinfo=None)).days) <= 1]
        hit = next((c for c in cands if same_team(g["home"], field(c, "homeTeam", "home_team"))
                    and same_team(g["away"], field(c, "awayTeam", "away_team"))), None)
        if not hit:
            continue
        line = pick(field(hit, "lines") or [])
        if not line:
            continue
        lines = {
            "spreadClose": f(line.get("spread")), "spreadOpen": f(field(line, "spreadOpen", "spread_open")),
            "totalClose": f(field(line, "overUnder", "over_under")), "totalOpen": f(field(line, "overUnderOpen", "over_under_open")),
            "source": f"CFBD {line.get('provider')}",
        }
        if lines["spreadClose"] is None:
            continue
        if not dry:
            g["lines"] = {**(g.get("lines") or {}), **{k: v for k, v in lines.items() if v is not None}}
        filled += 1
    if not dry and filled:
        STORE.write_text(json.dumps(store, separators=(",", ":")) + "\n")
    print(json.dumps({"cfbd": "done", "seasons": seasons, "calls": calls, "needed": len(need),
                      "filled": filled, "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
