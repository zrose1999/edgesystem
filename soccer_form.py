#!/usr/bin/env python3
"""EDGE soccer form (v1). Current-season team form from Understat for the five leagues where the early-price
overreaction was measured, written to stats/soccer_form.json for edge_stack.py.

  python3 soccer_form.py

Per team: luck in the last match ((goals - xG) for minus against), points minus expected points over the last 5,
and total goals in the last match. Understat's forecast probabilities give expected points.

Why (12 seasons, 5 leagues, Pinnacle early to close, ~20,000 matches; stats/backtest_soccer_spots.md):
  home luck - away luck, per goal: home win prob drifts -0.10 pts (t -9.4)
  points minus expected points over 5, per point: that team drifts -0.09 (home, t -10) / -0.075 (away, t -9)
  sum of both teams' last-match goals, per goal: over 2.5 drifts +0.07 (t 5.9)
"""

import json
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "soccer_form.json"
LEAGUES = {"EPL": "EPL", "LaLiga": "La_liga", "Bundesliga": "Bundesliga", "SerieA": "Serie_A", "Ligue1": "Ligue_1"}


def understat(league, year):
    out = subprocess.run(["curl", "-s", "--compressed", "-m", "40", "-H", "X-Requested-With: XMLHttpRequest",
                          f"https://understat.com/getLeagueData/{league}/{year}"], capture_output=True).stdout
    return json.loads(out)


def norm(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def form(dates):
    hist = {}
    for g in sorted([g for g in dates if g.get("isResult")], key=lambda g: g["datetime"]):
        gh, ga = int(g["goals"]["h"]), int(g["goals"]["a"])
        xh, xa = float(g["xG"]["h"]), float(g["xG"]["a"])
        fc = g.get("forecast") or {}
        w, d, l = (float(fc.get(k, 1 / 3)) for k in ("w", "d", "l"))
        for t, gf, gaa, xgf, xga, xp in ((g["h"]["title"], gh, ga, xh, xa, 3 * w + d), (g["a"]["title"], ga, gh, xa, xh, 3 * l + d)):
            pts = 3 if gf > gaa else (1 if gf == gaa else 0)
            hist.setdefault(t, []).append({"gf": gf, "ga": gaa, "xgf": xgf, "xga": xga, "pts": pts, "xpts": xp,
                                           "date": g["datetime"]})
    out = {}
    for t, H in hist.items():
        last = H[-1]
        out[t] = {"n": len(H), "luck1": round((last["gf"] - last["xgf"]) - (last["ga"] - last["xga"]), 3),
                  "formgap5": round(sum(x["pts"] for x in H[-5:]) - sum(x["xpts"] for x in H[-5:]), 3) if len(H) >= 5 else None,
                  "tot1": last["gf"] + last["ga"], "last": last["date"]}
    return out


def main():
    now = datetime.now(timezone.utc)
    year = now.year if now.month >= 7 else now.year - 1
    res = {"asOf": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "leagues": {}}
    for ours, us in LEAGUES.items():
        try:
            cur = form(understat(us, year)["dates"])
        except Exception as exc:  # noqa: BLE001
            print("understat", us, exc)
            continue
        res["leagues"][ours] = cur
    OUT.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({"soccerForm": {k: len(v) for k, v in res["leagues"].items()}}))


if __name__ == "__main__":
    main()
