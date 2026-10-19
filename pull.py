#!/usr/bin/env python3
"""EDGE price puller, read stamper and pick stamper. Last changed 2026-10-19; history in changelog.md.
(Was labeled v3, the 2026-10 read-stamper rewrite. EDGE_MODEL_VERSION, stamped on every pick as modelVersion,
stays v1 on purpose: it is part of every pickId, and changing it would let a duplicate pick through.)

  python pull.py            pull prices, closes and scores. This is what the jobs run.
  python pull.py read ...   stamp a read: fair number vs the stored market number, the lean,
                            and an A/B/C grade set by the edge against the bar. Every game read gets one.
  python pull.py pick ...   older pick stamper. Reads replace it. The model never types a price.

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
    "soccer_spain_la_liga": "LaLiga",
    "soccer_italy_serie_a": "SerieA",
    "soccer_germany_bundesliga": "Bundesliga",
    "soccer_france_ligue_one": "Ligue1",
    "soccer_uefa_europa_league": "UEL",
    "mma_mixed_martial_arts": "UFC",
}
# Only sports the desk actually reads are pulled. Each sport costs Odds API credits,
# and history calls for closes cost the most. Add a sport here when it gets real reads.
# EDGE_SPORTS overrides this, e.g. EDGE_SPORTS=NFL,NCAAF
ACTIVE = ["NFL", "NCAAF", "NBA", "NHL", "EPL", "UCL", "LaLiga", "SerieA", "Bundesliga", "Ligue1", "UEL", "MLS",
          "ATP", "WTA"]   # prices collected
READ = ["NFL"]                                          # sports the analyst reads and picks
_env = [s.strip().upper() for s in os.environ.get("EDGE_SPORTS", "").split(",") if s.strip()]
ACTIVE = _env or ACTIVE
# Credit guard. The Odds API reports credits left on every response.
# Under RESERVE, closes are looked up only for READ sports. Under FLOOR, no close lookups at all.
RESERVE = int(os.environ.get("EDGE_CREDIT_RESERVE", "3000"))
# Fast runs (every 15 minutes, games in the next 3 hours) stop earlier, so they never eat the credits that full
# runs and closes need.
# 2026-10-19: 6000 -> 1500. Fast runs cost ~6 credits and, since then, also supply the free closes (step 2a),
# so stopping them early would cost more in history calls than it saves.
FAST_RESERVE = int(os.environ.get("EDGE_FAST_RESERVE", "1500"))
FLOOR = int(os.environ.get("EDGE_CREDIT_FLOOR", "300"))
# A stored snap this many minutes or less before the start counts as the close (no history call).
CLOSE_SNAP_MIN = float(os.environ.get("EDGE_CLOSE_SNAP_MIN", "15"))
CREDITS = {"remaining": None, "used": None}
SPORTS = {k: v for k, v in SPORTS.items() if v in ACTIVE}
KEY_OF = {v: k for k, v in SPORTS.items()}
# Tennis is listed by tournament (a new Odds API key each week). discover() adds the active ones each run;
# the /sports listing costs no credits. Each row keeps its own sportKey, so closes and scores find it later.
TENNIS = {"ATP": "tennis_atp_", "WTA": "tennis_wta_"}


def discover():
    want = {pre: name for name, pre in TENNIS.items() if name in ACTIVE}
    if not want:
        return []
    try:
        listing = get("/sports", {})
    except Exception as exc:  # noqa: BLE001
        print("tennis discovery", exc)
        return []
    found = []
    for s in listing:
        for pre, name in want.items():
            if s.get("key", "").startswith(pre) and s.get("active") and not s.get("has_outrights"):
                SPORTS[s["key"]] = name
                found.append(s["key"])
    return found


def key_of(row):
    return row.get("sportKey") or KEY_OF.get(row.get("sport"))
# Books requested on every price call. Up to 10 books bill as one region, so adding books here
# costs no extra credits. DraftKings stays the print; the others feed the sharp-vs-soft scan.
BOOKS = os.environ.get("EDGE_BOOKS", "draftkings,betmgm,fanduel,williamhill_us,pinnacle")
BOOK_NAMES = {"draftkings": "DraftKings", "betmgm": "BetMGM", "fanduel": "FanDuel",
              "williamhill_us": "Caesars", "pinnacle": "Pinnacle"}
SPREAD = {"americanfootball_nfl", "americanfootball_ncaaf", "basketball_nba"}
# Hockey's main market is the moneyline; the puck line is almost always 1.5.
TOTAL = SPREAD | {"icehockey_nhl", "baseball_mlb", "soccer_epl", "soccer_uefa_champs_league", "soccer_usa_mls",
                  "soccer_spain_la_liga", "soccer_italy_serie_a", "soccer_germany_bundesliga", "soccer_france_ligue_one", "soccer_uefa_europa_league"}
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
    ("LaLiga", "total"): 0.3, ("SerieA", "total"): 0.3, ("Bundesliga", "total"): 0.3, ("Ligue1", "total"): 0.3, ("UEL", "total"): 0.3,
}
KEY_BAR = 2.5
# Goal and run totals are priced mostly through the odds (5.5 at -135), so for these sports
# a total pick's projection is the fair probability of the OVER and the edge is in probability.
SOCCER = {"EPL", "UCL", "MLS", "LaLiga", "SerieA", "Bundesliga", "Ligue1", "UEL"}
PROB_TOTALS = {"NHL", "MLB"} | SOCCER
H2H_BAR = 0.03
KEY_NUMBERS = (3, 7)


def pin_at_pick(snap, side):
    """Pinnacle's price in the snapshot a read is priced from: line, prices, its own update time, and the no-vig
    probability of the picked side. Stored on every read (2026-10-19) so the sharp gap at the pick can be studied.
    None when the snapshot has no Pinnacle price. Never used to price or grade the read."""
    pin = (snap or {}).get("books", {}).get("pinnacle")
    if not pin:
        return None
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in pin]
    out = {"line": pin.get("line"), "prices": {k: pin[k] for k in keys}, "updated": pin.get("updated"),
           "snapTime": snap.get("time")}
    if side in keys and len(keys) >= 2:
        try:
            import fair as fairlib
            out["noVig"] = round(fairlib.probs({k: pin[k] for k in keys})[side], 4)
        except Exception:  # noqa: BLE001
            pass
    return out


def context_at_pick(row):
    """The row's news context as it stood when a read was stamped: weather forecast, injury text, goalie signal.
    These row fields keep being refreshed until kickoff, so only this copy is safe to use as a pre-pick feature
    (2026-10-19). Never used to price or grade the read."""
    out = {}
    if row.get("weatherData"):
        out["weather"] = row["weatherData"]
    if row.get("injury") not in (None, "", "missing"):
        out["injury"] = row["injury"]
    if row.get("goalieSig"):
        out["goalie"] = row["goalieSig"]
    return out or None


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
        return "spreads,totals,h2h"     # h2h prices Kalshi winner markets; +1 credit per current call
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


PRINT_ORDER = ["draftkings", "fanduel", "betmgm", "williamhill_us", "pinnacle"]


def markets_present(game):
    """Markets any requested book prices (DraftKings posts no soccer totals, for one)."""
    keys = {m["key"] for item in game.get("bookmakers") or [] for m in item.get("markets") or []}
    return [name for key, name in (("spreads", "spread"), ("totals", "total"), ("h2h", "h2h")) if key in keys]


def print_snap(index, sport, game, market, stamp):
    """The row's print book: DraftKings when it prices the market, else the next book in PRINT_ORDER. A row keeps
    the book it opened with, so its open, close and picks all compare the same book."""
    ident = row_id(sport, game["commence_time"][:10], f"{game['away_team']} at {game['home_team']}", market)
    fixed = (index.get(ident) or {}).get("printBook")
    for bk in ([fixed] if fixed else PRINT_ORDER):
        snap = build_snap(game, market, stamp, bk)
        if snap:
            return snap, bk
    return None, None


def build_snap(game, market, stamp, bk="draftkings"):
    """Both sides of one market at one book at one moment, or None if incomplete.
    The default book is DraftKings, the print. Other books are stored under snap["books"]."""
    dk = book(game, bk)
    mgm = book(game, "betmgm") if bk == "draftkings" else {}
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
    snap["book"] = BOOK_NAMES.get(bk, bk)
    return snap


def books_for(game, market, stamp):
    """Every requested book's prices for one market, keyed by book. Each carries the book's own
    last update time, so a stale sharp price can be skipped."""
    out = {}
    for item in game.get("bookmakers") or []:
        key = item.get("key")
        snap = build_snap(game, market, stamp, key)
        if snap:
            snap.pop("time", None)
            snap["updated"] = item.get("last_update")
            out[key] = snap
    return out


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
                   openTime=snap["time"], openBook=snap.get("book", "DraftKings"))
    else:
        row.update(close=text, closeLine=line, closePrice=price,
                   closeTime=snap["time"], closeBook=snap.get("book", "DraftKings"))


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
    if game.get("sport_key"):
        row.setdefault("sportKey", game["sport_key"])
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


def near_sports(rows, now_dt, hours):
    """Sport keys with a game starting in the next `hours`, read from the ledger, so no credits are spent finding them."""
    lo, hi = iso(now_dt), iso(now_dt + timedelta(hours=hours))
    return {key_of(r) for r in rows if key_of(r) in SPORTS and r.get("commence") and lo < r["commence"] <= hi}


def pull(near=None):
    """Full pull: prices, closes and scores. near=N: current prices only, and only for sports with a
    game starting in the next N hours. Near runs feed the sharp-soft scan between the full runs."""
    ledger = load(LEDGER, {"rows": []})
    rows = ledger.get("rows") or []
    index = {r.get("id"): r for r in rows}
    now_dt = datetime.now(timezone.utc)
    now = iso(now_dt)
    opened = closed = scored = 0
    discover()
    keys = SPORTS
    if near:
        last = (ledger.get("credits") or {}).get("remaining")
        reserve = FAST_RESERVE if os.environ.get("EDGE_FAST") else RESERVE
        if last is not None and last < reserve:
            print(json.dumps({"near": near, "skipped": f"credits {last} under reserve {reserve}"}))
            return
        wanted = near_sports(rows, now_dt, near)
        keys = {k: v for k, v in SPORTS.items() if k in wanted}
        if not keys:
            print(json.dumps({"near": near, "sports": [], "note": "no games starting soon"}))
            return

    # 1. Current prices. Started games are skipped, so an in-play line never becomes an open.
    for sport_key, sport in keys.items():
        try:
            games = get(f"/sports/{sport_key}/odds", {
                "regions": "us", "markets": markets_for(sport_key),
                "oddsFormat": "american", "bookmakers": BOOKS})
        except Exception as exc:
            print(sport, "current", exc)
            continue
        for game in games:
            if game["commence_time"] <= now:
                continue
            for market in markets_present(game):
                snap, bk = print_snap(index, sport, game, market, now)
                if not snap:
                    continue
                snap["books"] = books_for(game, market, now)
                row = row_for(rows, index, sport, game, market)
                row.setdefault("printBook", bk)
                row["lastSnap"] = snap
                if "openSnap" not in row and missing(row.get("openLine")) and missing(row.get("openPrice")):
                    row["openSnap"] = snap
                    legacy(row, "open", snap)
                    opened += 1

    if near:
        ledger["rows"] = rows
        ledger["asOfCt"] = now
        if CREDITS["remaining"] is not None:
            ledger["credits"] = dict(CREDITS)
        save(LEDGER, ledger)
        print(json.dumps({"near": near, "sports": sorted(keys.values()), "opened": opened,
                          "creditsRemaining": CREDITS["remaining"]}))
        return

    # 2a. Free closes (2026-10-19). Fast runs price every game in its last 3 hours, so a started game's last stored
    # snap is usually minutes before kickoff. Checked on 98 rows that had both: same line on 92, median price
    # difference 0, 94% within 5 cents. A snap that close to the start is the close; no history call is paid.
    free = 0
    for row in rows:
        c, last = row.get("commence"), row.get("lastSnap")
        if not c or c > now or "closeSnap" in row or not last or not last.get("time"):
            continue
        gap = (parse(c) - parse(last["time"])).total_seconds() / 60
        if 0 <= gap <= CLOSE_SNAP_MIN:
            row["closeSnap"] = dict(last)
            row["closeGapMin"] = round(gap, 1)
            row["closeSource"] = "lastSnap"
            legacy(row, "close", row["closeSnap"])
            closed += 1
            free += 1

    # 2b. Closes, from history, one call per sport and kickoff time.
    floor = iso(now_dt - timedelta(days=7))
    groups = defaultdict(list)
    for row in rows:
        c = row.get("commence")
        if c and "closeSnap" not in row and floor <= c <= now and key_of(row):
            # A row whose market is no longer pulled (old NHL puck lines) can never close. Skip it.
            pulled = {{"spreads": "spread", "totals": "total"}.get(m, m) for m in markets_for(key_of(row)).split(",")}
            if row.get("market") not in pulled:
                continue
            # Two history calls that came back without this game mean it never will. Stop paying for it.
            if row.get("closeTries", 0) >= 2:
                continue
            groups[(key_of(row), c)].append(row)
    calls = skipped = 0
    # Closes are only used to grade picks and leans (CLV), and each history call costs 10 credits per market,
    # so they are fetched only for rows that carry a pick or a lean (since 2026-10-14; before, every row).
    picked = {p.get("rowId") for p in load(PICKS, {"picks": []}).get("picks") or [] if p.get("kind") in ("pick", "lean")}
    for key in list(groups):
        groups[key] = [r for r in groups[key] if r.get("id") in picked]
        if not groups[key]:
            del groups[key]
    read_keys = {KEY_OF[s] for s in READ if s in KEY_OF}
    # READ sports first, so they keep their closes if credits run short.
    order = sorted(groups.items(), key=lambda kv: (kv[0][0] not in read_keys, kv[0][1]))
    for (sport_key, commence), group in order:
        if calls >= MAX_HIST:
            print("history call cap reached; the rest wait for the next run")
            break
        left = CREDITS["remaining"]
        if left is not None and left < FLOOR:
            skipped += 1
            continue
        calls += 1
        try:
            need = {r.get("market") for r in group}
            mk = ",".join(m for m in markets_for(sport_key).split(",")
                          if {"spreads": "spread", "totals": "total"}.get(m, m) in need)
            resp = get(f"/historical/sports/{sport_key}/odds", {
                "regions": "us", "markets": mk, "oddsFormat": "american",
                "bookmakers": BOOKS, "date": iso(parse(commence) - timedelta(seconds=60))})
        except Exception as exc:
            print(sport_key, "close", commence, exc)
            continue
        stamp = resp.get("timestamp") or commence
        for row in group:
            game = find_game(resp.get("data") or [], row)
            snap = build_snap(game, row["market"], stamp, row.get("printBook") or "draftkings") if game else None
            if not snap:
                row["closeTries"] = row.get("closeTries", 0) + 1
                continue
            snap["books"] = books_for(game, row["market"], stamp)
            row["closeSnap"] = snap
            row["closeGapMin"] = round((parse(commence) - parse(stamp)).total_seconds() / 60, 1)
            legacy(row, "close", snap)
            closed += 1

    # 3. Final scores, completed games only.
    need = defaultdict(list)
    for row in rows:
        c = row.get("commence")
        if c and not row.get("final") and iso(now_dt - timedelta(days=3)) <= c <= now and key_of(row):
            need[key_of(row)].append(row)
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
    ledger["feed"] = "Odds API. DraftKings is the print. BetMGM line noted when it differs. FanDuel, Caesars and Pinnacle stored under books for the sharp-soft scan. Key is not in this file."
    ledger["credits"] = dict(CREDITS)
    save(LEDGER, ledger)
    print(json.dumps({"opened": opened, "closed": closed, "scored": scored, "rows": len(rows),
                      "historyCalls": calls, "freeCloses": free, "closesSkippedForCredits": skipped,
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
    prob_total = market == "total" and row["sport"] in PROB_TOTALS
    if market == "h2h" and not 0 < proj < 1:
        fail("for moneyline, projection is your win probability for the side picked, between 0 and 1")
    if prob_total and not 0 < proj < 1:
        fail(f"for {row['sport']} totals, projection is the fair probability of the OVER, between 0 and 1")

    price = snap[a.side]
    if market == "spread":
        # projection is the fair HOME line: -4.5 means home by 4.5
        line = snap["line"] if a.side == "home" else -snap["line"]
        edge = snap["line"] - proj if a.side == "home" else proj - snap["line"]
        unit = "points"
    elif prob_total:
        line = snap["line"]
        edge = (proj if a.side == "over" else 1 - proj) - implied(price)
        unit = "prob"
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
    bar = H2H_BAR if prob_total else bar_for(row["sport"], market, snap.get("line"), proj if market == "spread" else None)
    if edge < bar / 2:
        d = 3 if unit == "prob" else 2
        fail(f"edge {edge:.{d}f} {unit} is under half the bar ({bar / 2:.{d}f}). Pass.")
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
        "stakeUnits": stake, "kind": "pick", "grade": grade_for(edge, bar, a.confidence),
        "commence": row.get("commence"), "pinAtPick": pin_at_pick(snap, a.side),
        "contextAtPick": context_at_pick(row),
    })
    save(PICKS, picks)
    print(json.dumps({"stamped": pick_id, "line": line, "price": price, "edge": round(edge, 3),
                      "unit": unit, "bar": bar, "fullBar": full_bar, "tier": tier, "stakeUnits": stake}))

GRADES = "ABC"


def side_edge(row, snap, market, side, proj):
    """Line, price, edge and unit for one side, given the read's fair number.
    spread: proj is the fair HOME line. total: fair total (prob totals: fair P(over)).
    moneyline (read only): fair HOME win probability."""
    price = snap[side]
    prob_total = market == "total" and row["sport"] in PROB_TOTALS
    if market == "spread":
        line = snap["line"] if side == "home" else -snap["line"]
        edge = snap["line"] - proj if side == "home" else proj - snap["line"]
        return line, price, edge, "points"
    if prob_total:
        p = proj if side == "over" else 1 - proj
        return snap["line"], price, p - implied(price), "prob"
    if market == "total":
        return snap["line"], price, (proj - snap["line"] if side == "over" else snap["line"] - proj), "points"
    p = proj if side == "home" else 1 - proj
    return None, price, p - implied(price), "prob"


def grade_for(edge, bar, confidence):
    if edge <= 0:
        return "P"
    g = "A" if edge >= bar else "B" if edge >= bar / 2 else "C"
    if confidence == "low" and g != "C":
        g = GRADES[GRADES.index(g) + 1]
    return g


LEAN_CAP = set()   # (row id, pattern) pairs whose read may be at most a lean: expected move under the pattern's minimum


def make_read(a):
    """Stamp a read on one market: the fair number, the market number, the lean, and an A/B/C grade.
    The grade comes from the edge against the bar, never from the analyst:
      A  edge at or above the full bar        a shadow pick (official only if its pattern is official)
      B  edge from half the bar to the bar    a shadow pick
      C  edge under half the bar              a lean: graded against the close, never a pick
      P  no edge on either side               a pass, logged with its fair number
    Low confidence drops A to B and B to C. Every read with a side is graded on CLV."""
    def fail(msg):
        sys.exit("READ REJECTED: " + msg)

    ledger = load(LEDGER, {"rows": []})
    row = next((r for r in ledger.get("rows") or [] if r.get("id") == a.id), None)
    if not row:
        fail("no row with that id")
    if row.get("sport") not in READ:
        fail(f"{row.get('sport')} is collected for data only. Reads are open for {', '.join(READ)}.")
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
    if not (a.reason or "").strip():
        fail("--reason is required: the news items and what each is worth")
    try:
        fair = float(a.fair)
    except ValueError:
        fail("fair must be a number")
    market = row["market"]
    prob_total = market == "total" and row["sport"] in PROB_TOTALS
    if (market == "h2h" or prob_total) and not 0 < fair < 1:
        fail("for this market, fair is a probability between 0 and 1 (moneyline: HOME win; prob totals: OVER)")

    sides = sorted(VALID_SIDES[market])
    best = max(((s,) + side_edge(row, snap, market, s, fair) for s in sides), key=lambda t: t[3])
    side, line, price, edge, unit = best
    bar = H2H_BAR if (prob_total or market == "h2h") else bar_for(
        row["sport"], market, snap.get("line"), fair if market == "spread" else None)
    if edge > 4 * bar and not getattr(a, "big", False):
        home = row["event"].split(" at ")[-1]
        shown = f"{home} {snap['line']:+g}" if market == "spread" else f"{snap.get('line')}"
        fail(f"edge {edge:.2f} {unit} is over 4x the bar. The market is {shown}. For spreads, --fair is the HOME line "
             f"in the same sign as the market ({home} -3 means {home} favored by 3). If the number is right, add --big.")
    grade = grade_for(edge, bar, a.confidence)
    if (a.id, (a.pattern or "").strip()) in LEAN_CAP and grade in ("A", "B"):
        grade = "C"                          # expected move under the pattern's minimum: lean only

    picks = load(PICKS, {"picks": []})
    kind = {"A": "pick", "B": "pick", "C": "lean", "P": "pass"}[grade]
    tier, stake, note = None, 0.0, None
    if kind == "pick":
        for name in ("falsifier", "pattern"):
            if not (getattr(a, name) or "").strip():
                fail(f"this read grades {grade}, a pick. --{name} is required.")
        status = next((p.get("status") for p in ledger.get("patterns") or [] if p.get("id") == a.pattern), "shadow")
        if status == "retire":
            fail("that pattern is retired. A new idea needs a new pattern name.")
        tier = "official" if status == "official" and grade == "A" else "shadow"
        stake = min(float(a.stake), 1.0) if tier == "official" else 0.0
        # One pick per row, side and pattern. Different patterns are separate tests and never block each other.
        pick_id = f"{row['id']}|{side}|{VERSION}|{a.pattern.strip()}"
        if any(p.get("pickId") == pick_id for p in picks["picks"]):
            kind, tier, stake = "reread", None, 0.0
            note = "Same side already picked. Logged as a reread, graded, not counted."
    if kind == "lean":
        # One test entry per row, side and pattern (2026-10-19). A news feed that flickers used to stamp the same
        # lean a dozen times (Patriots at Bears spread: 13 rows), which inflated every pattern's n and t.
        # A repeat is still logged, as a reread: graded, never counted.
        pat = (a.pattern or "").strip() or None
        if any(p.get("rowId") == row["id"] and p.get("side") == side and p.get("pattern") == pat
               and p.get("kind") in ("pick", "lean") for p in picks["picks"]):
            kind = "reread"
            note = "Same side already read for this pattern. Logged as a reread, graded, not counted."
    if kind != "pick":
        pick_id = f"{row['id']}|{side if grade != 'P' else 'none'}|{VERSION}|{kind}|{(a.pattern or '').strip() or 'none'}|{now}"

    entry = {
        "pickId": pick_id, "kind": kind, "grade": grade, "rowId": row["id"], "sport": row["sport"],
        "event": row["event"], "commence": row.get("commence"), "market": market,
        "side": side if grade != "P" else None, "lineAtPick": line if grade != "P" else None,
        "priceAtPick": price if grade != "P" else None, "marketNumber": snap.get("line"),
        "marketPrices": {k: snap[k] for k in ("home", "away", "over", "under", "draw") if k in snap},
        "priceTime": snap["time"], "pickedAt": now, "fair": fair, "projection": fair,
        "edge": round(edge, 3), "edgeUnit": unit, "bar": bar, "fullBar": edge >= bar,
        "confidence": a.confidence, "pattern": (a.pattern or "").strip() or None,
        "reason": a.reason.strip(), "falsifier": (a.falsifier or "").strip() or None,
        "modelVersion": VERSION, "tier": tier, "stakeUnits": stake, "by": getattr(a, "by", "claude") or "claude",
        "pinAtPick": pin_at_pick(snap, side if grade != "P" else None), "contextAtPick": context_at_pick(row),
    }
    if note:
        entry["note"] = note
    picks["picks"].append(entry)
    save(PICKS, picks)
    home = row["event"].split(" at ")[-1]
    print(json.dumps({"read": pick_id, "grade": grade, "home": home, "kind": kind, "market": snap.get("line"),
                      "fair": fair, "side": entry["side"], "edge": round(edge, 3), "unit": unit,
                      "bar": bar, "tier": tier, "stakeUnits": stake}))


def main():
    ap = argparse.ArgumentParser(description="EDGE price puller and pick stamper")
    sub = ap.add_subparsers(dest="cmd")
    pp = sub.add_parser("pull")
    pp.add_argument("--near", type=float, default=None,
                    help="prices only, for sports with a game starting within this many hours")
    p = sub.add_parser("pick")
    p.add_argument("--id", required=True, help="row id: sport|date|event|market")
    p.add_argument("--side", required=True, help="home/away for spread and moneyline, over/under for total")
    p.add_argument("--projection", required=True,
                   help="spread: fair HOME line (-4.5 = home by 4.5). total: fair total (NHL, soccer, MLB: fair probability of the OVER). moneyline: win prob of the side picked")
    p.add_argument("--confidence", required=True, choices=["low", "medium", "high"])
    p.add_argument("--pattern", required=True, help="pattern name, defined in patterns.md")
    p.add_argument("--reason", required=True)
    p.add_argument("--falsifier", required=True, help="what fact or result would prove this read wrong")
    p.add_argument("--stake", default="0.5", help="units; used only when the pattern is official; capped at 1")
    r = sub.add_parser("read")
    r.add_argument("--id", required=True, help="row id: sport|date|event|market")
    r.add_argument("--fair", required=True,
                   help="spread: fair HOME line (-4.5 = home by 4.5). total: fair total (NHL, soccer, MLB: fair probability of the OVER). moneyline: fair HOME win probability")
    r.add_argument("--confidence", required=True, choices=["low", "medium", "high"])
    r.add_argument("--reason", required=True, help="each news item, its point value and direction")
    r.add_argument("--falsifier", default="", help="required when the read grades A or B")
    r.add_argument("--pattern", default="", help="required when the read grades A or B")
    r.add_argument("--stake", default="0.5", help="units; used only for an A on an official pattern; capped at 1")
    r.add_argument("--big", action="store_true", help="confirm an edge over 4x the bar is not a sign error")
    r.add_argument("--by", default="claude", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.cmd == "read":
        make_read(args)
    elif args.cmd == "pick":
        make_pick(args)
    elif args.cmd == "pull":
        pull(args.near)
    else:
        pull()


if __name__ == "__main__":
    main()
