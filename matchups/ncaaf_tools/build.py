#!/usr/bin/env python3
"""EDGE matchup notes for one college football game, in the same shape as matchups/latest_nfl.json.

  python3 build.py <espn_event_id> <out.json>

Data: ESPN play-by-play for every completed 2026 FBS game (fetch.py), ESPN rosters for positions,
EDGE's stats/ncaaf_games.json for 2025 closing lines, EDGE memory/log for the CLV check.
Differences from the NFL desk, all for college football:
  - Garbage time removed (margin > 38 in the 1st half, > 28 in the 3rd, > 22 in the 4th) and overtime dropped.
  - Unit numbers are opponent-adjusted (schedules in college differ far more than in the NFL); last-3 is
    adjusted the same way, using each opponent's full-season rating.
  - EPA comes from an expected-points table fitted on this season's FBS plays (next-score method).
  - Ranks run over every FBS team (about 136), not 32.
  - No air yards in ESPN's feed: "deep" throws are the ones ESPN marks deep; pressure = sacks + hurries + hits.
"""
import json, math, re, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
C = HERE / "cache"
REPO = Path.home() / "edgesystem"
sys.path.insert(0, str(REPO))
import matchups as MX  # reuse the NFL desk's suggestion and prop logic

EVENT = sys.argv[1]
OUTP = Path(sys.argv[2])
GAMES = json.load(open(C / "games.json"))
ROSTERS = json.load(open(C / "rosters.json"))
FBS_IDS = set(ROSTERS)

UNITS = MX.UNITS
PAIRS = MX.PAIRS

PASS_T = {"Pass Reception", "Pass Incompletion", "Passing Touchdown", "Sack", "Interception", "Pass Interception Return",
          "Interception Return Touchdown", "Pass"}
RUSH_T = {"Rush", "Rushing Touchdown"}
FUM_T = {"Fumble Recovery (Own)", "Fumble Recovery (Opponent)", "Fumble Return Touchdown", "Safety"}
TO_T = {"Interception", "Pass Interception Return", "Interception Return Touchdown", "Fumble Recovery (Opponent)",
        "Fumble Return Touchdown"}


def garbage(period, margin):
    m = abs(margin)
    return (period <= 2 and m > 38) or (period == 3 and m > 28) or (period == 4 and m > 22)


def dist_b(d):
    return 0 if d <= 1 else 1 if d <= 3 else 2 if d <= 6 else 3 if d <= 10 else 4


def ytg_b(y):
    return min(int(y) // 5, 19)


# ---------------- load plays ----------------
ABBR, NAME = {}, {}
plays, drives, team_games = [], [], defaultdict(list)
for gid, g in GAMES.items():
    if not g["done"] or not (C / f"{gid}.json").exists():
        continue
    s = json.load(open(C / f"{gid}.json"))
    h, a = g["teams"]["home"], g["teams"]["away"]
    for t in (h, a):
        ABBR[t["id"]], NAME[t["id"]] = t["ab"], t["name"]
    pc = (s.get("pickcenter") or [{}])
    pc = next((p for p in pc if p.get("provider", {}).get("name") == "DraftKings"), pc[0] if pc else {})
    try:
        hsc, asc = float(h["score"]), float(a["score"])
    except (TypeError, ValueError):
        continue
    rec = {"gid": gid, "week": g["week"], "date": g["date"], "home": h["id"], "away": a["id"], "hs": hsc, "as": asc,
           "spread": pc.get("spread"), "total": pc.get("overUnder"), "neutral": g["neutral"]}
    team_games[h["id"]].append(rec)
    team_games[a["id"]].append(rec)
    prev_h = prev_a = 0
    seq = []
    for dv in (s.get("drives") or {}).get("previous", []):
        did = dv.get("id")
        dteam = (dv.get("team") or {}).get("id")
        dplays = []
        for p in dv.get("plays", []):
            hs_, as_ = p.get("homeScore", prev_h), p.get("awayScore", prev_a)
            dh, da = hs_ - prev_h, as_ - prev_a
            per = (p.get("period") or {}).get("number", 1)
            margin_before = prev_h - prev_a
            prev_h, prev_a = hs_, as_
            st, en = p.get("start") or {}, p.get("end") or {}
            x = {"gid": gid, "week": g["week"], "drive": did, "period": per, "type": (p.get("type") or {}).get("text", ""),
                 "text": p.get("text") or "", "yds": p.get("statYardage") or 0, "off": (st.get("team") or {}).get("id"),
                 "down": st.get("down"), "dist": st.get("distance"), "ytg": st.get("yardsToEndzone"),
                 "eteam": (en.get("team") or {}).get("id"), "edown": en.get("down"), "edist": en.get("distance"),
                 "eytg": en.get("yardsToEndzone"), "dh": dh, "da": da, "home": h["id"], "away": a["id"],
                 "garbage": garbage(per, margin_before) or per > 4, "turnover": p.get("isTurnover")}
            seq.append(x)
            dplays.append(x)
        drives.append({"gid": gid, "week": g["week"], "team": dteam, "result": dv.get("result") or "", "plays": dplays,
                       "home": h["id"], "away": a["id"]})
    # next score in the half, from the perspective of each play's offense
    nxt_val, nxt_team = 0, None
    cur_half = None
    for x in reversed(seq):
        half = 1 if x["period"] <= 2 else 2 if x["period"] <= 4 else 3
        if half != cur_half:
            nxt_val, nxt_team, cur_half = 0, None, half
        if x["dh"] > 0 or x["da"] > 0:
            scorer = x["home"] if x["dh"] > 0 else x["away"]
            v = max(x["dh"], x["da"])
            nxt_val, nxt_team = (7 if v >= 6 else v), scorer
        x["ns"] = 0 if nxt_team is None else (nxt_val if nxt_team == x["off"] else -nxt_val)
    plays += seq


def scrimmage(x):
    t, tx = x["type"], x["text"].lower()
    if x["period"] > 4 or not x["off"] or x["down"] in (None, 0) or x["ytg"] in (None,):
        return None
    if "two-point" in tx or "conversion" in tx or "kneel" in tx or "spike" in tx or "no play" in tx:
        return None
    if t in PASS_T:
        return "pass"
    if t in RUSH_T:
        return "rush"
    if t in FUM_T:
        if " pass" in tx or "sacked" in tx:
            return "pass"
        if " rush" in tx or " run" in tx:
            return "rush"
    return None


for x in plays:
    x["kind"] = scrimmage(x)

# ---------------- expected points ----------------
acc = defaultdict(lambda: [0.0, 0])
for x in plays:
    if x["kind"] and not x["garbage"]:
        k = (min(x["down"], 4), dist_b(x["dist"] or 10), ytg_b(x["ytg"]))
        acc[k][0] += x["ns"]
        acc[k][1] += 1


def EP(down, dist, ytg):
    if down in (None, 0) or ytg is None:
        return 0.0
    d, b, y = min(down, 4), dist_b(dist or 10), ytg_b(ytg)
    s = n = 0.0
    for dy, w in ((0, 1.0), (-1, 0.5), (1, 0.5)):
        yy = y + dy
        if 0 <= yy <= 19:
            v = acc.get((d, b, yy))
            if v and v[1]:
                s += w * v[0]
                n += w * v[1]
    if n < 30:   # fall back to down + yardline only
        s2 = sum(v[0] for k, v in acc.items() if k[0] == d and k[2] == y)
        n2 = sum(v[1] for k, v in acc.items() if k[0] == d and k[2] == y)
        return s2 / n2 if n2 else 0.0
    return s / n


for x in plays:
    if not x["kind"]:
        continue
    ep0 = EP(x["down"], x["dist"], x["ytg"])
    my = x["dh"] if x["off"] == x["home"] else x["da"]
    their = x["da"] if x["off"] == x["home"] else x["dh"]
    if my >= 6:
        epa = 7 - ep0
    elif their > 0:
        epa = -(7 if their >= 6 else their) - ep0
    elif x["eteam"] and x["eteam"] != x["off"]:
        epa = -EP(1, 10, x["eytg"] if x["eytg"] is not None else 75) - ep0
    elif x["type"] in TO_T or x["turnover"]:
        epa = -EP(1, 10, 100 - (x["eytg"] or 50)) - ep0
    else:
        epa = EP(x["edown"], x["edist"], x["eytg"]) - ep0 if x["edown"] else -ep0
    x["epa"] = epa

# ---------------- players from play text ----------------
RX_PASSER = re.compile(r"#(\d+) ([A-Z][\w'.\-]*(?: [\w'.\-]+)*?) (?:pass|sacked)")
RX_TARGET = re.compile(r"pass (?:complete|incomplete)[^#]*? to #(\d+) ([A-Z][\w'.\-]*(?: (?:Jr\.|II|III|IV|Sr\.))?)")
RX_RUSH = re.compile(r"#(\d+) ([A-Z][\w'.\-]*(?: (?:Jr\.|II|III|IV|Sr\.))?) rush")
POSG = {"WR": "WR", "TE": "TE", "RB": "RB", "FB": "RB", "QB": "QB"}
BOXJ = {}
for gid in GAMES:
    f = C / f"{gid}.json"
    if not GAMES[gid]["done"] or not f.exists():
        continue
    for tb in ((json.load(open(f)).get("boxscore") or {}).get("players") or []):
        tid_ = tb["team"]["id"]
        for cat in tb.get("statistics", []):
            for at in cat.get("athletes", []):
                a_ = at.get("athlete") or {}
                if a_.get("jersey") and a_.get("displayName"):
                    BOXJ.setdefault((tid_, a_["jersey"]), {"id": a_.get("id"), "name": a_["displayName"], "pos": None})
RIDX = {}
for tid, ro in ROSTERS.items():
    for a in ro or []:
        RIDX.setdefault((tid, a["jersey"]), []).append(a)


def who(tid, jersey, nm):
    c = RIDX.get((tid, jersey)) or []
    parts = (nm or "").replace(".", " ").split()
    parts = [w for w in parts if w not in ("Jr", "Sr", "II", "III", "IV") and len(w) > 1]
    last = parts[-1].lower() if parts else ""
    for a in c:
        if last and last in (a["name"] or "").lower():
            return a
    b = BOXJ.get((tid, jersey))
    if b and last and last in b["name"].lower():
        return b
    return {"id": f"{tid}-{jersey}-{last}", "name": nm, "pos": None}


for x in plays:
    if not x["kind"]:
        continue
    tx = x["text"]
    x["passer"] = x["target"] = x["rusher"] = None
    if x["kind"] == "pass":
        m = RX_PASSER.search(tx)
        if m:
            x["passer"] = who(x["off"], m.group(1), m.group(2))
        m = RX_TARGET.search(tx)
        if m:
            x["target"] = who(x["off"], m.group(1), m.group(2))
    else:
        m = RX_RUSH.search(tx)
        if m:
            x["rusher"] = who(x["off"], m.group(1), m.group(2))
    low = tx.lower()
    x["sack"] = x["type"] == "Sack" or "sacked" in low
    x["att"] = x["kind"] == "pass" and not x["sack"]
    x["complete"] = x["type"] in ("Pass Reception", "Passing Touchdown") or ("pass complete" in low)
    x["pressure"] = x["sack"] or "hurried" in low or "qb hit" in low
    x["deep"] = " deep " in low and x["att"]
    my = x["dh"] if x["off"] == x["home"] else x["da"]
    x["td"] = my >= 6
    x["to"] = x["type"] in TO_T or bool(x["turnover"] and x["eteam"] and x["eteam"] != x["off"] and x["type"] not in RUSH_T | PASS_T - TO_T)

# ---------------- per team-game unit numbers ----------------
KEYS = [k for k, _, _ in UNITS]
DEN = {"epa": "n", "pass_epa": "drop", "rush_epa": "rush", "success": "n", "explosive": "n", "ppd": "drives",
       "rz_td": "rz", "third": "third_n", "sack": "drop", "pressure": "drop", "giveaway": "drives", "deep_epa": "deep_n"}
NUM = {"epa": "epa", "pass_epa": "pass_epa", "rush_epa": "rush_epa", "success": "success", "explosive": "explosive",
       "ppd": "points", "rz_td": "rz_td", "third": "third", "sack": "sack", "pressure": "pressure", "giveaway": "to",
       "deep_epa": "deep_epa"}
TG = defaultdict(lambda: defaultdict(float))   # (team, side, gid) -> sums
OPP = {}
for x in plays:
    if not x["kind"] or x["garbage"]:
        continue
    o = x["off"]
    d = x["away"] if o == x["home"] else x["home"]
    OPP[(o, x["gid"])], OPP[(d, x["gid"])] = d, o
    for side, t in (("off", o), ("def", d)):
        a = TG[(t, side, x["gid"])]
        a["n"] += 1
        a["epa"] += x["epa"]
        a["success"] += 1 if x["epa"] > 0 else 0
        if x["kind"] == "pass":
            a["drop"] += 1
            a["pass_epa"] += x["epa"]
            a["sack"] += x["sack"]
            a["pressure"] += x["pressure"]
            a["explosive"] += 1 if x["yds"] >= 20 else 0
            if x["deep"]:
                a["deep_n"] += 1
                a["deep_epa"] += x["epa"]
        else:
            a["rush"] += 1
            a["rush_epa"] += x["epa"]
            a["explosive"] += 1 if x["yds"] >= 10 else 0
        if x["down"] == 3:
            a["third_n"] += 1
            a["third"] += 1 if (x["yds"] >= (x["dist"] or 99) or x["td"]) and not x["to"] else 0
PTS = {"TD": 7, "FG": 3}
for dv in drives:
    sp = [x for x in dv["plays"] if x["kind"]]
    if not sp or sp[0]["garbage"]:
        continue
    o = sp[0]["off"]
    d = dv["away"] if o == dv["home"] else dv["home"]
    for side, t in (("off", o), ("def", d)):
        a = TG[(t, side, dv["gid"])]
        a["drives"] += 1
        a["points"] += PTS.get(dv["result"], 0)
        a["to"] += 1 if any(x["to"] for x in sp) else 0
        if min(x["ytg"] for x in sp) <= 20:
            a["rz"] += 1
            a["rz_td"] += 1 if dv["result"] == "TD" else 0

teams = sorted({t for (t, _, _) in TG})
GAMES_OF = defaultdict(set)
for (t, side, gid) in TG:
    GAMES_OF[t].add(gid)


def raw(t, side, key, gids=None):
    n = s = 0.0
    for gid in GAMES_OF[t]:
        if gids is not None and gid not in gids:
            continue
        a = TG.get((t, side, gid))
        if a:
            n += a[DEN[key]]
            s += a[NUM[key]]
    return (s / n) if n else None, n


# opponent adjustment: additive, iterated, weighted by each game's denominator
LG = {}
for key in KEYS:
    tn = ts = 0.0
    for (t, side, gid), a in TG.items():
        if side == "off":
            tn += a[DEN[key]]
            ts += a[NUM[key]]
    LG[key] = ts / tn if tn else 0
ADJ = {side: {key: {t: (raw(t, side, key)[0] if raw(t, side, key)[0] is not None else LG[key]) for t in teams}
              for key in KEYS} for side in ("off", "def")}
for _ in range(12):
    new = {side: {key: {} for key in KEYS} for side in ("off", "def")}
    for side, other in (("off", "def"), ("def", "off")):
        for key in KEYS:
            for t in teams:
                n = s = 0.0
                ng = 0
                for gid in GAMES_OF[t]:
                    a = TG.get((t, side, gid))
                    if not a or not a[DEN[key]]:
                        continue
                    opp = OPP.get((t, gid))
                    shift = ADJ[other][key].get(opp, LG[key]) - LG[key]
                    n += a[DEN[key]]
                    s += a[NUM[key]] - shift * a[DEN[key]] - LG[key] * a[DEN[key]]
                    ng += 1
                prior = 2.0 * (n / ng) if ng else 0      # two games of league average: keeps 8-game ratings honest
                new[side][key][t] = (LG[key] + s / (n + prior)) if n else None
    for side in new:
        for key in new[side]:
            for t, v in new[side][key].items():
                ADJ[side][key][t] = v if v is not None else LG[key]


def adj_window(t, side, key, gids):
    other = "def" if side == "off" else "off"
    n = s = 0.0
    for gid in gids:
        a = TG.get((t, side, gid))
        if not a or not a[DEN[key]]:
            continue
        shift = ADJ[other][key].get(OPP.get((t, gid)), LG[key]) - LG[key]
        n += a[DEN[key]]
        s += a[NUM[key]] - shift * a[DEN[key]]
    return s / n if n else None


fbs = [t for t in teams if t in FBS_IDS]
last3_of = {t: sorted(GAMES_OF[t], key=lambda gid: GAMES[gid]["date"])[-3:] for t in fbs}
S, S3 = {}, {}
for t in fbs:
    ab = ABBR[t]
    S[ab], S3[ab] = {}, {}
    for side in ("off", "def"):
        dsum = sum(TG[(t, side, gid)]["drives"] for gid in GAMES_OF[t])
        S[ab][side] = {k: (ADJ[side][k][t] if raw(t, side, k)[1] else None) for k in KEYS}
        S[ab][side]["games"] = len(GAMES_OF[t])
        S[ab][side]["drives_pg"] = dsum / len(GAMES_OF[t]) if GAMES_OF[t] else None
        S[ab][side]["pass_rate"] = (raw(t, side, "pass_epa")[1] / raw(t, side, "epa")[1]) if raw(t, side, "epa")[1] else None
        S3[ab][side] = {k: adj_window(t, side, k, last3_of[t]) for k in KEYS}
N_TEAMS = len(S)
R = MX.ranks(S)
R3 = MX.ranks(S3)

# ---------------- this game ----------------
G = GAMES[EVENT]
H, A = G["teams"]["home"]["id"], G["teams"]["away"]["id"]
HA, AA = ABBR.get(H, G["teams"]["home"]["ab"]), ABBR.get(A, G["teams"]["away"]["ab"])
summ = json.load(open(C / f"sum_{EVENT}.json"))
pc = next((p for p in summ.get("pickcenter") or [] if p.get("provider", {}).get("name") == "DraftKings"),
          (summ.get("pickcenter") or [{}])[0])
spread, total = pc.get("spread"), pc.get("overUnder")
ml = {"home": (pc.get("homeTeamOdds") or {}).get("moneyLine"), "away": (pc.get("awayTeamOdds") or {}).get("moneyLine")}
kick_utc = datetime.fromisoformat(G["date"].replace("Z", "+00:00"))
kick_et = (kick_utc - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")

# QB: most dropbacks in the team's last game (starter), with season share
def qb_usage(t, gids=None):
    q = defaultdict(lambda: [0, 0.0, 0, 0])   # dropbacks, epa, att, comp
    for x in plays:
        if x["kind"] == "pass" and x["off"] == t and not x["garbage"] and x.get("passer") and (gids is None or x["gid"] in gids):
            k = x["passer"]["name"]
            q[k][0] += 1
            q[k][1] += x["epa"]
            q[k][2] += x["att"]
            q[k][3] += x["complete"]
    return q


QBS, QBFLAG, PL, PL3 = {}, {}, {}, {}
for t, ab in ((H, HA), (A, AA)):
    lastg = sorted(GAMES_OF[t], key=lambda gid: GAMES[gid]["date"])[-1]
    ql = qb_usage(t, {lastg})
    qs = qb_usage(t)
    starter = max(ql, key=lambda n: ql[n][0]) if ql else None
    QBS[ab] = starter
    tot = sum(v[0] for v in qs.values()) or 1
    share = qs[starter][0] / tot if starter else 0
    if starter and share < 0.6:
        QBFLAG[ab] = (f"{starter} has {qs[starter][0]} of {ab}'s dropbacks ({share * 100:.0f}%): {ab}'s season offense "
                      f"numbers are partly another QB. Weigh the last-3 column and the market more.")

# player-game table for props and personnel
PG = {}
for x in plays:
    if not x["kind"] or x["garbage"]:
        continue
    t = x["off"]
    d = x["away"] if t == x["home"] else x["home"]
    if t not in FBS_IDS:
        continue

    def slot(a):
        p = PG.setdefault(a["id"], {"name": a["name"], "team": ABBR[t], "pos": POSG.get(a.get("pos") or "", a.get("pos")), "games": {}})
        return p["games"].setdefault(x["gid"], {"week": x["week"], "opp": ABBR.get(d, d), "tg": 0, "rec": 0, "ryd": 0.0, "car": 0,
                                                 "rush_yd": 0.0, "pass_yd": 0.0, "att": 0, "rz": 0, "td": 0, "long": 0.0,
                                                 "air": 0.0, "deep": 0})
    rz = x["ytg"] <= 20
    if x["kind"] == "pass" and x.get("target") and x["att"]:
        s_ = slot(x["target"])
        s_["tg"] += 1
        s_["rz"] += rz
        s_["deep"] += x["deep"]
        if x["complete"]:
            s_["rec"] += 1
            s_["ryd"] += x["yds"]
            s_["long"] = max(s_["long"], x["yds"])
            s_["td"] += x["td"]
    if x["kind"] == "rush" and x.get("rusher"):
        s_ = slot(x["rusher"])
        s_["car"] += 1
        s_["rush_yd"] += x["yds"]
        s_["rz"] += rz
        s_["td"] += x["td"]
    if x["kind"] == "pass" and x.get("passer") and x["att"]:
        s_ = slot(x["passer"])
        s_["att"] += 1
        if x["complete"]:
            s_["pass_yd"] += x["yds"]
for pid, p_ in PG.items():
    if p_["pos"] not in ("WR", "TE", "RB", "QB"):
        tg_ = sum(g["tg"] for g in p_["games"].values())
        car_ = sum(g["car"] for g in p_["games"].values())
        att_ = sum(g["att"] for g in p_["games"].values())
        if p_["pos"] is None or tg_ + car_ + att_ >= 10:
            p_["pos"] = "QB" if att_ > tg_ + car_ else "RB" if car_ > tg_ else "WR"
# FBS-only defenses for defense-vs-position; ranks over FBS
DV, DR, LGP = MX.defense_vs_position(PG)
for k in list(DV):
    if k not in S:
        DV.pop(k)
for grp in ("WR", "TE", "RB", "QB"):
    for k in ("tg", "rec", "ryd", "rush_yd", "pass_yd", "td"):
        vals = sorted(((d, v.get(grp, {}).get(k, 0.0)) for d, v in DV.items()), key=lambda z: -z[1])
        LGP[(grp, k)] = sum(v for _, v in vals) / len(vals) if vals else 0
        for i, (d, _) in enumerate(vals):
            DR[(d, grp, k)] = i + 1


def personnel(ab, gids=None):
    mine = {pid: p for pid, p in PG.items() if p["team"] == ab}
    ng = len(GAMES_OF[H if ab == HA else A]) if gids is None else len(gids)
    def gsel(p):
        return [g for gid, g in p["games"].items() if gids is None or gid in gids]
    team_tg = sum(g["tg"] for p in mine.values() for g in gsel(p))
    team_car = sum(g["car"] for p in mine.values() if p["pos"] != "QB" for g in gsel(p))
    team_deep = sum(g["deep"] for p in mine.values() for g in gsel(p))
    rec = sorted(mine.items(), key=lambda kv: -sum(g["tg"] for g in gsel(kv[1])))[:4]
    rb = sorted([kv for kv in mine.items() if kv[1]["pos"] != "QB"], key=lambda kv: -sum(g["car"] for g in gsel(kv[1])))[:2]
    out = {"receivers": [], "rushers": []}
    for pid, p in rec:
        gs = gsel(p)
        tg = sum(g["tg"] for g in gs)
        out["receivers"].append({"name": p["name"], "pos": p["pos"], "tgtShare": tg / team_tg if team_tg else None,
                                 "airShare": (sum(g["deep"] for g in gs) / team_deep) if team_deep else None,
                                 "aDOT": None, "ydsPg": sum(g["ryd"] for g in gs) / ng, "tgtPg": tg / ng,
                                 "tds": int(sum(g["td"] for g in gs)), "status": None})
    for pid, p in rb:
        gs = gsel(p)
        car = sum(g["car"] for g in gs)
        out["rushers"].append({"name": p["name"], "pos": p["pos"], "carryShare": car / team_car if team_car else None,
                               "ypc": sum(g["rush_yd"] for g in gs) / car if car else None,
                               "ydsPg": sum(g["rush_yd"] for g in gs) / ng, "status": None})
    q = qb_usage(H if ab == HA else A, gids)
    tot = sum(v[0] for v in q.values()) or 1
    st = QBS[ab]
    if st in q:
        out["qb"] = {"name": st, "epaPerDropback": q[st][1] / q[st][0], "cpoe": None,
                     "compPct": q[st][3] / q[st][2] if q[st][2] else None,
                     "dropbacks": q[st][0], "shareOfTeamDropbacks": q[st][0] / tot}
    else:
        out["qb"] = {"name": st, "epaPerDropback": None, "cpoe": None, "dropbacks": 0, "shareOfTeamDropbacks": 0}
    return out


for t, ab in ((H, HA), (A, AA)):
    PL[ab] = personnel(ab)
    PL3[ab] = personnel(ab, set(last3_of[t]))

# ---------------- trends vs the closing number (this season ESPN/DK, last season EDGE's CFBD back-fill) ----------------
hist = json.load(open(REPO / "stats" / "ncaaf_games.json"))
hg = hist["games"] if isinstance(hist.get("games"), list) else list(hist["games"].values())


def team_results(tid):
    nm = NAME[tid]
    rows = []
    for g in hg:
        if g.get("final") and nm in (g["home"], g["away"]) and g.get("lines", {}).get("spreadClose") is not None \
                and g["date"][:4] in ("2025",) or (g.get("final") and nm in (g["home"], g["away"]) and g["date"] < "2026-02-01"
                                                    and g["date"] >= "2025-08-01" and g.get("lines", {}).get("spreadClose") is not None):
            L = g["lines"]
            rows.append({"date": g["date"], "home": g["home"] == nm, "hs": g["hs"], "as": g["as"], "spread": L["spreadClose"],
                         "total": L.get("totalClose"), "season": 2025})
    for r in team_games[tid]:
        if r["spread"] is None:
            continue
        rows.append({"date": r["date"], "home": r["home"] == tid, "hs": r["hs"], "as": r["as"], "spread": r["spread"],
                     "total": r["total"], "season": 2026})
    rows.sort(key=lambda r: r["date"])
    dedup, seen = [], set()
    for r in rows:
        k = r["date"][:10]
        if k not in seen:
            seen.add(k)
            dedup.append(r)
    return dedup


def trends(tid, home_now, fav_now):
    rows = team_results(tid)

    def ats(r):
        m = (r["hs"] - r["as"]) + r["spread"]   # home line: >0 home covered
        if m == 0:
            return "P"
        return "W" if (m > 0) == r["home"] else "L"

    def ou(r):
        if r["total"] is None:
            return None
        d = r["hs"] + r["as"] - r["total"]
        return "P" if d == 0 else ("O" if d > 0 else "U")

    def rec(rs, f):
        v = [f(r) for r in rs]
        v = [z for z in v if z]
        a, b = ("W", "L") if f is ats else ("O", "U")
        return {"w": v.count(a), "l": v.count(b), "p": v.count("P"), "n": len(v)}

    def fav(r):
        my = r["spread"] if r["home"] else -r["spread"]
        return my < 0

    def et_hour(r):
        d = datetime.fromisoformat(r["date"].replace("Z", "+00:00")) - timedelta(hours=5)
        return d.hour

    this = [r for r in rows if r["season"] == 2026]
    role = [r for r in rows if r["home"] == home_now and fav(r) == fav_now]
    prime = [r for r in rows if et_hour(r) >= 19]
    su = []
    for r in rows[-5:]:
        mine, theirs = (r["hs"], r["as"]) if r["home"] else (r["as"], r["hs"])
        su.append("W" if mine > theirs else "L" if mine < theirs else "T")
    return {"atsSeason": rec(this, ats), "ouSeason": rec(this, ou), "atsLast10": rec(rows[-10:], ats),
            "ouLast10": rec(rows[-10:], ou), "atsRole": rec(role, ats),
            "roleLabel": ("home" if home_now else "road") + " " + ("favorite" if fav_now else "underdog") + " since 2025",
            "atsPrime": rec(prime, ats), "ouPrime": rec(prime, ou), "suLast5": "".join(su)}


home_fav = (spread or 0) < 0
T = {HA: trends(H, True, home_fav), AA: trends(A, False, not home_fav)}

# ---------------- mismatches, projection, suggestions, props ----------------
EDGE_GAP = round(14 / 32 * N_TEAMS)
STRONG_GAP = round(20 / 32 * N_TEAMS)
TOP = round(8 / 32 * N_TEAMS)


def mism(off_t, def_t):
    out = []
    for key, label in PAIRS:
        ro, rd = R[off_t]["off"].get(key), R[def_t]["def"].get(key)
        if ro is None or rd is None:
            continue
        gap = rd - ro
        kind = "offense edge" if gap >= EDGE_GAP else "defense edge" if gap <= -EDGE_GAP else \
            ("strength vs strength" if ro <= TOP and rd <= TOP else None)
        out.append({"unit": label, "key": key, "offense": off_t, "defense": def_t, "offRank": ro, "defRank": rd, "gap": gap,
                    "kind": kind, "strong": abs(gap) >= STRONG_GAP, "offVal": S[off_t]["off"].get(key),
                    "defVal": S[def_t]["def"].get(key)})
    return out


M = {HA: mism(HA, AA), AA: mism(AA, HA)}
HFA = 0.0 if G["neutral"] else 2.5
lg_ppd = MX.league_avg(S, "ppd")
dpg = MX.league_avg(S, "drives_pg") or 12.0


def ppd(o, d):
    po = MX.shrink(S[o]["off"]["ppd"], lg_ppd, S[o]["off"]["games"])
    pd = MX.shrink(S[d]["def"]["ppd"], lg_ppd, S[d]["def"]["games"])
    return po * pd / lg_ppd


def all_drives_pg(tid):
    n = sum(1 for dv in drives if dv["team"] == tid and any(x["kind"] for x in dv["plays"]))
    return n / len(GAMES_OF[tid])


drv = (all_drives_pg(H) + all_drives_pg(A)) / 2
hp, ap = ppd(HA, AA) * drv, ppd(AA, HA) * drv
proj = {"home": round(hp + HFA / 2, 1), "away": round(ap - HFA / 2, 1), "drives": round(drv, 1),
        "margin": round(hp - ap + HFA, 1), "total": round(hp + ap, 1)}

_mc = MX.memory_check
MX.memory_check = lambda sport, market, side: _mc("NCAAF", market, side)
gstub = {"home_team": HA, "away_team": AA, "spread_line": -spread if spread is not None else None, "total_line": total}
lines = {"spread": {"line": spread, "p": {"home": pc.get("homeTeamOdds", {}).get("spreadOdds"),
                                          "away": pc.get("awayTeamOdds", {}).get("spreadOdds")}, "book": "DraftKings"},
         "total": {"line": total, "p": {"over": pc.get("overOdds"), "under": pc.get("underOdds")}, "book": "DraftKings"},
         "h2h": {"line": None, "p": ml, "book": "DraftKings"}}
sugg = MX.suggestions(gstub, S, R, M, PL, proj, lines, T)

# props: same rule set, thresholds scaled to the FBS field
MX.OVER_RANK, MX.UNDER_RANK = TOP, N_TEAMS + 1 - TOP
_rw = MX.rank_words
MX.rank_words = lambda r, n=N_TEAMS: _rw(r, n)
last3_ids = set(last3_of[H]) | set(last3_of[A])
last3_weeks = {GAMES[gid]["week"] for gid in last3_ids}
PGs = {pid: p for pid, p in PG.items() if p["team"] in (HA, AA)}
# prop_angles reads "week in last3"; use per-team last-3 weeks by filtering games
for pid, p in PGs.items():
    tid = H if p["team"] == HA else A
    for gid, g in p["games"].items():
        g["week"] = g["week"] if gid in last3_of[tid] else -g["week"]   # negative = not in last 3
l3w = {w for w in last3_weeks}
props = MX.prop_angles(gstub, PGs, DV, DR, LGP, M, {}, QBS, l3w)
for pid, p in PGs.items():
    for g in p["games"].values():
        g["week"] = abs(g["week"])
STRONG_R = round(4 / 32 * N_TEAMS)
for x in props:
    if x.get("oppRank") is not None and x["stat"] not in ("long", "sacks"):
        x["strength"] = "strong" if (x["oppRank"] <= STRONG_R or x["oppRank"] >= N_TEAMS + 1 - STRONG_R) and x["strength"] != "lean" or \
            (x["strength"] == "strong" and (x["oppRank"] <= STRONG_R or x["oppRank"] >= N_TEAMS + 1 - STRONG_R)) else "lean"
    if x["team"] in QBFLAG and x["stat"] != "sacks":
        x["why"].append("Caution: " + QBFLAG[x["team"]])
        x["strength"] = "lean"
for x in sugg:
    if QBFLAG and x["market"] in ("spread", "total", "team total"):
        x["why"].append("Caution: " + " ".join(QBFLAG.values()))
        x["confidence"] = "low"

units = {}
for ab in (HA, AA):
    units[ab] = {side: {k: {"value": S[ab][side].get(k), "rank": R[ab][side].get(k), "last3": S3[ab][side].get(k),
                            "last3Rank": R3[ab][side].get(k)} for k in KEYS} for side in ("off", "def")}
    units[ab]["games"] = S[ab]["off"]["games"]
    units[ab]["passRate"] = S[ab]["off"]["pass_rate"]


def rest(tid):
    prev = [GAMES[gid]["date"] for gid in GAMES_OF[tid]]
    if not prev:
        return None
    last = datetime.fromisoformat(max(prev).replace("Z", "+00:00"))
    return round((kick_utc - last).total_seconds() / 86400)


gi = summ.get("gameInfo") or {}
venue = (gi.get("venue") or {})
edge_model = None
try:
    em = json.load(open(REPO / "stats" / "ncaaf_matchups.json"))
    for gg in em["games"]:
        if NAME[A] in gg["event"] and NAME[H] in gg["event"]:
            edge_model = {"rawMargin": gg["raw"]["margin"], "rawTotal": gg["raw"]["total"],
                          "fairHomeLine": gg["spread"]["fairHomeLine"], "fairTotal": gg["total"]["fairTotal"],
                          "kSide": em["k"]["kSide"], "kTotal": em["k"]["kTotal"], "asOf": em["asOf"]}
except Exception:
    pass

rec_ = {}
for ab, tid in ((HA, H), (AA, A)):
    w = l = 0
    for r in team_games[tid]:
        mine, theirs = (r["hs"], r["as"]) if r["home"] == tid else (r["as"], r["hs"])
        w += mine > theirs
        l += mine < theirs
    rec_[ab] = f"{w}-{l}"

game = {
    "id": f"2026_{G['week']:02d}_{AA}_{HA}", "espnId": EVENT, "kickoffET": kick_et, "home": HA, "away": AA,
    "homeName": NAME[H], "awayName": NAME[A], "records": rec_, "qbs": QBS, "rest": {HA: rest(H), AA: rest(A)},
    "roof": "outdoors", "surface": "grass" if venue.get("grass") else "turf", "venue": venue.get("fullName"),
    "injuries": [], "weather": None, "lines": {k: {"line": v["line"], "prices": v["p"], "pin": None, "book": v["book"],
                                                   "t": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} for k, v in lines.items()},
    "nflverseLine": {"homeSpread": spread, "total": total}, "projection": proj, "qbFlags": QBFLAG, "units": units,
    "mismatches": M, "trends": T, "players": PL, "playersLast3": PL3,
    "last3Weeks": sorted(last3_weeks), "suggestions": sugg, "props": props, "edgeModel": edge_model,
    "predictor": summ.get("predictor"),
}
top = sorted([dict(x, gameId=game["id"]) for x in props if x["stat"] not in ("sacks",)], key=MX.prop_score, reverse=True)
slate = {"sport": "NCAAF", "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "topProps": top[:6],
         "season": 2026, "throughWeek": max(GAMES[gid]["week"] for t in (H, A) for gid in GAMES_OF[t]),
         "games": [game], "label": f"{AA} at {HA}", "nTeams": N_TEAMS, "record": None,
         "method": {"garbage": "1st half > 38, 3rd > 28, 4th > 22; OT dropped", "adjusted": True, "hfa": HFA,
                    "plays": sum(1 for x in plays if x["kind"] and not x["garbage"]), "games": sum(1 for g in GAMES.values() if g["done"]),
                    "leagueEpa": round(LG["epa"], 4)}}
OUTP.write_text(json.dumps(slate, indent=1, default=str))
print(json.dumps({"teams": N_TEAMS, "edge_gap": EDGE_GAP, "proj": proj, "line": spread, "total": total, "qbs": QBS,
                  "qbflags": QBFLAG, "sugg": [s["label"] for s in sugg], "props": [(p["player"], p["label"], p["side"]) for p in props],
                  "leagueEPA": LG["epa"], "M": {k: [(m["unit"], m["offRank"], m["defRank"], m["kind"]) for m in v] for k, v in M.items()}}, indent=1))

if "--debug" in sys.argv:
    print("EP 1&10 at 75:", EP(1, 10, 75), " at 25:", EP(1, 10, 25), " at 5:", EP(1, 5, 5), " 3&8 at 50:", EP(3, 8, 50))
    print("LG ppd", LG["ppd"], "lg drives (S)", MX.league_avg(S, "drives_pg"))
    for t in (H, A):
        print(ABBR[t], "raw ppd off/def", raw(t, "off", "ppd"), raw(t, "def", "ppd"), "adj", ADJ["off"]["ppd"][t], ADJ["def"]["ppd"][t])
        print([(ABBR.get(OPP.get((t, g))), round(TG[(t, 'def', g)]['points'] / max(TG[(t, 'def', g)]['drives'], 1), 2), round(ADJ['off']['ppd'].get(OPP.get((t, g)), 0), 2)) for g in GAMES_OF[t]])
    import collections
    print([ (x["text"][:110]) for x in plays if x["off"] == H and x.get("target") and "Dottery" in (x["target"]["name"] or "")][:3])
    print([ (x["text"][:110]) for x in plays if x["off"] == A and x.get("target") and x["target"]["name"] == "R.Scott"][:3])
    print([a for a in ROSTERS[A] if "Scott" in (a["name"] or "")], [a for a in ROSTERS[H] if "Dottery" in (a["name"] or "") or "Wilson" in (a["name"] or "")])
