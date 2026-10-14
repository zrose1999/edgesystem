#!/usr/bin/env python3
"""EDGE injury lag (v1). Tracks the NFL injury report and stamps the news-lag pattern on
starting-quarterback news that broke after the open, with no analyst judgment.

  python3 injury.py          update the status history, write injury notes, stamp reads
  python3 injury.py --dry    show what would be stamped, write nothing

Scope of v1: the starting quarterback only, the biggest line in sizing.md. The starter is the
team's main passer over its last two games (stats/nfl_teams.json). Other positions are noted
on the row but not valued yet.

How a read is built (sizing.md, "The rule that matters")
  1. Every run records each player's report status with the time this desk first saw it
     (stats/injuries.json). Our own first-seen time is used, not ESPN's, so nothing is backdated.
  2. For each upcoming NFL row, the starter's status at the open is the last status seen at or
     before openTime. If tracking began after the open, the first status seen is used, so
     anything known before tracking counts 0.
  3. Absence weight: Out, IR, Suspension, Doubtful = 1.0. Questionable = 0.5. Active = 0.
     Value = (weight now - weight at open) x the QB value.
  4. QB value from the starter's last-two-game EPA per dropback, sizing.md midpoints:
     above 0.15 elite 6.0, -0.05 to 0.15 average 3.75, below -0.05 weak 1.75.
     Totals: -2.25 per starter fully out, scaled the same way.
  5. fair home line = open home line + home value - away value. fair total = open total + total value.
     The read is stamped through pull.py read, which grades the edge against the current price.
  A row is re-read only when its news changes. pull.py logs a repeat side as a reread.
"""

import json
import re
import sys
import urllib.request
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pull

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "stats" / "injuries.json"
TEAMS = ROOT / "stats" / "nfl_teams.json"
PATTERN = "news-lag"
FEED = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"
WEIGHT = {"out": 1.0, "injured reserve": 1.0, "suspension": 1.0, "doubtful": 1.0, "questionable": 0.5}
ABBR = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL", "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR", "Chicago Bears": "CHI", "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL", "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX", "Kansas City Chiefs": "KC",
    "Los Angeles Chargers": "LAC", "Los Angeles Rams": "LA", "Las Vegas Raiders": "LV", "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN", "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT", "Seattle Seahawks": "SEA",
    "San Francisco 49ers": "SF", "Tampa Bay Buccaneers": "TB", "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}


def weight(status):
    s = (status or "active").lower()
    if s.startswith("reserve"):
        return 1.0
    return WEIGHT.get(s, 0.0)


def key(name):
    """'Jacoby Brissett', 'J. Brissett' and 'J.Brissett' all become 'jbrissett'. 'C.J. Stroud' matches 'C.Stroud'."""
    parts = re.sub(r"[^a-z .'-]", "", (name or "").lower()).replace(".", " ").split()
    parts = [w for w in parts if w not in ("jr", "sr", "ii", "iii", "iv", "v")]
    if not parts:
        return ""
    rest = [w for w in parts[1:] if len(w) > 1] or parts[1:] or parts[:1]
    return parts[0][0] + re.sub(r"[^a-z]", "", "".join(rest))


def qb_value(passer):
    epa = (passer or {}).get("epaPerDropback")
    if epa is None:
        return 3.75, "average (no EPA)"
    if epa > 0.15:
        return 6.0, f"elite ({epa:+.2f} EPA/dropback)"
    if epa >= -0.05:
        return 3.75, f"average ({epa:+.2f} EPA/dropback)"
    return 1.75, f"weak ({epa:+.2f} EPA/dropback)"


def status_at(timeline, when):
    """Status at time `when` from a [[time, status], ...] timeline. Before tracking began: the first status seen."""
    if not timeline:
        return "Active"
    seen = [s for t, s in timeline if t <= when]
    return seen[-1] if seen else timeline[0][1]


def update_history(hist, feed, now):
    """Append a status to each player's timeline when it changes. Players who leave the report are Active."""
    current = {}
    for team in feed.get("injuries") or []:
        abbr = ABBR.get(team.get("displayName"))
        if not abbr:
            continue
        for item in team.get("injuries") or []:
            ath = item.get("athlete") or {}
            k = key(ath.get("displayName"))
            if k:
                current[(abbr, k)] = {"name": ath.get("displayName"), "pos": (ath.get("position") or {}).get("abbreviation"),
                                      "status": item.get("status") or "Active", "note": item.get("shortComment")}
    players = hist.setdefault("players", {})
    changes = 0
    for (abbr, k), info in current.items():
        p = players.setdefault(f"{abbr}|{k}", {"name": info["name"], "pos": info["pos"], "team": abbr, "timeline": []})
        p["note"] = info["note"]
        if not p["timeline"] or p["timeline"][-1][1] != info["status"]:
            p["timeline"].append([now, info["status"]])
            changes += 1
    for pid, p in players.items():
        abbr, k = pid.split("|", 1)
        if (abbr, k) not in current and p["timeline"] and p["timeline"][-1][1] != "Active":
            p["timeline"].append([now, "Active"])
            changes += 1
    if "trackingSince" not in hist:
        hist["trackingSince"] = now
    hist["asOf"] = now
    return changes


def team_news(team_name, teams, hist, open_time, now):
    """Starter QB value change since the open for one team: (spread value, total value, text)."""
    abbr = ABBR.get(team_name)
    passer = ((teams.get(abbr) or {}).get("lastTwoMainPasser")) if abbr else None
    if not passer or not passer.get("name"):
        return 0.0, 0.0, None
    pid = f"{abbr}|{key(passer['name'])}"
    p = (hist.get("players") or {}).get(pid)
    timeline = (p or {}).get("timeline") or []
    then, current = status_at(timeline, open_time), status_at(timeline, now)
    delta = weight(current) - weight(then)
    if not delta:
        return 0.0, 0.0, None
    val, tier = qb_value(passer)
    name = (p or {}).get("name") or passer["name"]
    text = (f"{abbr} QB {name}, {tier}: {then} at the open, {current} now. "
            f"{delta:+.1f} x {val:g} = {delta * val:+.2f} toward the opponent; total {delta * -2.25:+.2f}.")
    return delta * val, delta * -2.25, text


def main(dry=False):
    now = pull.iso(datetime.now(timezone.utc))
    hist = pull.load(HISTORY, {})
    try:
        req = urllib.request.Request(FEED, headers={"User-Agent": "EDGE desk"})
        with urllib.request.urlopen(req, timeout=30) as r:
            feed = json.loads(r.read().decode())
    except Exception as exc:
        print(json.dumps({"pattern": PATTERN, "error": f"injury feed: {exc}"}))
        return
    changes = update_history(hist, feed, now)
    teams = (pull.load(TEAMS, {}) or {}).get("teams") or {}
    ledger = pull.load(pull.LEDGER, {"rows": []})
    horizon = pull.iso(datetime.now(timezone.utc) + timedelta(days=8))
    to_read = []
    for row in ledger.get("rows") or []:
        if row.get("sport") != "NFL" or row.get("market") not in ("spread", "total"):
            continue
        if not row.get("commence") or not (now < row["commence"] <= horizon):
            continue
        open_line, open_time = row.get("openLine"), row.get("openTime")
        if not isinstance(open_line, (int, float)) or pull.missing(open_time):
            continue
        hs, ht, htext = team_news(row.get("home"), teams, hist, open_time, now)
        as_, at, atext = team_news(row.get("away"), teams, hist, open_time, now)
        items = [t for t in (htext, atext) if t]
        if not items:
            continue
        if row["market"] == "spread":
            fair = open_line + hs - as_
            fair_text = f"Open home line {open_line:+g}, fair {fair:+g}."
        else:
            fair = open_line + ht + at
            fair_text = f"Open total {open_line:g}, fair {fair:g}."
        signature = " | ".join(items)
        if row.get("newsLagSig") == signature:
            continue
        row["injury"] = signature
        to_read.append((row, fair, signature + " " + fair_text, signature))

    if dry:
        for row, fair, reason, _ in to_read:
            print(f"WOULD READ {row['id']} market {(row.get('lastSnap') or {}).get('line')} | {reason}")
    else:
        pull.save(HISTORY, hist)
        for row, _, _, sig in to_read:
            row["newsLagSig"] = sig
        pull.save(pull.LEDGER, ledger)
        for row, fair, reason, _ in to_read:
            args = Namespace(id=row["id"], fair=f"{fair:.2f}", confidence="medium", reason=reason,
                             falsifier="The line closes at or past the fair number on the other side, "
                                       "or the status changes back before kickoff.",
                             pattern=PATTERN, stake="0.5", big=True, by="injury.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"pattern": PATTERN, "statusChanges": changes, "reads": len(to_read),
                      "tracked": len(hist.get("players") or {}), "trackingSince": hist.get("trackingSince"), "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
