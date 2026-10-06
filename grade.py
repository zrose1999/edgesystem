#!/usr/bin/env python3
"""EDGE grader (v2). Grades the picks, not the market.

What it measures, per pick:
  CLV     did the price we took beat the closing price on the SAME side?
          clvPoints: line gained vs the close (spread and total).
          clvProb:   close no-vig win probability minus the probability our price implied.
                     This is the main score. Above 0 means we beat the close.
  Result  win / loss / push from the final score, and units won at the price taken.

Patterns (named ideas in patterns.md) move on evidence only:
  shadow   default. Tracked, no money.
  official n >= OFFICIAL_N graded FULL-BAR picks, mean clvProb > 0, and t-stat >= T_MIN.
  retire   n >= OFFICIAL_N and mean clvProb <= 0. Retired patterns cannot take new picks.
Win rate is shown but never promotes a pattern. Results are noise long before CLV is.

The model does not compute any of this. It reads score.json.
"""

import json
import math
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger" / "ledger.json"
PICKS = ROOT / "ledger" / "picks.json"
SCORE = ROOT / "score.json"

OFFICIAL_N = int(os.environ.get("EDGE_OFFICIAL_N", "30"))
T_MIN = float(os.environ.get("EDGE_T_MIN", "1.5"))

# Rough win-probability value of one point of line, used only when the line moved.
# Flagged as estimated on the pick. Near NFL key numbers 3 and 7 the true value is higher.
PER_POINT = {
    ("NFL", "spread"): 0.030, ("NFL", "total"): 0.022,
    ("NCAAF", "spread"): 0.025, ("NCAAF", "total"): 0.018,
    ("NBA", "spread"): 0.030, ("NBA", "total"): 0.025,
    ("NHL", "spread"): 0.15, ("NHL", "total"): 0.12,
    ("MLB", "total"): 0.10, ("EPL", "total"): 0.20, ("UCL", "total"): 0.20, ("MLS", "total"): 0.20,
}
KEY_NUMBERS = {3, 7}


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def implied(american):
    a = float(american)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def payout(american):
    a = float(american)
    return a / 100 if a > 0 else 100 / -a


def no_vig(snap, side):
    """Fair probability of `side` at the close with the bookmaker margin removed."""
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in snap]
    total = sum(implied(snap[k]) for k in keys)
    return implied(snap[side]) / total


def side_line(snap, side, market):
    if market == "spread":
        return snap["line"] if side == "home" else -snap["line"]
    if market == "total":
        return snap["line"]
    return None


def clv(pick, close):
    market, side = pick["market"], pick["side"]
    fair = no_vig(close, side)
    paid = implied(pick["priceAtPick"])
    out = {"closeLine": side_line(close, side, market), "closePrice": close[side],
           "closeNoVig": round(fair, 4), "estimated": False}
    if market == "h2h":
        out["clvPoints"] = 0.0
        out["clvProb"] = round(fair - paid, 4)
        return out
    pick_line, close_line = pick["lineAtPick"], out["closeLine"]
    if market == "spread":
        gained = pick_line - close_line          # more points on our side is better
    else:
        gained = (close_line - pick_line) if side == "over" else (pick_line - close_line)
    out["clvPoints"] = round(gained, 2)
    adj = 0.0
    if gained:
        slope = PER_POINT.get((pick["sport"], market), 0.03)
        if market == "spread" and pick["sport"] in ("NFL", "NCAAF"):
            lo, hi = sorted((abs(pick_line), abs(close_line)))
            crossed = sum(1 for k in KEY_NUMBERS if lo < k <= hi or lo <= k < hi)
            adj += 0.03 * crossed * (1 if gained > 0 else -1)
        adj += slope * gained
        out["estimated"] = True
    out["clvProb"] = round(fair + adj - paid, 4)
    return out


def result(pick, score):
    h, a = score["home"], score["away"]
    market, side = pick["market"], pick["side"]
    if market == "spread":
        margin = (h - a) if side == "home" else (a - h)
        value = margin + pick["lineAtPick"]
    elif market == "total":
        value = (h + a - pick["lineAtPick"]) * (1 if side == "over" else -1)
    else:
        value = (h - a) if side == "home" else (a - h)   # a draw is a loss on a 2-way side pick
    if value > 0:
        return "win", round(payout(pick["priceAtPick"]), 3)
    if value < 0 or market == "h2h":
        return "loss", -1.0
    return "push", 0.0


def tstat(values):
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return 0.0 if var == 0 else mean / math.sqrt(var / n)


def main():
    ledger = load(LEDGER, {"rows": []})
    picks = load(PICKS, {"picks": []})
    rows = {r.get("id"): r for r in ledger.get("rows") or []}

    for pick in picks["picks"]:
        row = rows.get(pick["rowId"]) or {}
        close = row.get("closeSnap")
        if close and pick["side"] in close and "clvProb" not in pick:
            pick.update(clv(pick, close))
        if row.get("final") and "result" not in pick:
            pick["result"], pick["units"] = result(pick, row["score"])
            if pick.get("tier") == "official":
                pick["unitsStaked"] = round(pick["units"] * pick.get("stakeUnits", 0), 3)

    groups = defaultdict(list)
    for pick in picks["picks"]:
        groups[pick["pattern"]].append(pick)

    patterns = []
    for name, group in sorted(groups.items()):
        # Only full-bar picks can make a pattern official. Half-bar picks are tracked separately.
        graded = [p["clvProb"] for p in group if "clvProb" in p and p.get("fullBar", True)]
        half = [p["clvProb"] for p in group if "clvProb" in p and not p.get("fullBar", True)]
        settled = [p for p in group if p.get("result") in ("win", "loss")]
        n = len(graded)
        mean = sum(graded) / n if n else 0.0
        t = tstat(graded)
        if n >= OFFICIAL_N and mean > 0 and t >= T_MIN:
            status = "official"
        elif n >= OFFICIAL_N and mean <= 0:
            status = "retire"
        else:
            status = "shadow"
        patterns.append({
            "id": name, "status": status, "picks": len(group), "clvN": n,
            "meanClvProb": round(mean, 4), "tStat": round(t, 2),
            "halfBarN": len(half), "halfBarMeanClv": round(sum(half) / len(half), 4) if half else None,
            "beatClose": sum(1 for v in graded if v > 0),
            "wins": sum(1 for p in settled if p["result"] == "win"),
            "losses": sum(1 for p in settled if p["result"] == "loss"),
            "flatUnits": round(sum(p.get("units", 0) for p in group), 2),
            "note": f"Promotion needs {OFFICIAL_N} graded full-bar picks, mean CLV above 0, t at least {T_MIN}. Win rate never promotes.",
        })

    clv_all = [p["clvProb"] for p in picks["picks"] if "clvProb" in p]
    settled = [p for p in picks["picks"] if p.get("result") in ("win", "loss", "push")]
    official = [p for p in settled if p.get("tier") == "official"]
    score = {
        "picks": len(picks["picks"]),
        "graded": len(clv_all),
        "meanClvProb": round(sum(clv_all) / len(clv_all), 4) if clv_all else None,
        "beatClose": sum(1 for v in clv_all if v > 0),
        "record": "{}-{}-{}".format(*(sum(1 for p in settled if p["result"] == r) for r in ("win", "loss", "push"))),
        "flatUnits": round(sum(p.get("units", 0) for p in settled), 2),
        "officialRecord": "{}-{}-{}".format(*(sum(1 for p in official if p["result"] == r) for r in ("win", "loss", "push"))),
        "officialUnits": round(sum(p.get("unitsStaked", 0) for p in official), 2),
        "patterns": patterns,
    }

    ledger["patterns"] = patterns
    ledger["score"] = {k: v for k, v in score.items() if k != "patterns"}
    ledger["law"] = ("A pick is a row in picks.json with a price stamped by pull.py. CLV is the pick's price against "
                     "the close on the same side. Patterns promote on CLV over a sample, never on win rate.")
    save(LEDGER, ledger)
    save(PICKS, picks)
    save(SCORE, score)
    print(json.dumps(ledger["score"]))


if __name__ == "__main__":
    main()
