#!/usr/bin/env python3
"""EDGE sharp-vs-soft scan (v1). Stamps the sharp-soft pattern with no analyst judgment.

  python3 sharp.py            scan every upcoming row pull.py priced in this run
  python3 sharp.py --dry      show what would be stamped, write nothing

The idea
  Pinnacle takes the sharpest action and moves first. Its price with the margin removed
  (no-vig) is the best free estimate of the true probability. When a retail book (DraftKings,
  FanDuel, BetMGM, Caesars) hangs a price on the SAME line that is better than that fair
  probability, the retail price is stale and should beat the close.

Rules
  Same line only. A soft book on a different spread or total number is skipped in v1.
  Pinnacle must have both sides and be updated within SHARP_STALE_MIN of the soft book.
  Edge is fair probability minus the probability the soft price implies.
  A  edge >= BAR (full bar)      B  edge >= BAR / 2      under that: not stamped.
  An edge over SHARP_MAX is treated as a data error and skipped, never stamped.
  One pick per row, side and pattern. The first price seen is the price taken. Never re-stamped.
  The pick is graded by grade.py like any other: its price against the DraftKings close.
  Shadow (0 units) until grade.py makes the pattern official. Nothing here types a price.
"""

import json
import os
import sys
from datetime import datetime, timezone

import pull

PATTERN = "sharp-soft"
SHARP = "pinnacle"
SOFT = [b for b in os.environ.get("EDGE_SOFT_BOOKS", "draftkings,fanduel,betmgm,williamhill_us").split(",") if b]
BAR = float(os.environ.get("SHARP_BAR", "0.03"))          # full bar, in probability
SHARP_MAX = float(os.environ.get("SHARP_MAX", "0.10"))    # above this is a data error
STALE_MIN = float(os.environ.get("SHARP_STALE_MIN", "60"))
SPORTS = [s.strip().upper() for s in os.environ.get("SHARP_SPORTS", "").split(",") if s.strip()] or pull.ACTIVE


def no_vig(snap, keys):
    total = sum(pull.implied(snap[k]) for k in keys)
    return {k: pull.implied(snap[k]) / total for k in keys}


def sides_for(market):
    return ("over", "under") if market == "total" else ("home", "away")


def best_edge(row, books):
    """The single best soft price on this row, measured against Pinnacle no-vig. None if nothing qualifies."""
    market = row["market"]
    pin = books.get(SHARP)
    sides = sides_for(market)
    if not pin or any(s not in pin for s in sides):
        return None, "no Pinnacle price"
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in pin]
    fair = no_vig(pin, keys)
    best, why = None, "no soft price beat Pinnacle"
    for bk in SOFT:
        soft = books.get(bk)
        if not soft or any(s not in soft for s in sides):
            continue
        if market in ("spread", "total") and soft.get("line") != pin.get("line"):
            why = "lines differ"
            continue
        if pin.get("updated") and soft.get("updated"):
            gap = abs((pull.parse(soft["updated"]) - pull.parse(pin["updated"])).total_seconds()) / 60
            if gap > STALE_MIN:
                why = "Pinnacle price stale"
                continue
        for side in sides:
            edge = fair[side] - pull.implied(soft[side])
            if edge > SHARP_MAX:
                print(f"skip {row['id']} {bk} {side}: edge {edge:.3f} over {SHARP_MAX}, treated as data error")
                continue
            if best is None or edge > best["edge"]:
                best = {"book": bk, "side": side, "price": soft[side], "line": soft.get("line"),
                        "fair": fair[side], "edge": edge, "pinPrice": pin[side], "pinLine": pin.get("line")}
    return best, why


def scan(dry=False):
    ledger = pull.load(pull.LEDGER, {"rows": []})
    picks = pull.load(pull.PICKS, {"picks": []})
    have = {p.get("pickId") for p in picks["picks"]}
    status = next((p.get("status") for p in ledger.get("patterns") or [] if p.get("id") == PATTERN), "shadow")
    now_dt = datetime.now(timezone.utc)
    now = pull.iso(now_dt)
    stamped, seen, reasons = [], 0, {}

    for row in ledger.get("rows") or []:
        snap = row.get("lastSnap") or {}
        books = snap.get("books")
        if not books or row.get("sport") not in SPORTS:
            continue
        if not row.get("commence") or row["commence"] <= now:
            continue
        age = (now_dt - pull.parse(snap["time"])).total_seconds() / 60
        if age > pull.STALE_MIN:
            continue
        seen += 1
        best, why = best_edge(row, books)
        if not best or best["edge"] < BAR / 2:
            reasons[why if not best else "under half the bar"] = reasons.get(why if not best else "under half the bar", 0) + 1
            continue
        market, side = row["market"], best["side"]
        pick_id = f"{row['id']}|{side}|{pull.VERSION}|{PATTERN}"
        if pick_id in have:
            reasons["already stamped"] = reasons.get("already stamped", 0) + 1
            continue
        grade = "A" if best["edge"] >= BAR else "B"
        tier = "official" if status == "official" and grade == "A" else "shadow"
        stake = 0.5 if tier == "official" else 0.0
        if market == "spread":
            line = best["line"] if side == "home" else -best["line"]
        elif market == "total":
            line = best["line"]
        else:
            line = None
        name = pull.BOOK_NAMES.get(best["book"], best["book"])
        shown = f"{side} {line:+g}" if market == "spread" else (f"{side} {line:g}" if market == "total" else side)
        entry = {
            "pickId": pick_id, "kind": "pick", "grade": grade, "rowId": row["id"], "sport": row["sport"],
            "event": row["event"], "commence": row.get("commence"), "market": market,
            "side": side, "lineAtPick": line, "priceAtPick": best["price"], "bookAtPick": name,
            "marketNumber": snap.get("line"),
            "marketPrices": {k: snap[k] for k in ("home", "away", "over", "under", "draw") if k in snap},
            "priceTime": snap["time"], "pickedAt": now, "fair": round(best["fair"], 4),
            "projection": round(best["fair"], 4), "edge": round(best["edge"], 4), "edgeUnit": "prob",
            "bar": BAR, "fullBar": best["edge"] >= BAR, "confidence": "medium", "pattern": PATTERN,
            "reason": (f"{name} {shown} {best['price']:+g} implies {pull.implied(best['price']):.1%}. "
                       f"Pinnacle {best['pinPrice']:+g} no-vig is {best['fair']:.1%}. Edge {best['edge']:+.1%}."),
            "falsifier": "The close no-vig on this side ends below the price taken (CLV under 0).",
            "modelVersion": pull.VERSION, "tier": tier, "stakeUnits": stake, "by": "sharp.py",
        }
        stamped.append(entry)
        have.add(pick_id)

    if stamped and not dry:
        picks["picks"].extend(stamped)
        pull.save(pull.PICKS, picks)
    for e in stamped:
        print(f"{'WOULD STAMP' if dry else 'STAMPED'} {e['grade']} {e['sport']} {e['event']} | {e['reason']}")
    print(json.dumps({"pattern": PATTERN, "rowsScanned": seen, "stamped": len(stamped),
                      "skipped": reasons, "dry": dry, "status": status}))


if __name__ == "__main__":
    scan(dry="--dry" in sys.argv[1:])
