#!/usr/bin/env python3
"""EDGE tennis research: does a surface Elo know anything Pinnacle's price does not?

  python3 tennis_backtest.py     downloads tennis-data.co.uk ATP and WTA results with Pinnacle odds (2015 on),
                                 writes stats/backtest_tennis.md and .json

Model: Elo per player, overall and per surface (Hard, Clay, Grass; Carpet counts as Hard), K = 250 / (matches + 5)^0.4
(the FiveThirtyEight tennis form). Probability = 50/50 blend of overall and surface Elo, walk-forward (each match
rated only from earlier matches). Players need 20+ prior matches.
Market: Pinnacle (PSW/PSL) with the margin removed (Shin, two-way). tennis-data's odds are taken close to the start.
Tests: log loss of model vs market; slope of (result - market) on (model - market) [above 0 means the model adds
information the market missed]; best blend weight; flat-stake ROI betting the model's side when it beats the
market price by 3+ points.
"""

import io
import json
import math
import urllib.request
from collections import defaultdict
from pathlib import Path

import openpyxl

import fair

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "backtest_tennis"
YEARS = range(2015, 2027)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 EDGE research"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def rows_for(tour, year):
    url = f"http://www.tennis-data.co.uk/{year}/{'' if tour == 'ATP' else 'w'}{year}.xlsx"
    try:
        wb = openpyxl.load_workbook(io.BytesIO(fetch(url)), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        print(tour, year, exc)
        return []
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    head = [str(h).strip() if h is not None else "" for h in next(it)]
    out = []
    for r in it:
        d = dict(zip(head, r))
        if not d.get("Winner") or not d.get("Date"):
            continue
        out.append(d)
    return out


def am(dec):
    return round((dec - 1) * 100) if dec >= 2 else round(-100 / (dec - 1))


def k_factor(n):
    return 250 / (n + 5) ** 0.4


def run():
    matches = []
    for tour in ("ATP", "WTA"):
        for y in YEARS:
            for d in rows_for(tour, y):
                if str(d.get("Comment", "")).strip().lower() not in ("completed", ""):
                    continue          # walkovers and retirements say little about strength
                matches.append((tour, d))
    matches.sort(key=lambda x: (str(x[1]["Date"]), x[0]))
    elo = {t: defaultdict(lambda: 1500.0) for t in ("ATP", "WTA")}
    selo = {t: defaultdict(lambda: 1500.0) for t in ("ATP", "WTA")}
    n = {t: defaultdict(int) for t in ("ATP", "WTA")}
    sn = {t: defaultdict(int) for t in ("ATP", "WTA")}
    recs = []
    for tour, d in matches:
        w, l = str(d["Winner"]).strip(), str(d["Loser"]).strip()
        surf = {"Carpet": "Hard"}.get(str(d.get("Surface") or "Hard"), str(d.get("Surface") or "Hard"))
        E, S, N, SN = elo[tour], selo[tour], n[tour], sn[tour]
        pe = 1 / (1 + 10 ** ((E[l] - E[w]) / 400))
        ps = 1 / (1 + 10 ** ((S[(l, surf)] - S[(w, surf)]) / 400))
        p_model = 0.5 * pe + 0.5 * ps                      # winner's probability
        try:
            psw, psl = float(d.get("PSW")), float(d.get("PSL"))
        except (TypeError, ValueError):
            psw = psl = None
        if psw and psl and psw > 1 and psl > 1 and min(N[w], N[l]) >= 20:
            p_mkt = fair.probs({"w": am(psw), "l": am(psl)}, ["w", "l"])["w"]
            # store from a fixed side (alphabetical) so the outcome is not always 1
            if w < l:
                recs.append((tour, str(d["Date"])[:10], surf, p_model, p_mkt, 1.0, (psw, psl)))
            else:
                recs.append((tour, str(d["Date"])[:10], surf, 1 - p_model, 1 - p_mkt, 0.0, (psl, psw)))
        kw, kl = k_factor(N[w]), k_factor(N[l])
        E[w] += kw * (1 - pe); E[l] -= kl * (1 - pe)
        skw, skl = k_factor(SN[(w, surf)]), k_factor(SN[(l, surf)])
        S[(w, surf)] += skw * (1 - ps); S[(l, surf)] -= skl * (1 - ps)
        N[w] += 1; N[l] += 1; SN[(w, surf)] += 1; SN[(l, surf)] += 1
    return recs


def analyse(recs):
    def ll(rows, k):
        t = 0.0
        for _, _, _, pm, pk, y, _ in rows:
            p = pk + k * (pm - pk)
            p = min(max(p, 1e-6), 1 - 1e-6)
            t -= y * math.log(p) + (1 - y) * math.log(1 - p)
        return t / len(rows)

    def slope(rows):
        xs = [pm - pk for _, _, _, pm, pk, _, _ in rows]
        ys = [y - pk for _, _, _, _, pk, y, _ in rows]
        nn = len(xs)
        mx, my = sum(xs) / nn, sum(ys) / nn
        sxx = sum((x - mx) ** 2 for x in xs)
        k = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
        b = my - k * mx
        se = (sum((y - b - k * x) ** 2 for x, y in zip(xs, ys)) / (nn - 2) / sxx) ** 0.5
        return k, se

    def roi(rows, thr=0.03):
        bets = units = 0.0
        for _, _, _, pm, pk, y, dec in rows:
            dec_a, dec_b = dec            # Pinnacle decimal prices of the stored side and the other side
            if pm - pk >= thr:
                bets += 1; units += (dec_a - 1) if y == 1 else -1
            elif pk - pm >= thr:
                bets += 1; units += (dec_b - 1) if y == 0 else -1
        return int(bets), units

    out = {}
    groups = {"all": recs}
    for tour in ("ATP", "WTA"):
        groups[tour] = [r for r in recs if r[0] == tour]
    for surf in ("Hard", "Clay", "Grass"):
        groups[surf] = [r for r in recs if r[2] == surf]
    half = sorted(recs, key=lambda r: r[1])
    groups["2015-2020"] = [r for r in half if r[1] < "2021"]
    groups["2021-2026"] = [r for r in half if r[1] >= "2021"]
    for name, rows in groups.items():
        if len(rows) < 200:
            continue
        k, se = slope(rows)
        best = min((i / 20 for i in range(0, 11)), key=lambda kk: ll(rows, kk))
        b, u = roi(rows)
        out[name] = {"n": len(rows), "llMarket": round(ll(rows, 0), 4), "llModel": round(ll(rows, 1), 4),
                     "slope": round(k, 3), "se": round(se, 3), "bestBlend": best, "llBest": round(ll(rows, best), 4),
                     "bets": b, "unitsFlat": round(u, 1), "roi": round(u / b, 3) if b else None}
    return out


def main():
    recs = run()
    res = analyse(recs)
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1))
    lines = ["# Tennis: surface Elo vs Pinnacle (tennis_backtest.py)", "",
             "Walk-forward Elo (overall + surface, 50/50), players with 20+ prior matches, completed matches only.",
             "Slope: (result - market) on (model - market); above 0 means the model adds information. "
             "Best blend: weight on the model that minimises log loss (0 = trust the market).", "",
             "| Group | Matches | Log loss market | Log loss model | Slope | se | Best blend | Bets (3+ pts) | Units | ROI |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in res.items():
        lines.append(f"| {k} | {v['n']} | {v['llMarket']} | {v['llModel']} | {v['slope']:+.3f} | {v['se']} | "
                     f"{v['bestBlend']} | {v['bets']} | {v['unitsFlat']:+.1f} | {v['roi'] if v['roi'] is not None else 'n/a'} |")
    OUT.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
