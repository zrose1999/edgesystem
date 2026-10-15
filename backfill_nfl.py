#!/usr/bin/env python3
"""EDGE NFL opening-line backfill. The free nflverse data has every past game's closing spread, total and moneyline;
what the desk lacks is the opening number. This takes ONE Odds API historical snapshot per week (Tuesday morning,
the early-week line for that week's games), so two seasons cost about 1,300 credits.

  python3 backfill_nfl.py --test          one snapshot (30 credits): prints events found and the credit cost
  python3 backfill_nfl.py 2024 2025       every week of those seasons not already saved

Needs ODDS_API_KEY (GitHub secret). Writes stats/history/nfl_open/<season>.json. Stops early if credits fall under
MIN_LEFT, so the price runs never go short.
"""

import csv
import io
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "history" / "nfl_open"
GAMES = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
BOOKS = "draftkings,fanduel,betmgm,williamhill_us,pinnacle"
MARKETS = "h2h,spreads,totals"
MIN_LEFT = int(os.environ.get("EDGE_BACKFILL_MIN_LEFT", "9000"))


def nflverse_games():
    out = subprocess.run(["curl", "-sL", "-m", "120", GAMES], capture_output=True).stdout.decode()
    return list(csv.DictReader(io.StringIO(out)))


def snapshot(key, when):
    q = urllib.parse.urlencode({"apiKey": key, "regions": "us", "markets": MARKETS, "oddsFormat": "american",
                                "bookmakers": BOOKS, "date": when})
    req = urllib.request.Request(f"https://api.the-odds-api.com/v4/historical/sports/americanfootball_nfl/odds?{q}")
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.loads(r.read().decode())
        return body, {k: r.headers.get(k) for k in ("x-requests-remaining", "x-requests-used", "x-requests-last")}


def compact(body):
    events = []
    for e in body.get("data") or []:
        books = {}
        for b in e.get("bookmakers") or []:
            rec = {}
            for m in b.get("markets") or []:
                for o in m.get("outcomes") or []:
                    if m["key"] == "h2h":
                        rec["ml_home" if o["name"] == e["home_team"] else "ml_away"] = o.get("price")
                    elif m["key"] == "spreads" and o["name"] == e["home_team"]:
                        rec["spread"], rec["spread_price"] = o.get("point"), o.get("price")
                    elif m["key"] == "spreads":
                        rec["spread_away_price"] = o.get("price")
                    elif m["key"] == "totals" and o["name"] == "Over":
                        rec["total"], rec["over_price"] = o.get("point"), o.get("price")
                    elif m["key"] == "totals":
                        rec["under_price"] = o.get("price")
            books[b["key"]] = rec
        events.append({"home": e["home_team"], "away": e["away_team"], "commence": e["commence_time"], "books": books})
    return {"snapshot": body.get("timestamp"), "events": events}


def week_snapshots(games, season):
    """Tuesday 14:00 UTC before each week's first game."""
    first = defaultdict(lambda: "9999")
    for g in games:
        if g["season"] == str(season) and g["gameday"]:
            first[(g["game_type"], int(g["week"]))] = min(first[(g["game_type"], int(g["week"]))], g["gameday"])
    out = []
    for (gt, wk), day in sorted(first.items(), key=lambda kv: kv[1]):
        d = datetime.fromisoformat(day)
        tue = d - timedelta(days=((d.weekday() - 1) % 7) or 7)
        out.append((f"{gt}-{wk}", tue.replace(hour=14, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    return out


def main(args):
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        sys.exit("ODDS_API_KEY is not set")
    games = nflverse_games()
    if args == ["--test"]:
        when = week_snapshots(games, 2025)[3][1]
        body, h = snapshot(key, when)
        c = compact(body)
        print(json.dumps({"test": when, "events": len(c["events"]), "credits": h,
                          "sample": c["events"][:1]}, indent=1))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for season in [int(a) for a in args]:
        f = OUT / f"{season}.json"
        saved = json.loads(f.read_text()) if f.exists() else {"season": season, "weeks": {}}
        for tag, when in week_snapshots(games, season):
            if tag in saved["weeks"]:
                continue
            body, h = snapshot(key, when)
            saved["weeks"][tag] = {"asked": when, **compact(body)}
            f.write_text(json.dumps(saved, separators=(",", ":")))
            left = int(h.get("x-requests-remaining") or 0)
            print(season, tag, when, "events", len(saved["weeks"][tag]["events"]), "cost", h.get("x-requests-last"), "left", left)
            if left < MIN_LEFT:
                print(f"Credits under {MIN_LEFT}; stopping. Rerun later to continue where this stopped.")
                return


if __name__ == "__main__":
    main(sys.argv[1:])
