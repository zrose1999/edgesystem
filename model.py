#!/usr/bin/env python3
"""EDGE data models. Stamps reads with no analyst judgment, so each idea is tested on its own.

  python3 model.py         stamp every upcoming NFL spread and total the models have a number for

Two patterns, each graded against the closing line like any other read:

  stats-model   The stats.py efficiency model's own number. fair = market + WEIGHT x (raw - market).
                The raw model is noisy (it misses by more than the market does), so only part of its
                gap is used. The backtest says the market usually wins these. This tests it live.

  trend-fade    Totals only. When both teams have gone over in most games this season, lean under,
                and the reverse. 2010 to 2025 at the closing line: fading strong trends hit 54.6%
                (321-267); following them hit 45.4%. The over/under records come from nflverse.

One read per game, market and pattern. Reads are stamped through pull.py read, so the price is the
stored DraftKings price and the grade comes from the edge against the bar. The model never types a price.
"""

import csv
import io
import json
import os
import sys
import urllib.request
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import pull  # noqa: E402

MATCHUPS = ROOT / "stats" / "nfl_matchups.json"
RESULTS_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
WEIGHT = float(os.environ.get("EDGE_MODEL_WEIGHT", "0.25"))
TREND_MIN_GAMES = 3
TREND_HIGH = 0.65
SEASON = int(os.environ.get("EDGE_SEASON", "2026"))


def stamp(row_id, fair, reason, falsifier, pattern):
    args = Namespace(id=row_id, fair=str(round(fair, 2)), confidence="medium", reason=reason,
                     falsifier=falsifier, pattern=pattern, stake="0", big=True, by="model")
    try:
        pull.make_read(args)
        return True
    except SystemExit as exc:
        print(json.dumps({"skipped": row_id, "pattern": pattern, "why": str(exc)}))
        return False


def trend_records():
    """Each team's over/under record this season, from completed games at the closing total."""
    try:
        with urllib.request.urlopen(RESULTS_URL, timeout=120) as resp:
            text = resp.read().decode()
    except Exception as exc:
        print(json.dumps({"trendFade": "results download failed", "why": str(exc)}))
        return None
    rec = {}
    for g in csv.DictReader(io.StringIO(text)):
        if g.get("season") != str(SEASON) or g.get("game_type") != "REG":
            continue
        if not g.get("home_score") or not g.get("total_line"):
            continue
        diff = float(g["home_score"]) + float(g["away_score"]) - float(g["total_line"])
        if diff == 0:
            continue
        for team in (g["home_team"], g["away_team"]):
            over, n = rec.get(team, (0, 0))
            rec[team] = (over + (diff > 0), n + 1)
    return rec


def main():
    if not MATCHUPS.exists():
        sys.exit("stats/nfl_matchups.json is missing. Run python3 stats.py first.")
    games = json.loads(MATCHUPS.read_text()).get("games") or []
    ledger = pull.load(pull.LEDGER, {"rows": []})
    rows = {r.get("id"): r for r in ledger.get("rows") or []}
    done = {(p.get("rowId"), p.get("pattern")) for p in pull.load(pull.PICKS, {"picks": []})["picks"]}
    now = pull.iso(datetime.now(timezone.utc))
    trends = trend_records()
    out = {"statsModel": 0, "trendFade": 0, "already": 0, "skipped": 0}

    for g in games:
        for market in ("spread", "total"):
            m = g.get(market) or {}
            row = rows.get(m.get("rowId"))
            if not row or not row.get("lastSnap") or not row.get("commence") or row["commence"] <= now:
                continue
            line = row["lastSnap"].get("line")
            if line is None:
                continue

            # stats-model
            if (row["id"], "stats-model") in done:
                out["already"] += 1
            else:
                if market == "spread":
                    mkt_margin = -line
                    raw = g["rawHomeMargin"]
                    fair = -(mkt_margin + WEIGHT * (raw - mkt_margin))
                    reason = (f"Stats model raw {g['home']} by {raw:+.1f}, market {g['home']} {line:+g}. "
                              f"Fair = market + {WEIGHT} x gap = {g['home']} {fair:+.1f}.")
                else:
                    raw = g["rawTotal"]
                    fair = line + WEIGHT * (raw - line)
                    reason = f"Stats model raw total {raw:.1f}, market {line:g}. Fair = market + {WEIGHT} x gap = {fair:.1f}."
                ok = stamp(row["id"], fair, reason, "The line moves away from the model side by the close.", "stats-model")
                out["statsModel" if ok else "skipped"] += 1

            # trend-fade, totals only
            if market != "total" or not trends:
                continue
            if (row["id"], "trend-fade") in done:
                out["already"] += 1
                continue
            h, a = trends.get(g.get("home")), trends.get(g.get("away"))
            if not h or not a or h[1] < TREND_MIN_GAMES or a[1] < TREND_MIN_GAMES:
                continue
            rate = (h[0] / h[1] + a[0] / a[1]) / 2
            strength = abs(rate - 0.5)
            if strength < TREND_HIGH - 0.5:
                continue
            size = min(2.5, 1.0 + (strength - (TREND_HIGH - 0.5)) * 10)
            fair = line - size if rate > 0.5 else line + size
            way = "under" if rate > 0.5 else "over"
            reason = (f"{g['home']} {h[0]}-{h[1] - h[0]} and {g['away']} {a[0]}-{a[1] - a[0]} to the over this season, "
                      f"{rate:.0%} combined. Fade to the {way}: market {line:g}, fair {fair:.1f}.")
            ok = stamp(row["id"], fair, reason, "Both teams keep the trend going and the total closes further the trend's way.", "trend-fade")
            out["trendFade" if ok else "skipped"] += 1

    print(json.dumps(out))


if __name__ == "__main__":
    main()
