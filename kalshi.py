#!/usr/bin/env python3
"""EDGE Kalshi desk (v1). Prices Kalshi's game contracts against Pinnacle and EDGE's picks, sizes trades
from Zack's bankroll rules, keeps a paper book always, and places real orders only while Zack's switch is On.

  python3 kalshi.py           scan, settle, trade (paper always; real orders only while the switch is On)
  python3 kalshi.py --dry     scan and print candidates, write nothing

Signal sources (each tracked on its own record)
  kalshi-sharp      Kalshi contract on the same number Pinnacle hangs (or a winner market with a Pinnacle
                    moneyline). Fair = Pinnacle price with the margin removed by Shin's method (fair.py).
  kalshi-sharp-alt  Kalshi contract up to 1 point off Pinnacle's number (NFL, NCAAF, NBA). Fair is moved with
                    grade.py's per-point values. Estimated.
  mirror:<pattern>  An EDGE A or B pick, placed on the matching Kalshi contract. Fair = the Pinnacle fair at that
                    contract plus the pick's own edge.

Value
  cost per contract = ask + Kalshi taker fee (0.07 x price x (1 - price), rounded up per order)
  edge              = fair probability - cost. A trade needs edge >= minEdge (config).
  size              = kellyFraction x Kelly stake on current equity, capped by maxPerTradePct and maxPerDay.

Books
  paper  every source, every qualifying contract, sized from startingBankroll, each source with its own daily
         cap so none crowds another out. Never places an order and never stops: where stopLoss or takeProfit
         would have hit is recorded instead.
  live   real orders, only while Zack's switch on the site is On and not paused (read from /api/control at
         the start of every run; unreadable = off), only from the sources he allows, sized from the starting
         balance he set. Switching On starts a new session at that balance; the old session is archived.
  One position per game, market (winner, spread or total) and source in each book: the best edge is taken,
  never several neighbouring strikes or both sides of the same bet.
  A book stops when its equity reaches its start - stopLoss or + takeProfit. A stopped live session stays
  stopped until Zack switches trading off and on again, which starts a new session.

Safety
  No order on a game that has started, on a Pinnacle price older than PIN_STALE_MIN, on a ledger price older
  than SNAP_STALE_MIN, or outside priceBand. One trade per contract, side and source, ever.
  Keys come only from environment variables (GitHub secrets); nothing secret is written to a file.
"""

import base64
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import fair
import pull

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "trading" / "config.json"
BOOK = ROOT / "trading" / "ledger.json"
PROD = "https://api.elections.kalshi.com/trade-api/v2"
CONTROL_URL = os.environ.get("EDGE_CONTROL_URL", "https://edgesystem.netlify.app/api/control")
DEMO = "https://demo-api.kalshi.co/trade-api/v2"
ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")
SERIES = {
    "NFL": {"game": "KXNFLGAME", "spread": "KXNFLSPREAD", "total": "KXNFLTOTAL"},
    "NCAAF": {"game": "KXNCAAFGAME", "spread": "KXNCAAFSPREAD", "total": "KXNCAAFTOTAL"},
    "NBA": {"game": "KXNBAGAME", "spread": "KXNBASPREAD", "total": "KXNBATOTAL"},
    "NHL": {"game": "KXNHLGAME", "spread": "KXNHLSPREAD", "total": "KXNHLTOTAL"},
    "UCL": {"game": "KXUCLGAME", "total": "KXUCLTOTAL"},
    "EPL": {"game": "KXEPLGAME", "total": "KXEPLTOTAL"},
    "UEL": {"game": "KXUELGAME", "total": "KXUELTOTAL"},
    "LaLiga": {"game": "KXLALIGAGAME", "total": "KXLALIGATOTAL"},
    "SerieA": {"game": "KXSERIEAGAME", "total": "KXSERIEATOTAL"},
    "Bundesliga": {"game": "KXBUNDESLIGAGAME", "total": "KXBUNDESLIGATOTAL"},
    "Ligue1": {"game": "KXLIGUE1GAME", "total": "KXLIGUE1TOTAL"},
    "MLS": {"game": "KXMLSGAME", "total": "KXMLSTOTAL"},
    "ATP": {"game": "KXATPMATCH"},
    "WTA": {"game": "KXWTAMATCH"},
}
# Tennis tickers carry the local match date, which can be a day off US Eastern; look one day either side.
DAY_SLACK = {"ATP": 1, "WTA": 1}
PER_POINT = {("NFL", "spread"): 0.030, ("NFL", "total"): 0.022, ("NCAAF", "spread"): 0.025,
             ("NCAAF", "total"): 0.018, ("NBA", "spread"): 0.030, ("NBA", "total"): 0.025}
MARGIN_SD = {"NFL": 13.5, "NCAAF": 15.5, "NBA": 12.0}   # spread -> win probability, normal approximation
# Off: on the first scan a normal curve made every NFL underdog look 4-6 cents cheap, a model artefact, not value.
# Winner markets for spread sports are priced from the real Pinnacle moneyline pull.py stores (since 2026-10-14).
WINNER_FROM_SPREAD = False
ALT_MAX = 1.0
PIN_STALE_MIN = 60
SNAP_STALE_MIN = 90
MIN_LEAD_MIN = 5
FEE_RATE = 0.07
MAX_EDGE = 0.10        # bigger than this is a matching or data error, never a trade


# ---------- small helpers ----------

def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fee(price, count=1):
    """Kalshi taker fee for one order, rounded up to the cent."""
    return math.ceil(FEE_RATE * count * price * (1 - price) * 100 - 1e-9) / 100


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


# ---------- Kalshi API ----------

def api_get(base, path, params=None):
    """Public read. Paced, and retried with backoff when Kalshi says too many requests."""
    url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(5):
        time.sleep(0.25)
        req = urllib.request.Request(url, headers={"User-Agent": "EDGE desk", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 4:
                raise
            time.sleep(2 ** attempt)


def markets(base, series):
    out, cursor = [], None
    for _ in range(20):
        params = {"series_ticker": series, "status": "open", "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        d = api_get(base, "/markets", params)
        out += d.get("markets") or []
        cursor = d.get("cursor")
        if not cursor:
            break
    return out


def events(base, series):
    out, cursor = {}, None
    for _ in range(10):
        params = {"series_ticker": series, "status": "open", "limit": 200}
        if cursor:
            params["cursor"] = cursor
        d = api_get(base, "/events", params)
        for e in d.get("events") or []:
            out[e["event_ticker"]] = e
        cursor = d.get("cursor")
        if not cursor:
            break
    return out


class Signer:
    """Signs requests with the Kalshi key from the environment (RSA-PSS SHA-256 or Ed25519)."""

    def __init__(self, key_id, pem):
        from cryptography.hazmat.primitives import serialization   # only needed for real orders
        self.key_id = key_id
        self.key = serialization.load_pem_private_key(pem.encode(), password=None)

    def headers(self, method, path):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        ts = str(int(time.time() * 1000))
        msg = (ts + method.upper() + path.split("?", 1)[0]).encode()
        if isinstance(self.key, Ed25519PrivateKey):
            sig = self.key.sign(msg)
        else:
            sig = self.key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                                 salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())
        return {"KALSHI-ACCESS-KEY": self.key_id, "KALSHI-ACCESS-TIMESTAMP": ts,
                "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(), "User-Agent": "EDGE desk",
                "Accept": "application/json", "Content-Type": "application/json"}

    def call(self, base, method, path, body=None):
        full = urllib.parse.urlparse(base).path + path
        req = urllib.request.Request(base + path, method=method, headers=self.headers(method, full),
                                     data=json.dumps(body).encode() if body is not None else None)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())


# ---------- matching Kalshi events to ledger games ----------

def ticker_date(event_ticker):
    m = re.search(r"-(\d{2})([A-Z]{3})(\d{2})", event_ticker)
    if not m:
        return None
    try:
        return datetime.strptime(f"20{m.group(1)}{m.group(2)}{m.group(3)}", "%Y%b%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def words(s):
    return [w for w in re.sub(r"[^a-z0-9 ]", " ", (s or "").lower().replace("st.", "state")).split() if w]


def team_score(kalshi, ledger):
    """How well a Kalshi team label ('SEA Seahawks', 'Los Angeles L', 'Kennesaw St.') fits a ledger name."""
    k, l = words(kalshi), words(ledger)
    if not k or not l:
        return 0.0
    letter = k[-1] if len(k[-1]) == 1 and len(k) > 1 else None
    body = k[:-1] if letter else k
    hits = sum(1 for w in body if any(x.startswith(w) or w.startswith(x) for x in l if len(x) >= 2))
    score = hits / len(body)
    if letter:
        rest = [x for x in l if x not in body]
        score = score if rest and rest[0].startswith(letter) else score * 0.4
    return score


def split_title(title):
    t = (title or "").split(":")[0]
    for sep in (" vs. ", " vs ", " at ", " @ "):
        if sep in t:
            a, h = t.split(sep, 1)
            return a.strip(), h.strip()
    return None, None


def ledger_games(rows, sports):
    """(sport, ET date) -> list of games, each with its ledger rows by market."""
    games = {}
    for r in rows:
        if r.get("sport") not in sports or not r.get("commence"):
            continue
        d = pull.parse(r["commence"]).astimezone(ET).strftime("%Y-%m-%d")
        key = (r["sport"], r["home"], r["away"], r["commence"])
        g = games.setdefault(key, {"sport": r["sport"], "home": r["home"], "away": r["away"],
                                   "commence": r["commence"], "date": d, "rows": {}})
        g["rows"][r["market"]] = r
    out = {}
    for g in games.values():
        out.setdefault((g["sport"], g["date"]), []).append(g)
    return out


def match_game(sport, event, by_day):
    """The ledger game for a Kalshi event, and Kalshi's labels by side: (game, {"home": .., "away": ..}).
    'A at B' is away at home. 'A vs B' is home first on soccer and away first on some US series, so both
    orientations are scored and the better one must win clearly (2026-10-14: a reversed soccer match priced
    the wrong team)."""
    d = ticker_date(event["event_ticker"])
    title = (event.get("title") or "").split(":")[0]
    first, second = split_title(title)
    if not d or not first:
        return None, None
    fixed = " at " in title or " @ " in title
    best, best_s, best_lab, runner = None, 0.0, None, 0.0
    slack = DAY_SLACK.get(sport, 0)
    day0 = datetime.strptime(d, "%Y-%m-%d")
    days = [(day0 + timedelta(days=k)).strftime("%Y-%m-%d") for k in range(-slack, slack + 1)]
    for g in [g for dd in days for g in by_day.get((sport, dd), [])]:
        a_first = min(team_score(first, g["away"]), team_score(second, g["home"]))
        h_first = 0.0 if fixed else min(team_score(first, g["home"]), team_score(second, g["away"]))
        for s, lab in ((a_first, {"away": first, "home": second}), (h_first, {"home": first, "away": second})):
            if s > best_s:
                runner = max(runner, best_s)
                best, best_s, best_lab = g, s, lab
            else:
                runner = max(runner, s)
    if best_s < 0.5 or best_s - runner < 0.25:
        return None, None
    return best, best_lab


# ---------- fair prices ----------

def pin(row, now):
    """Pinnacle prices on a ledger row, if fresh."""
    snap = (row or {}).get("lastSnap") or {}
    p = (snap.get("books") or {}).get("pinnacle")
    if not p or not snap.get("time"):
        return None
    if (now - pull.parse(snap["time"])).total_seconds() / 60 > SNAP_STALE_MIN:
        return None
    if p.get("updated") and (now - pull.parse(p["updated"])).total_seconds() / 60 > PIN_STALE_MIN:
        return None
    return p


def key_adj(sport, a, b):
    """Extra value for crossing 3 or 7 between two NFL/NCAAF margins, signed toward b > a."""
    if sport not in ("NFL", "NCAAF") or a == b:
        return 0.0
    lo, hi = sorted((abs(a), abs(b)))
    crossed = sum(1 for k in (3, 7) if lo < k <= hi or lo <= k < hi)
    return 0.03 * crossed


def fair_for(sport, kind, team_side, strike, game, now):
    """Fair YES probability for a Kalshi contract and whether it is estimated.
    kind: game | spread | total. team_side: home | away | draw | over."""
    if kind == "total":
        r = game["rows"].get("total")
        p = pin(r, now)
        if not p or "over" not in p or p.get("line") is None:
            return None, None
        base = fair.probs(p, ["over", "under"])["over"]
        gap = p["line"] - strike                 # strike below Pinnacle's line: over is easier
        if gap == 0:
            return base, False
        if (sport, "total") in PER_POINT and abs(gap) <= ALT_MAX:
            return min(max(base + PER_POINT[(sport, "total")] * gap, 0.01), 0.99), True
        return None, None
    if kind == "spread":
        r = game["rows"].get("spread")
        p = pin(r, now)
        if not p or p.get("line") is None or "home" not in p:
            return None, None
        probs = fair.probs(p, ["home", "away"])
        # Pinnacle home line H: home covers when margin > -H; away covers when away margin > H.
        need = -p["line"] if team_side == "home" else p["line"]
        base = probs[team_side]
        gap = need - strike                      # Kalshi needs fewer points than Pinnacle: easier
        if gap == 0:
            return base, False
        if (sport, "spread") in PER_POINT and abs(gap) <= ALT_MAX:
            adj = PER_POINT[(sport, "spread")] * gap + math.copysign(key_adj(sport, need, strike), gap)
            return min(max(base + adj, 0.01), 0.99), True
        return None, None
    # winner
    r = game["rows"].get("h2h")
    p = pin(r, now)
    if p and "home" in p and "away" in p:
        keys = [k for k in ("home", "away", "draw") if k in p]
        probs = fair.probs(p, keys)
        if team_side in probs:
            return probs[team_side], False
        return None, None
    if WINNER_FROM_SPREAD and sport in MARGIN_SD and team_side in ("home", "away"):
        rs = game["rows"].get("spread")
        p = pin(rs, now)
        if not p or p.get("line") is None or "home" not in p:
            return None, None
        probs = fair.probs(p, ["home", "away"])
        # mean margin implied by the fair cover probability at Pinnacle's line
        mu = -p["line"] + MARGIN_SD[sport] * _inv_norm(probs["home"])
        ph = 1 - norm_cdf((0.5 - mu) / MARGIN_SD[sport])      # home wins by at least 1 (ties are rare)
        return (ph if team_side == "home" else 1 - ph), True
    return None, None


def _inv_norm(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    lo, hi = -8.0, 8.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def side_of(label, game):
    """home or away for a Kalshi team label. Kalshi's own event labels decide first (exact, then prefix);
    ledger-name similarity only breaks what they cannot. None if still unclear."""
    lab = re.sub(r"[^a-z0-9]", "", (label or "").lower())
    labels = {k: re.sub(r"[^a-z0-9]", "", (v or "").lower()) for k, v in (game.get("labels") or {}).items()}
    exact = [k for k, v in labels.items() if v and v == lab]
    if len(exact) == 1:
        return exact[0]
    pre = [k for k, v in labels.items() if v and (v.startswith(lab) or lab.startswith(v))]
    if len(pre) == 1:
        return pre[0]
    hs, as_ = team_score(label, game["home"]), team_score(label, game["away"])
    if max(hs, as_) < 0.5 or abs(hs - as_) < 0.25:
        return None
    return "home" if hs > as_ else "away"


def parse_market(sport, kind, m, game):
    """Which side of the game a Kalshi contract's YES is: (team_side, strike) or None."""
    sub = m.get("yes_sub_title") or m.get("title") or ""
    if kind == "total":
        if m.get("strike_type") not in (None, "greater"):
            return None
        s = f(m.get("floor_strike"))
        return ("over", s) if s is not None else None
    if kind == "spread":
        s = f(m.get("floor_strike"))
        team = re.split(r"\s+wins by", sub)[0]
        side = side_of(team, game)
        return (side, s) if s is not None and side else None
    if re.search(r"\btie\b", sub, re.I):
        return ("draw", None)
    team = re.split(r"\s+wins", sub)[0]
    side = side_of(team, game)
    return (side, None) if side else None


# ---------- EDGE picks mirrored ----------

def mirror_fair(pick, sport, kind, team_side, strike, base):
    """Fair for an EDGE pick placed on a Kalshi contract on the same side: Pinnacle's fair there plus the pick's edge."""
    if pick["market"] != {"game": "h2h"}.get(kind, kind) or pick["side"] != team_side:
        return None
    if pick.get("edgeUnit") == "prob":
        return min(base + pick["edge"], 0.99)
    slope = PER_POINT.get((sport, kind))
    if not slope:
        return None
    return min(base + slope * pick["edge"], 0.99)


# ---------- the books ----------

def new_book(cfg):
    return {"start": cfg["startingBankroll"], "cash": cfg["startingBankroll"], "trades": [], "equity": [],
            "stopped": None}


def book_state(book):
    open_cost = sum(t["cost"] + t["fee"] for t in book["trades"] if t["status"] == "open")
    realized = sum(t.get("pnl", 0) for t in book["trades"] if t["status"] == "settled")
    clv = [t["clv"] for t in book["trades"] if t.get("clv") is not None]
    return {"open": round(open_cost, 2), "realized": round(realized, 2),
            "equity": round(book["start"] + realized, 2),
            "clvN": len(clv), "meanClv": round(sum(clv) / len(clv), 4) if clv else None}


def check_stop(book, cfg, now):
    st = book_state(book)
    if st["equity"] <= book["start"] - cfg["stopLoss"]:
        return "stop-loss"
    if st["equity"] >= book["start"] + cfg["takeProfit"]:
        return "take-profit"
    return None


def spent_today(book, now, source=None):
    day = now.astimezone(CT).strftime("%Y-%m-%d")
    return sum(t["cost"] + t["fee"] for t in book["trades"]
               if pull.parse(t["time"]).astimezone(CT).strftime("%Y-%m-%d") == day
               and (source is None or t["source"] == source))


def size(cfg, book, price, prob, now, source=None):
    """Contracts to buy: fractional Kelly on equity, capped per trade and per day.
    source: the paper book caps each source separately so one cannot crowd out another."""
    st = book_state(book)
    equity = st["equity"]
    c = price + FEE_RATE * price * (1 - price)
    k = max((prob - c) / (1 - c), 0.0)
    room = equity - st["open"] if source is None else equity
    stake = min(cfg["kellyFraction"] * k * equity, cfg["maxPerTradePct"] / 100 * equity,
                cfg["maxPerDay"] - spent_today(book, now, source), room)
    n = int(stake // c) if stake > 0 else 0
    while n > 0 and n * price + fee(price, n) > stake + 1e-9:
        n -= 1
    return n


def settle(book, base, now):
    done = 0
    for t in book["trades"]:
        if t["status"] != "open" or pull.parse(t["commence"]) + timedelta(hours=3) > now:
            continue
        try:
            m = api_get(base, f"/markets/{t['ticker']}").get("market") or {}
        except Exception as exc:  # noqa: BLE001
            print("settle", t["ticker"], exc)
            continue
        res = (m.get("result") or "").lower()
        if res not in ("yes", "no"):
            continue
        payout = t["count"] * (1.0 if res == t["side"] else 0.0)
        t.update(status="settled", result=res, won=res == t["side"], payout=payout,
                 pnl=round(payout - t["cost"] - t["fee"], 2), settledAt=iso(now))
        done += 1
    return done


def snapshot(book, now):
    st = book_state(book)
    last = book["equity"][-1] if book["equity"] else None
    if not last or last["equity"] != st["equity"] or last["open"] != st["open"]:
        book["equity"].append({"t": iso(now), **st})
        book["equity"] = book["equity"][-3000:]


# ---------- CS2 (cs2.py ratings, no sportsbook price) ----------

QUOTES = {}
CS2_SERIES = "KXCS2GAME"
CS2_RATINGS = ROOT / "stats" / "cs2_ratings.json"
CS2_MAX_EDGE = 0.15        # a model, not a sharp price: bigger gaps are more likely a rating error


def cs2_name_score(label, team):
    best = 0.0
    for name in (team.get("name"), team.get("acronym")):
        if not name:
            continue
        a = re.sub(r"[^a-z0-9]", "", label.lower())
        b = re.sub(r"[^a-z0-9]", "", name.lower())
        if a and b and (a == b or (len(min(a, b, key=len)) >= 4 and (a.startswith(b) or b.startswith(a)))):
            best = max(best, 1.0)
        else:
            best = max(best, team_score(label, name))
    return best


def cs2_candidates(cfg, now):
    """Kalshi CS2 match markets priced from cs2.py's map Elo. Source cs2-elo; paper-only (CS2 is not in liveSports)."""
    if "CS2" not in (cfg.get("sports") or []):
        return [], 0
    ratings = load(CS2_RATINGS, {})
    ups = ratings.get("upcoming") or []
    if not ups:
        return [], 0
    try:
        evs, mks = events(PROD, CS2_SERIES), markets(PROD, CS2_SERIES)
    except Exception as exc:  # noqa: BLE001
        print("kalshi", CS2_SERIES, exc)
        return [], 0
    for m in mks:
        QUOTES[m["ticker"]] = m
    games, matched = {}, 0
    for et, e in evs.items():
        d = ticker_date(et)
        first, second = split_title(e.get("title"))
        if not d or not first:
            continue
        best, best_s, runner = None, 0.0, 0.0
        for u in ups:
            if abs((datetime.strptime(u["begin"][:10], "%Y-%m-%d") - datetime.strptime(d, "%Y-%m-%d")).days) > 1:
                continue
            s1 = min(cs2_name_score(first, u["a"]), cs2_name_score(second, u["b"]))
            s2 = min(cs2_name_score(first, u["b"]), cs2_name_score(second, u["a"]))
            s = max(s1, s2)
            if s > best_s:
                runner, best, best_s = max(runner, best_s), u, s
            else:
                runner = max(runner, s)
        if best and best_s >= 0.75 and best_s - runner >= 0.25:
            games[et] = best
            matched += 1
    cands = []
    for m in mks:
        u = games.get(m.get("event_ticker"))
        if not u or u["begin"] <= iso(now + timedelta(minutes=MIN_LEAD_MIN)):
            continue
        label = m.get("yes_sub_title") or ""
        sa, sb = cs2_name_score(label, u["a"]), cs2_name_score(label, u["b"])
        if max(sa, sb) < 0.75 or abs(sa - sb) < 0.25:
            continue
        yes_fair = u["pA"] if sa > sb else 1 - u["pA"]
        for side, ask in (("yes", f(m.get("yes_ask_dollars"))), ("no", f(m.get("no_ask_dollars")))):
            if ask is None or not (cfg["priceBand"][0] <= ask <= cfg["priceBand"][1]):
                continue
            bid = f(m.get(f"{side}_bid_dollars"))
            if bid is None or ask - bid > 0.10:
                continue                      # thin tier-3 books: no real price to trade or to close against
            p_side = yes_fair if side == "yes" else 1 - yes_fair
            cost = ask + FEE_RATE * ask * (1 - ask)
            edge = p_side - cost
            if edge < cfg["minEdge"] or edge > CS2_MAX_EDGE:
                continue
            cands.append({"ticker": m["ticker"], "title": m.get("title") or label, "sport": "CS2", "kind": "game",
                          "event": f"{u['a']['name']} vs {u['b']['name']}", "commence": u["begin"], "side": side,
                          "ask": ask, "strike": None, "teamSide": None, "source": "cs2-elo", "fair": round(p_side, 4),
                          "edge": round(edge, 4), "estimated": True,
                          "why": f"CS2 map Elo: {label} {yes_fair if side == 'yes' else 1 - yes_fair:.1%} "
                                 f"(best of {u['bestOf']}, {u['mapsA']} and {u['mapsB']} rated maps); "
                                 f"Kalshi {side.upper()} {ask:.2f} + fee = {cost:.3f}."})
    return cands, matched


def track_close(book, now):
    """Kalshi CLV: the last quote seen before start becomes the trade's close. Same-side mid when the spread is
    10 cents or less (thinner books have no meaningful close). clv = close - price paid, per contract."""
    for t in book["trades"]:
        if t.get("closeMid") is not None:
            continue
        if pull.parse(t["commence"]) > now:
            m = QUOTES.get(t["ticker"])
            if not m:
                continue
            bid, ask = f(m.get(f"{t['side']}_bid_dollars")), f(m.get(f"{t['side']}_ask_dollars"))
            if bid is not None and ask is not None and 0 < ask - bid <= 0.10:
                t["lastMid"], t["lastSeen"] = round((bid + ask) / 2, 4), iso(now)
        elif t.get("lastMid") is not None:
            t["closeMid"] = t["lastMid"]
            t["clv"] = round(t["lastMid"] - t["ask"], 4)


# ---------- main ----------

def main(dry=False):
    now = now_utc()
    cfg = load(CONFIG, {})
    state = load(BOOK, {})
    for name in ("paper", "live"):
        if name not in state:
            state[name] = new_book(cfg)
        if name == "paper" and not state[name]["trades"]:   # a paper book that never traded follows the config
            state[name]["start"] = state[name]["cash"] = cfg["startingBankroll"]
    ledger = pull.load(pull.LEDGER, {"rows": []})
    picks = pull.load(pull.PICKS, {"picks": []})
    official = {p["id"] for p in ledger.get("patterns") or [] if p.get("status") == "official"}
    by_day = ledger_games(ledger.get("rows") or [], set(cfg.get("sports") or SERIES))
    open_picks = [p for p in picks["picks"] if p.get("kind") == "pick" and p.get("side")
                  and p.get("commence", "") > iso(now)]

    control = fetch_control()
    cfg_live = live_cfg(cfg, control)
    mode = "demo" if cfg.get("mode") == "demo" else "live"
    base = DEMO if mode == "demo" else PROD
    live = state["live"]
    if control and control.get("enabled") and control.get("sessionId") and live.get("sessionId") != control["sessionId"]:
        if live["trades"]:
            state.setdefault("sessions", []).append(dict(live, endedAt=iso(now), summary=book_state(live)))
        state["live"] = new_book(cfg_live)
        state["live"]["sessionId"] = control["sessionId"]
    elif not state["live"]["trades"]:
        state["live"]["start"] = state["live"]["cash"] = cfg_live["startingBankroll"]
    settled = {name: settle(state[name], DEMO if (name == "live" and mode == "demo") else PROD, now)
               for name in ("paper", "live")}
    for old in state.get("sessions") or []:          # earlier sessions' open positions still settle
        settled["live"] += settle(old, DEMO if old.get("mode") == "demo" else PROD, now)
        old["summary"] = book_state(old)

    # Scan every configured series.
    cands, matched, unmatched, fetched = [], 0, 0, 0
    for sport in cfg.get("sports") or SERIES:
        for kind, series in SERIES.get(sport, {}).items():
            try:
                evs, mks = events(PROD, series), markets(PROD, series)
            except Exception as exc:  # noqa: BLE001
                print("kalshi", series, exc)
                continue
            fetched += len(mks)
            for m in mks:
                QUOTES[m["ticker"]] = m
            games = {}
            for et, e in evs.items():
                g, labels = match_game(sport, e, by_day)
                if g:
                    g = dict(g, labels=labels)
                games[et] = g
                matched += bool(g)
                unmatched += not g
            for m in mks:
                g = games.get(m.get("event_ticker"))
                if not g or g["commence"] <= iso(now + timedelta(minutes=MIN_LEAD_MIN)):
                    continue
                parsed = parse_market(sport, kind, m, g)
                if not parsed:
                    continue
                team_side, strike = parsed
                yes_fair, est = fair_for(sport, kind, team_side, strike, g, now)
                if yes_fair is None:
                    continue
                quotes = {"yes": f(m.get("yes_ask_dollars")), "no": f(m.get("no_ask_dollars"))}
                for side, ask in quotes.items():
                    if ask is None or not (cfg["priceBand"][0] <= ask <= cfg["priceBand"][1]):
                        continue
                    p_side = yes_fair if side == "yes" else 1 - yes_fair
                    cost = ask + FEE_RATE * ask * (1 - ask)
                    contract = {"ticker": m["ticker"], "title": m.get("yes_sub_title") or m.get("title"),
                                "sport": sport, "kind": kind, "event": f"{g['away']} at {g['home']}",
                                "commence": g["commence"], "side": side, "ask": ask, "strike": strike,
                                "teamSide": team_side}
                    edge = p_side - cost
                    if edge > MAX_EDGE:
                        print(f"skip {m['ticker']} {side}: edge {edge:.3f} over {MAX_EDGE}, treated as a data error")
                        continue
                    if edge >= cfg["minEdge"]:
                        cands.append(dict(contract, source="kalshi-sharp-alt" if est else "kalshi-sharp",
                                          fair=round(p_side, 4), edge=round(edge, 4), estimated=est,
                                          why=f"Pinnacle fair {p_side:.1%} vs Kalshi {side.upper()} {ask:.2f} "
                                              f"+ fee = {cost:.3f}."))
                    # EDGE picks on this game, same side of the same market.
                    yes_side_team = team_side if side == "yes" else _other(team_side, kind)
                    if kind == "game" and side == "no" and sport in pull.SOCCER:
                        yes_side_team = None     # NO on a three-way winner also wins on a draw: not a mirror
                    for pk in open_picks:
                        if yes_side_team is None:
                            break
                        if pk["sport"] != sport or pk["event"] != f"{g['away']} at {g['home']}":
                            continue
                        mf = mirror_fair(pk, sport, kind, yes_side_team, strike, p_side)
                        if mf is None or mf - cost < cfg["minEdge"] or mf - cost > MAX_EDGE:
                            continue
                        cands.append(dict(contract, source=f"mirror:{pk['pattern']}", pattern=pk["pattern"],
                                          pickId=pk["pickId"], grade=pk["grade"], fair=round(mf, 4),
                                          edge=round(mf - cost, 4), estimated=True,
                                          why=f"EDGE {pk['pattern']} {pk['grade']} pick ({pk['reason'][:140]}). "
                                              f"Pinnacle fair here {p_side:.1%} plus the pick's edge = {mf:.1%}; "
                                              f"Kalshi {side.upper()} {ask:.2f} + fee = {cost:.3f}."))
    cs2_cands, cs2_matched = cs2_candidates(cfg, now)
    cands += cs2_cands
    matched += cs2_matched
    for name in ("paper", "live"):
        track_close(state[name], now)
    # Best first, so caps go to the biggest edges.
    cands.sort(key=lambda c: -c["edge"])

    if dry:
        for c in cands[:40]:
            print(f"{c['source']:<22} {c['sport']:<5} {c['event'][:40]:<40} {c['title'][:42]:<42} "
                  f"{c['side']:<3} ask {c['ask']:.2f} fair {c['fair']:.3f} edge {c['edge']:+.3f}")
        print(json.dumps({"kalshiMarkets": fetched, "eventsMatched": matched, "eventsUnmatched": unmatched,
                          "candidates": len(cands), "dry": True}))
        return

    placed = {"paper": 0, "live": 0}
    live_ok, live_why = live_allowed(control, state["live"])
    signer = None
    if live_ok:
        try:
            pre = "KALSHI_DEMO_" if mode == "demo" else "KALSHI_"
            signer = Signer(os.environ[pre + "KEY_ID"], os.environ[pre + "PRIVATE_KEY"])
        except Exception as exc:  # noqa: BLE001
            live_ok, live_why = False, f"no usable Kalshi key in the environment ({type(exc).__name__})"

    for name in ("paper", "live"):
        book = state[name]
        bcfg = cfg_live if name == "live" else cfg
        stop = check_stop(book, bcfg, now)
        if stop and not book.get("stopped"):
            book["stopped"] = {"why": stop, "at": iso(now)}
            if name == "paper":
                book.setdefault("wouldHaveStopped", []).append(book["stopped"])
        if name == "paper":
            book["stopped"] = None          # research never stops; the mark above shows where the limit hit
        if name == "live" and (not live_ok or book.get("stopped")):
            snapshot(book, now)
            continue
        have = {(t["event"], t["kind"], t["source"]) for t in book["trades"]}
        for c in cands:
            if (c["event"], c["kind"], c["source"]) in have:
                continue
            if name == "live" and not source_allowed(c, cfg_live, official):
                continue
            if name == "live" and c["sport"] not in (cfg.get("liveSports") or cfg.get("sports") or []):
                continue          # new sports and leagues trade on paper until their matching has been checked
            n = size(bcfg, book, c["ask"], c["fair"], now, c["source"] if name == "paper" else None)
            if n < 1:
                continue
            trade = {k: c[k] for k in ("ticker", "title", "sport", "kind", "event", "commence", "side", "ask",
                                       "strike", "source", "fair", "edge", "estimated", "why") if k in c}
            trade.update(time=iso(now), count=n, cost=round(n * c["ask"], 2), fee=fee(c["ask"], n),
                         status="open", book=name, mode=mode if name == "live" else "paper")
            if name == "live":
                filled = place(signer, base, c, n)
                if not filled:
                    continue
                trade.update(filled)
            book["trades"].append(trade)
            have.add((c["event"], c["kind"], c["source"]))
            placed[name] += 1
            if check_stop(book, bcfg, now):
                break
        snapshot(book, now)

    state["account"] = account_check(mode)
    state["asOf"] = iso(now)
    if state["live"].get("stopped") is None and check_stop(state["live"], cfg_live, now):
        state["live"]["stopped"] = {"why": check_stop(state["live"], cfg_live, now), "at": iso(now)}
    state["status"] = {"mode": mode, "switch": control_view(control), "liveActive": live_ok,
                       "liveWhy": live_why, "paper": book_state(state["paper"]), "live": book_state(state["live"]),
                       "paperStopped": state["paper"].get("stopped"), "liveStopped": state["live"].get("stopped"),
                       "config": {k: cfg_live.get(k) for k in ("startingBankroll", "stopLoss", "takeProfit", "kellyFraction",
                                                               "maxPerTradePct", "maxPerDay", "minEdge", "liveSources")},
                       "unit": round(cfg_live["startingBankroll"] / 100, 2),
                       "paperConfig": {k: cfg.get(k) for k in ("startingBankroll", "stopLoss", "takeProfit", "maxPerDay")},
                       "lastScan": {"kalshiMarkets": fetched, "eventsMatched": matched,
                                    "eventsUnmatched": unmatched, "candidates": len(cands)}}
    save(BOOK, state)
    print(json.dumps({"mode": mode, "live": live_why, "kalshiMarkets": fetched, "eventsMatched": matched,
                      "candidates": len(cands), "placed": placed, "settled": settled,
                      "paper": book_state(state["paper"]), "liveBook": book_state(state["live"])}))


def account_check(mode):
    """Read-only: confirms the Kalshi key works and reads the balance. Never places or changes anything."""
    pre = "KALSHI_DEMO_" if mode == "demo" else "KALSHI_"
    if not os.environ.get(pre + "KEY_ID") or not os.environ.get(pre + "PRIVATE_KEY"):
        return {"keys": "missing", "checkedAt": iso(now_utc())}
    try:
        signer = Signer(os.environ[pre + "KEY_ID"], os.environ[pre + "PRIVATE_KEY"])
        bal = signer.call(DEMO if mode == "demo" else PROD, "GET", "/portfolio/balance")
    except Exception as exc:  # noqa: BLE001
        return {"keys": "error", "error": f"{type(exc).__name__}: {str(exc)[:160]}", "checkedAt": iso(now_utc())}
    cents = bal.get("balance")
    dollars = f(bal.get("balance_dollars"))
    return {"keys": "ok", "balance": round(dollars if dollars is not None else (cents or 0) / 100, 2),
            "env": "demo" if mode == "demo" else "production", "checkedAt": iso(now_utc())}


def _other(team_side, kind):
    return {"home": "away", "away": "home", "over": "under", "under": "over"}.get(team_side, None) \
        if kind != "game" else {"home": "away", "away": "home"}.get(team_side)


def fetch_control():
    """Zack's switch and limits from the site. Any failure returns None, which means off."""
    try:
        req = urllib.request.Request(CONTROL_URL + "?t=" + str(int(time.time())),
                                     headers={"User-Agent": "EDGE desk", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            c = json.loads(r.read().decode())
        if not isinstance(c, dict) or "enabled" not in c:
            return None
        return c
    except Exception as exc:  # noqa: BLE001
        print("control", exc)
        return None


def live_cfg(cfg, control):
    """The live book's limits: Zack's numbers from the switch panel over the file defaults."""
    out = dict(cfg)
    if control:
        bank = float(control.get("bankroll") or cfg["startingBankroll"])
        out.update(startingBankroll=bank, stopLoss=float(control.get("stopLoss", cfg["stopLoss"])),
                   takeProfit=float(control.get("takeProfit", cfg["takeProfit"])),
                   maxPerTradePct=float(control.get("maxPerTradePct", cfg["maxPerTradePct"])),
                   maxPerDay=round(bank * float(control.get("maxPerDayPct", 20)) / 100, 2),
                   liveSources=control.get("liveSources") or cfg.get("liveSources") or [])
    return out


def control_view(control):
    if not control:
        return {"read": False}
    return {"read": True, **{k: control.get(k) for k in ("enabled", "paused", "bankroll", "stopLoss", "takeProfit",
                                                         "maxPerTradePct", "maxPerDayPct", "liveSources",
                                                         "sessionId", "updatedAt")}}


def live_allowed(control, book):
    if not control:
        return False, "the on/off switch could not be read, so it counts as off"
    if not control.get("enabled"):
        return False, "switched off"
    if control.get("paused"):
        return False, "paused"
    if book.get("stopped"):
        return False, f"stopped at the {book['stopped']['why']} limit; switch off and on to start a new session"
    return True, f"on since {control.get('sessionId')}"


def source_allowed(c, cfg, official):
    allowed = cfg.get("liveSources") or []
    if c["source"] in allowed:
        return True
    return "official" in allowed and c["source"].startswith("mirror:") and c.get("pattern") in official


def place(signer, base, c, n):
    """Buy n contracts at no worse than the ask, immediate-or-cancel. Returns fill info or None."""
    body = {"ticker": c["ticker"], "action": "buy", "side": c["side"], "count": n, "type": "limit",
            "time_in_force": "immediate_or_cancel",
            "client_order_id": f"edge-{c['ticker']}-{c['side']}-{int(time.time())}"}
    body[f"{c['side']}_price"] = int(round(c["ask"] * 100))
    try:
        o = signer.call(base, "POST", "/portfolio/orders", body).get("order") or {}
    except Exception as exc:  # noqa: BLE001
        print("order failed", c["ticker"], exc)
        return None
    filled = int(f(o.get("fill_count")) or 0)
    if filled < 1:
        print("order not filled", c["ticker"], o.get("status"))
        return None
    cost = f(o.get("taker_fill_cost_dollars")) or filled * c["ask"]
    fees = f(o.get("taker_fees_dollars"))
    return {"count": filled, "cost": round(cost, 2), "fee": round(fees if fees is not None else fee(c["ask"], filled), 2),
            "orderId": o.get("order_id"), "orderStatus": o.get("status")}


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
