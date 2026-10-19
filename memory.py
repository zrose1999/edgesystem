#!/usr/bin/env python3
"""EDGE living memory and feature research ledger. Runs at the end of grade.py; safe to run by hand.

  python3 memory.py                 rebuild memory/log, memory/research.json and memory/summary.md
  python3 memory.py query [filters] sample size and CLV of past reads that match, e.g.
        python3 memory.py query --sport NFL --market total --feature wind=15+
        python3 memory.py query --pattern news-lag --feature timing=early --since 2026-10-01

What it writes
  memory/log/<YYYY-MM>.jsonl  one entry per settled read (pick, lean or pass), keyed by pickId and upserted, never
                              dropped: sport, date, teams, open, close, line taken, fair (projected) number, result,
                              CLV, and the features present when the read was stamped.
  memory/research.json        every candidate feature: sample, mean CLV, t, beat-close rate, last-30-day CLV, and how
                              far it is from grade.py's promotion bar or the retirement bar.
  memory/summary.md           under 30 lines: what has beaten the close recently, what has not, closest to promotion,
                              the largest early-negative slices (still collecting), and data gaps.
                              Read this first in every session.

Rules
  Features are recorded only from data stored before or at the pick (the row's open, the pick's line and time, the
  injury, weather and goalie fields). Nothing after the pick is a feature, so CLV is never explained by itself.
  The test sample is the same one grade.py uses: one entry per pattern, row and side (the pick, else the first lean).
  Rereads and passes are logged but never counted in a feature's CLV.
  Status thresholds come from grade.py (STAGES). This file proposes; it never promotes, retires or changes a pattern.
  A feature that clears the bar is a lead for review, not a rule.
  Posture (Zack, 2026-10-19): EDGE is in its data-collection and learning phase. Negative CLV on early features is
  expected and is logged to learn from; no slice is labeled for retirement here. Statuses: research (too few reads to
  say), early-positive, early-negative (still collecting), at-promotion-bar.
"""

import argparse
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import grade

ROOT = Path(__file__).resolve().parent
MEM = ROOT / "memory"
LOG = MEM / "log"
RESEARCH = MEM / "research.json"
SUMMARY = MEM / "summary.md"
ARCH = ROOT / "ledger" / "archive"
RECENT_DAYS = 30

# Shipped data features: when each began, so coverage is measured only on reads stamped after it. A shipped feature
# at 0 coverage after MIN_READS_FOR_ALARM new reads is breakage (health check), not a quiet gap.
SHIPPED = {"pinAtPick": "2026-10-19T18:00:00Z"}
MIN_READS_FOR_ALARM = 10

# Candidate features EDGE wants to test but does not collect yet. Listed so they stay visible, with what is missing.
# Each note says what it would take to start collecting.
NOT_COLLECTED = {
    "public-pct": "Needs a betting-splits source (Action Network or VSiN pages, or a paid splits API), pulled near the "
                  "open and near kickoff per game. No free API in the stack today.",
    "late-steam": "Needs a per-row price history: fast runs already price every game every 15 min in its last 3 hours "
                  "but overwrite lastSnap. Appending those snaps costs no extra credits; code change in pull.py.",
    "travel": "Needs each team's previous venue joined to stats/venues.json coordinates (miles, time zones crossed, "
              "days since). Free; code only.",
    "guru": "Needs a list of X/Reddit accounts and a reader (Reddit API is free with an app key; X API is paid). "
            "Log account, number, time, result; keep after 20 settled calls beat the close (MISSION.md).",
}

QB_WORDS = re.compile(r"\bQB\d?\b|quarterback", re.I)
GOALIE_WORDS = re.compile(r"goalie|goaltender", re.I)
REST_WORDS = re.compile(r"back-to-back|\bb2b\b|rest", re.I)


def load_json(path, default):
    try:
        return json.loads(path.read_text()) if path.exists() else default
    except ValueError:
        return default


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def all_rows():
    """Ledger rows plus archived rows, by id. Picked rows leave the ledger after 30 days, so both are needed."""
    rows = {}
    if ARCH.exists():
        for path in sorted(ARCH.glob("*/*.jsonl")):
            if path.name == "kalshi.jsonl":
                continue
            for line in path.read_text().splitlines():
                if line.strip():
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    rows[r.get("id")] = r
    for r in load_json(grade.LEDGER, {"rows": []}).get("rows") or []:
        rows[r.get("id")] = r
    return rows


def side_open_line(row, pick):
    """The open line from the picked side's point of view, or None."""
    snap = row.get("openSnap") or {}
    line = snap.get("line")
    if line is None or pick.get("market") == "h2h":
        return None
    if pick["market"] == "spread":
        return line if pick["side"] == "home" else -line
    return line


def minutes_to_kick(pick):
    try:
        return round((parse(pick["commence"]) - parse(pick["pickedAt"])).total_seconds() / 60)
    except (KeyError, TypeError, ValueError):
        return None


def sharp_divergence(pick, row):
    """Pinnacle minus the print book, no-vig probability of the picked side, at the OPEN (known before the pick).
    Positive: Pinnacle rated our side higher than the print book did. Only when both books show the same line."""
    side = pick.get("side")
    snap = row.get("openSnap") or {}
    books = snap.get("books") or {}
    pin = books.get("pinnacle")
    if not side or not pin:
        return None
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in snap and k in pin]
    if side not in keys or len(keys) < 2:
        return None
    if pick.get("market") != "h2h" and pin.get("line") != snap.get("line"):
        return None
    try:
        import fair as fairlib
        return round(fairlib.probs({k: pin[k] for k in keys})[side] - fairlib.probs({k: snap[k] for k in keys})[side], 4)
    except Exception:  # noqa: BLE001
        return None


def sharp_divergence_at_pick(pick):
    """Pinnacle minus the print book, no-vig probability of the picked side, in the snapshot the read was priced
    from. Same line only. Stored from 2026-10-19 (pinAtPick)."""
    pin, side, mp = pick.get("pinAtPick") or {}, pick.get("side"), pick.get("marketPrices") or {}
    if not side or "noVig" not in pin or side not in mp:
        return None
    if pick.get("market") != "h2h" and pin.get("line") != pick.get("marketNumber"):
        return None
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in mp and k in (pin.get("prices") or {})]
    if len(keys) < 2:
        return None
    try:
        import fair as fairlib
        return round(pin["noVig"] - fairlib.probs({k: mp[k] for k in keys})[side], 4)
    except Exception:  # noqa: BLE001
        return None


def coverage(picks):
    """For each shipped feature: reads stamped since it shipped, and how many carry it."""
    out = {}
    for name, since in SHIPPED.items():
        new = [p for p in picks if p.get("side") and (p.get("pickedAt") or "") >= since]
        have = sum(1 for p in new if p.get(name))
        out[name] = {"since": since, "reads": len(new), "with": have,
                     "alarm": len(new) >= MIN_READS_FOR_ALARM and have == 0}
    return out


def features(pick, row):
    """Features present when the read was stamped. Keys are stable; values are short labels."""
    f = {"pattern": pick.get("pattern") or "none", "grade": pick.get("grade"), "confidence": pick.get("confidence"),
         "market": pick.get("market")}
    side, market = pick.get("side"), pick.get("market")
    mins = minutes_to_kick(pick)
    if mins is not None:
        hrs = mins / 60
        f["timing"] = "early" if hrs > 48 else "day" if hrs > 6 else "late"
    div = sharp_divergence(pick, row)
    if div is not None:
        f["sharpDiv"] = "pin-for" if div >= 0.01 else "pin-against" if div <= -0.01 else "aligned"
    dp = sharp_divergence_at_pick(pick)
    if dp is not None:
        f["sharpDivPick"] = "pin-for" if dp >= 0.01 else "pin-against" if dp <= -0.01 else "aligned"
    if side:
        line, price = pick.get("lineAtPick"), pick.get("priceAtPick")
        if market in ("spread", "h2h"):
            f["venue"] = side
        if market == "spread" and isinstance(line, (int, float)):
            f["role"] = "fav" if line < 0 else "dog" if line > 0 else "pk"
            if pick.get("sport") in ("NFL", "NCAAF"):
                lo, hi = sorted((abs(line), abs(pick.get("fair") or line)))
                f["keyNumber"] = abs(line) in (3, 7, 3.5, 7.5, 2.5, 6.5) or any(lo <= k <= hi for k in (3, 7))
        elif market == "h2h" and isinstance(price, (int, float)):
            f["role"] = "fav" if price < 0 else "dog"
        elif market == "total":
            f["role"] = side
        # Line move from the open to the pick, from the picked side's view. "for": the number got better for us
        # before we took it (the market moved away from our side); "against": it moved toward our side first.
        ol = side_open_line(row, pick)
        if ol is not None and isinstance(line, (int, float)):
            gained = (line - ol) if market == "spread" or side == "under" else (ol - line)
            f["moveBeforePick"] = "for" if gained > 0 else "against" if gained < 0 else "none"
        edge, bar = pick.get("edge"), pick.get("bar")
        if isinstance(edge, (int, float)) and bar:
            ratio = edge / bar
            f["edgeBar"] = "<0.5x" if ratio < 0.5 else "0.5-1x" if ratio < 1 else "1-2x" if ratio < 2 else "2x+"
    inj = []
    text = " ".join(str(x) for x in (row.get("injury"), row.get("newsLagSig"), pick.get("reason")) if x and x != "missing")
    if row.get("injury") not in (None, "missing") or row.get("newsLagSig"):
        inj.append("any")
    if QB_WORDS.search(text):
        inj.append("qb")
    if row.get("goalieSig") or GOALIE_WORDS.search(text):
        inj.append("goalie")
    if inj:
        f["injury"] = inj
    if REST_WORDS.search(pick.get("reason") or ""):
        f["rest"] = True
    wd = row.get("weatherData") or {}
    if isinstance(wd.get("windMph"), (int, float)):
        w = wd["windMph"]
        f["wind"] = "15+" if w >= 15 else "10-15" if w >= 10 else "<10"
        if wd.get("heavy"):
            f["precip"] = "heavy"
    if pick.get("bookAtPick"):
        f["bookAtPick"] = pick["bookAtPick"]
    return f


def entry(pick, row, counted):
    snap_o, snap_c = row.get("openSnap") or {}, row.get("closeSnap") or {}
    return {
        "pickId": pick["pickId"], "sport": pick.get("sport"), "date": (pick.get("commence") or "")[:10],
        "event": pick.get("event"), "home": row.get("home"), "away": row.get("away"),
        "market": pick.get("market"), "kind": pick.get("kind", "pick"), "counted": counted,
        "side": pick.get("side"), "pattern": pick.get("pattern"), "grade": pick.get("grade"),
        "openLine": snap_o.get("line"), "openPrices": {k: snap_o[k] for k in ("home", "away", "over", "under", "draw") if k in snap_o},
        "lineAtPick": pick.get("lineAtPick"), "priceAtPick": pick.get("priceAtPick"), "pickedAt": pick.get("pickedAt"),
        "minutesToKick": minutes_to_kick(pick), "sharpDivergence": sharp_divergence(pick, row),
        "pinAtPick": pick.get("pinAtPick"), "sharpDivergenceAtPick": sharp_divergence_at_pick(pick),
        "fair": pick.get("fair"), "edge": pick.get("edge"), "edgeUnit": pick.get("edgeUnit"), "bar": pick.get("bar"),
        "closeLine": snap_c.get("line"), "closePrice": pick.get("closePrice"), "closeNoVig": pick.get("closeNoVig"),
        "clvProb": pick.get("clvProb"), "clvPoints": pick.get("clvPoints"), "clvEstimated": pick.get("estimated"),
        "result": pick.get("result"), "units": pick.get("units"), "score": row.get("score"),
        "features": features(pick, row),
        "injury": row.get("injury") if row.get("injury") != "missing" else None,
        "weather": row.get("weather") if row.get("weather") != "missing" else None,
        "reason": pick.get("reason"), "falsifier": pick.get("falsifier"), "by": pick.get("by"),
        "notes": pick.get("note"),
    }


def tokens(f):
    """Feature tokens used for research and queries, e.g. timing=early, injury=qb."""
    out = []
    for k, v in f.items():
        for val in (v if isinstance(v, list) else [v]):
            if val is None or val is False:
                continue
            out.append(f"{k}={'yes' if val is True else val}")
    return out


def stats(vals):
    n = len(vals)
    mean = sum(vals) / n if n else None
    return {"n": n, "meanClvProb": round(mean, 4) if n else None, "tStat": round(grade.tstat(vals), 2),
            "beatClose": sum(1 for v in vals if v > 0)}


def status_for(n, mean, t, fast=False):
    """Where a feature stands against grade.py's own bars (fast track for gate-passed learned patterns, as in
    grade.py). Never changes a pattern."""
    need = grade.stage_t(n, fast)
    if need is not None and mean is not None and mean > 0 and t >= need:
        return "at-promotion-bar", 0, 0.0
    first_n, first_t = (grade.FAST_TRACK if fast else grade.STAGES)[0]
    label = "research" if n < 8 or mean is None else "early-positive" if mean > 0 else "early-negative"
    return label, max(0, first_n - n), round(max(0.0, (need or first_t) - t), 2)


def build():
    now = datetime.now(timezone.utc)
    picks = load_json(grade.PICKS, {"picks": []}).get("picks") or []
    rows = all_rows()

    first = {}
    for p in sorted(picks, key=lambda p: (p.get("kind", "pick") != "pick", p.get("pickedAt") or "")):
        if p.get("kind", "pick") in ("pick", "lean") and p.get("side"):
            first.setdefault((p.get("pattern"), p.get("rowId"), p.get("side")), p)
    counted_ids = {p["pickId"] for p in first.values()}

    # 1. Log: upsert settled reads by pickId, month by month. Old entries are kept even if picks.json is pruned.
    LOG.mkdir(parents=True, exist_ok=True)
    months = defaultdict(dict)
    for path in LOG.glob("*.jsonl"):
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    e = json.loads(line)
                    months[path.stem][e["pickId"]] = e
                except (ValueError, KeyError):
                    continue
    added = 0
    for p in picks:
        row =rows.get(p.get("rowId")) or {}
        settled = "clvProb" in p or p.get("result") or (row.get("final") and p.get("kind") == "pass")
        if not settled:
            continue
        month = (p.get("commence") or p.get("pickedAt") or "unknown")[:7]
        if p["pickId"] not in months[month]:
            added += 1
        months[month][p["pickId"]] = entry(p, row, p["pickId"] in counted_ids)
    for month, entries in months.items():
        lines = [json.dumps(e, ensure_ascii=False, separators=(",", ":"))
                 for e in sorted(entries.values(), key=lambda e: (e.get("date") or "", e["pickId"]))]
        (LOG / f"{month}.jsonl").write_text("\n".join(lines) + "\n")
    log = [e for m in months.values() for e in m.values()]

    # 2. Research ledger: every feature token across counted, graded reads, overall and per sport.
    cutoff = (now - timedelta(days=RECENT_DAYS)).strftime("%Y-%m-%d")
    graded = [e for e in log if e.get("counted") and isinstance(e.get("clvProb"), (int, float))]
    groups = defaultdict(list)
    for e in graded:
        for tok in tokens(e["features"]):
            if tok.startswith(("market=", "grade=", "confidence=")):
                groups[("ALL", tok)].append(e)
                continue
            groups[("ALL", tok)].append(e)
            groups[(e["sport"], tok)].append(e)
    old = load_json(RESEARCH, {})
    first_seen = {f["key"]: f.get("firstSeen") for f in old.get("features", [])}
    feats = []
    for (sport, tok), es in groups.items():
        vals = [e["clvProb"] for e in es]
        picks_only = [e["clvProb"] for e in es if e["kind"] == "pick"]
        recent = [e["clvProb"] for e in es if (e.get("date") or "") >= cutoff]
        s = stats(vals)
        fast = tok.startswith("pattern=") and grade.gate_passed(tok[8:])
        st, n_short, t_short = status_for(s["n"], s["meanClvProb"], s["tStat"], fast)
        settled = [e for e in es if e.get("result") in ("win", "loss", "push")]
        key = f"{sport}|{tok}"
        feats.append({
            "key": key, "sport": sport, "feature": tok, **s, "status": st,
            "picksN": len(picks_only), "picksMeanClvProb": round(sum(picks_only) / len(picks_only), 4) if picks_only else None,
            "recentN": len(recent), "recentMeanClvProb": round(sum(recent) / len(recent), 4) if recent else None,
            "nShortOfFirstStage": n_short, "tShort": t_short,
            "record": "{}-{}-{}".format(*(sum(1 for e in settled if e["result"] == r) for r in ("win", "loss", "push"))),
            "firstSeen": first_seen.get(key) or now.strftime("%Y-%m-%d"),
        })
    feats.sort(key=lambda f: (f["sport"] != "ALL", f["sport"], f["feature"]))
    new_patterns = sorted({f["feature"][8:] for f in feats if f["feature"].startswith("pattern=") and f["key"] not in first_seen})
    research = {
        "asOf": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rules": (f"Sample: one entry per pattern, row and side (grade.py). Bars from grade.py: promotion at mean CLV > 0 "
                  f"and t >= {grade.STAGES[0][1]} at {grade.STAGES[0][0]}+ (t >= {grade.STAGES[-1][1]} at "
                  f"{grade.STAGES[-1][0]}+). Learning phase: early-negative means still collecting, never a "
                  f"retirement call. A feature at a bar is a lead for review; this file never changes a pattern. "
                  f"Win rate never counts."),
        "gradedReads": len(graded), "loggedReads": len(log),
        "newPatternsThisRun": new_patterns,
        "notCollected": NOT_COLLECTED,
        "coverage": coverage(picks),
        "sharpDivergenceCoverage": {"graded": len(graded),
                                    "withData": sum(1 for e in graded if e.get("sharpDivergence") is not None)},
        "features": feats,
    }
    patterns = load_json(grade.LEDGER, {}).get("patterns") or []
    research["flags"] = flags(feats, patterns)
    # Conditional pockets for every early-negative slice with 15+ reads, and for grade A.
    research["pockets"] = []
    for f in feats:
        if f["status"] == "early-negative" and f["n"] >= 15 and not f["feature"].startswith("confidence="):
            best, tested = pocket(slice_entries(graded, f), f["feature"].split("=")[0], with_sport=f["sport"] == "ALL")
            research["pockets"].append({"slice": f["key"], "n": f["n"], "meanClvProb": f["meanClvProb"],
                                        "pocket": best, "tested": tested})

    MEM.mkdir(parents=True, exist_ok=True)
    RESEARCH.write_text(json.dumps(research, indent=1) + "\n")
    SUMMARY.write_text(summary(research, now, patterns, graded))
    return {"logged": len(log), "newLogEntries": added, "graded": len(graded), "features": len(feats),
            "newPatterns": new_patterns}


def fmt(f):
    m = f["meanClvProb"]
    r = f["recentMeanClvProb"]
    return (f"{f['sport']} {f['feature']}: n {f['n']}, CLV {m * 100:+.1f}%, t {f['tStat']:+.1f}"
            + (f", last {RECENT_DAYS}d {r * 100:+.1f}% on {f['recentN']}" if r is not None else ""))


GAP_SHORT = {
    "public-pct": "needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack",
    "late-steam": "needs pull.py to append fast-run snaps per row instead of overwriting lastSnap; no extra credits",
    "travel": "needs previous venue joined to stats/venues.json (miles, time zones); free, code only",
    "guru": "needs an account list + reader (Reddit API free, X API paid); log account, number, time, result",
}


def dedupe(features):
    """Drop a cross-sport (ALL) line when one sport holds the whole sample: it would repeat that sport's line."""
    by_key = {(f["sport"], f["feature"]): f for f in features}
    sports = {f["sport"] for f in features} - {"ALL"}
    return [f for f in features if not (f["sport"] == "ALL" and any(
        (by_key.get((s, f["feature"])) or {}).get("n") == f["n"] for s in sports))]


def flags(features, patterns):
    """Standing observations for every health check. They never change a rule."""
    out = []
    g = {f["feature"][6:]: f for f in features if f["sport"] == "ALL" and f["feature"].startswith("grade=")
         and f["meanClvProb"] is not None}
    if all(k in g for k in "ABC"):
        a, b, c = (g[k]["meanClvProb"] for k in "ABC")
        out.append({"type": "grade-order", "ordered": a > b > c,
                    "A": {"n": g["A"]["n"], "meanClvProb": a}, "B": {"n": g["B"]["n"], "meanClvProb": b},
                    "C": {"n": g["C"]["n"], "meanClvProb": c},
                    "note": "Observation, not a defect: in a working system A > B > C on CLV. Until it is, edge size "
                            "is not yet predicting CLV."})
    return out


POCKET_MIN_N = 8


def pocket_tokens(e, with_sport):
    toks = set(tokens(e.get("features") or {}))
    if with_sport:
        toks.add(f"sport={e.get('sport')}")
    return toks


def pocket(entries, exclude_key, with_sport=True):
    """Inside one slice, the best one-feature sub-slice with mean CLV >= 0 and n >= POCKET_MIN_N.
    Returns (best or None, combinations tested). Many combinations are tested, so a pocket is a lead to keep
    watching, not a finding."""
    groups = defaultdict(list)
    for e in entries:
        for tok in pocket_tokens(e, with_sport):
            if tok.split("=")[0] != exclude_key and not tok.startswith("confidence="):
                groups[tok].append(e["clvProb"])
    tested = [(tok, v) for tok, v in groups.items() if len(v) >= POCKET_MIN_N and len(v) < len(entries)]
    hits = [(tok, v) for tok, v in tested if sum(v) / len(v) >= 0]
    if not hits:
        return None, len(tested)
    tok, v = max(hits, key=lambda h: (sum(h[1]) / len(h[1]), len(h[1])))
    return {"feature": tok, "n": len(v), "meanClvProb": round(sum(v) / len(v), 4), "tStat": round(grade.tstat(v), 2)}, len(tested)


def grade_order_pockets(graded, min_n=5):
    """Features inside which the grade order holds (A > B > C on CLV, each grade with min_n+ reads)."""
    by = defaultdict(lambda: defaultdict(list))
    for e in graded:
        g = (e.get("features") or {}).get("grade")
        if g not in ("A", "B", "C"):
            continue
        for tok in pocket_tokens(e, True):
            if not tok.startswith(("grade=", "confidence=")):
                by[tok][g].append(e["clvProb"])
    tested, holds = 0, []
    for tok, gs in by.items():
        if all(len(gs[k]) >= min_n for k in "ABC"):
            tested += 1
            m = {k: sum(gs[k]) / len(gs[k]) for k in "ABC"}
            if m["A"] > m["B"] > m["C"]:
                holds.append({"feature": tok, **{k: {"n": len(gs[k]), "meanClvProb": round(m[k], 4)} for k in "ABC"}})
    holds.sort(key=lambda h: -(h["A"]["meanClvProb"] - h["C"]["meanClvProb"]))
    return holds, tested


def slice_entries(graded, f):
    return [e for e in graded if (f["sport"] == "ALL" or e.get("sport") == f["sport"])
            and f["feature"] in pocket_tokens(e, False)]


def pocket_line(best, tested, inside):
    if best is None:
        return f"  > no conditional pocket found in current features ({tested} combos tested inside {inside})"
    return (f"  > pocket: {best['feature']} inside {inside}: n {best['n']}, CLV {best['meanClvProb'] * 100:+.1f}%, "
            f"t {best['tStat']:+.1f} (best of {tested} tested; a lead to watch)")


def summary(research, now, patterns, graded):
    feats = dedupe([f for f in research["features"] if not f["feature"].startswith(("grade=", "confidence="))])
    pstat = {p["id"]: p for p in patterns}
    leads = sorted([f for f in feats if f["feature"].startswith("pattern=") and f["status"] == "early-positive"],
                   key=lambda f: -f["n"])
    # Largest samples first, not the worst t: the point is where the most is being learned, not what to cut.
    neg = sorted([f for f in feats if f["status"] == "early-negative" and not f["feature"].startswith("confidence=")],
                 key=lambda f: -f["n"])[:4]
    other = [f for f in feats if f["n"] >= 8 and f["recentN"] >= 8 and not f["feature"].startswith(("pattern=", "market="))]
    top2 = sorted([f for f in other if f["recentMeanClvProb"] > 0], key=lambda f: -f["recentMeanClvProb"])[:2]
    low2 = sorted([f for f in other if f["recentMeanClvProb"] < 0], key=lambda f: f["recentMeanClvProb"])[:2]
    lines = [f"# What EDGE is learning ({now.strftime('%Y-%m-%d %H:%M')}Z)",
             "Phase: data collection and learning. Samples are small and key features are still being added. "
             "Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.",
             f"{research['gradedReads']} graded reads counted, {research['loggedReads']} logged. CLV is mean clvProb. "
             "Patterns move only by grade.py.", "",
             "Early positive leads (one of many being tested; no acceleration):"]
    for f in leads[:3]:
        ps = pstat.get(f["feature"][8:]) or {}
        need = (f"; grade.py needs {ps.get('nNeeded', '?')} more graded full-bar picks (has {ps.get('clvN', 0)}), "
                f"t >= {ps.get('tNeeded', '?')}") if ps else ""
        lines.append(f"- {fmt(f)}{need}")
    if not leads:
        lines.append("- none yet")
    lines.append("Early negative, still collecting (largest samples):")
    for f in neg:
        lines.append(f"- {fmt(f)}")
        best, tested = pocket(slice_entries(graded, f), f["feature"].split("=")[0], with_sport=f["sport"] == "ALL")
        lines.append(pocket_line(best, tested, f["feature"]))
    if not neg:
        lines.append("- none")
    go = next((x for x in research["flags"] if x["type"] == "grade-order"), None)
    if go:
        txt = ", ".join(f"{k} {go[k]['meanClvProb'] * 100:+.1f}% on {go[k]['n']}" for k in "ABC")
        lines.append(f"Observation: {'grades rank A > B > C' if go['ordered'] else 'edge size is not yet predicting CLV'}"
                     f" ({txt}).")
        ga = [e for e in graded if (e.get("features") or {}).get("grade") == "A"]
        best, tested = pocket(ga, "grade")
        lines.append(pocket_line(best, tested, "grade A"))
        holds, tested = grade_order_pockets(graded)
        if holds:
            h = holds[0]
            lines.append(f"  > order holds inside {h['feature']}: " + ", ".join(
                f"{k} {h[k]['meanClvProb'] * 100:+.1f}% on {h[k]['n']}" for k in "ABC")
                + f" ({len(holds)} of {tested} features tested)")
        else:
            lines.append(f"  > grade order holds inside no feature yet ({tested} tested with 5+ reads per grade)")
    lines += ["", "Other slices, last 30d (context, not leads): best " + ("; ".join(fmt(f) for f in top2) or "none")
              + " | worst " + ("; ".join(fmt(f) for f in low2) or "none"),
              "", "Data gaps, free (building next):"]
    lines += [f"- {k}: {GAP_SHORT[k]}" for k in ("late-steam", "travel", "sharp-divergence-at-pick") if k in research["notCollected"]]
    lines.append("Data gaps, waiting on a source:")
    lines += [f"- {k}: {GAP_SHORT[k]}" for k in ("public-pct", "guru") if k in research["notCollected"]]
    for name, c in (research.get("coverage") or {}).items():
        pct = f" ({c['with'] / c['reads']:.0%})" if c["reads"] else ""
        lines.append(f"{'BREAKAGE: ' if c['alarm'] else ''}{name} (shipped {c['since'][:16]}Z): on {c['with']} of "
                     f"{c['reads']} new reads{pct}" + (" -- shipped feature not flowing; fix as breakage" if c["alarm"] else ""))
    sd = research.get("sharpDivergenceCoverage") or {}
    lines.append(f"sharpDivergence (at the open) on {sd.get('withData', 0)} of {sd.get('graded', 0)} graded reads; "
                 "Pinnacle opens stored since 2026-10-14.")
    return "\n".join(lines[:30]) + "\n"


def query(a):
    log = []
    for path in sorted(LOG.glob("*.jsonl")):
        log += [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    hits = []
    for e in log:
        if not e.get("counted") or not isinstance(e.get("clvProb"), (int, float)):
            continue
        if a.sport and e.get("sport") != a.sport.upper():
            continue
        if a.market and e.get("market") != a.market:
            continue
        if a.pattern and e.get("pattern") != a.pattern:
            continue
        if a.since and (e.get("date") or "") < a.since:
            continue
        toks = set(tokens(e.get("features") or {}))
        if all(f in toks for f in a.feature or []):
            hits.append(e)
    vals = [e["clvProb"] for e in hits]
    res = [e for e in hits if e.get("result") in ("win", "loss", "push")]
    out = {"filters": {k: v for k, v in vars(a).items() if v and k != "cmd"}, **stats(vals),
           "record": "{}-{}-{}".format(*(sum(1 for e in res if e["result"] == r) for r in ("win", "loss", "push"))),
           "examples": [f"{e['date']} {e['event']} {e['market']} {e['side']} {e['lineAtPick']} "
                        f"CLV {e['clvProb'] * 100:+.1f}%" for e in hits[-5:]]}
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(description="EDGE living memory")
    sub = ap.add_subparsers(dest="cmd")
    q = sub.add_parser("query")
    q.add_argument("--sport")
    q.add_argument("--market", choices=["spread", "total", "h2h"])
    q.add_argument("--pattern")
    q.add_argument("--feature", action="append", help="key=value, repeatable: timing=early, injury=qb, wind=15+")
    q.add_argument("--since", help="YYYY-MM-DD")
    a = ap.parse_args()
    if a.cmd == "query":
        query(a)
    else:
        print(json.dumps(build()))


if __name__ == "__main__":
    main()
