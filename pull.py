#!/usr/bin/env python3
"""EDGE price puller and pick stamper (v2).

  python pull.py            pull prices, closes and scores. This is what the jobs run.
  python pull.py pick ...   stamp a pick with the stored price. The model never types a price.

Rules
  DraftKings is the print. A BetMGM line is noted when it differs.
  The first print is the open and is never overwritten. In-play lines are never used.
  The close is the last DraftKings snapshot at or before start. It is looked up from
  history by event, so no run is needed during the game. Historical odds need a paid plan.
  Scores come from the scores endpoint. The model does not type a score.
  Nothing here writes the autopsy field. Reasons live on the pick.
  The key is ODDS_API_KEY. It is never written to a file.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger" / "ledger.json"
PICKS = ROOT / "ledger" / "picks.json"
API = "https://api.the-odds-api.com/v4"
STALE_MIN = int(os.environ.get("EDGE_STALE_MIN", "240"))
MAX_HIST = int(os.environ.get("EDGE_MAX_HIST_CALLS", "40"))
VERSION = os.environ.get("EDGE_MODEL_VERSION", "v1")

SPORTS = {
    "americanfootball_nfl": "NFL",
    "americanfootball_ncaaf": "NCAAF",
    "baseball_mlb": "MLB",
    "basketball_nba": "NBA",
    "icehockey_nhl": "NHL",
    "soccer_epl": "EPL",
    "soccer_uefa_champs_league": "UCL",
    "soccer_usa_mls": "MLS",
    "mma_mixed_martial_arts": "UFC",
}
# Only sports the desk actually reads are pulled. Each sport costs Odds API credits,
# and history calls for closes cost the most. Add a sport here when it gets real reads.
# EDGE_SPORTS overrides this, e.g. EDGE_SPORTS=NFL,NCAAF
ACTIVE = ["NFL", "NCAAF", "NBA", "NHL", "EPL", "UCL"]   # prices collected
READ = ["NFL"]                                          # sports the analyst reads and picks
_env = [s.strip().upper() for s in os.environ.get("EDGE_SPORTS", "").split(",") if s.strip()]
ACTIVE = _env or ACTIVE
# Credit guard. The Odds API reports credits left on every response.
# Under RESERVE, closes are looked up only for READ sports. Under FLOOR, no close lookups at all.
RESERVE = int(os.environ.get("EDGE_CREDIT_RESERVE", "3000"))
FLOOR = int(os.environ.get("EDGE_CREDIT_FLOOR", "300"))
CREDITS = {"remaining": None, "used": None}
SPORTS = {k: v for k, v in SPORTS.items() if v in ACTIVE}
KEY_OF = {v: k for k, v in SPORTS.items()}
SPREAD = {"americanfootball_nfl", "americanfootball_ncaaf", "basketball_nba", "icehockey_nhl"}
TOTAL = SPREAD | {"baseball_mlb", "soccer_epl", "soccer_uefa_champs_league", "soccer_usa_mls"}
VALID_SIDES = {"spread": {"home", "away"}, "total": {"over", "under"}, "h2h": {"home", "away"}}

# The betting bar, by sport and market, in points (moneyline: win probability).
# NFL sides use the higher bar when the gap between the line and the fair number
# touches 3 or 7. A pick needs at least half the bar to be stamped at all; it is
# a full-bar pick only at the full bar. Only full-bar picks can make a pattern official.
BARS = {
    ("NFL", "spread"): 1.5, ("NFL", "total"): 2.0,
    ("NCAAF", "spread"): 2.5, ("NCAAF", "total"): 3.0,
    ("NBA", "spread"): 2.0, ("NBA", "total"): 3.0,
    ("NHL", "total"): 0.4, ("MLB", "total"): 0.5,
    ("EPL", "total"): 0.3, ("UCL", "total"): 0.3, ("MLS", "total"): 0.3,
}
KEY_BAR = 2.5
H2H_BAR = 0.03
KEY_NUMBERS = (3, 7)


def bar_for(sport, market, home_line=None, fair_home=None):
    if market == "h2h":
        return H2H_BAR
    bar = BARS.get((sport, market), 2.0)
    if sport == "NFL" and market == "spread" and home_line is not None:
        lo, hi = sorted((home_line, fair_home))
        if any(lo <= s * k <= hi for k in KEY_NUMBERS for s in (1, -1)):
            bar = KEY_BAR
    return bar


def api_key():
    value = os.environ.get("ODDS_API_KEY", "").strip()
    if not value:
        raise SystemExit("ODDS_API_KEY is not set")
    return value


def get(path, params):
    params = dict(params)
    params["apiKey"] = api_key()
    url = API + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as response:
        rem, used = response.headers.get("x-requests-remaining"), response.headers.get("x-requests-used")
        if rem is not None:
            CREDITS["remaining"] = int(float(rem))
        if used is not None:
            CREDITS["used"] = int(float(used))
        return json.loads(response.read().decode())


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def missing(value):
    if value is None:
        return True
    text = str(value).strip().lower()
    return text == "" or text.startswith("missing")


def implied(american):
    a = float(american)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def row_id(sport, date, event, market):
    return "|".join((sport, date, event, market))


def blank(sport, date, event, market):
    return {
        "sport": sport, "event": event, "date": date, "market": market,
        "id": row_id(sport, date, event, market),
        "side": "missing", "open": "missing", "openLine": "missing", "openPrice": "missing",
        "openTime": "missing", "openBook": "missing",
        "close": "missing", "closeLine": "missing", "closePrice": "missing",
        "closeTime": "missing", "closeBook": "missing",
        "result": "pending", "clv": "missing", "clvPoints": "missing", "clvCents": "missing",
        "injury": "missing", "weather": "missing", "starter": "missing",
        "bucket": "pass", "lean": "logged", "autopsy": "",
    }


def markets_for(sport_key):
    if sport_key in SPREAD:
        return "spreads,totals"
    if sport_key in TOTAL:
        return "h2h,totals"
    return "h2h"


def book(game, name):
    for item in game.get("bookmakers") or []:
        if item.get("key") == name:
            return {m["key"]: m for m in item.get("markets") or []}
    return {}


def outcome(market, name):
    for item in (market or {}).get("outcomes") or []:
        if item.get("name") == name:
            return item
    return None


def markets_present(game):
    dk = book(game, "draftkings")
    found = []
    if "spreads" in dk:
        found.append("spread")
    if "totals" in dk:
        found.append("total")
    if "h2h" in dk and "spreads" not in dk:
        found.append("h2h")
    return found


def build_snap(game, market, stamp):
    """Both sides of one DraftKings market at one moment, or None if incomplete."""
    dk = book(game, "draftkings")
    mgm = book(game, "betmgm")
    home, away = game["home_team"], game["away_team"]
    if market == "spread":
        h, a = outcome(dk.get("spreads"), home), outcome(dk.get("spreads"), away)
        if not h or not a or h.get("point") is None or h.get("price") is None or a.get("price") is None:
            return None
        snap = {"line": h["point"], "home": h["price"], "away": a["price"]}
        other = outcome(mgm.get("spreads"), home)
        if other and other.get("point") is not None and other["point"] != h["point"]:
            snap["mgmLine"] = other["point"]
    elif market == "total":
        o, u = outcome(dk.get("totals"), "Over"), outcome(dk.get("totals"), "Under")
        if not o or not u or o.get("point") is None or o.get("price") is None or u.get("price") is None:
            return None
        snap = {"line": u["point"], "over": o["price"], "under": u["price"]}
        other = outcome(mgm.get("totals"), "Under")
        if other and other.get("point") is not None and other["point"] != u["point"]:
            snap["mgmLine"] = other["point"]
    else:
        h, a = outcome(dk.get("h2h"), home), outcome(dk.get("h2h"), away)
        if not h or not a or h.get("price") is None or a.get("price") is None:
            return None
        snap = {"home": h["price"], "away": a["price"]}
        d = outcome(dk.get("h2h"), "Draw")
        if d and d.get("price") is not None:
            snap["draw"] = d["price"]
    snap["time"] = stamp
    snap["book"] = "DraftKings"
    return snap


def legacy(row, which, snap):
    """Keep the flat fields the shell already reads."""
    market = row["market"]
    if market == "spread":
        side, line, price = row["home"], snap["line"], snap["home"]
    elif market == "total":
        side, line, price = "under", snap["line"], snap["under"]
    else:
        side, line, price = row["home"], "missing", snap["home"]
    text = f"{side} {line} {price}"
    if which == "open":
        row.update(side=side, open=text, openLine=line, openPrice=price,
                   openTime=snap["time"], openBook="DraftKings")
    else:
        row.update(close=text, closeLine=line, closePrice=price,
                   closeTime=snap["time"], closeBook="DraftKings")


def row_for(rows, index, sport, game, market):
    date = game["commence_time"][:10]
    event = f"{game['away_team']} at {game['home_team']}"
    ident = row_id(sport, date, event, market)
    row = index.get(ident)
    if row is None:
        row = blank(sport, date, event, market)
        rows.append(row)
        index[ident] = row
    row.setdefault("eventId", game.get("id"))
    row["commence"] = game["commence_time"]
    row.setdefault("home", game["home_team"])
    row.setdefault("away", game["away_team"])
    return row


def find_game(data, row):
    for g in data:
        if row.get("eventId") and g.get("id") == row["eventId"]:
            return g
    for g in data:
        if (g.get("home_team") == row.get("home") and g.get("away_team") == row.get("away")
                and g.get("commence_time") == row.get("commence")):
            return g
    return None


def pull():
    ledger = load(LEDGER, {"rows": []})
    rows = ledger.get("rows") or []
    index = {r.get("id"): r for r in rows}
    now_dt = datetime.now(timezone.utc)
    now = iso(now_dt)
    opened = closed = scored = 0

    # 1. Current prices. Started games are skipped, so an in-play line never becomes an open.
    for sport_key, sport in SPORTS.items():
        try:
            games = get(f"/sports/{sport_key}/odds", {
                "regions": "us", "markets": markets_for(sport_key),
                "oddsFormat": "american", "bookmakers": "draftkings,betmgm"})
        except Exception as exc:
            print(sport, "current", exc)
            continue
        for game in games:
            if game["commence_time"] <= now:
                continue
            for market in markets_present(game):
                snap = build_snap(game, market, now)
                if not snap:
                    continue
                row = row_for(rows, index, sport, game, market)
                row["lastSnap"] = snap
                if "openSnap" not in row and missing(row.get("openLine")) and missing(row.get("openPrice")):
                    row["openSnap"] = snap
                    legacy(row, "open", snap)
                    opened += 1

    # 2. Closes, from history, one call per sport and kickoff time.
    floor = iso(now_dt - timedelta(days=7))
    groups = defaultdict(list)
    for row in rows:
        c = row.get("commence")
        if c and "closeSnap" not in row and floor <= c <= now and row.get("sport") in KEY_OF:
            groups[(KEY_OF[row["sport"]], c)].append(row)
    calls = skipped = 0
    read_keys = {KEY_OF[s] for s in READ if s in KEY_OF}
    # READ sports first, so they keep their closes if credits run short.
    order = sorted(groups.items(), key=lambda kv: (kv[0][0] not in read_keys, kv[0][1]))
    for (sport_key, commence), group in order:
        if calls >= MAX_HIST:
            print("history call cap reached; the rest wait for the next run")
            break
        left = CREDITS["remaining"]
        if left is not None and (left < FLOOR or (left < RESERVE and sport_key not in read_keys)):
            skipped += 1
            continue
        calls += 1
        try:
            resp = get(f"/historical/sports/{sport_key}/odds", {
                "regions": "us", "markets": markets_for(sport_key), "oddsFormat": "american",
                "bookmakers": "draftkings,betmgm", "date": iso(parse(commence) - timedelta(seconds=60))})
        except Exception as exc:
            print(sport_key, "close", commence, exc)
            continue
        stamp = resp.get("timestamp") or commence
        for row in group:
            game = find_game(resp.get("data") or [], row)
            if not game:
                continue
            snap = build_snap(game, row["market"], stamp)
            if not snap:
                continue
            row["closeSnap"] = snap
            row["closeGapMin"] = round((parse(commence) - parse(stamp)).total_seconds() / 60, 1)
            legacy(row, "close", snap)
            closed += 1

    # 3. Final scores, completed games only.
    need = defaultdict(list)
    for row in rows:
        c = row.get("commence")
        if c and not row.get("final") and iso(now_dt - timedelta(days=3)) <= c <= now and row.get("sport") in KEY_OF:
            need[KEY_OF[row["sport"]]].append(row)
    for sport_key, group in need.items():
        try:
            data = get(f"/sports/{sport_key}/scores", {"daysFrom": 3})
        except Exception as exc:
            print(sport_key, "scores", exc)
            continue
        done = [g for g in data if g.get("completed")]
        for row in group:
            game = find_game(done, row)
            if not game:
                continue
            try:
                by = {s["name"]: float(s["score"]) for s in game.get("scores") or []}
                h, a = by[row["home"]], by[row["away"]]
            except (KeyError, TypeError, ValueError):
                continue
            row["score"] = {"home": h, "away": a}
            row["final"] = True
            row["result"] = f"{row['away']} {a:g}, {row['home']} {h:g}"
            scored += 1

    ledger["rows"] = rows
    ledger["asOfCt"] = now
    ledger["feed"] = "Odds API. DraftKings is the print. BetMGM line noted when it differs. Key is not in this file."
    save(LEDGER, ledger)
    ledger["credits"] = dict(CREDITS)
    save(LEDGER, ledger)
    print(json.dumps({"opened": opened, "closed": closed, "scored": scored, "rows": len(rows),
                      "historyCalls": calls, "closesSkippedForCredits": skipped,
                      "creditsRemaining": CREDITS["remaining"]}))


def make_pick(a):
    def fail(msg):
        sys.exit("PICK REJECTED: " + msg)

    ledger = load(LEDGER, {"rows": []})
    row = next((r for r in ledger.get("rows") or [] if r.get("id") == a.id), None)
    if not row:
        fail("no row with that id")
    if row.get("sport") not in READ:
        fail(f"{row.get('sport')} is collected for data only. Picks are open for {', '.join(READ)}.")
    snap = row.get("lastSnap")
    if not snap:
        fail("row has no stored price. Run pull.py first.")
    now_dt = datetime.now(timezone.utc)
    now = iso(now_dt)
    if not row.get("commence") or row["commence"] <= now:
        fail("game has started or has no start time")
    age = (now_dt - parse(snap["time"])).total_seconds() / 60
    if age > STALE_MIN:
        fail(f"stored price is {age:.0f} minutes old. Run pull.py first.")
    market = row["market"]
    if a.side not in VALID_SIDES[market]:
        fail(f"side must be one of {sorted(VALID_SIDES[market])} for {market}")
    for name in ("reason", "falsifier", "pattern"):
        if not (getattr(a, name) or "").strip():
            fail(f"--{name} is required")
    try:
        proj = float(a.projection)
    except ValueError:
        fail("projection must be a number")
    if market == "h2h" and not 0 < proj < 1:
        fail("for moneyline, projection is your win probability for the side picked, between 0 and 1")

    price = snap[a.side]
    if market == "spread":
        # projection is the fair HOME line: -4.5 means home by 4.5
        line = snap["line"] if a.side == "home" else -snap["line"]
        edge = snap["line"] - proj if a.side == "home" else proj - snap["line"]
        unit = "points"
    elif market == "total":
        line = snap["line"]
        edge = proj - line if a.side == "over" else line - proj
        unit = "points"
    else:
        line = None
        edge = proj - implied(price)
        unit = "prob"
    if edge <= 0:
        fail(f"your projection gives this side no edge ({edge:+.2f} {unit}). Pick the other side or pass.")
    bar = bar_for(row["sport"], market, snap.get("line"), proj if market == "spread" else None)
    if edge < bar / 2:
        fail(f"edge {edge:.2f} {unit} is under half the bar ({bar / 2:.2f}). Pass.")
    full_bar = edge >= bar

    status = next((p.get("status") for p in ledger.get("patterns") or [] if p.get("id") == a.pattern), "shadow")
    if status == "retire":
        fail("that pattern is retired. A new idea needs a new pattern name.")
    tier = "official" if status == "official" and full_bar else "shadow"
    stake = min(float(a.stake), 1.0) if tier == "official" else 0.0

    picks = load(PICKS, {"picks": []})
    pick_id = f"{row['id']}|{a.side}|{VERSION}"
    if any(p.get("pickId") == pick_id for p in picks["picks"]):
        fail("this pick already exists. Picks are never edited.")
    picks["picks"].append({
        "pickId": pick_id, "rowId": row["id"], "sport": row["sport"], "event": row["event"],
        "market": market, "side": a.side, "lineAtPick": line, "priceAtPick": price,
        "marketNumber": snap.get("line"), "priceTime": snap["time"], "pickedAt": now,
        "projection": proj, "edge": round(edge, 3), "edgeUnit": unit,
        "bar": bar, "fullBar": full_bar,
        "confidence": a.confidence, "pattern": a.pattern, "reason": a.reason.strip(),
        "falsifier": a.falsifier.strip(), "modelVersion": VERSION, "tier": tier,
        "stakeUnits": stake,
    })
    save(PICKS, picks)
    print(json.dumps({"stamped": pick_id, "line": line, "price": price, "edge": round(edge, 3),
                      "unit": unit, "bar": bar, "fullBar": full_bar, "tier": tier, "stakeUnits": stake}))


def main():
    ap = argparse.ArgumentParser(description="EDGE price puller and pick stamper")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("pull")
    p = sub.add_parser("pick")
    p.add_argument("--id", required=True, help="row id: sport|date|event|market")
    p.add_argument("--side", required=True, help="home/away for spread and moneyline, over/under for total")
    p.add_argument("--projection", required=True,
                   help="spread: fair HOME line (-4.5 = home by 4.5). total: fair total. moneyline: win prob of the side picked")
    p.add_argument("--confidence", required=True, choices=["low", "medium", "high"])
    p.add_argument("--pattern", required=True, help="pattern name, defined in patterns.md")
    p.add_argument("--reason", required=True)
    p.add_argument("--falsifier", required=True, help="what fact or result would prove this read wrong")
    p.add_argument("--stake", default="0.5", help="units; used only when the pattern is official; capped at 1")
    args = ap.parse_args()
    if args.cmd == "pick":
        make_pick(args)
    else:
        pull()


if __name__ == "__main__":
    main()
