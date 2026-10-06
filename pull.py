#!/usr/bin/env python3
"""Pull open and close from The Odds API. The model does not type the number.

DraftKings is the print. BetMGM is written when it differs.
First print writes the open and is never overwritten.
The close is the last DraftKings snapshot at or before start.
The key is ODDS_API_KEY. It is not written to a file.
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger" / "ledger.json"
API = "https://api.the-odds-api.com/v4"

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
SPREAD = {"americanfootball_nfl", "americanfootball_ncaaf", "basketball_nba", "icehockey_nhl"}
TOTAL = SPREAD | {"baseball_mlb", "soccer_epl", "soccer_uefa_champs_league", "soccer_usa_mls"}


def key():
    value = os.environ.get("ODDS_API_KEY", "").strip()
    if not value:
        raise SystemExit("ODDS_API_KEY is not set")
    return value


def get(path, params):
    params = dict(params)
    params["apiKey"] = key()
    url = API + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read().decode())


def missing(value):
    if value is None:
        return True
    text = str(value).strip().lower()
    return text == "" or text.startswith("missing")


def row_id(sport, date, event, market):
    return "|".join((sport, date, event, market))


def blank(sport, date, event, market):
    return {
        "sport": sport,
        "event": event,
        "date": date,
        "market": market,
        "id": row_id(sport, date, event, market),
        "side": "missing",
        "open": "missing",
        "openLine": "missing",
        "openPrice": "missing",
        "openTime": "missing",
        "openBook": "missing",
        "close": "missing",
        "closeLine": "missing",
        "closePrice": "missing",
        "closeTime": "missing",
        "closeBook": "missing",
        "result": "pending",
        "clv": "missing",
        "clvPoints": "missing",
        "clvCents": "missing",
        "injury": "missing",
        "weather": "missing",
        "starter": "missing",
        "bucket": "pass",
        "lean": "logged",
        "autopsy": "",
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
            return {market["key"]: market for market in item.get("markets") or []}
    return {}


def outcome(market, name):
    for item in (market or {}).get("outcomes") or []:
        if item.get("name") == name:
            return item
    return None


def prints(game):
    dk = book(game, "draftkings")
    mgm = book(game, "betmgm")
    found = []
    if "spreads" in dk:
        home = outcome(dk["spreads"], game["home_team"])
        if home and home.get("point") is not None:
            other = outcome(mgm.get("spreads"), game["home_team"])
            found.append(("spread", game["home_team"], home, other))
    if "totals" in dk:
        under = outcome(dk["totals"], "Under")
        if under and under.get("point") is not None:
            other = outcome(mgm.get("totals"), "Under")
            found.append(("total", "under", under, other))
    if "h2h" in dk and "spreads" not in dk:
        home = outcome(dk["h2h"], game["home_team"])
        if home and home.get("price") is not None:
            other = outcome(mgm.get("h2h"), game["home_team"])
            found.append(("h2h", game["home_team"], home, other))
    return found


def note(other, point):
    if not other or other.get("point") == point or other.get("price") == point:
        return ""
    value = other.get("point", other.get("price"))
    return f" BetMGM {value}."


def upsert(rows, index, sport, game, market, side, price, stamp, field):
    date = game["commence_time"][:10]
    event = f"{game['away_team']} at {game['home_team']}"
    ident = row_id(sport, date, event, market)
    row = index.get(ident)
    if row is None:
        row = blank(sport, date, event, market)
        rows.append(row)
        index[ident] = row
    line = price.get("point", "missing")
    american = price.get("price", "missing")
    text = f"{side} {line} {american}"
    if field == "open" and missing(row.get("openLine")) and missing(row.get("openPrice")):
        row["side"] = side
        row["open"] = text
        row["openLine"] = line
        row["openPrice"] = american
        row["openTime"] = stamp
        row["openBook"] = "DraftKings"
    if field == "close" and missing(row.get("closeLine")):
        row["close"] = text
        row["closeLine"] = line
        row["closePrice"] = american
        row["closeTime"] = stamp
        row["closeBook"] = "DraftKings"
    return row


def main():
    ledger = json.loads(LEDGER.read_text())
    rows = ledger.get("rows") or []
    index = {row.get("id"): row for row in rows}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opened = closed = 0
    for sport_key, sport in SPORTS.items():
        try:
            games = get(
                f"/sports/{sport_key}/odds",
                {
                    "regions": "us",
                    "markets": markets_for(sport_key),
                    "oddsFormat": "american",
                    "bookmakers": "draftkings,betmgm",
                },
            )
        except Exception as exc:
            print(sport, "current", exc)
            continue
        for game in games:
            for market, side, price, other in prints(game):
                row = upsert(rows, index, sport, game, market, side, price, now, "open")
                if row.get("openBook") == "DraftKings" and row.get("openTime") == now:
                    opened += 1
                row["autopsy"] = (row.get("autopsy") or "").split(" BetMGM")[0] + note(other, price.get("point"))
            if game["commence_time"] > now:
                continue
            try:
                snap = get(
                    f"/historical/sports/{sport_key}/odds",
                    {
                        "regions": "us",
                        "markets": markets_for(sport_key),
                        "oddsFormat": "american",
                        "bookmakers": "draftkings,betmgm",
                        "date": game["commence_time"],
                    },
                )
            except Exception as exc:
                print(sport, "close", game.get("id"), exc)
                continue
            stamp = snap.get("timestamp") or game["commence_time"]
            live = next((item for item in snap.get("data") or [] if item.get("id") == game.get("id")), None)
            if not live:
                continue
            for market, side, price, other in prints(live):
                row = upsert(rows, index, sport, live, market, side, price, stamp, "close")
                if row.get("closeTime") == stamp:
                    closed += 1
                row["autopsy"] = f"Odds API. Last DraftKings snapshot at or before start, {stamp}." + note(other, price.get("point"))
    ledger["rows"] = rows
    ledger["asOfCt"] = now
    ledger["feed"] = "Odds API. DraftKings is the print. BetMGM when it differs. Key is not in this file."
    LEDGER.write_text(json.dumps(ledger, indent=2) + "\n")
    print(json.dumps({"opened": opened, "closed": closed, "rows": len(rows)}))


if __name__ == "__main__":
    main()
