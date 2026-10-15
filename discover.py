#!/usr/bin/env python3
"""EDGE discovery engine. Searches every sport's history for situations where the price moves the same way from
the open to the close, which is exactly what beats the close. Writes stats/discovery.md and .json for the weekly
review. It proposes; it never adopts. A candidate becomes a pattern only through a reviewed change Zack approves.

  python3 discover.py

Sources
  ESPN line history (stats/<sport>_games.json): DraftKings open and close, NBA, NHL, NCAAF, EPL.
  EDGE's own archive (ledger/archive/*/<sport>.jsonl + finished rows in the ledger): open and last pre-start or
    close snapshot for every sport and market, with every book (so it can test, e.g., whether DraftKings moves
    toward Pinnacle's opening price).
  Kalshi price history (ledger/archive/*/kalshi.jsonl): first-seen and last pre-start mid per market.

Rules for a candidate: 150+ games, |t| >= 3, the same sign in both halves of the sample (time-ordered), and the
average move at least MIN_EFFECT. Every test run is counted and reported (the number of tests matters: with ~200
tests, a t of 3 happens by chance about once in 2-3 reports, so a candidate is a lead, not a result).
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import fair as fairlib
import pull

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "discovery"
ARCH = ROOT / "ledger" / "archive"
MIN_N, MIN_T = 150, 3.0
MIN_EFFECT = {"prob": 0.004, "points": 0.25}


def novig2(a, b):
    try:
        return fairlib.probs({"a": a, "b": b}, ["a", "b"])["a"]
    except Exception:  # noqa: BLE001
        return None


def stat(xs):
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    sd = (sum((x - m) ** 2 for x in xs) / (n - 1)) ** 0.5
    se = sd / n ** 0.5 if sd else 0.0
    h = n // 2
    return {"n": n, "mean": m, "se": se, "t": (m / se if se else 0.0),
            "first": sum(xs[:h]) / max(h, 1), "second": sum(xs[h:]) / max(n - h, 1)}


def espn_samples():
    """(sport, market, unit, features, move, date) from ESPN open/close histories."""
    out = []
    for sport in ("NBA", "NHL", "NCAAF", "EPL"):
        g = pull.load(ROOT / "stats" / f"{sport.lower()}_games.json", {}).get("games") or {}
        for x in (g.values() if isinstance(g, dict) else g):
            L = x.get("lines") or {}
            if not x.get("final") or not L:
                continue
            d = x.get("date") or ""
            wd = datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%a") if d else "?"
            if L.get("spreadOpen") is not None and L.get("spreadClose") is not None:
                so = L["spreadOpen"]
                fav = "home fav 7+" if so <= -7 else "home fav 3-7" if so <= -3 else "pick'em" if so < 3 else "home dog 3-7" if so < 7 else "home dog 7+"
                out.append((sport, "spread", "points", {"size": fav, "day": wd}, L["spreadClose"] - so, d))
            if L.get("totalOpen") is not None and L.get("totalClose") is not None:
                out.append((sport, "total", "points", {"day": wd}, L["totalClose"] - L["totalOpen"], d))
            if all(L.get(k) for k in ("mlHomeOpen", "mlAwayOpen", "mlHomeClose", "mlAwayClose")):
                po, pc = novig2(L["mlHomeOpen"], L["mlAwayOpen"]), novig2(L["mlHomeClose"], L["mlAwayClose"])
                if po is not None and pc is not None:
                    size = "home fav 65%+" if po >= 0.65 else "home fav 55-65%" if po >= 0.55 else "even" if po >= 0.45 else "home dog 35-45%" if po >= 0.35 else "home dog <35%"
                    out.append((sport, "h2h", "prob", {"size": size, "day": wd}, pc - po, d))
    return out


def archive_rows():
    rows = []
    if ARCH.exists():
        for f in sorted(ARCH.glob("*/*.jsonl")):
            if f.stem == "kalshi":
                continue
            rows += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    rows += [r for r in pull.load(pull.LEDGER, {"rows": []}).get("rows") or [] if r.get("final")]
    return rows


def edge_samples(rows):
    """From EDGE's own snapshots: open vs last pre-start (or close) at the print book, plus book-gap features."""
    out = []
    for r in rows:
        o = r.get("openSnap")
        c = r.get("closeSnap") or r.get("lastSnap")
        if not o or not c or o.get("time") == c.get("time"):
            continue
        sport, market = r.get("sport"), r.get("market")
        d = r.get("commence") or ""
        feats = {"day": datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%a") if d else "?"}
        ob = o.get("books") or {}
        pin = ob.get("pinnacle")
        if market in ("spread", "total") and sport not in pull.PROB_TOTALS:
            if o.get("line") is None or c.get("line") is None:
                continue
            if pin and pin.get("line") is not None:
                gap = pin["line"] - o["line"]
                feats["print vs Pinnacle at open"] = "Pinnacle higher" if gap > 0 else "Pinnacle lower" if gap < 0 else "same"
            out.append((sport, market, "points", feats, c["line"] - o["line"], d))
        else:
            keys = ["home", "away"] if market == "h2h" else ["over", "under"]
            if any(k not in o or k not in c for k in keys) or (market == "total" and o.get("line") != c.get("line")):
                continue
            po = fairlib.probs(o, keys + (["draw"] if "draw" in o and "draw" in c else []))[keys[0]]
            pc = fairlib.probs(c, keys + (["draw"] if "draw" in o and "draw" in c else []))[keys[0]]
            if pin and all(k in pin for k in keys):
                pp = fairlib.probs(pin, keys + (["draw"] if "draw" in pin else []))[keys[0]]
                gap = pp - po
                feats["Pinnacle vs print at open"] = "Pinnacle 1pt+ higher" if gap >= 0.01 else "Pinnacle 1pt+ lower" if gap <= -0.01 else "within 1pt"
            out.append((sport, market, "prob", feats, pc - po, d))
    return out


def kalshi_samples():
    out = []
    if ARCH.exists():
        for f in sorted(ARCH.glob("*/kalshi.jsonl")):
            for l in f.read_text().splitlines():
                if not l.strip():
                    continue
                r = json.loads(l)
                if r.get("open") is None or r.get("last") is None or r.get("openT") == r.get("lastT"):
                    continue
                o = r["open"]
                size = "fav 65c+" if o >= 0.65 else "35-65c" if o >= 0.35 else "longshot <35c"
                kind = "tie" if "tie" in (r.get("title") or "").lower() else "yes"
                out.append(((r.get("sport") or "?") + " (Kalshi)", kind, "prob", {"price": size}, r["last"] - o, r.get("start") or ""))
    return out


def main():
    samples = espn_samples() + edge_samples(archive_rows()) + kalshi_samples()
    groups = defaultdict(list)
    for sport, market, unit, feats, move, d in samples:
        groups[(sport, market, unit, "all", "all")].append((d, move))
        for k, v in feats.items():
            groups[(sport, market, unit, k, v)].append((d, move))
    tests, cands = [], []
    for (sport, market, unit, k, v), xs in groups.items():
        xs.sort()
        s = stat([m for _, m in xs])
        if not s or s["n"] < 30:
            continue
        rec = {"sport": sport, "market": market, "unit": unit, "feature": k, "value": v, **{a: round(b, 4) for a, b in s.items()}}
        tests.append(rec)
        same_sign = (s["first"] > 0) == (s["second"] > 0) and s["first"] and s["second"]
        if s["n"] >= MIN_N and abs(s["t"]) >= MIN_T and same_sign and abs(s["mean"]) >= MIN_EFFECT[unit]:
            cands.append(rec)
    cands.sort(key=lambda r: -abs(r["t"]))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.with_suffix(".json").write_text(json.dumps({"asOf": now, "samples": len(samples), "tests": len(tests),
                                                    "candidates": cands}, indent=1))
    md = ["# Discovery report (discover.py)", "",
          f"{now}. {len(samples)} game-markets, {len(tests)} situations tested. Candidates: {MIN_N}+ games, |t| >= {MIN_T}, "
          "same direction in both halves. Moves are close minus open: home line (spreads), total line, home or over "
          "probability. Leads for the weekly review, not patterns.", "",
          "| Sport | Market | Situation | Games | Avg move | t | 1st half | 2nd half |", "|---|---|---|---|---|---|---|---|"]
    for c in cands[:40]:
        f = "{:+.2f} pts" if c["unit"] == "points" else "{:+.2%}"
        md.append(f"| {c['sport']} | {c['market']} | {c['feature']}: {c['value']} | {c['n']} | {f.format(c['mean'])} | "
                  f"{c['t']:+.1f} | {f.format(c['first'])} | {f.format(c['second'])} |")
    if not cands:
        md.append("| none yet | | | | | | | |")
    OUT.with_suffix(".md").write_text("\n".join(md) + "\n")
    print(json.dumps({"samples": len(samples), "tests": len(tests), "candidates": len(cands)}))


if __name__ == "__main__":
    main()
