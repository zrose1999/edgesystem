#!/usr/bin/env python3
"""EDGE strategy scanner (2026-10-21). The loop that turns data into strategies without being asked.

  python3 scan.py           morning: generate hypotheses, test them on all stored history, adopt the survivors
  python3 scan.py stamp     every full/near run: stamp shadow reads for upcoming games that match a tracked strategy
  python3 scan.py --dry     test and report, adopt nothing
  python3 scan.py learn     weekly: export the scanner's data as numbers and train learner.py on it (--force: now)

1. Hypotheses. Every game in EDGE's history (ESPN DraftKings open/close for NBA, NHL, NCAAF; CFBD closes for NCAAF
   2021+; Pinnacle open/close for five soccer leagues since 2016; nflverse closes for the NFL when reachable) is
   described by pre-pick features only: the opening number band (spread, total, price), favourite/dog and venue,
   days rest and the rest edge, day of week, month. Every single feature and every pair is a hypothesis, for every
   side of every market. Nothing is hand-picked.
2. Tests, three per hypothesis and side: the open-to-close move in the side's favour (CLV, what EDGE promotes on),
   the result at the opening number, and the result at the closing number (flat 1 unit at the price).
3. Survivors: enough games, the same sign in both time-ordered halves, a minimum effect, and a Benjamini-Hochberg
   false-discovery cut (q 0.10) across every test of the same kind, so a big search cannot manufacture edges.
   A result-only survivor is dropped if its own move test is clearly against it (t <= -1).
4. Adoption: survivors become shadow strategies (pattern "scan-<sport>-<market>-<side>-<conditions>") in
   stats/scan/strategies.json. Strategies that stop passing are marked lapsed: no new reads, history kept.
5. Live: `stamp` reads every upcoming row against the tracked strategies. A strategy with a measured move stamps
   fair = current line + the part of 0.8 x that move not yet made (grade from edge vs bar, as every pattern); a
   result-only strategy stamps a lean. Every read is shadow (stake 0) and Kalshi mirrors of scan patterns are
   track-only. From here the normal machinery takes over: grade.py grades CLV and decides promotion under the
   existing rules; memory.py logs and ranks the reads. The scanner never promotes, retires, or stakes anything.
"""

import csv
import glob
import gzip
import hashlib
import io
import json
import math
import os
import sys
import urllib.request
from argparse import Namespace
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path

import pull

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "scan"
CACHE = Path(os.environ.get("EDGE_CACHE", "/tmp/edge-cache"))
NFL_GAMES = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
FD = {"E0": "EPL", "SP1": "LaLiga", "I1": "SerieA", "D1": "Bundesliga", "F1": "Ligue1"}

MIN_N = {1: 150, 2: 120}                 # games for a single feature / a pair
MIN_EFFECT = {"move_points": 0.25, "move_prob": 0.004, "res": 0.03}
Q = 0.10                                 # Benjamini-Hochberg false discovery rate
MAX_TRACK = 40                           # tracked strategies at once (strongest first)
SHRINK = 0.8
WINDOW_H = 72
# Pick minimums set by Zack 2026-10-14 (rest-spot 0.75 pt, college 1 pt, NHL 2%, soccer 1.5%); smaller is a lean
MIN_MOVE = {"NBA": 0.75, "NCAAF": 1.0, "NFL": 1.0, "NHL": 0.02, "soccer": 0.015}
TRACK_ONLY_PREFIX = "mirror:scan-"
CLOSE_KEYS = {"closeLine", "closeTotal"}
CLOSE_WINDOW_H = 3          # fast runs (every 15 min, last 3 hours) stamp these near the close


# ---------- helpers ----------

def parse(ts):
    ts = ts.replace("Z", "+00:00")
    if len(ts) == 22 and ts[16] == "+":           # 2025-10-07T21:00+00:00
        ts = ts[:16] + ":00" + ts[16:]
    return datetime.fromisoformat(ts)


def dec(american):
    if american in (None, "", "missing"):
        return None
    a = float(american)
    return 1 + (a / 100 if a > 0 else 100 / -a)


def novig(p_a, p_b):
    if not p_a or not p_b:
        return None
    a, b = 1 / p_a, 1 / p_b
    return a / (a + b)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def band(x, edges, fmt="{:g}"):
    if x is None:
        return None
    if x < edges[0]:
        return "<" + fmt.format(edges[0])
    for lo, hi in zip(edges, edges[1:]):
        if lo <= x < hi:
            return f"{fmt.format(lo)}-{fmt.format(hi)}"
    return fmt.format(edges[-1]) + "+"


def spread_band(sport, home_line):
    if home_line is None:
        return None
    a = abs(home_line)
    if a < 0.5:
        return "pick'em"
    edges = [0.5, 3, 4, 7, 8, 10, 14, 21] if sport in ("NFL", "NCAAF") else [0.5, 3, 6, 9, 13]
    who = "home fav" if home_line < 0 else "home dog"
    return f"{who} {band(a, edges)}"


TOTAL_EDGES = {"NBA": [210, 215, 220, 225, 230, 235, 240, 245], "NCAAF": [40, 45, 50, 55, 60, 65, 70],
               "NFL": [37, 40, 43, 46, 49, 52]}


def total_band(sport, t):
    if t is None:
        return None
    if sport == "NHL":
        return f"{t:g}"
    return band(t, TOTAL_EDGES.get(sport, [0]))


def prob_band(p):
    return None if p is None else band(round(p, 4), [0.25, 0.35, 0.45, 0.55, 0.65, 0.75], "{:.0%}")


def rest_bucket(sport, d):
    if d is None:
        return None
    if sport in ("NFL", "NCAAF"):
        return "short" if d < 6 else "normal" if d <= 8 else "long"
    if pull_soccer(sport):
        return "short" if d <= 3 else "normal" if d <= 6 else "long"
    return "b2b" if d <= 1 else "1day" if d == 2 else "2+days"


def pull_soccer(sport):
    return sport in pull.SOCCER


def us_day(when):
    """The game's calendar day in US time (UTC-6h, as rest_nba.py): a Thursday 8:20pm ET kickoff is Thursday."""
    return when - timedelta(hours=6)


def base_feats(sport, when, rh, ra):
    d = us_day(when)
    f = {"dow": d.strftime("%a"), "month": d.strftime("%b")}
    bh, ba = rest_bucket(sport, rh), rest_bucket(sport, ra)
    if bh:
        f["restHome"] = bh
    if ba:
        f["restAway"] = ba
    if rh is not None and ra is not None:
        f["restEdge"] = "home more" if rh > ra else "away more" if ra > rh else "even"
    return f


# ---------- schedules (rest) ----------

class Schedule:
    def __init__(self):
        self.times = defaultdict(list)

    def add(self, team, when):
        self.times[team].append(when)

    def done(self):
        for k in self.times:
            self.times[k].sort()
        return self

    def rest(self, team, when):
        prev = [t for t in self.times.get(team, ()) if t < when - timedelta(hours=6)]
        if not prev or (when - prev[-1]).days > 30:
            return None
        return round((when - prev[-1]).total_seconds() / 86400)


SCHED_FILES = {"NBA": "nba_games", "NHL": "nhl_games", "NCAAF": "ncaaf_games", "NFL": "nfl_schedule"}


def load_schedule(sport):
    s = Schedule()
    g = pull.load(ROOT / "stats" / f"{SCHED_FILES[sport]}.json", {}).get("games") or {}
    for x in (g.values() if isinstance(g, dict) else g):
        if x.get("date") and x.get("home"):
            w = parse(x["date"])
            s.add(x["home"], w)
            s.add(x["away"], w)
    return s.done()


# ---------- history -> samples ----------
# sample: sport, market, when, feats, sides {side: {"move": x|None, "resOpen": profit|None, "resClose": profit|None}}

def side_results(market, hs, as_, line_home=None, total=None, prices=None):
    """Profit per side at a number (1 unit). None for a push or a missing number."""
    prices = prices or {}
    out = {}
    if market == "spread" and line_home is not None:
        c = hs - as_ + line_home
        for side, won in (("home", c > 0), ("away", c < 0)):
            d = prices.get(side) or 1.909
            out[side] = None if c == 0 else (d - 1 if won else -1.0)
    elif market == "total" and total is not None:
        pts = hs + as_
        for side, won in (("over", pts > total), ("under", pts < total)):
            d = prices.get(side) or 1.909
            out[side] = None if pts == total else (d - 1 if won else -1.0)
    elif market == "h2h":
        res = "home" if hs > as_ else "away" if as_ > hs else "draw"
        for side in ("home", "away", "draw"):
            d = prices.get(side)
            if d:
                out[side] = d - 1 if res == side else -1.0
    return out


def espn_samples():
    out = []
    for sport in ("NBA", "NHL", "NCAAF"):
        sched = load_schedule(sport)
        g = pull.load(ROOT / "stats" / f"{sport.lower()}_games.json", {}).get("games") or {}
        for x in (g.values() if isinstance(g, dict) else g):
            L = x.get("lines") or {}
            if not x.get("final") or x.get("hs") is None or x.get("seasonType") == 1 or not L:
                continue
            when = parse(x["date"])
            hs, as_ = x["hs"], x["as"]
            f0 = base_feats(sport, when, sched.rest(x["home"], when), sched.rest(x["away"], when))
            f0["id"] = str(x.get("id"))
            so, sc = L.get("spreadOpen"), L.get("spreadClose")
            if sport != "NHL" and sc is not None:
                f = dict(f0, line=spread_band(sport, so)) if so is not None else dict(f0)
                ro = side_results("spread", hs, as_, line_home=so) if so is not None else {}
                rc = side_results("spread", hs, as_, line_home=sc)
                sides = {s: {"move": (so - sc if s == "home" else sc - so) if so is not None else None,
                             "resOpen": ro.get(s), "resClose": rc.get(s)} for s in ("home", "away")}
                out.append((sport, "spread", when, f, sides))
            to, tc = L.get("totalOpen"), L.get("totalClose")
            if tc is not None:
                f = dict(f0, total=total_band(sport, to)) if to is not None else dict(f0)
                po = {"over": dec(L.get("overOpenOdds")), "under": dec(L.get("underOpenOdds"))}
                pc = {"over": dec(L.get("overCloseOdds")), "under": dec(L.get("underCloseOdds"))}
                if sport == "NHL":
                    pov = novig(po["over"], po["under"])
                    if pov is not None:
                        f["overPrice"] = prob_band(pov)
                    pcv = novig(pc["over"], pc["under"])
                    mv = (pcv - pov) if (pov is not None and pcv is not None and to == tc) else None
                    unit_move = {"over": mv, "under": -mv if mv is not None else None}
                else:
                    unit_move = {"over": (tc - to) if to is not None else None,
                                 "under": (to - tc) if to is not None else None}
                ro = side_results("total", hs, as_, total=to, prices=po) if to is not None else {}
                rc = side_results("total", hs, as_, total=tc, prices=pc)
                sides = {s: {"move": unit_move[s], "resOpen": ro.get(s), "resClose": rc.get(s)} for s in ("over", "under")}
                out.append((sport, "total", when, f, sides))
            mo = {"home": dec(L.get("mlHomeOpen")), "away": dec(L.get("mlAwayOpen"))}
            mc = {"home": dec(L.get("mlHomeClose")), "away": dec(L.get("mlAwayClose"))}
            if mc["home"] and mc["away"] and hs != as_:
                ph_o, ph_c = novig(mo["home"], mo["away"]), novig(mc["home"], mc["away"])
                f = dict(f0)
                if ph_o is not None:
                    f["homePrice"] = prob_band(ph_o)
                ro = side_results("h2h", hs, as_, prices=mo) if ph_o is not None else {}
                rc = side_results("h2h", hs, as_, prices=mc)
                mv = (ph_c - ph_o) if (ph_o is not None and ph_c is not None) else None
                sides = {s: {"move": (mv if s == "home" else -mv) if mv is not None else None,
                             "resOpen": ro.get(s), "resClose": rc.get(s)} for s in ("home", "away")}
                out.append((sport, "h2h", when, f, sides))
    return out


def cfbd_samples(seen_ids):
    """NCAAF seasons ESPN no longer keeps: CFBD DraftKings spread open/close and total close."""
    out = []
    sched = load_schedule("NCAAF")
    for path in sorted(glob.glob(str(ROOT / "stats" / "history" / "ncaaf" / "cfbd_*.json"))):
        d = pull.load(Path(path), {})
        lines = d.get("lines") or {}
        for g in d.get("games") or []:
            L = lines.get(str(g.get("id")))
            if not L or not g.get("done") or g.get("hp") is None or str(g.get("id")) in seen_ids:
                continue
            when = parse(g["date"])
            hs, as_ = g["hp"], g["ap"]
            f0 = base_feats("NCAAF", when, sched.rest(g["home"], when), sched.rest(g["away"], when))
            so, sc, to, tc = L.get("so"), L.get("sc"), L.get("to"), L.get("tc")
            if sc is not None and not g.get("neutral"):
                f = dict(f0, line=spread_band("NCAAF", so)) if so is not None else dict(f0)
                ro = side_results("spread", hs, as_, line_home=so) if so is not None else {}
                rc = side_results("spread", hs, as_, line_home=sc)
                out.append(("NCAAF", "spread", when, f, {s: {"move": (so - sc if s == "home" else sc - so) if so is not None else None,
                                                             "resOpen": ro.get(s), "resClose": rc.get(s)} for s in ("home", "away")}))
            if tc is not None:
                f = dict(f0, total=total_band("NCAAF", to)) if to is not None else dict(f0, closeTotal=total_band("NCAAF", tc))
                rc = side_results("total", hs, as_, total=tc)
                ro = side_results("total", hs, as_, total=to) if to is not None else {}
                out.append(("NCAAF", "total", when, f, {s: {"move": ((tc - to) if s == "over" else (to - tc)) if to is not None else None,
                                                            "resOpen": ro.get(s), "resClose": rc.get(s)} for s in ("over", "under")}))
    return out


def soccer_samples():
    out = []
    for path in sorted(glob.glob(str(ROOT / "stats" / "history" / "soccer" / "fd_*.csv"))):
        code = Path(path).stem.split("_")[1]
        sport = FD.get(code)
        if not sport:
            continue
        with open(path, encoding="utf-8-sig", errors="ignore") as fh:
            for r in csv.DictReader(fh):
                hg, ag = num(r.get("FTHG")), num(r.get("FTAG"))
                if hg is None or not r.get("Date"):
                    continue
                try:
                    day = r["Date"]
                    when = datetime.strptime(day, "%d/%m/%Y" if len(day.split("/")[-1]) == 4 else "%d/%m/%y").replace(
                        hour=15, tzinfo=timezone.utc)
                except ValueError:
                    continue
                f0 = {"dow": us_day(when).strftime("%a"), "month": us_day(when).strftime("%b")}
                oo, ou, co, cu = (num(r.get(k)) for k in ("P>2.5", "P<2.5", "PC>2.5", "PC<2.5"))
                if co and cu:
                    p_o, p_c = novig(oo, ou), novig(co, cu)
                    f = dict(f0, line="2.5")
                    if p_o is not None:
                        f["overPrice"] = prob_band(p_o)
                    mv = (p_c - p_o) if p_o is not None else None
                    ro = side_results("total", hg, ag, total=2.5, prices={"over": oo, "under": ou}) if oo and ou else {}
                    rc = side_results("total", hg, ag, total=2.5, prices={"over": co, "under": cu})
                    out.append((sport, "total", when, f, {s: {"move": (mv if s == "over" else -mv) if mv is not None else None,
                                                             "resOpen": ro.get(s), "resClose": rc.get(s)} for s in ("over", "under")}))
                ph, pd, pa = num(r.get("PSH")), num(r.get("PSD")), num(r.get("PSA"))
                ch, cd, ca = num(r.get("PSCH")), num(r.get("PSCD")), num(r.get("PSCA"))
                if ch and cd and ca:
                    f = dict(f0)
                    so = None
                    if ph and pd and pa:
                        s = 1 / ph + 1 / pd + 1 / pa
                        so = {"home": 1 / ph / s, "draw": 1 / pd / s, "away": 1 / pa / s}
                        f["homePrice"] = prob_band(so["home"])
                    s2 = 1 / ch + 1 / cd + 1 / ca
                    sc = {"home": 1 / ch / s2, "draw": 1 / cd / s2, "away": 1 / ca / s2}
                    ro = side_results("h2h", hg, ag, prices={"home": ph, "draw": pd, "away": pa}) if so else {}
                    rc = side_results("h2h", hg, ag, prices={"home": ch, "draw": cd, "away": ca})
                    out.append((sport, "h2h", when, f, {s: {"move": (sc[s] - so[s]) if so else None,
                                                           "resOpen": ro.get(s), "resClose": rc.get(s)} for s in ("home", "draw", "away")}))
    return out


def nfl_samples():
    """nflverse games.csv (closes, rest, results), 2015 on. Reachable from GitHub's runners; skipped when not."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "nfl_games.csv"
    try:
        if not path.exists() or (datetime.now().timestamp() - path.stat().st_mtime) > 20 * 3600:
            req = urllib.request.Request(NFL_GAMES, headers={"User-Agent": "EDGE"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if not data.startswith(b"game_id"):
                return []
            path.write_bytes(data)
        rows = list(csv.DictReader(io.StringIO(path.read_text())))
    except Exception as exc:  # noqa: BLE001
        print(f"nfl history skipped: {exc}")
        return []
    out = []
    for g in rows:
        if num(g.get("season")) is None or num(g["season"]) < 2015 or g.get("home_score") in ("", "NA", None):
            continue
        sp, tl = num(g.get("spread_line")), num(g.get("total_line"))
        hs, as_ = num(g["home_score"]), num(g["away_score"])
        if hs is None or as_ is None:
            continue
        try:
            when = datetime.strptime(f"{g['gameday']} {g.get('gametime') or '13:00'}", "%Y-%m-%d %H:%M").replace(
                tzinfo=timezone.utc) + timedelta(hours=4)
        except ValueError:
            continue
        rh, ra = num(g.get("home_rest")), num(g.get("away_rest"))
        f0 = base_feats("NFL", when, rh, ra)
        if g.get("location") == "Neutral":
            continue
        if sp is not None:
            hl = -sp                                   # nflverse spread_line: home minus away, positive = home favoured
            rc = side_results("spread", hs, as_, line_home=hl)
            out.append(("NFL", "spread", when, dict(f0, closeLine=spread_band("NFL", hl)),
                        {s: {"move": None, "resOpen": None, "resClose": rc.get(s)} for s in ("home", "away")}))
        if tl is not None:
            rc = side_results("total", hs, as_, total=tl, prices={"over": dec(num(g.get("over_odds"))),
                                                                   "under": dec(num(g.get("under_odds")))})
            out.append(("NFL", "total", when, dict(f0, closeTotal=total_band("NFL", tl)),
                        {s: {"move": None, "resOpen": None, "resClose": rc.get(s)} for s in ("over", "under")}))
    return out


# ---------- testing ----------

def stat(xs):
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    sd = (sum((x - m) ** 2 for x in xs) / (n - 1)) ** 0.5
    se = sd / n ** 0.5 if sd else 0.0
    t = m / se if se else 0.0
    h = n // 2
    return {"n": n, "mean": m, "t": t, "p": math.erfc(abs(t) / 2 ** 0.5),
            "first": sum(xs[:h]) / max(h, 1), "second": sum(xs[h:]) / max(n - h, 1)}


UNIT = {"spread": "points", "total": "points", "h2h": "prob"}


def unit_of(sport, market):
    return "prob" if market == "h2h" or (market == "total" and sport in pull.PROB_TOTALS) else "points"


def run_tests(samples):
    """Every condition (single feature or pair) x side x target. Moves are tested as the EXCESS over the same
    sport/market/side average move (the league drift edge_stack already trades), so a survivor is a condition that
    moves differently from its league, not the league itself. Results are tested as they are (must be profitable)."""
    groups = defaultdict(list)          # (target, sport, market, side, conds) -> [(when, value)]
    base = defaultdict(list)
    for sport, market, when, feats, sides in samples:
        items = sorted((k, v) for k, v in feats.items() if v is not None and k != "id")
        conds = [(c,) for c in items] + list(combinations(items, 2))
        for side, vals in sides.items():
            for target in ("move", "resOpen", "resClose"):
                v = vals.get(target)
                if v is None:
                    continue
                base[(target, sport, market, side)].append(v)
                for c in conds:
                    groups[(target, sport, market, side, c)].append((when, v))
    base_mean = {k: sum(v) / len(v) for k, v in base.items()}
    tests = []
    for (target, sport, market, side, conds), xs in groups.items():
        if len(xs) < MIN_N[len(conds)]:
            continue
        xs.sort(key=lambda t: t[0])
        b = base_mean[(target, sport, market, side)] if target == "move" else 0.0
        s = stat([v - b for _, v in xs])
        if not s:
            continue
        raw = s["mean"] + b
        tests.append({"target": target, "sport": sport, "market": market, "side": side,
                      "conds": [list(c) for c in conds], "unit": unit_of(sport, market), **s,
                      "raw": raw, "base": b, "rawFirst": s["first"] + b, "rawSecond": s["second"] + b,
                      "from": xs[0][0].strftime("%Y-%m-%d"), "to": xs[-1][0].strftime("%Y-%m-%d")})
    # Benjamini-Hochberg per target, across every test of that kind
    by_t = defaultdict(list)
    for t in tests:
        by_t[t["target"]].append(t)
    for target, ts in by_t.items():
        ts.sort(key=lambda t: t["p"])
        m = len(ts)
        cut = 0
        for i, t in enumerate(ts, 1):
            if t["p"] <= Q * i / m:
                cut = i
        for i, t in enumerate(ts, 1):
            t["bh"] = i <= cut
            t["tests"] = m
    # A pair must add something beyond each of its singles (1.25x the excess of a passing single)
    single = {(t["target"], t["sport"], t["market"], t["side"], tuple(t["conds"][0])): t for t in tests if len(t["conds"]) == 1}
    for t in tests:
        if len(t["conds"]) == 2:
            for c in t["conds"]:
                s1 = single.get((t["target"], t["sport"], t["market"], t["side"], tuple(c)))
                if s1 and passes(s1) and t["mean"] <= 1.25 * s1["mean"]:
                    t["redundant"] = True
    return tests


def passes(t):
    """Excess over the league (moves) or profit (results) is positive, survives the false-discovery cut, holds in both
    halves, and the side's own number clears the minimum effect (a move must also favour the side outright)."""
    if t["mean"] <= 0 or not t.get("bh") or t.get("redundant"):
        return False
    if not (t["first"] > 0 and t["second"] > 0):
        return False
    if t["target"] == "move":
        floor = MIN_EFFECT["move_" + t["unit"]]
        return t["mean"] >= floor / 2 and t["raw"] >= floor and t["rawFirst"] > 0 and t["rawSecond"] > 0
    return t["mean"] >= MIN_EFFECT["res"]


def key_of(t):
    return (t["sport"], t["market"], t["side"], tuple(tuple(c) for c in t["conds"]))


def slug(sport, market, side, conds):
    words = "-".join(f"{k}={v}" for k, v in conds)
    h = hashlib.sha1(f"{sport}|{market}|{side}|{words}".encode()).hexdigest()[:6]
    clean = "".join(ch if ch.isalnum() else "" for ch in words.replace("=", ""))[:28].lower()
    return f"scan-{sport.lower()}-{market}-{side}-{clean}-{h}"


def fmt(t):
    if t is None:
        return "n/a"
    if t["target"] == "move":
        v = f"{t['mean']:+.2f} pts" if t["unit"] == "points" else f"{t['mean'] * 100:+.2f}%"
    else:
        v = f"ROI {t['mean'] * 100:+.1f}%"
    return f"{v} (n {t['n']}, t {t['t']:+.1f})"


def adopt(tests, now, dry=False):
    by_key = defaultdict(dict)
    for t in tests:
        by_key[key_of(t)][t["target"]] = t
    found = []
    for k, ev in by_key.items():
        mv, ro, rc = ev.get("move"), ev.get("resOpen"), ev.get("resClose")
        move_ok = mv is not None and passes(mv)
        res = [r for r in (ro, rc) if r is not None and passes(r)]
        if not move_ok and not res:
            continue
        if not move_ok and mv is not None and mv["t"] <= -1:
            continue                                  # results say yes, the market's own move says no
        score = max(([mv["t"]] if move_ok else []) + [r["t"] for r in res])
        found.append({"key": k, "score": score, "move": mv, "resOpen": ro, "resClose": rc, "moveBacked": move_ok})
    found.sort(key=lambda f: -f["score"])
    path = OUT / "strategies.json"
    store = pull.load(path, {"strategies": {}})
    S = store["strategies"]
    live = set()
    for f in found[:MAX_TRACK]:
        sport, market, side, conds = f["key"]
        sid = slug(sport, market, side, conds)
        live.add(sid)
        cur = S.get(sid) or {"id": sid, "firstFound": now, "sport": sport, "market": market, "side": side,
                             "conds": [list(c) for c in conds]}
        cur.update({"status": "tracking", "lastPassed": now, "moveBacked": f["moveBacked"], "score": round(f["score"], 2),
                    "evidence": {x: ({k2: (round(v, 5) if isinstance(v, float) else v) for k2, v in f[x].items()
                                      if k2 in ("n", "mean", "raw", "base", "t", "first", "second", "from", "to", "tests")} if f[x] else None)
                                 for x in ("move", "resOpen", "resClose")},
                    "unit": unit_of(sport, market)})
        S[sid] = cur
    for sid, s in S.items():
        if sid not in live and s.get("status") == "tracking":
            s["status"] = "lapsed"
            s["lapsedAt"] = now
    store.update({"asOf": now, "tests": len(tests), "survivors": len(found), "tracking": len(live)})
    if not dry:
        OUT.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(store, indent=1) + "\n")
    return store, found


def report(store, found, tests, n_samples, now):
    by_target = defaultdict(int)
    for t in tests:
        by_target[t["target"]] += 1
    md = ["# Strategy scanner (scan.py)", "",
          f"{now}. {n_samples} game-markets; {len(tests)} hypotheses tested ({', '.join(f'{k} {v}' for k, v in sorted(by_target.items()))}). "
          f"Survivors pass a Benjamini-Hochberg cut at q {Q} per test kind, the same sign in both time-ordered halves, and a "
          f"minimum effect. {len(found)} survivors; the strongest {min(len(found), MAX_TRACK)} are tracked as shadow strategies "
          "(stake 0) and stamp live reads, so their CLV builds on its own. grade.py alone decides promotion.", "",
          "| Strategy | Side | Conditions | Move (CLV) | Result at open | Result at close | Status |",
          "|---|---|---|---|---|---|---|"]
    S = store["strategies"]
    for s in sorted(S.values(), key=lambda s: (s["status"] != "tracking", -s.get("score", 0)))[:60]:
        e = s.get("evidence") or {}
        conds = "; ".join(f"{k} {v}" for k, v in s["conds"])
        md.append(f"| {s['sport']} {s['market']} | {s['side']} | {conds} | {fmt(dict(e['move'], target='move', unit=s['unit'])) if e.get('move') else 'n/a'} | "
                  f"{fmt(dict(e['resOpen'], target='res')) if e.get('resOpen') else 'n/a'} | "
                  f"{fmt(dict(e['resClose'], target='res')) if e.get('resClose') else 'n/a'} | {s['status']} |")
    (OUT / "report.md").write_text("\n".join(md) + "\n")


# ---------- live stamping ----------

def row_feats(row, sched_cache):
    sport, market = row["sport"], row["market"]
    o = row.get("openSnap") or {}
    when = parse(row["commence"])
    if pull_soccer(sport):
        f = {"dow": us_day(when).strftime("%a"), "month": us_day(when).strftime("%b")}
    else:
        if sport not in sched_cache:
            sched_cache[sport] = load_schedule(sport) if sport in SCHED_FILES else Schedule()
        sc = sched_cache[sport]
        f = base_feats(sport, when, sc.rest(row["home"], when), sc.rest(row["away"], when))
    c = row.get("lastSnap") or {}
    if market == "spread" and c.get("line") is not None:
        f["closeLine"] = spread_band(sport, c["line"])     # strategies found on closing numbers (NFL history)
    if market == "total" and c.get("line") is not None and not pull_soccer(sport):
        f["closeTotal"] = total_band(sport, c["line"])
    if market == "spread" and o.get("line") is not None:
        f["line"] = spread_band(sport, o["line"])
    elif market == "total" and o.get("line") is not None:
        if pull_soccer(sport):
            if o["line"] != 2.5:
                return None
            f["line"] = "2.5"
        else:
            f["total"] = total_band(sport, o["line"])
        if sport in pull.PROB_TOTALS:
            p = novig(dec(o.get("over")), dec(o.get("under")))
            if p is not None:
                f["overPrice"] = prob_band(p)
    elif market == "h2h":
        if pull_soccer(sport) or "draw" in o:
            return None                                    # three-way moneylines are tested, not stamped (v1)
        p = novig(dec(o.get("home")), dec(o.get("away")))
        if p is not None:
            f["homePrice"] = prob_band(p)
    return f


def moved_for_side(row, side, unit):
    o, c = row.get("openSnap") or {}, row.get("lastSnap") or {}
    if unit == "points":
        if o.get("line") is None or c.get("line") is None:
            return 0.0
        d = c["line"] - o["line"]
        return {"home": -d, "away": d, "over": d, "under": -d}[side]
    keys = ("home", "away") if row["market"] == "h2h" else ("over", "under")
    po, pc = novig(dec(o.get(keys[0])), dec(o.get(keys[1]))), novig(dec(c.get(keys[0])), dec(c.get(keys[1])))
    if po is None or pc is None or (row["market"] == "total" and o.get("line") != c.get("line")):
        return 0.0
    d = pc - po
    return d if side == keys[0] else -d


def fair_for(row, side, edge, unit):
    """A fair number that gives `side` exactly `edge` against the current snapshot (make_read's convention)."""
    c = row["lastSnap"]
    if row["market"] == "spread":
        return c["line"] - edge if side == "home" else c["line"] + edge
    if unit == "points":
        return c["line"] + edge if side == "over" else c["line"] - edge
    keys = ("home", "away") if row["market"] == "h2h" else ("over", "under")
    imp = 1 / dec(c[side])
    p_side = imp + edge
    return p_side if side == keys[0] else 1 - p_side


def stamp(dry=False):
    store = pull.load(OUT / "strategies.json", {"strategies": {}})
    strategies = [s for s in store["strategies"].values() if s.get("status") == "tracking"]
    now = datetime.now(timezone.utc)
    horizon = pull.iso(now + timedelta(hours=WINDOW_H))
    ledger = pull.load(pull.LEDGER, {"rows": []})
    picks = pull.load(pull.PICKS, {"picks": []})["picks"]
    done = {(p.get("rowId"), p.get("pattern")) for p in picks}
    cache, todo = {}, []
    for row in ledger.get("rows") or []:
        if not row.get("commence") or not (pull.iso(now) < row["commence"] <= horizon) or not row.get("lastSnap"):
            continue
        mine = [s for s in strategies if s["sport"] == row["sport"] and s["market"] == row["market"]
                and (row["id"], s["id"]) not in done]
        if not mine:
            continue
        f = row_feats(row, cache)
        if not f:
            continue
        to_kick = (parse(row["commence"]) - now).total_seconds() / 3600
        for s in mine:
            if not all(f.get(k) == v for k, v in s["conds"]):
                continue
            if any(k in CLOSE_KEYS for k, _ in s["conds"]) and to_kick > CLOSE_WINDOW_H:
                continue                                   # a closing-number strategy reads only near kickoff
            side, unit = s["side"], s["unit"]
            if side not in (row["lastSnap"] or {}) or side == "draw":
                continue                                   # three-way draw markets are tested, not stamped (v1)
            e = s.get("evidence") or {}
            conds = "; ".join(f"{k} {v}" for k, v in s["conds"])
            minimum = MIN_MOVE["soccer" if pull_soccer(row["sport"]) else row["sport"]] if (
                pull_soccer(row["sport"]) or row["sport"] in MIN_MOVE) else 0.0
            if s.get("moveBacked") and e.get("move"):
                expected = SHRINK * e["move"].get("raw", e["move"]["mean"])
                remaining = expected - max(0.0, moved_for_side(row, side, unit))
                if remaining <= (0.05 if unit == "points" else 0.001):
                    continue
                edge, lean = remaining, remaining < minimum
                basis = (f"measured open-to-close move {e['move'].get('raw', e['move']['mean']):+.3g} for this side "
                         f"({e['move']['mean']:+.3g} beyond the league average; n {e['move']['n']}, t {e['move']['t']:+.1f}) "
                         f"x{SHRINK}, {remaining:.3g} still to come")
            else:
                edge, lean = (0.1 if unit == "points" else 0.002), True
                r = e.get("resClose") or e.get("resOpen") or {}
                basis = f"result-only: ROI {r.get('mean', 0) * 100:+.1f}% on {r.get('n')} games (t {r.get('t', 0):+.1f}); no measured move, lean only"
            why = f"Scanner strategy {s['id']}: {s['sport']} {s['market']} {side} when {conds}; {basis}."
            todo.append((row, s, fair_for(row, side, edge, unit), why, lean))
    learned = learned_stamp(ledger.get("rows") or [], now, done, dry)
    todo += [(row, {"id": pat, "side": side}, fair, why, lean) for row, pat, fair, why, lean, side in learned]
    stamped = 0
    for row, s, fair, why, lean in todo:
        if dry:
            print("WOULD READ", row["id"], s["side"], round(fair, 4), "lean" if lean else "", "|", why)
            continue
        if lean:
            pull.LEAN_CAP.add((row["id"], s["id"]))
        if row["sport"] not in pull.READ:
            pull.READ = pull.READ + [row["sport"]]
        args = Namespace(id=row["id"], fair=f"{fair:.4f}", confidence="medium", reason=why,
                         falsifier="The price closes at or past the open on the other side.",
                         pattern=s["id"], stake="0", big=True, by="scan.py")
        try:
            pull.make_read(args)
            stamped += 1
        except SystemExit as exc:
            print(f"read not stamped {row['id']} {s['id']}: {exc}")
    print(json.dumps({"tracked": len(strategies), "matches": len(todo), "learnedReads": len(learned),
                      "stamped": stamped, "dry": dry}))


# ---------- learner on the scanner's whole feature set ----------
# The scan tests conditions one and two at a time. learner.py (walk-forward ridge and gradient-boosted trees, the
# same out-of-sample gate as every learned model) gets the same pre-pick data as numbers, so it can find thresholds
# and interactions the condition search cannot. Targets: scan_<sport>_<market>, y = open-to-close move for the
# first side (home / over). Only games with an opening number (the move needs it).
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
LEARN_EVERY_D = 7


def numeric(sport, market, when, open_line, open_prob, rh, ra):
    day = us_day(when)
    f = {"month": day.month, "weekend": 1.0 if day.strftime("%a") in ("Sat", "Sun") else 0.0}
    for d in DOW:
        f["dow_" + d] = 1.0 if day.strftime("%a") == d else 0.0
    if open_line is not None:
        f["open_line"] = open_line
        if market == "spread":
            f["open_abs_line"] = abs(open_line)
    if open_prob is not None:
        f["open_prob"] = open_prob
    if rh is not None:
        f["rest_home"] = min(rh, 30)
    if ra is not None:
        f["rest_away"] = min(ra, 30)
    if rh is not None and ra is not None:
        f["rest_diff"] = max(-14, min(14, rh - ra))
    return f


def learn_rows():
    """learner.py rows per scan target, from the same histories as the condition search."""
    out = defaultdict(list)
    for sport in ("NBA", "NHL", "NCAAF"):
        sched = load_schedule(sport)
        g = pull.load(ROOT / "stats" / f"{sport.lower()}_games.json", {}).get("games") or {}
        for x in (g.values() if isinstance(g, dict) else g):
            L = x.get("lines") or {}
            if not x.get("final") or x.get("seasonType") == 1 or not L:
                continue
            when = parse(x["date"])
            rh, ra = sched.rest(x["home"], when), sched.rest(x["away"], when)
            so, sc = L.get("spreadOpen"), L.get("spreadClose")
            if sport != "NHL" and so is not None and sc is not None:
                out[f"scan_{sport.lower()}_spread"].append({"date": x["date"], "y": so - sc,
                                                           "f": numeric(sport, "spread", when, so, None, rh, ra)})
            to, tc = L.get("totalOpen"), L.get("totalClose")
            if to is not None and tc is not None:
                if sport == "NHL":
                    po = novig(dec(L.get("overOpenOdds")), dec(L.get("underOpenOdds")))
                    pc = novig(dec(L.get("overCloseOdds")), dec(L.get("underCloseOdds")))
                    if po is not None and pc is not None and to == tc:
                        out["scan_nhl_total"].append({"date": x["date"], "y": pc - po,
                                                      "f": numeric(sport, "total", when, to, po, rh, ra)})
                else:
                    out[f"scan_{sport.lower()}_total"].append({"date": x["date"], "y": tc - to,
                                                              "f": numeric(sport, "total", when, to, None, rh, ra)})
            po = novig(dec(L.get("mlHomeOpen")), dec(L.get("mlAwayOpen")))
            pc = novig(dec(L.get("mlHomeClose")), dec(L.get("mlAwayClose")))
            if po is not None and pc is not None:
                out[f"scan_{sport.lower()}_h2h"].append({"date": x["date"], "y": pc - po,
                                                        "f": numeric(sport, "h2h", when, so, po, rh, ra)})
    # NCAAF seasons ESPN no longer keeps: CFBD spread open and close (neutral sites out, same as the condition search)
    have = {r["date"] + "|" + str(r["f"].get("open_line")) for r in out["scan_ncaaf_spread"]}
    sched = load_schedule("NCAAF")
    for path in sorted(glob.glob(str(ROOT / "stats" / "history" / "ncaaf" / "cfbd_*.json"))):
        d = pull.load(Path(path), {})
        lines = d.get("lines") or {}
        for g in d.get("games") or []:
            L = lines.get(str(g.get("id")))
            if not L or not g.get("done") or g.get("neutral") or L.get("so") is None or L.get("sc") is None:
                continue
            when = parse(g["date"])
            date = when.strftime("%Y-%m-%dT%H:%MZ")
            if date + "|" + str(L["so"]) in have:
                continue
            out["scan_ncaaf_spread"].append({"date": date, "y": L["so"] - L["sc"], "f": numeric(
                "NCAAF", "spread", when, L["so"], None, sched.rest(g["home"], when), sched.rest(g["away"], when))})
    # soccer totals: over-2.5 move with the opening no-vig over probability and the league as numbers
    for path in sorted(glob.glob(str(ROOT / "stats" / "history" / "soccer" / "fd_*.csv"))):
        code = Path(path).stem.split("_")[1]
        sport = FD.get(code)
        if not sport:
            continue
        with open(path, encoding="utf-8-sig", errors="ignore") as fh:
            for r in csv.DictReader(fh):
                oo, ou, co, cu = (num(r.get(k)) for k in ("P>2.5", "P<2.5", "PC>2.5", "PC<2.5"))
                po, pc = novig(oo, ou), novig(co, cu)
                if po is None or pc is None or not r.get("Date"):
                    continue
                try:
                    day = r["Date"]
                    when = datetime.strptime(day, "%d/%m/%Y" if len(day.split("/")[-1]) == 4 else "%d/%m/%y").replace(
                        hour=15, tzinfo=timezone.utc)
                except ValueError:
                    continue
                f = numeric(sport, "total", when, 2.5, po, None, None)
                for lg in FD.values():
                    f["league_" + lg] = 1.0 if lg == sport else 0.0
                out["scan_soccer_total"].append({"date": when.strftime("%Y-%m-%dT%H:%MZ"), "y": pc - po, "f": f})
    return out


def target_unit(name):
    return "prob" if name.endswith("_h2h") or name in ("scan_nhl_total", "scan_soccer_total") else "points"


def learn(force=False):
    """Export the rows, then train every scan target with learner.py (weekly; the gate decides what goes live)."""
    import learner
    feat_dir = ROOT / "stats" / "features"
    feat_dir.mkdir(parents=True, exist_ok=True)
    reg_path = feat_dir / "scan_targets.json"
    reg = pull.load(reg_path, {})
    rows = learn_rows()
    out = {}
    for name, rs in rows.items():
        if len(rs) < 300:
            continue
        rs.sort(key=lambda r: r["date"])
        (feat_dir / f"{name}.json").write_text(json.dumps({"rows": rs}))
        reg[name] = {"file": f"stats/features/{name}.json", "y": "y", "unit": target_unit(name)}
    reg_path.write_text(json.dumps(reg, indent=1) + "\n")
    learner.TARGETS.update(reg)
    for name in reg:
        rep_path = ROOT / "stats" / "models" / f"{name}.json"
        if not force and rep_path.exists():
            age = datetime.now(timezone.utc) - parse(json.loads(rep_path.read_text())["trained"])
            if age < timedelta(days=LEARN_EVERY_D):
                out[name] = "fresh"
                continue
        try:
            rep = learner.run(name)
            out[name] = {"live": rep["live"], "chosen": rep["chosen"], "t": rep["results"][rep["chosen"]]["t"],
                         "rows": rep["rows"]}
        except Exception as exc:  # noqa: BLE001  one target failing must not stop the others
            out[name] = f"error: {str(exc)[:120]}"
    print(json.dumps({"learn": out}))
    return out


def live_numeric(row, cache):
    sport, market = row["sport"], row["market"]
    o = row.get("openSnap") or {}
    when = parse(row["commence"])
    rh = ra = None
    if not pull_soccer(sport):
        if sport not in cache:
            cache[sport] = load_schedule(sport) if sport in SCHED_FILES else Schedule()
        rh, ra = cache[sport].rest(row["home"], when), cache[sport].rest(row["away"], when)
    if market == "h2h":
        if "draw" in o:
            return None
        sp = None
        p = novig(dec(o.get("home")), dec(o.get("away")))
        return numeric(sport, market, when, sp, p, rh, ra) if p is not None else None
    if market == "total" and (sport in pull.PROB_TOTALS):
        if pull_soccer(sport) and o.get("line") != 2.5:
            return None
        p = novig(dec(o.get("over")), dec(o.get("under")))
        if p is None:
            return None
        f = numeric(sport, market, when, o.get("line"), p, rh, ra)
        if pull_soccer(sport):
            for lg in FD.values():
                f["league_" + lg] = 1.0 if lg == sport else 0.0
        return f
    return numeric(sport, market, when, o.get("line"), None, rh, ra) if o.get("line") is not None else None


def learned_stamp(rows, now, done, dry):
    """Reads from scan_* models that passed learner.py's gate: top 30% predicted moves, fair = current number + the
    predicted move not yet made. Pattern learned-scan-<sport>-<market>, shadow, stake 0."""
    import pickle
    import numpy as np
    import learner  # noqa: F401  (model classes for unpickling)
    reg = pull.load(ROOT / "stats" / "features" / "scan_targets.json", {})
    cache, todo = {}, []
    horizon = pull.iso(now + timedelta(hours=WINDOW_H))
    for name in reg:
        mp = ROOT / "stats" / "models" / f"{name}.pkl"
        if not mp.exists():
            continue
        m = pickle.loads(mp.read_bytes())
        if not m.get("live"):
            continue
        _, sport_l, market = name.split("_", 2)
        pat = "learned-" + name.replace("_", "-")
        for r in rows:
            sp = r.get("sport") or ""
            if (sport_l == "soccer" and not (pull_soccer(sp) and sp in FD.values())) or \
                    (sport_l != "soccer" and sp.lower() != sport_l):
                continue
            if r.get("market") != market or (r.get("id"), pat) in done or not r.get("lastSnap"):
                continue
            if not r.get("commence") or not (pull.iso(now) < r["commence"] <= horizon):
                continue
            f = live_numeric(r, cache)
            if not f:
                continue
            x = np.array([[f.get(k, np.nan) for k in m["keys"]]], dtype=float)
            pred = float(m["model"].predict(m["prep"].transform(x))[0])
            if abs(pred - m["center"]) < m["threshold"] or not pred:
                continue
            side = ("home" if market in ("spread", "h2h") else "over") if pred > 0 else ("away" if market in ("spread", "h2h") else "under")
            unit = m.get("unit", "points")
            remaining = abs(pred) - max(0.0, moved_for_side(r, side, unit))
            if remaining <= (0.15 if unit == "points" else 0.003):
                continue
            minimum = MIN_MOVE["soccer" if pull_soccer(sp) else sp] if (pull_soccer(sp) or sp in MIN_MOVE) else 0.0
            why = (f"Model learned on the scanner's data ({m['kind']}, {len(m['keys'])} data points, passed the "
                   f"out-of-sample gate) predicts a move of {pred:+.3g} from the open for {side}; {remaining:.3g} still "
                   f"to come. Report: stats/models/{name}.json.")
            todo.append((r, pat, fair_for(r, side, remaining, unit), why, remaining < minimum, side))
    return todo


def main(dry=False):
    now = pull.iso(datetime.now(timezone.utc))
    espn = espn_samples()
    ids = {f[3].get("id") for f in espn if f[0] == "NCAAF"}
    samples = espn + cfbd_samples(ids) + soccer_samples() + nfl_samples()
    tests = run_tests(samples)
    store, found = adopt(tests, now, dry)
    if not dry:
        report(store, found, tests, len(samples), now)
    by = defaultdict(int)
    for s in samples:
        by[s[0]] += 1
    print(json.dumps({"samples": len(samples), "bySport": by, "tests": len(tests), "survivors": len(found),
                      "tracking": store["tracking"], "dry": dry}))
    return store, found


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "stamp":
        stamp(dry="--dry" in a)
    elif a and a[0] == "learn":
        learn(force="--force" in a)
    else:
        main(dry="--dry" in a)
