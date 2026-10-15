#!/usr/bin/env python3
"""EDGE college football totals move (v1). Stamps the ncaaf-total-move pattern: the stats_more.py NCAAF ratings'
total, used only for where the line is likely to go between the open and the close. No analyst judgment.

  python3 model_ncaaf.py          stamp reads for games in the next WINDOW_D days
  python3 model_ncaaf.py --dry    show what would be stamped, write nothing

Why (stats_more.py walk-forward backtest, 540 games, Nov 2025 to Oct 2026, DraftKings open and close from ESPN):
  close - open = 0.18 x (model total - open total), se 0.029. Both halves of the sample agree (0.13, 0.24).
  When the model is 4+ points from the open, the total moved toward it 1.3 points on average and did so in about
  60% of games. Against the close the model has nothing (kTotal 0), so this is a closing-line pattern only.

The read: expected move = K_MOVE x (model - open). Only the part not yet made since this desk's open counts:
fair = current total + remaining move. A total that already moved the other way keeps that drift (other news).
K_MOVE is fixed here; the weekly review can propose a new value from stats/ncaaf_calibration.json.
"""

import json
import sys
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pull

ROOT = Path(__file__).resolve().parent
MATCHUPS = ROOT / "stats" / "ncaaf_matchups.json"
CAL = ROOT / "stats" / "ncaaf_calibration.json"
PATTERN = "ncaaf-total-move"
K_MOVE = 0.18
MIN_GAMES = 8
MIN_GAP = 4.0             # under this the expected move is under 0.75 points: noise
WINDOW_D = 7


def main(dry=False):
    if not MATCHUPS.exists():
        sys.exit("stats/ncaaf_matchups.json is missing. Run python3 stats_more.py NCAAF first.")
    games = json.loads(MATCHUPS.read_text()).get("games") or []
    teams = (pull.load(ROOT / "stats" / "ncaaf_teams.json", {}).get("teams") or {})
    cal = (pull.load(CAL, {}).get("moveTotal") or {})
    ledger = pull.load(pull.LEDGER, {"rows": []})
    rows = {r.get("id"): r for r in ledger.get("rows") or []}
    done = {p.get("rowId") for p in pull.load(pull.PICKS, {"picks": []})["picks"] if p.get("pattern") == PATTERN}
    now_dt = datetime.now(timezone.utc)
    now, horizon = pull.iso(now_dt), pull.iso(now_dt + timedelta(days=WINDOW_D))
    todo = []
    for g in games:
        raw = (g.get("raw") or {}).get("total")
        away_t, home_t = g["event"].split(" at ", 1) if " at " in g["event"] else (None, None)
        if min((teams.get(away_t) or {}).get("games", 0), (teams.get(home_t) or {}).get("games", 0)) < MIN_GAMES:
            continue                       # thinly rated teams (mostly FCS) give unreliable totals
        row = rows.get((g.get("total") or {}).get("rowId"))
        if raw is None or not row or row.get("id") in done:
            continue
        if not row.get("commence") or not (now < row["commence"] <= horizon):
            continue
        open_line, cur = row.get("openLine"), (row.get("lastSnap") or {}).get("line")
        if not isinstance(open_line, (int, float)) or not isinstance(cur, (int, float)):
            continue
        gap = raw - open_line
        if abs(gap) < MIN_GAP:
            continue
        move = K_MOVE * gap
        moved = cur - open_line
        already = max(0.0, moved / move) * abs(move) if move else 0.0     # part of the move already made
        remaining = max(0.0, abs(move) - already)
        if remaining <= 0:
            continue
        fair = cur + (remaining if move > 0 else -remaining)
        reason = (f"NCAAF ratings total {raw:.1f}, open {open_line:g} (gap {gap:+.1f}). Lines moved {K_MOVE} x the gap "
                  f"from open to close in the backtest (current calibration {cal.get('kMove')}, se {cal.get('se')}, "
                  f"n {cal.get('n')}). Expected move {move:+.2f}, {remaining:.2f} still to come; now {cur:g}, fair {fair:.2f}.")
        todo.append((row, fair, reason))
    if dry:
        for row, fair, reason in todo:
            print(f"WOULD READ {row['id']} | {reason}")
    else:
        if "NCAAF" not in pull.READ:
            pull.READ = pull.READ + ["NCAAF"]       # scripted reads only
        for row, fair, reason in todo:
            args = Namespace(id=row["id"], fair=f"{fair:.2f}", confidence="medium", reason=reason,
                             falsifier="The total closes at or past the open on the other side of the model.",
                             pattern=PATTERN, stake="0", big=True, by="model_ncaaf.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"pattern": PATTERN, "sport": "NCAAF", "reads": len(todo), "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
