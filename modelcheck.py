#!/usr/bin/env python3
"""EDGE model and move checks. Added 2026-10-21 (north-star plan, gaps 4 and 5); history in changelog.md.

Two questions for every pattern, on its counted reads (one per pattern, row and side, picks and leans alike):

  move check   Did the line move the way the read said it would? predicted = how far the read's fair number sat from
               the market at the stamp, toward the side taken; realized = how far the market actually moved toward
               that side by the close. Points for spreads and point totals, no-vig probability otherwise. Grades
               every read, leans included, in days instead of months.
  model check  Benter's test: does the read's probability add information to the market's own no-vig probability at
               the stamp? logLossGain = mean of log(p_model on what happened) - log(p_market on what happened).
               Above 0 means the model knew something the price did not. Needs many settled reads to mean anything.

Verdicts (move check, used by edge_stack.py): "proven" when n >= MIN_N, mean realized move toward the side > 0
and t >= PROVEN_T; otherwise "collecting". Nothing here retires or removes anything (learning phase): a proven
pattern only gains the right to feed edge-stack.

Writes stats/modelcheck.json (job output, single writer: the data job). Run at the end of grade.py.
"""

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import fair as fairlib

ROOT = Path(__file__).resolve().parent
PICKS = ROOT / "ledger" / "picks.json"
LEDGER = ROOT / "ledger" / "ledger.json"
OUT = ROOT / "stats" / "modelcheck.json"
MIN_N = 30
PROVEN_T = 2.0
PROB_TOTALS = {"NHL", "MLB", "EPL", "UCL", "MLS", "LaLiga", "SerieA", "Bundesliga", "Ligue1", "UEL"}
PER_POINT = {("NFL", "spread"): 0.030, ("NFL", "total"): 0.022, ("NCAAF", "spread"): 0.025, ("NCAAF", "total"): 0.018,
             ("NBA", "spread"): 0.030, ("NBA", "total"): 0.025}


def load(path, default):
    try:
        return json.loads(Path(path).read_text())
    except Exception:  # noqa: BLE001
        return default


def implied(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def tstat(v):
    n = len(v)
    if n < 2:
        return 0.0
    m = sum(v) / n
    var = sum((x - m) ** 2 for x in v) / (n - 1)
    return 0.0 if var == 0 else m / math.sqrt(var / n)


def novig_side(prices, side):
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in (prices or {})]
    if side not in keys or len(keys) < 2:
        return None
    try:
        return fairlib.probs({k: prices[k] for k in keys})[side]
    except Exception:  # noqa: BLE001
        return None


def point_market(p):
    return p["market"] == "spread" or (p["market"] == "total" and p["sport"] not in PROB_TOTALS)


def fair_side_prob(p, p_mkt):
    """The read's own probability for the side it took."""
    side, fair = p["side"], p.get("fair")
    if fair is None:
        return None
    if p.get("bookAtPick"):                # sharp.py, learn_live.py, edge_stack sharp-drift: fair is the side's own
        return fair
    if point_market(p):
        slope = PER_POINT.get((p["sport"], p["market"]), 0.03)
        return None if p_mkt is None else min(max(p_mkt + slope * (p.get("edge") or 0), 0.01), 0.99)
    return fair if side in ("home", "over") else 1 - fair    # make_read: fair is HOME (h2h) or OVER (prob totals)


def one(p, row):
    """(predicted move, realized move, unit, model prob, market prob, outcome) for one read; None when unknown."""
    close, side = row.get("closeSnap"), p.get("side")
    if not close or not side or side not in close:
        return None
    p_mkt = novig_side(p.get("marketPrices"), side)
    if point_market(p):
        m0, m1 = p.get("marketNumber"), close.get("line")
        if m0 is None or m1 is None:
            return None
        if p["market"] == "spread":
            realized = (m0 - m1) if side == "home" else (m1 - m0)   # home wants the home line to fall
        else:
            realized = (m1 - m0) if side == "over" else (m0 - m1)
        predicted, unit = p.get("edge"), "points"
        if p.get("edgeUnit") == "prob" and predicted is not None:   # priced in probability on a point market
            predicted = predicted / PER_POINT.get((p["sport"], p["market"]), 0.03)
    else:
        if p_mkt is None:
            return None
        same_line = p["market"] == "h2h" or close.get("line") == p.get("marketNumber")
        p_close = novig_side(close, side) if same_line else None
        if p_close is None:
            return None
        f = fair_side_prob(p, p_mkt)
        if f is None:
            return None
        predicted, realized, unit = f - p_mkt, p_close - p_mkt, "prob"
    res = p.get("result")
    outcome = 1 if res == "win" else 0 if res == "loss" else None
    return predicted, realized, unit, fair_side_prob(p, p_mkt), p_mkt, outcome


def counted(picks):
    first = {}
    for p in sorted(picks, key=lambda p: (p.get("kind", "pick") != "pick", p.get("pickedAt") or "")):
        # Gated reads (Pinnacle gate, 2026-10-28) still carry the model's prediction, so the move check keeps
        # measuring the model on them; the gate only decides what counts toward a pattern's CLV record.
        if p.get("kind", "pick") in ("pick", "lean", "gated") and p.get("side") and p.get("pattern"):
            first.setdefault((p["pattern"], p.get("rowId"), p["side"]), p)
    return list(first.values())


def build():
    picks = load(PICKS, {"picks": []}).get("picks") or []
    rows = {r.get("id"): r for r in load(LEDGER, {"rows": []}).get("rows") or []}
    groups = defaultdict(list)
    for p in counted(picks):
        got = one(p, rows.get(p.get("rowId")) or {})
        if got:
            groups[(p["pattern"], got[2])].append(got)
    out = {}
    for (pat, unit), g in sorted(groups.items()):
        pred = [x[0] for x in g if x[0] is not None]
        real = [x[1] for x in g]
        t = tstat(real)
        mean_r = sum(real) / len(real)
        ll = []
        for _, _, _, pm, p0, y in g:
            if y is None or pm is None or p0 is None or not (0 < pm < 1 and 0 < p0 < 1):
                continue
            ll.append(math.log(pm if y else 1 - pm) - math.log(p0 if y else 1 - p0))
        verdict = "proven" if len(real) >= MIN_N and mean_r > 0 and t >= PROVEN_T else "collecting"
        key = pat if pat not in out else f"{pat}|{unit}"
        out[key] = {
            "pattern": pat, "unit": unit, "n": len(real),
            "meanPredicted": round(sum(pred) / len(pred), 4) if pred else None,
            "meanRealized": round(mean_r, 4), "tRealized": round(t, 2),
            "capture": round(mean_r / (sum(pred) / len(pred)), 2) if pred and sum(pred) else None,
            "rightWay": round(sum(1 for r in real if r > 0) / max(1, sum(1 for r in real if r != 0)), 3),
            "noMove": sum(1 for r in real if r == 0),
            "logLossGain": {"n": len(ll), "mean": round(sum(ll) / len(ll), 5) if ll else None,
                            "t": round(tstat(ll), 2)},
            "verdict": verdict,
        }
    report = {
        "asOf": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rules": (f"Move check: predicted vs realized move toward the side, open of the read to the print close. Proven "
                  f"at n >= {MIN_N}, mean realized > 0, t >= {PROVEN_T}: the pattern may feed edge-stack. Model check: "
                  "log-loss gain over the market's no-vig price at the stamp (Benter). Nothing here retires a pattern."),
        "patterns": out,
        "proven": sorted(v["pattern"] for v in out.values() if v["verdict"] == "proven"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    return {"modelcheck": len(out), "proven": report["proven"]}


def proven():
    """Patterns whose predicted moves have come true (used by edge_stack.py). Empty if the report is missing."""
    return set(load(OUT, {}).get("proven") or [])


if __name__ == "__main__":
    print(json.dumps(build()))
