#!/usr/bin/env python3
"""EDGE findings: the system's own pattern review of wins vs losses. Added 2026-10-28 (Zack: "finding patterns on your
own and making sense of them is how I want the whole system to operate").

Runs at the end of every grade.py run, after memory.py (it reads memory/log). It does, every run, the review a person
would do by hand:

  1. Price check: CLV and the market move after the pick, by how the price taken compared with Pinnacle's fair price
     at the pick (autopsy split). Answers "are we wrong about direction, or paying too much?"
  2. Condition scan: every pre-pick condition (memory features, overall and per sport, plus sport x market x side
     slices) on counted, graded reads of patterns that are not parked. A finding needs n >= MIN_N, |t| >= MIN_T and
     the same sign in both halves of the sample (split by pick time), so a pattern that only lived in one week is not
     reported.
  3. Pairs: two conditions together, built only from conditions that were already near a finding (|t| >= PAIR_SEED_T),
     same sport scope. Catches "rest edge AND travel edge" when neither alone is enough.
  4. Confound check: if one pattern supplies over half of a finding's reads, the finding is recomputed without that
     pattern and labelled "holds without it" or "driven by it".
  5. Chance check: how many conditions were tested and how many would clear |t| >= MIN_T by luck alone (5% two-sided),
     printed beside the findings so they are read with the right suspicion.
  6. Memory: stats/findings.json keeps every finding across runs (first seen, days seen, history). A finding seen on
     HOLD_DAYS separate days that still clears the bar is "holding"; one that fell back under |t| 1 is "faded".
     Holding findings are what the weekly review turns into measured-pattern proposals; nothing here changes a rule.

Writes memory/findings.md (plain-English, newest picture) and stats/findings.json (history). Both are job output:
the data job is their only writer.
"""

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "memory" / "log"
OUT_MD = ROOT / "memory" / "findings.md"
OUT_JSON = ROOT / "stats" / "findings.json"

MIN_N = 20            # reads behind a finding
MIN_HALF = 8          # reads in each half
MIN_T = 2.0           # |t| of mean CLV
PAIR_SEED_T = 1.5     # a condition this strong may seed a pair
PAIR_MIN_N = 15
HOLD_DAYS = 3         # distinct days a finding must be seen to count as holding
FADE_T = 1.0
DOMINANT = 0.5        # one pattern above this share of a finding's reads triggers the confound check
SKIP_KEYS = ("pattern", "confidence", "grade")   # pattern results live in grade.py; grade is the read's own label

PHRASES = {
    "restDays=2+days": "our side had 2+ days of rest", "restDays=long": "our side had a long rest",
    "restDays=b2b": "our side was on a back-to-back", "restDays=normal": "our side had normal rest",
    "restDays=1day": "our side had one day of rest",
    "restEdge=more": "our side was more rested than the opponent", "restEdge=less": "our side was less rested",
    "restEdge=even": "both sides equally rested",
    "travelEdge=more": "the opponent travelled further (travel edge ours)",
    "travelEdge=less": "our side travelled further", "travel=none": "our side did not travel",
    "tzShift=none": "no time-zone change",
    "moveBeforePick=for": "the number had already moved our way before the pick",
    "moveBeforePick=against": "the line had moved toward our side before the pick",
    "moveBeforePick=none": "the line had not moved before the pick",
    "timing=early": "the read was stamped early (a day or more out)", "timing=day": "the read was stamped game day",
    "timing=late": "the read was stamped close to the start",
    "role=dog": "we took the underdog", "role=fav": "we took the favourite", "role=over": "we took the over",
    "role=under": "we took the under", "venue=home": "we took the home side", "venue=away": "we took the away side",
    "keyNumber=yes": "the line sat on or across a key number",
    "injury=any": "injury news was in play", "injury=qb": "QB news was in play",
    "sharpDivPick=pin-for": "Pinnacle rated our side higher than the print at the pick",
    "sharpDivPick=pin-against": "Pinnacle rated our side lower than the print at the pick",
    "steamBeforePick=away": "Pinnacle was moving away from our side before the pick",
    "steamBeforePick=toward": "Pinnacle was moving toward our side before the pick",
    "pinEdge=2%+": "our price beat Pinnacle's fair price by 2%+", "pinEdge=0-2%": "our price beat Pinnacle's fair price",
    "pinEdge=-2-0%": "our price was up to 2% worse than Pinnacle's fair price",
    "pinEdge=<-2%": "our price was 2%+ worse than Pinnacle's fair price",
    "edgeBar=0.5-1x": "the read's edge was half to one times its bar", "edgeBar=1-2x": "the read's edge was 1-2x its bar",
    "travelEdge=even": "both sides travelled about the same", "sharpDiv=pin-for": "Pinnacle rated our side higher at the open",
    "sharpDiv=pin-against": "Pinnacle rated our side lower at the open", "sharpDiv=aligned": "Pinnacle and the print agreed at the open",
    "edgeBar=<0.5x": "the read's edge was under half its bar", "edgeBar=2x+": "the read's edge was 2x its bar or more",
}


def phrase(tok):
    if tok in PHRASES:
        return PHRASES[tok]
    k, _, v = tok.partition("=")
    if k == "market":
        return {"total": "totals", "spread": "spreads", "h2h": "moneylines"}.get(v, v)
    if k == "side":
        return f"side {v}"
    if k == "bookAtPick":
        return f"the price came from {v}"
    if k == "travel":
        return f"our side travelled {v} miles"
    return f"{k} = {v}"


def tstat(v):
    n = len(v)
    if n < 2:
        return 0.0
    m = sum(v) / n
    var = sum((x - m) ** 2 for x in v) / (n - 1)
    return 0.0 if var <= 0 else m / math.sqrt(var / n)


def mean(v):
    return sum(v) / len(v) if v else None


def load_log():
    out = []
    for path in sorted(LOG.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def tokens(e):
    import memory
    toks = {t for t in memory.tokens(e.get("features") or {}) if t.split("=")[0] not in SKIP_KEYS}
    toks.discard("market=" + str(e.get("market")))
    return toks


def slice_keys(e):
    """(scope, condition) keys one read belongs to: every condition overall and within its sport, plus the
    sport x market x side slice (where totals and sides bleed or win)."""
    sport, market = e.get("sport"), e.get("market")
    role = (e.get("features") or {}).get("role")
    keys = set()
    for t in tokens(e):
        keys.add(("ALL", t))
        keys.add((sport, t))
    keys.add(("ALL", f"market={market}"))
    keys.add((sport, f"market={market}"))
    if role:
        keys.add((sport, f"market={market}&role={role}"))
    return keys


def describe(scope, cond):
    parts = [phrase(c) for c in cond.split("&")]
    where = "" if scope == "ALL" else f"{scope} "
    return f"{where}reads where " + " and ".join(parts)


def welch(a, b):
    """t of mean(a) - mean(b), unequal variances. 0 when either side is too small."""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    ma, mb = mean(a), mean(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return 0.0 if se == 0 else (ma - mb) / se


def evaluate(es, half_at, ctx):
    """A condition against every other read: does it separate wins from losses? diff = mean inside - mean outside,
    t = Welch t of that difference; the same difference is measured in each half of the sample (by pick time)."""
    ids = {id(e) for e in es}
    inn = [e["clvProb"] for e in es]
    out = [e["clvProb"] for e in ctx if id(e) not in ids]
    r = {"n": len(inn), "mean": mean(inn), "tSelf": tstat(inn), "outMean": mean(out), "t": welch(inn, out)}
    r["diff"] = (r["mean"] - r["outMean"]) if out else 0.0
    for h, pick in (("1", lambda e: (e.get("pickedAt") or "") < half_at), ("2", lambda e: (e.get("pickedAt") or "") >= half_at)):
        a = [e["clvProb"] for e in es if pick(e)]
        b = [e["clvProb"] for e in ctx if pick(e) and id(e) not in ids]
        r["n" + h], r["m" + h] = len(a), mean(a)
        r["d" + h] = (mean(a) - mean(b)) if a and b else None
    return r


def passes(r, min_n=MIN_N):
    """n, both halves big enough, |Welch t| >= MIN_T, and the difference has the same sign in both halves.
    A "wins" finding must also be above 0 CLV itself: better than a losing average is not a win."""
    if r["n"] < min_n or r["n1"] < MIN_HALF or r["n2"] < MIN_HALF or abs(r["t"]) < MIN_T:
        return False
    sign = 1 if r["diff"] > 0 else -1
    if (r["d1"] or 0) * sign <= 0 or (r["d2"] or 0) * sign <= 0:
        return False
    return sign < 0 or r["mean"] > 0


def confound(es, half_at, ctx, diff):
    """If one pattern supplies most of a finding's reads, does the finding survive without that pattern (inside and
    outside the condition alike)?"""
    pats = Counter(e.get("pattern") for e in es)
    top, cnt = pats.most_common(1)[0]
    if cnt / len(es) <= DOMINANT:
        return {"topPattern": top, "share": round(cnt / len(es), 2)}
    rest = [e for e in es if e.get("pattern") != top]
    ctx_rest = [e for e in ctx if e.get("pattern") != top]
    r = evaluate(rest, half_at, ctx_rest) if len(rest) >= 5 and len(ctx_rest) > len(rest) else None
    holds = bool(r and (r["diff"] > 0) == (diff > 0) and abs(r["t"]) >= 1.0)
    return {"topPattern": top, "share": round(cnt / len(es), 2), "without": (
        {"n": r["n"], "mean": round(r["mean"], 4), "diff": round(r["diff"], 4), "t": round(r["t"], 2)} if r else None),
            "verdict": "holds without it" if holds else f"driven by {top}"}


def price_check(reads):
    buckets = defaultdict(list)
    for e in reads:
        sp = ((e.get("autopsy") or {}).get("market") or {}).get("split")
        if not sp:
            continue
        if sp.get("fairSource") != "pinnacle":
            buckets["no Pinnacle at pick"].append((e["clvProb"], sp["marketMove"]))
            continue
        p = sp["pricePaid"]
        k = ("better than Pinnacle" if p > 0 else "0-1% worse" if p > -0.01 else "1-2% worse" if p > -0.02
             else "2%+ worse")
        buckets[k].append((e["clvProb"], sp["marketMove"]))
    out = {}
    for k in ("better than Pinnacle", "0-1% worse", "1-2% worse", "2%+ worse", "no Pinnacle at pick"):
        v = buckets.get(k) or []
        if v:
            out[k] = {"n": len(v), "clv": round(mean([x[0] for x in v]), 4), "moveAfter": round(mean([x[1] for x in v]), 4),
                      "beatClose": round(sum(1 for x in v if x[0] > 0) / len(v), 2)}
    return out


def build(now=None):
    import pull
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    today = stamp[:10]
    log = load_log()
    graded = [e for e in log if e.get("counted") and isinstance(e.get("clvProb"), (int, float))]
    reads = [e for e in graded if e.get("pattern") not in pull.PARKED]
    reads.sort(key=lambda e: e.get("pickedAt") or "")
    if len(reads) < 2 * MIN_N:
        OUT_MD.write_text(f"# Findings ({stamp})\n\nToo few graded reads to scan ({len(reads)}).\n")
        return {"findings": 0, "reads": len(reads)}
    half_at = reads[len(reads) // 2].get("pickedAt") or ""
    base = mean([e["clvProb"] for e in reads])

    groups, by_sport = defaultdict(list), defaultdict(list)
    for e in reads:
        by_sport[e.get("sport")].append(e)
        for k in slice_keys(e):
            groups[k].append(e)
    tested, results, seeds = 0, {}, defaultdict(list)
    for (scope, cond), es in groups.items():
        if len(es) < MIN_N or len(es) == len(reads):
            continue
        tested += 1
        ctx = reads if scope == "ALL" else by_sport[scope]
        if len(es) == len(ctx):
            continue
        r = evaluate(es, half_at, ctx)
        results[(scope, cond)] = (r, es)
        if abs(r["t"]) >= PAIR_SEED_T and "&" not in cond:
            seeds[scope].append(cond)
    # pairs from near-findings, same scope, different feature keys
    for scope, conds in seeds.items():
        conds = sorted(set(conds))
        for i, c1 in enumerate(conds):
            for c2 in conds[i + 1:]:
                if c1.split("=")[0] == c2.split("=")[0]:
                    continue
                ids2 = {id(e) for e in groups[(scope, c2)]}
                es = [e for e in groups[(scope, c1)] if id(e) in ids2]
                if len(es) < PAIR_MIN_N:
                    continue
                tested += 1
                r = evaluate(es, half_at, reads if scope == "ALL" else by_sport[scope])
                singles = [results[(scope, c)][0] for c in (c1, c2)]
                # a pair is kept only if it separates better than either condition alone
                if all(abs(r["t"]) > abs(x["t"]) + 0.5 and abs(r["diff"]) > abs(x["diff"]) for x in singles):
                    results[(scope, f"{c1}&{c2}")] = (r, es)

    found, seen_sets = [], {}
    order = sorted(results.items(), key=lambda kv: (kv[0][1].count("&"), kv[0][0] != "ALL", -abs(kv[1][0]["t"])))
    for (scope, cond), (r, es) in order:
        if not passes(r, PAIR_MIN_N if "&" in cond else MIN_N):
            continue
        sig = frozenset(id(e) for e in es)
        if sig in seen_sets:          # same reads under another name (totals&under = under): keep the simplest
            continue
        seen_sets[sig] = cond
        found.append({"key": f"{scope}|{cond}", "scope": scope, "condition": cond, "text": describe(scope, cond),
                      "n": r["n"], "mean": round(r["mean"], 4), "t": round(r["t"], 2),
                      "outside": round(r["outMean"], 4), "diff": round(r["diff"], 4),
                      "half1": {"n": r["n1"], "mean": round(r["m1"], 4), "diff": round(r["d1"], 4)},
                      "half2": {"n": r["n2"], "mean": round(r["m2"], 4), "diff": round(r["d2"], 4)},
                      "confound": confound(es, half_at, reads if scope == "ALL" else by_sport[scope], r["diff"]),
                      "direction": "wins" if r["diff"] > 0 else "loses"})
    found.sort(key=lambda f: -abs(f["t"]))

    hist = {}
    try:
        hist = json.loads(OUT_JSON.read_text()).get("findings") or {}
    except (OSError, ValueError):
        pass
    now_keys = {f["key"] for f in found}
    for f in found:
        h = hist.setdefault(f["key"], {"firstSeen": today, "days": [], "history": []})
        if today not in h["days"]:
            h["days"].append(today)
        h["history"] = (h["history"] + [{"date": stamp, "n": f["n"], "mean": f["mean"], "t": f["t"]}])[-30:]
        h.update(text=f["text"], last=f, lastSeen=today, status="holding" if len(h["days"]) >= HOLD_DAYS else "new")
        f["status"], f["firstSeen"], f["daysSeen"] = h["status"], h["firstSeen"], len(h["days"])
    faded = []
    for key, h in hist.items():
        if key in now_keys:
            continue
        scope, cond = key.split("|", 1)
        cur = results.get((scope, cond))
        t_now = cur[0]["t"] if cur else 0.0
        if h.get("status") in ("new", "holding") and abs(t_now) < FADE_T:
            h["status"] = "faded"
            h["fadedOn"] = today
        if h.get("status") == "faded":
            faded.append({"key": key, "text": h.get("text"), "was": h.get("last", {}), "tNow": round(t_now, 2),
                          "fadedOn": h.get("fadedOn")})
        elif h.get("status") in ("new", "holding"):
            h["status"] = "below bar"
    by_chance = round(tested * 0.0455, 1)
    report = {"asOf": stamp, "reads": len(reads), "excluded": sorted(pull.PARKED), "baseline": round(base, 4),
              "halfSplit": half_at, "tested": tested, "expectedByChance": by_chance,
              "price": price_check(graded), "findings": found, "themes": themes(found)}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"asOf": stamp, "report": report, "findings": hist}, indent=1) + "\n")
    OUT_MD.write_text(markdown(report, faded))
    return {"findings": len(found), "holding": sum(1 for f in found if f["status"] == "holding"), "tested": tested}


THEMES = [
    ("Schedule (rest, travel, time zones)", ("restDays", "restEdge", "travel", "travelEdge", "tzShift", "shortWeek")),
    ("Price against Pinnacle", ("pinEdge", "sharpDivPick", "sharpDiv", "sharpGapPick", "sharpGapOpen", "bookAtPick")),
    ("Size of the read's edge", ("edgeBar",)),
    ("Line movement before the pick", ("moveBeforePick", "steamBeforePick")),
    ("Market and side (favourite, dog, over, under)", ("market", "role", "venue", "keyNumber")),
    ("Timing and news", ("timing", "injury", "wind", "precip")),
]


def themes(found):
    """Groups findings by what they are about and says whether they point the same way, so the review reads as a
    few explanations instead of a list of slices."""
    out = []
    for name, keys in THEMES:
        fs = [f for f in found if any(c.split("=")[0] in keys for c in f["condition"].split("&"))]
        if not fs:
            continue
        wins = [f for f in fs if f["direction"] == "wins"]
        loses = [f for f in fs if f["direction"] == "loses"]
        best = max(fs, key=lambda f: abs(f["t"]))
        def short(f):
            body = " and ".join(phrase(c) for c in f["condition"].split("&"))
            return body if f["scope"] == "ALL" else f"{body} ({f['scope']})"
        out.append({"theme": name, "findings": len(fs), "wins": len(wins), "loses": len(loses),
                    "wins_on": [short(f) for f in wins][:4], "loses_on": [short(f) for f in loses][:4],
                    "strongest": best["text"], "strongestT": best["t"],
                    "holding": sum(1 for f in fs if f.get("status") == "holding")})
    return sorted(out, key=lambda t: -t["findings"])


def pct(v):
    return f"{v * 100:+.1f}%" if isinstance(v, (int, float)) else "n/a"


def markdown(rep, faded):
    L = [f"# Findings ({rep['asOf'][:16].replace('T', ' ')}Z)", "",
         "Generated by findings.py after every grade run. Do not edit. EDGE's own review of what separates reads that",
         "beat the close from reads that lost. Leads, never rules: a finding becomes a pattern only as a measured shadow",
         "pattern approved at a weekly review.", "",
         f"Sample: {rep['reads']} counted, graded reads (parked patterns left out: {', '.join(rep['excluded'])}); baseline "
         f"CLV {pct(rep['baseline'])}. Halves split at {rep['halfSplit'][:16]}Z; a finding must hold in both. "
         f"Each condition is compared with every other read in its scope. {rep['tested']} conditions tested: about "
         f"{rep['expectedByChance']} would clear |t| {MIN_T:g} by chance; {len(rep['findings'])} cleared it and held in "
         "both halves.", ""]
    pr = rep.get("price") or {}
    if pr:
        L += ["## Price or direction?", "",
              "| Price taken vs Pinnacle's fair price | Reads | Mean CLV | Market move after | Beat the close |",
              "|---|---|---|---|---|"]
        for k, v in pr.items():
            L.append(f"| {k} | {v['n']} | {pct(v['clv'])} | {pct(v['moveAfter'])} | {v['beatClose']:.0%} |")
        moves = [v["moveAfter"] for k, v in pr.items() if k != "no Pinnacle at pick"]
        if moves and min(moves) > 0:
            L += ["", "Reading: the market moved our way after the pick in every price group, so direction is mostly "
                      "right; what decides CLV is the price paid against Pinnacle's fair price."]
        elif moves and max(moves) < 0:
            L += ["", "Reading: the market moved against us in every price group: the reads' direction is the problem, "
                      "not only the price."]
    th = rep.get("themes") or []
    if th:
        L += ["", "## What it adds up to (themes)", ""]
        for t in th:
            side = []
            if t["wins_on"]:
                side.append("beat the close when " + "; ".join(t["wins_on"]))
            if t["loses_on"]:
                side.append("lost when " + "; ".join(t["loses_on"]))
            L.append(f"- **{t['theme']}**: {t['findings']} finding{'s' if t['findings'] != 1 else ''} "
                     f"({t['holding']} holding). Reads " + ", and ".join(side) + ".")
    for title, want in (("## Conditions where we win", "wins"), ("## Conditions where we lose", "loses")):
        fs = [f for f in rep["findings"] if f["direction"] == want]
        L += ["", title, ""]
        if not fs:
            L.append("None clear the bar yet.")
            continue
        for f in fs[:12]:
            c = f["confound"]
            note = ""
            if c.get("verdict"):
                w = c.get("without") or {}
                note = (f" {c['share']:.0%} of these reads are {c['topPattern']}; without it the difference is "
                        f"{pct(w.get('diff'))} on {w.get('n')}: {c['verdict']}.")
            days = f"{f['daysSeen']} day" + ("s" if f["daysSeen"] != 1 else "")
            L.append(f"- **{f['status']}** (seen {days}, since {f['firstSeen']}): {f['text']}: CLV {pct(f['mean'])} on "
                     f"{f['n']} vs {pct(f['outside'])} on the rest (difference t {f['t']:+.1f}); held in both halves "
                     f"({pct(f['half1']['diff'])} on {f['half1']['n']}, {pct(f['half2']['diff'])} on {f['half2']['n']})."
                     f"{note}")
    if faded:
        L += ["", "## Faded (found before, no longer there)", ""]
        for f in faded[:8]:
            w = f.get("was") or {}
            L.append(f"- {f['text']}: was {pct(w.get('mean'))} on {w.get('n')} (t {w.get('t')}), now t {f['tNow']:+.1f}"
                     f" (faded {f.get('fadedOn')}).")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    print(json.dumps(build()))
