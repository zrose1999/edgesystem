#!/usr/bin/env python3
"""EDGE college quarterback watch. Free sources only.

  python3 cfb_qb.py           refresh (at most every REFRESH_H hours): CFBDepth depth charts, CFBD box-score starters
  python3 cfb_qb.py --force   refresh now

1. CFBDepth (cfbdepth.com, robots.txt allows all): the server-rendered depth chart of every FBS team, read politely
   (one page per team, PAUSE seconds apart). Per team: the listed quarterbacks in order, their role (Full-Time,
   Starter, Backup, ...), any status flag the site shows (Q, D, O, ...), class and CFBDepth rating.
   Some teams' pages carry no static depth chart; they are counted as missing, never guessed.
2. CFBD box scores (CFBD_API_KEY, already a secret): for every finished game this season, the quarterback with the
   most pass attempts for each team: who actually started. Gives each quarterback's starts this season.

Writes:
  stats/cfb_qb.json                     current view per team, plus recent QB1 changes (for alerts)
  stats/history/cfb_qb/<YYYY-MM>.jsonl  one line per team per refresh: the as-of record the learner uses
  stats/cfb_qb_starts.json              box-score starters by team and week
No reads or picks come from this file. Its data points go to the learner (features_archive.py) and to alerts.
"""

import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats" / "cfb_qb.json"
HIST = ROOT / "stats" / "history" / "cfb_qb"
STARTS = ROOT / "stats" / "cfb_qb_starts.json"
SITE = "https://cfbdepth.com"
UA = "EDGE/1.0 (+https://edgesystem.netlify.app)"   # honest bot name; robots.txt allows all
REFRESH_H = 6
PAUSE = 1.5
KEEP_CHANGES_D = 10
# CFBDepth spelling -> the odds feed's spelling (what ledger rows use). Everything else already matches.
ALIASES = {"Miami (FL) Hurricanes": "Miami Hurricanes", "Louisiana Ragin' Cajuns": "Louisiana Ragin Cajuns",
           "Louisiana-Monroe Warhawks": "UL Monroe Warhawks", "Massachusetts Minutemen": "UMass Minutemen",
           "Southern Miss Golden Eagles": "Southern Mississippi Golden Eagles", "Sam Houston Bearkats": "Sam Houston State Bearkats",
           "North Carolina State Wolfpack": "NC State Wolfpack", "Connecticut Huskies": "UConn Huskies"}
FLAGS = {"Q": "questionable", "D": "doubtful", "O": "out", "P": "probable", "GTD": "game-time decision",
         "OUT": "out", "INJ": "injured", "IR": "injured", "SUSP": "suspended"}


def now_utc():
    return datetime.now(timezone.utc)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(url, timeout=40):
    r = subprocess.run(["curl", "-sL", "--compressed", "-m", str(timeout), "-A", UA, url], capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""


def slugs():
    xml = fetch(f"{SITE}/sitemap.xml")
    return sorted(set(re.findall(r"<loc>https://cfbdepth\.com/([^/<]+)/depth-chart</loc>", xml)))


def parse_team(page):
    h1 = re.search(r"<h1>(.*?) Football Depth Chart", page)
    if not h1:
        return None, None
    team = html.unescape(h1.group(1)).strip()
    team = ALIASES.get(team, team)
    sec = re.search(r"<h3>QB Quarterbacks</h3><ol>(.*?)</ol>", page, re.S)
    if not sec:
        return team, None
    qbs = []
    for name, desc in re.findall(r"<li><strong>(.*?)</strong> - (.*?)</li>", sec.group(1)):
        parts = [p.strip() for p in html.unescape(desc).split(",")]
        rating = next((float(m.group(1)) for p in parts for m in [re.search(r"rating ([\d.]+)", p)] if m), None)
        core = [p for p in parts if not p.startswith("No.") and "rating" not in p]
        num = next((p[3:].strip() for p in parts if p.startswith("No.")), None)
        cls = core[0] if core else None
        role = core[1] if len(core) > 1 else None
        flags = [p for p in core[2:] if p]
        status = next((FLAGS.get(f.upper(), f) for f in flags if f.lower() not in ("cleared", "healthy", "active")), None)
        qbs.append({"name": html.unescape(name).strip(), "no": num, "class": cls, "role": role,
                    "status": status, "rating": rating})
    return team, qbs


def refresh_depth(prev):
    teams, missing = {}, []
    for s in slugs():
        page = fetch(f"{SITE}/{s}/depth-chart")
        team, qbs = parse_team(page)
        if team and qbs:
            teams[team] = {"slug": s, "qbs": qbs[:4]}
        else:
            missing.append(team or s)
        time.sleep(PAUSE)
    return teams, missing


def cfbd(path, key):
    req = urllib.request.Request("https://api.collegefootballdata.com" + path,
                                 headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def refresh_starts(key, year):
    """Most pass attempts per team per finished week = the quarterback who started."""
    data = json.loads(STARTS.read_text()) if STARTS.exists() else {"year": year, "weeks": {}}
    if data.get("year") != year:
        data = {"year": year, "weeks": {}}
    try:
        cal = cfbd(f"/calendar?year={year}", key)
    except Exception as exc:  # noqa: BLE001
        print("cfbd calendar", exc)
        return data
    today = now_utc().date().isoformat()
    for w in cal:
        wk, stype = w.get("week"), w.get("seasonType") or w.get("season_type") or "regular"
        end = (w.get("endDate") or w.get("lastGameStart") or w.get("end_date") or "")[:10]
        tag = f"{stype}-{wk}"
        if not end or end >= today:
            continue                    # only finished weeks
        if tag in data["weeks"] and data["weeks"][tag].get("final"):
            continue
        try:
            games = cfbd(f"/games/players?year={year}&week={wk}&seasonType={stype}&category=passing", key)
        except Exception as exc:  # noqa: BLE001
            print("cfbd players", tag, exc)
            continue
        out = {}
        for g in games:
            for t in g.get("teams") or []:
                best = None
                for cat in t.get("categories") or []:
                    if cat.get("name") != "passing":
                        continue
                    for typ in cat.get("types") or []:
                        if typ.get("name") not in ("C/ATT", "COMP/ATT"):
                            continue
                        for a in typ.get("athletes") or []:
                            try:
                                att = int(str(a.get("stat", "0/0")).split("/")[1])
                            except (IndexError, ValueError):
                                continue
                            if best is None or att > best[1]:
                                best = (a.get("name"), att)
                school = t.get("team") or t.get("school")
                if best and school:
                    out[school] = {"qb": best[0], "att": best[1]}
        data["weeks"][tag] = {"end": end, "final": True, "starters": out}
        time.sleep(0.5)
    STARTS.parent.mkdir(parents=True, exist_ok=True)
    STARTS.write_text(json.dumps(data, separators=(",", ":")))
    return data


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower().replace("st.", "state"))


CFBD_SCHOOL = {"Massachusetts": "UMass", "Southern Miss": "Southern Mississippi", "Connecticut": "UConn",
               "Sam Houston": "Sam Houston State", "Hawai'i": "Hawaii", "San José State": "San Jose State",
               "Louisiana Monroe": "UL Monroe", "Miami (FL)": "Miami"}


def school_index(names):
    """CFBD school name -> CFBDepth full team name (school + mascot), only when it is unambiguous."""
    cache = {}

    def match(school):
        if school in cache:
            return cache[school]
        k = CFBD_SCHOOL.get(school, school or "").lower().strip()
        hits = [n for n in names if n.lower().startswith(k + " ")]
        # "Miami" must not take "Miami (OH) ..."; "Florida" must not take "Florida State ..."
        hits = [n for n in hits if not re.match(r"\s*(\(|state\b|tech\b|a&m\b|international\b|atlantic\b|southern\b|northern\b|eastern\b|western\b|central\b)",
                                               n[len(k):].lower())]
        cache[school] = hits[0] if len(hits) == 1 else None
        return cache[school]
    return match


def starts_count(starts, team_full, schools):
    """Season starts per QB for one team (by CFBDepth name)."""
    out = {}
    for w in (starts.get("weeks") or {}).values():
        for school, v in (w.get("starters") or {}).items():
            if schools(school) == team_full:
                out[v["qb"]] = out.get(v["qb"], 0) + 1
    return out


def last_starter(starts, team_full, schools):
    best = None
    for w in (starts.get("weeks") or {}).values():
        for school, v in (w.get("starters") or {}).items():
            if schools(school) == team_full and (best is None or w["end"] > best[0]):
                best = (w["end"], v["qb"])
    return best[1] if best else None


def main(force=False):
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    t = now_utc()
    if not force and prev.get("at") and (t - datetime.fromisoformat(prev["at"].replace("Z", "+00:00"))) < timedelta(hours=REFRESH_H):
        print(json.dumps({"cfbQb": "fresh", "at": prev["at"]}))
        return
    teams, missing = refresh_depth(prev)
    if len(teams) < 30:
        print(json.dumps({"cfbQb": "depth charts unavailable", "teams": len(teams)}))
        return
    key = os.environ.get("CFBD_API_KEY", "").strip()
    year = t.year if t.month >= 6 else t.year - 1
    starts = refresh_starts(key, year) if key else (json.loads(STARTS.read_text()) if STARTS.exists() else {"weeks": {}})
    schools = school_index(list(teams))
    old = prev.get("teams") or {}
    changes = [c for c in prev.get("changes") or []
               if (t - datetime.fromisoformat(c["at"].replace("Z", "+00:00"))).days <= KEEP_CHANGES_D]
    stamp = iso(t)
    HIST.mkdir(parents=True, exist_ok=True)
    hist_lines = []
    for name, v in teams.items():
        qbs = v["qbs"]
        q1 = qbs[0]
        sc = starts_count(starts, name, schools)
        v["qb1"] = q1["name"]
        v["qb1Status"] = q1.get("status")
        v["qb1Starts"] = sc.get(q1["name"], 0) if sc else None
        v["lastStarter"] = last_starter(starts, name, schools)
        before = (old.get(name) or {}).get("qb1")
        v["qb1Since"] = (old.get(name) or {}).get("qb1Since") if before == q1["name"] else stamp
        if not old:
            pass                                  # first refresh: record only, no alerts
        elif before and before != q1["name"]:
            changes.append({"team": name, "from": before, "to": q1["name"], "at": stamp, "kind": "qb1"})
        elif q1.get("status") and q1.get("status") != (old.get(name) or {}).get("qb1Status"):
            changes.append({"team": name, "from": q1["name"], "to": f"{q1['name']} ({q1['status']})", "at": stamp,
                            "kind": "status"})
        r2 = qbs[1]["rating"] if len(qbs) > 1 else None
        hist_lines.append(json.dumps({"at": stamp, "team": name, "qb1": q1["name"], "r1": q1.get("rating"), "r2": r2,
                                      "status": q1.get("status"), "role": q1.get("role"), "starts": v["qb1Starts"],
                                      "last": v["lastStarter"]}, separators=(",", ":")))
    with open(HIST / f"{t.strftime('%Y-%m')}.jsonl", "a") as f:
        f.write("\n".join(hist_lines) + "\n")
    OUT.write_text(json.dumps({"at": stamp, "source": SITE, "teams": teams, "missing": missing, "changes": changes},
                              indent=1))
    print(json.dumps({"cfbQb": "refreshed", "teams": len(teams), "missing": len(missing),
                      "flagged": sum(1 for v in teams.values() if v.get("qb1Status")),
                      "boxScoreWeeks": len(starts.get("weeks") or {}), "newChanges": sum(1 for c in changes if c["at"] == stamp)}))


def as_of(team, when):
    """Latest history record for a team at or before `when` (ISO). For the learner; no lookahead."""
    best = None
    month = when[:7]
    for f in sorted(HIST.glob("*.jsonl")) if HIST.exists() else []:
        if f.stem > month:
            break
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r["team"] == team and r["at"] <= when:
                best = r
    return best


if __name__ == "__main__":
    main(force="--force" in sys.argv[1:])
