#!/usr/bin/env python3
"""EDGE NBA feature store. Pre-game data points for every past game (training) and upcoming game (live), same form.

  python3 features_nba.py history     build stats/features/nba_history.json

Data: ESPN results and DraftKings open/close lines (stats/nba_games.json), the stats_more.py ratings (walk-forward).
Per team, before the game: scoring for/against and margin at 3/5/10/season windows, results against the closing
spread (how the market has misjudged the team lately), against the closing total, rest, back-to-back, games in the
last 4 and 7 nights, road-trip length, time-zone travel since the last game; plus the ratings' gaps and the opening
market itself. Targets: home spread line, total line and home win probability, close minus open.
"""

import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "features" / "nba_history.json"
TZ = {"Celtics": -5, "Nets": -5, "Knicks": -5, "76ers": -5, "Raptors": -5, "Bulls": -6, "Cavaliers": -5, "Pistons": -5,
      "Pacers": -5, "Bucks": -6, "Hawks": -5, "Hornets": -5, "Heat": -5, "Magic": -5, "Wizards": -5, "Nuggets": -7,
      "Timberwolves": -6, "Thunder": -6, "Trail Blazers": -8, "Jazz": -7, "Warriors": -8, "Clippers": -8, "Lakers": -8,
      "Suns": -7, "Kings": -8, "Mavericks": -6, "Rockets": -6, "Grizzlies": -6, "Pelicans": -6, "Spurs": -6}


def nick(name):
    for k in TZ:
        if (name or "").endswith(k):
            return k
    return (name or "").split()[-1]


def day_of(s):
    return (datetime.fromisoformat(s.replace("Z", "+00:00")) - timedelta(hours=6)).date()


def novig2(a, b):
    imp = lambda p: 100 / (p + 100) if p > 0 else -p / (-p + 100)
    x, y = imp(a), imp(b)
    return x / (x + y)


class Book:
    """Per-team game log built in date order from final games."""
    def __init__(self):
        self.log = defaultdict(list)

    def add(self, g):
        L = g.get("lines") or {}
        sc, tc = L.get("spreadClose"), L.get("totalClose")
        d = day_of(g["date"])
        for side, t, opp, pf, pa in (("home", g["home"], g["away"], g["hs"], g["as"]), ("away", g["away"], g["home"], g["as"], g["hs"])):
            ats = None
            if sc is not None:
                line = sc if side == "home" else -sc
                ats = (pf - pa) + line
            self.log[nick(t)].append({"day": d, "pf": pf, "pa": pa, "home": side == "home", "ats": ats,
                                      "ou": (pf + pa - tc) if tc is not None else None, "venue": nick(g["home"])})

    def feats(self, t, d, side):
        H = [x for x in self.log.get(nick(t), []) if x["day"] < d]
        f = {f"{side}_gp": float(len(H))}
        for n in (3, 5, 10, 82):
            G = H[-n:]
            if not G:
                continue
            k = len(G)
            f[f"{side}_pf{n}"] = sum(x["pf"] for x in G) / k
            f[f"{side}_pa{n}"] = sum(x["pa"] for x in G) / k
            f[f"{side}_mg{n}"] = f[f"{side}_pf{n}"] - f[f"{side}_pa{n}"]
            a = [x["ats"] for x in G if x["ats"] is not None]
            o = [x["ou"] for x in G if x["ou"] is not None]
            if a:
                f[f"{side}_ats{n}"] = sum(a) / len(a)
            if o:
                f[f"{side}_ou{n}"] = sum(o) / len(o)
        if H:
            last = H[-1]
            rest = (d - last["day"]).days
            f[f"{side}_rest"] = float(min(rest, 5))
            f[f"{side}_b2b"] = 1.0 if rest == 1 else 0.0
            f[f"{side}_g4"] = float(sum(1 for x in H if (d - x["day"]).days <= 3))
            f[f"{side}_g7"] = float(sum(1 for x in H if (d - x["day"]).days <= 7))
            road = 0
            for x in reversed(H):
                if x["home"]:
                    break
                road += 1
            f[f"{side}_roadtrip"] = float(road)
            f[f"{side}_lastmargin"] = last["pf"] - last["pa"]
        return f


def game_features(book, home, away, when, open_spread, open_total, open_ml_home, model_margin=None, model_total=None):
    d = day_of(when)
    f = {}
    f.update(book.feats(home, d, "h"))
    f.update(book.feats(away, d, "a"))
    # travel: time zones the away team crossed from its last venue to this one
    H = [x for x in book.log.get(nick(away), []) if x["day"] < d]
    if H:
        f["a_tzmove"] = float(TZ.get(nick(home), -6) - TZ.get(H[-1]["venue"], -6))
    for k in list(f):
        if k.startswith("h_") and "a_" + k[2:] in f:
            f["d_" + k[2:]] = f[k] - f["a_" + k[2:]]
    if open_spread is not None:
        f["open_spread"] = open_spread
    if open_total is not None:
        f["open_total"] = open_total
    if open_ml_home is not None:
        f["open_home"] = open_ml_home
    if model_margin is not None and open_spread is not None:
        f["model_spread_gap"] = (-model_margin) - open_spread
    if model_total is not None and open_total is not None:
        f["model_total_gap"] = model_total - open_total
    f["dow"] = float(d.weekday())
    f["month"] = float(d.month)
    return f


def build_history():
    import stats_more as sm
    g = json.loads((ROOT / "stats" / "nba_games.json").read_text())["games"]
    games = sorted([x for x in (g.values() if isinstance(g, dict) else g) if x.get("seasonType") in (2, None)], key=lambda x: x["date"])
    model = {}
    try:
        for x, p in sm.backtest(games, sm.CONFIG["NBA"]):
            model[x["id"]] = (p.get("margin"), p.get("total"))
    except Exception as exc:  # noqa: BLE001
        print("ratings backtest", exc)
    book, rows = Book(), []
    for x in games:
        if not x.get("final"):
            continue
        L = x.get("lines") or {}
        so, sc, to, tc = L.get("spreadOpen"), L.get("spreadClose"), L.get("totalOpen"), L.get("totalClose")
        ml = None
        if all(L.get(k) for k in ("mlHomeOpen", "mlAwayOpen", "mlHomeClose", "mlAwayClose")):
            ml = (novig2(L["mlHomeOpen"], L["mlAwayOpen"]), novig2(L["mlHomeClose"], L["mlAwayClose"]))
        if so is not None and sc is not None:
            mm, mt = model.get(x["id"], (None, None))
            f = game_features(book, x["home"], x["away"], x["date"], so, to, ml[0] if ml else None, mm, mt)
            rows.append({"id": x["id"], "date": x["date"], "home": x["home"], "away": x["away"], "f": f,
                         "y_spread": sc - so, "y_total": (tc - to) if to is not None and tc is not None else None,
                         "y_ml": (ml[1] - ml[0]) if ml else None})
        book.add(x)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"built": datetime.now(timezone.utc).isoformat(), "rows": rows}, separators=(",", ":")))
    return len(rows)


if __name__ == "__main__":
    print("history rows", build_history())
