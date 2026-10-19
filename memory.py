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
                              closest to a kill, and data gaps. Read this first in every session.

Rules
  Features are recorded only from data stored before or at the pick (the row's open, the pick's line and time, the
  injury, weather and goalie fields). Nothing after the pick is a feature, so CLV is never explained by itself.
  The test sample is the same one grade.py uses: one entry per pattern, row and side (the pick, else the first lean).
  Rereads and passes are logged but never counted in a feature's CLV.
  Status thresholds come from grade.py (STAGES, OFFICIAL_N). This file proposes; it never promotes, retires or
  changes a pattern. A feature that clears the bar is a lead for review, not a rule.
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

# Candidate features EDGE wants to test but does not collect yet. Listed so they stay visible, with what is missing.
NOT_COLLECTED = {
    "public-pct": "Public bet and money percentages. Needs a source (e.g. Action Network, VSiN); none is pulled.",
    "late-steam": "Sharp moves in the last hour. Needs intraday snapshots stored per row; only open, last and close are kept.",
    "travel": "Travel distance and time zones crossed (NFL, NBA, NHL). Venues are stored (stats/venues.json); not joined yet.",
    "guru": "X or Reddit handicapper calls (MISSION.md). Not collected.",
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


def features(pick, row):
    """Features present when the read was stamped. Keys are stable; values are short labels."""
    f = {"pattern": pick.get("pattern") or "none", "grade": pick.get("grade"), "confidence": pick.get("confidence"),
         "market": pick.get("market")}
    side, market = pick.get("side"), pick.get("market")
    try:
        hrs = (parse(pick["commence"]) - parse(pick["pickedAt"])).total_seconds() / 3600
        f["timing"] = "early" if hrs > 48 else "day" if hrs > 6 else "late"
        f["hoursBefore"] = round(hrs, 1)
    except (KeyError, TypeError, ValueError):
        pass
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
        if k in ("hoursBefore",):
            continue
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
    if n >= grade.OFFICIAL_N and mean is not None and mean <= 0:
        return "kill-candidate", 0, 0.0
    first_n, first_t = (grade.FAST_TRACK if fast else grade.STAGES)[0]
    return "research", max(0, first_n - n), round(max(0.0, (need or first_t) - t), 2)


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
                  f"{grade.STAGES[-1][0]}+); kill candidate at n >= {grade.OFFICIAL_N} with mean CLV <= 0. A feature "
                  f"at a bar is a lead for review; this file never changes a pattern. Win rate never counts."),
        "gradedReads": len(graded), "loggedReads": len(log),
        "newPatternsThisRun": new_patterns,
        "notCollected": NOT_COLLECTED,
        "features": feats,
    }
    MEM.mkdir(parents=True, exist_ok=True)
    RESEARCH.write_text(json.dumps(research, indent=1) + "\n")
    SUMMARY.write_text(summary(research, now))
    return {"logged": len(log), "newLogEntries": added, "graded": len(graded), "features": len(feats),
            "newPatterns": new_patterns}


def fmt(f):
    m = f["meanClvProb"]
    r = f["recentMeanClvProb"]
    return (f"{f['sport']} {f['feature']}: n {f['n']}, CLV {m * 100:+.1f}%, t {f['tStat']:+.1f}"
            + (f", last {RECENT_DAYS}d {r * 100:+.1f}% on {f['recentN']}" if r is not None else ""))


def summary(research, now):
    # A cross-sport (ALL) line is dropped when one sport holds the whole sample: it would just repeat that sport's line.
    by_key = {(f["sport"], f["feature"]): f for f in research["features"]}
    sports = {f["sport"] for f in research["features"]} - {"ALL"}
    def twin(f):
        return f["sport"] == "ALL" and any((by_key.get((s, f["feature"])) or {}).get("n") == f["n"] for s in sports)
    feats = [f for f in research["features"] if not twin(f) and not f["feature"].startswith(("grade=", "confidence="))]
    real = [f for f in feats if f["n"] >= 8]
    up = sorted([f for f in real if (f["recentMeanClvProb"] or 0) > 0 and f["recentN"] >= 8],
                key=lambda f: -f["recentMeanClvProb"])[:5]
    down = sorted([f for f in real if (f["recentMeanClvProb"] or 0) < 0 and f["recentN"] >= 8],
                  key=lambda f: f["recentMeanClvProb"])[:5]
    near = sorted([f for f in feats if f["status"] == "research" and (f["meanClvProb"] or 0) > 0 and f["n"] >= 8],
                  key=lambda f: (f["tShort"], f["nShortOfFirstStage"]))[:3]
    # Kill candidates use grade.py's retirement sample. "Trending" is a watch list at 15+ reads and t <= -2.
    kill = sorted([f for f in feats if f["status"] == "kill-candidate"], key=lambda f: f["tStat"])[:3]
    trend = sorted([f for f in feats if f["status"] != "kill-candidate" and f["n"] >= grade.STAGES[0][0]
                    and (f["meanClvProb"] or 0) < 0 and f["tStat"] <= -2], key=lambda f: f["tStat"])[:3]
    bar = [f for f in feats if f["status"] == "at-promotion-bar"]
    g = {f["feature"]: f for f in research["features"] if f["sport"] == "ALL" and f["feature"].startswith("grade=")}
    lines = [f"# What has worked ({now.strftime('%Y-%m-%d %H:%M')}Z)",
             f"{research['gradedReads']} graded reads counted, {research['loggedReads']} logged. CLV is mean clvProb. "
             f"Leads only; patterns move by grade.py.", "",
             "Beating the close lately:"] + [f"- {fmt(f)}" for f in up] + (["- none with 8+ recent reads"] if not up else []) + [
             "Losing to the close lately:"] + [f"- {fmt(f)}" for f in down] + (["- none"] if not down else []) + [
             "Closest to the promotion bar:"] + [f"- {fmt(f)} (needs {f['nShortOfFirstStage']} more, t short {f['tShort']})" for f in near] + (
             ["- none positive yet"] if not near else []) + [
             f"Kill candidates (n {grade.OFFICIAL_N}+, CLV <= 0):"] + [f"- {fmt(f)}" for f in kill] + (["- none"] if not kill else []) + [
             "Trending toward a kill:"] + [f"- {fmt(f)}" for f in trend] + (["- none"] if not trend else [])
    if bar:
        lines += ["At the promotion bar (review, do not auto-adopt):"] + [f"- {fmt(f)}" for f in bar[:3]]
    if g:
        lines.append("Grade test (A > B > C?): " + ", ".join(
            f"{k[6:]} {v['meanClvProb'] * 100:+.1f}% on {v['n']}" for k, v in sorted(g.items()) if v["meanClvProb"] is not None))
    if research["newPatternsThisRun"]:
        lines.append("New patterns added to research: " + ", ".join(research["newPatternsThisRun"][:6]))
    lines.append("Not collected: " + ", ".join(research["notCollected"]))
    return "\n".join(lines[:29]) + "\n"


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
