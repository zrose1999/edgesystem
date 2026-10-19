#!/usr/bin/env python3
"""EDGE team home locations for travel features. Run by hand (not by the jobs) when teams change venues.

  python3 team_venues.py        write stats/team_venues.json for every team in the NBA, NHL and NCAAF schedules

Each team's home venue city and state come from ESPN's team pages (free). Coordinates and IANA time zone come from
the offline GeoNames city table (pip package geonamescache), so the jobs never geocode and need no new packages:
memory.py only reads the JSON this writes. Teams ESPN gives no venue for, or whose city the table lacks, are listed
under "missing" and get no travel features. A neutral-site game has no known location and is skipped.
"""

import json
import re
import time
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "team_venues.json"
LEAGUES = {"NBA": ("basketball", "nba", "nba_games"), "NHL": ("hockey", "nhl", "nhl_games"),
           "NCAAF": ("football", "college-football", "ncaaf_games")}
CA_PROVINCES = {"AB": "01", "BC": "02", "MB": "03", "NB": "04", "NL": "05", "NS": "07", "ON": "08", "PE": "09",
                "QC": "10", "SK": "11"}
# ESPN city spellings that differ from the GeoNames table.
CITY_FIX = {("New York", "NY"): "New York City", ("Montréal", "QC"): "Montreal", ("Mt. Pleasant", "MI"): "Mount Pleasant",
            # campus or township addresses the city table does not list: the nearest listed city
            ("USAF Academy", "CO"): "Colorado Springs", ("Lorman", "MS"): "Port Gibson", ("Bronx", "NY"): "New York City",
            ("University Park", "PA"): "State College", ("Moon Township", "PA"): "Coraopolis",
            ("North Easton", "MA"): "Easton"}
# Teams ESPN gives no home venue for (or lists under another name): home city by hand.
MANUAL = {"detroit pistons": ("Detroit", "MI"), "st thomasminnesota tommies": ("Saint Paul", "MN"),
          "ut rio grande valley vaqueros": ("Edinburg", "TX")}
SKIP = {"team stars", "team stripes", "world"}   # All-Star exhibition teams


def key(name):
    t = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r" +", " ", re.sub(r"[^a-z0-9 ]", "", t)).strip()


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EDGE desk"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def venue_of(group, league, team_id):
    """The team's home venue: ESPN's site API (pro teams), else the core API (college teams), current season first."""
    v = (fetch(f"https://site.api.espn.com/apis/site/v2/sports/{group}/{league}/teams/{team_id}")["team"]
         .get("franchise") or {}).get("venue") or {}
    if (v.get("address") or {}).get("city"):
        return v
    for season in (2027, 2026):
        try:
            v = fetch(f"https://sports.core.api.espn.com/v2/sports/{group}/leagues/{league}/seasons/{season}/teams/{team_id}").get("venue") or {}
        except Exception:  # noqa: BLE001
            continue
        if (v.get("address") or {}).get("city"):
            return v
    return {}


def gazetteer():
    import geonamescache
    by = {}
    for c in geonamescache.GeonamesCache(min_city_population=500).get_cities().values():
        if c["countrycode"] in ("US", "CA"):
            k = (key(c["name"]), c["countrycode"], c["admin1code"])
            if k not in by or c["population"] > by[k]["population"]:
                by[k] = c
    return by


def locate(city, state, gaz):
    city = CITY_FIX.get((city, state), city)
    if state in CA_PROVINCES:
        hit = gaz.get((key(city), "CA", CA_PROVINCES[state]))
    else:
        hit = gaz.get((key(city), "US", state))
        if not hit and state == "DC":
            hit = gaz.get((key("Washington"), "US", "DC"))
    if not hit:
        return None
    return {"lat": round(hit["latitude"], 4), "lon": round(hit["longitude"], 4), "tz": hit["timezone"]}


def main():
    gaz = gazetteer()
    out = {"note": __doc__.strip().splitlines()[0], "teams": {}, "missing": {}}
    for sport, (group, league, sched) in LEAGUES.items():
        games = json.loads((ROOT / "stats" / f"{sched}.json").read_text()).get("games") or {}
        wanted = {key(g[s]) for g in games.values() for s in ("home", "away") if g.get(s)} - SKIP
        listing = fetch(f"https://site.api.espn.com/apis/site/v2/sports/{group}/{league}/teams?limit=1000")
        teams = [t["team"] for lg in listing["sports"][0]["leagues"] for t in lg["teams"]]
        found, missing = {}, []
        for t in teams:
            if key(t["displayName"]) not in wanted:
                continue
            try:
                venue = venue_of(group, league, t["id"])
            except Exception as exc:  # noqa: BLE001
                missing.append(f"{t['displayName']} (fetch: {exc})")
                continue
            addr = venue.get("address") or {}
            if not addr.get("city") and key(t["displayName"]) in MANUAL:
                addr = dict(zip(("city", "state"), MANUAL[key(t["displayName"])]))
            loc = locate(addr.get("city"), addr.get("state"), gaz) if addr.get("city") and addr.get("state") else None
            if not loc:
                missing.append(f"{t['displayName']} ({addr.get('city')}, {addr.get('state')})")
                continue
            found[key(t["displayName"])] = {"name": t["displayName"], "venue": venue.get("fullName"),
                                            "city": addr.get("city"), "state": addr.get("state"), **loc}
        for k, (city, state) in MANUAL.items():
            if k in wanted and k not in found:
                loc = locate(city, state, gaz)
                if loc:
                    found[k] = {"name": k, "venue": None, "city": city, "state": state, "manual": True, **loc}
        out["teams"][sport] = found
        out["missing"][sport] = sorted(missing) + sorted(w for w in wanted - set(found) if not any(
            key(m.split(" (")[0]) == w for m in missing))
        print(sport, "teams located", len(found), "of", len(wanted), "missing", len(out["missing"][sport]))
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
