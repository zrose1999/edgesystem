#!/usr/bin/env python3
"""EDGE NFL stats (v1). Real numbers for the read, and a model that grades itself.

Run it before every read. It:
  1. Downloads free nflverse play-by-play for this season and the two before it.
  2. Rates every team: offense and defense EPA per play and success rate, adjusted for
     the opponents they faced, garbage time removed, blended with last season's
     rating while the current sample is small.
  3. Backtests itself: for every completed week in the last season and this one, it
     rebuilds the ratings using only earlier games, projects each game, and compares
     the projection with the closing line and the result. From that it LEARNS k, how
     much of its own gap from the market to trust. This is how the model gets better
     every run: more games, better k, and no rule is rewritten by hand.
  4. Projects every upcoming NFL game in the ledger: raw margin and total, the market
     number, and the fair number after shrinking by the learned k.

Outputs (read these, never retype them):
  stats/nfl_teams.json        ratings per team, plus the last two games' main passer
  stats/nfl_calibration.json  learned k, backtest sample size, and accuracy vs the market
  stats/nfl_matchups.json     upcoming games: raw, market, fair, edge, and the bar check

The stats cannot see injuries, a QB change that has not happened yet, or weather. That
is the analyst's job: start from the fair number here and adjust only with a named reason.
"""

import csv
import gzip
import io
import json
import os
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats"
CACHE = Path(os.environ.get("EDGE_CACHE", "/tmp/edge-cache"))   # outside the repo, never committed
LEDGER = ROOT / "ledger" / "ledger.json"
URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.csv.gz"

SEASON = int(os.environ.get("EDGE_SEASON", "2026"))
PRIOR_GAMES = 4.0      # games of current data that weigh the same as the prior
PRIOR_KEEP = 0.6       # last season's rating carried forward (the rest regresses to average)
HFA = 1.5              # home field, points
PLAYS = 62.0           # offensive plays per team per game, turns EPA per play into points
K_DEFAULT = 0.3
K_MAX = 0.5
BIG_GAP = 6.0
ITERATIONS = 12

BARS = {"spread": 1.5, "total": 2.0}
KEY_BAR = 2.5

TEAMS = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Los Angeles Rams": "LA", "Los Angeles Chargers": "LAC",
    "Las Vegas Raiders": "LV", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "Seattle Seahawks": "SEA", "San Francisco 49ers": "SF", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}


def fetch(season):
    """Play-by-play CSV for a season. Past seasons are cached; the current one is re-downloaded."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"pbp_{season}.csv.gz"
    if season < SEASON and path.exists():
        return path
    with urllib.request.urlopen(URL.format(season), timeout=180) as resp:
        path.write_bytes(resp.read())
    return path


def fnum(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load(season):
    """Team-game aggregates and game results for one season, regular season only."""
    agg = {}
    games = {}
    passers = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
    with gzip.open(fetch(season), "rt", newline="") as fh:
        for p in csv.DictReader(fh):
            if p.get("season_type") != "REG":
                continue
            gid = p["game_id"]
            if gid not in games:
                games[gid] = {"id": gid, "week": int(p["week"]), "home": p["home_team"],
                              "away": p["away_team"], "line": fnum(p.get("spread_line")),
                              "totalLine": fnum(p.get("total_line")), "result": fnum(p.get("result")),
                              "total": fnum(p.get("total")), "date": p.get("game_date")}
            if p.get("play_type") not in ("pass", "run"):
                continue
            epa, wp = fnum(p.get("epa")), fnum(p.get("wp"))
            off, dfn = p.get("posteam"), p.get("defteam")
            if epa is None or not off or not dfn or wp is None or not 0.05 <= wp <= 0.95:
                continue
            key = (gid, off)
            a = agg.get(key)
            if a is None:
                a = agg[key] = {"game": gid, "week": int(p["week"]), "team": off, "opp": dfn,
                                "plays": 0, "epa": 0.0, "succ": 0.0,
                                "passN": 0, "passEpa": 0.0, "rushN": 0, "rushEpa": 0.0}
            a["plays"] += 1
            a["epa"] += epa
            a["succ"] += fnum(p.get("success")) or 0.0
            if p.get("pass") == "1" or p.get("qb_dropback") == "1":
                a["passN"] += 1
                a["passEpa"] += epa
                name = p.get("passer_player_name")
                if name:
                    passers[key][name][0] += 1
                    passers[key][name][1] += epa
            else:
                a["rushN"] += 1
                a["rushEpa"] += epa
    for gid, g in games.items():
        done = g["result"] is not None and (gid, g["home"]) in agg and (gid, g["away"]) in agg
        g["done"] = done
    return list(agg.values()), games, passers


def rate(rows, prior=None):
    """Opponent-adjusted offense and defense EPA per play, centered on league average,
    blended with the prior while the sample is small."""
    if not rows:
        return {}
    plays = sum(r["plays"] for r in rows)
    mean = sum(r["epa"] for r in rows) / plays
    smean = sum(r["succ"] for r in rows) / plays
    teams = {r["team"] for r in rows} | {r["opp"] for r in rows}
    off = {t: 0.0 for t in teams}
    dfn = {t: 0.0 for t in teams}
    for _ in range(ITERATIONS):
        new_off, new_def = {}, {}
        for t in teams:
            mine = [r for r in rows if r["team"] == t]
            n = sum(r["plays"] for r in mine)
            new_off[t] = (sum(r["epa"] - r["plays"] * (mean + dfn[r["opp"]]) for r in mine) / n) if n else 0.0
            theirs = [r for r in rows if r["opp"] == t]
            n = sum(r["plays"] for r in theirs)
            new_def[t] = (sum(r["epa"] - r["plays"] * (mean + off[r["team"]]) for r in theirs) / n) if n else 0.0
        off, dfn = new_off, new_def
    out = {}
    for t in teams:
        mine = [r for r in rows if r["team"] == t]
        theirs = [r for r in rows if r["opp"] == t]
        g = len(mine)
        w = g / (g + PRIOR_GAMES) if prior is not None else 1.0
        p = (prior or {}).get(t, {"off": 0.0, "def": 0.0})
        po, pd = p["off"] * PRIOR_KEEP, p["def"] * PRIOR_KEEP
        n_off = sum(r["plays"] for r in mine) or 1
        n_def = sum(r["plays"] for r in theirs) or 1
        pn = sum(r["passN"] for r in mine) or 1
        rn = sum(r["rushN"] for r in mine) or 1
        out[t] = {
            "games": g,
            "off": round(w * off[t] + (1 - w) * po, 4),
            "def": round(w * dfn[t] + (1 - w) * pd, 4),
            "offAdjOnly": round(off[t], 4), "defAdjOnly": round(dfn[t], 4),
            "offRaw": round(sum(r["epa"] for r in mine) / n_off - mean, 4),
            "defRaw": round(sum(r["epa"] for r in theirs) / n_def - mean, 4),
            "offSuccess": round(sum(r["succ"] for r in mine) / n_off - smean, 4),
            "defSuccess": round(sum(r["succ"] for r in theirs) / n_def - smean, 4),
            "passEpa": round(sum(r["passEpa"] for r in mine) / pn, 4),
            "rushEpa": round(sum(r["rushEpa"] for r in mine) / rn, 4),
            "priorWeight": round(1 - w, 2),
        }
    return out


def project(R, home, away, avg_points):
    h, a = R.get(home), R.get(away)
    if not h or not a:
        return None
    home_epa = h["off"] + a["def"]      # positive def = bad defense, gives up more
    away_epa = a["off"] + h["def"]
    margin = PLAYS * (home_epa - away_epa) + HFA
    total = 2 * avg_points + PLAYS * (home_epa + away_epa)
    return round(margin, 2), round(total, 2)


def avg_points(games):
    done = [g for g in games if g.get("total") is not None]
    return sum(g["total"] for g in done) / (2 * len(done)) if done else 22.5


def season_ratings(season, prior):
    rows, games, passers = load(season)
    return rows, games, passers, rate(rows, prior)


def backtest(season, prior):
    """Walk forward through a season: rate on earlier weeks only, project the next week."""
    rows, games, _ = load(season)
    out = []
    weeks = sorted({g["week"] for g in games.values() if g["done"]})
    for wk in weeks:
        if wk < 2:
            continue
        past = [r for r in rows if r["week"] < wk]
        R = rate(past, prior)
        pts = avg_points([g for g in games.values() if g["done"] and g["week"] < wk])
        for g in games.values():
            if g["week"] != wk or not g["done"] or g["line"] is None:
                continue
            proj = project(R, g["home"], g["away"], pts)
            if not proj:
                continue
            out.append({"season": season, "week": wk, "game": g["id"], "rawMargin": proj[0],
                        "rawTotal": proj[1], "line": g["line"], "totalLine": g["totalLine"],
                        "result": g["result"], "total": g["total"]})
    return out


def learn_k(samples, raw, line, actual):
    """Slope of (result - line) on (model - line). The clipped value is what the desk uses."""
    xs = [(s[raw] - s[line], s[actual] - s[line]) for s in samples
          if s.get(line) is not None and s.get(actual) is not None]
    n = len(xs)
    if n < 40:
        return {"k": K_DEFAULT, "kRaw": None, "n": n, "se": None, "bigGap": None}
    sxx = sum(x * x for x, _ in xs)
    k = sum(x * y for x, y in xs) / sxx if sxx else 0.0
    se = (sum((y - k * x) ** 2 for x, y in xs) / (n - 1) / sxx) ** 0.5 if sxx else None
    big = [(x, y) for x, y in xs if abs(x) >= BIG_GAP]
    won = sum(1 for x, y in big if x * y > 0)
    push = sum(1 for x, y in big if y == 0)
    return {"k": round(max(0.0, min(K_MAX, k)), 3), "kRaw": round(k, 3), "n": n,
            "se": round(se, 3) if se else None,
            "bigGap": {"gapAtLeast": BIG_GAP, "games": len(big), "modelSideWon": won,
                       "modelSideLost": len(big) - won - push, "push": push}}


def mae(samples, a, b):
    xs = [abs(s[a] - s[b]) for s in samples if s.get(a) is not None and s.get(b) is not None]
    return round(sum(xs) / len(xs), 2) if xs else None


def bar_check(edge, bar):
    if edge >= bar:
        return "full"
    if edge >= bar / 2:
        return "half"
    return "no"


def matchups(R, pts, k_side, k_total):
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {"rows": []}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    games = {}
    for r in ledger.get("rows") or []:
        if r.get("sport") != "NFL" or not r.get("commence") or r["commence"] <= now or "lastSnap" not in r:
            continue
        key = (r["home"], r["away"], r["commence"])
        games.setdefault(key, {})[r["market"]] = r
    out = []
    for (home, away, commence), mk in sorted(games.items(), key=lambda kv: kv[0][2]):
        hc, ac = TEAMS.get(home), TEAMS.get(away)
        proj = project(R, hc, ac, pts) if hc and ac else None
        item = {"event": f"{away} at {home}", "commence": commence, "home": hc, "away": ac}
        if not proj:
            item["note"] = "no rating for one team"
            out.append(item)
            continue
        raw_margin, raw_total = proj
        item["rawHomeMargin"] = raw_margin
        item["rawTotal"] = raw_total
        sp = mk.get("spread")
        if sp:
            line = sp["lastSnap"]["line"]               # home line, -3 = home favored by 3
            market_margin = -line
            fair_margin = market_margin + k_side * (raw_margin - market_margin)
            fair_line = round(-fair_margin, 2)
            side = "home" if fair_line < line else "away"
            edge = round(abs(line - fair_line), 2)
            lo, hi = sorted((line, fair_line))
            bar = KEY_BAR if any(lo <= s * n <= hi for n in (3, 7) for s in (1, -1)) else BARS["spread"]
            item["spread"] = {"rowId": sp["id"], "marketHomeLine": line, "fairHomeLine": fair_line,
                              "lean": side, "edge": edge, "bar": bar, "clears": bar_check(edge, bar),
                              "priceTime": sp["lastSnap"]["time"]}
        tt = mk.get("total")
        if tt:
            line = tt["lastSnap"]["line"]
            fair = round(line + k_total * (raw_total - line), 2)
            edge = round(abs(fair - line), 2)
            item["total"] = {"rowId": tt["id"], "marketTotal": line, "fairTotal": fair,
                             "lean": "over" if fair > line else "under", "edge": edge,
                             "bar": BARS["total"], "clears": bar_check(edge, BARS["total"]),
                             "priceTime": tt["lastSnap"]["time"]}
        out.append(item)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s2, s1, s0 = SEASON - 2, SEASON - 1, SEASON

    rows2, games2, _ = load(s2)
    prior1 = rate(rows2)
    rows1, games1, _ = load(s1)
    prior0 = rate(rows1, prior1)
    rows0, games0, passers0 = load(s0)
    R = rate(rows0, prior0)
    pts = avg_points([g for g in games0.values() if g["done"]]) if any(g["done"] for g in games0.values()) \
        else avg_points(list(games1.values()))

    samples = backtest(s1, prior1) + backtest(s0, prior0)
    side = learn_k(samples, "rawMargin", "line", "result")
    tot = learn_k(samples, "rawTotal", "totalLine", "total")
    k_side, k_total = side["k"], tot["k"]
    for s in samples:
        s["fairMargin"] = s["line"] + k_side * (s["rawMargin"] - s["line"])
    cal = {
        "asOf": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "games": len(samples),
        "side": side, "total": tot, "kSide": k_side, "kTotal": k_total,
        "maeMarketSide": mae(samples, "line", "result"),
        "maeRawSide": mae(samples, "rawMargin", "result"),
        "maeFairSide": mae(samples, "fairMargin", "result"),
        "maeMarketTotal": mae(samples, "totalLine", "total"),
        "maeRawTotal": mae(samples, "rawTotal", "total"),
        "read": ("k is how much of the model's gap from the closing line has held up in results, "
                 "relearned from every completed game each run. 0 means the market already prices "
                 "everything these stats know, so a stats gap alone is not an edge. kRaw below 0 means "
                 "the market was right more often than the stats when they disagreed. bigGap shows how "
                 "the stats side did when it disagreed with the close by 6 or more. Use k as given. "
                 "While k is near 0, edges come from what the stats cannot see: news, timing, weather."),
    }

    latest = max((r["week"] for r in rows0), default=0)
    teams = {}
    for t, v in sorted(R.items()):
        recent = [key for key in passers0 if key[1] == t]
        recent = sorted(recent, key=lambda key: next((r["week"] for r in rows0 if r["game"] == key[0] and r["team"] == t), 0))[-2:]
        qb = defaultdict(lambda: [0, 0.0])
        for key in recent:
            for name, (n, e) in passers0[key].items():
                qb[name][0] += n
                qb[name][1] += e
        main_qb = max(qb.items(), key=lambda kv: kv[1][0]) if qb else None
        v["lastTwoMainPasser"] = ({"name": main_qb[0], "dropbacks": main_qb[1][0],
                                   "epaPerDropback": round(main_qb[1][1] / main_qb[1][0], 3)} if main_qb else None)
        teams[t] = v
    (OUT / "nfl_teams.json").write_text(json.dumps({
        "season": s0, "throughWeek": latest, "avgPointsPerTeam": round(pts, 2),
        "note": "EPA per play relative to league average. off: higher is better. def: lower is better (EPA allowed).",
        "teams": teams}, indent=2) + "\n")
    (OUT / "nfl_calibration.json").write_text(json.dumps(cal, indent=2) + "\n")
    games = matchups(R, pts, k_side, k_total)
    (OUT / "nfl_matchups.json").write_text(json.dumps({
        "asOf": cal["asOf"], "kSide": k_side, "kTotal": k_total, "games": games}, indent=2) + "\n")
    print(json.dumps({"throughWeek": latest, "backtestGames": len(samples), "kSide": k_side,
                      "kTotal": k_total, "maeMarketSide": cal["maeMarketSide"],
                      "maeRawSide": cal["maeRawSide"], "upcoming": len(games)}))


if __name__ == "__main__":
    main()
