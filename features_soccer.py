#!/usr/bin/env python3
"""EDGE soccer feature store (EPL, La Liga, Bundesliga, Serie A, Ligue 1). Every pre-match data point the desk can
get, in the same form for history (training) and upcoming matches (live). The learner decides what matters.

  python3 features_soccer.py history    build stats/features/soccer_history.json from stats/history/soccer

Data: Understat (goals and xG for every match; expected points from its post-match forecast of PAST matches only),
football-data (Pinnacle early and closing 1X2 and 2.5-goal prices, plus Bet365, market average and best price
early, for market-disagreement features). Live: Understat current season and this desk's own opening snapshot
(Pinnacle and the US books).
Targets: Pinnacle close minus early no-vig probability for home, draw, and over 2.5.
"""

import csv
import difflib
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HIST = ROOT / "stats" / "history" / "soccer"
OUT = ROOT / "stats" / "features" / "soccer_history.json"
LEAGUES = {"EPL": ("EPL", "E0"), "LaLiga": ("La_liga", "SP1"), "Bundesliga": ("Bundesliga", "D1"),
           "SerieA": ("Serie_A", "I1"), "Ligue1": ("Ligue_1", "F1")}


def shin3(a, b, c):
    import fair
    am = lambda o: round((o - 1) * 100) if o >= 2 else round(-100 / (o - 1))
    p = fair.probs({"h": am(a), "d": am(b), "a": am(c)}, ["h", "d", "a"])
    return p["h"], p["d"], p["a"]


def shin2(a, b):
    import fair
    am = lambda o: round((o - 1) * 100) if o >= 2 else round(-100 / (o - 1))
    return fair.probs({"o": am(a), "u": am(b)}, ["o", "u"])["o"]


def dec(r, k):
    try:
        v = float(r.get(k) or 0)
        return v if v > 1 else None
    except ValueError:
        return None


class Form:
    """Per-team match history inside one league, updated in date order."""
    def __init__(self):
        self.h = defaultdict(list)

    def add(self, g):
        gh, ga = int(g["goals"]["h"]), int(g["goals"]["a"])
        xh, xa = float(g["xG"]["h"]), float(g["xG"]["a"])
        fc = g.get("forecast") or {}
        w, d, l = (float(fc.get(k, 1 / 3)) for k in ("w", "d", "l"))
        day = g["datetime"][:10]
        for t, gf, gaa, xf, xa_, xp, home in ((g["h"]["title"], gh, ga, xh, xa, 3 * w + d, 1),
                                              (g["a"]["title"], ga, gh, xa, xh, 3 * l + d, 0)):
            pts = 3 if gf > gaa else (1 if gf == gaa else 0)
            self.h[t].append({"day": day, "gf": gf, "ga": gaa, "xf": xf, "xa": xa_, "pts": pts, "xp": xp, "home": home})

    def feats(self, t, day, side):
        H = [x for x in self.h.get(t, []) if x["day"] < day]
        f = {f"{side}_n": float(len(H))}
        if not H:
            return f
        for n in (1, 3, 5, 10, 38):
            G = H[-n:]
            k = len(G)
            f[f"{side}_xf{n}"] = sum(x["xf"] for x in G) / k
            f[f"{side}_xa{n}"] = sum(x["xa"] for x in G) / k
            f[f"{side}_gf{n}"] = sum(x["gf"] for x in G) / k
            f[f"{side}_ga{n}"] = sum(x["ga"] for x in G) / k
            f[f"{side}_luck{n}"] = sum((x["gf"] - x["xf"]) - (x["ga"] - x["xa"]) for x in G) / k
            f[f"{side}_ppg{n}"] = sum(x["pts"] for x in G) / k
            f[f"{side}_xpg{n}"] = sum(x["xp"] for x in G) / k
            f[f"{side}_formgap{n}"] = f[f"{side}_ppg{n}"] - f[f"{side}_xpg{n}"]
        f[f"{side}_tot1"] = H[-1]["gf"] + H[-1]["ga"]
        try:
            d0 = datetime.fromisoformat(H[-1]["day"])
            f[f"{side}_rest"] = float(min((datetime.fromisoformat(day) - d0).days, 14))
        except ValueError:
            pass
        return f


def match_features(form, home, away, day, league, promoted):
    f = {f"lg_{k}": 1.0 if k == league else 0.0 for k in LEAGUES}
    f.update(form.feats(home, day, "h"))
    f.update(form.feats(away, day, "a"))
    f["h_promoted"] = 1.0 if home in promoted else 0.0
    f["a_promoted"] = 1.0 if away in promoted else 0.0
    for k in list(f):
        if k.startswith("h_") and "a_" + k[2:] in f:
            f["d_" + k[2:]] = f[k] - f["a_" + k[2:]]
    f["month"] = float(int(day[5:7]))
    return f


def market_features(f, pin_h, pin_d, pin_a, pin_over, avg=None, b365=None, mx=None):
    f.update({"open_h": pin_h, "open_d": pin_d, "open_a": pin_a})
    if pin_over is not None:
        f["open_over"] = pin_over
    for tag, trio in (("avg", avg), ("b365", b365), ("max", mx)):
        if trio:
            f[f"{tag}_minus_pin_h"] = trio[0] - pin_h
            f[f"{tag}_minus_pin_d"] = trio[1] - pin_d
            f[f"{tag}_minus_pin_a"] = trio[2] - pin_a
    return f


def build_history():
    rows = []
    for league, (us, fd) in LEAGUES.items():
        FD = defaultdict(list)
        for p in sorted(HIST.glob(f"fd_{fd}_*.csv")):
            for r in csv.DictReader(open(p, encoding="utf-8-sig", errors="replace")):
                try:
                    d = datetime.strptime(r["Date"], "%d/%m/%Y" if len(r["Date"]) > 8 else "%d/%m/%y").date().isoformat()
                except ValueError:
                    continue
                FD[d].append(r)
        form, prev = Form(), set()
        for p in sorted(HIST.glob(f"understat_{us}_*.json")):
            dates = sorted([g for g in json.loads(p.read_text())["dates"] if g.get("isResult")], key=lambda g: g["datetime"])
            teams = {g["h"]["title"] for g in dates} | {g["a"]["title"] for g in dates}
            promoted = teams - prev if prev else set()
            for g in dates:
                day = g["datetime"][:10]
                h, a = g["h"]["title"], g["a"]["title"]
                best, bs = None, 0.0
                for r in FD.get(day, []):
                    sc = (difflib.SequenceMatcher(None, h.lower(), r["HomeTeam"].lower()).ratio()
                          + difflib.SequenceMatcher(None, a.lower(), r["AwayTeam"].lower()).ratio())
                    if sc > bs:
                        best, bs = r, sc
                if best is not None and bs > 1.0:
                    E = [dec(best, k) for k in ("PSH", "PSD", "PSA")]
                    C = [dec(best, k) for k in ("PSCH", "PSCD", "PSCA")]
                    if all(E) and all(C):
                        eh, ed, ea = shin3(*E)
                        ch, cd, ca = shin3(*C)
                        eo = co = None
                        EO, CO = [dec(best, k) for k in ("P>2.5", "P<2.5")], [dec(best, k) for k in ("PC>2.5", "PC<2.5")]
                        if all(EO) and all(CO):
                            eo, co = shin2(*EO), shin2(*CO)
                        trio = lambda ks: shin3(*[dec(best, k) for k in ks]) if all(dec(best, k) for k in ks) else None
                        f = match_features(form, h, a, day, league, promoted)
                        market_features(f, eh, ed, ea, eo, trio(("AvgH", "AvgD", "AvgA")) or trio(("BbAvH", "BbAvD", "BbAvA")),
                                        trio(("B365H", "B365D", "B365A")), trio(("MaxH", "MaxD", "MaxA")) or trio(("BbMxH", "BbMxD", "BbMxA")))
                        rows.append({"date": g["datetime"], "league": league, "home": h, "away": a, "f": f,
                                     "y_home": ch - eh, "y_draw": cd - ed, "y_away": ca - ea,
                                     "y_over": (co - eo) if eo is not None else None})
                form.add(g)
            prev = teams
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"built": datetime.now(timezone.utc).isoformat(), "rows": rows}, separators=(",", ":")))
    return len(rows)


CACHE = ROOT / "stats" / "features" / "understat_cache.json"
CACHE_H = 6


def understat_cached(us, y):
    """Understat league data, refetched at most every CACHE_H hours (fast runs come every 15 minutes)."""
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    key = f"{us}/{y}"
    rec = cache.get(key)
    now = datetime.now(timezone.utc)
    if rec and (now - datetime.fromisoformat(rec["at"])).total_seconds() < CACHE_H * 3600:
        return rec["dates"]
    try:
        out = subprocess.run(["curl", "-s", "--compressed", "-m", "40", "-H", "X-Requested-With: XMLHttpRequest",
                              f"https://understat.com/getLeagueData/{us}/{y}"], capture_output=True).stdout
        dates = sorted([g for g in json.loads(out)["dates"]], key=lambda g: g["datetime"])
    except Exception as exc:  # noqa: BLE001
        print("understat", us, y, exc)
        return rec["dates"] if rec else None
    slim = [{k: g.get(k) for k in ("datetime", "isResult", "h", "a", "goals", "xG", "forecast")} for g in dates]
    cache[key] = {"at": now.isoformat(), "dates": slim}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, separators=(",", ":")))
    return slim


def live_form(year):
    """Form objects per league from Understat: last season (for early-season windows) then this season."""
    forms = {}
    for league, (us, _) in LEAGUES.items():
        form, teams_prev, teams_cur = Form(), set(), set()
        for y in (year - 1, year):
            dates = understat_cached(us, y)
            if dates is None:
                continue
            names = {g["h"]["title"] for g in dates} | {g["a"]["title"] for g in dates}
            if y == year - 1:
                teams_prev = names
            else:
                teams_cur = names
            for g in dates:
                if g.get("isResult"):
                    form.add(g)
        forms[league] = (form, teams_cur - teams_prev if teams_prev else set())
    return forms


if __name__ == "__main__":
    print("history rows", build_history())
