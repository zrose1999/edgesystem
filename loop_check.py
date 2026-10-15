#!/usr/bin/env python3
"""EDGE loop check. One status line per sport for every stage of the loop, written to stats/loop_status.json
(the site's Strategies tab shows it; notify.py pushes an alert when a sport goes stale):

  prices    upcoming games with a fresh price, and how many carry Pinnacle (the fair-price reference)
  results   games that started 6+ hours ago and have a final score
  closes    picks and leans whose game started that have a closing price (CLV needs it)
  picks     picks and leans stamped in the last 7 days, by strategy
  graded    picks and leans graded on CLV, all time
  history   games kept for research (live ledger + archive)

Status: ok, quiet (nothing scheduled), or a named problem (no prices, stale prices, missing results, missing closes).
"""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pull

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "loop_status.json"
ARCH = ROOT / "ledger" / "archive"
SPORTS = ["NFL", "NCAAF", "NBA", "NHL", "EPL", "UCL", "UEL", "LaLiga", "SerieA", "Bundesliga", "Ligue1", "MLS",
          "ATP", "WTA"]
STRATEGIES = {
    "NFL": ["news-lag", "wind-total", "stats-model", "trend-fade", "sharp-soft", "sharp-soft-alt", "edge-stack"],
    "NCAAF": ["ncaaf-total-move", "ncaaf-spot", "wind-total", "sharp-soft", "sharp-soft-alt", "sharp-drift", "edge-stack"],
    "NBA": ["news-lag", "rest-spot", "nba-stats-model", "nba-model-fav", "sharp-soft", "sharp-soft-alt", "edge-stack"],
    "NHL": ["goalie-news", "nhl-ml-move", "nhl-total-move", "sharp-soft", "sharp-drift", "edge-stack"],
    "ATP": ["tennis-elo", "tennis-fatigue", "sharp-soft", "edge-stack"],
    "WTA": ["tennis-elo", "tennis-fatigue", "sharp-soft", "edge-stack"],
    **{lg: ["sharp-drift (form, luck, draw and under drift)", "sharp-soft", "kalshi-drift"]
       for lg in ("EPL", "LaLiga", "SerieA", "Bundesliga", "Ligue1")},
    **{lg: ["sharp-soft", "kalshi-sharp"] for lg in ("UCL", "UEL", "MLS")},
}
SOURCES = {
    "NFL": ["stats/injuries.json", "stats/nfl_depth.json", "stats/nfl_matchups.json"],
    "NCAAF": ["stats/ncaaf_matchups.json", "stats/ncaaf_games.json"],
    "NBA": ["stats/injuries_nba.json", "stats/nba_player_values.json", "stats/nba_matchups.json"],
    "NHL": ["stats/nhl_goalies.json", "stats/nhl_games.json"],
    "EPL": ["stats/epl_games.json", "stats/soccer_form.json"],
    "LaLiga": ["stats/soccer_form.json"], "SerieA": ["stats/soccer_form.json"], "Bundesliga": ["stats/soccer_form.json"],
    "Ligue1": ["stats/soccer_form.json"], "ATP": ["stats/tennis_matches.json"], "WTA": ["stats/tennis_matches.json"],
}


def as_of(path):
    p = ROOT / path
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None
    return d.get("asOf") if isinstance(d, dict) else None


def archived_counts():
    n = Counter()
    if ARCH.exists():
        for f in ARCH.glob("*/*.jsonl"):
            n[f.stem] += sum(1 for line in f.read_text().splitlines() if line.strip())
    return n


def main():
    now = datetime.now(timezone.utc)
    iso = pull.iso
    ledger = pull.load(pull.LEDGER, {"rows": []})
    rows = ledger.get("rows") or []
    picks = pull.load(pull.PICKS, {"picks": []}).get("picks") or []
    arch = archived_counts()
    by = defaultdict(list)
    for r in rows:
        by[r.get("sport")].append(r)
    out = {}
    week = iso(now - timedelta(days=7))
    for sport in SPORTS:
        rs = by.get(sport, [])
        up = [r for r in rs if r.get("commence", "") > iso(now)]
        soon = [r for r in up if r["commence"] <= iso(now + timedelta(hours=48))]
        snaps = [r["lastSnap"]["time"] for r in up if r.get("lastSnap")]
        last_price = max(snaps) if snaps else None
        pin = sum(1 for r in up if "pinnacle" in ((r.get("lastSnap") or {}).get("books") or {}))
        started = [r for r in rs if iso(now - timedelta(days=3)) <= r.get("commence", "") <= iso(now - timedelta(hours=6))]
        finals = sum(1 for r in started if r.get("final"))
        sp = [p for p in picks if p.get("sport") == sport and p.get("kind") in ("pick", "lean")]
        row_by_id = {r.get("id"): r for r in rs}
        need_close = [p for p in sp if p.get("commence", "") <= iso(now - timedelta(hours=2))
                      and p.get("commence", "") >= iso(now - timedelta(days=6)) and p.get("rowId") in row_by_id]
        closed = sum(1 for p in need_close if "closeSnap" in row_by_id[p["rowId"]])
        recent = Counter(p.get("pattern") or "analyst" for p in sp if p.get("pickedAt", "") >= week)
        graded = sum(1 for p in sp if "clvProb" in p)
        problems = []
        if soon and not snaps:
            problems.append("no prices")
        elif soon and last_price and last_price < iso(now - timedelta(hours=6)):
            problems.append(f"prices stale since {last_price}")
        if len(started) >= 3 and finals == 0:
            problems.append("no results")
        if len(need_close) >= 2 and closed == 0:
            problems.append("no closes")
        out[sport] = {
            "status": "ok" if (up and not problems) else ("quiet" if not up and not problems else "; ".join(problems)),
            "upcoming": len(up), "next48h": len(soon), "lastPrice": last_price, "withPinnacle": pin,
            "started3d": len(started), "finals3d": finals,
            "picksNeedingClose": len(need_close), "closed": closed,
            "picks7d": dict(recent), "graded": graded,
            "history": len(rs) + arch.get(sport, 0),
            "strategies": STRATEGIES.get(sport, ["sharp-soft", "kalshi-sharp"]),
            "sources": {s: as_of(s) for s in SOURCES.get(sport, [])},
        }
    cs2 = pull.load(ROOT / "stats" / "cs2_ratings.json", {})
    cs2h = pull.load(ROOT / "stats" / "cs2_matches.json", {})
    out["CS2"] = {"status": ("loading history" if cs2.get("backfillPending") else ("ok" if cs2.get("upcoming") else "quiet"))
                  if cs2 else "no data", "upcoming": len(cs2.get("upcoming") or []), "lastPrice": cs2.get("asOf"),
                  "history": len(cs2h.get("matches") or []), "strategies": ["cs2-elo"], "teams": cs2.get("teams")}
    OUT.write_text(json.dumps({"asOf": iso(now), "sports": out}, indent=1))
    bad = {s: v["status"] for s, v in out.items() if v["status"] not in ("ok", "quiet", "loading history")}
    print(json.dumps({"loop": "checked", "problems": bad}))


if __name__ == "__main__":
    main()
