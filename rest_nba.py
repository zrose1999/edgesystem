#!/usr/bin/env python3
"""EDGE NBA rest spots (v1). Stamps the rest-spot pattern on NBA spreads where one team is on the second night
of a back-to-back and the other has had at least a day off. No analyst judgment.

  python3 rest_nba.py              stamp reads for games in the next WINDOW_H hours
  python3 rest_nba.py --dry        show what would be stamped, write nothing
  python3 rest_nba.py --backtest   rebuild stats/backtest_nba_rest.{json,md} from stats/nba_games.json

Why (backtest on 2025-26, DraftKings open and close from ESPN, 979 regular-season games):
  Away team on a back-to-back, home team rested 2+ days: the home line moved 0.93 points toward the home team
  from open to close (se 0.19, n 123), and did so in both halves of the season (-0.83, -0.97).
  Home team on a back-to-back, away team rested: the line moved 0.50 toward the away team (se 0.18, n 111;
  halves +0.33, +0.58). Against the close, neither spot beat the spread (the close prices rest), so the edge is
  getting the number before it moves: a closing-line pattern, which is what EDGE grades.

The read: fair home line = the current line + whatever part of the average move (MOVE below) has not happened
since this desk's open. A line that already moved toward the rested team earns less or nothing; drift the other
way is left alone (it is other news), so the edge is never more than the move itself. Rest days come from the ESPN schedule in
stats/nba_games.json plus the ledger; a day is the US date (UTC minus 6 hours).
"""

import json
import sys
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pull

ROOT = Path(__file__).resolve().parent
GAMES = ROOT / "stats" / "nba_games.json"
OUT = ROOT / "stats" / "backtest_nba_rest"
PATTERN = "rest-spot"
WINDOW_H = 36
# Average open-to-close move of the HOME line, rounded from the backtest. Negative: toward the home team.
MIN_MOVE = 0.75          # set by Zack 2026-10-14: a smaller expected move still reads, but only as a lean (graded, stackable, never a pick) (points)
MOVE = {"away-b2b": -0.9, "home-b2b": +0.5}


def us_day(ts):
    return (datetime.fromisoformat(ts.replace("Z", "+00:00")) - timedelta(hours=6)).date()


def schedule(games, ledger_rows):
    """Every NBA game date per team, from the ESPN file and the ledger."""
    days = {}
    for g in games:
        if g.get("seasonType") not in (2, 3, None):
            continue
        for team in (g.get("home"), g.get("away")):
            days.setdefault(team, set()).add(us_day(g["date"]))
    for r in ledger_rows:
        if r.get("sport") == "NBA" and r.get("commence"):
            for team in (r.get("home"), r.get("away")):
                days.setdefault(team, set()).add(us_day(r["commence"]))
    return days


def rest(days, team, day):
    before = [d for d in days.get(norm_team(days, team), ()) if d < day]
    return (day - max(before)).days if before else None


def norm_team(days, team):
    if team in days:
        return team
    m = (team or "").split()[-1].lower()
    for t in days:
        if t.split()[-1].lower() == m:
            return t
    return team


def spot(rh, ra):
    if rh is None or ra is None:
        return None
    if ra == 1 and rh >= 2:
        return "away-b2b"
    if rh == 1 and ra >= 2:
        return "home-b2b"
    return None


def load_games():
    d = pull.load(GAMES, {})
    g = d.get("games") or {}
    return list(g.values()) if isinstance(g, dict) else g


def main(dry=False):
    games = load_games()
    ledger = pull.load(pull.LEDGER, {"rows": []})
    rows = ledger.get("rows") or []
    days = schedule(games, rows)
    now_dt = datetime.now(timezone.utc)
    now, horizon = pull.iso(now_dt), pull.iso(now_dt + timedelta(hours=WINDOW_H))
    done = {p.get("rowId") for p in pull.load(pull.PICKS, {"picks": []})["picks"] if p.get("pattern") == PATTERN}
    todo = []
    for row in rows:
        if row.get("sport") != "NBA" or row.get("market") != "spread" or row.get("id") in done:
            continue
        if not row.get("commence") or not (now < row["commence"] <= horizon):
            continue
        open_line = row.get("openLine")
        if not isinstance(open_line, (int, float)):
            continue
        day = us_day(row["commence"])
        rh, ra = rest(days, row["home"], day), rest(days, row["away"], day)
        kind = spot(rh, ra)
        if not kind:
            continue
        cur = (row.get("lastSnap") or {}).get("line")
        if not isinstance(cur, (int, float)):
            continue
        # Only the part of the usual move still to come counts. A line that drifted the other way since the
        # open keeps that drift (it is other news), so the read never turns drift into edge.
        step = MOVE[kind]
        done_already = max(0.0, (cur - open_line) / step) * abs(step) if step else 0.0
        remaining = max(0.0, abs(step) - done_already)
        if remaining <= 0:
            continue
        fair = cur + (remaining if step > 0 else -remaining)
        tired = row["away"] if kind == "away-b2b" else row["home"]
        rested = row["home"] if kind == "away-b2b" else row["away"]
        reason = (f"{tired} on the second night of a back-to-back, {rested} rested {rh if kind == 'away-b2b' else ra} days. "
                  f"Lines in this spot moved {abs(MOVE[kind]):g} toward the rested team from open to close in 2025-26. "
                  f"Open home line {open_line:+g}, now {cur:+g}, {remaining:.2f} of the move still to come, fair {fair:+.2f}.")
        if remaining < MIN_MOVE:
            pull.LEAN_CAP.add((row["id"], PATTERN))
            reason += " (Under the pattern's minimum move: lean only.)"
        todo.append((row, fair, reason))
    if dry:
        for row, fair, reason in todo:
            print(f"WOULD READ {row['id']} now {(row.get('lastSnap') or {}).get('line')} | {reason}")
    else:
        if "NBA" not in pull.READ:
            pull.READ = pull.READ + ["NBA"]     # scripted NBA reads only
        for row, fair, reason in todo:
            args = Namespace(id=row["id"], fair=f"{fair:.2f}", confidence="medium", reason=reason,
                             falsifier="The line closes at or past the open on the tired team's side.",
                             pattern=PATTERN, stake="0", big=True, by="rest_nba.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"pattern": PATTERN, "sport": "NBA", "spots": len(todo), "dry": dry}))


def backtest():
    import statistics as st
    games = sorted((g for g in load_games() if g.get("seasonType") == 2), key=lambda g: g["date"])
    days = schedule(games, [])
    groups = {"away-b2b": [], "home-b2b": [], "both-b2b": [], "other": []}
    for g in games:
        L = g.get("lines") or {}
        if not g.get("final") or L.get("spreadOpen") is None or L.get("spreadClose") is None:
            continue
        day = us_day(g["date"])
        rh, ra = rest(days, g["home"], day), rest(days, g["away"], day)
        k = spot(rh, ra) or ("both-b2b" if rh == 1 and ra == 1 else "other")
        groups[k].append({"move": L["spreadClose"] - L["spreadOpen"], "ats": g["hs"] - g["as"] + L["spreadClose"],
                          "date": g["date"]})
    out = {}
    for k, xs in groups.items():
        n = len(xs)
        if n < 2:
            continue
        mv, ats = [x["move"] for x in xs], [x["ats"] for x in xs]
        out[k] = {"n": n, "meanMove": round(st.mean(mv), 2), "seMove": round(st.stdev(mv) / n ** 0.5, 2),
                  "homeAtsVsClose": round(st.mean(ats), 2), "seAts": round(st.stdev(ats) / n ** 0.5, 2)}
    OUT.with_suffix(".json").write_text(json.dumps({"asOf": pull.iso(datetime.now(timezone.utc)), "groups": out}, indent=1))
    lines = ["# NBA rest spots (rest_nba.py --backtest)", "",
             "Home spread line, DraftKings open to close (ESPN). Move below 0: toward the home team.", "",
             "| Spot | Games | Mean move | se | Home ATS vs close | se |", "|---|---|---|---|---|---|"]
    lines += [f"| {k} | {v['n']} | {v['meanMove']:+.2f} | {v['seMove']} | {v['homeAtsVsClose']:+.2f} | {v['seAts']} |" for k, v in out.items()]
    OUT.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if "--backtest" in sys.argv[1:]:
        backtest()
    else:
        main(dry="--dry" in sys.argv[1:])
