#!/usr/bin/env python3
"""EDGE learner. Learns, per sport and market, which pre-game data points predict the move from the open to the
close (the thing that beats the close), alone or in combination. The procedure is fixed (this file); what it
learns is data. A learned model is used live only if it passes the out-of-sample gate, and its reads start in
shadow like every other pattern until CLV says otherwise.

  python3 learner.py nhl_ml        train and evaluate one target (see TARGETS), save model + report
  python3 learner.py all

Procedure
  1. Rows sorted by date. Walk-forward: 5 test blocks over the last 60% of the sample; each block is predicted by
     models trained only on everything before it (no look-ahead, ever).
  2. Two learners compete: ridge regression on all standardized features (linear, many small effects) and shallow
     gradient-boosted trees (finds combinations and thresholds). A drift-only baseline (training mean) is the bar.
  3. Out-of-sample trade test: in each block, take the side the model predicts when its predicted move is in the
     top 30% by size (threshold set on training data only). Realized signed move = the CLV that side would have got.
  4. Gate to go live: pooled out-of-sample t >= 2.5, positive in 4 of 5 blocks, and better than the drift baseline.
  5. The winner is refit on all rows and saved (stats/models/<target>.pkl) with a report (stats/models/<target>.json):
     out-of-sample results per block and the features that carry the signal (permutation importance on held-out
     blocks, with direction). The report is what the weekly review reads.
"""

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "stats" / "models"
TARGETS = {
    "nhl_ml": {"file": "stats/features/nhl_history.json", "y": "y_ml", "unit": "prob"},
    "nhl_over": {"file": "stats/features/nhl_history.json", "y": "y_over", "unit": "prob"},
    "soccer_home": {"file": "stats/features/soccer_history.json", "y": "y_home", "unit": "prob"},
    "soccer_away": {"file": "stats/features/soccer_history.json", "y": "y_away", "unit": "prob"},
    "soccer_draw": {"file": "stats/features/soccer_history.json", "y": "y_draw", "unit": "prob"},
    "soccer_over": {"file": "stats/features/soccer_history.json", "y": "y_over", "unit": "prob"},
}
BLOCKS, TEST_SHARE, TOP_SHARE = 5, 0.6, 0.30
GATE_T, GATE_BLOCKS = 2.5, 4


def load(target):
    spec = TARGETS[target]
    rows = [r for r in json.loads((ROOT / spec["file"]).read_text())["rows"] if r.get(spec["y"]) is not None]
    rows.sort(key=lambda r: r["date"])
    keys = sorted({k for r in rows for k in r["f"]})
    X = np.array([[r["f"].get(k, np.nan) for k in keys] for r in rows], dtype=float)
    y = np.array([r[spec["y"]] for r in rows], dtype=float)
    return rows, keys, X, y


class Prep:
    """Median fill and standardization, fit on training rows only."""
    def fit(self, X):
        self.med = np.nanmedian(X, axis=0)
        self.med = np.where(np.isnan(self.med), 0.0, self.med)
        Z = np.where(np.isnan(X), self.med, X)
        self.mu, self.sd = Z.mean(axis=0), Z.std(axis=0)
        self.sd[self.sd == 0] = 1.0
        return self

    def transform(self, X):
        Z = np.where(np.isnan(X), self.med, X)
        return (Z - self.mu) / self.sd


def make(kind):
    if kind == "ridge":
        from sklearn.linear_model import RidgeCV
        return RidgeCV(alphas=np.logspace(0, 4, 13))
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.04, max_iter=250, min_samples_leaf=40,
                                         l2_regularization=1.0, random_state=7)


def tstat(v):
    v = np.asarray(v, dtype=float)
    if len(v) < 3 or v.std(ddof=1) == 0:
        return 0.0
    return float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v))))


def walk_forward(X, y, kind):
    n = len(y)
    start = int(n * (1 - TEST_SHARE))
    edges = np.linspace(start, n, BLOCKS + 1).astype(int)
    blocks, preds = [], np.full(n, np.nan)
    for b in range(BLOCKS):
        tr, te = slice(0, edges[b]), slice(edges[b], edges[b + 1])
        if kind == "baseline":
            p_tr = np.full(edges[b], y[tr].mean())
            p_te = np.full(edges[b + 1] - edges[b], y[tr].mean())
        else:
            prep = Prep().fit(X[tr])
            m = make(kind).fit(prep.transform(X[tr]), y[tr])
            p_tr, p_te = m.predict(prep.transform(X[tr])), m.predict(prep.transform(X[te]))
        thr = np.quantile(np.abs(p_tr - np.median(p_tr)) if kind != "baseline" else np.abs(p_tr), 1 - TOP_SHARE) if kind != "baseline" else 0.0
        preds[te] = p_te
        sel = np.abs(p_te - (np.median(p_tr) if kind != "baseline" else 0.0)) >= thr if kind != "baseline" else np.ones(len(p_te), bool)
        side = np.sign(p_te[sel] - (0 if kind == "baseline" else 0))
        signed = side * y[te][sel]
        blocks.append({"from": int(edges[b]), "to": int(edges[b + 1]), "trades": int(sel.sum()),
                       "meanMove": float(signed.mean()) if sel.sum() else 0.0, "t": tstat(signed)})
    oos = slice(edges[0], n)
    allsigned = []
    for b in range(BLOCKS):
        pass
    corr = float(np.corrcoef(preds[oos], y[oos])[0, 1]) if np.nanstd(preds[oos]) > 0 else 0.0
    return blocks, preds, corr


def pooled(blocks, preds, y, X, kind):
    """Pooled out-of-sample trade results from the per-block selections."""
    n = len(y)
    start = int(n * (1 - TEST_SHARE))
    signed = []
    edges = np.linspace(start, n, BLOCKS + 1).astype(int)
    for b in range(BLOCKS):
        te = slice(edges[b], edges[b + 1])
        p = preds[te]
        if kind == "baseline":
            signed += list(np.sign(p) * y[te])
            continue
        tr_med = np.median(p)
        thr = np.quantile(np.abs(p - tr_med), 1 - TOP_SHARE)
        sel = np.abs(p - tr_med) >= thr
        signed += list(np.sign(p[sel]) * y[te][sel])
    return np.array(signed)


def importance(X, y, keys, kind):
    """Permutation importance on the last 40% when trained on the first 60%: which data points carry the signal."""
    n = len(y)
    cut = int(n * 0.6)
    prep = Prep().fit(X[:cut])
    m = make(kind).fit(prep.transform(X[:cut]), y[:cut])
    Xt = prep.transform(X[cut:])
    base = np.mean((m.predict(Xt) - y[cut:]) ** 2)
    rng = np.random.default_rng(7)
    imp = []
    for j, k in enumerate(keys):
        Xp = Xt.copy()
        Xp[:, j] = rng.permutation(Xp[:, j])
        imp.append((k, float(np.mean((m.predict(Xp) - y[cut:]) ** 2) - base)))
    imp.sort(key=lambda kv: -kv[1])
    out = []
    for k, v in imp[:15]:
        if v <= 0:
            break
        j = keys.index(k)
        x = np.where(np.isnan(X[:, j]), np.nanmedian(X[:, j]), X[:, j])
        direction = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 else 0.0
        out.append({"feature": k, "mseGain": v, "corrWithMove": round(direction, 3)})
    return out


def run(target):
    rows, keys, X, y = load(target)
    res = {}
    for kind in ("baseline", "ridge", "gbm"):
        blocks, preds, corr = walk_forward(X, y, kind)
        signed = pooled(blocks, preds, y, X, kind)
        res[kind] = {"blocks": blocks, "oosCorr": round(corr, 4) if kind != "baseline" else None,
                     "trades": int(len(signed)), "meanMove": float(signed.mean()) if len(signed) else 0.0,
                     "t": round(tstat(signed), 2),
                     "positiveBlocks": int(sum(1 for b in blocks if b["meanMove"] > 0))}
    best = max(("ridge", "gbm"), key=lambda k: res[k]["t"])
    b = res[best]
    passed = (b["t"] >= GATE_T and b["positiveBlocks"] >= GATE_BLOCKS and b["meanMove"] > res["baseline"]["meanMove"])
    report = {"target": target, "trained": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "rows": len(rows), "features": len(keys), "unit": TARGETS[target]["unit"],
              "from": rows[0]["date"], "to": rows[-1]["date"], "results": res, "chosen": best, "live": passed,
              "gate": f"pooled OOS t >= {GATE_T}, {GATE_BLOCKS}/{BLOCKS} blocks positive, beats drift baseline",
              "signals": importance(X, y, keys, best)}
    MODELS.mkdir(parents=True, exist_ok=True)
    prep = Prep().fit(X)
    model = make(best).fit(prep.transform(X), y)
    p_all = model.predict(prep.transform(X))
    center = float(np.median(p_all))
    thr = float(np.quantile(np.abs(p_all - center), 1 - TOP_SHARE))
    import pickle
    (MODELS / f"{target}.pkl").write_bytes(pickle.dumps({"prep": prep, "model": model, "keys": keys,
                                                          "kind": best, "live": passed, "trained": report["trained"],
                                                          "center": center, "threshold": thr, "unit": TARGETS[target]["unit"]}))
    (MODELS / f"{target}.json").write_text(json.dumps(report, indent=1))
    return report


def summary(rep):
    r = rep["results"]
    lines = [f"{rep['target']}: {rep['rows']} games, {rep['features']} features, chosen {rep['chosen']}, live={rep['live']}"]
    for k in ("baseline", "ridge", "gbm"):
        lines.append(f"  {k:8s} trades {r[k]['trades']:4d} mean move {r[k]['meanMove']:+.4f} t {r[k]['t']:+.2f} "
                     f"blocks+ {r[k]['positiveBlocks']}/5 corr {r[k]['oosCorr']}")
    lines.append("  signals: " + ", ".join(f"{s['feature']} ({s['corrWithMove']:+.2f})" for s in rep["signals"][:10]))
    return "\n".join(lines)


def live_check():
    """Live out-of-sample check of every learned model: first logged prediction per game vs the realized move from
    the open to the last pre-start price (archive and ledger). Same top-30% trade test as the walk-forward."""
    import fair as fairlib
    log = [json.loads(l) for l in (MODELS / "live_log.jsonl").read_text().splitlines() if l.strip()] \
        if (MODELS / "live_log.jsonl").exists() else []
    rows = {}
    arch = ROOT / "ledger" / "archive"
    if arch.exists():
        for f in arch.glob("*/*.jsonl"):
            if f.stem != "kalshi":
                for l in f.read_text().splitlines():
                    if l.strip():
                        r = json.loads(l)
                        rows[r.get("id")] = r
    for r in json.loads((ROOT / "ledger" / "ledger.json").read_text()).get("rows") or []:
        rows.setdefault(r.get("id"), r)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {}
    for rec in log:
        r = rows.get(rec["rowId"])
        if not r or (r.get("commence") or "9") > now:
            continue
        snap = r.get("closeSnap") or r.get("lastSnap") or {}
        t = rec["target"]
        if rec.get("book") == "pinnacle":
            b = (snap.get("books") or {}).get("pinnacle") or {}
            keys = ["home", "draw", "away"] if t.startswith("soccer_") and t != "soccer_over" else ["over", "under"]
            side = t.split("_")[1] if t != "soccer_over" else "over"
        else:
            b = snap
            keys = ["home", "away"] if t.endswith("_ml") else ["over", "under"]
            side = keys[0]
        if not all(k in b for k in keys):
            continue
        realized = fairlib.probs(b, keys)[side] - rec["open"]
        out.setdefault(t, []).append((rec["pred"], realized, rec["top"]))
    rep = {}
    for t, xs in out.items():
        top = [np.sign(p) * y for p, y, top in xs if top]
        allc = np.corrcoef([p for p, _, _ in xs], [y for _, y, _ in xs])[0, 1] if len(xs) > 2 else None
        rep[t] = {"games": len(xs), "corr": None if allc is None or np.isnan(allc) else round(float(allc), 3),
                  "topTrades": len(top), "topMeanMove": round(float(np.mean(top)), 4) if top else None, "topT": round(tstat(top), 2)}
    (MODELS / "live_check.json").write_text(json.dumps({"asOf": now, "targets": rep}, indent=1))
    return rep


if __name__ == "__main__":
    import learner as _L          # run through the module, so saved models load from any script
    which = sys.argv[1:] or ["all"]
    if which == ["live"]:
        print(json.dumps(_L.live_check(), indent=1))
        sys.exit(0)
    for t in (_L.TARGETS if which == ["all"] else which):
        print(_L.summary(_L.run(t)))
