#!/usr/bin/env python3
"""EDGE MLB odds backfill (2026-10-21). ESPN keeps DraftKings open and close for the current season only (stats_more.py
saves it: 2026 is stored). Earlier seasons need Odds API historical snapshots. Per game day this takes an EARLY
snapshot (14:00 UTC, the morning number) and LATE snapshots (16:45, 22:45 and 01:45 UTC, so every first pitch has a
price taken within about three hours of it); each game's close is the last late snapshot before its start.

  python3 backfill_mlb.py --test            one snapshot: events found and the exact credit cost (about 20 credits)
  python3 backfill_mlb.py --plan 2025       days and snapshots a season needs and the credit estimate (no calls)
  python3 backfill_mlb.py 2025 [--early-only | --late=22:45]   every day of that season not already saved
      --late=22:45 keeps one late snapshot (night games' close, about two thirds of games) for half the credits

Needs ODDS_API_KEY (GitHub secret). Writes stats/history/mlb_odds/<season>.json. Stops early if credits fall under
MIN_LEFT, so the price runs never go short; rerun to continue where it stopped.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "history" / "mlb_odds"
BOOKS = "draftkings,fanduel,betmgm,williamhill_us,pinnacle"
MARKETS = "h2h,totals"
EARLY = "14:00"
LATE = ("16:45", "22:45", "01:45")          # 01:45 belongs to the next UTC day
SEASONS = {2025: ("2025-03-18", "2025-10-01"), 2024: ("2024-03-20", "2024-09-30"), 2023: ("2023-03-30", "2023-10-01")}
MIN_LEFT = int(os.environ.get("EDGE_BACKFILL_MIN_LEFT", "9000"))
COST_PER_SNAPSHOT = 20                       # 10 per market per region (2 markets, 1 region); --test measures it


def snapshot(key, when):
    q = urllib.parse.urlencode({"apiKey": key, "regions": "us", "markets": MARKETS, "oddsFormat": "american",
                                "bookmakers": BOOKS, "date": when})
    req = urllib.request.Request(f"https://api.the-odds-api.com/v4/historical/sports/baseball_mlb/odds?{q}")
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
                    elif m["key"] == "totals" and o["name"] == "Over":
                        rec["total"], rec["over_price"] = o.get("point"), o.get("price")
                    elif m["key"] == "totals":
                        rec["under_price"] = o.get("price")
            books[b["key"]] = rec
        events.append({"id": e.get("id"), "home": e["home_team"], "away": e["away_team"], "commence": e["commence_time"],
                       "books": books})
    return {"snapshot": body.get("timestamp"), "events": events}


def days(season):
    a, b = (date.fromisoformat(x) for x in SEASONS[season])
    while a <= b:
        yield a
        a += timedelta(days=1)


def times_for(day, early_only=False, late=LATE):
    out = [("early", f"{day}T{EARLY}:00Z")]
    if not early_only:
        for t in late:
            d = day + timedelta(days=1) if t < "06:00" else day
            out.append(("late", f"{d}T{t}:00Z"))
    return out


def main(args):
    early_only = "--early-only" in args
    late = next((tuple(a.split("=", 1)[1].split(",")) for a in args if a.startswith("--late=")), LATE)
    args = [a for a in args if a != "--early-only" and not a.startswith("--late=")]
    if args[:1] == ["--plan"]:
        for s in [int(a) for a in args[1:]] or [2025]:
            n = sum(len(times_for(d, early_only, late)) for d in days(s))
            print(json.dumps({"season": s, "days": sum(1 for _ in days(s)), "snapshots": n,
                              "creditsEstimate": n * COST_PER_SNAPSHOT, "earlyOnly": early_only, "late": late}))
        return
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        sys.exit("ODDS_API_KEY is not set")
    if args == ["--test"]:
        body, h = snapshot(key, "2025-07-15T22:45:00Z")
        c = compact(body)
        print(json.dumps({"test": "2025-07-15T22:45:00Z", "events": len(c["events"]), "credits": h,
                          "booksOnFirst": sorted((c["events"][0]["books"] if c["events"] else {}).keys()),
                          "sample": c["events"][:1]}, indent=1))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for season in [int(a) for a in args]:
        f = OUT / f"{season}.json"
        saved = json.loads(f.read_text()) if f.exists() else {"season": season, "snaps": {}}
        for d in days(season):
            for kind, when in times_for(d, early_only, late):
                if when in saved["snaps"]:
                    continue
                body, h = snapshot(key, when)
                saved["snaps"][when] = {"kind": kind, **compact(body)}
                f.write_text(json.dumps(saved, separators=(",", ":")))
                left = int(h.get("x-requests-remaining") or 0)
                print(season, when, kind, "events", len(saved["snaps"][when]["events"]), "cost", h.get("x-requests-last"),
                      "left", left)
                if left < MIN_LEFT:
                    print(f"Credits under {MIN_LEFT}; stopping. Rerun later to continue where this stopped.")
                    return


if __name__ == "__main__":
    main(sys.argv[1:])
