#!/usr/bin/env python3
"""EDGE stats for the sports beyond the NFL (v1): NBA, NHL, NCAAF, EPL.

Same idea as stats.py, one file per sport:
  stats/<sport>_games.json        game history with results and market lines (grows every run)
  stats/<sport>_teams.json        opponent-adjusted team ratings, recent games weighted more
  stats/<sport>_calibration.json  backtest against the market, and the learned k
  stats/<sport>_matchups.json     upcoming games from the ledger: raw, market, fair, edge, bar check

Sources (all free, no key):
  NBA, NHL  ESPN results, and DraftKings open and close per game from ESPN game summaries
  NCAAF     ESPN results. No free line history, so k is learned from the ledger's own closes
            once 40 graded games exist. Until then k is 0.
  EPL       football-data.co.uk results with Pinnacle closing odds

Two tests run for each sport with market history:
  k      does the model's gap from the CLOSE show up in results? (same as stats.py)
  kMove  does the model's gap from the OPEN predict where the line closes? That is the
         direct test of whether the model would have beaten the close.

The analyst reads a sport's files only when that sport is in READ in pull.py.

  python3 stats_more.py            all sports
  python3 stats_more.py NBA NHL    some sports
"""

import csv
import io
import json
import math
import os
import re
import sys
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "stats"
LEDGER = ROOT / "ledger" / "ledger.json"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/{}/{}"
FD = "https://www.football-data.co.uk/mmz4281/{}/{}.csv"
LOOKBACK = int(os.environ.get("EDGE_LOOKBACK_DAYS", "430"))
WORKERS = 8
K_MAX = 0.5
MIN_N = 40
MIN_GAIN = 0.002   # log-loss improvement over the market needed before the model gets any weight
BIG_GAP = {"NBA": 5.0, "NCAAF": 7.0}

CONFIG = {
    "NBA": {"kind": "points", "espn": "basketball/nba", "summaries": True,
            "halflife": 60, "ridge": 6.0, "bar": {"spread": 2.0, "total": 3.0}},
    "NCAAF": {"kind": "points", "espn": "football/college-football", "groups": "80", "summaries": False,
              "halflife": 150, "ridge": 3.0, "bar": {"spread": 2.5, "total": 3.0}},
    "NHL": {"kind": "hockey", "espn": "hockey/nhl", "summaries": True,
            "halflife": 90, "ridge": 8.0, "bar": {"h2h": 0.03}},
    "EPL": {"kind": "soccer", "fd": "E0", "halflife": 200, "ridge": 5.0,
            "bar": {"h2h": 0.03}},
}

# football-data names -> the Odds API names the ledger uses
EPL_NAMES = {
    "Man City": "Manchester City", "Man United": "Manchester United", "Tottenham": "Tottenham Hotspur",
    "Newcastle": "Newcastle United", "Wolves": "Wolverhampton Wanderers", "Brighton": "Brighton and Hove Albion",
    "West Ham": "West Ham United", "Nott'm Forest": "Nottingham Forest", "Leicester": "Leicester City",
    "Ipswich": "Ipswich Town", "Leeds": "Leeds United", "Coventry": "Coventry City", "Hull": "Hull City",
    "Sheffield United": "Sheffield United", "Luton": "Luton Town", "Norwich": "Norwich City",
    "West Brom": "West Bromwich Albion", "Middlesbrough": "Middlesbrough", "Stoke": "Stoke City",
    "Swansea": "Swansea City", "Cardiff": "Cardiff City", "Watford": "Watford", "Burnley": "Burnley",
}
# ESPN display names that differ from the Odds API beyond accents and punctuation
ALIASES = {"la clippers": "los angeles clippers", "utah hockey club": "utah mammoth",
           "app state mountaineers": "appalachian state mountaineers",
           "sam houston bearkats": "sam houston state bearkats",
           "southern miss golden eagles": "southern mississippi golden eagles",
           "massachusetts minutemen": "umass minutemen"}


# ---------- helpers ----------

def norm(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", "", s.replace("&", "and"))
    s = re.sub(r"\s+", " ", s).strip()
    return ALIASES.get(s, s)


def fetch(url, tries=3):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 EDGE-stats"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise last


def jget(url):
    return json.loads(fetch(url).decode())


def num(x):
    if x is None:
        return None
    s = str(x).strip().lower().lstrip("ou")
    if s in ("even", "ev"):
        return 100.0
    try:
        return float(s)
    except ValueError:
        return None


def implied(american):
    a = float(american)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def novig(prices):
    ps = [implied(p) for p in prices]
    t = sum(ps)
    return [p / t for p in ps]


def poisson_pmf(lam, kmax=12):
    lam = max(lam, 0.05)
    out = [math.exp(-lam)]
    for k in range(1, kmax + 1):
        out.append(out[-1] * lam / k)
    return out


def outcome_probs(lh, la):
    ph, pa = poisson_pmf(lh), poisson_pmf(la)
    home = draw = away = 0.0
    for i, x in enumerate(ph):
        for j, y in enumerate(pa):
            if i > j:
                home += x * y
            elif i == j:
                draw += x * y
            else:
                away += x * y
    s = home + draw + away
    return home / s, draw / s, away / s


def p_over(lh, la, line):
    pt = poisson_pmf(lh + la, 20)
    under = sum(p for g, p in enumerate(pt) if g < line)
    push = sum(p for g, p in enumerate(pt) if g == line)
    return 1 - under - push


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- data ----------

def espn_day(cfg, day):
    q = f"?dates={day}&limit=500" + (f"&groups={cfg['groups']}" if cfg.get("groups") else "")
    return jget(ESPN.format(cfg["espn"], "scoreboard") + q).get("events", [])


def espn_lines(cfg, event_id):
    try:
        pc = (jget(ESPN.format(cfg["espn"], "summary") + f"?event={event_id}").get("pickcenter") or [])
    except Exception:  # noqa: BLE001
        return None
    p = next((x for x in pc if "draft" in str(x.get("provider", {}).get("name", "")).lower()), pc[0] if pc else None)
    if not p:
        return None
    sp, tt, ml = p.get("pointSpread") or {}, p.get("total") or {}, p.get("moneyline") or {}

    def g(d, *path):
        for k in path:
            d = (d or {}).get(k)
        return num(d)
    return {
        "spreadOpen": g(sp, "home", "open", "line"), "spreadClose": g(sp, "home", "close", "line"),
        "totalOpen": g(tt, "over", "open", "line"), "totalClose": g(tt, "over", "close", "line"),
        "overOpenOdds": g(tt, "over", "open", "odds"), "underOpenOdds": g(tt, "under", "open", "odds"),
        "overCloseOdds": g(tt, "over", "close", "odds"), "underCloseOdds": g(tt, "under", "close", "odds"),
        "mlHomeOpen": g(ml, "home", "open", "odds"), "mlAwayOpen": g(ml, "away", "open", "odds"),
        "mlHomeClose": g(ml, "home", "close", "odds"), "mlAwayClose": g(ml, "away", "close", "odds"),
    }


def load_store(sport):
    path = OUT / f"{sport.lower()}_games.json"
    if path.exists():
        return path, json.loads(path.read_text())
    return path, {"games": {}, "done": []}


def update_espn(sport, cfg):
    path, store = load_store(sport)
    games, done = store["games"], set(store["done"])
    today = now_utc().date()
    days = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(LOOKBACK, -8, -1)]
    todo = [d for d in days if d not in done]

    def day_job(d):
        try:
            return d, espn_day(cfg, d)
        except Exception as exc:  # noqa: BLE001
            return d, exc
    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(day_job, todo))
    need_lines = []
    errors = 0
    for d, events in results:
        if isinstance(events, Exception):
            errors += 1
            continue
        all_final = True
        for e in events:
            c = e["competitions"][0]
            teams = c.get("competitors") or []
            h = next((t for t in teams if t.get("homeAway") == "home"), None)
            a = next((t for t in teams if t.get("homeAway") == "away"), None)
            if not h or not a:
                continue
            stype = (e.get("season") or {}).get("type")
            if stype == 1:          # preseason never counts
                continue
            final = bool(c["status"]["type"].get("completed"))
            all_final = all_final and final
            g = games.get(e["id"], {})
            g.update({"id": e["id"], "date": e["date"], "seasonType": stype, "home": h["team"]["displayName"],
                      "away": a["team"]["displayName"], "neutral": bool(c.get("neutralSite")), "final": final})
            if final:
                g["hs"], g["as"] = num(h.get("score")), num(a.get("score"))
                if cfg.get("summaries") and "lines" not in g:
                    need_lines.append(e["id"])
            games[e["id"]] = g
        past = datetime.strptime(d, "%Y%m%d").date() < today - timedelta(days=1)
        if past and all_final:
            done.add(d)
    floor = iso(now_utc() - timedelta(days=LOOKBACK + 30))

    def save():
        store["games"] = {k: v for k, v in games.items() if v["date"] >= floor and v.get("seasonType") != 1}
        store["done"] = sorted(x for x in done if x >= (today - timedelta(days=LOOKBACK + 30)).strftime("%Y%m%d"))
        OUT.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(store, separators=(",", ":")) + "\n")
    save()          # progress is kept even if a long first run is cut off
    for i in range(0, len(need_lines), 250):
        batch = need_lines[i:i + 250]
        with ThreadPoolExecutor(WORKERS) as pool:
            for gid, lines in zip(batch, pool.map(lambda x: espn_lines(cfg, x), batch)):
                games[gid]["lines"] = lines
        save()
    return list(store["games"].values()), {"fetchedDays": len(todo), "dayErrors": errors, "newLines": len(need_lines)}


def update_epl(sport, cfg):
    path, store = load_store(sport)
    today = now_utc().date()
    y = today.year if today.month >= 7 else today.year - 1
    seasons = [f"{(y - i) % 100:02d}{(y - i + 1) % 100:02d}" for i in (1, 0)]
    games = {}
    for code in seasons:
        try:
            text = fetch(FD.format(code, cfg["fd"])).decode("utf-8-sig", "ignore")
        except Exception:  # noqa: BLE001
            continue
        for r in csv.DictReader(io.StringIO(text)):
            if not r.get("HomeTeam") or not r.get("FTHG"):
                continue
            dt = datetime.strptime(r["Date"], "%d/%m/%Y" if len(r["Date"]) > 8 else "%d/%m/%y")
            home, away = EPL_NAMES.get(r["HomeTeam"], r["HomeTeam"]), EPL_NAMES.get(r["AwayTeam"], r["AwayTeam"])

            def pick(*cols):
                for c in cols:
                    v = num(r.get(c))
                    if v:
                        return v
                return None
            gid = f"{dt:%Y%m%d}-{norm(home)}-{norm(away)}"
            games[gid] = {
                "id": gid, "date": iso(dt), "home": home, "away": away, "neutral": False, "final": True,
                "hs": num(r["FTHG"]), "as": num(r["FTAG"]), "season": code,
                "lines": {"decHomeClose": pick("PSCH", "AvgCH", "B365CH"), "decDrawClose": pick("PSCD", "AvgCD", "B365CD"),
                          "decAwayClose": pick("PSCA", "AvgCA", "B365CA"),
                          "decHomeOpen": pick("PSH", "AvgH", "B365H"), "decDrawOpen": pick("PSD", "AvgD", "B365D"),
                          "decAwayOpen": pick("PSA", "AvgA", "B365A"),
                          "decOverClose": pick("PC>2.5", "AvgC>2.5", "B365C>2.5"),
                          "decUnderClose": pick("PC<2.5", "AvgC<2.5", "B365C<2.5"),
                          "decOverOpen": pick("P>2.5", "Avg>2.5", "B365>2.5"),
                          "decUnderOpen": pick("P<2.5", "Avg<2.5", "B365<2.5")},
            }
    store = {"games": games, "done": [], "seasons": seasons}
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, separators=(",", ":")) + "\n")
    return list(games.values()), {"seasons": seasons, "games": len(games)}


# ---------- model ----------

def fit(games, cutoff, cfg, priors=None):
    """Score model: score = mu + off[team] + def[opp] +/- half home edge, recency weighted,
    with ridge pulling each team toward 0 (or toward its prior)."""
    obs = []
    cut = parse(cutoff)
    hl = cfg["halflife"]
    for g in games:
        if not g.get("final") or g.get("hs") is None or g["date"] >= cutoff:
            continue
        w = 0.5 ** ((cut - parse(g["date"])).days / hl)
        hf = 0 if g.get("neutral") else 1
        obs.append((g["home"], g["away"], g["hs"], hf, w))
        obs.append((g["away"], g["home"], g["as"], -hf, w))
    if not obs:
        return None
    teams = {o[0] for o in obs} | {o[1] for o in obs}
    off = {t: 0.0 for t in teams}
    dfn = {t: 0.0 for t in teams}
    pr = priors or {}
    lam = cfg["ridge"]
    wsum = sum(o[4] for o in obs)
    mu = sum(o[2] * o[4] for o in obs) / wsum
    hh = 0.0
    for _ in range(20):
        so, wo, sd, wd = {}, {}, {}, {}
        hnum = hden = 0.0
        for t, o, s, hf, w in obs:
            r = s - mu - hf * hh
            so[t] = so.get(t, 0) + w * (r - dfn[o]); wo[t] = wo.get(t, 0) + w
            sd[o] = sd.get(o, 0) + w * (r - off[t]); wd[o] = wd.get(o, 0) + w
            if hf:
                hnum += w * hf * (s - mu - off[t] - dfn[o]); hden += w
        for t in teams:
            p = pr.get(t, {})
            off[t] = (so.get(t, 0) + lam * p.get("off", 0.0)) / (wo.get(t, 0) + lam)
            dfn[t] = (sd.get(t, 0) + lam * p.get("def", 0.0)) / (wd.get(t, 0) + lam)
        hh = hnum / hden if hden else 0.0
        mu = sum(w * (s - off[t] - dfn[o] - hf * hh) for t, o, s, hf, w in obs) / wsum
    n = {}
    for t, o, s, hf, w in obs:
        n[t] = n.get(t, 0) + 1
    return {"mu": mu, "hh": hh, "off": off, "def": dfn, "n": n}


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def find(model, name):
    if not model:
        return None
    key = norm(name)
    for t in model["off"]:
        if norm(t) == key:
            return t
    return None


def project(model, home, away, neutral, cfg):
    h, a = find(model, home), find(model, away)
    if not h or not a:
        return None
    hf = 0 if neutral else 1
    sh = model["mu"] + model["off"][h] + model["def"][a] + hf * model["hh"]
    sa = model["mu"] + model["off"][a] + model["def"][h] - hf * model["hh"]
    out = {"homeScore": round(sh, 2), "awayScore": round(sa, 2),
           "margin": round(sh - sa, 2), "total": round(sh + sa, 2)}
    if cfg["kind"] == "hockey":
        ph, pt, pa = outcome_probs(max(sh, 0.3), max(sa, 0.3))
        share = max(sh, 0.3) / (max(sh, 0.3) + max(sa, 0.3))
        out["pHome"] = round(ph + pt * share, 4)
    if cfg["kind"] == "soccer":
        ph, pdr, pa = outcome_probs(max(sh, 0.2), max(sa, 0.2))
        out.update(pHome=round(ph, 4), pDraw=round(pdr, 4), pAway=round(pa, 4),
                   pOver25=round(p_over(max(sh, 0.2), max(sa, 0.2), 2.5), 4))
    return out


# ---------- calibration ----------

def slope(pairs):
    """Least-squares slope with an intercept, so an average bias between results and the
    line is not mistaken for skill."""
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
    n = len(pairs)
    if n < MIN_N:
        return None, n, None
    mx = sum(x for x, _ in pairs) / n
    my = sum(y for _, y in pairs) / n
    sxx = sum((x - mx) ** 2 for x, _ in pairs)
    if not sxx:
        return None, n, None
    k = sum((x - mx) * (y - my) for x, y in pairs) / sxx
    b = my - k * mx
    se = (sum((y - b - k * x) ** 2 for x, y in pairs) / (n - 2) / sxx) ** 0.5
    return round(k, 3), n, round(se, 3)


def clip(k):
    return 0.0 if k is None else round(max(0.0, min(K_MAX, k)), 3)


def logloss_k(rows):
    """rows: (model probs, market probs, outcome index). Best blend weight on a 0..0.5 grid."""
    if len(rows) < MIN_N:
        return None, len(rows), None, None, None
    def ll(k):
        tot = 0.0
        for mp, mk, y in rows:
            p = mk[y] + k * (mp[y] - mk[y])
            tot -= math.log(min(max(p, 1e-6), 1))
        return tot / len(rows)
    grid = [i / 20 for i in range(0, 11)]
    best = min(grid, key=ll)
    if ll(0.0) - ll(best) < MIN_GAIN:      # a gain this small is noise: trust the market
        best = 0.0
    return best, len(rows), round(ll(0.0), 4), round(ll(1.0), 4), round(ll(best), 4)


def backtest(games, cfg, start_days=45):
    final = sorted((g for g in games if g.get("final") and g.get("hs") is not None), key=lambda g: g["date"])
    if not final:
        return []
    first = parse(final[0]["date"]) + timedelta(days=start_days)
    out, model, refit_at = [], None, None
    for g in final:
        t = parse(g["date"])
        if t < first:
            continue
        if refit_at is None or t >= refit_at:
            model = fit(final, iso(t.replace(hour=0, minute=0, second=0)), cfg)
            refit_at = t + timedelta(days=7)
        p = project(model, g["home"], g["away"], g.get("neutral"), cfg)
        if p:
            out.append((g, p))
    return out


def calibrate(sport, cfg, games):
    samples = backtest(games, cfg)
    cal = {"asOf": iso(now_utc()), "sport": sport, "backtestGames": len(samples)}
    kind = cfg["kind"]
    if kind == "points":
        side, move, tot, tmove, big, mae = [], [], [], [], [], {"market": [], "raw": []}
        for g, p in samples:
            L = g.get("lines") or {}
            res = g["hs"] - g["as"]
            if L.get("spreadClose") is not None:
                close = -L["spreadClose"]
                side.append((p["margin"] - close, res - close))
                mae["market"].append(abs(res - close)); mae["raw"].append(abs(res - p["margin"]))
                if abs(p["margin"] - close) >= BIG_GAP.get(sport, 5):
                    big.append((p["margin"] - close) * (res - close))
                if L.get("spreadOpen") is not None:
                    opn = -L["spreadOpen"]
                    move.append((p["margin"] - opn, close - opn))
            if L.get("totalClose") is not None:
                tot.append((p["total"] - L["totalClose"], g["hs"] + g["as"] - L["totalClose"]))
                if L.get("totalOpen") is not None:
                    tmove.append((p["total"] - L["totalOpen"], L["totalClose"] - L["totalOpen"]))
        if not side:
            side = ledger_pairs(sport, cfg, games)
            cal["note"] = "No free line history for this sport. Calibrating on the ledger's own closes."
        ks, ns, ses = slope(side)
        km, nm, sem = slope(move)
        kt, nt, set_ = slope(tot)
        ktm, ntm, setm = slope(tmove)
        cal.update({
            "kSide": clip(ks), "side": {"kRaw": ks, "n": ns, "se": ses},
            "moveSide": {"kMove": km, "n": nm, "se": sem},
            "kTotal": clip(kt), "total": {"kRaw": kt, "n": nt, "se": set_},
            "moveTotal": {"kMove": ktm, "n": ntm, "se": setm},
            "bigGap": {"gapAtLeast": BIG_GAP.get(sport, 5), "games": len(big),
                       "modelSideWon": sum(1 for v in big if v > 0), "modelSideLost": sum(1 for v in big if v < 0)},
            "maeMarketSide": round(sum(mae["market"]) / len(mae["market"]), 2) if mae["market"] else None,
            "maeRawSide": round(sum(mae["raw"]) / len(mae["raw"]), 2) if mae["raw"] else None,
        })
    else:
        rows, move, trows, tmove = [], [], [], []
        for g, p in samples:
            L = g.get("lines") or {}
            goals = g["hs"] + g["as"]
            if kind == "hockey":
                if L.get("mlHomeClose") and L.get("mlAwayClose"):
                    mk = novig([L["mlHomeClose"], L["mlAwayClose"]])
                    y = 0 if g["hs"] > g["as"] else 1
                    rows.append(([p["pHome"], 1 - p["pHome"]], mk, y))
                    if L.get("mlHomeOpen") and L.get("mlAwayOpen"):
                        mo = novig([L["mlHomeOpen"], L["mlAwayOpen"]])
                        move.append((p["pHome"] - mo[0], mk[0] - mo[0]))
                line = L.get("totalClose")
                if line is not None and L.get("overCloseOdds") and L.get("underCloseOdds") and goals != line:
                    mk = novig([L["overCloseOdds"], L["underCloseOdds"]])
                    pm = p_over(max(p["homeScore"], 0.3), max(p["awayScore"], 0.3), line)
                    trows.append(([pm, 1 - pm], mk, 0 if goals > line else 1))
                    if L.get("totalOpen") == line and L.get("overOpenOdds") and L.get("underOpenOdds"):
                        mo = novig([L["overOpenOdds"], L["underOpenOdds"]])
                        tmove.append((pm - mo[0], mk[0] - mo[0]))
            else:
                c = [L.get("decHomeClose"), L.get("decDrawClose"), L.get("decAwayClose")]
                if all(c):
                    inv = [1 / x for x in c]; sm = sum(inv); mk = [v / sm for v in inv]
                    y = 0 if g["hs"] > g["as"] else (1 if g["hs"] == g["as"] else 2)
                    rows.append(([p["pHome"], p["pDraw"], p["pAway"]], mk, y))
                    o = [L.get("decHomeOpen"), L.get("decDrawOpen"), L.get("decAwayOpen")]
                    if all(o):
                        inv = [1 / x for x in o]; sm = sum(inv); mo = [v / sm for v in inv]
                        move.append((p["pHome"] - mo[0], mk[0] - mo[0]))
                if L.get("decOverClose") and L.get("decUnderClose"):
                    inv = [1 / L["decOverClose"], 1 / L["decUnderClose"]]; sm = sum(inv); mk = [v / sm for v in inv]
                    trows.append(([p["pOver25"], 1 - p["pOver25"]], mk, 0 if goals > 2.5 else 1))
                    if L.get("decOverOpen") and L.get("decUnderOpen"):
                        inv = [1 / L["decOverOpen"], 1 / L["decUnderOpen"]]; sm = sum(inv); mo = [v / sm for v in inv]
                        tmove.append((p["pOver25"] - mo[0], mk[0] - mo[0]))
        kp, n, ll_market, ll_model, ll_blend = logloss_k(rows)
        ktp, tn, tll_market, tll_model, tll_blend = logloss_k(trows)
        km, nm, sem = slope(move)
        ktm, ntm, setm = slope(tmove)
        cal.update({
            "kProb": 0.0 if kp is None else kp,
            "prob": {"n": n, "logLossMarket": ll_market, "logLossModel": ll_model, "logLossBlend": ll_blend},
            "moveProb": {"kMove": km, "n": nm, "se": sem},
            "kTotalProb": 0.0 if ktp is None else ktp,
            "totalProb": {"n": tn, "logLossMarket": tll_market, "logLossModel": tll_model, "logLossBlend": tll_blend},
            "moveTotalProb": {"kMove": ktm, "n": ntm, "se": setm},
        })
    cal["read"] = ("k (kSide, kTotal, kProb) is how much of the model's gap from the closing market held up in "
                   "results. 0 means the market already knows what these ratings know. kMove above 0 means the "
                   "model's gap from the OPEN tended to be where the line moved by the close, which is the edge "
                   "that beats the close. Use the fair numbers in matchups as given.")
    return cal


def ledger_pairs(sport, cfg, games):
    """For sports without line history: graded closes from the ledger itself."""
    if not LEDGER.exists():
        return []
    pairs, cache = [], {}
    for r in json.loads(LEDGER.read_text()).get("rows") or []:
        if r.get("sport") != sport or r.get("market") != "spread" or "closeSnap" not in r or not r.get("final"):
            continue
        day = r["commence"][:10] + "T00:00:00Z"
        if day not in cache:
            cache[day] = fit(games, day, cfg)
        p = project(cache[day], r["home"], r["away"], False, cfg)
        if not p:
            continue
        close = -r["closeSnap"]["line"]
        pairs.append((p["margin"] - close, r["score"]["home"] - r["score"]["away"] - close))
    return pairs


# ---------- matchups ----------

def matchups(sport, cfg, model, cal):
    if not LEDGER.exists():
        return []
    now = iso(now_utc())
    by = {}
    for r in json.loads(LEDGER.read_text()).get("rows") or []:
        if r.get("sport") != sport or not r.get("commence") or r["commence"] <= now or "lastSnap" not in r:
            continue
        by.setdefault((r["home"], r["away"], r["commence"]), {})[r["market"]] = r
    out, missing = [], set()
    for (home, away, commence), mk in sorted(by.items(), key=lambda kv: kv[0][2]):
        p = project(model, home, away, False, cfg)
        item = {"event": f"{away} at {home}", "commence": commence}
        if not p:
            for t in (home, away):
                if not find(model, t):
                    missing.add(t)
            item["note"] = "no rating for one team"
            out.append(item)
            continue
        item["raw"] = p
        sp = mk.get("spread")
        if sp and cfg["kind"] == "points":
            line = sp["lastSnap"]["line"]
            fair_margin = -line + cal["kSide"] * (p["margin"] + line)
            fair_line = round(-fair_margin, 2)
            edge = round(abs(line - fair_line), 2)
            bar = cfg["bar"]["spread"]
            item["spread"] = {"rowId": sp["id"], "marketHomeLine": line, "fairHomeLine": fair_line,
                              "lean": "home" if fair_line < line else "away", "edge": edge, "bar": bar,
                              "clears": "full" if edge >= bar else ("half" if edge >= bar / 2 else "no"),
                              "projectionForPick": fair_line}
        tt = mk.get("total")
        if tt and cfg["kind"] in ("hockey", "soccer"):
            s = tt["lastSnap"]; line = s["line"]
            pm = p_over(max(p["homeScore"], 0.2), max(p["awayScore"], 0.2), line)
            mkt = novig([s["over"], s["under"]])
            k = cal.get("kTotalProb", 0.0)
            fo = mkt[0] + k * (pm - mkt[0])
            e_over, e_under = fo - implied(s["over"]), (1 - fo) - implied(s["under"])
            side, edge = ("over", e_over) if e_over >= e_under else ("under", e_under)
            bar = cfg["bar"]["h2h"]
            item["total"] = {"rowId": tt["id"], "marketTotal": line, "marketNoVigOver": round(mkt[0], 4),
                             "modelOver": round(pm, 4), "fairOver": round(fo, 4), "lean": side,
                             "edge": round(edge, 4), "edgeUnit": "prob", "bar": bar,
                             "clears": "full" if edge >= bar else ("half" if edge >= bar / 2 else "no"),
                             "projectionForPick": round(fo, 4),
                             "note": "projection is the fair probability of the OVER"}
            tt = None
        if tt:
            line = tt["lastSnap"]["line"]
            fair = round(line + cal["kTotal"] * (p["total"] - line), 2)
            edge = round(abs(fair - line), 2)
            bar = cfg["bar"]["total"]
            item["total"] = {"rowId": tt["id"], "marketTotal": line, "fairTotal": fair,
                             "lean": "over" if fair > line else "under", "edge": edge, "bar": bar,
                             "clears": "full" if edge >= bar else ("half" if edge >= bar / 2 else "no"),
                             "projectionForPick": fair}
        h2 = mk.get("h2h")
        if h2 and "pHome" in p:
            s = h2["lastSnap"]
            if "draw" in s:
                mkt = novig([s["home"], s["draw"], s["away"]]); model_p = [p["pHome"], p["pDraw"], p["pAway"]]
                names = ["home", "draw", "away"]
            else:
                mkt = novig([s["home"], s["away"]]); model_p = [p["pHome"], 1 - p["pHome"]]
                names = ["home", "away"]
            k = cal.get("kProb", 0.0)
            fair = [m + k * (q - m) for q, m in zip(model_p, mkt)]
            sides = []
            for i, nme in enumerate(names):
                if nme == "draw":
                    continue
                edge = fair[i] - implied(s[nme])
                sides.append((edge, nme, fair[i]))
            edge, side, fp = max(sides)
            bar = cfg["bar"]["h2h"]
            item["h2h"] = {"rowId": h2["id"], "marketNoVig": [round(x, 4) for x in mkt],
                           "fair": [round(x, 4) for x in fair], "lean": side, "edge": round(edge, 4), "bar": bar,
                           "clears": "full" if edge >= bar else ("half" if edge >= bar / 2 else "no"),
                           "projectionForPick": round(fp, 4)}
        out.append(item)
    return out, sorted(missing)


def team_table(model, games):
    if not model:
        return {}
    last = {}
    for g in sorted(games, key=lambda g: g["date"]):
        if g.get("final"):
            last[g["home"]] = g["date"][:10]; last[g["away"]] = g["date"][:10]
    rows = {t: {"off": round(model["off"][t], 3), "def": round(model["def"][t], 3),
                "net": round(model["off"][t] - model["def"][t], 3), "games": model["n"].get(t, 0),
                "lastGame": last.get(t)} for t in model["off"]}
    return dict(sorted(rows.items(), key=lambda kv: -kv[1]["net"]))


def promoted_priors(games):
    """Soccer: a team with no games in the previous season was promoted. Start it below average."""
    seasons = sorted({g.get("season") for g in games if g.get("season")})
    if len(seasons) < 2:
        return {}
    prev = {t for g in games if g.get("season") == seasons[-2] for t in (g["home"], g["away"])}
    cur = {t for g in games if g.get("season") == seasons[-1] for t in (g["home"], g["away"])}
    return {t: {"off": -0.15, "def": 0.15} for t in cur - prev}


def run(sport):
    cfg = CONFIG[sport]
    games, info = (update_epl if cfg["kind"] == "soccer" else update_espn)(sport, cfg)
    model = fit(games, iso(now_utc()), cfg, promoted_priors(games) if cfg["kind"] == "soccer" else None)
    cal = calibrate(sport, cfg, games)
    cal["fetch"] = info
    (OUT / f"{sport.lower()}_calibration.json").write_text(json.dumps(cal, indent=2) + "\n")
    (OUT / f"{sport.lower()}_teams.json").write_text(json.dumps({
        "asOf": iso(now_utc()), "sport": sport,
        "model": {"mu": round(model["mu"], 3), "homeEdge": round(2 * model["hh"], 3)} if model else None,
        "note": "Scores per game relative to average, recent games weighted more. off: higher scores more. "
                "def: higher allows more. net = off - def.",
        "teams": team_table(model, games)}, indent=2) + "\n")
    games_out, missing = matchups(sport, cfg, model, cal) if model else ([], [])
    (OUT / f"{sport.lower()}_matchups.json").write_text(json.dumps({
        "asOf": iso(now_utc()), "sport": sport,
        "k": {k: cal.get(k) for k in ("kSide", "kTotal", "kProb", "kTotalProb") if k in cal},
        "unmatchedTeams": missing, "games": games_out}, indent=2) + "\n")
    summary = {"sport": sport, "games": len(games), "backtest": cal["backtestGames"],
               **{k: cal.get(k) for k in ("kSide", "kTotal", "kProb", "kTotalProb") if k in cal},
               "upcoming": len(games_out), "unmatched": len(missing)}
    for key in ("moveSide", "moveProb"):
        if key in cal:
            summary["kMove"] = cal[key]["kMove"]
    return summary


def main():
    sports = [s.upper() for s in sys.argv[1:]] or list(CONFIG)
    for s in sports:
        try:
            print(json.dumps(run(s)))
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"sport": s, "error": str(exc)[:300]}))


if __name__ == "__main__":
    main()
