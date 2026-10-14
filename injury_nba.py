#!/usr/bin/env python3
"""EDGE NBA injury lag (v1). Tracks the NBA injury report and stamps the news-lag pattern on player news
that broke after the open, with no analyst judgment. Same rules as injury.py (NFL), NBA values.

  python3 injury_nba.py          update status history and player values, stamp reads
  python3 injury_nba.py --dry    show what would be stamped, write nothing

Sources (free, no key): ESPN NBA injury report; ESPN league player stats (season averages).

Player value (points of spread toward the other team when he sits)
  Game Score per game (Hollinger, rebounds split 0.4 since ESPN gives totals only), turned into production
  per 36 minutes above a replacement level of REPLACEMENT_GS36, times his share of 36 minutes, times
  POINTS_PER_GS. A 35-minute star with a Game Score near 25 is about 5 points; a 30-minute starter near
  12 is about 1.5; bench players are well under 1. Capped at VALUE_CAP.
  Current season once a player has MIN_GAMES games, last season before that (the new season starts empty).
  Totals: TOTAL_SHARE of the spread value, taken off the total (a sitting player's points are only partly
  replaced). Both are starting values; the weekly review and backtest move them.

Status weight
  ESPN lists most NBA players as Day-To-Day, so its comment decides: won't play / ruled out / will miss = 1.0,
  doubtful = 0.75, questionable / game-time decision = 0.5, probable / expected to play = 0.1, otherwise 0.4.
  Out = 1.0. Active (off the report) = 0.

The read (sizing.md rule): only the change since the open counts, with this desk's own first-seen times
(stats/injuries_nba.json), so nothing known before tracking or before the open is counted.
fair home line = open home line + home value - away value. fair total = open total + total values.
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
HISTORY = ROOT / "stats" / "injuries_nba.json"
VALUES = ROOT / "stats" / "nba_player_values.json"
PATTERN = "news-lag"
FEED = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
STATS = "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byathlete?season={season}&seasontype=2&limit=1000"
REPLACEMENT_GS36 = 9.0
POINTS_PER_GS = 0.30
VALUE_CAP = 7.0
TOTAL_SHARE = 0.6
MIN_GAMES = 10
VALUE_REFRESH_H = 20
MIN_VALUE = 0.25          # players worth less than this are noted but not valued


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "EDGE desk"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def mascot(name):
    return (name or "").split()[-1].lower()


def espn_id(athlete):
    for link in athlete.get("links") or []:
        m = re.search(r"/id/(\d+)", link.get("href") or "")
        if m:
            return m.group(1)
    return athlete.get("id")


def weight(status, comment):
    s, c = (status or "").lower(), (comment or "").lower()
    if s == "active":
        return 0.0
    if s == "out" or re.search(r"won't play|will not play|ruled out|will miss|out for|is out|sidelined", c):
        return 1.0
    if "doubtful" in c or s == "doubtful":
        return 0.75
    if re.search(r"questionable|game-time|uncertain", c) or s == "questionable":
        return 0.5
    if re.search(r"probable|expected to play|will play|plans to play|good to go|cleared", c) or s == "probable":
        return 0.1
    return 0.4


# ---------- player values ----------

def season_rows(season):
    d = fetch(STATS.format(season=season))
    names = {c["name"]: c.get("names") or [] for c in d.get("categories") or []}
    out = {}
    for a in d.get("athletes") or []:
        vals = {}
        for c in a.get("categories") or []:
            for k, v in zip(names.get(c["name"], []), c.get("values") or []):
                vals[k] = v
        out[str(a["athlete"]["id"])] = {"name": a["athlete"].get("displayName"), **vals}
    return out


def game_score(v):
    g = lambda k: float(v.get(k) or 0)
    return (g("avgPoints") + 0.4 * g("avgFieldGoalsMade") - 0.7 * g("avgFieldGoalsAttempted")
            - 0.4 * (g("avgFreeThrowsAttempted") - g("avgFreeThrowsMade")) + 0.4 * g("avgRebounds")
            + g("avgSteals") + 0.7 * g("avgAssists") + 0.7 * g("avgBlocks") - 0.4 * g("avgFouls") - g("avgTurnovers"))


def value_of(v):
    mins = float(v.get("avgMinutes") or 0)
    if mins < 5:
        return 0.0, 0.0
    gs = game_score(v)
    per36 = gs * 36 / mins
    val = max(0.0, per36 - REPLACEMENT_GS36) * (mins / 36) * POINTS_PER_GS
    return round(min(val, VALUE_CAP), 2), round(gs, 1)


def refresh_values(store, now):
    last = store.get("asOf")
    if last and (now - pull.parse(last)).total_seconds() < VALUE_REFRESH_H * 3600:
        return 0
    season = now.year + 1 if now.month >= 8 else now.year            # ESPN names a season by the year it ends
    try:
        cur = season_rows(season)
    except Exception:  # noqa: BLE001
        cur = {}
    try:
        prev = season_rows(season - 1)
    except Exception as exc:  # noqa: BLE001
        print("nba values", exc)
        prev = {}
    players = {}
    for pid in set(cur) | set(prev):
        c, p = cur.get(pid), prev.get(pid)
        use, which = (c, season) if c and float(c.get("gamesPlayed") or 0) >= MIN_GAMES else (p or c, season - 1 if p else season)
        if not use:
            continue
        val, gs = value_of(use)
        players[pid] = {"name": use.get("name"), "value": val, "gameScore": gs,
                        "minutes": round(float(use.get("avgMinutes") or 0), 1),
                        "games": int(float(use.get("gamesPlayed") or 0)), "season": which}
    if players:
        store["players"] = players
        store["asOf"] = pull.iso(now)
    return len(players)


# ---------- status history ----------

def update_history(hist, feed, now):
    current = {}
    for team in feed.get("injuries") or []:
        tname = team.get("displayName")
        for item in team.get("injuries") or []:
            ath = item.get("athlete") or {}
            pid = espn_id(ath)
            if not pid:
                continue
            w = weight(item.get("status"), item.get("shortComment"))
            current[str(pid)] = {"name": ath.get("displayName"), "team": tname, "status": item.get("status"),
                                 "weight": w, "note": item.get("shortComment")}
    players = hist.setdefault("players", {})
    changes = 0
    for pid, info in current.items():
        p = players.setdefault(pid, {"timeline": []})
        p.update(name=info["name"], team=info["team"], note=info["note"])
        if not p["timeline"] or p["timeline"][-1][1] != info["weight"]:
            p["timeline"].append([pull.iso(now), info["weight"], info["status"]])
            changes += 1
    for pid, p in players.items():
        if pid not in current and p.get("timeline") and p["timeline"][-1][1] != 0.0:
            p["timeline"].append([pull.iso(now), 0.0, "Active"])
            changes += 1
    hist.setdefault("trackingSince", pull.iso(now))
    hist["asOf"] = pull.iso(now)
    return changes


def weight_at(timeline, when):
    if not timeline:
        return 0.0
    seen = [w for t, w, *_ in timeline if t <= when]
    return seen[-1] if seen else timeline[0][1]


def team_news(team, hist, values, open_time, now):
    spread = total = 0.0
    items = []
    for pid, p in (hist.get("players") or {}).items():
        if mascot(p.get("team")) != mascot(team):
            continue
        v = (values.get(pid) or {}).get("value", 0.0)
        if v < MIN_VALUE:
            continue
        tl = p.get("timeline") or []
        then, cur = weight_at(tl, open_time), weight_at(tl, now)
        d = cur - then
        if not d:
            continue
        spread += d * v
        total -= d * v * TOTAL_SHARE
        items.append(f"{p['name']} ({mascot(team).title()}, worth {v:g}): weight {then:g} at the open, {cur:g} now, "
                     f"{d * v:+.2f} spread, {-d * v * TOTAL_SHARE:+.2f} total")
    return spread, total, items


def main(dry=False):
    now_dt = datetime.now(timezone.utc)
    now = pull.iso(now_dt)
    hist = pull.load(HISTORY, {})
    store = pull.load(VALUES, {})
    try:
        feed = fetch(FEED)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"pattern": PATTERN, "sport": "NBA", "error": f"injury feed: {exc}"}))
        return
    changes = update_history(hist, feed, now_dt)
    refreshed = refresh_values(store, now_dt)
    values = store.get("players") or {}
    ledger = pull.load(pull.LEDGER, {"rows": []})
    horizon = pull.iso(now_dt + timedelta(days=3))
    to_read = []
    for row in ledger.get("rows") or []:
        if row.get("sport") != "NBA" or row.get("market") not in ("spread", "total"):
            continue
        if not row.get("commence") or not (now < row["commence"] <= horizon):
            continue
        open_line, open_time = row.get("openLine"), row.get("openTime")
        if not isinstance(open_line, (int, float)) or pull.missing(open_time):
            continue
        hs, ht, hi = team_news(row.get("home"), hist, values, open_time, now)
        as_, at, ai = team_news(row.get("away"), hist, values, open_time, now)
        items = hi + ai
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
        sig = " | ".join(items)
        if row.get("newsLagSig") == sig:
            continue
        to_read.append((row, fair, sig + ". " + fair_text, sig))

    if dry:
        for row, fair, reason, _ in to_read:
            print(f"WOULD READ {row['id']} market {(row.get('lastSnap') or {}).get('line')} | {reason}")
    else:
        pull.save(HISTORY, hist)
        pull.save(VALUES, store)
        for row, _, _, sig in to_read:
            row["newsLagSig"] = sig
            row["injury"] = sig
        pull.save(pull.LEDGER, ledger)
        if "NBA" not in pull.READ:
            pull.READ = pull.READ + ["NBA"]     # scripted NBA reads only
        for row, fair, reason, _ in to_read:
            args = Namespace(id=row["id"], fair=f"{fair:.2f}", confidence="medium", reason=reason,
                             falsifier="The line closes at or past the fair number on the other side, "
                                       "or a status changes back before tip-off.",
                             pattern=PATTERN, stake="0.5", big=True, by="injury_nba.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"pattern": PATTERN, "sport": "NBA", "statusChanges": changes, "valuesRefreshed": refreshed,
                      "reads": len(to_read), "tracked": len(hist.get("players") or {}),
                      "trackingSince": hist.get("trackingSince"), "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
