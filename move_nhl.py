#!/usr/bin/env python3
"""EDGE NHL line-move reads (v1). The stats_more.py NHL ratings, used for where the price is going between the
open and the close (not where the game lands: against the close they add nothing). No analyst judgment.

  python3 move_nhl.py          stamp reads for games in the next WINDOW_H hours
  python3 move_nhl.py --dry    show what would be stamped

Why (stats_more.py walk-forward backtest, 2025-26, DraftKings open and close from ESPN):
  moneyline: close - open (home win prob) = 0.104 x (model - open), se 0.015, n 1,123; halves 0.12 and 0.06.
             With a 4+ point gap the price moved toward the model 59% of the time, away 29%.
  total:     close - open (over prob, same line) = 0.236 x (model - open), se 0.018, n 841; halves 0.28 and 0.16.
             With a 4+ point gap: toward 57%, away 27%.
Patterns nhl-ml-move and nhl-total-move. K values are set below the full-sample estimates (stability first).
Fair = current no-vig price + the part of the expected move not yet made since this desk's open.
"""

import json
import sys
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fair as fairlib
import pull

ROOT = Path(__file__).resolve().parent
MATCHUPS = ROOT / "stats" / "nhl_matchups.json"
K = {"h2h": 0.10, "total": 0.20}
PATTERN = {"h2h": "nhl-ml-move", "total": "nhl-total-move"}
MIN_MOVE = 0.02          # set by Zack 2026-10-14: a smaller expected move still reads, but only as a lean (graded, stackable, never a pick) (probability)
MIN_GAP = 0.04
WINDOW_H = 36


def novig(snap, keys):
    if not snap or any(k not in snap for k in keys):
        return None
    return fairlib.probs(snap, keys)[keys[0]]


def main(dry=False):
    games = json.loads(MATCHUPS.read_text()).get("games") or [] if MATCHUPS.exists() else []
    ledger = pull.load(pull.LEDGER, {"rows": []})
    rows = {r.get("id"): r for r in ledger.get("rows") or []}
    done = {(p.get("rowId"), p.get("pattern")) for p in pull.load(pull.PICKS, {"picks": []})["picks"]}
    now_dt = datetime.now(timezone.utc)
    now, horizon = pull.iso(now_dt), pull.iso(now_dt + timedelta(hours=WINDOW_H))
    todo = []
    for g in games:
        raw = g.get("raw") or {}
        for market in ("h2h", "total"):
            m = g.get(market) or {}
            row = rows.get(m.get("rowId"))
            if not row or (row.get("id"), PATTERN[market]) in done:
                continue
            if not row.get("commence") or not (now < row["commence"] <= horizon):
                continue
            o, c = row.get("openSnap"), row.get("lastSnap")
            if market == "h2h":
                model, keys = raw.get("pHome"), ["home", "away"]
            else:
                if not o or not c or o.get("line") is None or o.get("line") != c.get("line"):
                    continue          # the over probability only compares on the same line
                model, keys = m.get("modelOver"), ["over", "under"]
            p0, p1 = novig(o, keys), novig(c, keys)
            if model is None or p0 is None or p1 is None:
                continue
            gap = model - p0
            if abs(gap) < MIN_GAP:
                continue
            move = K[market] * gap
            moved = p1 - p0
            already = max(0.0, moved / move) * abs(move) if move else 0.0
            remaining = max(0.0, abs(move) - already)
            if remaining <= 0.002:
                continue
            fair = min(max(p1 + (remaining if move > 0 else -remaining), 0.02), 0.98)
            what = "home win" if market == "h2h" else f"over {o.get('line')}"
            reason = (f"NHL ratings {what} {model:.3f}, open {p0:.3f} (gap {gap:+.3f}). Prices moved {K[market]} x the "
                      f"gap from open to close in the backtest. Expected move {move:+.3f}, {remaining:.3f} still to come; "
                      f"now {p1:.3f}, fair {fair:.3f}.")
            if remaining < MIN_MOVE:
                pull.LEAN_CAP.add((row["id"], PATTERN[market]))
                reason += " (Under the pattern's minimum move: lean only.)"
            todo.append((row, fair, reason, PATTERN[market]))
    if dry:
        for row, fair, reason, pat in todo:
            print(f"WOULD READ {pat} {row['id']} | {reason}")
    else:
        if "NHL" not in pull.READ:
            pull.READ = pull.READ + ["NHL"]
        for row, fair, reason, pat in todo:
            args = Namespace(id=row["id"], fair=f"{fair:.3f}", confidence="medium", reason=reason,
                             falsifier="The price closes at or past the open on the other side of the model.",
                             pattern=pat, stake="0", big=True, by="move_nhl.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"patterns": list(PATTERN.values()), "sport": "NHL", "reads": len(todo), "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
