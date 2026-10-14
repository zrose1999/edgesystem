#!/usr/bin/env python3
"""EDGE NFL backtest (v1). Checks the sizing.md values for starting-QB news and wind against
16 seasons of real closing lines and results.

  python3 backtest.py            all seasons from 2010 (stats/backtest_nfl.*) and 2018 on (stats/backtest_nfl_2018.*)
  python3 backtest.py --from 2012 --to 2025

Data (free, nflverse, CC-BY 4.0)
  games.csv           every game: closing spread and total, wind, roof, starting QB ids, score
  player_stats_YYYY   weekly QB passing EPA, to tier each team's regular starter

Method
  For each team-season, the regular starter is the QB with the most starts. A game where a team
  starts anyone else is a backup start, tagged by the regular starter's tier (season passing EPA
  per dropback, the same cut points injury.py uses: above 0.15 elite, -0.05 to 0.15 average,
  below -0.05 weak).
  Two least-squares fits over all seasons at once, each with a home edge and one rating per team
  per season:
    margin = home edge + rating(home) - rating(away) - QB values(home) + QB values(away)
    total  = league level + pace(home) + pace(away) + wind values + QB total values
  Each is fitted twice: on the CLOSING LINE (what the market prices in) and on the FINAL SCORE
  (what actually happened). If the actual effect is bigger than the priced one, the close leaves
  value; if they match, only beating the open can pay.
  Wind values come from outdoor and open-roof games only.
  Standard errors are ordinary least squares; the results side is noisy, so read its error bars.
"""

import csv
import io
import json
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / "stats" / "backtest_nfl.json"
OUT_MD = ROOT / "stats" / "backtest_nfl.md"
GAMES = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
PSTATS = ("https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats_{}.csv",
          "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{}.csv")
TIERS = (("elite", 0.15), ("average", -0.05), ("weak", -99))
WIND = (("wind 15-19", 15, 20), ("wind 20+", 20, 99))
SIZING = {  # sizing.md, for comparison
    "spread": {"elite": (6.5, 8.5), "average": (3.0, 4.0), "weak": (0.5, 1.5)},
    "total": {"qb": (-3.0, -1.5), "wind 15-19": (-3.5, -2.5), "wind 20+": (-4.0, -3.0)},
}


def fetch_csv(url, local=None):
    if local and Path(local).exists():
        return list(csv.DictReader(open(local, newline="")))
    req = urllib.request.Request(url, headers={"User-Agent": "EDGE desk"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode())))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def qb_tiers(seasons):
    """(season, player_id) -> season passing EPA per dropback, from weekly stats."""
    out = {}
    for s in seasons:
        rows = None
        for url in PSTATS:          # nflverse renamed the file from 2025
            try:
                rows = fetch_csv(url.format(s))
                break
            except Exception:
                continue
        if rows is None:
            print("player stats", s, "not found; that season's starters are tiered average")
            continue
        epa, drop = defaultdict(float), defaultdict(float)
        for r in rows:
            if r.get("position") != "QB":
                continue
            pid = r["player_id"]
            epa[pid] += num(r.get("passing_epa")) or 0.0
            drop[pid] += (num(r.get("attempts")) or 0) + (num(r.get("sacks", r.get("sacks_suffered"))) or 0)
        for pid in epa:
            if drop[pid] >= 100:
                out[(s, pid)] = epa[pid] / drop[pid]
    return out


def tier_of(v):
    if v is None:
        return "average"
    for name, cut in TIERS:
        if v > cut:
            return name
    return "weak"


def fit(rows, cols, y):
    """OLS. rows: list of {col: value}. Returns coef and standard error per column."""
    idx = {c: i for i, c in enumerate(cols)}
    X = np.zeros((len(rows), len(cols)))
    for i, r in enumerate(rows):
        for c, v in r.items():
            X[i, idx[c]] = v
    y = np.asarray(y, dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - np.linalg.matrix_rank(X), 1)
    sigma2 = float(resid @ resid) / dof
    cov = sigma2 * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    return {c: (float(beta[idx[c]]), float(se[idx[c]])) for c in cols}, float(np.sqrt(sigma2))


def main(first=2010, last=None, suffix=""):
    out_json = OUT_JSON.with_name(f"backtest_nfl{suffix}.json")
    out_md = OUT_MD.with_name(f"backtest_nfl{suffix}.md")
    games = fetch_csv(GAMES, local=sys.argv[sys.argv.index("--games") + 1] if "--games" in sys.argv else None)
    last = last or max(int(g["season"]) for g in games if g.get("result"))
    games = [g for g in games if first <= int(g["season"]) <= last and g.get("result")
             and num(g.get("spread_line")) is not None and num(g.get("total_line")) is not None
             and g.get("home_qb_id") and g.get("away_qb_id")]
    seasons = sorted({int(g["season"]) for g in games})
    epa = qb_tiers(seasons)

    # Regular starter per team-season.
    starts = defaultdict(Counter)
    for g in games:
        s = int(g["season"])
        starts[(s, g["home_team"])][g["home_qb_id"]] += 1
        starts[(s, g["away_team"])][g["away_qb_id"]] += 1
    regular = {k: c.most_common(1)[0][0] for k, c in starts.items()}

    side_rows, total_rows, close_m, act_m, close_t, act_t, meta = [], [], [], [], [], [], []
    counts = Counter()
    for g in games:
        s = int(g["season"])
        h, a = f"{s}:{g['home_team']}", f"{s}:{g['away_team']}"
        neutral = (g.get("location") or "").lower() == "neutral"
        sr = {"home edge": 0.0 if neutral else 1.0, "R " + h: 1.0, "R " + a: -1.0}
        tr = {"league": 1.0, "P " + h: 1.0, "P " + a: 1.0}
        tags = []
        for team, sign in ((g["home_team"], 1.0), (g["away_team"], -1.0)):
            qb = g["home_qb_id"] if sign > 0 else g["away_qb_id"]
            reg = regular[(s, team)]
            if qb != reg:
                t = tier_of(epa.get((s, reg)))
                key = f"backup for {t} starter"
                sr[key] = sr.get(key, 0.0) - sign       # positive coefficient = points lost by that team
                tr["backup QB (total)"] = tr.get("backup QB (total)", 0.0) + 1.0
                counts[key] += 1
                tags.append((key, sign))
        wind = num(g.get("wind"))
        outdoor = (g.get("roof") or "") in ("outdoors", "open")
        if outdoor and wind is not None:
            for name, lo, hi in WIND:
                if lo <= wind < hi:
                    tr[name] = 1.0
                    counts[name] += 1
                    tags.append((name, 0))
        side_rows.append(sr)
        total_rows.append(tr)
        close_m.append(num(g["spread_line"]))
        act_m.append(num(g["result"]))
        close_t.append(num(g["total_line"]))
        act_t.append(num(g["total"]))
        meta.append(tags)

    side_cols = sorted({c for r in side_rows for c in r})
    total_cols = sorted({c for r in total_rows for c in r})
    m_close, se_mc = fit(side_rows, side_cols, close_m)
    m_act, se_ma = fit(side_rows, side_cols, act_m)
    t_close, se_tc = fit(total_rows, total_cols, close_t)
    t_act, se_ta = fit(total_rows, total_cols, act_t)

    # Does the close leave value? Against-the-close results in each bucket.
    ats = defaultdict(lambda: {"n": 0, "covers": 0, "pushes": 0, "resid": 0.0})
    for g, tags, cm, am, ct, at in zip(games, meta, close_m, act_m, close_t, act_t):
        for tag, side in tags:
            if tag.startswith("backup"):
                d = side * (am - cm)            # margin vs the close, from the backup team's view
                b = ats[tag + " (backup side vs spread)"]
            else:
                d = at - ct
                b = ats[tag + " (over vs total)"]
            b["n"] += 1
            b["resid"] += d
            b["covers"] += d > 0
            b["pushes"] += d == 0

    effects = []
    for key in sorted(k for k in side_cols if k.startswith("backup")):
        tier = key.split()[2]
        effects.append({"what": key, "market": "spread", "n": counts[key],
                        "pricedAtClose": round(m_close[key][0], 2), "pricedSE": round(m_close[key][1], 2),
                        "actual": round(m_act[key][0], 2), "actualSE": round(m_act[key][1], 2),
                        "sizingMd": SIZING["spread"][tier]})
    for key in [c for c in total_cols if c.startswith("wind") or c.startswith("backup")]:
        sz = SIZING["total"]["qb" if key.startswith("backup") else key]
        effects.append({"what": key, "market": "total", "n": counts.get(key, sum(v for k, v in counts.items() if k.startswith("backup"))),
                        "pricedAtClose": round(t_close[key][0], 2), "pricedSE": round(t_close[key][1], 2),
                        "actual": round(t_act[key][0], 2), "actualSE": round(t_act[key][1], 2), "sizingMd": sz})
    vs_close = {k: {"n": v["n"], "coverOrOverRate": round(v["covers"] / max(v["n"] - v["pushes"], 1), 3),
                    "meanVsClose": round(v["resid"] / max(v["n"], 1), 2)} for k, v in sorted(ats.items())}
    result = {"asOf": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "seasons": [seasons[0], seasons[-1]],
              "games": len(games), "homeEdgeClose": round(m_close["home edge"][0], 2),
              "residualSD": {"spreadClose": round(se_mc, 2), "margin": round(se_ma, 2),
                             "totalClose": round(se_tc, 2), "total": round(se_ta, 2)},
              "effects": effects, "againstTheClose": vs_close,
              "read": "pricedAtClose is what the closing line already moved for the event, in points. actual is the "
                      "effect on the final score. sizingMd is the range sizing.md uses. A positive spread number is "
                      "points lost by the team starting a backup. Totals are points added (negative = lower)."}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2) + "\n")

    lines = [f"# NFL backtest: sizing.md vs {seasons[0]}-{seasons[-1]} closing lines",
             "", f"{len(games)} games. Written by backtest.py on {result['asOf'][:10]}. Data: nflverse (CC-BY 4.0).", "",
             "| Event | Market | Games | Priced at close | Actual effect | sizing.md |", "|---|---|---|---|---|---|"]
    for e in effects:
        lines.append(f"| {e['what']} | {e['market']} | {e['n']} | {e['pricedAtClose']:+.2f} ± {e['pricedSE']:.2f} | "
                     f"{e['actual']:+.2f} ± {e['actualSE']:.2f} | {e['sizingMd'][0]:g} to {e['sizingMd'][1]:g} |")
    lines += ["", "Against the close (does betting the event at the close win?)", "",
              "| Bucket | Games | Cover / over rate | Mean vs close |", "|---|---|---|---|"]
    for k, v in vs_close.items():
        lines.append(f"| {k} | {v['n']} | {v['coverOrOverRate']:.1%} | {v['meanVsClose']:+.2f} |")
    out_md.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--from" in a or "--to" in a:
        main(int(a[a.index("--from") + 1]) if "--from" in a else 2010, int(a[a.index("--to") + 1]) if "--to" in a else None,
             suffix="_custom")
    else:
        main(2010)
        main(2018, suffix="_2018")
