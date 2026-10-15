#!/usr/bin/env python3
"""EDGE NFL feature store. Pre-game data points for every past game (training) and upcoming game (live), same form.

  python3 features_nfl.py history     build stats/features/nfl_history.json

Data: nflverse games (free): scores, closing spread/total/moneyline, rest, division game, roof, surface, starting QB
and coach; opening lines from backfill_nfl.py (Odds API, one early-week snapshot per week) for past seasons, and from
EDGE's own ledger for this season. Per team, before the game: scoring and margin over the last 1/3/8 games, results
against the closing spread and total, rest and rest gap, whether the starting QB changed in the last game (the
upcoming starter is left out: it is not known the same way live), games
since the coach's first game, plus division game, roof, surface, week; the opening market itself.
Targets: closing minus opening home spread and total, and the home win probability (no-vig) close minus open.
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OPENS = ROOT / "stats" / "history" / "nfl_open"
OUT = ROOT / "stats" / "features" / "nfl_history.json"
NAMES = {"ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
         "CAR": "Carolina Panthers", "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
         "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
         "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
         "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers", "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins",
         "MIN": "Minnesota Vikings", "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
         "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks",
         "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
         "OAK": "Las Vegas Raiders", "SD": "Los Angeles Chargers", "STL": "Los Angeles Rams"}
OPEN_PREF = ["draftkings", "fanduel", "betmgm", "williamhill_us", "pinnacle"]
ROOFS = {"dome": 1.0, "closed": 1.0, "retractable": 0.5}


def novig(a, b):
    imp = lambda p: 100 / (p + 100) if p > 0 else -p / (-p + 100)
    try:
        a, b = float(a), float(b)
        x, y = imp(a), imp(b)
        return x / (x + y)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class Book:
    def __init__(self):
        self.log = defaultdict(list)

    def add(self, g):
        hs, as_ = fnum(g.get("home_score")), fnum(g.get("away_score"))
        if hs is None or as_ is None:
            return
        sl, tl = fnum(g.get("spread_line")), fnum(g.get("total_line"))
        for side, t, pf, pa, qb, coach in (("h", g["home_team"], hs, as_, g.get("home_qb_id"), g.get("home_coach")),
                                           ("a", g["away_team"], as_, hs, g.get("away_qb_id"), g.get("away_coach"))):
            ats = None
            if sl is not None:                       # nflverse spread_line: home favoured by that many points
                ats = (pf - pa) - sl if side == "h" else (pf - pa) + sl
            self.log[NAMES.get(t, t)].append({"day": g["gameday"], "season": g["season"], "pf": pf, "pa": pa, "ats": ats,
                                               "ou": (pf + pa - tl) if tl is not None else None, "qb": qb, "coach": coach})

    def feats(self, team, day, season, p, qb=None, coach=None):
        H = [z for z in self.log.get(team, []) if z["day"] < day]
        S = [z for z in H if z["season"] == season]
        f = {f"{p}_gp": float(len(S))}
        for tag, G in (("l1", S[-1:]), ("l3", S[-3:]), ("l8", H[-8:]), ("ssn", S)):
            if not G:
                continue
            k = len(G)
            f[f"{p}_{tag}_pf"] = sum(z["pf"] for z in G) / k
            f[f"{p}_{tag}_pa"] = sum(z["pa"] for z in G) / k
            f[f"{p}_{tag}_mg"] = f[f"{p}_{tag}_pf"] - f[f"{p}_{tag}_pa"]
            a = [z["ats"] for z in G if z["ats"] is not None]
            o = [z["ou"] for z in G if z["ou"] is not None]
            if a:
                f[f"{p}_{tag}_ats"] = sum(a) / len(a)
            if o:
                f[f"{p}_{tag}_ou"] = sum(o) / len(o)
        if H:
            last = H[-1]
            if len(H) > 1 and last["qb"] and H[-2]["qb"]:
                f[f"{p}_qb_changed_last"] = 1.0 if last["qb"] != H[-2]["qb"] else 0.0
            c = coach or last["coach"]
            f[f"{p}_coach_games"] = float(sum(1 for z in H if z["coach"] == c))
        return f


def game_features(book, g, so, to, mo):
    day, season = g["gameday"], g["season"]
    home, away = NAMES.get(g["home_team"], g["home_team"]), NAMES.get(g["away_team"], g["away_team"])
    f = {}
    f.update(book.feats(home, day, season, "h", g.get("home_qb_id"), g.get("home_coach")))
    f.update(book.feats(away, day, season, "a", g.get("away_qb_id"), g.get("away_coach")))
    for k in list(f):
        if k.startswith("h_") and "a_" + k[2:] in f:
            f["d_" + k[2:]] = f[k] - f["a_" + k[2:]]
    hr, ar = fnum(g.get("home_rest")), fnum(g.get("away_rest"))
    if hr is not None and ar is not None:
        f["h_rest"], f["a_rest"], f["d_rest"] = hr, ar, hr - ar
    f["div_game"] = fnum(g.get("div_game")) or 0.0
    f["roof"] = ROOFS.get((g.get("roof") or "").lower(), 0.0)
    f["grass"] = 1.0 if "grass" in (g.get("surface") or "").lower() else 0.0
    f["neutral"] = 1.0 if (g.get("location") or "").lower() == "neutral" else 0.0
    f["week"] = fnum(g.get("week")) or 0.0
    f["post"] = 0.0 if g.get("game_type") == "REG" else 1.0
    try:
        f["dow"] = float(datetime.fromisoformat(day).weekday())
    except ValueError:
        pass
    if so is not None:
        f["open_spread"] = so
    if to is not None:
        f["open_total"] = to
    if mo is not None:
        f["open_home"] = mo
    return f


def opens_index():
    """(home full name, away full name, game day) -> opening home spread, total, home no-vig prob."""
    idx = {}
    for f in sorted(OPENS.glob("*.json")) if OPENS.exists() else []:
        for wk in json.loads(f.read_text())["weeks"].values():
            for e in wk.get("events") or []:
                b = next((e["books"][k] for k in OPEN_PREF if k in e["books"] and e["books"][k].get("spread") is not None), None)
                if not b:
                    continue
                day = e["commence"][:10]
                rec = {"so": b.get("spread"), "to": b.get("total"), "mo": novig(b.get("ml_home"), b.get("ml_away"))}
                rec["snap"] = wk.get("snapshot") or wk.get("asked")
                for d in (day, (datetime.fromisoformat(day) - timedelta(days=1)).date().isoformat()):
                    k = (e["home"], e["away"], d)                       # UTC evening games fall on the next date
                    # Week 1 carries season-long lookahead lines; the game week's own Tuesday line is the open.
                    if k not in idx or rec["snap"] > idx[k]["snap"]:
                        idx[k] = rec
    return idx


def build_history():
    import backfill_nfl
    games = sorted([g for g in backfill_nfl.nflverse_games() if g.get("gameday")], key=lambda g: g["gameday"])
    idx = opens_index()
    book, rows = Book(), []
    for g in games:
        home, away = NAMES.get(g["home_team"], g["home_team"]), NAMES.get(g["away_team"], g["away_team"])
        o = idx.get((home, away, g["gameday"]))
        sl, tl = fnum(g.get("spread_line")), fnum(g.get("total_line"))
        if o and o["so"] is not None and sl is not None and g.get("home_score"):
            mc = novig(g.get("home_moneyline"), g.get("away_moneyline"))
            f = game_features(book, g, o["so"], o["to"], o["mo"])
            rows.append({"id": g["game_id"], "date": g["gameday"], "home": home, "away": away, "f": f,
                         "y_spread": (-sl) - o["so"],
                         "y_total": (tl - o["to"]) if tl is not None and o["to"] is not None else None,
                         "y_ml": (mc - o["mo"]) if mc is not None and o["mo"] is not None else None})
        book.add(g)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"built": datetime.now(timezone.utc).isoformat(), "rows": rows}, separators=(",", ":")))
    return len(rows)


GAMES_CACHE = ROOT / "stats" / "features" / "nflverse_games.json"
CACHE_H = 6


def cached_games():
    """nflverse games, refetched at most every CACHE_H hours (fast runs come every 15 minutes)."""
    now = datetime.now(timezone.utc)
    if GAMES_CACHE.exists():
        c = json.loads(GAMES_CACHE.read_text())
        if (now - datetime.fromisoformat(c["at"])).total_seconds() < CACHE_H * 3600:
            return c["games"]
    import backfill_nfl
    keep = ("game_id", "season", "game_type", "week", "gameday", "home_team", "away_team", "home_score", "away_score",
            "spread_line", "total_line", "home_moneyline", "away_moneyline", "home_rest", "away_rest", "div_game", "roof",
            "surface", "location", "home_qb_id", "away_qb_id", "home_coach", "away_coach")
    try:
        games = [{k: g.get(k) for k in keep} for g in backfill_nfl.nflverse_games() if int(g["season"]) >= now.year - 2]
    except Exception as exc:  # noqa: BLE001
        print("nflverse", exc)
        return json.loads(GAMES_CACHE.read_text())["games"] if GAMES_CACHE.exists() else []
    if games:
        GAMES_CACHE.parent.mkdir(parents=True, exist_ok=True)
        GAMES_CACHE.write_text(json.dumps({"at": now.isoformat(), "games": games}, separators=(",", ":")))
    return games


def live_book():
    games = sorted([g for g in cached_games() if g.get("gameday")], key=lambda g: g["gameday"])
    book, upcoming = Book(), []
    for g in games:
        if g.get("home_score"):
            book.add(g)
        else:
            upcoming.append(g)
    return book, upcoming


if __name__ == "__main__":
    print("history rows", build_history())
