#!/usr/bin/env python3
"""EDGE edge stack (v1): the desk's "instinct". Small, measured edges that are independent of each other are added
up on the same game and side, so a combination can clear a bar no single one clears. Two patterns:

  edge-stack   On one row, the expected remaining move from every measured pattern that has read it (news-lag,
               rest-spot, goalie-news, wind-total, ncaaf-total-move, nhl-ml-move, nhl-total-move) plus the
               market's measured opening drift and NHL schedule spots, summed and shrunk for overlap.
               Needs 2+ independent sources pointing the same way.
  sharp-drift  Pinnacle's no-vig price now, moved by the part of the measured open-to-close drift still to come,
               against the best retail price on the same line. The price-gap scan, aimed at where Pinnacle will
               close instead of where it is.

  python3 edge_stack.py          stamp reads
  python3 edge_stack.py --dry    show them

Measured drifts (open to close, probability points unless noted; see stats/backtest_drift.md):
  NHL moneyline home -0.6 (n 1,123, halves -0.9/-0.3); NHL over (same line) +0.55 (n 841)
  NHL home team on the 2nd night of a back-to-back vs a rested team: home a further -1.0 (halves -1.1/-1.0)
  NCAAF total line -0.38 points (n 548, halves -0.28/-0.49), about +0.7 under
  Soccer, Pinnacle early to close, 2022-2026: over 2.5 -0.43 to -0.56 in all 5 leagues; draw +0.30 to +0.56
  (home/away per league below). All t near 5 per league.
None of these is a pick alone; each is a stated, fixed input. The monthly backtest re-measures them and the weekly
review proposes changes; nothing here re-fits itself.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fair as fairlib
import pull

ROOT = Path(__file__).resolve().parent
STACKABLE = {"news-lag", "rest-spot", "goalie-news", "wind-total", "ncaaf-total-move", "ncaaf-spot", "nhl-ml-move",
             "nhl-total-move", "tennis-fatigue"}
INCLUDES_DRIFT = {"ncaaf-spot", "rest-spot"}   # measured as raw moves: the average drift is already inside
SHRINK = 0.85                 # overlap between sources (e.g. a back-to-back and the backup goalie it brings)
SOCCER_1X2 = {               # home, draw, away probability drift, Pinnacle early to close
    "EPL": (-0.0008, 0.0030, -0.0022), "LaLiga": (0.0010, 0.0040, -0.0050), "Bundesliga": (-0.0002, 0.0041, -0.0039),
    "SerieA": (-0.0033, 0.0056, -0.0023), "Ligue1": (-0.0039, 0.0037, 0.0002)}
SOCCER_OVER = {"EPL": -0.0043, "LaLiga": -0.0047, "Bundesliga": -0.0056, "SerieA": -0.0048, "Ligue1": -0.0044}
# Soccer early-price overreaction (stats/backtest_soccer_spots.md), probability per unit
LUCK = 0.0010            # per goal of (luck for minus luck against) in the last match, home minus away
FORM_H, FORM_A = 0.0009, 0.00075   # per point of points minus expected points over 5
FORM_X = 0.0004          # the other side's form gap, half-measured cross effect
LAST_TOTALS = 0.00072    # over 2.5, per goal of both teams' last-match totals above 5.5
_FORM = None


def team_form(league, name):
    global _FORM
    if _FORM is None:
        _FORM = (pull.load(ROOT / "stats" / "soccer_form.json", {}).get("leagues") or {})
    teams = _FORM.get(league) or {}
    import difflib
    import unicodedata
    n = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    best, score = None, 0.0
    for t, v in teams.items():
        tn = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
        sc = 1.0 if (n.startswith(tn) or tn.startswith(n)) else difflib.SequenceMatcher(None, n, tn).ratio()
        if sc > score:
            best, score = v, sc
    return best if score >= 0.75 else None


NHL_HOME = -0.006
NHL_OVER = 0.0055
NHL_HOME_B2B = -0.010
NCAAF_TOTAL_PTS = -0.38
NCAAF_PER_POINT = 0.018
SNAP_MAX_MIN = 90
SOFT = ["draftkings", "fanduel", "betmgm", "williamhill_us"]
BAR = 0.03


def novig(snap, keys):
    if not snap or any(k not in snap for k in keys):
        return None
    return fairlib.probs(snap, keys)


def left_share(row, now):
    """Share of the open-to-close drift still to come, assuming it accrues evenly from this desk's open."""
    try:
        t0, t1 = pull.parse(row.get("openTime") or row["openSnap"]["time"]), pull.parse(row["commence"])
    except Exception:  # noqa: BLE001
        return 1.0
    span = (t1 - t0).total_seconds()
    return 1.0 if span <= 0 else max(0.0, min(1.0, (t1 - now).total_seconds() / span))


def nhl_home_b2b(row, games):
    """True when the home team played the day before and the away team did not."""
    day = (pull.parse(row["commence"]) - timedelta(hours=6)).date()
    mascot = lambda s: (s or "").split()[-1].lower()
    played = {}
    for g in games:
        if not g.get("date"):
            continue
        d = (pull.parse(g["date"]) - timedelta(hours=6)).date()
        for side in ("home", "away"):
            played.setdefault(mascot(g.get(side)), set()).add(d)
    h, a = played.get(mascot(row["home"]), set()), played.get(mascot(row["away"]), set())
    y = day - timedelta(days=1)
    return y in h and y not in a and (day - timedelta(days=2)) not in a


def drift_prob(row, now, nhl_games):
    """Expected remaining drift by side, in probability, for the row's market. None if no measured drift."""
    sport, market = row.get("sport"), row.get("market")
    share = left_share(row, now)
    if sport == "NHL" and market == "h2h":
        home = NHL_HOME * share
        if nhl_home_b2b(row, nhl_games):
            home += NHL_HOME_B2B          # schedule known in advance; counts in full until the start
        return {"home": home, "away": -home}
    if sport == "NHL" and market == "total":
        return {"over": NHL_OVER * share, "under": -NHL_OVER * share}
    if sport == "NCAAF" and market == "total":
        d = -NCAAF_TOTAL_PTS * NCAAF_PER_POINT * share         # line drifts down: under gains
        return {"under": d, "over": -d}
    if sport in SOCCER_1X2 and market == "h2h":
        h, d, a = SOCCER_1X2[sport]
        fh, fa = team_form(sport, row["home"]), team_form(sport, row["away"])
        if fh and fa:                      # early prices overreact to luck and to points above expected points
            lh, la = fh["luck1"], fa["luck1"]
            gh, ga = fh.get("formgap5") or 0.0, fa.get("formgap5") or 0.0
            ah = -LUCK * (lh - la) - FORM_H * gh + FORM_X * ga
            aa = -LUCK * (la - lh) - FORM_A * ga + FORM_X * gh
            h, a, d = h + ah, a + aa, d - ah - aa
        return {"home": h * share, "draw": d * share, "away": a * share}
    if sport in SOCCER_OVER and market == "total" and (row.get("lastSnap") or {}).get("line") == 2.5:
        o = SOCCER_OVER[sport]
        fh, fa = team_form(sport, row["home"]), team_form(sport, row["away"])
        if fh and fa:
            o += LAST_TOTALS * (fh["tot1"] + fa["tot1"] - 5.5)
        o *= share
        return {"over": o, "under": -o}
    return None


def contribution(p):
    """A measured read's expected move, home/over direction: points for point markets, probability otherwise."""
    market, sport = p["market"], p["sport"]
    if market in ("spread",) or (market == "total" and sport not in pull.PROB_TOTALS):
        if p.get("marketNumber") is None:
            return None, None
        return p["fair"] - p["marketNumber"], "points"
    keys = ["home", "away"] if market == "h2h" else ["over", "under"]
    mp = novig(p.get("marketPrices"), keys)
    if not mp:
        return None, None
    return p["fair"] - mp[keys[0]], "prob"


def stack(rows, picks, now, nhl_games, done):
    out = []
    by_row = {}
    for p in picks:
        if p.get("pattern") in STACKABLE and p.get("kind") in ("pick", "lean") and p.get("commence", "") > pull.iso(now):
            by_row.setdefault(p["rowId"], {})[p["pattern"]] = p        # latest read per pattern wins
    for rid, reads in by_row.items():
        row = rows.get(rid)
        if not row or rid in done or not row.get("lastSnap"):
            continue
        parts, unit = [], None
        for pat, p in reads.items():
            c, u = contribution(p)
            if c is None or (unit and u != unit):
                continue
            unit = u
            parts.append((pat, c))
        # Situational values measured as raw open-to-close moves already include the market's average drift.
        dp = None if INCLUDES_DRIFT & set(reads) else drift_prob(row, now, nhl_games)
        if dp:
            if unit == "points" and row["market"] == "total" and row["sport"] == "NCAAF":
                parts.append(("opening drift", (dp.get("over", 0)) / NCAAF_PER_POINT))
            elif unit in (None, "prob") and row["market"] in ("h2h", "total"):
                key = "home" if row["market"] == "h2h" else "over"
                if key in dp:
                    unit = unit or "prob"
                    parts.append(("opening drift", dp[key]))
        if len(parts) < 2:
            continue
        signs = {1 if c > 0 else -1 for _, c in parts if c}
        if len(signs) != 1:
            continue                       # sources disagree: no stack
        total = sum(c for _, c in parts) * SHRINK
        snap = row["lastSnap"]
        if unit == "points":
            cur = snap.get("line")
            if cur is None:
                continue
            fair = cur + total
        else:
            keys = ["home", "away"] if row["market"] == "h2h" else ["over", "under"]
            mp = novig(snap, keys) if row["market"] != "h2h" or "draw" not in snap else None
            if not mp:
                continue
            fair = min(max(mp[keys[0]] + total, 0.02), 0.98)
        why = "; ".join(f"{pat} {c:+.3f}" for pat, c in parts)
        out.append((row, fair, f"Edge stack ({len(parts)} sources, x{SHRINK} for overlap): {why}. Fair {fair:.3f}."))
    return out


def sharp_drift(rows, now, nhl_games, have):
    entries = []
    for row in rows.values():
        if not row.get("commence") or not (pull.iso(now) < row["commence"] <= pull.iso(now + timedelta(hours=48))):
            continue
        snap = row.get("lastSnap") or {}
        books = snap.get("books") or {}
        pin = books.get("pinnacle")
        if not pin or not snap.get("time") or (now - pull.parse(snap["time"])).total_seconds() > SNAP_MAX_MIN * 60:
            continue
        dp = drift_prob(row, now, nhl_games)
        if not dp:
            continue
        keys = [k for k in ("home", "away", "draw", "over", "under") if k in pin]
        fair = fairlib.probs(pin, keys)
        best = None
        for bk in SOFT:
            soft = books.get(bk)
            if not soft or (row["market"] == "total" and soft.get("line") != pin.get("line")):
                continue
            for side in keys:
                if side not in soft or side not in dp:
                    continue
                pf = fair[side] + dp[side]
                edge = pf - pull.implied(soft[side])
                if edge > 0.10:
                    continue
                if not best or edge > best["edge"]:
                    best = {"book": bk, "side": side, "price": soft[side], "line": soft.get("line"), "fair": pf,
                            "pin": fair[side], "drift": dp[side], "edge": edge}
        if not best or best["edge"] < BAR / 2:
            continue
        pid = f"{row['id']}|{best['side']}|{pull.VERSION}|sharp-drift"
        if pid in have:
            continue
        grade = "A" if best["edge"] >= BAR else "B"
        name = pull.BOOK_NAMES.get(best["book"], best["book"])
        line = best["line"] if row["market"] == "total" else None
        entries.append({
            "pickId": pid, "kind": "pick", "grade": grade, "rowId": row["id"], "sport": row["sport"],
            "event": row["event"], "commence": row["commence"], "market": row["market"], "side": best["side"],
            "lineAtPick": line, "priceAtPick": best["price"], "bookAtPick": name, "marketNumber": snap.get("line"),
            "marketPrices": {k: snap[k] for k in ("home", "away", "over", "under", "draw") if k in snap},
            "priceTime": snap["time"], "pickedAt": pull.iso(now), "fair": round(best["fair"], 4),
            "projection": round(best["fair"], 4), "edge": round(best["edge"], 4), "edgeUnit": "prob", "bar": BAR,
            "fullBar": best["edge"] >= BAR, "confidence": "medium", "pattern": "sharp-drift",
            "reason": (f"{name} {best['side']} {best['price']:+g} implies {pull.implied(best['price']):.1%}. Pinnacle no-vig "
                       f"{best['pin']:.1%} plus the measured drift still to come {best['drift']:+.2%} = {best['fair']:.1%}. "
                       f"Edge {best['edge']:+.1%}."),
            "falsifier": "The close no-vig on this side ends below the price taken (CLV under 0).",
            "modelVersion": pull.VERSION, "tier": "shadow", "stakeUnits": 0.0, "by": "edge_stack.py"})
    return entries


SOCCER_MIN_MOVE = 0.015   # set by Zack 2026-10-14: a smaller expected move still reads, but only as a lean (graded, stackable, never a pick) (over probability)


def soccer_reads(rows, now, done):
    """soccer-drift: on 2.5-goal totals in the five measured leagues, the over/under side the drift model (league
    drift + last-match totals) expects to gain, read once per game within 48 hours. Leans unless the gap is large;
    their job is to build the CLV record for the soccer drift model."""
    out = []
    for row in rows.values():
        if row.get("sport") not in SOCCER_OVER or row.get("market") != "total" or row.get("id") in done:
            continue
        if not row.get("commence") or not (pull.iso(now) < row["commence"] <= pull.iso(now + timedelta(hours=48))):
            continue
        snap = row.get("lastSnap") or {}
        mp = novig(snap, ["over", "under"])
        dp = drift_prob(row, now, [])
        if not mp or not dp or abs(dp["over"]) < 0.003:
            continue
        fair = min(max(mp["over"] + dp["over"], 0.02), 0.98)
        if abs(dp["over"]) < SOCCER_MIN_MOVE:
            pull.LEAN_CAP.add((row["id"], "soccer-drift"))
        out.append((row, fair, f"Soccer drift model: league under-drift and last-match totals give over {dp['over']:+.2%} "
                               f"still to come; over now {mp['over']:.1%}, fair {fair:.1%}."))
    return out


def main(dry=False):
    now = datetime.now(timezone.utc)
    ledger = pull.load(pull.LEDGER, {"rows": []})
    rows = {r.get("id"): r for r in ledger.get("rows") or []}
    picks_doc = pull.load(pull.PICKS, {"picks": []})
    picks = picks_doc["picks"]
    nhl = pull.load(ROOT / "stats" / "nhl_games.json", {}).get("games") or {}
    nhl_games = list(nhl.values()) if isinstance(nhl, dict) else nhl
    done = {p.get("rowId") for p in picks if p.get("pattern") == "edge-stack"}
    stacks = stack(rows, picks, now, nhl_games, done)
    socc = soccer_reads(rows, now, {p.get("rowId") for p in picks if p.get("pattern") == "soccer-drift"})
    drifts = sharp_drift(rows, now, nhl_games, {p.get("pickId") for p in picks})
    if dry:
        for row, fair, why in stacks:
            print("STACK", row["id"], why)
        for row, fair, why in socc:
            print("SOCCER", row["id"], why)
        for e in drifts:
            print("SHARP-DRIFT", e["grade"], e["rowId"], e["reason"])
    else:
        if drifts:
            picks.extend(drifts)
            pull.save(pull.PICKS, picks_doc)
        from argparse import Namespace
        for sport in {r["sport"] for r, _, _ in stacks}:
            if sport not in pull.READ:
                pull.READ = pull.READ + [sport]
        for sport in {r["sport"] for r, _, _ in socc}:
            if sport not in pull.READ:
                pull.READ = pull.READ + [sport]
        for row, fair, why in socc:
            args = Namespace(id=row["id"], fair=f"{fair:.3f}", confidence="medium", reason=why,
                             falsifier="The over/under price closes at or past the current price on the other side.",
                             pattern="soccer-drift", stake="0", big=True, by="edge_stack.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
        for row, fair, why in stacks:
            args = Namespace(id=row["id"], fair=f"{fair:.3f}", confidence="medium", reason=why,
                             falsifier="The line closes at or past the current number on the other side.",
                             pattern="edge-stack", stake="0", big=True, by="edge_stack.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"stacks": len(stacks), "sharpDrift": len(drifts), "soccerDrift": len(socc), "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
