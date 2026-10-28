#!/usr/bin/env python3
"""EDGE sharp-vs-soft scan (v1). Stamps the sharp-soft pattern with no analyst judgment.

  python3 sharp.py            scan every upcoming row pull.py priced in this run
  python3 sharp.py --dry      show what would be stamped, write nothing

The idea
  Pinnacle takes the sharpest action and moves first. Its price with the margin removed
  (no-vig) is the best free estimate of the true probability. When a retail book (DraftKings,
  FanDuel, BetMGM, Caesars) hangs a price on the SAME line that is better than that fair
  probability, the retail price is stale and should beat the close.

Two patterns, tested separately
  sharp-soft      same line at both books. The cleanest test.
  sharp-soft-alt  the soft book is on a different spread or total number, at most ALT_MAX points
                  away. Pinnacle's fair probability is moved to the soft line with the same per-point
                  and key-number values grade.py uses. Point sports only (NFL, NCAAF, NBA).
                  Estimated, so it earns trust on its own record.

Rules
  Pinnacle must have both sides and be updated within SHARP_STALE_MIN of the soft book.
  Only prices pulled within SHARP_SNAP_MAX_MIN are scanned, so a stamp is never an old price.
  Edge is fair probability (Pinnacle, margin removed with Shin's method) minus the probability
  the soft price implies.
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

import fair
import pull

PATTERN = "sharp-soft"
ALT_PATTERN = "sharp-soft-alt"
ALT_SPORTS = {"NFL", "NCAAF", "NBA"}
ALT_MAX = float(os.environ.get("SHARP_ALT_MAX", "1.0"))
PER_POINT = {("NFL", "spread"): 0.030, ("NFL", "total"): 0.022, ("NCAAF", "spread"): 0.025,
             ("NCAAF", "total"): 0.018, ("NBA", "spread"): 0.030, ("NBA", "total"): 0.025}
KEY_NUMBERS = (3, 7)
SHARP = "pinnacle"
# 2026-10-28: the five books added to pull.BOOKS are soft books too (more sharp-soft reads at no credit cost).
SOFT = [b for b in os.environ.get("EDGE_SOFT_BOOKS", "draftkings,fanduel,betmgm,williamhill_us,betrivers,fanatics,"
                                                 "espnbet,hardrockbet,ballybet").split(",") if b]
BAR = float(os.environ.get("SHARP_BAR", "0.03"))          # full bar, in probability
SHARP_MAX = float(os.environ.get("SHARP_MAX", "0.10"))    # above this is a data error
STALE_MIN = float(os.environ.get("SHARP_STALE_MIN", "60"))
SNAP_MAX_MIN = float(os.environ.get("SHARP_SNAP_MAX_MIN", "90"))   # only prices pulled this recently are scanned
SPORTS = [s.strip().upper() for s in os.environ.get("SHARP_SPORTS", "").split(",") if s.strip()] or pull.ACTIVE


def no_vig(snap, keys):
    """Pinnacle's fair probabilities with the margin removed by Shin's method (fair.py)."""
    return fair.probs(snap, keys)


def sides_for(market):
    return ("over", "under") if market == "total" else ("home", "away")


def gained(market, side, soft_line, pin_line):
    """Points the soft line gives this side over the Pinnacle line. Positive is better for the bettor."""
    if market == "spread":
        return soft_line - pin_line if side == "home" else pin_line - soft_line
    return pin_line - soft_line if side == "over" else soft_line - pin_line


def line_value(sport, market, side, soft_line, pin_line):
    """Win-probability value of the line difference, the same way grade.py values a line move."""
    g = gained(market, side, soft_line, pin_line)
    adj = PER_POINT[(sport, market)] * g
    if market == "spread" and sport in ("NFL", "NCAAF") and g:
        lo, hi = sorted((abs(soft_line), abs(pin_line)))
        crossed = sum(1 for k in KEY_NUMBERS if lo < k <= hi or lo <= k < hi)
        adj += 0.03 * crossed * (1 if g > 0 else -1)
    return adj


def best_edge(row, books, alt=False):
    """The single best soft price on this row, measured against Pinnacle no-vig.
    alt=False: same line only. alt=True: different lines only, valued to the soft line.
    Returns (best or None, reason)."""
    market, sport = row["market"], row.get("sport")
    pin = books.get(SHARP)
    sides = sides_for(market)
    if market == "h2h" and pin and "draw" in pin:
        sides = sides + ("draw",)          # three-way soccer: the draw is a price too
    if not pin or any(s not in pin for s in sides):
        return None, "no Pinnacle price"
    if alt and (market not in ("spread", "total") or (sport, market) not in PER_POINT):
        return None, "alt not priced for this market"
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in pin]
    fair = no_vig(pin, keys)
    best, why = None, "no soft price beat Pinnacle"
    for bk in SOFT:
        soft = books.get(bk)
        if not soft or any(s not in soft for s in sides):
            continue
        differs = market in ("spread", "total") and soft.get("line") != pin.get("line")
        if differs != alt:
            why = "lines differ" if differs else "same line"
            continue
        if alt and abs(soft["line"] - pin["line"]) > ALT_MAX:
            why = "lines too far apart"
            continue
        if pin.get("updated") and soft.get("updated"):
            gap = abs((pull.parse(soft["updated"]) - pull.parse(pin["updated"])).total_seconds()) / 60
            if gap > STALE_MIN:
                why = "Pinnacle price stale"
                continue
        for side in sides:
            adj = line_value(sport, market, side, soft["line"], pin["line"]) if alt else 0.0
            p_fair = min(max(fair[side] + adj, 0.01), 0.99)
            edge = p_fair - pull.implied(soft[side])
            if edge > SHARP_MAX:
                print(f"skip {row['id']} {bk} {side}: edge {edge:.3f} over {SHARP_MAX}, treated as data error")
                continue
            if best is None or edge > best["edge"]:
                best = {"book": bk, "side": side, "price": soft[side], "line": soft.get("line"),
                        "fair": p_fair, "edge": edge, "pinPrice": pin[side], "pinLine": pin.get("line"),
                        "pinFair": fair[side], "lineAdj": adj}
    return best, why


def scan(dry=False):
    ledger = pull.load(pull.LEDGER, {"rows": []})
    picks = pull.load(pull.PICKS, {"picks": []})
    have = {p.get("pickId") for p in picks["picks"]}
    statuses = {p.get("id"): p.get("status") for p in ledger.get("patterns") or []}
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
        if age > SNAP_MAX_MIN:
            continue
        seen += 1
        for pattern, alt in ((PATTERN, False), (ALT_PATTERN, True)):
            entry = stamp_one(row, snap, books, pattern, alt, statuses.get(pattern, "shadow"), have, reasons, now)
            if entry:
                stamped.append(entry)
                have.add(entry["pickId"])

    if not dry:
        stamped = pull.gate_direct(stamped, picks["picks"], {r.get("id"): r.get("lastSnap") for r in ledger.get("rows") or []})
    if stamped and not dry:
        picks["picks"].extend(stamped)
        pull.save(pull.PICKS, picks)
    for e in stamped:
        print(f"{'WOULD STAMP' if dry else 'STAMPED'} {e['grade']} {e['pattern']} {e['sport']} {e['event']} | {e['reason']}")
    print(json.dumps({"rowsScanned": seen, "stamped": len(stamped), "skipped": reasons, "dry": dry,
                      "status": {p: statuses.get(p, "shadow") for p in (PATTERN, ALT_PATTERN)}}))


def stamp_one(row, snap, books, pattern, alt, status, have, reasons, now):
    def skip(why):
        key = f"{pattern}: {why}"
        reasons[key] = reasons.get(key, 0) + 1

    best, why = best_edge(row, books, alt)
    if not best:
        skip(why)
        return None
    if best["edge"] < BAR / 2:
        skip("under half the bar")
        return None
    market, side = row["market"], best["side"]
    pick_id = f"{row['id']}|{side}|{pull.VERSION}|{pattern}"
    if pick_id in have:
        skip("already stamped")
        return None

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
        "bar": BAR, "fullBar": best["edge"] >= BAR, "confidence": "medium", "pattern": pattern,
        "reason": (f"{name} {shown} {best['price']:+g} implies {pull.implied(best['price']):.1%}. "
                   f"Pinnacle {best['pinPrice']:+g} no-vig is {best['pinFair']:.1%}"
                   + (f" at {best['pinLine']:g}, worth {best['fair']:.1%} at this line" if alt else "")
                   + f". Edge {best['edge']:+.1%}."),
        "falsifier": "The close no-vig on this side ends below the price taken (CLV under 0).",
        "modelVersion": pull.VERSION, "tier": tier, "stakeUnits": stake, "by": "sharp.py",
        "pinAtPick": pull.pin_at_pick(snap, side), "contextAtPick": pull.context_at_pick(row),
        "bestAtPick": pull.best_at_pick(snap, side),
        "priceBook": (pull.best_at_pick(snap, side) or {}).get("book"),   # same field as pull.py reads (north star)
    }
    if alt:
        entry["estimated"] = True
        entry["lineAdj"] = round(best["lineAdj"], 4)
    return entry


if __name__ == "__main__":
    scan(dry="--dry" in sys.argv[1:])
