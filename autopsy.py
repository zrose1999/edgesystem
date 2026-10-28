#!/usr/bin/env python3
"""EDGE autopsy: why each settled read came out the way it did. Post-pick only; never a feature, never a rule.

  python3 autopsy.py              fetch box scores for settled reads not yet cached (ESPN, free), then print counts
  python3 autopsy.py --dry        print counts from the cache only, fetch nothing
  python3 autopsy.py show ID      the full autopsy of one pickId

Two questions, answered separately because only one of them carries signal at today's sample size:

  1. Market autopsy (the signal): why did the line move for or against us between the pick and the close?
     Sources: ledger/snaps (print and Pinnacle prices, from 2026-10-19), pinAtPick, the open snapshot, and the
     timestamped injury / goalie / QB timelines in stats/ (NBA injuries, NFL injuries, NHL goalies, college QBs,
     tracked from 2026-10-14). Costs no Odds API credits.
       cause, for reads that lost to the close, first match wins:
         news-after-pick         a meaningful injury, goalie or QB change landed between the pick and the start
         sharps-against-at-pick  Pinnacle already rated our side lower than the print book when we took it
         sharps-against-at-open  same, at the open (when no pick-time Pinnacle price exists)
         bet-into-steam          Pinnacle was moving away from our side in the 30 min - 6 h before the pick
         late-move               the move came in the final hour with no news found
         sharp-move-against      (2026-10-28) Pinnacle itself moved against us after the pick, no news found:
                                 sharp money disagreed with the read
         soft-move-against       (2026-10-28) the print moved against us while Pinnacle held: a soft-book move
         model-wrong             (2026-10-28) the market moved against us and nothing above explains it: the read's
                                 number was off (was "number-off")
         unknown                 too little stored data to say (reads before the snapshots and timelines)
       Before any of these: every read's CLV is split exactly (2026-10-28, Zack: "find out exactly what happened")
         CLV = price paid (fair no-vig at the pick, Pinnacle where stored, else the print, minus the price taken)
             + market move (fair at the pick to the close)
       and a loss whose market move is under MOVE_EPS is
         overpaid                we paid more than the fair price and the line never moved against us: the loss is
                                 the price, not the read (pre-pick feature pinEdge; blocked now by the Pinnacle gate)
       Every loss also gets a one-line lesson and nowBlocked: whether today's rules (Pinnacle gate, parked
       patterns) would have stopped it. memory.py turns these into memory/losses.md, the weekly loss review.
       Reads that beat the close get market-agreed (or news-for-us when news broke our way).
       Each cause names the pre-pick feature that could have warned us, where one exists. That pre-pick feature,
       not the cause, is what gets tested on CLV (memory/research.json).

  2. Game autopsy (mostly noise, labelled so it stops being mistaken for signal): did the result follow the
     process, and what in the box score decided it?
       verdict: right-and-rewarded (beat close, won), right-but-unlucky (beat close, lost),
                lucky-win (lost to close, won), market-was-right (lost to close, lost), push.
       variance tags, each marked helped or hurt our side: close-margin, overtime, flipped-late,
       turnover-swing and defensive-td (NFL/NCAAF), three-point-outlier and free-throw-gap (NBA),
       goalie-outlier and empty-net (NHL).

The box-score cache (stats/autopsy_box.json) is job output, written only by the data job through grade.py.
Sessions never commit it.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATS = ROOT / "stats"
BOX = STATS / "autopsy_box.json"
MAX_FETCH = 60            # box-score summaries per run; the rest wait for the next run
ESPN = "https://site.api.espn.com/apis/site/v2/sports/{path}"
LEAGUES = {"NFL": "football/nfl", "NCAAF": "football/college-football", "NBA": "basketball/nba",
           "NHL": "hockey/nhl"}
REG_PERIODS = {"NFL": 4, "NCAAF": 4, "NBA": 4, "NHL": 3}
# A result inside these margins of the number is close: a single play, foul shot or empty net decides it.
CLOSE = {("NFL", "spread"): 3, ("NFL", "total"): 4, ("NCAAF", "spread"): 3, ("NCAAF", "total"): 4,
         ("NBA", "spread"): 3, ("NBA", "total"): 5, ("NHL", "total"): 1, ("NHL", "h2h"): 1}
NEWS_POINTS = 1.0         # NBA/NFL news must be worth at least this many points to count
CFB_QB_POINTS = 4.0       # a college QB1 change, at full absence weight
STEAM_AWAY = -0.005       # Pinnacle no-vig move before the pick, as memory.py's steamBeforePick
SHARP_AGAINST = -0.01     # as memory.py's sharpDiv / sharpDivPick
PRICE_MOVE = 0.015        # a same-line no-vig move this large counts as a move
MOVE_EPS = 0.005          # a market move smaller than this (no-vig, toward the close) is no move: the price decided it
PIN_HELD = 0.005          # Pinnacle moving less than this after the pick counts as holding

# Where a pre-pick feature exists that could have flagged the cause before the bet.
PRE_PICK_FEATURE = {
    "news-after-pick": "timing=early",               # stamped long before the reports settle
    "sharps-against-at-pick": "sharpDivPick=pin-against",
    "sharps-against-at-open": "sharpDiv=pin-against",
    "bet-into-steam": "steamBeforePick=away",
    "late-move": None, "number-off": None, "unknown": None,
    "overpaid": "pinEdge",                             # price taken vs Pinnacle no-vig at the pick (memory.py)
    "sharp-move-against": "steamBeforePick=away",      # the nearest pre-pick sharp signal we store
    "soft-move-against": "sharpDivPick=pin-for",       # Pinnacle already on our side: the print came back to it
    "model-wrong": "edgeBar",                          # the size of the read's own disagreement with the market
}
# What already learns from each cause without anyone acting (2026-10-28).
FEEDBACK = {
    "overpaid": "Pinnacle gate: a read whose price is not better than Pinnacle's fair price no longer counts.",
    "model-wrong": "Model shrink: the move check lowers this pattern's weight when its predicted moves fail.",
    "sharp-move-against": "Move check: counts against the pattern's capture; tested pre-pick as steamBeforePick.",
    "news-after-pick": "Tested pre-pick as timing (early reads before reports settle).",
}


def price_split(pick):
    """CLV = price paid + market move, exactly. price paid = fair no-vig for our side at the pick (Pinnacle moved to
    our line where stored, as the gate computes it; else the print's own no-vig, which is our line) minus the implied
    probability of the price taken. market move = CLV - price paid. None when no fair price at the pick is stored."""
    clv, side, price = pick.get("clvProb"), pick.get("side"), pick.get("priceAtPick")
    if not isinstance(clv, (int, float)) or not side or price is None:
        return None
    try:
        import pull
        paid = pull.implied(price)
    except Exception:  # noqa: BLE001
        return None
    fair_p, src = None, None
    pin = pick.get("pinAtPick") or {}
    if pin.get("prices"):
        snap = {"time": pin.get("snapTime") or pick.get("priceTime"),
                "books": {"pinnacle": {**pin["prices"], "line": pin.get("line"), "updated": pin.get("updated")}}}
        pe = pull.pin_edge_at_pick(snap, side, pick.get("market"), pick.get("sport"), pick.get("lineAtPick"), price)
        if pe:
            fair_p, src = pe["edge"] + paid, "pinnacle"
    if fair_p is None:
        nv = no_vig(pick.get("marketPrices"), side)
        if nv is not None:
            fair_p, src = nv, "print"
    if fair_p is None:
        return None
    return {"pricePaid": round(fair_p - paid, 4), "marketMove": round(clv - (fair_p - paid), 4), "fairSource": src}


def lesson(cause, split, m, pick):
    """One plain sentence: what happened to this read, in numbers."""
    pp = split["pricePaid"] if split else None
    mv = split["marketMove"] if split else None
    pr = f"{pp * 100:+.1f}%" if pp is not None else "n/a"
    mm = f"{mv * 100:+.1f}%" if mv is not None else "n/a"
    src = "Pinnacle's" if split and split["fairSource"] == "pinnacle" else "the print's no-vig"
    if cause == "overpaid":
        return (f"Paid {abs(pp) * 100:.1f}% over {src} fair price at the pick; the market moved {mm}. The loss was the "
                "price, not the read.")
    if cause == "news-after-pick":
        items = "; ".join(str(x) for x in (m.get("news") or [])[:2])
        return f"News landed after the pick ({items or 'see news'}); market moved {mm}, price paid {pr}."
    if cause == "sharp-move-against":
        return (f"Pinnacle moved {m.get('pinMoveAfterPick', 0) * 100:+.1f}% against us after the pick with no news: sharp "
                f"money disagreed. Market move {mm}, price paid {pr}.")
    if cause == "soft-move-against":
        return f"The print moved against us ({mm}) while Pinnacle held; price paid {pr}."
    if cause in ("sharps-against-at-pick", "sharps-against-at-open"):
        return f"Pinnacle already rated our side below the print when we bet; price paid {pr}, market move {mm}."
    if cause == "bet-into-steam":
        return f"Bet into a Pinnacle move already running against us; price paid {pr}, market move {mm}."
    if cause == "late-move":
        return f"Market moved {mm} against us in the final hour, no news found; price paid {pr}."
    if cause == "model-wrong":
        return (f"Market moved {mm} against the read's side with no news, sharp or steam signal: the read's number "
                f"was off. Price paid {pr}.")
    return "Too little stored data to say what happened."


def load_json(path, default):
    try:
        return json.loads(path.read_text()) if path.exists() else default
    except ValueError:
        return default


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


_STATS = {}


def stats_file(name):
    """A stats/ file, read once per run."""
    if name not in _STATS:
        _STATS[name] = load_json(STATS / name, {})
    return _STATS[name]


def key(name):
    import memory
    return memory.team_key(name)


# ---------------------------------------------------------------- market autopsy

def no_vig(prices, side):
    keys = [k for k in ("home", "away", "draw", "over", "under") if k in (prices or {})]
    if side not in keys or len(keys) < 2:
        return None
    try:
        import fair
        return fair.probs({k: prices[k] for k in keys})[side]
    except Exception:  # noqa: BLE001
        return None


def side_line(line, market, side):
    """The number from our side's view, where higher means a better number for anyone taking our side. A later
    number higher than ours means the market moved against us (we got the worse of it)."""
    if line is None or market == "h2h":
        return None
    if market == "spread":
        return line if side == "home" else -line
    return -line if side == "over" else line   # over wants a lower total, under a higher one


def first_move_against(pick, snaps):
    """Minutes before the start of the first stored print move against our side after the pick, or None."""
    side, market = pick.get("side"), pick.get("market")
    try:
        t0, start = parse(pick["pickedAt"]), parse(pick["commence"])
    except (KeyError, TypeError, ValueError):
        return None
    after = [s for s in snaps if s.get("t") and t0 < parse(s["t"]) <= start]
    if not after:
        return None
    base_line = side_line(pick.get("marketNumber"), market, side)
    base_nv = no_vig(pick.get("marketPrices"), side)
    for s in after:
        sl = side_line(s.get("line"), market, side)
        worse = False
        if base_line is not None and sl is not None and sl > base_line:
            worse = True
        elif (sl is None or sl == base_line) and base_nv is not None:
            nv = no_vig(s.get("p"), side)
            worse = nv is not None and nv <= base_nv - PRICE_MOVE
        if worse:
            return round((start - parse(s["t"])).total_seconds() / 60)
    return None


def pin_after_pick(pick, snaps):
    """Pinnacle's no-vig move on our side from the pick to its last stored price before the start (same line)."""
    pin, side = pick.get("pinAtPick") or {}, pick.get("side")
    if pin.get("noVig") is None or not side:
        return None
    try:
        start = parse(pick["commence"])
    except (KeyError, TypeError, ValueError):
        return None
    last = [s for s in snaps if s.get("pin") and s.get("t") and parse(s["t"]) <= start]
    if not last:
        return None
    lp = last[-1]["pin"]
    if pick.get("market") != "h2h" and lp.get("line") != pin.get("line"):
        return None
    nv = no_vig(lp.get("p"), side)
    return None if nv is None else round(nv - pin["noVig"], 4)


def _status_at(timeline, when, idx):
    """Value at index idx of the last timeline entry at or before `when` (timeline entries start with a time)."""
    val = None
    for entry in timeline or []:
        if entry[0] <= when:
            val = entry[idx]
        else:
            break
    return val


def news_after_pick(pick, row):
    """Injury, goalie and QB changes between the pick and the start, in points against each team.
    Returns {"items": [...], "home": pts, "away": pts} (positive = that team got weaker) or None if no source."""
    sport, t0, t1 = pick.get("sport"), pick.get("pickedAt"), pick.get("commence")
    home, away = row.get("home") or pick.get("home"), row.get("away") or pick.get("away")
    if not (t0 and t1 and home and away):
        return None
    t0, t1 = t0.replace(".000", ""), t1.replace(".000", "")
    teams = {key(home): "home", key(away): "away"}
    out = {"items": [], "home": 0.0, "away": 0.0}

    def add(team_side, pts, text):
        out[team_side] = round(out[team_side] + pts, 2)
        out["items"].append(f"{text} ({pts:+.1f})")

    if sport == "NBA":
        inj = stats_file("injuries_nba.json")
        if not inj.get("trackingSince") or inj["trackingSince"] > t0:
            return None
        values = stats_file("nba_player_values.json").get("players") or {}
        for pid, p in (inj.get("players") or {}).items():
            ts = teams.get(key(p.get("team")))
            if not ts:
                continue
            w0, w1 = _status_at(p.get("timeline"), t0, 1) or 0.0, _status_at(p.get("timeline"), t1, 1) or 0.0
            val = (values.get(pid) or {}).get("value") or 0.0
            if w0 != w1 and val:
                add(ts, (w1 - w0) * val, f"{p.get('name')} {_status_at(p['timeline'], t1, 2)}")
    elif sport == "NFL":
        # The desk's own starter valuation (injury.py: depth-chart starters, QB tiers, sizing.md values), applied to
        # the window between the pick and the start instead of the open and now.
        inj = stats_file("injuries.json")
        if not inj.get("trackingSince") or inj["trackingSince"] > t0:
            return None
        import injury
        depth, teams_tbl = stats_file("nfl_depth.json"), stats_file("nfl_teams.json").get("teams") or {}
        totals = 0.0
        for team_side, name in (("home", home), ("away", away)):
            sv, tv, items = injury.team_news(name, teams_tbl, inj, depth, t0, t1)
            if sv:
                out[team_side] = round(out[team_side] + sv, 2)
            totals += tv
            out["items"] += [i.replace(" at the open,", " at the pick,").replace(" now,", " at the start,") for i in items]
        out["total"] = round(totals, 2)
    elif sport == "NCAAF":
        qb = stats_file("cfb_qb.json")
        changes = qb.get("changes") or []
        if not changes:
            return None
        for c in changes:
            ts = teams.get(key(c.get("team")))
            if ts and t0 < (c.get("at") or "") <= t1:
                add(ts, CFB_QB_POINTS * cfb_weight(c), f"QB {c.get('from')} -> {c.get('to')}")
    elif sport == "NHL":
        g = stats_file("nhl_goalies.json")
        if not g.get("trackingSince") or g["trackingSince"] > t0:
            return None
        for game in (g.get("games") or {}).values():
            if {key(game.get("home")), key(game.get("away"))} != set(teams) or \
                    abs((parse(game["commence"].replace("Z", ":00Z") if len(game["commence"]) == 17 else game["commence"])
                         - parse(t1)).total_seconds()) > 6 * 3600:
                continue
            for gs in ("home", "away"):
                tl = (game.get("timeline") or {}).get(gs) or []
                n0, n1 = _status_at(tl, t0, 1), _status_at(tl, t1, 1)
                if n0 and n1 and n0 != n1:
                    ts = teams[key(game[gs])]
                    qual = g.get("quality") or {}
                    q0, q1 = (qual.get(n0.lower()) or {}).get("q"), (qual.get(n1.lower()) or {}).get("q")
                    # Quality drop in goals-saved terms; unknown goalies count as a full swing of 0.5.
                    add(ts, round(q0 - q1, 2) if q0 is not None and q1 is not None else 0.5, f"goalie {n0} -> {n1}")
            break
    else:
        return None
    return out


def cfb_weight(change):
    """Absence weight of a college QB change, as injury.py weighs NFL statuses."""
    to = (change.get("to") or "").lower()
    if change.get("kind") == "qb1" or "(out" in to or "(doubtful" in to or "(suspended" in to:
        return 1.0
    if "game-time" in to:
        return 0.5
    if "(questionable" in to:
        return 0.5
    return 0.25


def news_for_side(news, side):
    """Points the news moved toward our side (positive = good for us). Totals: weaker teams favour the under."""
    if not news:
        return 0.0
    if side == "home":
        return news["away"] - news["home"]
    if side == "away":
        return news["home"] - news["away"]
    total = news.get("total")
    if total is None:            # no total valuation: weaker teams lean under
        total = -(news["home"] + news["away"])
    return -total if side == "under" else total


def market_autopsy(pick, row, snaps, entry=None):
    """Why the line moved for or against us between the pick and the close."""
    e = entry or {}
    clv = pick.get("clvProb")
    if not isinstance(clv, (int, float)) or not pick.get("side"):
        return None
    side = pick["side"]
    news = news_after_pick(pick, row)
    news_pts = news_for_side(news, side)
    big_news = news is not None and abs(news_pts) >= (NEWS_POINTS if pick.get("sport") in ("NBA", "NFL") else 0.5)
    div_pick = e.get("sharpDivergenceAtPick")
    div_open = e.get("sharpDivergence")
    steam = e.get("pinMoveBeforePick")
    move_min = first_move_against(pick, snaps)
    pin_after = pin_after_pick(pick, snaps)
    have_snaps = any(s.get("t") and pick.get("pickedAt") and s["t"] > pick["pickedAt"] for s in snaps)

    split = price_split(pick)
    if clv > 0:
        cause = "news-for-us" if big_news and news_pts > 0 else "market-agreed"
    elif split and split["marketMove"] > -MOVE_EPS and split["pricePaid"] < 0:
        cause = "overpaid"
    elif big_news and news_pts < 0:
        cause = "news-after-pick"
    elif isinstance(div_pick, (int, float)) and div_pick <= SHARP_AGAINST:
        cause = "sharps-against-at-pick"
    elif div_pick is None and isinstance(div_open, (int, float)) and div_open <= SHARP_AGAINST:
        cause = "sharps-against-at-open"
    elif isinstance(steam, (int, float)) and steam <= STEAM_AWAY:
        cause = "bet-into-steam"
    elif move_min is not None and move_min <= 60:
        cause = "late-move"
    elif isinstance(pin_after, (int, float)) and pin_after <= -PIN_HELD:
        cause = "sharp-move-against"
    elif isinstance(pin_after, (int, float)) and split and split["fairSource"] == "print":
        cause = "soft-move-against"
    elif have_snaps or news is not None or div_pick is not None or div_open is not None or split:
        cause = "model-wrong"
    else:
        cause = "unknown"
    out = {
        "clv": "beat" if clv > 0 else "lost",
        "cause": cause,
        "prePickFeature": PRE_PICK_FEATURE.get(cause),
        "newsPointsForUs": round(news_pts, 2) if news is not None else None,
        "news": (news or {}).get("items")[:6] if news and news.get("items") else None,
        "newsSourced": news is not None,
        "firstMoveAgainstMinBeforeStart": move_min,
        "pinMoveAfterPick": pin_after,
        "snapsAfterPick": have_snaps,
        "split": split,
    }
    if clv <= 0:
        out["lesson"] = lesson(cause, split, out, pick)
        out["feedback"] = FEEDBACK.get(cause)
        out["nowBlocked"] = now_blocked(pick, split)
    return out


def now_blocked(pick, split):
    """Would today's rules have stopped this read? "parked", "gated" (price not better than Pinnacle's fair price at the
    pick), or None. Uses only what was stored at the pick."""
    try:
        import pull
        if pick.get("pattern") in pull.PARKED:
            return "parked"
    except Exception:  # noqa: BLE001
        pass
    if split and split["fairSource"] == "pinnacle" and split["pricePaid"] <= 0:
        return "gated"
    return None


# ---------------------------------------------------------------- game autopsy

def _num(text):
    try:
        return float(str(text).split("-")[0].split("/")[0])
    except (TypeError, ValueError):
        return None


def _pair(text):
    try:
        a, b = str(text).replace("/", "-").split("-")[:2]
        return float(a), float(b)
    except (TypeError, ValueError):
        return None, None


def extract_box(sport, summary, event):
    """The handful of numbers the variance tags need, keyed home/away, from an ESPN summary and scoreboard event."""
    comp = event["competitions"][0]
    out = {"espnId": event["id"], "period": (comp.get("status") or {}).get("period"),
           "final": ((comp.get("status") or {}).get("type") or {}).get("completed", False)}
    for c in comp.get("competitors") or []:
        hs = c.get("homeAway")
        out[hs] = {"team": (c.get("team") or {}).get("displayName"), "score": _num(c.get("score")),
                   "lines": [_num(x.get("value", x.get("displayValue"))) for x in c.get("linescores") or []]}
    ids = {str((c.get("team") or {}).get("id")): c.get("homeAway") for c in comp.get("competitors") or []}
    for t in (summary.get("boxscore") or {}).get("teams") or []:
        hs = ids.get(str((t.get("team") or {}).get("id")))
        if hs not in out:
            continue
        st = {}
        for s in t.get("statistics") or []:
            st[s.get("name")] = s.get("displayValue")
        box = out[hs]
        if sport in ("NFL", "NCAAF"):
            box["turnovers"] = _num(st.get("turnovers"))
            box["defTD"] = _num(st.get("defensiveTouchdowns"))
        elif sport == "NBA":
            box["three"] = _pair(st.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
            box["ft"] = _pair(st.get("freeThrowsMade-freeThrowsAttempted"))
        elif sport == "NHL":
            box["shots"] = _num(st.get("shotsTotal"))
    if sport == "NHL":
        en = {"home": 0, "away": 0}
        for p in summary.get("plays") or []:
            marks = {((p.get("shotInfo") or {}).get("abbreviation") or ""), ((p.get("strength") or {}).get("abbreviation") or "")}
            if p.get("scoringPlay") and "empty-net" in marks:   # ESPN marks these in shotInfo (verified 2026-10-20)
                hs = ids.get(str((p.get("team") or {}).get("id")))
                if hs in en:
                    en[hs] += 1
        out["emptyNet"] = en
    return out


def _result_value(market, side, line, h, a):
    """Positive: our side won by that much against the number."""
    if market == "spread":
        return ((h - a) if side == "home" else (a - h)) + line
    if market == "total":
        return (h + a - line) * (1 if side == "over" else -1)
    return (h - a) if side == "home" else (a - h)


def game_autopsy(pick, box):
    """Verdict (process vs result) and the box-score variance that decided it, each tag marked helped or hurt."""
    res, clv = pick.get("result"), pick.get("clvProb")
    if res not in ("win", "loss", "push") or not isinstance(clv, (int, float)):
        return None
    verdict = ("push" if res == "push" else
               "right-and-rewarded" if clv > 0 and res == "win" else
               "right-but-unlucky" if clv > 0 else
               "lucky-win" if res == "win" else "market-was-right")
    out = {"verdict": verdict, "tags": [], "boxSourced": bool(box)}
    sport, market, side, line = pick.get("sport"), pick.get("market"), pick.get("side"), pick.get("lineAtPick")
    if not box or "home" not in box or "away" not in box:
        return out
    h, a = box["home"].get("score"), box["away"].get("score")
    if h is None or a is None:
        return out
    helped = res == "win"
    mark = "helped" if helped else "hurt"
    ours = side if side in ("home", "away") else None
    theirs = {"home": "away", "away": "home"}.get(ours)
    if market in ("spread", "total") and isinstance(line, (int, float)) or market == "h2h":
        v = _result_value(market, side, line if isinstance(line, (int, float)) else 0, h, a)
        lim = CLOSE.get((sport, market))
        if lim is not None and abs(v) <= lim:
            out["tags"].append(f"close-margin:{mark}")
    reg = REG_PERIODS.get(sport)
    if reg and (box.get("period") or 0) > reg:
        # Overtime adds points (helps the over) and decides the side for whoever won it.
        if market == "total":
            ot_mark = "helped" if side == "over" else "hurt"
        else:
            rl_h, rl_a = box["home"].get("lines") or [], box["away"].get("lines") or []
            ot_h = sum(x or 0 for x in rl_h[reg:]) if len(rl_h) > reg else None
            ot_a = sum(x or 0 for x in rl_a[reg:]) if len(rl_a) > reg else None
            if ot_h is None or ot_a is None or ot_h == ot_a:
                ot_mark = mark
            else:
                ot_mark = "helped" if (ot_h > ot_a) == (side == "home") else "hurt"
        out["tags"].append(f"overtime:{ot_mark}")
    # Flipped late: the result through the second-to-last regulation period (pace-adjusted for totals) pointed the
    # other way from the final.
    lh, la = box["home"].get("lines") or [], box["away"].get("lines") or []
    if reg and len(lh) >= reg and len(la) >= reg and all(x is not None for x in lh[:reg - 1] + la[:reg - 1]):
        h3, a3 = sum(lh[:reg - 1]), sum(la[:reg - 1])
        if market == "total" and isinstance(line, (int, float)):
            pace = (h3 + a3) * reg / (reg - 1)
            early = (pace - line) * (1 if side == "over" else -1)
        elif market in ("spread", "h2h"):
            early = _result_value(market, side, line if market == "spread" else 0, h3, a3)
        else:
            early = None
        final = _result_value(market, side, line if isinstance(line, (int, float)) else 0, h, a)
        if early is not None and early * final < 0:
            out["tags"].append(f"flipped-late:{mark}")
    hb, ab = box["home"], box["away"]
    if sport in ("NFL", "NCAAF") and hb.get("turnovers") is not None and ab.get("turnovers") is not None:
        diff = ab["turnovers"] - hb["turnovers"]          # positive: home won the turnover battle
        if abs(diff) >= 3:
            good = (diff > 0) == (ours == "home") if ours else None
            out["tags"].append("turnover-swing:" + ("helped" if good else "hurt") if ours else "turnover-swing")
        if (hb.get("defTD") or 0) + (ab.get("defTD") or 0) > 0:
            out["tags"].append("defensive-td" + (":" + mark if market == "total" else ""))
    if sport == "NBA":
        for team in ("home", "away"):
            m, att = (box[team].get("three") or (None, None))
            if m is not None and att and att >= 15:
                pct = m / att
                if abs(pct - 0.36) >= 0.12:
                    hot = pct > 0.36
                    if ours:
                        good = hot == (team == ours)
                        out["tags"].append(f"three-point-outlier:{'helped' if good else 'hurt'}")
                    else:
                        good = hot == (side == "over")
                        out["tags"].append(f"three-point-outlier:{'helped' if good else 'hurt'}")
        fh, fa = hb.get("ft") or (None, None), ab.get("ft") or (None, None)
        if fh[1] is not None and fa[1] is not None and abs(fh[1] - fa[1]) >= 15 and ours:
            good = (fh[1] > fa[1]) == (ours == "home")
            out["tags"].append(f"free-throw-gap:{'helped' if good else 'hurt'}")
    if sport == "NHL":
        en = box.get("emptyNet") or {}
        if en.get("home") or en.get("away"):
            out["tags"].append(f"empty-net:{mark}")
        for team, opp in (("home", "away"), ("away", "home")):
            shots, goals = box[opp].get("shots"), box[opp].get("score")
            if shots and goals is not None and shots >= 20:
                sv = 1 - (goals - (en.get(opp) or 0)) / shots
                if sv >= 0.96 or sv <= 0.85:
                    good_for_team = sv >= 0.96
                    if ours:
                        good = good_for_team == (team == ours)
                    else:
                        good = (not good_for_team) == (side == "over")
                    out["tags"].append(f"goalie-outlier:{'helped' if good else 'hurt'}")
    out["tags"] = sorted(set(out["tags"]))
    return out


# ---------------------------------------------------------------- box-score fetch (data job only)

def _get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())


def espn_date(commence):
    from zoneinfo import ZoneInfo
    return parse(commence).astimezone(ZoneInfo("America/New_York")).strftime("%Y%m%d")


def fetch(limit=MAX_FETCH, dry=False):
    """Cache box-score tags for every settled read's game that is not cached yet. Fail-soft."""
    import memory
    cache = load_json(BOX, {"games": {}, "misses": {}})
    picks = load_json(ROOT / "ledger" / "picks.json", {"picks": []}).get("picks") or []
    rows = memory.all_rows()
    want = {}
    for p in picks:
        row = rows.get(p.get("rowId")) or {}
        sport = p.get("sport")
        if sport not in LEAGUES or not row.get("final") or not p.get("commence"):
            continue
        gid = "|".join(p["rowId"].split("|")[:3])
        if gid in cache["games"] or cache["misses"].get(gid, 0) >= 2:
            continue
        want.setdefault((sport, espn_date(p["commence"])), {})[gid] = row
    if dry:
        return {"cached": len(cache["games"]), "wanted": sum(len(v) for v in want.values())}
    fetched = errors = 0
    for (sport, day), games in sorted(want.items()):
        if fetched >= limit:
            break
        groups = "&groups=80" if sport == "NCAAF" else ""
        try:
            board = _get(ESPN.format(path=f"{LEAGUES[sport]}/scoreboard?dates={day}&limit=400{groups}"))
        except Exception as exc:  # noqa: BLE001
            print("autopsy scoreboard", sport, day, exc)
            errors += 1
            continue
        by_teams = {}
        for ev in board.get("events") or []:
            comp = (ev.get("competitions") or [{}])[0]
            names = {c.get("homeAway"): key((c.get("team") or {}).get("displayName")) for c in comp.get("competitors") or []}
            by_teams[(names.get("home"), names.get("away"))] = ev
        for gid, row in games.items():
            if fetched >= limit:
                break
            ev = by_teams.get((key(row.get("home")), key(row.get("away"))))
            if not ev:
                cache["misses"][gid] = cache["misses"].get(gid, 0) + 1
                continue
            try:
                summary = _get(ESPN.format(path=f"{LEAGUES[sport]}/summary?event={ev['id']}"))
                box = extract_box(sport, summary, ev)
            except Exception as exc:  # noqa: BLE001
                print("autopsy summary", gid, exc)
                errors += 1
                continue
            fetched += 1
            if box.get("final"):
                cache["games"][gid] = box
    cache["asOf"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    BOX.write_text(json.dumps(cache, separators=(",", ":")) + "\n")
    return {"fetched": fetched, "errors": errors, "cached": len(cache["games"]),
            "unmatched": sum(1 for v in cache["misses"].values() if v >= 2)}


_BOXES = None


def box_for(row_id):
    global _BOXES
    if _BOXES is None:
        _BOXES = load_json(BOX, {}).get("games") or {}
    return _BOXES.get("|".join((row_id or "").split("|")[:3]))


def autopsy(pick, row, entry=None):
    """Both autopsies for one settled read, or None if it has no side or no CLV."""
    import memory
    m = market_autopsy(pick, row, memory.snap_rows().get(pick.get("rowId"), []), entry)
    if m is None:
        return None
    g = game_autopsy(pick, box_for(pick.get("rowId")))
    return {"market": m, "game": g}


def main():
    ap = argparse.ArgumentParser(description="EDGE autopsy")
    ap.add_argument("cmd", nargs="?", default="fetch", choices=["fetch", "show"])
    ap.add_argument("pick_id", nargs="?")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if a.cmd == "show":
        import memory
        picks = load_json(ROOT / "ledger" / "picks.json", {"picks": []}).get("picks") or []
        p = next((x for x in picks if x.get("pickId") == a.pick_id), None)
        if not p:
            sys.exit("no pick with that id")
        print(json.dumps(autopsy(p, memory.all_rows().get(p.get("rowId")) or {}), indent=1))
        return
    print(json.dumps({"autopsy": fetch(dry=a.dry)}))


if __name__ == "__main__":
    main()
