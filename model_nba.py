#!/usr/bin/env python3
"""EDGE NBA model reads (v1). Stamps two NBA patterns with no analyst judgment, so each is tested on its own.

  python3 model_nba.py      stamp NBA spreads and totals tipping within WINDOW_H hours

  nba-stats-model  The stats_more.py NBA ratings' own number, using WEIGHT of its gap from the market:
                   fair = market + WEIGHT x (raw - market). Spreads and totals.
  nba-model-fav    The same spread read, stamped only when the model's side is the market favourite.
                   This is the live test of the old Rose desk's best NBA bucket (spread favourites,
                   15-13 in the history file), which came from model picks restricted to favourites.

Both start in shadow and are graded on CLV like everything else. Early in a season the ratings lean on last
season (rosters change), so expect noise until a few weeks of games are in.
"""

import json
import os
import sys
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pull

ROOT = Path(__file__).resolve().parent
MATCHUPS = ROOT / "stats" / "nba_matchups.json"
WEIGHT = float(os.environ.get("EDGE_NBA_MODEL_WEIGHT", "0.25"))
WINDOW_H = 48


def stamp(row_id, fair, reason, pattern):
    args = Namespace(id=row_id, fair=str(round(fair, 2)), confidence="medium", reason=reason,
                     falsifier="The line moves away from the model side by the close.",
                     pattern=pattern, stake="0", big=True, by="model_nba")
    try:
        pull.make_read(args)
        return True
    except SystemExit as exc:
        print(json.dumps({"skipped": row_id, "pattern": pattern, "why": str(exc)}))
        return False


def main():
    if not MATCHUPS.exists():
        sys.exit("stats/nba_matchups.json is missing. Run python3 stats_more.py NBA first.")
    if "NBA" not in pull.READ:
        pull.READ = pull.READ + ["NBA"]       # scripted NBA reads only
    games = json.loads(MATCHUPS.read_text()).get("games") or []
    ledger = pull.load(pull.LEDGER, {"rows": []})
    rows = {r.get("id"): r for r in ledger.get("rows") or []}
    done = {(p.get("rowId"), p.get("pattern")) for p in pull.load(pull.PICKS, {"picks": []})["picks"]}
    now_dt = datetime.now(timezone.utc)
    now, horizon = pull.iso(now_dt), pull.iso(now_dt + timedelta(hours=WINDOW_H))
    out = {"nba-stats-model": 0, "nba-model-fav": 0, "already": 0, "skipped": 0}
    for g in games:
        raw = g.get("raw") or {}
        for market in ("spread", "total"):
            m = g.get(market) or {}
            row = rows.get(m.get("rowId"))
            if not row or not row.get("lastSnap") or not row.get("commence") or not (now < row["commence"] <= horizon):
                continue
            line = row["lastSnap"].get("line")
            if line is None or raw.get("margin") is None:
                continue
            home = g["event"].split(" at ")[-1]
            if market == "spread":
                mkt = -line
                fair = -(mkt + WEIGHT * (raw["margin"] - mkt))
                reason = (f"NBA ratings raw {home} by {raw['margin']:+.1f}, market {home} {line:+g}. "
                          f"Fair = market + {WEIGHT} x gap = {home} {fair:+.1f}.")
            else:
                fair = line + WEIGHT * (raw["total"] - line)
                reason = f"NBA ratings raw total {raw['total']:.1f}, market {line:g}. Fair = market + {WEIGHT} x gap = {fair:.1f}."
            patterns = ["nba-stats-model"]
            if market == "spread":
                model_side = "home" if fair < line else "away"
                favourite = "home" if line < 0 else "away" if line > 0 else None
                if favourite and model_side == favourite and abs(fair - line) >= 0.05:
                    patterns.append("nba-model-fav")
            for pattern in patterns:
                if (row["id"], pattern) in done:
                    out["already"] += 1
                    continue
                ok = stamp(row["id"], fair, reason, pattern)
                out[pattern if ok else "skipped"] += 1
    print(json.dumps(out))


if __name__ == "__main__":
    main()
