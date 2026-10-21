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
import edge_stack
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


MAKER_FEE_RATE = 0.0175   # about a quarter of the taker rate; confirm against Kalshi's published schedule before live


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
        self.key_id = key_id.strip()
        # Tolerate secrets pasted with surrounding quotes, literal "\n" sequences or Windows line ends.
        pem = pem.strip().strip('"').strip("'").replace("\\n", "\n").replace("\r\n", "\n")
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
    clv = [t["clv"] for t in book["trades"] if t.get("clv") is not None and not t.get("trackOnly")]
    return {"open": round(open_cost, 2), "realized": round(realized, 2),
            "equity": round(book["start"] + realized, 2),
            "clvN": len(clv), "meanClv": round(sum(clv) / len(clv), 4) if clv else None}


def check_stop(book, cfg, now):
    """Stop loss and take profit in dollars from the start. 0 or blank means no limit (2026-10-21: a take profit of 0
    on the site stopped a fresh $35 book before its first order)."""
    st = book_state(book)
    sl, tp = cfg.get("stopLoss") or 0, cfg.get("takeProfit") or 0
    if sl > 0 and st["equity"] <= book["start"] - sl:
        return "stop-loss"
    if tp > 0 and st["equity"] >= book["start"] + tp:
        return "take-profit"
    return None


def spent_today(book, now, source=None):
    day = now.astimezone(CT).strftime("%Y-%m-%d")
    spent = sum(t["cost"] + t["fee"] for t in book["trades"]
                if t.get("status") != "void" and pull.parse(t["time"]).astimezone(CT).strftime("%Y-%m-%d") == day
                and (source is None or t["source"] == source))
    # Resting live maker orders hold their unfilled remainder against the day's cap.
    return spent + sum((o["count"] - o.get("filledSeen", 0)) * o["price"] for o in book.get("orders") or []
                       if o.get("status") == "resting" and (source is None or o["source"] == source))


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
SPORT_OF = {}
CS2_FAIR = {}
_nhl = pull.load(ROOT / "stats" / "nhl_games.json", {}).get("games") or {}
NHL_GAMES = list(_nhl.values()) if isinstance(_nhl, dict) else _nhl
CS2_SERIES = "KXCS2GAME"
CS2_RATINGS = ROOT / "stats" / "cs2_ratings.json"
CS2_MAX_EDGE = 0.15        # a model, not a sharp price: bigger gaps are more likely a rating error
# The walk-forward backtest (stats/backtest_cs2.md, 12,705 series) shows the Elo is overconfident: 74.6% favourites
# won 69.8%, 84.1% won 76.7%. Shrinking toward 50% by 0.8 matches that table (64.7 -> 61.8 vs 62.3 won,
# 74.6 -> 69.7 vs 69.8, 84.1 -> 77.3 vs 76.7). Added 2026-10-19 after 40 paper trades lost $43 at -4.1% mean CLV.
CS2_SHRINK = 0.8


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
    if not ups or ratings.get("backfillPending"):
        return [], 0          # ratings from a part-loaded history are not ready to price anything
    try:
        evs, mks = events(PROD, CS2_SERIES), markets(PROD, CS2_SERIES)
    except Exception as exc:  # noqa: BLE001
        print("kalshi", CS2_SERIES, exc)
        return [], 0
    for m in mks:
        QUOTES[m["ticker"]] = m
        SPORT_OF[m.get("event_ticker")] = "CS2"
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
        p_a = 0.5 + CS2_SHRINK * (u["pA"] - 0.5)
        yes_fair = p_a if sa > sb else 1 - p_a
        CS2_FAIR[m["ticker"]] = {"model": round(yes_fair, 4), "bestOf": u.get("bestOf"), "tier": u.get("tier"),
                                 "maps": min(u.get("mapsA") or 0, u.get("mapsB") or 0)}
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


MARKS = ROOT / "stats" / "kalshi_marks.json"


def record_marks(now, sports_of):
    """Kalshi price history for every sport: each liquid market's first-seen and last pre-start YES mid
    (spread 15 cents or less). Markets 3+ days past their close move to ledger/archive/<month>/kalshi.jsonl."""
    marks = load(MARKS, {})
    t = iso(now)
    for tk, m in QUOTES.items():
        bid, ask = f(m.get("yes_bid_dollars")), f(m.get("yes_ask_dollars"))
        close_t = m.get("occurrence_datetime") or m.get("expected_expiration_time") or m.get("close_time")
        if bid is None or ask is None or not (0 < ask - bid <= 0.15) or not close_t or close_t <= t:
            continue
        mid = round((bid + ask) / 2, 4)
        rec = marks.setdefault(tk, {"event": m.get("event_ticker"), "title": m.get("title"), "start": close_t,
                                    "sport": sports_of.get(m.get("event_ticker")), "open": mid, "openT": t})
        rec.update(last=mid, lastT=t)
        if tk in CS2_FAIR and "model" not in rec:
            rec.update(CS2_FAIR[tk])            # the model's view at first sight, for CS2's own learned model
    keep, old = {}, {}
    for tk, rec in marks.items():
        if (rec.get("start") or t) < iso(now - timedelta(days=3)):
            old.setdefault((rec.get("start") or t)[:7], []).append(dict(rec, ticker=tk))
        else:
            keep[tk] = rec
    for month, recs in old.items():
        path = ROOT / "ledger" / "archive" / month / "kalshi.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            for r in recs:
                fh.write(json.dumps(r, separators=(",", ":")) + "\n")
    MARKS.write_text(json.dumps(keep, separators=(",", ":")))
    return len(keep)


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


# ---------- maker paper book (north-star plan, 2026-10-21) ----------
# Research only, one contract per signal, no bankroll and never a real order. For every candidate the taker paper
# book sees, a resting limit order is posted one cent above the best bid (never at or through the ask), capped so the
# edge after the maker fee still clears minEdge. A later scan counts it filled when the same side's ask has come
# down to the order's price: someone sold there, so a resting bid would have traded. Unfilled at the start = expired.
# Fills that arrive mostly when the market moves against us (adverse selection) show up as a worse CLV, which is
# the point of measuring it before any live maker order. clv = last pre-start mid - price paid (as the taker book);
# clvNet also subtracts the per-contract fee, unrounded, so maker and taker compare like for like.

def maker_fee_raw(price):
    return MAKER_FEE_RATE * price * (1 - price)


def maker_post(mk, cands, cfg, now):
    seen = {(o["event"], o["kind"], o["source"]) for o in mk["orders"]}
    posted = 0
    for c in cands:
        key = (c["event"], c["kind"], c["source"])
        if key in seen or c.get("source", "").startswith("cs2"):
            continue
        m = QUOTES.get(c["ticker"]) or {}
        bid, ask = f(m.get(f"{c['side']}_bid_dollars")), c["ask"]
        if bid is None or bid <= 0:
            continue
        price = round(bid + 0.01, 2) if bid + 0.01 < ask - 1e-9 else round(bid, 2)
        cap = math.floor((c["fair"] - cfg["minEdge"]) * 100 + 1e-9) / 100
        price = min(price, cap)
        while price > 0 and c["fair"] - price - maker_fee_raw(price) < cfg["minEdge"]:
            price = round(price - 0.01, 2)
        if price < 0.01 or price >= ask:
            continue
        mk["orders"].append({k: c[k] for k in ("ticker", "title", "sport", "kind", "event", "commence", "side",
                                                "source", "fair", "estimated") if k in c}
                            | {"price": price, "bidAtPost": bid, "askAtPost": ask, "takerEdge": c["edge"],
                               "makerEdge": round(c["fair"] - price - maker_fee_raw(price), 4),
                               "postedAt": iso(now), "status": "resting"})
        seen.add(key)
        posted += 1
    return posted


def maker_fill(mk, now):
    filled = expired = 0
    for o in mk["orders"]:
        if o["status"] != "resting":
            continue
        if pull.parse(o["commence"]) <= now:
            o.update(status="expired", expiredAt=iso(now))
            expired += 1
            continue
        m = QUOTES.get(o["ticker"]) or {}
        ask = f(m.get(f"{o['side']}_ask_dollars"))
        if ask is not None and ask <= o["price"] + 1e-9:
            o.update(status="filled", filledAt=iso(now), askAtFill=ask)
            mk["trades"].append({k: o[k] for k in ("ticker", "title", "sport", "kind", "event", "commence", "side",
                                                   "source", "fair", "estimated") if k in o}
                                | {"ask": o["price"], "count": 1, "cost": o["price"],
                                   "fee": round(maker_fee_raw(o["price"]), 4), "time": iso(now), "status": "open",
                                   "book": "maker", "mode": "paper", "postedAt": o["postedAt"]})
            filled += 1
    return filled, expired


def maker_summary(mk, paper):
    orders = mk["orders"]
    done = [o for o in orders if o["status"] in ("filled", "expired")]
    tr = [t for t in mk["trades"] if t.get("clv") is not None]
    taker = {(t["event"], t["kind"], t["source"]): t for t in paper["trades"] if t.get("clv") is not None}
    pairs = [(t, taker[(t["event"], t["kind"], t["source"])]) for t in tr if (t["event"], t["kind"], t["source"]) in taker]

    def mean(v):
        return round(sum(v) / len(v), 4) if v else None
    return {"orders": len(orders), "resting": sum(1 for o in orders if o["status"] == "resting"),
            "filled": sum(1 for o in orders if o["status"] == "filled"),
            "expired": sum(1 for o in orders if o["status"] == "expired"),
            "fillRate": round(sum(1 for o in done if o["status"] == "filled") / len(done), 3) if done else None,
            "clvN": len(tr), "meanClv": mean([t["clv"] for t in tr]),
            "meanClvNet": mean([t["clv"] - t["fee"] for t in tr]),
            "settledPnl": round(sum(t.get("pnl", 0) for t in mk["trades"] if t["status"] == "settled"), 2),
            "pairedWithTaker": len(pairs),
            "pairedMakerClvNet": mean([m["clv"] - m["fee"] for m, _ in pairs]),
            "pairedTakerClvNet": mean([tk["clv"] - FEE_RATE * tk["ask"] * (1 - tk["ask"]) for _, tk in pairs]),
            "note": ("Research only: one simulated contract per signal, never a real order. Net = CLV minus the "
                     "per-contract fee, unrounded.")}


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
    maker = state.setdefault("maker", {"start": 0.0, "cash": 0.0, "orders": [], "trades": [], "equity": [],
                                       "stopped": None})
    if not dry:
        settled["maker"] = settle(maker, PROD, now)
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
                SPORT_OF[m.get("event_ticker")] = sport
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
                    # Same price, aimed at where Pinnacle is expected to close (edge_stack's measured drifts).
                    if not est:
                        drow = g["rows"].get({"game": "h2h"}.get(kind, kind))
                        dp = edge_stack.drift_prob(drow, now, NHL_GAMES) if drow else None
                        dside = team_side if kind == "game" else "over"
                        if dp and dside in dp:
                            shift = dp[dside] if side == "yes" else -dp[dside]
                            dedge = p_side + shift - cost
                            if cfg["minEdge"] <= dedge <= MAX_EDGE:
                                cands.append(dict(contract, source="kalshi-drift", fair=round(p_side + shift, 4),
                                                  edge=round(dedge, 4), estimated=True,
                                                  why=f"Pinnacle fair {p_side:.1%} plus the measured drift still to come "
                                                      f"{shift:+.2%}; Kalshi {side.upper()} {ask:.2f} + fee = {cost:.3f}."))
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
    if not dry:
        mfill, mexp = maker_fill(maker, now)
        track_close(maker, now)
    if not dry:
        try:
            record_marks(now, SPORT_OF)
        except Exception as exc:  # noqa: BLE001
            print("kalshi marks", exc)
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
    skips = {"paper": {}, "live": {}}

    def skip(book_name, why):
        skips[book_name][why] = skips[book_name].get(why, 0) + 1
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
            skip("live", f"book not trading: {live_why if not live_ok else book['stopped']}")
            snapshot(book, now)
            continue
        if name == "live" and live_ok and signer:
            try:
                reconcile(book, signer, base, now)
            except Exception as exc:  # noqa: BLE001
                print("reconcile", exc)
        have = {(t["event"], t["kind"], t["source"]) for t in book["trades"] if t.get("status") != "void"}
        have |= {(o["event"], o["kind"], o["source"]) for o in book.get("orders") or [] if o.get("status") == "resting"}
        for c in cands:
            if (c["event"], c["kind"], c["source"]) in have:
                skip(name, "already held")
                continue
            if name == "live" and c["sport"] not in (cfg.get("liveSports") or cfg.get("sports") or []):
                skip(name, "sport paper-only")
                continue          # new sports and leagues trade on paper until their matching has been checked
            # Scanner strategies (scan.py) are track-only until grade.py promotes them: price, close and CLV, no stake.
            track_only = c["source"] in (cfg.get("trackOnlySources") or []) or c["source"].startswith(("mirror:scan-", "mirror:learned-scan-"))
            track = name == "paper" and track_only
            is_test = False
            if name == "live":
                if track_only:
                    skip(name, "track-only")
                    continue
                if not source_allowed(c, cfg_live, official, state.get("sourceStatus")):
                    tcfg = cfg.get("liveTest") or {}
                    if not test_allowed(c, cfg_live, tcfg, track_only):
                        skip(name, "not confirmed, not test-eligible")
                        continue
                    n_test = int(tcfg.get("contracts", 1))
                    if test_spent_today(book, now) + n_test * c["ask"] > float(tcfg.get("maxPerDay", 5.0)) + 1e-9:
                        skip(name, "test cap reached")
                        continue
                    is_test = True
            n = int((cfg.get("liveTest") or {}).get("contracts", 1)) if is_test else \
                (0 if track else size(bcfg, book, c["ask"], c["fair"], now, c["source"] if name == "paper" else None))
            if n < 1 and not track:
                skip(name, "size 0")
                continue
            trade = {k: c[k] for k in ("ticker", "title", "sport", "kind", "event", "commence", "side", "ask",
                                       "strike", "source", "fair", "edge", "estimated", "why") if k in c}
            # Track-only sources (trading/config.json) log the price, close and CLV with no money on them,
            # so a source still being tested cannot drain the paper book the other sources are sized from.
            trade.update(time=iso(now), count=n, cost=round(n * c["ask"], 2), fee=fee(c["ask"], n) if n else 0.0,
                         status="open", book=name, mode=mode if name == "live" else "paper")
            if track:
                trade["trackOnly"] = True
            if is_test:
                trade["test"] = True
            order_type = (cfg.get("liveTest") or {}).get("orderType", "maker") if is_test else cfg.get("liveOrderType")
            if name == "live" and order_type == "maker":
                m = QUOTES.get(c["ticker"]) or {}
                bid = f(m.get(f"{c['side']}_bid_dollars"))
                mprice = None if bid is None else (round(bid + 0.01, 2) if bid + 0.01 < c["ask"] - 1e-9 else round(bid, 2))
                if mprice is None or mprice < 0.01 or c["fair"] - mprice - maker_fee_raw(mprice) < cfg["minEdge"]:
                    skip(name, "no maker price with edge")
                    continue
                order = place_maker(signer, base, c, n, mprice)
                if not order:
                    skip(name, "maker order failed")
                    continue
                order["time"] = iso(now)
                if is_test:
                    order["test"] = True
                book.setdefault("orders", []).append(order)
                have.add((c["event"], c["kind"], c["source"]))
                placed[name] += 1
                continue
            if name == "live":
                filled = place(signer, base, c, n)
                if not filled:
                    skip(name, "taker order failed or unfilled")
                    continue
                trade.update(filled)
            book["trades"].append(trade)
            have.add((c["event"], c["kind"], c["source"]))
            placed[name] += 1
            if check_stop(book, bcfg, now):
                break
        snapshot(book, now)

    maker_posted = maker_post(maker, cands, cfg, now)
    state["sourceStatus"] = source_status(state["paper"], state.get("sourceStatus"), now)
    state["account"] = account_check(mode)
    state["asOf"] = iso(now)
    if state["live"].get("stopped") is None and check_stop(state["live"], cfg_live, now):
        state["live"]["stopped"] = {"why": check_stop(state["live"], cfg_live, now), "at": iso(now)}
    state["status"] = {"mode": mode, "switch": control_view(control), "liveActive": live_ok,
                       "liveWhy": live_why, "paper": book_state(state["paper"]), "live": book_state(state["live"]),
                       "paperStopped": state["paper"].get("stopped"), "liveStopped": state["live"].get("stopped"),
                       "maker": maker_summary(maker, state["paper"]),
                       "liveSkips": skips["live"], "liveCandidates": len(cands),
                       "sourceStatus": state.get("sourceStatus"),
                       "liveRule": "Full-size live money only for confirmed signals: mirrors of official EDGE patterns, or "
                                   "Kalshi sources whose paper CLV net of fees cleared the bar and a 15-trade confirmation. "
                                   "Every other signal may trade as a small live test (liveTest in trading/config.json).",
                       "liveTest": {**(cfg.get("liveTest") or {}), "spentToday": round(test_spent_today(state["live"], now), 2),
                                    "trades": sum(1 for t in state["live"]["trades"] if t.get("test")),
                                    "resting": sum(1 for o in state["live"].get("orders") or []
                                                   if o.get("test") and o.get("status") == "resting")},
                       "config": {k: cfg_live.get(k) for k in ("startingBankroll", "stopLoss", "takeProfit", "kellyFraction",
                                                               "maxPerTradePct", "maxPerDay", "minEdge", "liveSources")},
                       "unit": round(cfg_live["startingBankroll"] / 100, 2),
                       "paperConfig": {k: cfg.get(k) for k in ("startingBankroll", "stopLoss", "takeProfit", "maxPerDay")},
                       "lastScan": {"kalshiMarkets": fetched, "eventsMatched": matched,
                                    "eventsUnmatched": unmatched, "candidates": len(cands)}}
    save(BOOK, state)
    print(json.dumps({"mode": mode, "live": live_why, "kalshiMarkets": fetched, "eventsMatched": matched,
                      "candidates": len(cands), "placed": placed, "settled": settled,
                      "maker": {"posted": maker_posted, "filled": mfill, "expired": mexp}, "liveSkips": skips["live"],
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


SOURCE_STAGES = [(15, 2.5), (20, 2.0)]   # grade.py's promotion stages, applied to Kalshi CLV net of fees
SOURCE_CONFIRM_N = 15


def source_status(paper, prev, now):
    """North-star rules 4 and 7 for Kalshi's own sources (kalshi-sharp, kalshi-sharp-alt, kalshi-drift, cs2-elo):
    a source is official only after its paper CLV, net of the taker fee per contract, clears grade.py's bar and
    then a confirmation run of SOURCE_CONFIRM_N fresh trades. Mirror sources follow their EDGE pattern instead."""
    by = {}
    for t in paper["trades"]:
        if t.get("clv") is None or t["source"].startswith("mirror:"):
            continue
        per_fee = (t["fee"] / t["count"]) if t.get("count") else FEE_RATE * t["ask"] * (1 - t["ask"])
        by.setdefault(t["source"], []).append((t["time"], t["clv"] - per_fee))
    out = {}
    for src, vals in by.items():
        v = [x for _, x in vals]
        n, mean = len(v), sum(v) / len(v)
        sd = (sum((x - mean) ** 2 for x in v) / (n - 1)) ** 0.5 if n > 1 else 0
        t = mean / (sd / n ** 0.5) if sd else 0.0
        need = None
        for k, tt in SOURCE_STAGES:
            if n >= k:
                need = tt
        rec = dict((prev or {}).get(src) or {})
        clears = need is not None and mean > 0 and t >= need
        if clears and not rec.get("clearedAt"):
            rec = {"clearedAt": iso(now)}
        if not clears and rec.get("result") != "passed":
            rec = {}
        fresh = [x for when, x in vals if rec.get("clearedAt") and when > rec["clearedAt"]]
        if rec.get("clearedAt") and not rec.get("result") and len(fresh) >= SOURCE_CONFIRM_N:
            rec["result"] = "passed" if sum(fresh) / len(fresh) > 0 else None
            if not rec["result"]:
                rec = {}
        if not clears:
            rec = {}
        status = "official" if rec.get("result") == "passed" else "confirming" if rec.get("clearedAt") else "shadow"
        out[src] = {"status": status, "n": n, "meanClvNet": round(mean, 4), "t": round(t, 2), "tNeeded": need,
                    "freshN": len(fresh), **({"clearedAt": rec["clearedAt"]} if rec.get("clearedAt") else {}),
                    **({"result": rec["result"]} if rec.get("result") else {})}
    return out


def test_spent_today(book, now):
    """Dollars committed today by live test trades and resting live test orders (Central time)."""
    day = now.astimezone(CT).strftime("%Y-%m-%d")
    spent = sum(t["cost"] + t["fee"] for t in book["trades"]
                if t.get("test") and t.get("status") != "void"
                and pull.parse(t["time"]).astimezone(CT).strftime("%Y-%m-%d") == day)
    return spent + sum((o["count"] - o.get("filledSeen", 0)) * o["price"] for o in book.get("orders") or []
                       if o.get("test") and o.get("status") == "resting"
                       and pull.parse(o["time"]).astimezone(CT).strftime("%Y-%m-%d") == day)


def test_allowed(c, cfg, tcfg, track_only):
    """Small real-money tests (Zack, 2026-10-21: "use my real money ... just use small units to test the idea"):
    any signal that is not track-only and not a mirror of a parked pattern, at tcfg["contracts"] contracts, capped at
    tcfg["maxPerDay"] dollars a day. The switch panel's live-source list narrows it like full-size trades."""
    if not tcfg.get("enabled") or track_only:
        return False
    if c["source"].startswith("mirror:") and c.get("pattern") in pull.PARKED:
        return False
    allowed = cfg.get("liveSources") or []
    return not allowed or "official" in allowed or c["source"] in allowed


def source_allowed(c, cfg, official, sources=None):
    """Live money only for confirmed signals: a mirror of an official EDGE pattern, or a Kalshi source whose own
    status is official. The switch panel's live-source list can narrow this further, never widen it."""
    eligible = (c["source"].startswith("mirror:") and c.get("pattern") in official) \
        or (sources or {}).get(c["source"], {}).get("status") == "official"
    if not eligible:
        return False
    allowed = cfg.get("liveSources") or []
    if not allowed or "official" in allowed:
        return True
    return c["source"] in allowed


def fp(x):
    """Kalshi fixed-point strings ("12.00", "0.5600") or numbers to float; None when absent."""
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def order_numbers(o, price):
    """Fills, cost and fee from a Kalshi order object, old or new field names (2026-10-21: Kalshi reports
    fill_count_fp; the old code read fill_count, so a filled order looked unfilled and could be bought again)."""
    filled = fp(o.get("fill_count_fp"))
    if filled is None:
        filled = fp(o.get("fill_count"))
    filled = int(round(filled or 0))
    cost = sum(v for v in (fp(o.get("taker_fill_cost_dollars")), fp(o.get("maker_fill_cost_dollars"))) if v) or filled * price
    fees = [v for v in (fp(o.get("taker_fees_dollars")), fp(o.get("maker_fees_dollars"))) if v is not None]
    return filled, round(cost, 2), round(sum(fees), 2) if fees else None


def get_order(signer, base, order_id):
    return (signer.call(base, "GET", f"/portfolio/orders/{order_id}") or {}).get("order") or {}


def create_order(signer, base, c, n, price, tif, post_only=False, expiration=None):
    """One limit order, current endpoint first (POST /portfolio/events/orders, bid = buy YES, ask = sell YES =
    buy NO at 1 - price), the legacy endpoint if that path is refused. Returns (order_id, path) or (None, why)."""
    cid = f"edge-{c['ticker']}-{c['side']}-{int(time.time() * 1000)}"
    yes_price = price if c["side"] == "yes" else round(1 - price, 4)
    body = {"ticker": c["ticker"], "side": "bid" if c["side"] == "yes" else "ask", "count": f"{n:.2f}",
            "price": f"{yes_price:.4f}", "time_in_force": tif, "self_trade_prevention_type": "taker_at_cross",
            "client_order_id": cid}
    if post_only:
        body["post_only"] = True
    if expiration:
        body["expiration_time"] = int(expiration)
    try:
        r = signer.call(base, "POST", "/portfolio/events/orders", body) or {}
        if r.get("order_id"):
            return r["order_id"], "v2"
    except urllib.error.HTTPError as exc:
        if exc.code not in (404, 405):
            return None, f"v2 refused: HTTP {exc.code} {exc.read()[:200]!r}"
    except Exception as exc:  # noqa: BLE001
        return None, f"v2 failed: {exc}"
    legacy = {"ticker": c["ticker"], "action": "buy", "side": c["side"], "count": n, "type": "limit",
              "time_in_force": tif, "client_order_id": cid + "-l", f"{c['side']}_price": int(round(price * 100))}
    if post_only:
        legacy["post_only"] = True
    if expiration:
        legacy["expiration_ts"] = int(expiration)
    try:
        o = (signer.call(base, "POST", "/portfolio/orders", legacy) or {}).get("order") or {}
        return (o.get("order_id"), "legacy") if o.get("order_id") else (None, "legacy: no order id")
    except Exception as exc:  # noqa: BLE001
        return None, f"legacy failed: {exc}"


def place(signer, base, c, n):
    """Buy n contracts at no worse than the ask, immediate-or-cancel. Fills are read back from the order itself.
    If the read-back fails the trade is kept as unconfirmed at the full count, so the same bet is never bought
    twice, and reconcile() corrects it on the next run."""
    oid, how = create_order(signer, base, c, n, c["ask"], "immediate_or_cancel")
    if not oid:
        print("order failed", c["ticker"], how)
        return None
    try:
        o = get_order(signer, base, oid)
    except Exception as exc:  # noqa: BLE001
        print("order read-back failed", c["ticker"], exc)
        return {"count": n, "cost": round(n * c["ask"], 2), "fee": fee(c["ask"], n), "orderId": oid,
                "orderPath": how, "unconfirmed": True}
    filled, cost, fees = order_numbers(o, c["ask"])
    if filled < 1:
        print("order not filled", c["ticker"], o.get("status"))
        return None
    return {"count": filled, "cost": cost, "fee": fees if fees is not None else fee(c["ask"], filled), "orderId": oid,
            "orderPath": how, "orderStatus": o.get("status")}


def place_maker(signer, base, c, n, price):
    """A resting post-only order at `price`, expiring 5 minutes before the start. Returns the order record or None.
    Used only when trading/config.json liveOrderType is "maker" (north-star rule 3, off until the paper maker book
    beats the taker book net of fees)."""
    exp = pull.parse(c["commence"]).timestamp() - 300
    oid, how = create_order(signer, base, c, n, price, "good_till_canceled", post_only=True, expiration=exp)
    if not oid:
        print("maker order failed", c["ticker"], how)
        return None
    keep = ("ticker", "title", "sport", "kind", "event", "commence", "side", "strike", "source", "fair", "edge",
            "estimated", "why")
    return {**{k: c[k] for k in keep if k in c}, "orderId": oid, "orderPath": how, "price": price, "count": n,
            "filledSeen": 0, "status": "resting"}


def reconcile(book, signer, base, now):
    """Live book upkeep: unconfirmed taker fills get their real numbers, and resting maker orders turn their fills
    into trades. Runs before new orders are placed."""
    changed = 0
    for t in book["trades"]:
        if not t.get("unconfirmed") or not t.get("orderId"):
            continue
        try:
            o = get_order(signer, base, t["orderId"])
        except Exception as exc:  # noqa: BLE001
            print("reconcile", t["ticker"], exc)
            continue
        filled, cost, fees = order_numbers(o, t["ask"])
        t.update(count=filled, cost=cost, fee=fees if fees is not None else fee(t["ask"], max(filled, 1)) if filled else 0.0,
                 unconfirmed=False, orderStatus=o.get("status"))
        if filled < 1:
            t.update(status="void", note="order read back with no fill")
        changed += 1
    for o in book.get("orders") or []:
        if o["status"] != "resting":
            continue
        try:
            got = get_order(signer, base, o["orderId"])
        except Exception as exc:  # noqa: BLE001
            print("maker reconcile", o["ticker"], exc)
            continue
        filled, cost, fees = order_numbers(got, o["price"])
        if filled > o["filledSeen"]:
            add = filled - o["filledSeen"]
            share = add / filled if filled else 1
            book["trades"].append({k: o[k] for k in ("ticker", "title", "sport", "kind", "event", "commence", "side",
                                                     "strike", "source", "fair", "edge", "estimated", "why") if k in o}
                                  | {"ask": o["price"], "count": add, "cost": round(cost * share, 2),
                                     "fee": round((fees or 0) * share, 2), "time": iso(now), "status": "open",
                                     "book": "live", "mode": "maker", "orderId": o["orderId"],
                                     **({"test": True} if o.get("test") else {})})
            o["filledSeen"] = filled
            changed += 1
        st = got.get("status")
        if st in ("canceled", "executed") or pull.parse(o["commence"]) <= now:
            o["status"] = st or "expired"
    return changed


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
