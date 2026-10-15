#!/usr/bin/env python3
"""EDGE generic feature store from the desk's own archive. Gives every sport and market a learned model as soon as
EDGE has collected enough of its own history, with no strategy written by hand.

  python3 features_archive.py    build stats/features/archive_<sport>_<market>.json for every sport/market with
                                 MIN_ROWS+ finished games, and register them as learner targets
                                 (stats/features/archive_targets.json)

Every finished row in ledger/archive and the ledger with an opening snapshot and a later pre-start snapshot (every
book's prices at both) becomes a training row. Features, all known at the open:
  the opening no-vig price (and line), how far each US book was from Pinnacle at the open, how much the books
  disagreed (spread of their implied probabilities, lines), whether the print book was the best price, hours from
  the open to the start, day of week and hour, the number of books, plus sport extras where the desk has them:
  tennis surface-Elo gap and fatigue (tennis.py history), CS2 is handled through Kalshi marks separately.
Target: the move in Pinnacle's no-vig probability (or line) from the open to the last pre-start snapshot; the print
book's move when Pinnacle is missing.
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import fair as fairlib
import pull

ROOT = Path(__file__).resolve().parent
ARCH = ROOT / "ledger" / "archive"
OUT = ROOT / "stats" / "features"
MIN_ROWS = 300
US = ["draftkings", "fanduel", "betmgm", "williamhill_us"]


def all_rows():
    rows = {}
    if ARCH.exists():
        for f in sorted(ARCH.glob("*/*.jsonl")):
            if f.stem == "kalshi":
                continue
            for line in f.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    rows[r.get("id")] = r
    for r in pull.load(pull.LEDGER, {"rows": []}).get("rows") or []:
        if r.get("final"):
            rows.setdefault(r.get("id"), r)
    return list(rows.values())


def side_keys(r):
    if r["market"] == "h2h":
        return ["home", "away"] + (["draw"] if "draw" in (r.get("openSnap") or {}) else [])
    if r["market"] == "total":
        return ["over", "under"]
    return ["home", "away"]


def prob(b, keys):
    try:
        return fairlib.probs(b, keys)[keys[0]] if b and all(k in b for k in keys) else None
    except Exception:  # noqa: BLE001
        return None


def row_features(r, extras=None):
    o = r.get("openSnap") or {}
    books = o.get("books") or {}
    keys = side_keys(r)
    pts = r["market"] == "spread" or (r["market"] == "total" and r["sport"] not in pull.PROB_TOTALS)
    f = {}
    pin = books.get("pinnacle")
    if pts:
        if o.get("line") is None:
            return None
        f["open_line"] = o["line"]
        lines = [b.get("line") for k, b in books.items() if b.get("line") is not None]
        if len(lines) > 1:
            f["book_line_range"] = max(lines) - min(lines)
            f["book_line_mean_minus_print"] = sum(lines) / len(lines) - o["line"]
        if pin and pin.get("line") is not None:
            f["pin_minus_print_line"] = pin["line"] - o["line"]
        po = prob(o, keys)
        if po is not None:
            f["open_price_prob"] = po
    else:
        po = prob(o, keys)
        if po is None:
            return None
        f["open_prob"] = po
        ps = {k: prob(b, keys) for k, b in books.items()}
        ps = {k: v for k, v in ps.items() if v is not None}
        if len(ps) > 1:
            vals = list(ps.values())
            m = sum(vals) / len(vals)
            f["book_prob_sd"] = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5
            f["book_prob_mean_minus_print"] = m - po
        if "pinnacle" in ps:
            f["pin_minus_print"] = ps["pinnacle"] - po
            for k in US:
                if k in ps:
                    f[f"{k}_minus_pin"] = ps[k] - ps["pinnacle"]
        if "draw" in keys and "draw" in o:
            f["open_draw"] = prob(o, ["draw", "home", "away"])
    try:
        t0, t1 = pull.parse(o["time"]), pull.parse(r["commence"])
        f["hours_open_to_start"] = max(0.0, (t1 - t0).total_seconds() / 3600)
        f["dow"] = float(t1.weekday())
        f["hour_utc"] = float(t1.hour)
    except Exception:  # noqa: BLE001
        pass
    f["n_books"] = float(len(books))
    if extras:
        f.update(extras(r) or {})
    return f


def target(r):
    o, c = r.get("openSnap") or {}, r.get("closeSnap") or r.get("lastSnap") or {}
    if not c or c.get("time") == o.get("time"):
        return None
    keys = side_keys(r)
    pts = r["market"] == "spread" or (r["market"] == "total" and r["sport"] not in pull.PROB_TOTALS)
    po_b, pc_b = (o.get("books") or {}).get("pinnacle"), (c.get("books") or {}).get("pinnacle")
    if pts:
        a = (po_b or {}).get("line") if po_b and pc_b else o.get("line")
        b = (pc_b or {}).get("line") if po_b and pc_b else c.get("line")
        return (b - a) if a is not None and b is not None else None
    if r["market"] == "total" and o.get("line") != c.get("line"):
        return None
    a, b = (prob(po_b, keys), prob(pc_b, keys)) if po_b and pc_b else (prob(o, keys), prob(c, keys))
    return (b - a) if a is not None and b is not None else None


def tennis_extras():
    try:
        import tennis as T
        hist = pull.load(T.HIST, {"matches": []})["matches"]
        R, _ = T.ratings(hist)
        names = {T.norm(n): n for n in R[2]}
    except Exception:  # noqa: BLE001
        return None

    def ex(r):
        h, a = names.get(T.norm(r.get("home"))), names.get(T.norm(r.get("away")))
        if not h or not a:
            return {}
        sf = T.surface((r.get("sportKey") or "").replace("_", " "), None)
        when = pull.parse(r["commence"])
        p = T.prob(R, h, a, sf)
        out = {"games2d_diff": float(T.recent_games(hist, h, when) - T.recent_games(hist, a, when))}
        if p is not None:
            out["elo_home"] = p
        return out
    return ex


def build():
    rows = all_rows()
    groups = defaultdict(list)
    tex = tennis_extras()
    for r in rows:
        y = target(r)
        if y is None:
            continue
        ex = tex if r.get("sport") in ("ATP", "WTA") and r.get("market") == "h2h" else None
        f = row_features(r, ex)
        if f is None:
            continue
        if ex and "elo_home" in f and "open_prob" in f:
            f["elo_gap"] = f["elo_home"] - f["open_prob"]
        groups[(r["sport"], r["market"])].append({"id": r["id"], "date": r["commence"], "f": f, "y": y})
    # CS2 (and any sport) on Kalshi: first-seen vs last pre-start mid, with the CS2 model's view at first sight.
    if ARCH.exists():
        for f in sorted(ARCH.glob("*/kalshi.jsonl")):
            for line in f.read_text().splitlines():
                if not line.strip():
                    continue
                k = json.loads(line)
                if k.get("sport") != "CS2" or k.get("open") is None or k.get("last") is None or k.get("openT") == k.get("lastT"):
                    continue
                feats = {"open_prob": k["open"], "bestOf": float(k.get("bestOf") or 3), "maps": float(k.get("maps") or 0),
                         "tier_rank": float("sabcd".find(k.get("tier") or "d"))}
                if k.get("model") is not None:
                    feats["model_gap"] = k["model"] - k["open"]
                try:
                    feats["hours_open_to_start"] = (pull.parse(k["start"]) - pull.parse(k["openT"])).total_seconds() / 3600
                except Exception:  # noqa: BLE001
                    pass
                groups[("CS2", "kalshi")].append({"id": k.get("ticker"), "date": k.get("start"), "f": feats, "y": k["last"] - k["open"]})
    targets = {}
    for (sport, market), rs in groups.items():
        name = f"archive_{sport.lower()}_{market}"
        if len(rs) >= MIN_ROWS:
            (OUT / f"{name}.json").write_text(json.dumps({"rows": rs}, separators=(",", ":")))
            unit = "points" if (market == "spread" or (market == "total" and sport not in pull.PROB_TOTALS)) else "prob"
            targets[name] = {"file": f"stats/features/{name}.json", "y": "y", "unit": unit}
    (OUT / "archive_targets.json").write_text(json.dumps(targets, indent=1))
    counts = {f"{s}/{m}": len(v) for (s, m), v in groups.items()}
    print(json.dumps({"archiveRows": len(rows), "byMarket": counts, "learnerTargets": list(targets),
                      "needed": MIN_ROWS, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}))


if __name__ == "__main__":
    build()
