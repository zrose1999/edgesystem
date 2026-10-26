#!/usr/bin/env python3
"""EDGE matchup notes: the secondary desk. Key stats and unit-vs-unit matchups for every upcoming game, with
suggestions. NOT official EDGE plays.

Kept apart from the CLV desk on purpose (Zack, 2026-10-22):
  - Writes only under matchups/. Nothing in pull.py, grade.py, scan.py, learner.py, learn_live.py, edge_stack.py,
    kalshi.py or trading/ reads it. Notes take no reads, carry no stake and never reach Kalshi.
  - Notes are graded here, on their own track record (win/loss at the line when noted, plus how the line moved to
    the close). That record is information only. A note type can join EDGE only as a measured pattern at a weekly
    review, like any hand idea (DESK.md standing rules).

  python3 matchups.py                 notes for this week's NFL games (default)
  python3 matchups.py nfl [--days N]  same, games in the next N days (default 7)
  python3 matchups.py grade           settle past notes from final scores and EDGE's line snapshots
  python3 matchups.py html [file]     render the latest slate as one self-contained page

Data (free): nflverse play-by-play and schedule (GitHub), EDGE's own NFL line snapshots (ledger/snaps) for the
current DraftKings and Pinnacle number, EDGE's living memory (memory/log) for the CLV check on each suggestion.
No Odds API credits are spent: player prop lines are not pulled, so player angles name the stat, not a price.
"""

import csv
import gzip
import io
import json
import math
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "matchups"
CACHE = Path("/tmp/edge_matchups_cache")
PBP_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.csv.gz"
ROSTER_URL = "https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{season}.csv"
GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
SNAPS = ROOT / "ledger" / "snaps"
MEMLOG = ROOT / "memory" / "log"

NAMES = {"ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
         "CAR": "Carolina Panthers", "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
         "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
         "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
         "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers", "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins",
         "MIN": "Minnesota Vikings", "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
         "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks",
         "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans", "WAS": "Washington Commanders"}
OLD = {"OAK": "LV", "SD": "LAC", "STL": "LA"}

# Unit metrics: (key, label, higher_is_better_for_offense). Defense ranks use the same number "allowed", so a
# defense ranked 32 is the one that gives up the most of whatever helps an offense.
UNITS = [
    ("epa", "EPA per play", True),
    ("pass_epa", "EPA per dropback", True),
    ("rush_epa", "EPA per rush", True),
    ("success", "Success rate", True),
    ("explosive", "Explosive play rate", True),
    ("ppd", "Points per drive", True),
    ("rz_td", "Red-zone TD rate", True),
    ("third", "3rd-down conversion", True),
    ("sack", "Sack rate", False),          # offense: sacks taken (lower better); defense: sacks made
    ("pressure", "Pressure rate (hits+sacks)", False),
    ("giveaway", "Turnovers per drive", False),
    ("deep_epa", "EPA on deep throws (20+ air yds)", True),
]
# Pairings that make a matchup: offense metric vs the same metric allowed by the defense.
PAIRS = [
    ("pass_epa", "Passing game"),
    ("rush_epa", "Run game"),
    ("explosive", "Explosive plays"),
    ("ppd", "Scoring per drive"),
    ("rz_td", "Red zone"),
    ("third", "Third downs"),
    ("sack", "Protection vs pass rush"),
    ("giveaway", "Turnovers"),
    ("deep_epa", "Deep passing"),
]
EDGE_GAP = 14      # rank gap (1-32) that makes a mismatch worth a note
STRONG_GAP = 20


# ---------------- io ----------------

def fetch(url, dest, max_age_hours=6):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / dest
    if p.exists() and (datetime.now().timestamp() - p.stat().st_mtime) < max_age_hours * 3600:
        return p
    req = urllib.request.Request(url, headers={"User-Agent": "EDGE-matchups"})
    with urllib.request.urlopen(req, timeout=120) as r:
        p.write_bytes(r.read())
    return p


def fnum(v):
    try:
        if v in (None, "", "NA"):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def team(t):
    return OLD.get(t, t)


def load_games():
    rows = list(csv.DictReader(io.open(fetch(GAMES_URL, "games.csv"), encoding="utf-8")))
    for r in rows:
        r["home_team"], r["away_team"] = team(r["home_team"]), team(r["away_team"])
        for k in ("season", "week"):
            r[k] = int(r[k])
        for k in ("home_score", "away_score", "spread_line", "total_line", "result", "total",
                  "home_rest", "away_rest"):
            r[k] = fnum(r.get(k))
    return rows


KEEP = ["game_id", "week", "posteam", "defteam", "play_type", "qb_dropback", "rush_attempt", "pass_attempt",
        "qb_scramble", "sack", "qb_hit", "epa", "success", "yards_gained", "air_yards", "down", "wp",
        "half_seconds_remaining", "third_down_converted", "third_down_failed", "fixed_drive", "fixed_drive_result",
        "yardline_100", "interception", "fumble_lost", "receiver_player_name", "rusher_player_name",
        "passer_player_name", "cpoe", "pass_oe", "complete_pass", "receiving_yards", "rushing_yards", "touchdown",
        "td_team", "posteam_type", "receiver_player_id", "rusher_player_id", "passer_player_id", "passing_yards",
        "pass_touchdown", "rush_touchdown"]


def load_pbp(season):
    p = fetch(PBP_URL.format(season=season), f"pbp_{season}.csv.gz")
    out = []
    with gzip.open(p, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("season_type") not in ("REG", "POST"):
                continue
            out.append({k: r.get(k) for k in KEEP})
    for r in out:
        r["posteam"], r["defteam"] = team(r["posteam"] or ""), team(r["defteam"] or "")
        r["week"] = int(r["week"])
    return out


# ---------------- unit stats ----------------

def is_play(r):
    return r["play_type"] in ("pass", "run") and r["posteam"] and fnum(r["epa"]) is not None


def unit_stats(plays, weeks=None):
    """Per team, offense and defense, over the given weeks (None = all)."""
    acc = {side: defaultdict(lambda: defaultdict(float)) for side in ("off", "def")}
    drives = defaultdict(dict)        # (game, team, drive) -> {result, min_yl, to}
    games_of = defaultdict(set)
    for r in plays:
        if weeks is not None and r["week"] not in weeks:
            continue
        if not r["posteam"]:
            continue
        o, d = r["posteam"], r["defteam"]
        games_of[o].add(r["game_id"])
        games_of[d].add(r["game_id"])
        dk = (r["game_id"], o, r["fixed_drive"])
        if r["fixed_drive"]:
            dv = drives[dk]
            dv["off"], dv["def"] = o, d
            dv["result"] = r["fixed_drive_result"]
            yl = fnum(r["yardline_100"])
            if yl is not None:
                dv["min_yl"] = min(dv.get("min_yl", 100), yl)
            if fnum(r["interception"]) == 1 or fnum(r["fumble_lost"]) == 1:
                dv["to"] = 1
        if not is_play(r):
            continue
        epa = fnum(r["epa"])
        drop = fnum(r["qb_dropback"]) == 1
        rush = r["play_type"] == "run" and not drop
        yds = fnum(r["yards_gained"]) or 0
        air = fnum(r["air_yards"])
        for side, t in (("off", o), ("def", d)):
            a = acc[side][t]
            a["n"] += 1
            a["epa"] += epa
            a["success"] += fnum(r["success"]) or 0
            if drop:
                a["drop"] += 1
                a["pass_epa"] += epa
                a["sack"] += fnum(r["sack"]) or 0
                a["pressure"] += 1 if (fnum(r["sack"]) == 1 or fnum(r["qb_hit"]) == 1) else 0
                if yds >= 20:
                    a["explosive"] += 1
                if air is not None and air >= 20 and fnum(r["pass_attempt"]) == 1:
                    a["deep_n"] += 1
                    a["deep_epa"] += epa
            elif rush:
                a["rush"] += 1
                a["rush_epa"] += epa
                if yds >= 10:
                    a["explosive"] += 1
            if fnum(r["down"]) == 3:
                c, f_ = fnum(r["third_down_converted"]) or 0, fnum(r["third_down_failed"]) or 0
                a["third_n"] += c + f_
                a["third"] += c
    pts = {"Touchdown": 7, "Field goal": 3}
    for dv in drives.values():
        if "off" not in dv:
            continue
        for side, t in (("off", dv["off"]), ("def", dv["def"])):
            a = acc[side][t]
            a["drives"] += 1
            a["points"] += pts.get(dv.get("result"), 0)
            a["to"] += dv.get("to", 0)
            if dv.get("min_yl", 100) <= 20:
                a["rz"] += 1
                a["rz_td"] += 1 if dv.get("result") == "Touchdown" else 0
    out = {}
    for side in ("off", "def"):
        for t, a in acc[side].items():
            dv = lambda x, y: (a[x] / a[y]) if a[y] else None
            out.setdefault(t, {})[side] = {
                "games": len(games_of[t]),
                "plays": int(a["n"]),
                "epa": dv("epa", "n"), "pass_epa": dv("pass_epa", "drop"), "rush_epa": dv("rush_epa", "rush"),
                "success": dv("success", "n"), "explosive": dv("explosive", "n"),
                "ppd": dv("points", "drives"), "rz_td": dv("rz_td", "rz"), "third": dv("third", "third_n"),
                "sack": dv("sack", "drop"), "pressure": dv("pressure", "drop"), "giveaway": dv("to", "drives"),
                "deep_epa": dv("deep_epa", "deep_n"), "drives_pg": (a["drives"] / len(games_of[t])) if games_of[t] else None,
                "pass_rate": dv("drop", "n"),
            }
    return out


def ranks(stats):
    """rank 1 = best for that side. Offense: best offense. Defense: stingiest defense."""
    R = {t: {"off": {}, "def": {}} for t in stats}
    for key, _, hib in UNITS:
        for side in ("off", "def"):
            vals = [(t, s[side].get(key)) for t, s in stats.items() if side in s and s[side].get(key) is not None]
            # offense wants high when hib; a defense is "best" when it allows the opposite of what helps offense,
            # except sack/pressure/giveaway where the defense wants MORE (those are bad for the offense).
            good_high = hib if side == "off" else (not hib)
            vals.sort(key=lambda x: x[1], reverse=good_high)
            for i, (t, _) in enumerate(vals):
                R[t][side][key] = i + 1
    return R


def league_avg(stats, key, side="off"):
    v = [s[side][key] for s in stats.values() if side in s and s[side].get(key) is not None]
    return sum(v) / len(v) if v else None


# ---------------- players ----------------

def players(plays, t, weeks=None, starter=None):
    tg, air, ryd, car, rush_yd, tds = (defaultdict(float) for _ in range(6))
    team_tg = team_air = team_car = 0
    qb = defaultdict(lambda: [0, 0.0, 0.0, 0])   # dropbacks, epa, cpoe sum, cpoe n
    for r in plays:
        if r["posteam"] != t or (weeks is not None and r["week"] not in weeks) or not is_play(r):
            continue
        if fnum(r["pass_attempt"]) == 1 and r["receiver_player_name"]:
            n = r["receiver_player_name"]
            tg[n] += 1
            team_tg += 1
            a = fnum(r["air_yards"]) or 0
            air[n] += a
            team_air += a
            ryd[n] += fnum(r["receiving_yards"]) or 0
            if fnum(r["touchdown"]) == 1 and r["td_team"] == t:
                tds[n] += 1
        if r["play_type"] == "run" and r["rusher_player_name"] and fnum(r["qb_scramble"]) != 1:
            n = r["rusher_player_name"]
            car[n] += 1
            team_car += 1
            rush_yd[n] += fnum(r["rushing_yards"]) or 0
        if fnum(r["qb_dropback"]) == 1 and r["passer_player_name"]:
            q = qb[r["passer_player_name"]]
            q[0] += 1
            q[1] += fnum(r["epa"]) or 0
            c = fnum(r["cpoe"])
            if c is not None:
                q[2] += c
                q[3] += 1
    games = len({r["game_id"] for r in plays if r["posteam"] == t and (weeks is None or r["week"] in weeks)}) or 1
    rec = sorted(tg, key=lambda n: -tg[n])[:4]
    rb = sorted(car, key=lambda n: -car[n])[:2]
    top_qb = max(qb, key=lambda n: qb[n][0]) if qb else None
    team_drop = sum(v[0] for v in qb.values())
    if starter:
        last = starter.replace(" Jr.", "").replace(" Sr.", "").replace(" III", "").replace(" II", "").split()[-1]
        hit = [n for n in qb if n.split(".")[-1] == last and n[0] == starter[0]]
        if hit:
            top_qb = max(hit, key=lambda n: qb[n][0])
        else:
            top_qb = None
    return {
        "receivers": [{"name": n, "tgtShare": tg[n] / team_tg if team_tg else None,
                       "airShare": air[n] / team_air if team_air else None,
                       "aDOT": air[n] / tg[n] if tg[n] else None, "ydsPg": ryd[n] / games,
                       "tgtPg": tg[n] / games, "tds": int(tds[n])} for n in rec],
        "rushers": [{"name": n, "carryShare": car[n] / team_car if team_car else None,
                     "ypc": rush_yd[n] / car[n] if car[n] else None, "ydsPg": rush_yd[n] / games} for n in rb],
        "qb": ({"name": top_qb, "epaPerDropback": qb[top_qb][1] / qb[top_qb][0],
                "cpoe": (qb[top_qb][2] / qb[top_qb][3]) if qb[top_qb][3] else None,
                "dropbacks": qb[top_qb][0], "shareOfTeamDropbacks": qb[top_qb][0] / team_drop if team_drop else None}
               if top_qb else ({"name": starter, "epaPerDropback": None, "cpoe": None, "dropbacks": 0,
                                "shareOfTeamDropbacks": 0.0} if starter else None)),
    }


# ---------------- trends (results vs the closing number) ----------------

def trends(games, t, season, kick_role):
    """kick_role: dict(home=bool, fav=bool). Records vs nflverse's closing spread/total."""
    done = [g for g in games if g["result"] is not None and g["spread_line"] is not None
            and t in (g["home_team"], g["away_team"]) and g["season"] >= season - 2]
    done.sort(key=lambda g: (g["season"], g["week"]))

    def ats(g):
        home = g["home_team"] == t
        m = g["result"] - g["spread_line"]           # >0 home covered
        if m == 0:
            return "P"
        return "W" if (m > 0) == home else "L"

    def ou(g):
        if g["total_line"] is None:
            return None
        d = g["total"] - g["total_line"]
        return "P" if d == 0 else ("O" if d > 0 else "U")

    def rec(gs, f):
        r = [f(g) for g in gs]
        r = [x for x in r if x]
        a, b = ("W", "L") if f is ats else ("O", "U")
        return {"w": r.count(a), "l": r.count(b), "p": r.count("P"), "n": len(r)}

    def role(g):
        home = g["home_team"] == t
        fav = (g["spread_line"] > 0) == home if g["spread_line"] != 0 else None
        return home, fav

    this = [g for g in done if g["season"] == season]
    last10 = done[-10:]
    same_role = [g for g in done if g["season"] >= season - 1 and role(g)[0] == kick_role["home"]
                 and role(g)[1] == kick_role["fav"]]
    prime = [g for g in done if g["season"] >= season - 1 and (g.get("gametime") or "00:00") >= "19:00"]
    su_last5 = []
    for g in done[-5:]:
        home = g["home_team"] == t
        su_last5.append("W" if (g["result"] > 0) == home and g["result"] != 0 else ("T" if g["result"] == 0 else "L"))
    return {
        "atsSeason": rec(this, ats), "ouSeason": rec(this, ou),
        "atsLast10": rec(last10, ats), "ouLast10": rec(last10, ou),
        "atsRole": rec(same_role, ats), "roleLabel": ("home" if kick_role["home"] else "road") + " "
        + ("favorite" if kick_role["fav"] else "underdog") + " since " + str(season - 1),
        "atsPrime": rec(prime, ats), "ouPrime": rec(prime, ou),
        "suLast5": "".join(su_last5),
    }


# ---------------- EDGE lines and living memory ----------------

_LEDGER = None


def ledger_rows():
    global _LEDGER
    if _LEDGER is None:
        try:
            _LEDGER = json.loads((ROOT / "ledger" / "ledger.json").read_text()).get("rows", [])
        except (OSError, ValueError):
            _LEDGER = []
    return _LEDGER


def edge_context(home, away):
    """Injury and weather notes EDGE's own collectors wrote on this game's ledger rows."""
    want = f"{NAMES.get(away)} at {NAMES.get(home)}"
    inj, wx = [], None
    for r in ledger_rows():
        if r.get("sport") == "NFL" and r.get("event") == want:
            if r.get("injury") and r["injury"] not in ("missing", "") and r["injury"] not in inj:
                inj.append(r["injury"])
            if r.get("weather") and r["weather"] != "missing":
                wx = r["weather"]
    notes = []
    for block in inj:
        for part in block.split(" | "):
            if part not in notes:
                notes.append(part)
    return {"injuries": notes, "weather": wx}


def injury_status(notes):
    """'NE WR1 Romeo Doubs: Active at the open, Injured Reserve now, ...' -> {('R', 'Doubs'): 'Injured Reserve'}"""
    out = {}
    for n in notes:
        if ":" not in n or " now" not in n:
            continue
        head, tail = n.split(":", 1)
        words = head.split()
        name = [w for w in words[2:] if w not in ("starter", "defensive", "OL", "QB")]
        if words[1:3] == ["defensive", "starter"]:
            name = words[3:]
        elif words[1:3] == ["OL", "starter"]:
            name = words[3:]
        else:
            name = words[2:]
        if words[1] == "QB":
            name = [w.rstrip(",") for w in words[2:4]]
        name = [w.rstrip(",") for w in name if w not in ("Jr.", "Sr.", "II", "III")]
        if len(name) < 2:
            continue
        now = None
        for part in tail.split(","):
            part = part.strip()
            if part.endswith(" now"):
                now = part[:-4]
        if now:
            out[(name[0][0], name[-1])] = now
    return out


def status_of(short, status):
    """'R.Doubs' -> status from injury_status."""
    if "." not in short:
        return None
    first, last = short.split(".", 1)
    return status.get((first[:1], last.split()[-1] if last else last))


def edge_lines(home, away, kick_utc_date):
    """Latest DraftKings and Pinnacle numbers EDGE logged for this game (no API credits): the ledger row's last
    snapshot, replaced by a newer near-game snapshot when there is one."""
    out = {}
    want = f"{NAMES.get(away)} at {NAMES.get(home)}"
    for r in ledger_rows():
        if r.get("sport") != "NFL" or r.get("event") != want or r.get("market") not in ("spread", "total", "h2h"):
            continue
        ls = r.get("lastSnap") or {}
        if not ls.get("time"):
            continue
        mk = r["market"]
        line = ls.get("line")
        if mk == "spread" and line is not None and r.get("side") == r.get("away"):
            line = -line
        if mk not in out or ls["time"] >= out[mk]["t"]:
            out[mk] = {"t": ls["time"], "book": ls.get("book"), "line": line,
                       "p": {k: ls.get(k) for k in ("home", "away", "over", "under") if ls.get(k) is not None},
                       "pin": None}
    for month in sorted({kick_utc_date[:7], (datetime.fromisoformat(kick_utc_date) - timedelta(days=7)).strftime("%Y-%m")}):
        p = SNAPS / month / "NFL.jsonl"
        if not p.exists():
            continue
        for line in p.open():
            try:
                s = json.loads(line)
            except ValueError:
                continue
            parts = s.get("id", "").split("|")
            if len(parts) < 4 or parts[2] != want:
                continue
            mk = parts[3]
            if mk not in out or s["t"] >= out[mk]["t"]:
                out[mk] = s
    return out


_MEM = None


def memory_rows():
    global _MEM
    if _MEM is None:
        _MEM = []
        for p in sorted(MEMLOG.glob("*.jsonl")) if MEMLOG.exists() else []:
            for line in p.open():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("clvProb") is not None and r.get("kind") in ("pick", "lean"):
                    _MEM.append(r)
    return _MEM


def memory_check(sport, market, side_kind):
    """Closest past situations in EDGE's living memory: same sport and market, and the same side kind
    (home/away or over/under). Returns n and mean CLV (probability points)."""
    rows = [r for r in memory_rows() if r.get("sport") == sport and r.get("market") == market]
    close = [r for r in rows if (r.get("side") or "") == side_kind]
    def summ(rs):
        if not rs:
            return {"n": 0, "meanClv": None}
        return {"n": len(rs), "meanClv": round(sum(r["clvProb"] for r in rs) / len(rs), 4)}
    return {"sameSide": summ(close), "sameMarket": summ(rows)}


# ---------------- the notes ----------------

def shrink(v, avg, games, k=4.0):
    if v is None or avg is None:
        return avg
    w = games / (games + k)
    return avg + w * (v - avg)


def projection(S, home, away):
    """Matchup view, not a model read: points per drive each way (offense x defense / league), times drives."""
    lg = league_avg(S, "ppd")
    dpg = league_avg(S, "drives_pg") or 11.0
    def ppd(o, d):
        po = shrink(S[o]["off"]["ppd"], lg, S[o]["off"]["games"])
        pd = shrink(S[d]["def"]["ppd"], lg, S[d]["def"]["games"])
        return po * pd / lg
    drives = ((S[home]["off"].get("drives_pg") or dpg) + (S[away]["off"].get("drives_pg") or dpg)) / 2
    h, a = ppd(home, away) * drives, ppd(away, home) * drives
    return {"home": round(h + 0.75, 1), "away": round(a - 0.75, 1), "drives": round(drives, 1),
            "margin": round(h - a + 1.5, 1), "total": round(h + a, 1)}


def mismatches(R, S, off_t, def_t):
    out = []
    for key, label in PAIRS:
        ro, rd = R[off_t]["off"].get(key), R[def_t]["def"].get(key)
        if ro is None or rd is None:
            continue
        gap = rd - ro    # defense rank worse (higher) than offense rank -> offense edge
        kind = None
        if gap >= EDGE_GAP:
            kind = "offense edge"
        elif gap <= -EDGE_GAP:
            kind = "defense edge"
        elif ro <= 8 and rd <= 8:
            kind = "strength vs strength"
        out.append({"unit": label, "key": key, "offense": off_t, "defense": def_t, "offRank": ro, "defRank": rd,
                    "gap": gap, "kind": kind, "strong": abs(gap) >= STRONG_GAP,
                    "offVal": S[off_t]["off"].get(key), "defVal": S[def_t]["def"].get(key)})
    return out


def fmt(key, v):
    if v is None:
        return "–"
    if key in ("success", "explosive", "rz_td", "third", "sack", "pressure", "tgtShare", "airShare", "carryShare"):
        return f"{v * 100:.0f}%"
    if key == "giveaway":
        return f"{v:.2f}"
    if key == "ppd":
        return f"{v:.2f}"
    return f"{v:+.2f}"


OUT_STATUSES = ("Out", "Injured Reserve", "Doubtful", "Suspended", "PUP")


def suggestions(g, S, R, M, P, proj, lines, T, status=None):
    """Plain-language leans built from the mismatches. Each carries its reasons and the living-memory check."""
    home, away = g["home_team"], g["away_team"]
    out = []
    spread = lines.get("spread", {}).get("line")       # DraftKings home line, e.g. -3.0
    total = lines.get("total", {}).get("line")
    if spread is None and g["spread_line"] is not None:
        spread = -g["spread_line"]
    if total is None:
        total = g["total_line"]

    def add(market, side, label, why, conf, kind, line=None):
        mem = memory_check("NFL", {"spread": "spread", "total": "total", "team total": "total"}.get(market, market),
                           {"home": "home", "away": "away", "over": "over", "under": "under"}.get(kind, ""))
        out.append({"market": market, "side": side, "label": label, "why": why, "confidence": conf,
                    "lineAtNote": line if line is not None else {"spread": spread, "total": total}.get(market),
                    "memory": mem})

    edges = {t: [m for m in M[t] if m["kind"] == "offense edge"] for t in (home, away)}
    walls = {t: [m for m in M[t] if m["kind"] == "defense edge"] for t in (home, away)}

    # Side: mismatch count plus the drive-scoring view against the number.
    if spread is not None:
        fair = -proj["margin"]                                # home line equivalent
        diff = spread - fair                                  # >0 home is getting more than the matchup says
        score = {t: len(edges[t]) + sum(1 for m in edges[t] if m["strong"]) - len(walls[t]) for t in (home, away)}
        lean = None
        if diff >= 2.0 and score[home] >= score[away]:
            lean = home
        elif diff <= -2.0 and score[away] >= score[home]:
            lean = away
        if lean:
            opp = away if lean == home else home
            num = spread if lean == home else -spread
            why = [f"Drive-scoring view: {home} {proj['home']}, {away} {proj['away']} (margin {proj['margin']:+.1f} "
                   f"to {home}); the market has {lean} {num:+.1f}."]
            for m in edges[lean][:3]:
                why.append(f"{m['unit']}: {lean} offense #{m['offRank']} vs {opp} defense #{m['defRank']}.")
            tr = T[lean]
            why.append(f"{lean} ATS this season {tr['atsSeason']['w']}-{tr['atsSeason']['l']}"
                       f"{'-' + str(tr['atsSeason']['p']) if tr['atsSeason']['p'] else ''}; "
                       f"{tr['roleLabel']} {tr['atsRole']['w']}-{tr['atsRole']['l']}.")
            add("spread", lean, f"{lean} {num:+.1f}", why, "medium" if abs(diff) >= 3.5 else "low",
                "home" if lean == home else "away")

    # Total: both offenses vs defenses, explosives, red zone, plus the drive-scoring total.
    if total is not None:
        d = proj["total"] - total
        both_off = len(edges[home]) + len(edges[away])
        both_def = len(walls[home]) + len(walls[away])
        side = None
        if d >= 3.0 and both_off >= both_def:
            side = "over"
        elif d <= -3.0 and both_def >= both_off:
            side = "under"
        if side:
            why = [f"Drive-scoring total {proj['total']} vs market {total} ({d:+.1f}); about {proj['drives']} drives a team."]
            pool = (edges[home] + edges[away]) if side == "over" else (walls[home] + walls[away])
            for m in sorted(pool, key=lambda m: -abs(m["gap"]))[:3]:
                why.append(f"{m['unit']}: {m['offense']} offense #{m['offRank']} vs {m['defense']} defense #{m['defRank']}.")
            why.append(f"O/U this season: {home} {T[home]['ouSeason']['w']}-{T[home]['ouSeason']['l']}, "
                       f"{away} {T[away]['ouSeason']['w']}-{T[away]['ouSeason']['l']}.")
            add("total", side, f"{side.title()} {total}", why, "medium" if abs(d) >= 5 else "low", side)

    # Team totals: one offense with a clear scoring edge.
    for t in (home, away):
        opp = away if t == home else home
        strong = [m for m in edges[t] if m["key"] in ("ppd", "rz_td", "pass_epa", "rush_epa", "explosive")]
        if len(strong) >= 2:
            pts = proj["home"] if t == home else proj["away"]
            why = [f"{m['unit']}: {t} offense #{m['offRank']} vs {opp} defense #{m['defRank']}." for m in strong[:3]]
            why.append(f"Drive-scoring view puts {t} at {pts} points.")
            add("team total", t, f"{t} team total over (check the book; about {pts})", why, "low", "over", pts)

    return out


# ---------------- props: player vs the defense he faces ----------------

POS_GROUP = {"WR": "WR", "TE": "TE", "RB": "RB", "FB": "RB", "QB": "QB"}
PROP_STATS = {
    # key: (label, player field, defense field, positions, usage field, usage minimum per game)
    "rec_yds": ("Receiving yards", "ryd", "ryd", ("WR", "TE", "RB"), "tg", 4.0),
    "receptions": ("Receptions", "rec", "rec", ("WR", "TE", "RB"), "tg", 4.0),
    "rush_yds": ("Rushing yards", "rush_yd", "rush_yd", ("RB",), "car", 8.0),
    "pass_yds": ("Passing yards", "pass_yd", "pass_yd", ("QB",), "att", 18.0),
    "td": ("Anytime TD", "td", "td", ("WR", "TE", "RB"), "rz", 1.0),
}
OVER_RANK, UNDER_RANK = 8, 25      # rank 1 = the defense that allows the most of this stat to this position


def load_positions(season):
    try:
        rows = csv.DictReader(io.open(fetch(ROSTER_URL.format(season=season), f"roster_{season}.csv", 24),
                                      encoding="utf-8"))
        return {r["gsis_id"]: POS_GROUP.get(r.get("position") or "", r.get("position")) for r in rows if r.get("gsis_id")}
    except Exception as e:          # props degrade to nothing; the rest of the notes still build
        print(json.dumps({"warning": f"roster load failed: {e}"}))
        return {}


def player_games(plays, pos):
    """Per player, per game: targets, catches, yards, carries, rush yards, pass yards, attempts, red-zone chances, TDs."""
    P = {}

    def slot(pid, name, team, gid, week, opp):
        p = P.setdefault(pid, {"name": name, "team": team, "pos": pos.get(pid), "games": {}})
        p["name"] = p["name"] or name
        return p["games"].setdefault(gid, {"week": week, "opp": opp, "tg": 0, "rec": 0, "ryd": 0.0, "car": 0,
                                           "rush_yd": 0.0, "pass_yd": 0.0, "att": 0, "rz": 0, "td": 0, "long": 0.0})
    for r in plays:
        if not is_play(r):
            continue
        gid, wk, t, d = r["game_id"], r["week"], r["posteam"], r["defteam"]
        rz = (fnum(r["yardline_100"]) or 100) <= 20
        if fnum(r["pass_attempt"]) == 1 and r["receiver_player_id"]:
            x = slot(r["receiver_player_id"], r["receiver_player_name"], t, gid, wk, d)
            x["tg"] += 1
            x["rz"] += 1 if rz else 0
            if fnum(r["complete_pass"]) == 1:
                x["rec"] += 1
                y = fnum(r["receiving_yards"]) or 0
                x["ryd"] += y
                x["long"] = max(x["long"], y)
            if fnum(r["pass_touchdown"]) == 1:
                x["td"] += 1
        if r["play_type"] == "run" and r["rusher_player_id"] and fnum(r["qb_scramble"]) != 1:
            x = slot(r["rusher_player_id"], r["rusher_player_name"], t, gid, wk, d)
            x["car"] += 1
            x["rush_yd"] += fnum(r["rushing_yards"]) or 0
            x["rz"] += 1 if rz else 0
            if fnum(r["rush_touchdown"]) == 1:
                x["td"] += 1
        if fnum(r["qb_dropback"]) == 1 and r["passer_player_id"] and fnum(r["pass_attempt"]) == 1:
            x = slot(r["passer_player_id"], r["passer_player_name"], t, gid, wk, d)
            x["att"] += 1
            x["pass_yd"] += fnum(r["passing_yards"]) or 0
    return P


def rank_words(rank, n=32):
    """Allowed-stat rank (1 = allows the most) in plain words. "#32 most" read as the most when it is the fewest
    (Zack, 2026-10-22: R.Harvey under looked like a mistake against a defense ranked 32nd vs RBs)."""
    if rank == 1:
        return "the most"
    if rank >= n:
        return "the fewest"
    return f"#{rank} most" if rank <= n // 2 else f"#{n + 1 - rank} fewest"


def defense_vs_position(PG, weeks=None):
    """What each defense allows per game to WRs, TEs, RBs and QBs; rank 1 = allows the most."""
    tot = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    games = defaultdict(set)
    for p in PG.values():
        grp = p["pos"]
        if grp not in ("WR", "TE", "RB", "QB"):
            continue
        for gid, x in p["games"].items():
            if weeks is not None and x["week"] not in weeks:
                continue
            games[x["opp"]].add(gid)
            for k in ("tg", "rec", "ryd", "car", "rush_yd", "pass_yd", "att", "td"):
                tot[x["opp"]][grp][k] += x[k]
    out = {}
    for d, by in tot.items():
        n = len(games[d]) or 1
        out[d] = {grp: {k: v / n for k, v in st.items()} for grp, st in by.items()}
        out[d]["games"] = n
    ranks_ = {}
    league = {}
    for grp in ("WR", "TE", "RB", "QB"):
        for k in ("tg", "rec", "ryd", "rush_yd", "pass_yd", "td"):
            vals = sorted(((d, v.get(grp, {}).get(k, 0.0)) for d, v in out.items()), key=lambda x: -x[1])
            league[(grp, k)] = sum(v for _, v in vals) / len(vals) if vals else 0
            for i, (d, _) in enumerate(vals):
                ranks_[(d, grp, k)] = i + 1
    return out, ranks_, league


def prop_angles(g, PG, DV, DR, LG, M, status, qbs, last3):
    home, away = g["home_team"], g["away_team"]
    out = []
    for t in (home, away):
        opp = away if t == home else home
        mine = [dict(p, pid=pid) for pid, p in PG.items() if p["team"] == t and p["pos"] in ("WR", "TE", "RB", "QB")]
        for p in mine:
            st = status_of(p["name"], status)
            if st in OUT_STATUSES:
                continue
            gs = list(p["games"].values())
            if not gs:
                continue
            if p["pos"] == "QB":
                q = qbs.get(t) or ""
                last = q.replace(" Jr.", "").replace(" III", "").replace(" II", "").split()[-1] if q else ""
                if not (p["name"] and p["name"].split(".")[-1] == last and p["name"][0] == q[:1]):
                    continue                     # only tonight's listed starter
            n = len(gs)
            if n < 3:
                continue                         # too few games to say anything about the player
            l3 = [x for x in gs if x["week"] in last3]
            for key, (label, pf, df, poss, uf, umin) in PROP_STATS.items():
                if p["pos"] not in poss:
                    continue
                if sum(x[uf] for x in gs) / n < umin:
                    continue
                if key == "td":
                    season = sum(x["td"] for x in gs) / n                   # TDs a game (rate)
                    l3v = (sum(x["td"] for x in l3) / len(l3)) if l3 else None
                else:
                    season = sum(x[pf] for x in gs) / n
                    l3v = (sum(x[pf] for x in l3) / len(l3)) if l3 else None
                if season <= 0:
                    continue
                grp = p["pos"]
                raw = DV.get(opp, {}).get(grp, {}).get(df)
                lg = LG.get((grp, df)) or 0
                dg = DV.get(opp, {}).get("games", 0)
                allowed = shrink(raw, lg, dg) if raw is not None else None   # six games is a small sample
                rank = DR.get((opp, grp, df))
                if allowed is None or not lg or rank is None:
                    continue
                base = season if (l3v is None or len(l3) < 2) else 0.6 * season + 0.4 * l3v
                factor = 1 + 0.6 * (allowed / lg - 1)                   # 60% of the defense's gap from average
                if key == "td":
                    # TD counts are small: cap the adjustment and turn the rate into a chance to score at least once
                    factor = min(max(factor, 0.7), 1.4)
                    expected = 1 - math.exp(-base * factor)
                    p_base = 1 - math.exp(-base)
                    adj = expected / p_base - 1 if p_base > 0 else 0
                else:
                    expected = base * factor
                    adj = factor - 1
                side = None
                if rank <= OVER_RANK and adj >= 0.10:
                    side = "over"
                elif rank >= UNDER_RANK and adj <= -0.10 and key != "td":
                    side = "under"
                if key == "td" and (allowed < 1.3 * lg or expected < 0.30):
                    side = None                          # only clear red-zone spots with a real chance to score
                if not side:
                    continue
                strong = rank <= 4 or rank >= 29
                show = (lambda v: f"{v:.2f}") if key == "td" else (lambda v: f"{v:.1f}" if key == "receptions" else f"{v:.0f}")
                num = (lambda v: f"{v:.2f}") if key in ("td", "receptions") else (lambda v: f"{v:.0f}")
                what = "TDs" if key == "td" else label.lower()
                head = (f"{p['name']} ({grp}): {show(season)} "
                        f"{'TDs a game' if key == 'td' else label.lower() + ' a game'} over {n} games")
                if l3v is not None and len(l3) >= 2:
                    head += f", {show(l3v)} the last {len(l3)}"
                why = [head + ".",
                       f"{opp} allows {num(raw)} {what} a game to {grp}s, "
                       f"{rank_words(rank)} in the league "
                       f"(average {num(lg)}; {num(allowed)} after weighting for {dg} games)."]
                against = False
                if l3v is not None and len(l3) >= 2 and key != "td":
                    trend = l3v / season - 1
                    if abs(trend) >= 0.25:
                        against = (trend > 0) != (side == "over")
                        why.append(f"Recent form: last {len(l3)} games {'up' if trend > 0 else 'down'} "
                                   f"{abs(trend) * 100:.0f}% on his season average"
                                   + (" (works against it)." if against else " (supports it)."))
                if key == "td":
                    why.append(f"Chance to score: about {expected * 100:.0f}% vs {p_base * 100:.0f}% on his season rate.")
                if st == "Questionable":
                    why.append(f"{p['name']} is Questionable now; check the inactive list.")
                if against and not strong:
                    continue                             # a lean that his own recent games argue against
                out.append({"player": p["name"], "pid": p["pid"], "team": t, "opp": opp, "pos": grp, "stat": key, "label": label,
                            "side": side, "projection": round(expected, 2 if key == "td" else 1),
                            "seasonAvg": round(season, 2), "last3Avg": round(l3v, 2) if l3v is not None else None,
                            "oppAllowed": round(raw, 2), "oppAllowedWeighted": round(allowed, 2), "oppRank": rank, "leagueAvg": round(lg, 2),
                            "adj": round(adj, 3), "strength": "strong" if strong and not against else "lean", "status": st,
                            "why": why, "games": n})
        # Unit-level angles from the tape that have no per-position stat
        keys = {m["key"]: m for m in M[t] if m["kind"] == "offense edge"}
        walls = {m["key"]: m for m in M[t] if m["kind"] == "defense edge"}
        if "deep_epa" in keys:
            rec = sorted([dict(p, pid=pid) for pid, p in PG.items() if p["team"] == t and p["pos"] in ("WR", "TE")
                          and status_of(p["name"], status) not in OUT_STATUSES], key=lambda p: -sum(
                              x["tg"] for x in p["games"].values()))
            for p in rec:
                gs = list(p["games"].values())
                tg = sum(x["tg"] for x in gs)
                longs = [x["long"] for x in gs]
                if tg / max(len(gs), 1) >= 3 and max(longs or [0]) >= 25:
                    m = keys["deep_epa"]
                    out.append({"player": p["name"], "pid": p["pid"], "team": t, "opp": opp, "pos": p["pos"], "stat": "long",
                                "label": "Longest reception", "side": "over",
                                "projection": None, "seasonAvg": round(sum(longs) / len(longs), 1), "last3Avg": None,
                                "oppAllowed": None, "oppRank": m["defRank"], "leagueAvg": None, "adj": None,
                                "strength": "strong" if m["strong"] else "lean", "status": status_of(p["name"], status),
                                "why": [f"{p['name']}: longest catch averages {sum(longs) / len(longs):.0f} yards a game, "
                                        f"best {max(longs):.0f}.",
                                        f"Deep passing: {t} offense #{m['offRank']} vs {opp} defense #{m['defRank']} "
                                        f"on throws of 20+ air yards (small sample)."], "games": len(gs)})
                    break
        if "sack" in walls:
            m = walls["sack"]
            out.append({"player": qbs.get(t), "team": t, "opp": opp, "pos": "QB", "stat": "sacks",
                        "label": "Sacks taken", "side": "over", "projection": None, "seasonAvg": None,
                        "last3Avg": None, "oppAllowed": m["defVal"], "oppRank": m["defRank"], "leagueAvg": None,
                        "adj": None, "strength": "strong" if m["strong"] else "lean", "status": None,
                        "why": [f"{t} line ranks #{m['offRank']} in sack rate allowed ({fmt('sack', m['offVal'])}); "
                                f"{opp} ranks #{m['defRank']} getting home ({fmt('sack', m['defVal'])})."],
                        "games": None})
    out.sort(key=prop_score, reverse=True)
    return out[:8]


def prop_score(x):
    """Order props: strong first, then the size of the matchup adjustment (capped so TDs cannot crowd the list)."""
    return (x["strength"] == "strong", min(abs(x["adj"] if x["adj"] is not None else 0.12), 0.35 if x["stat"] == "td" else 0.6))


def game_note(g, S, S3, R, R3, plays, games, season, PG=None, DV=None, DR=None, LG=None):
    home, away = g["home_team"], g["away_team"]
    kick = f"{g['gameday']}T{g.get('gametime') or '13:00'}"
    kick_utc = (datetime.fromisoformat(kick) + timedelta(hours=4)).strftime("%Y-%m-%d")   # ET -> UTC date
    lines = edge_lines(home, away, kick_utc)
    hs = g["spread_line"]
    home_fav = (lines.get("spread", {}).get("line") or (-hs if hs is not None else 0)) < 0
    T = {home: trends(games, home, season, {"home": True, "fav": home_fav}),
         away: trends(games, away, season, {"home": False, "fav": not home_fav})}
    M = {home: mismatches(R, S, home, away), away: mismatches(R, S, away, home)}
    last3 = sorted({r["week"] for r in plays})[-3:]
    qbs = {home: g.get("home_qb_name"), away: g.get("away_qb_name")}
    P = {t: players(plays, t, starter=qbs[t]) for t in (home, away)}
    P3 = {t: players(plays, t, set(last3), starter=qbs[t]) for t in (home, away)}
    # Team numbers are only as good as the QB who produced them. Flag when tonight's starter threw less than 60%
    # of the team's dropbacks (missed time, new starter) or the season starter is out.
    qbflag = {}
    for t in (home, away):
        q = P[t]["qb"]
        if q and (q.get("shareOfTeamDropbacks") or 0) < 0.6:
            qbflag[t] = (f"{qbs[t]} has {q['dropbacks']} of {t}'s dropbacks "
                         f"({(q.get('shareOfTeamDropbacks') or 0) * 100:.0f}%): {t}'s season offense numbers are "
                         f"mostly another QB. Weigh the last-3 column and the market more.")
    proj = projection(S, home, away)
    ctx = edge_context(home, away)
    status = injury_status(ctx["injuries"])
    for t in (home, away):
        for grp in ("receivers", "rushers"):
            for r in P[t][grp] + P3[t][grp]:
                r["status"] = status_of(r["name"], status)
    sugg = suggestions(g, S, R, M, P, proj, lines, T, status)
    kept = []
    for x in sugg:
        if x["market"] == "player":
            st = status_of(x["side"], status)
            if st in ("Out", "Injured Reserve", "Doubtful", "Suspended", "PUP"):
                continue                                   # the player is not expected to play
            if st == "Questionable":
                x["why"].append(f"{x['side']} is Questionable now; check the inactive list.")
                x["confidence"] = "low"
        kept.append(x)
    sugg = kept
    props = prop_angles(g, PG, DV, DR, LG, M, status, qbs, set(last3)) if PG else []
    for x in props:
        if x["team"] in qbflag and x["stat"] not in ("sacks",):
            x["why"].append("Caution: " + qbflag[x["team"]])
            if x["strength"] == "strong":
                x["strength"] = "lean"
    for x in sugg:
        hit = [t for t in qbflag if t in (x["side"], home, away)]
        if qbflag and (x["market"] in ("spread", "total") or x["side"] in qbflag or
                       any(x["label"].startswith(n) for n in [r["name"] for t in qbflag for r in P[t]["receivers"] + P[t]["rushers"]])):
            x["why"].append("Caution: " + " ".join(qbflag.values()))
            x["confidence"] = "low"
    units = {}
    for t in (home, away):
        units[t] = {side: {k: {"value": S[t][side].get(k), "rank": R[t][side].get(k),
                               "last3": S3.get(t, {}).get(side, {}).get(k),
                               "last3Rank": R3.get(t, {}).get(side, {}).get(k)} for k, _, _ in UNITS}
                    for side in ("off", "def")}
        units[t]["games"] = S[t]["off"]["games"]
        units[t]["passRate"] = S[t]["off"].get("pass_rate")
    ctx = edge_context(home, away)
    ln = {k: {"line": v.get("line"), "prices": v.get("p"), "pin": v.get("pin"), "book": v.get("book"), "t": v.get("t")}
          for k, v in lines.items()}
    return {
        "id": g["game_id"], "kickoffET": kick, "home": home, "away": away,
        "homeName": NAMES.get(home), "awayName": NAMES.get(away),
        "qbs": {home: g.get("home_qb_name"), away: g.get("away_qb_name")},
        "rest": {home: g.get("home_rest"), away: g.get("away_rest")},
        "roof": g.get("roof"), "surface": g.get("surface"), "injuries": ctx["injuries"], "weather": ctx["weather"],
        "lines": ln, "nflverseLine": {"homeSpread": -hs if hs is not None else None, "total": g["total_line"]},
        "projection": proj, "qbFlags": qbflag, "units": units, "mismatches": M, "trends": T, "players": P, "playersLast3": P3,
        "last3Weeks": last3, "suggestions": sugg, "props": props,
    }


def run_nfl(days=7, today=None):
    today = today or datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-5))).date()
    games = load_games()
    upcoming = [g for g in games if g["result"] is None and g["gameday"]
                and today <= date.fromisoformat(g["gameday"]) <= today + timedelta(days=days)]
    if not upcoming:
        print(json.dumps({"nfl": 0, "note": "no NFL games in window"}))
        return None
    season = upcoming[0]["season"]
    plays = load_pbp(season)
    S = unit_stats(plays)
    weeks = sorted({r["week"] for r in plays})
    S3 = unit_stats(plays, set(weeks[-3:]))
    R, R3 = ranks(S), ranks(S3)
    PG = player_games(plays, load_positions(season))
    DV, DR, LG = defense_vs_position(PG)
    notes = []
    for g in sorted(upcoming, key=lambda g: (g["gameday"], g.get("gametime") or "")):
        if g["home_team"] not in S or g["away_team"] not in S:
            continue
        notes.append(game_note(g, S, S3, R, R3, plays, games, season, PG, DV, DR, LG))
    top = [dict(p, gameId=n["id"]) for n in notes for p in n["props"] if p["adj"] is not None]
    top.sort(key=prop_score, reverse=True)
    picked, per_pos = [], defaultdict(int)
    for p in top:                                   # at most 3 a position and 2 TD props, so one group cannot fill it
        cap = 2 if p["stat"] == "td" else 3
        key = "TD" if p["stat"] == "td" else p["pos"]
        if per_pos[key] < cap:
            picked.append(p)
            per_pos[key] += 1
        if len(picked) == 10:
            break
    top = picked
    slate = {"sport": "NFL", "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "topProps": top[:10],
             "season": season, "throughWeek": max(weeks), "games": notes,
             "label": "Matchup notes: information and suggestions, not official EDGE plays. No stake, no reads, "
                      "never traded. Graded separately (matchups/notes.jsonl)."}
    OUT.mkdir(exist_ok=True)
    (OUT / "nfl").mkdir(exist_ok=True)
    (OUT / "nfl" / f"{today.isoformat()}.json").write_text(json.dumps(slate, indent=1, default=str))
    (OUT / "latest_nfl.json").write_text(json.dumps(slate, default=str))
    try:
        slate["record"] = json.loads((OUT / "record.json").read_text())
        (OUT / "latest_nfl.json").write_text(json.dumps(slate, default=str))
    except (OSError, ValueError):
        pass
    log_notes(slate)
    print(json.dumps({"nfl": len(notes), "suggestions": sum(len(n["suggestions"]) for n in notes),
                      "props": sum(len(n["props"]) for n in notes),
                      "throughWeek": max(weeks)}))
    return slate


# ---------------- log and grade (separate from grade.py) ----------------

def log_notes(slate):
    p = OUT / "notes.jsonl"
    seen = set()
    if p.exists():
        for line in p.open():
            try:
                seen.add(json.loads(line)["noteId"])
            except (ValueError, KeyError):
                pass
    with p.open("a") as f:
        for g in slate["games"]:
            for x in g.get("props", []):
                nid = f"NFL|{g['id']}|prop|{x.get('pid') or x['player']}|{x['stat']}|{x['side']}"
                if nid in seen:
                    continue
                seen.add(nid)
                f.write(json.dumps({"noteId": nid, "sport": "NFL", "gameId": g["id"], "kickoffET": g["kickoffET"],
                                    "home": g["home"], "away": g["away"], "market": "prop", "stat": x["stat"],
                                    "player": x["player"], "pid": x.get("pid"), "team": x["team"], "side": x["side"],
                                    "label": f"{x['player']} {x['label']} {x['side']}", "strength": x["strength"],
                                    "lineAtNote": note_line(x), "gradeBasis": "matchup projection (no book line)",
                                    "seasonAvg": x["seasonAvg"], "oppRank": x["oppRank"], "notedAt": slate["generated"],
                                    "why": x["why"], "result": None, "actual": None}) + "\n")
            for s in g["suggestions"]:
                what = s["label"].split(" (")[0] if s["market"] == "player" or s["market"] == "team total" else ""
                nid = f"NFL|{g['id']}|{s['market']}|{s['side']}|{what}"
                if nid in seen:
                    continue           # first note on a game/market/side stands; later reruns do not restamp
                seen.add(nid)
                f.write(json.dumps({"noteId": nid, "sport": "NFL", "gameId": g["id"], "kickoffET": g["kickoffET"],
                                    "home": g["home"], "away": g["away"], "market": s["market"], "side": s["side"],
                                    "label": s["label"], "confidence": s["confidence"], "lineAtNote": s["lineAtNote"],
                                    "notedAt": slate["generated"], "why": s["why"], "memory": s["memory"],
                                    "projection": g["projection"], "result": None, "closeLine": None,
                                    "lineMove": None}) + "\n")


def note_line(x):
    """The number a prop note is graded against: the matchup projection, or for longest reception (no projection)
    the season average the note quotes (health check 2026-10-23: these notes were written with no number and could
    never settle)."""
    if x.get("projection") is not None:
        return x["projection"]
    return x.get("seasonAvg") if x.get("stat") == "long" else None


GRADE_FIELD = {k: v[1] for k, v in PROP_STATS.items()}
GRADE_FIELD["long"] = "long"


def team_total_line(r):
    """A team-total note's number: lineAtNote, or for notes written before 2026-10-23 the 'about N' in its label."""
    if r.get("lineAtNote") is not None:
        return r["lineAtNote"]
    m = re.search(r"about (-?[0-9.]+)", r.get("label") or "")
    return float(m.group(1)) if m else None


def grade():
    p = OUT / "notes.jsonl"
    if not p.exists():
        print(json.dumps({"graded": 0}))
        return
    games = {g["game_id"]: g for g in load_games()}
    rows = [json.loads(l) for l in p.open() if l.strip()]
    n = 0
    PGcache = {}
    for r in rows:
        if r.get("result") is None and r["market"] == "prop" and r.get("stat") in GRADE_FIELD:
            g = games.get(r["gameId"])
            if r.get("lineAtNote") is None and r["stat"] == "long":
                r["lineAtNote"] = r.get("seasonAvg")      # notes written before 2026-10-23 had no number
            if not g or g["result"] is None or r.get("lineAtNote") is None:
                continue
            if g["season"] not in PGcache:
                PGcache[g["season"]] = player_games(load_pbp(g["season"]), {})
            PGs = PGcache[g["season"]]
            pid = r.get("pid") or next((k for k, v in PGs.items() if v["name"] == r.get("player")
                                        and v["team"] == r.get("team") and r["gameId"] in v["games"]), None)
            pg = PGs.get(pid, {}).get("games", {}).get(r["gameId"]) if pid else None
            if pg is None:
                # Final game, play-by-play loaded for it, and no play for him: inactive or no touch. Void it, as a
                # book voids an inactive player's prop, so it stops sitting ungraded (2026-10-26: 5 week-7 notes).
                if any(r["gameId"] in v["games"] for v in PGs.values()):
                    r["result"], r["voidReason"] = "void", "no play-by-play record (inactive or no touch)"
                    n += 1
                continue                                  # not in the play-by-play yet
            r["pid"] = pid
            actual = pg[GRADE_FIELD[r["stat"]]]
            r["actual"] = actual
            if r["stat"] == "td":
                hit = actual > 0
                r["result"] = "W" if hit == (r["side"] == "over") else "L"
            else:
                d = actual - r["lineAtNote"]
                r["result"] = "P" if d == 0 else ("W" if (d > 0) == (r["side"] == "over") else "L")
            n += 1
            continue
        if r.get("result") is None and r["market"] == "team total":
            g = games.get(r["gameId"])
            L = team_total_line(r)
            if not g or g["result"] is None or L is None or g.get("home_score") is None:
                continue
            pts = g["home_score"] if r["side"] == r["home"] else g["away_score"]
            r["lineAtNote"], r["actual"] = L, pts
            d = pts - L                                   # team-total notes are overs
            r["result"] = "P" if d == 0 else ("W" if d > 0 else "L")
            n += 1
            continue
        if r.get("result") is not None or r["market"] not in ("spread", "total"):
            continue
        g = games.get(r["gameId"])
        if not g or g["result"] is None:
            continue
        lines = edge_lines(r["home"], r["away"],
                           (datetime.fromisoformat(r["kickoffET"]) + timedelta(hours=4)).strftime("%Y-%m-%d"))
        close = lines.get(r["market"], {}).get("line")
        L = r["lineAtNote"]
        if r["market"] == "spread" and L is not None:
            home_margin = g["result"]
            m = home_margin + L if r["side"] == r["home"] else -home_margin - L
            r["result"] = "P" if m == 0 else ("W" if m > 0 else "L")
            if close is not None:
                r["closeLine"] = close
                r["lineMove"] = (L - close) if r["side"] == r["home"] else (close - L)   # + = note beat the close
        elif r["market"] == "total" and L is not None:
            d = g["total"] - L
            r["result"] = "P" if d == 0 else ("W" if (d > 0) == (r["side"] == "over") else "L")
            if close is not None:
                r["closeLine"] = close
                r["lineMove"] = (close - L) if r["side"] == "over" else (L - close)
        n += 1
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    def rec(rs):
        return f"{sum(r['result'] == 'W' for r in rs)}-{sum(r['result'] == 'L' for r in rs)}"
    done = [r for r in rows if r.get("result") in ("W", "L", "P")]
    props = [r for r in done if r["market"] == "prop"]
    game = [r for r in done if r["market"] != "prop"]
    mv = [r["lineMove"] for r in game if r.get("lineMove") is not None]
    summary = {"graded": n, "settled": len(done), "void": sum(r.get("result") == "void" for r in rows),
               "suggestions": rec(game), "props": rec(props),
               "propsStrong": rec([r for r in props if r.get("strength") == "strong"]),
               "meanLineMove": round(sum(mv) / len(mv), 2) if mv else None}
    (OUT / "record.json").write_text(json.dumps(summary))
    print(json.dumps(summary))


# ---------------- page ----------------

def html(path=None):
    slate = json.loads((OUT / "latest_nfl.json").read_text())
    tpl = (ROOT / "matchups_page.html").read_text()
    page = tpl.replace("/*__DATA__*/null", json.dumps(slate, default=str))
    dest = Path(path) if path else OUT / "nfl.html"
    dest.write_text(page)
    print(dest)


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd = a[0] if a else "nfl"
    if cmd == "nfl":
        d = int(a[a.index("--days") + 1]) if "--days" in a else 7
        run_nfl(d)
    elif cmd == "grade":
        grade()
    elif cmd == "html":
        html(a[1] if len(a) > 1 else None)
    else:
        print(__doc__)
