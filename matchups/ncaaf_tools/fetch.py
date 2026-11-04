#!/usr/bin/env python3
"""Fetch 2026 FBS scoreboards and completed-game summaries (play-by-play) from ESPN, cached to disk."""
import json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

D = Path(__file__).resolve().parent / "cache"
D.mkdir(exist_ok=True)
SB = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=80&week={w}&limit=300&dates=2026&seasontype=2"
SUM = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event={e}"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "EDGE desk"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as ex:
            err = ex
    raise err


games = {}
for w in range(1, 12):
    d = get(SB.format(w=w))
    for e in d.get("events", []):
        c = e["competitions"][0]
        games[e["id"]] = {"id": e["id"], "week": w, "date": e["date"], "name": e["name"],
                          "done": c["status"]["type"]["completed"], "neutral": c.get("neutralSite", False),
                          "teams": {t["homeAway"]: {"id": t["team"]["id"], "ab": t["team"]["abbreviation"],
                                                     "name": t["team"]["displayName"],
                                                     "score": t.get("score"),
                                                     "conf": t["team"].get("conferenceId")} for t in c["competitors"]}}
json.dump(games, open(D / "games.json", "w"))
todo = [g["id"] for g in games.values() if g["done"] and not (D / f"{g['id']}.json").exists()]
print(len(games), "games,", sum(g["done"] for g in games.values()), "done,", len(todo), "to fetch")


def one(eid):
    try:
        s = get(SUM.format(e=eid))
        keep = {k: s.get(k) for k in ("drives", "boxscore", "header", "pickcenter", "gameInfo", "scoringPlays")}
        json.dump(keep, open(D / f"{eid}.json", "w"))
        return 1
    except Exception as ex:
        print("fail", eid, ex, file=sys.stderr)
        return 0


with ThreadPoolExecutor(16) as ex:
    print(sum(ex.map(one, todo)), "fetched")
