#!/usr/bin/env python3
"""EDGE college football feature store. Every pre-game data point the desk can get for free, in the same form for
history (training) and upcoming games (live). The learner decides what matters; nothing here is a strategy.

  python3 features_ncaaf.py refresh   fetch CFBD data into compact caches (needs CFBD_API_KEY): past seasons once,
                                      the current season every run
  python3 features_ncaaf.py history   build stats/features/ncaaf_history.json from the caches (no key needed)

Data (CollegeFootballData, CFBD_API_KEY): /games (dates, sites, conferences, scores, pregame Elo), /lines (opening and
closing spread and total and moneylines per provider), /stats/game/advanced (per-game EPA/PPA, success rate,
explosiveness, line yards, stuff rate, passing and rushing splits, offense and defense). Seasons 2016 on, 2020 skipped.
Per team, before each game (no lookahead): scoring and margin over the last 1/3 games and the season, results against
the closing spread and total, advanced offense and defense over the last 3 and the season (last season's for the
first weeks), Elo, rest, games played, home/away/neutral, conference game, power-conference flags, week; the opening
market itself and the gap between Elo and the open. Targets: closing minus opening spread (home) and total.
"""

import json
import os
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "stats" / "history" / "ncaaf"
OUT = ROOT / "stats" / "features" / "ncaaf_history.json"
API = "https://api.collegefootballdata.com"
FIRST = 2016
PREF = ["DraftKings", "ESPN Bet", "Bovada", "consensus", "William Hill (New Jersey)", "teamrankings", "numberfire"]
P5 = {"SEC", "Big Ten", "Big 12", "ACC", "Pac-12"}
ADV = ["ppa", "successRate", "explosiveness", "powerSuccess", "stuffRate", "lineYards", "secondLevelYards",
       "openFieldYards", "pass_ppa", "rush_ppa", "pass_sr", "rush_sr", "plays", "drives"]


def g(d, *names, default=None):
    for n in names:
        if isinstance(d, dict) and d.get(n) is not None:
            return d[n]
    return default


def current_season(now=None):
    now = now or datetime.now(timezone.utc)
    return now.year if now.month >= 6 else now.year - 1


def get(path, key):
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except Exception as exc:  # noqa: BLE001
            print("cfbd", path, exc)
            time.sleep(5 * (attempt + 1))
    return None


def compact_games(games):
    out = []
    for x in games or []:
        out.append({
            "id": g(x, "id"), "season": g(x, "season"), "week": g(x, "week"),
            "stype": g(x, "seasonType", "season_type"), "date": g(x, "startDate", "start_date"),
            "neutral": bool(g(x, "neutralSite", "neutral_site", default=False)),
            "conf": bool(g(x, "conferenceGame", "conference_game", default=False)),
            "home": g(x, "homeTeam", "home_team"), "away": g(x, "awayTeam", "away_team"),
            "hc": g(x, "homeConference", "home_conference"), "ac": g(x, "awayConference", "away_conference"),
            "hcls": g(x, "homeClassification", "home_division"), "acls": g(x, "awayClassification", "away_division"),
            "hp": g(x, "homePoints", "home_points"), "ap": g(x, "awayPoints", "away_points"),
            "helo": g(x, "homePregameElo", "home_pregame_elo"), "aelo": g(x, "awayPregameElo", "away_pregame_elo"),
            "done": bool(g(x, "completed", default=g(x, "homePoints", "home_points") is not None)),
        })
    return out


def compact_lines(lines):
    out = {}
    for x in lines or []:
        by = {l.get("provider"): l for l in x.get("lines") or []}
        best = None
        for p in PREF + list(by):
            l = by.get(p)
            if l and l.get("spreadOpen") is not None and l.get("spread") is not None:
                best = l
                break
        if not best:
            continue
        out[str(x.get("id"))] = {"so": best.get("spreadOpen"), "sc": best.get("spread"), "to": best.get("overUnderOpen"),
                                 "tc": best.get("overUnder"), "mlh": best.get("homeMoneyline"),
                                 "mla": best.get("awayMoneyline"), "prov": best.get("provider")}
    return out


def compact_adv(rows):
    out = {}
    for x in rows or []:
        gid, team = g(x, "gameId", "game_id"), g(x, "team")
        rec = {}
        for side in ("offense", "defense"):
            s = x.get(side) or {}
            vals = {"ppa": s.get("ppa"), "successRate": s.get("successRate"), "explosiveness": s.get("explosiveness"),
                    "powerSuccess": s.get("powerSuccess"), "stuffRate": s.get("stuffRate"), "lineYards": s.get("lineYards"),
                    "secondLevelYards": s.get("secondLevelYards"), "openFieldYards": s.get("openFieldYards"),
                    "pass_ppa": (s.get("passingPlays") or {}).get("ppa"), "rush_ppa": (s.get("rushingPlays") or {}).get("ppa"),
                    "pass_sr": (s.get("passingPlays") or {}).get("successRate"),
                    "rush_sr": (s.get("rushingPlays") or {}).get("successRate"),
                    "plays": s.get("plays"), "drives": s.get("drives")}
            rec[side[0]] = {k: float(v) for k, v in vals.items() if isinstance(v, (int, float))}
        out[f"{gid}|{team}"] = rec
    return out


REFRESH_H = 44


def refresh(key, force_current=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    cur = current_season()
    calls = 0
    for y in range(FIRST, cur + 1):
        if y == 2020:
            continue
        f = CACHE / f"cfbd_{y}.json"
        if f.exists() and y < cur:
            continue
        if y == cur and f.exists():
            age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(json.loads(f.read_text())["at"])).total_seconds() / 3600
            if age_h < REFRESH_H and not force_current:
                continue                     # the current season refreshes every REFRESH_H hours (keeps commits small)
        games = (get(f"/games?year={y}&seasonType=regular", key) or []) + (get(f"/games?year={y}&seasonType=postseason", key) or [])
        lines = (get(f"/lines?year={y}&seasonType=regular", key) or []) + (get(f"/lines?year={y}&seasonType=postseason", key) or [])
        adv = get(f"/stats/game/advanced?year={y}", key) or []
        calls += 5
        if not games:
            print("no games for", y)
            continue
        f.write_text(json.dumps({"season": y, "games": compact_games(games), "lines": compact_lines(lines),
                                 "adv": compact_adv(adv), "at": datetime.now(timezone.utc).isoformat()},
                                separators=(",", ":")))
        print(y, "games", len(games), "lines", len(lines), "adv", len(adv))
    return calls


def load_all():
    games, lines, adv = [], {}, {}
    for f in sorted(CACHE.glob("cfbd_*.json")):
        d = json.loads(f.read_text())
        games += d["games"]
        lines.update(d["lines"])
        adv.update(d["adv"])
    games = [x for x in games if x.get("date") and x.get("home") and x.get("away")]
    games.sort(key=lambda x: x["date"])
    return games, lines, adv


class Book:
    """Per-team game log, filled in date order with finished games only."""
    def __init__(self, lines, adv):
        self.log = defaultdict(list)
        self.lines, self.adv = lines, adv

    def add(self, x):
        if x.get("hp") is None or x.get("ap") is None:
            return
        L = self.lines.get(str(x["id"])) or {}
        sc, tc = L.get("sc"), L.get("tc")
        day = x["date"][:10]
        for side, t, o, pf, pa in (("h", x["home"], x["away"], x["hp"], x["ap"]), ("a", x["away"], x["home"], x["ap"], x["hp"])):
            a = self.adv.get(f"{x['id']}|{t}") or {}
            ats = None
            if sc is not None:
                ats = (pf - pa) + (sc if side == "h" else -sc)
            self.log[t].append({"day": day, "season": x["season"], "pf": pf, "pa": pa, "ats": ats,
                                "ou": (pf + pa - tc) if tc is not None else None, "o": a.get("o") or {}, "d": a.get("d") or {}})

    def feats(self, t, day, season, p):
        H = [z for z in self.log.get(t, []) if z["day"] < day]
        S = [z for z in H if z["season"] == season]
        P = [z for z in H if z["season"] == season - 1]
        f = {f"{p}_gp": float(len(S))}
        for tag, G in (("l1", S[-1:]), ("l3", S[-3:]), ("ssn", S), ("prev", P)):
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
            if tag in ("l3", "ssn", "prev"):
                for side in ("o", "d"):
                    for k2 in ADV:
                        v = [z[side][k2] for z in G if k2 in z[side]]
                        if v:
                            f[f"{p}_{tag}_{side}_{k2}"] = sum(v) / len(v)
        if S:
            try:
                rest = (datetime.fromisoformat(day) - datetime.fromisoformat(S[-1]["day"])).days
                f[f"{p}_rest"] = float(min(rest, 21))
            except ValueError:
                pass
        return f


def game_features(book, x, so, to, ml_home=None):
    day, season = x["date"][:10], x["season"]
    f = {}
    f.update(book.feats(x["home"], day, season, "h"))
    f.update(book.feats(x["away"], day, season, "a"))
    for k in list(f):
        if k.startswith("h_") and "a_" + k[2:] in f:
            f["d_" + k[2:]] = f[k] - f["a_" + k[2:]]
    f["neutral"] = 1.0 if x.get("neutral") else 0.0
    f["conf_game"] = 1.0 if x.get("conf") else 0.0
    f["h_p5"] = 1.0 if x.get("hc") in P5 else 0.0
    f["a_p5"] = 1.0 if x.get("ac") in P5 else 0.0
    f["h_fbs"] = 1.0 if (x.get("hcls") or "fbs").lower() == "fbs" else 0.0
    f["a_fbs"] = 1.0 if (x.get("acls") or "fbs").lower() == "fbs" else 0.0
    f["week"] = float(x.get("week") or 0)
    f["post"] = 1.0 if x.get("stype") == "postseason" else 0.0
    if x.get("helo") is not None and x.get("aelo") is not None:
        f["elo_diff"] = float(x["helo"] - x["aelo"])
        if so is not None:
            f["elo_minus_open"] = (x["helo"] - x["aelo"] + (0 if x.get("neutral") else 55)) / 25.0 + so
    if so is not None:
        f["open_spread"] = float(so)
    if to is not None:
        f["open_total"] = float(to)
    if ml_home is not None:
        f["open_home"] = ml_home
    return f


def novig(a, b):
    imp = lambda p: 100 / (p + 100) if p > 0 else -p / (-p + 100)
    try:
        x, y = imp(a), imp(b)
        return x / (x + y)
    except (TypeError, ZeroDivisionError):
        return None


def build_history():
    games, lines, adv = load_all()
    book, rows = Book(lines, adv), []
    for x in games:
        L = lines.get(str(x["id"]))
        if x.get("done") and L and x.get("hp") is not None:
            so, sc, to, tc = L.get("so"), L.get("sc"), L.get("to"), L.get("tc")
            if so is not None and sc is not None:
                f = game_features(book, x, so, to)
                rows.append({"id": x["id"], "date": x["date"], "home": x["home"], "away": x["away"], "f": f,
                             "y_spread": sc - so, "y_total": (tc - to) if to is not None and tc is not None else None})
        book.add(x)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"built": datetime.now(timezone.utc).isoformat(), "rows": rows}, separators=(",", ":")))
    return len(rows)


def live_book():
    """Book of every finished game in the caches, plus the upcoming games (for Elo, sites, conferences)."""
    games, lines, adv = load_all()
    book = Book(lines, adv)
    upcoming = []
    for x in games:
        if x.get("done"):
            book.add(x)
        else:
            upcoming.append(x)
    return book, upcoming


if __name__ == "__main__":
    cmd = (sys.argv[1:] or ["history"])[0]
    if cmd == "refresh":
        key = os.environ.get("CFBD_API_KEY", "").strip()
        if not key:
            sys.exit("CFBD_API_KEY is not set")
        print(json.dumps({"cfbdCalls": refresh(key, force_current="--force" in sys.argv)}))
    else:
        print("history rows", build_history())
