#!/usr/bin/env python3
"""EDGE college football situational spots (v1). Stamps ncaaf-spot reads from the measured open-to-close moves in
stats/backtest_ncaaf_spots.md (CFBD, 9 FBS seasons, 4,126 games; every value below held in both halves).

  python3 ncaaf_spots.py          stamp reads for games in the next 7 days
  python3 ncaaf_spots.py --dry

Spread (home line; below 0 = toward the home team)
  home off a bye (12+ days) vs away on normal rest (6-8)   -0.55   (t -3.4)
  away off a bye vs home on normal rest                      +0.43   (t +2.8)
  power-conference home vs Group of 5 away                   -0.37   (t -4.5)   } the largest of these three
  other non-conference                                       -0.20   (t -3.7)   } counts (they overlap)
  weeks 0-2                                                  -0.25   (t -3.3)   }
  home favourite of 21+ at the open                          -0.34   (t -4.1)
Total
  home underdog of 7+ at the open                            -0.49   (t -4.5)
  opening total under 45                                     -0.35   (t -3.5)
  weeks 10+                                                  -0.23   (t -3.0)
The applicable values are summed x0.8 for overlap. Fair = current line + the part of that move not yet made since this
desk's open. Conferences and weeks come from the ESPN scoreboard; rest from stats/ncaaf_games.json.
"""

import json
import sys
import urllib.request
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pull

ROOT = Path(__file__).resolve().parent
PATTERN = "ncaaf-spot"
BOARD = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates={d}&groups=80&limit=400"
P5 = {"1", "4", "5", "8", "9"}            # ACC, Big 12, Big Ten, SEC, Pac-12 (ESPN conference ids)
INDEPENDENT_P5 = {"Notre Dame Fighting Irish"}
SHRINK = 0.8
WINDOW_D = 7


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "EDGE desk"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def mascotless(s):
    return " ".join((s or "").lower().split()[:-1]) or (s or "").lower()


def espn_games(now):
    out = {}
    for k in range(0, WINDOW_D + 1):
        d = (now + timedelta(days=k)).strftime("%Y%m%d")
        try:
            data = fetch(BOARD.format(d=d))
        except Exception as exc:  # noqa: BLE001
            print("espn ncaaf", d, exc)
            continue
        week = (data.get("week") or {}).get("number")
        for e in data.get("events") or []:
            c = (e.get("competitions") or [{}])[0]
            t = {x.get("homeAway"): x.get("team") or {} for x in c.get("competitors") or []}
            if "home" not in t or "away" not in t:
                continue
            out[(t["home"].get("displayName"), t["away"].get("displayName"))] = {
                "week": (e.get("week") or {}).get("number") or week, "conf": bool(c.get("conferenceCompetition")),
                "homeConf": str(t["home"].get("conferenceId") or ""), "awayConf": str(t["away"].get("conferenceId") or ""),
                "neutral": bool(c.get("neutralSite")), "home": t["home"].get("displayName"), "away": t["away"].get("displayName")}
    return out


def rest_days(games, team, when):
    day = (pull.parse(when) - timedelta(hours=6)).date()
    prev = [(pull.parse(g["date"]) - timedelta(hours=6)).date() for g in games
            if team in (g.get("home"), g.get("away")) and g.get("date")
            and (pull.parse(g["date"]) - timedelta(hours=6)).date() < day]
    return (day - max(prev)).days if prev else None


def is_p5(conf, name):
    return conf in P5 or name in INDEPENDENT_P5


def main(dry=False):
    now = datetime.now(timezone.utc)
    g = pull.load(ROOT / "stats" / "ncaaf_games.json", {}).get("games") or {}
    sched = list(g.values()) if isinstance(g, dict) else g
    espn = espn_games(now)
    by_names = {(mascotless(h), mascotless(a)): v for (h, a), v in espn.items()}
    ledger = pull.load(pull.LEDGER, {"rows": []})
    done = {p.get("rowId") for p in pull.load(pull.PICKS, {"picks": []})["picks"] if p.get("pattern") == PATTERN}
    horizon = pull.iso(now + timedelta(days=WINDOW_D))
    todo = []
    for row in ledger.get("rows") or []:
        if row.get("sport") != "NCAAF" or row.get("market") not in ("spread", "total") or row.get("id") in done:
            continue
        if not row.get("commence") or not (pull.iso(now) < row["commence"] <= horizon):
            continue
        info = espn.get((row["home"], row["away"])) or by_names.get((mascotless(row["home"]), mascotless(row["away"])))
        o, c = row.get("openSnap") or {}, row.get("lastSnap") or {}
        if not info or o.get("line") is None or c.get("line") is None or info["neutral"]:
            continue
        parts = []
        if row["market"] == "spread":
            hr, ar = rest_days(sched, info["home"], row["commence"]), rest_days(sched, info["away"], row["commence"])
            if hr and ar and hr >= 12 and 6 <= ar <= 8:
                parts.append(("home off a bye", -0.55))
            elif hr and ar and ar >= 12 and 6 <= hr <= 8:
                parts.append(("away off a bye", +0.43))
            group = []
            if is_p5(info["homeConf"], info["home"]) and not is_p5(info["awayConf"], info["away"]):
                group.append(("power home vs Group of 5", -0.37))
            elif not info["conf"]:
                group.append(("non-conference", -0.20))
            if info["week"] is not None and info["week"] <= 2:
                group.append(("weeks 0-2", -0.25))
            if group:
                parts.append(max(group, key=lambda p: abs(p[1])))
            if o["line"] <= -21:
                parts.append(("home favourite 21+", -0.34))
        else:
            sp = next((r for r in ledger["rows"] if r.get("id") == row["id"].replace("|total", "|spread")), None)
            so = ((sp or {}).get("openSnap") or {}).get("line")
            if so is not None and so >= 7:
                parts.append(("home underdog 7+", -0.49))
            if o["line"] < 45:
                parts.append(("opening total under 45", -0.35))
            if info["week"] is not None and info["week"] >= 10:
                parts.append(("weeks 10+", -0.23))
        if not parts:
            continue
        move = SHRINK * sum(v for _, v in parts)
        moved = c["line"] - o["line"]
        already = max(0.0, moved / move) * abs(move) if move else 0.0
        remaining = max(0.0, abs(move) - already)
        if remaining < 0.1:
            continue
        fair = c["line"] + (remaining if move > 0 else -remaining)
        why = (f"{'; '.join(f'{n} {v:+.2f}' for n, v in parts)} (x{SHRINK} overlap) = expected move {move:+.2f}. "
               f"Open {o['line']:g}, now {c['line']:g}, {remaining:.2f} still to come; fair {fair:+.2f}.")
        todo.append((row, fair, why))
    if dry:
        for row, fair, why in todo:
            print(f"WOULD READ {row['id']} | {why}")
    else:
        if "NCAAF" not in pull.READ:
            pull.READ = pull.READ + ["NCAAF"]
        for row, fair, why in todo:
            args = Namespace(id=row["id"], fair=f"{fair:.2f}", confidence="medium", reason=why,
                             falsifier="The line closes at or past the open on the other side.",
                             pattern=PATTERN, stake="0", big=True, by="ncaaf_spots.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"pattern": PATTERN, "reads": len(todo), "espnGames": len(espn), "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
