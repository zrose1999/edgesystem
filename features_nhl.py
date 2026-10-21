#!/usr/bin/env python3
"""EDGE NHL feature store. Every pre-game data point the desk can get, for every past game (training) and every
upcoming game (live), in the same form. The learner (learner.py) decides which ones matter and how much.

  python3 features_nhl.py refresh    pull MoneyPuck team game logs and goalie seasons, NHL starters (daily)
  python3 features_nhl.py history    build stats/features/nhl_history.json (features + open-to-close targets)

Data (all free): MoneyPuck team game-by-game (xG, shots, danger, power play, penalty kill, score-adjusted xG),
MoneyPuck goalie seasons (GSAx), NHL API boxscores (who actually started in goal), ESPN schedule and DraftKings
open/close lines (stats/nhl_games.json), the stats_more.py ratings (walk-forward), and the market itself.
Nothing here is a strategy; these are inputs.
"""

import csv
import io
import json
import math
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "stats" / "features"
TEAMS_FILE = STORE / "nhl_team_games.json"
GOALIES_FILE = STORE / "nhl_goalie_seasons.json"
STARTERS_FILE = STORE / "nhl_starters.json"
HIST_FILE = STORE / "nhl_history.json"
MP_TEAM = "https://moneypuck.com/moneypuck/playerData/careers/gameByGame/regular/teams/{t}.csv"
MP_GOALIE = "https://moneypuck.com/moneypuck/playerData/seasonSummary/{y}/regular/goalies.csv"
NHL_API = "https://api-web.nhle.com/v1"
ABBR = {"ANA": "ducks", "ARI": "coyotes", "BOS": "bruins", "BUF": "sabres", "CGY": "flames", "CAR": "hurricanes",
        "CHI": "blackhawks", "COL": "avalanche", "CBJ": "jackets", "DAL": "stars", "DET": "wings", "EDM": "oilers",
        "FLA": "panthers", "LAK": "kings", "MIN": "wild", "MTL": "canadiens", "NSH": "predators", "NJD": "devils",
        "NYI": "islanders", "NYR": "rangers", "OTT": "senators", "PHI": "flyers", "PIT": "penguins", "SJS": "sharks",
        "SEA": "kraken", "STL": "blues", "TBL": "lightning", "TOR": "leafs", "UTA": "mammoth", "VAN": "canucks",
        "VGK": "knights", "WSH": "capitals", "WPG": "jets"}
MASCOT_TO_ABBR = {v: k for k, v in ABBR.items()}
MASCOT_TO_ABBR.update({"club": "UTA", "hockey club": "UTA"})
SHRINK_H = 10.0


def get(url, as_json=True):
    req = urllib.request.Request(url, headers={"User-Agent": "EDGE desk"})
    with urllib.request.urlopen(req, timeout=90) as r:
        b = r.read().decode("utf-8", "replace")
    return json.loads(b) if as_json else b


def abbr_of(name):
    words = (name or "").lower().replace(".", "").split()
    if not words:
        return None
    if words[-1] == "club" and "utah" in words:
        return "UTA"
    return MASCOT_TO_ABBR.get(words[-1])


def parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def game_day(s):
    return (parse_dt(s) - timedelta(hours=6)).date()


# ---------------- raw data ----------------

KEEP = ["xGoalsFor", "xGoalsAgainst", "goalsFor", "goalsAgainst", "shotsOnGoalFor", "shotsOnGoalAgainst",
        "highDangerShotsFor", "highDangerShotsAgainst", "scoreVenueAdjustedxGoalsFor",
        "scoreVenueAdjustedxGoalsAgainst", "shotAttemptsFor", "shotAttemptsAgainst", "penaltiesFor", "penaltiesAgainst"]


def refresh_team_games(min_season=2023):
    out = {}
    import time
    for t in ABBR:
        time.sleep(1)
        try:
            text = get(MP_TEAM.format(t=t), as_json=False)
        except Exception as exc:  # noqa: BLE001
            print("moneypuck team", t, exc)
            continue
        games = {}
        for r in csv.DictReader(io.StringIO(text)):
            if int(r["season"]) < min_season:
                continue
            g = games.setdefault(r["gameId"], {"date": r["gameDate"], "home": r["home_or_away"] == "HOME",
                                               "opp": r["opposingTeam"], "season": int(r["season"])})
            sit = r["situation"]
            if sit == "all":
                g.update({k: float(r[k] or 0) for k in KEEP})
            elif sit == "5on4":
                g["ppxg"] = float(r["xGoalsFor"] or 0)
                g["ppgoals"] = float(r["goalsFor"] or 0)
            elif sit == "4on5":
                g["pkxga"] = float(r["xGoalsAgainst"] or 0)
        out[t] = sorted(games.values(), key=lambda g: g["date"])
    if out:
        STORE.mkdir(parents=True, exist_ok=True)
        TEAMS_FILE.write_text(json.dumps(out, separators=(",", ":")))
    return sum(len(v) for v in out.values())


def refresh_goalies(years):
    out = {}
    import time
    for y in years:
        time.sleep(3)                     # MoneyPuck rate-limits bursts
        try:
            text = get(MP_GOALIE.format(y=y), as_json=False)
        except Exception as exc:  # noqa: BLE001
            print("moneypuck goalies", y, exc)
            continue
        out[str(y)] = {r["playerId"]: {"name": r["name"], "gsax": float(r["xGoals"]) - float(r["goals"]),
                                       "hours": float(r["icetime"]) / 3600, "team": r["team"]}
                       for r in csv.DictReader(io.StringIO(text)) if r["situation"] == "all"}
    if out:
        old = json.loads(GOALIES_FILE.read_text()) if GOALIES_FILE.exists() else {}
        old.update(out)
        GOALIES_FILE.write_text(json.dumps(old, separators=(",", ":")))


def refresh_starters(season_codes):
    old = json.loads(STARTERS_FILE.read_text()) if STARTERS_FILE.exists() else {}
    for code in season_codes:
        ids = set()
        for t in ABBR:
            if t == "ARI":
                continue
            try:
                for g in get(f"{NHL_API}/club-schedule-season/{t}/{code}").get("games") or []:
                    if g.get("gameType") == 2 and g.get("gameState") in ("OFF", "FINAL") and str(g["id"]) not in old:
                        ids.add(g["id"])
            except Exception as exc:  # noqa: BLE001
                print("nhl schedule", t, exc)
        for gid in sorted(ids):
            try:
                d = get(f"{NHL_API}/gamecenter/{gid}/boxscore")
            except Exception:  # noqa: BLE001
                continue
            p = d.get("playerByGameStats") or {}
            rec = {"date": d.get("startTimeUTC"), "home": d["homeTeam"]["abbrev"], "away": d["awayTeam"]["abbrev"]}
            for side, key in (("homeTeam", "homeG"), ("awayTeam", "awayG")):
                st = [g for g in (p.get(side) or {}).get("goalies", []) if g.get("starter")]
                rec[key] = [str(st[0]["playerId"]), st[0]["name"]["default"]] if st else None
            old[str(gid)] = rec
    STARTERS_FILE.write_text(json.dumps(old, separators=(",", ":")))
    return len(old)


# ---------------- feature computation ----------------

class TeamHistory:
    def __init__(self, team_games):
        self.games = {t: [(g["date"], g) for g in gs] for t, gs in team_games.items()}

    def before(self, team, ymd, n=None, season=None):
        gs = [g for d, g in self.games.get(team, []) if d < ymd and (season is None or g["season"] == season)]
        return gs[-n:] if n else gs


def agg(gs, prefix):
    if not gs:
        return {}
    s = lambda k: sum(g.get(k, 0.0) for g in gs)
    n = len(gs)
    xgf, xga, gf, ga = s("xGoalsFor"), s("xGoalsAgainst"), s("goalsFor"), s("goalsAgainst")
    sf, sa = s("shotsOnGoalFor"), s("shotsOnGoalAgainst")
    out = {
        f"{prefix}_xgpct": xgf / (xgf + xga) if xgf + xga else 0.5,
        f"{prefix}_svxgpct": (s("scoreVenueAdjustedxGoalsFor") / max(s("scoreVenueAdjustedxGoalsFor") + s("scoreVenueAdjustedxGoalsAgainst"), 1e-9)),
        f"{prefix}_cfpct": s("shotAttemptsFor") / max(s("shotAttemptsFor") + s("shotAttemptsAgainst"), 1e-9),
        f"{prefix}_luck": ((gf - xgf) - (ga - xga)) / n,
        f"{prefix}_gd": (gf - ga) / n,
        f"{prefix}_pdo": (gf / sf if sf else 0.09) + (1 - ga / sa if sa else 0.91),
        f"{prefix}_hdpct": s("highDangerShotsFor") / max(s("highDangerShotsFor") + s("highDangerShotsAgainst"), 1e-9),
        f"{prefix}_pp": s("ppxg") / n, f"{prefix}_pk": s("pkxga") / n,
        f"{prefix}_pen": (s("penaltiesAgainst") - s("penaltiesFor")) / n,
        f"{prefix}_xgf": xgf / n, f"{prefix}_xga": xga / n,
        f"{prefix}_win": sum(1 for g in gs if g.get("goalsFor", 0) > g.get("goalsAgainst", 0)) / n,
    }
    return out


def goalie_quality(goalies, pid, season):
    """Prior two seasons of GSAx per 60, shrunk; no information from the game's own season (no leakage)."""
    g, h = 0.0, 0.0
    for y, w in ((season - 1, 1.0), (season - 2, 0.5)):
        rec = (goalies.get(str(y)) or {}).get(str(pid))
        if rec:
            g += w * rec["gsax"]
            h += w * rec["hours"]
    return g / (h + SHRINK_H), h


def novig2(a, b):
    def imp(p):
        return 100 / (p + 100) if p > 0 else -p / (-p + 100)
    x, y = imp(a), imp(b)
    s = x + y
    over = s - 1
    return x / s - 0.0 * over      # two-way: proportional and Shin agree to within a hair at these margins


def logit(p):
    p = min(max(p, 0.01), 0.99)
    return math.log(p / (1 - p))


def features_for(home, away, when_iso, th, starters_index, goalies, sched_days, open_home, open_total, open_over,
                 model_p=None, model_total=None, home_g=None, away_g=None):
    """One game's feature dict. home/away are MoneyPuck abbreviations. when_iso is the start time."""
    day = game_day(when_iso)
    ymd = day.strftime("%Y%m%d")
    season = day.year if day.month >= 9 else day.year - 1
    f = {"open_home_logit": logit(open_home), "open_home": open_home}
    if open_total is not None:
        f["open_total"] = open_total
    if open_over is not None:
        f["open_over"] = open_over
    for side, t in (("h", home), ("a", away)):
        for n, tag in ((5, "l5"), (10, "l10"), (25, "l25")):
            f.update(agg(th.before(t, ymd, n=n), f"{side}_{tag}"))
        f.update(agg(th.before(t, ymd, season=season), f"{side}_ssn"))
        f[f"{side}_gp"] = len(th.before(t, ymd, season=season))
        days = sorted(d for d in sched_days.get(t, []) if d < day)
        f[f"{side}_rest"] = min((day - days[-1]).days, 5) if days else 5
        f[f"{side}_b2b"] = 1.0 if days and (day - days[-1]).days == 1 else 0.0
        f[f"{side}_g4"] = float(sum(1 for d in days if (day - d).days <= 4))
        f[f"{side}_g7"] = float(sum(1 for d in days if (day - d).days <= 7))
    # goalies: actual starter (history) or confirmed/expected probable (live), vs the team's No. 1
    for side, t, g in (("h", home, home_g), ("a", away, away_g)):
        recent = [s.get(f"{'home' if s['home'] == t else 'away'}G") for s in starters_index.get(t, []) if (s.get("date") or "") < when_iso][-10:]
        recent = [r[0] for r in recent if r]
        no1 = max(set(recent), key=recent.count) if recent else None
        q_no1 = goalie_quality(goalies, no1, season)[0] if no1 else 0.0
        if g:
            q, hrs = goalie_quality(goalies, g, season)
            f[f"{side}_gq"] = q
            f[f"{side}_gq_vs_no1"] = q - q_no1
            f[f"{side}_backup"] = 0.0 if g == no1 else 1.0
            f[f"{side}_g_hours"] = hrs
    for k in list(f):
        if k.startswith("h_") and "a_" + k[2:] in f:
            f["d_" + k[2:]] = f[k] - f["a_" + k[2:]]
    f["dow"] = float(day.weekday())
    f["month"] = float(day.month)
    if model_p is not None:
        f["model_gap"] = model_p - open_home
    if model_total is not None and open_total is not None:
        f["model_total_gap"] = model_total - open_total
    return f


def build_history():
    import stats_more as sm
    team_games = json.loads(TEAMS_FILE.read_text())
    goalies = json.loads(GOALIES_FILE.read_text())
    starters = json.loads(STARTERS_FILE.read_text())
    th = TeamHistory(team_games)
    st_index = defaultdict(list)
    for gid, s in sorted(starters.items(), key=lambda kv: kv[1].get("date") or ""):
        st_index[s["home"]].append(s)
        st_index[s["away"]].append(s)
    st_by_day = {(game_day(s["date"]).isoformat(), s["home"]): s for s in starters.values() if s.get("date")}
    games = list(json.loads((ROOT / "stats" / "nhl_games.json").read_text())["games"].values())
    sched = defaultdict(list)
    for g in games:
        for side in ("home", "away"):
            a = abbr_of(g[side])
            if a:
                sched[a].append(game_day(g["date"]))
    model_p = {}
    try:
        for g, p in sm.backtest(games, sm.CONFIG["NHL"]):
            model_p[g["id"]] = (p.get("pHome"), (p.get("homeScore") or 0) + (p.get("awayScore") or 0))
    except Exception as exc:  # noqa: BLE001
        print("ratings backtest", exc)
    rows = []
    for g in sorted(games, key=lambda g: g["date"]):
        L = g.get("lines") or {}
        if not g.get("final") or not all(L.get(k) for k in ("mlHomeOpen", "mlAwayOpen", "mlHomeClose", "mlAwayClose")):
            continue
        h, a = abbr_of(g["home"]), abbr_of(g["away"])
        if not h or not a:
            continue
        po = novig2(L["mlHomeOpen"], L["mlAwayOpen"])
        pc = novig2(L["mlHomeClose"], L["mlAwayClose"])
        oo = oc = None
        if all(L.get(k) for k in ("overOpenOdds", "underOpenOdds", "overCloseOdds", "underCloseOdds")) \
                and L.get("totalOpen") is not None and L.get("totalClose") is not None:
            # Every game, with the close converted to the opening line (scan.over_at_line, Poisson). Keeping only games
            # whose line held is a look-ahead filter that manufactures reversion (2026-10-21).
            import scan
            oo = novig2(L["overOpenOdds"], L["underOpenOdds"])
            oc = scan.over_at_line("NHL", novig2(L["overCloseOdds"], L["underCloseOdds"]), L["totalClose"], L["totalOpen"])
        s = st_by_day.get((game_day(g["date"]).isoformat(), h)) or {}
        mp = model_p.get(g["id"], (None, None))
        f = features_for(h, a, g["date"], th, st_index, goalies, sched, po, L.get("totalOpen"), oo, mp[0], mp[1],
                         (s.get("homeG") or [None])[0], (s.get("awayG") or [None])[0])
        rows.append({"id": g["id"], "date": g["date"], "home": h, "away": a, "f": f,
                     "y_ml": pc - po, "y_over": (oc - oo) if oo is not None else None,
                     "won": 1.0 if g["hs"] > g["as"] else 0.0, "close_home": pc})
    HIST_FILE.write_text(json.dumps({"built": datetime.now(timezone.utc).isoformat(), "rows": rows}, separators=(",", ":")))
    return len(rows)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "history"
    if cmd == "refresh":
        now = datetime.now(timezone.utc)
        season = now.year if now.month >= 9 else now.year - 1
        print("team games", refresh_team_games())
        refresh_goalies([season - 2, season - 1, season])
        print("starters", refresh_starters([f"{season}{season + 1}"]))
    else:
        print("history rows", build_history())
