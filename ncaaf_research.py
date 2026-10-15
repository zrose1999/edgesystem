#!/usr/bin/env python3
"""EDGE college football research: which situations predict the move from the opening line to the close?
Runs on GitHub (needs CFBD_API_KEY). Writes stats/backtest_ncaaf_spots.md and .json.

Data: CollegeFootballData /lines (opening and closing spread and total per provider) and /games (dates, neutral
site, conference), FBS regular seasons 2016-2025 (2020 skipped). One provider per game: DraftKings, then ESPN Bet,
Bovada, consensus. ~22 API calls.
"""

import json
import os
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "backtest_ncaaf_spots"
API = "https://api.collegefootballdata.com"
YEARS = [y for y in range(2016, 2026) if y != 2020]
PREF = ["DraftKings", "ESPN Bet", "Bovada", "consensus", "William Hill (New Jersey)", "teamrankings", "numberfire"]


def get(path):
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {os.environ['CFBD_API_KEY']}",
                                                      "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def pick_line(lines):
    by = {l.get("provider"): l for l in lines or []}
    for p in PREF + list(by):
        l = by.get(p)
        if l and l.get("spread") is not None and l.get("spreadOpen") is not None:
            return l
    return None


def main():
    rows = []
    for y in YEARS:
        games = {g["id"]: g for g in get(f"/games?year={y}&seasonType=regular&classification=fbs")}
        lines = get(f"/lines?year={y}&seasonType=regular")
        last = {}
        for g in sorted(games.values(), key=lambda g: g.get("startDate") or ""):
            d = datetime.fromisoformat((g.get("startDate") or "").replace("Z", "+00:00")).date() if g.get("startDate") else None
            g["_rest"] = {}
            for side in ("homeTeam", "awayTeam"):
                t = g.get(side)
                g["_rest"][side] = (d - last[t]).days if d and t in last else None
                if d:
                    last[t] = d
        for L in lines:
            g = games.get(L.get("id"))
            l = pick_line(L.get("lines"))
            if not g or not l:
                continue
            try:
                so, sc = float(l["spreadOpen"]), float(l["spread"])
            except (TypeError, ValueError):
                continue
            to, tc = l.get("overUnderOpen"), l.get("overUnder")
            hs, as_ = L.get("homeScore"), L.get("awayScore")
            rows.append({"y": y, "week": g.get("week"), "so": so, "sc": sc, "to": float(to) if to not in (None, "") else None,
                         "tc": float(tc) if tc not in (None, "") else None, "hs": hs, "as": as_,
                         "neutral": bool(g.get("neutralSite")), "conf": bool(g.get("conferenceGame")),
                         "hr": g["_rest"].get("homeTeam"), "ar": g["_rest"].get("awayTeam"),
                         "homeConf": g.get("homeConference"), "awayConf": g.get("awayConference")})
    out = {}

    def grp(name, f, key="sm"):
        S = []
        for r in rows:
            if not f(r):
                continue
            if key == "sm":
                v = r["sc"] - r["so"]
            elif key == "tm":
                if r["to"] is None or r["tc"] is None:
                    continue
                v = r["tc"] - r["to"]
            elif key == "ats":
                if r["hs"] is None:
                    continue
                v = (r["hs"] - r["as"]) + r["sc"]
            S.append(v)
        if len(S) < 80:
            return
        a = np.array(S)
        h = len(a) // 2
        out[f"{name} | {key}"] = {"n": len(a), "mean": round(float(a.mean()), 3), "se": round(float(a.std() / np.sqrt(len(a))), 3),
                                  "early": round(float(a[:h].mean()), 3), "late": round(float(a[h:].mean()), 3)}

    P5 = {"SEC", "Big Ten", "Big 12", "ACC", "Pac-12"}
    specs = [
        ("all", lambda r: True),
        ("home off bye (12+ days), away 6-8", lambda r: (r["hr"] or 0) >= 12 and 6 <= (r["ar"] or 0) <= 8),
        ("away off bye, home 6-8", lambda r: (r["ar"] or 0) >= 12 and 6 <= (r["hr"] or 0) <= 8),
        ("home short week (<=5)", lambda r: (r["hr"] or 9) <= 5),
        ("away short week (<=5)", lambda r: (r["ar"] or 9) <= 5),
        ("home fav 21+ (open)", lambda r: r["so"] <= -21),
        ("home fav 7-14", lambda r: -14 <= r["so"] <= -7),
        ("home dog 7+", lambda r: r["so"] >= 7),
        ("pick'em +-3", lambda r: abs(r["so"]) <= 3),
        ("weeks 0-2", lambda r: (r["week"] or 99) <= 2),
        ("weeks 10+", lambda r: (r["week"] or 0) >= 10),
        ("neutral site", lambda r: r["neutral"]),
        ("non-conference", lambda r: not r["conf"]),
        ("P5 home vs G5 away", lambda r: r["homeConf"] in P5 and r["awayConf"] not in P5),
        ("G5 home vs P5 away", lambda r: r["homeConf"] not in P5 and r["awayConf"] in P5),
        ("total open 60+", lambda r: (r["to"] or 0) >= 60),
        ("total open <45", lambda r: r["to"] is not None and r["to"] < 45),
    ]
    for name, f in specs:
        for key in ("sm", "tm", "ats"):
            grp(name, f, key)
    OUT.with_suffix(".json").write_text(json.dumps({"rows": len(rows), "groups": out}, indent=1))
    lines_md = ["# College football: open-to-close moves by situation (ncaaf_research.py)", "",
                f"CFBD lines, FBS regular seasons {YEARS[0]}-{YEARS[-1]} (no 2020), {len(rows)} games. "
                "sm: home spread close minus open (below 0 = toward the home team). tm: total close minus open. "
                "ats: home margin + closing spread (above 0 = home covered the close). early/late = halves of the sample.", "",
                "| Situation | Measure | Games | Mean | se | Early | Late |", "|---|---|---|---|---|---|---|"]
    for k, v in out.items():
        name, key = k.split(" | ")
        lines_md.append(f"| {name} | {key} | {v['n']} | {v['mean']:+.3f} | {v['se']} | {v['early']:+.3f} | {v['late']:+.3f} |")
    OUT.with_suffix(".md").write_text("\n".join(lines_md) + "\n")
    print("\n".join(lines_md))


if __name__ == "__main__":
    main()
