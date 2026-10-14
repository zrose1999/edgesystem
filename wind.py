#!/usr/bin/env python3
"""EDGE weather (v1). Writes the forecast on every outdoor NFL and NCAAF game and stamps the
wind-total pattern with no analyst judgment.

  python3 wind.py           update weather on upcoming rows, stamp wind-total reads
  python3 wind.py --dry     show what would be written, write nothing

Sources (free, no key)
  ESPN scoreboard   venue, city, state, indoor flag, kickoff
  Open-Meteo        geocoding of a venue's city, once, cached in stats/venues.json
  weather.gov       hourly forecast at the venue

Values come from sizing.md, total table, midpoints:
  sustained wind 15 to 19 mph   -3.0       20 mph or more   -3.5
  heavy rain or snow            -1.0
Wind is the average of the forecast from kickoff through three hours after.

Rules
  The forecast is written on every row (weather field) inside WRITE_HOURS of kickoff.
  It is valued only inside VALUE_HOURS (sizing.md: 36). A read is stamped only inside
  STAMP_HOURS (patterns.md: 24), and only when the value is not 0.
  fair = open total + value. News known before the open is already in the open, so a row
  whose open was taken inside VALUE_HOURS of kickoff is not stamped.
  One wind-total read per row, ever. The read is stamped through pull.py read, so the price
  is the stored DraftKings price and the grade comes from the edge against the bar.
"""

import difflib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pull

ROOT = Path(__file__).resolve().parent
VENUES = ROOT / "stats" / "venues.json"
UA = {"User-Agent": "EDGE desk (github.com/zrose1999/edgesystem)", "Accept": "application/geo+json"}
PATTERN = "wind-total"
WRITE_HOURS = float(os.environ.get("WIND_WRITE_HOURS", "72"))
VALUE_HOURS = float(os.environ.get("WIND_VALUE_HOURS", "36"))
STAMP_HOURS = float(os.environ.get("WIND_STAMP_HOURS", "24"))
LEAGUES = {"NFL": "football/nfl", "NCAAF": "football/college-football"}
# ESPN marks these as outdoor, but they have a fixed roof.
COVERED = {"SoFi Stadium"}
STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
    "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def norm(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").lower().replace("&", "and"))


def espn_games(sport, days):
    """Upcoming games for the next `days` days: kickoff, home, away, venue."""
    out = []
    today = datetime.now(timezone.utc).date()
    for i in range(days + 1):
        d = (today + timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/{LEAGUES[sport]}/scoreboard?dates={d}&limit=400"
        if sport == "NCAAF":
            url += "&groups=80"
        try:
            data = fetch(url)
        except Exception as exc:
            print(sport, d, "scoreboard", exc)
            continue
        for e in data.get("events") or []:
            c = (e.get("competitions") or [{}])[0]
            teams = {t.get("homeAway"): t.get("team", {}).get("displayName") for t in c.get("competitors") or []}
            v = c.get("venue") or {}
            out.append({"kickoff": c.get("date"), "home": teams.get("home"), "away": teams.get("away"), "venue": v})
    return out


def geocode(venue, cache):
    vid = str(venue.get("id") or venue.get("fullName"))
    if vid in cache:
        return cache[vid]
    addr = venue.get("address") or {}
    city, state = addr.get("city"), STATES.get(addr.get("state") or "")
    if not city or not state:
        return None
    q = urllib.parse.urlencode({"name": city, "count": 10, "country_code": "US"})
    try:
        res = fetch(f"https://geocoding-api.open-meteo.com/v1/search?{q}").get("results") or []
    except Exception as exc:
        print("geocode", city, exc)
        return None
    hit = next((r for r in res if r.get("admin1") == state), None)
    if not hit:
        return None
    cache[vid] = {"name": venue.get("fullName"), "city": city, "state": addr.get("state"),
                  "lat": round(hit["latitude"], 4), "lon": round(hit["longitude"], 4)}
    return cache[vid]


def hourly(spot, cache_urls):
    key = f"{spot['lat']},{spot['lon']}"
    url = cache_urls.get(key)
    if not url:
        url = fetch(f"https://api.weather.gov/points/{key}", UA)["properties"]["forecastHourly"]
        cache_urls[key] = url
    return fetch(url, UA)["properties"]["periods"]


def near_kick(g, row):
    return abs((pull.parse(g["kickoff"]) - pull.parse(row["commence"])).total_seconds()) <= 3 * 3600


def match(row, by_key, games):
    """ESPN game for a ledger row: exact home name first, then the closest names at the same kickoff
    (ESPN and the Odds API spell some schools differently, e.g. Sam Houston vs Sam Houston State)."""
    exact = next((g for g in by_key.get((row["sport"], norm(row.get("home"))), []) if near_kick(g, row)), None)
    if exact:
        return exact
    best, score = None, 0.0
    for g in games:
        if g["sport"] != row["sport"] or not g.get("home") or not g.get("away") or not near_kick(g, row):
            continue
        s = (difflib.SequenceMatcher(None, norm(g["home"]), norm(row.get("home"))).ratio()
             + difflib.SequenceMatcher(None, norm(g["away"]), norm(row.get("away"))).ratio()) / 2
        if s > score:
            best, score = g, s
    return best if score >= 0.75 else None


def mph(text):
    nums = [float(n) for n in re.findall(r"\d+", text or "")]
    return sum(nums) / len(nums) if nums else 0.0


def conditions(periods, kickoff):
    """Average sustained wind, worst precipitation chance and the forecast text, kickoff to +3h."""
    k = pull.parse(kickoff)
    window = [p for p in periods if k - timedelta(minutes=59) <= pull.parse(p["startTime"]) <= k + timedelta(hours=3)]
    if not window:
        return None
    wind = sum(mph(p.get("windSpeed")) for p in window) / len(window)
    pop = max((p.get("probabilityOfPrecipitation") or {}).get("value") or 0 for p in window)
    text = "; ".join(dict.fromkeys(p.get("shortForecast", "") for p in window))
    heavy = pop >= 60 and bool(re.search(r"heavy rain|snow", text, re.I))
    return {"windMph": round(wind, 1), "pop": pop, "text": text, "heavy": heavy,
            "temp": window[0].get("temperature")}


def value(c):
    v, why = 0.0, []
    if c["windMph"] >= 20:
        v -= 3.5
        why.append(f"wind {c['windMph']:.0f} mph sustained, -3.5")
    elif c["windMph"] >= 15:
        v -= 3.0
        why.append(f"wind {c['windMph']:.0f} mph sustained, -3.0")
    if c["heavy"]:
        v -= 1.0
        why.append(f"heavy precipitation ({c['text']}, {c['pop']}%), -1.0")
    return v, why


def main(dry=False):
    ledger = pull.load(pull.LEDGER, {"rows": []})
    picks = pull.load(pull.PICKS, {"picks": []})
    cache = pull.load(VENUES, {"venues": {}, "forecastUrls": {}})
    done = {p.get("rowId") for p in picks["picks"] if p.get("pattern") == PATTERN}
    now = datetime.now(timezone.utc)
    rows = [r for r in ledger.get("rows") or [] if r.get("sport") in LEAGUES and r.get("commence")]
    horizon = pull.iso(now + timedelta(hours=WRITE_HOURS))
    rows = [r for r in rows if pull.iso(now) < r["commence"] <= horizon]
    if not rows:
        print(json.dumps({"pattern": PATTERN, "rows": 0, "note": "no NFL or NCAAF games in the window"}))
        return
    days = int(WRITE_HOURS // 24) + 1
    games = []
    for sport in sorted({r["sport"] for r in rows}):
        games += [dict(g, sport=sport) for g in espn_games(sport, days)]
    by_key = {}
    for g in games:
        if g.get("home") and g.get("kickoff"):
            by_key.setdefault((g["sport"], norm(g["home"])), []).append(g)

    written = unmatched = indoor = 0
    to_stamp, forecast_cache = [], {}
    for row in rows:
        game = match(row, by_key, games)
        if not game:
            unmatched += 1
            continue
        v = game["venue"]
        if v.get("indoor") or v.get("fullName") in COVERED:
            indoor += 1
            if pull.missing(row.get("weather")):
                row["weather"] = f"indoor ({v.get('fullName')})"
                written += 1
            continue
        if (v.get("address") or {}).get("country") not in (None, "USA"):
            row["weather"] = f"not checked: {v.get('fullName')} is outside the US forecast area"
            continue
        spot = geocode(v, cache["venues"])
        if not spot:
            row["weather"] = f"not checked: could not place {v.get('fullName')}"
            continue
        key = f"{spot['lat']},{spot['lon']}"
        try:
            if key not in forecast_cache:
                forecast_cache[key] = hourly(spot, cache["forecastUrls"])
            c = conditions(forecast_cache[key], row["commence"])
        except Exception as exc:
            print("forecast", v.get("fullName"), exc)
            continue
        if not c:
            continue
        hours_out = (pull.parse(row["commence"]) - now).total_seconds() / 3600
        val, why = value(c)
        if hours_out > VALUE_HOURS:
            val, why = 0.0, ["forecast outside 36 hours, valued at 0"]
        stamp = pull.iso(now)
        row["weather"] = (f"{c['text']}, {c['temp']}F, wind {c['windMph']:.0f} mph, precip {c['pop']}% "
                          f"at {v.get('fullName')} (weather.gov {stamp}). Total value {val:+.1f}.")
        row["weatherData"] = dict(c, value=val, asOf=stamp, venue=v.get("fullName"))
        written += 1
        if (row.get("market") == "total" and val != 0 and hours_out <= STAMP_HOURS
                and row["id"] not in done):
            open_line, open_time = row.get("openLine"), row.get("openTime")
            if not isinstance(open_line, (int, float)) or pull.missing(open_time):
                continue
            if (pull.parse(row["commence"]) - pull.parse(open_time)).total_seconds() / 3600 <= VALUE_HOURS:
                print(f"no stamp {row['id']}: open taken inside {VALUE_HOURS:g}h, weather may be in it")
                continue
            to_stamp.append((row, open_line + val, why))

    if dry:
        for row, fair, why in to_stamp:
            print(f"WOULD READ {row['id']} fair {fair:g} vs market {(row.get('lastSnap') or {}).get('line')} | {'; '.join(why)}")
    else:
        pull.save(pull.LEDGER, ledger)
        cache["asOf"] = pull.iso(now)
        pull.save(VENUES, cache)
        # Reads are stamped after the ledger is saved, through pull.py's own read path.
        if "NCAAF" not in pull.READ:
            pull.READ = pull.READ + ["NCAAF"]   # weather reads are scripted, so NCAAF is open to them
        for row, fair, why in to_stamp:
            args = Namespace(id=row["id"], fair=str(fair), confidence="medium",
                             reason=f"Open {row['openLine']:g}; " + "; ".join(why) + f". Fair {fair:g}.",
                             falsifier="The total closes at or below the fair number before the forecast changes, "
                                       "or kickoff wind comes in under 15 mph.",
                             pattern=PATTERN, stake="0.5", big=False, by="wind.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"pattern": PATTERN, "rows": len(rows), "weatherWritten": written, "indoor": indoor,
                      "unmatched": unmatched, "reads": len(to_stamp), "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
