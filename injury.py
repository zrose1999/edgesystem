#!/usr/bin/env python3
"""EDGE injury lag (v2). Tracks the NFL injury report against each team's starters and stamps the
news-lag pattern on news that broke after the open, with no analyst judgment.

  python3 injury.py          update status history and depth charts, write injury notes, stamp reads
  python3 injury.py --dry    show what would be stamped, write nothing

Who counts as a starter
  ESPN depth charts, refreshed once a day (stats/nfl_depth.json). A player counts as a starter in a
  role if any snapshot in the last STARTER_DAYS days had him first at that slot, so a starter who is
  moved down the chart because he is hurt still counts. The quarterback is also the team's main
  passer over its last two games (stats/nfl_teams.json), which sets his tier.

Values (sizing.md tables; the low end where the table gives a range, because roles are read
from a chart and not confirmed by the analyst)
  spread, points toward the other team            total, points
  QB   elite 6.0 / average 3.75 / weak 1.75       QB -2.25
  WR1 0.5     RB1 0.25     kicker 0.5             WR1 or RB1 -0.5
  LT or C 0.5     other OL starter 0.25           two or more OL out -0.5
  two or more OL out: add them, then add 0.5
  defensive starter 0.25

How a read is built (sizing.md, "The rule that matters")
  1. Every run records each player's report status with the time this desk first saw it
     (stats/injuries.json). Our own first-seen time is used, not ESPN's, so nothing is backdated.
  2. A starter's status at the open is the last status seen at or before openTime. If tracking began
     after the open, the first status seen is used, so news known before tracking counts 0.
  3. Absence weight: Out, IR, Suspension, Doubtful, Reserve = 1.0. Questionable = 0.5. Active = 0.
     Each item is (weight now - weight at open) x its value. Only the change since the open counts.
  4. fair home line = open home line + home value - away value. fair total = open total + total value.
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
DEPTH = ROOT / "stats" / "nfl_depth.json"
TEAMS = ROOT / "stats" / "nfl_teams.json"
PATTERN = "news-lag"
FEED = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"
TEAM_LIST = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
CHART = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{season}/teams/{tid}/depthcharts"
STARTER_DAYS = 10
DEPTH_REFRESH_H = 20
WEIGHT = {"out": 1.0, "injured reserve": 1.0, "suspension": 1.0, "doubtful": 1.0, "questionable": 0.5}
# role: (spread value, total value, label)
VALUES = {
    "WR1": (0.5, -0.5, "WR1"), "RB1": (0.25, -0.5, "RB1"), "K": (0.5, 0.0, "kicker"),
    "LT": (0.5, 0.0, "LT"), "C": (0.5, 0.0, "C"), "OL": (0.25, 0.0, "OL starter"),
    "DEF": (0.25, 0.0, "defensive starter"),
}
OL_ROLES = ("LT", "C", "OL")
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


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "EDGE desk"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


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


def espn_id(athlete):
    for link in athlete.get("links") or []:
        m = re.search(r"/id/(\d+)", link.get("href") or "")
        if m:
            return m.group(1)
    return None


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


# ---------- injury report ----------

def update_history(hist, feed, now):
    """Append a status to each player's timeline when it changes. Players who leave the report are Active.
    Players are keyed TEAM|espnId. v1 entries keyed TEAM|namekey hand their timeline over once."""
    current = {}
    for team in feed.get("injuries") or []:
        abbr = ABBR.get(team.get("displayName"))
        if not abbr:
            continue
        for item in team.get("injuries") or []:
            ath = item.get("athlete") or {}
            pid = espn_id(ath)
            if not pid:
                continue
            current[f"{abbr}|{pid}"] = {"name": ath.get("displayName"), "nameKey": key(ath.get("displayName")),
                                        "pos": (ath.get("position") or {}).get("abbreviation"), "team": abbr,
                                        "id": pid, "status": item.get("status") or "Active",
                                        "note": item.get("shortComment")}
    players = hist.setdefault("players", {})
    changes = 0
    for pk, info in current.items():
        if pk not in players:
            old = players.pop(f"{info['team']}|{info['nameKey']}", None)
            players[pk] = {"timeline": (old or {}).get("timeline") or []}
        p = players[pk]
        p.update({k: info[k] for k in ("name", "nameKey", "pos", "team", "id", "note")})
        if not p["timeline"] or p["timeline"][-1][1] != info["status"]:
            p["timeline"].append([now, info["status"]])
            changes += 1
    for pk, p in players.items():
        if pk not in current and p.get("timeline") and p["timeline"][-1][1] != "Active":
            p["timeline"].append([now, "Active"])
            changes += 1
    hist.setdefault("trackingSince", now)
    hist["asOf"] = now
    return changes


# ---------- depth charts ----------

def first_ids(position, n=1):
    out = []
    for a in (position or {}).get("athletes") or []:
        m = re.search(r"/athletes/(\d+)", (a.get("athlete") or {}).get("$ref") or "")
        if m and m.group(1) not in out:
            out.append(m.group(1))
        if len(out) >= n:
            break
    return out


def roles_from_chart(chart):
    roles = {}
    for dc in chart.get("items") or []:
        pos = dc.get("positions") or {}
        if "qb" in pos and not roles.get("QB"):
            roles["QB"] = first_ids(pos.get("qb"))
            roles["WR1"] = first_ids(pos.get("wr"))
            roles["RB1"] = first_ids(pos.get("rb"))
            roles["LT"] = first_ids(pos.get("lt"))
            roles["C"] = first_ids(pos.get("c"))
            roles["OL"] = [i for k in ("lg", "rg", "rt") for i in first_ids(pos.get(k))]
        elif "pk" in pos:
            roles["K"] = first_ids(pos.get("pk"))
        elif any(k in pos for k in ("lcb", "rcb", "fs", "ss")) and not roles.get("DEF"):
            ids = []
            for k in pos:
                for i in first_ids(pos[k]):
                    if i not in ids:
                        ids.append(i)
            roles["DEF"] = ids
    return roles


def refresh_depth(depth, now_dt):
    last = depth.get("asOf")
    if last and (now_dt - pull.parse(last)).total_seconds() < DEPTH_REFRESH_H * 3600:
        return 0
    try:
        team_ids = {t["team"]["displayName"]: t["team"]["id"]
                    for t in fetch(TEAM_LIST)["sports"][0]["leagues"][0]["teams"]}
    except Exception as exc:
        print("depth team list", exc)
        return 0
    season = now_dt.year if now_dt.month >= 3 else now_dt.year - 1
    today = now_dt.strftime("%Y-%m-%d")
    floor = (now_dt - timedelta(days=STARTER_DAYS)).strftime("%Y-%m-%d")
    got = 0
    for name, abbr in ABBR.items():
        tid = team_ids.get(name)
        if not tid:
            continue
        try:
            roles = roles_from_chart(fetch(CHART.format(season=season, tid=tid)))
        except Exception as exc:
            print("depth", abbr, exc)
            continue
        team = depth.setdefault("teams", {}).setdefault(abbr, {"snapshots": []})
        snaps = [s for s in team["snapshots"] if s["date"] != today and s["date"] >= floor]
        snaps.append({"date": today, "roles": roles})
        team["snapshots"] = snaps
        got += 1
    if got:
        depth["asOf"] = pull.iso(now_dt)
    return got


def starters(depth, abbr):
    """role -> set of ESPN ids who started there in any recent snapshot."""
    out = {}
    for snap in ((depth.get("teams") or {}).get(abbr) or {}).get("snapshots") or []:
        for role, ids in (snap.get("roles") or {}).items():
            out.setdefault(role, set()).update(ids)
    return out


# ---------- valuation ----------

def team_news(team_name, teams, hist, depth, open_time, now):
    """Value of starter news since the open for one team: (spread value, total value, [text])."""
    abbr = ABBR.get(team_name)
    if not abbr:
        return 0.0, 0.0, []
    players = hist.get("players") or {}
    by_id = {p.get("id"): p for p in players.values() if p.get("team") == abbr and p.get("id")}
    roles = starters(depth, abbr)
    passer = (teams.get(abbr) or {}).get("lastTwoMainPasser") or {}
    spread = total = 0.0
    items, ol_then, ol_now, seen = [], 0.0, 0.0, set()

    def delta_of(p):
        tl = p.get("timeline") or []
        then, cur = status_at(tl, open_time), status_at(tl, now)
        return weight(cur) - weight(then), then, cur, weight(then), weight(cur)

    # Quarterback: depth-chart starter, plus the main passer by name.
    qbs = [by_id[i] for i in roles.get("QB", set()) if i in by_id]
    if passer.get("name"):
        qbs += [p for p in by_id.values() if p.get("nameKey") == key(passer["name"]) and p not in qbs]
    for p in qbs:
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        d, then, cur, _, _ = delta_of(p)
        if not d:
            continue
        is_passer = passer.get("name") and p.get("nameKey") == key(passer["name"])
        val, tier = qb_value(passer) if is_passer else (3.75, "average (not the recent main passer)")
        spread += d * val
        total += d * -2.25
        items.append(f"{abbr} QB {p['name']}, {tier}: {then} at the open, {cur} now, "
                     f"{d * val:+.2f} spread, {d * -2.25:+.2f} total")

    for role, (sv, tv, label) in VALUES.items():
        for pid in sorted(roles.get(role, set())):
            p = by_id.get(pid)
            if not p or pid in seen:
                continue
            seen.add(pid)
            d, then, cur, w_then, w_now = delta_of(p)
            if role in OL_ROLES:
                ol_then += w_then
                ol_now += w_now
            if not d:
                continue
            spread += d * sv
            total += d * tv
            items.append(f"{abbr} {label} {p['name']}: {then} at the open, {cur} now, "
                         f"{d * sv:+.2f} spread" + (f", {d * tv:+.2f} total" if tv else ""))
    # Two or more OL starters out: add 0.5 spread and -0.5 total, counted only if it became true after the open.
    if ol_now >= 2 and ol_then < 2:
        spread += 0.5
        total -= 0.5
        items.append(f"{abbr} two or more OL starters out since the open, +0.50 spread, -0.50 total")
    elif ol_then >= 2 and ol_now < 2:
        spread -= 0.5
        total += 0.5
        items.append(f"{abbr} OL back under two out since the open, -0.50 spread, +0.50 total")
    return spread, total, items


def main(dry=False):
    now_dt = datetime.now(timezone.utc)
    now = pull.iso(now_dt)
    hist = pull.load(HISTORY, {})
    depth = pull.load(DEPTH, {})
    try:
        feed = fetch(FEED)
    except Exception as exc:
        print(json.dumps({"pattern": PATTERN, "error": f"injury feed: {exc}"}))
        return
    changes = update_history(hist, feed, now)
    charts = refresh_depth(depth, now_dt)
    teams = (pull.load(TEAMS, {}) or {}).get("teams") or {}
    ledger = pull.load(pull.LEDGER, {"rows": []})
    horizon = pull.iso(now_dt + timedelta(days=8))
    to_read = []
    for row in ledger.get("rows") or []:
        if row.get("sport") != "NFL" or row.get("market") not in ("spread", "total"):
            continue
        if not row.get("commence") or not (now < row["commence"] <= horizon):
            continue
        open_line, open_time = row.get("openLine"), row.get("openTime")
        if not isinstance(open_line, (int, float)) or pull.missing(open_time):
            continue
        hs, ht, hitems = team_news(row.get("home"), teams, hist, depth, open_time, now)
        as_, at, aitems = team_news(row.get("away"), teams, hist, depth, open_time, now)
        items = hitems + aitems
        if not items:
            continue
        if row["market"] == "spread":
            if not (hs or as_):
                continue
            fair = open_line + hs - as_
            fair_text = f"Open home line {open_line:+g}, fair {fair:+.2f}."
        else:
            if not (ht or at):
                continue
            fair = open_line + ht + at
            fair_text = f"Open total {open_line:g}, fair {fair:.2f}."
        signature = " | ".join(items)
        if row.get("newsLagSig") == signature:
            continue
        to_read.append((row, fair, signature + ". " + fair_text, signature))

    if dry:
        for row, fair, reason, _ in to_read:
            print(f"WOULD READ {row['id']} market {(row.get('lastSnap') or {}).get('line')} | {reason}")
    else:
        pull.save(HISTORY, hist)
        pull.save(DEPTH, depth)
        for row, _, _, sig in to_read:
            row["newsLagSig"] = sig
            row["injury"] = sig
        pull.save(pull.LEDGER, ledger)
        for row, fair, reason, _ in to_read:
            args = Namespace(id=row["id"], fair=f"{fair:.2f}", confidence="medium", reason=reason,
                             falsifier="The line closes at or past the fair number on the other side, "
                                       "or a status changes back before kickoff.",
                             pattern=PATTERN, stake="0.5", big=True, by="injury.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"pattern": PATTERN, "statusChanges": changes, "depthChartsRefreshed": charts,
                      "reads": len(to_read), "tracked": len(hist.get("players") or {}),
                      "trackingSince": hist.get("trackingSince"), "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
