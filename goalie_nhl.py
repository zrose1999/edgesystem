#!/usr/bin/env python3
"""EDGE NHL goalie news (v1). Tracks ESPN's probable starting goalies with this desk's own first-seen times and
stamps the goalie-news pattern when the starter changes after the open. No analyst judgment.

  python3 goalie_nhl.py          update goalie history, stamp reads
  python3 goalie_nhl.py --dry    show what would be stamped, write nothing

Sources (free, no key): ESPN NHL scoreboard (probable starters, 'expected' or 'confirmed'; past games keep the
confirmed starter); MoneyPuck goalie season summaries (goals saved above expected, GSAx).

Goalie quality q: GSAx per 60 minutes, this season plus last season (weighted LAST_WEIGHT), shrunk toward
league average with SHRINK_H hours of average play. Unknown goalies (call-ups) get UNKNOWN_Q.
Team's No. 1: the goalie with the most confirmed starts in the team's last 10 games (tracked here), until a
team has 5, MoneyPuck's games played this season, then last season.

Why (backtest, 2025-26, 1,018 games, DraftKings open and close from ESPN, starters from NHL boxscores, quality
from the season before, so no look-ahead): the home moneyline moved 1.85 points of win probability per goal of
quality gap between the starter and the team's No. 1 (se 0.29), and the close priced it (no edge left against
the close). Totals moved 0.12 goals down per goal of combined gap (se 0.05).

The read (sizing.md rule): fair = the open + only the goalie news first seen after the open.
  moneyline: fair HOME win prob = open no-vig prob + PROB_PER_GOAL x (change in home q - change in away q)
  total (only while the line is still the open line): fair P(over) = open no-vig P(over)
      - Poisson pmf(floor(line); line) x REPEAT x (change in home q + change in away q)
An 'expected' starter counts EXPECTED_WEIGHT; 'confirmed' counts fully. All values are starting values.
"""

import csv
import io
import json
import math
import sys
import unicodedata
import urllib.request
from argparse import Namespace
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fair as fairlib
import pull

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "stats" / "nhl_goalies.json"
PATTERN = "goalie-news"
BOARD = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates={d}"
MP = "https://moneypuck.com/moneypuck/playerData/seasonSummary/{y}/regular/goalies.csv"
SHRINK_H = 10.0
LAST_WEIGHT = 0.7
UNKNOWN_Q = -0.15
REPEAT = 0.35               # share of a GSAx gap that carries into the next game (goalie results are noisy)
PROB_PER_GOAL = 0.06        # win probability per goal of expected goal difference (0.166) x REPEAT, rounded
EXPECTED_WEIGHT = 0.6
WINDOW_H = 30
LOOKBACK_DAYS = 21
MIN_PROB = 0.01


def fetch(url, as_json=True):
    req = urllib.request.Request(url, headers={"User-Agent": "EDGE desk"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", "replace")
    return json.loads(body) if as_json else body


def norm(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return " ".join(s.replace(".", " ").replace("-", " ").split())


def mascot(team):
    return norm(team).split()[-1] if team else ""


# ---------- quality ----------

def mp_season(y):
    rows = {}
    for r in csv.DictReader(io.StringIO(fetch(MP.format(y=y), as_json=False))):
        if r.get("situation") != "all":
            continue
        rows[norm(r["name"])] = {"gsax": float(r["xGoals"]) - float(r["goals"]), "hours": float(r["icetime"]) / 3600,
                                 "games": int(float(r["games_played"])), "team": r["team"]}
    return rows


def refresh_quality(store, now):
    if store.get("qualityAsOf") and (now - pull.parse(store["qualityAsOf"])).total_seconds() < 20 * 3600:
        return 0
    season = now.year if now.month >= 9 else now.year - 1        # MoneyPuck names a season by the year it starts
    try:
        cur = mp_season(season)
    except Exception:  # noqa: BLE001
        cur = {}
    try:
        last = mp_season(season - 1)
    except Exception as exc:  # noqa: BLE001
        print("moneypuck", exc)
        last = {}
    q = {}
    for name in set(cur) | set(last):
        c, l = cur.get(name, {}), last.get(name, {})
        g = c.get("gsax", 0) + LAST_WEIGHT * l.get("gsax", 0)
        h = c.get("hours", 0) + LAST_WEIGHT * l.get("hours", 0)
        q[name] = {"q": round(g / (h + SHRINK_H), 3), "gamesThis": c.get("games", 0), "gamesLast": l.get("games", 0),
                   "teamThis": c.get("team"), "teamLast": l.get("team")}
    if q:
        store["quality"] = q
        store["qualityAsOf"] = pull.iso(now)
    return len(q)


def quality(store, name):
    v = (store.get("quality") or {}).get(norm(name))
    return v["q"] if v else UNKNOWN_Q


# ---------- ESPN boards ----------

def read_board(day):
    d = fetch(BOARD.format(d=day.strftime("%Y%m%d")))
    out = []
    for e in d.get("events") or []:
        c = (e.get("competitions") or [{}])[0]
        g = {"id": e["id"], "date": e.get("date"), "final": c.get("status", {}).get("type", {}).get("completed", False)}
        for t in c.get("competitors") or []:
            side = t.get("homeAway")
            g[side] = t.get("team", {}).get("displayName")
            probs = [p for p in t.get("probables") or [] if p.get("athlete")]
            g[side + "G"] = ((probs[0]["athlete"].get("displayName"), (probs[0].get("status") or {}).get("type"))
                             if probs else None)
        out.append(g)
    return out


def update(store, now):
    store.setdefault("trackingSince", pull.iso(now))
    games, starts, done = store.setdefault("games", {}), store.setdefault("starts", {}), set(store.get("doneDates") or [])
    changes = 0
    today = (now - timedelta(hours=6)).date()
    for i in range(-LOOKBACK_DAYS, 2):
        day = today + timedelta(days=i)
        key = day.isoformat()
        if i < -1 and key in done:
            continue
        try:
            board = read_board(day)
        except Exception as exc:  # noqa: BLE001
            print("espn board", key, exc)
            continue
        for g in board:
            if g["final"]:
                for side in ("home", "away"):
                    if g.get(side + "G") and g[side + "G"][1] == "confirmed":
                        lst = starts.setdefault(g[side], [])
                        if not any(x[0] == g["id"] for x in lst):
                            lst.append([g["id"], g["date"], g[side + "G"][0]])
                            lst.sort(key=lambda x: x[1])
                continue
            rec = games.setdefault(g["id"], {"home": g.get("home"), "away": g.get("away"), "commence": g.get("date"),
                                             "timeline": {"home": [], "away": []}})
            for side in ("home", "away"):
                cur = g.get(side + "G")
                tl = rec["timeline"][side]
                state = [cur[0], cur[1]] if cur else [None, None]
                if not tl or tl[-1][1:] != state:
                    tl.append([pull.iso(now)] + state)
                    changes += 1
        if i < -1 and all(g["final"] for g in board):
            done.add(key)
    store["doneDates"] = sorted(done)[-60:]
    cutoff = pull.iso(now - timedelta(days=3))
    store["games"] = {k: v for k, v in games.items() if (v.get("commence") or "") >= cutoff}
    for team in starts:
        starts[team] = starts[team][-20:]
    store["asOf"] = pull.iso(now)
    return changes


def number_one(store, team):
    recent = [x[2] for x in (store.get("starts") or {}).get(team, [])][-10:]
    if len(recent) >= 5:
        return Counter(recent).most_common(1)[0][0]
    m = mascot(team)
    best = None
    for key in ("gamesThis", "gamesLast"):
        tkey = "teamThis" if key == "gamesThis" else "teamLast"
        cands = [(v[key], n) for n, v in (store.get("quality") or {}).items()
                 if v.get(tkey) and TEAM_ABBR.get(v[tkey]) == m and v[key] > 0]
        if cands and (key == "gamesLast" or max(cands)[0] >= 5):
            best = max(cands)[1]
            break
    return best


TEAM_ABBR = {"ANA": "ducks", "ARI": "coyotes", "BOS": "bruins", "BUF": "sabres", "CGY": "flames", "CAR": "hurricanes",
             "CHI": "blackhawks", "COL": "avalanche", "CBJ": "jackets", "DAL": "stars", "DET": "wings", "EDM": "oilers",
             "FLA": "panthers", "LAK": "kings", "L.A": "kings", "MIN": "wild", "MTL": "canadiens", "NSH": "predators",
             "NJD": "devils", "N.J": "devils", "NYI": "islanders", "NYR": "rangers", "OTT": "senators", "PHI": "flyers",
             "PIT": "penguins", "SJS": "sharks", "S.J": "sharks", "SEA": "kraken", "STL": "blues", "TBL": "lightning",
             "T.B": "lightning", "TOR": "leafs", "UTA": "mammoth", "VAN": "canucks", "VGK": "knights", "WSH": "capitals",
             "WPG": "jets"}


def q_entry(store, entry, fallback):
    """Effective quality of a timeline entry [time, name, status]; an 'expected' starter is blended with the No. 1."""
    _, name, status = entry
    qf = quality(store, fallback) if fallback else 0.0
    if not name:
        return qf
    w = 1.0 if status == "confirmed" else EXPECTED_WEIGHT
    return w * quality(store, name) + (1 - w) * qf


def team_change(store, rec, side, open_time):
    """Change in effective goalie quality since the open, and a note. Only news first seen after the open."""
    tl = rec["timeline"][side]
    if not tl or not tl[-1][1]:
        return 0.0, None
    team = rec[side]
    no1 = number_one(store, team)
    before = [e for e in tl if e[0] <= open_time]
    if before:
        base = q_entry(store, before[-1], no1)
        base_txt = f"{before[-1][1] or 'none listed'} ({before[-1][2] or '-'}) at the open"
    elif store["trackingSince"] > open_time:
        return 0.0, None                       # tracking began after the open: what we first saw may have been priced
    else:
        base = quality(store, no1) if no1 else 0.0
        base_txt = f"No. 1 {no1 or 'unknown'} assumed at the open"
    now_q = q_entry(store, tl[-1], no1)
    d = now_q - base
    if abs(d) < 1e-9:
        return 0.0, None
    return d, (f"{mascot(team).title()}: {base_txt}, now {tl[-1][1]} ({tl[-1][2]}), "
               f"GSAx/60 {base:+.2f} to {now_q:+.2f}")


def poisson_pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def match_event(store, row):
    hm, am = mascot(row.get("home")), mascot(row.get("away"))
    for eid, rec in (store.get("games") or {}).items():
        if mascot(rec.get("home")) == hm and mascot(rec.get("away")) == am and rec.get("commence") and row.get("commence"):
            if abs((pull.parse(rec["commence"].replace("Z", ":00Z") if len(rec["commence"]) == 17 else rec["commence"])
                    - pull.parse(row["commence"])).total_seconds()) < 12 * 3600:
                return rec
    return None


def main(dry=False):
    now_dt = datetime.now(timezone.utc)
    now = pull.iso(now_dt)
    store = pull.load(HISTORY, {})
    refreshed = refresh_quality(store, now_dt)
    changes = update(store, now_dt)
    ledger = pull.load(pull.LEDGER, {"rows": []})
    horizon = pull.iso(now_dt + timedelta(hours=WINDOW_H))
    todo = []
    for row in ledger.get("rows") or []:
        if row.get("sport") != "NHL" or row.get("market") not in ("h2h", "total"):
            continue
        if not row.get("commence") or not (now < row["commence"] <= horizon):
            continue
        osnap, open_time = row.get("openSnap"), row.get("openTime")
        if not osnap or pull.missing(open_time):
            continue
        rec = match_event(store, row)
        if not rec:
            continue
        dh, nh = team_change(store, rec, "home", open_time)
        da, na = team_change(store, rec, "away", open_time)
        notes = [n for n in (nh, na) if n]
        if not notes:
            continue
        if row["market"] == "h2h":
            if "home" not in osnap or "away" not in osnap:
                continue
            keys = [k for k in ("home", "away", "draw") if k in osnap]
            p0 = fairlib.probs(osnap, keys)["home"]
            delta = PROB_PER_GOAL * (dh - da)
            fair = min(max(p0 + delta, 0.02), 0.98)
            text = f"Open home win {p0:.3f}, goalie change {delta:+.3f}, fair {fair:.3f}."
        else:
            line = osnap.get("line")
            if line is None or (row.get("lastSnap") or {}).get("line") != line or "over" not in osnap:
                continue
            p0 = fairlib.probs(osnap, ["over", "under"])["over"]
            dlam = -REPEAT * (dh + da)
            delta = poisson_pmf(math.floor(line), line) * dlam
            fair = min(max(p0 + delta, 0.02), 0.98)
            text = f"Open over {line:g} {p0:.3f}, expected goals {dlam:+.2f}, fair over {fair:.3f}."
        if abs(delta) < MIN_PROB:
            continue
        sig = " | ".join(notes)
        if row.get("goalieSig") == sig:
            continue
        todo.append((row, fair, sig + ". " + text, sig))

    if dry:
        for row, fair, reason, _ in todo:
            print(f"WOULD READ {row['id']} | {reason}")
    else:
        pull.save(HISTORY, store)
        for row, _, _, sig in todo:
            row["goalieSig"] = sig
        pull.save(pull.LEDGER, ledger)
        if "NHL" not in pull.READ:
            pull.READ = pull.READ + ["NHL"]     # scripted NHL reads only
        for row, fair, reason, _ in todo:
            args = Namespace(id=row["id"], fair=f"{fair:.3f}", confidence="medium", reason=reason,
                             falsifier="The price closes at or past the fair number on the other side, "
                                       "or the starter changes back before puck drop.",
                             pattern=PATTERN, stake="0", big=True, by="goalie_nhl.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"pattern": PATTERN, "sport": "NHL", "goalieChanges": changes, "qualityRefreshed": refreshed,
                      "reads": len(todo), "trackingSince": store.get("trackingSince"), "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
