#!/usr/bin/env python3
"""EDGE learned reads. Scores upcoming games with the models learner.py trained and passed through its
out-of-sample gate, using the same feature builders as training. Stamps learned-<target> reads.

  python3 learn_live.py          stamp reads
  python3 learn_live.py --dry

A read is stamped once per game and market when the model is live and its predicted move is in the top 30% by size
(the same rule as the out-of-sample trade test). Fair = current no-vig price + the part of the predicted
open-to-close move not yet made since this desk's open.
"""

import json
import pickle
import sys
import unicodedata
from argparse import Namespace
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

import fair as fairlib
import features_nhl as FN
import learner  # noqa: F401  (model classes)
import pull

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "stats" / "models"
WINDOW_H = 36


def load_model(name):
    p = MODELS / f"{name}.pkl"
    if not p.exists():
        return None
    m = pickle.loads(p.read_bytes())
    return m if m.get("live") else None


def predict(m, f):
    x = np.array([[f.get(k, np.nan) for k in m["keys"]]], dtype=float)
    return float(m["model"].predict(m["prep"].transform(x))[0])


def norm(s):
    return " ".join(unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().split())


def nhl_context():
    team_games = json.loads(FN.TEAMS_FILE.read_text())
    goalies = json.loads(FN.GOALIES_FILE.read_text())
    starters = json.loads(FN.STARTERS_FILE.read_text())
    th = FN.TeamHistory(team_games)
    st_index = defaultdict(list)
    for s in sorted(starters.values(), key=lambda s: s.get("date") or ""):
        st_index[s["home"]].append(s)
        st_index[s["away"]].append(s)
    sched = defaultdict(list)
    g = pull.load(ROOT / "stats" / "nhl_games.json", {}).get("games") or {}
    for x in (g.values() if isinstance(g, dict) else g):
        for side in ("home", "away"):
            a = FN.abbr_of(x.get(side))
            if a and x.get("date"):
                sched[a].append(FN.game_day(x["date"]))
    ids = {}
    for y in goalies.values():
        for pid, rec in y.items():
            ids[norm(rec["name"])] = pid
    probables = pull.load(ROOT / "stats" / "nhl_goalies.json", {}).get("games") or {}
    mt = pull.load(ROOT / "stats" / "nhl_matchups.json", {}).get("games") or []
    model = {(x["event"]): x for x in mt}
    return th, goalies, st_index, sched, ids, probables, model


def probable_id(probables, ids, row, side):
    hm, am = FN.abbr_of(row["home"]), FN.abbr_of(row["away"])
    for rec in probables.values():
        if FN.abbr_of(rec.get("home")) == hm and FN.abbr_of(rec.get("away")) == am:
            tl = (rec.get("timeline") or {}).get(side) or []
            if tl and tl[-1][1]:
                return ids.get(norm(tl[-1][1]))
    return None


def nhl_reads(rows, now, done):
    m_ml, m_over = load_model("nhl_ml"), load_model("nhl_over")
    if not m_ml and not m_over:
        return []
    th, goalies, st_index, sched, ids, probables, model = nhl_context()
    horizon = pull.iso(now + timedelta(hours=WINDOW_H))
    by_game = defaultdict(dict)
    for r in rows:
        if r.get("sport") == "NHL" and r.get("commence") and pull.iso(now) < r["commence"] <= horizon:
            by_game[(r["home"], r["away"], r["commence"])][r["market"]] = r
    out = []
    for (home, away, when), mk in by_game.items():
        ml = mk.get("h2h")
        if not ml or not ml.get("openSnap") or not ml.get("lastSnap"):
            continue
        h, a = FN.abbr_of(home), FN.abbr_of(away)
        if not h or not a:
            continue
        o = ml["openSnap"]
        if "home" not in o or "away" not in o:
            continue
        p_open = fairlib.probs(o, ["home", "away"])["home"]
        tot = mk.get("total")
        t_open = t_over = None
        if tot and tot.get("openSnap") and "over" in tot["openSnap"]:
            t_open = tot["openSnap"].get("line")
            t_over = fairlib.probs(tot["openSnap"], ["over", "under"])["over"]
        mrec = model.get(ml.get("event")) or {}
        raw = mrec.get("raw") or {}
        mp = raw.get("pHome")
        mt = (raw.get("homeScore") or 0) + (raw.get("awayScore") or 0) if raw.get("homeScore") is not None else None
        f = FN.features_for(h, a, when, th, st_index, goalies, sched, p_open, t_open, t_over, mp, mt,
                            probable_id(probables, ids, ml, "home"), probable_id(probables, ids, ml, "away"))
        for name, m, row, keys in (("nhl_ml", m_ml, ml, ["home", "away"]), ("nhl_over", m_over, tot, ["over", "under"])):
            pat = "learned-" + name.replace("_", "-")
            if not m or not row or (row["id"], pat) in done:
                continue
            if name == "nhl_over" and (row["openSnap"].get("line") != row["lastSnap"].get("line") or t_over is None):
                continue
            pred = predict(m, f)
            LOG.append({"target": name, "rowId": row["id"], "pred": round(pred, 5), "open": round(start_of(name, p_open, t_over), 5),
                        "top": abs(pred - m["center"]) >= m["threshold"], "at": pull.iso(now), "book": "print"})
            if abs(pred - m["center"]) < m["threshold"]:
                continue
            cur = fairlib.probs(row["lastSnap"], keys)[keys[0]]
            start = p_open if name == "nhl_ml" else t_over
            moved = cur - start
            already = max(0.0, moved / pred) * abs(pred) if pred else 0.0
            remaining = max(0.0, abs(pred) - already)
            if remaining < 0.003:
                continue
            fair = min(max(cur + (remaining if pred > 0 else -remaining), 0.02), 0.98)
            what = "home win" if name == "nhl_ml" else f"over {row['lastSnap'].get('line')}"
            why = (f"Learned model ({m['kind']}, {len(m['keys'])} data points, trained {m['trained'][:10]}) predicts the "
                   f"{what} price moves {pred:+.3f} from the open; open {start:.3f}, now {cur:.3f}, {remaining:.3f} still to come. "
                   f"Fair {fair:.3f}. Report: stats/models/{name}.json.")
            side = keys[0] if pred > 0 else keys[1]
            e = direct_entry(row, side, fair if side == keys[0] else 1 - fair, pat, why, now)
            if e:
                DIRECT.append(e)
    return out


LOG = []
DIRECT = []
LIVE_LOG = MODELS / "live_log.jsonl"


def start_of(name, p_open, t_over):
    return p_open if name == "nhl_ml" else (t_over or 0.0)


def opn_of(pin, side):
    return dict(zip(("home", "draw", "away"), pin))[side]


def write_log():
    """First prediction per game and target is kept: that is the one the open-to-close move tests."""
    seen = set()
    if LIVE_LOG.exists():
        for line in LIVE_LOG.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                seen.add((r["target"], r["rowId"]))
    new = [r for r in LOG if (r["target"], r["rowId"]) not in seen]
    if new:
        with LIVE_LOG.open("a") as fh:
            for r in new:
                fh.write(json.dumps(r, separators=(",", ":")) + "\n")
    return len(new)


SOCCER_SPORTS = {"EPL", "LaLiga", "Bundesliga", "SerieA", "Ligue1"}
_FORMS = None


ALIASES = {"athletic bilbao": "athletic club", "as roma": "roma", "1. fc koln": "fc cologne", "fc koln": "fc cologne",
           "1. fc union berlin": "union berlin", "bayer leverkusen": "bayer leverkusen", "borussia monchengladbach":
           "borussia m.gladbach", "paris saint germain": "paris saint germain", "inter milan": "inter",
           "ac milan": "ac milan", "atletico madrid": "atletico madrid", "real betis": "real betis",
           "celta vigo": "celta vigo", "rayo vallecano": "rayo vallecano", "1. fsv mainz 05": "mainz 05",
           "fsv mainz 05": "mainz 05", "tsg hoffenheim": "hoffenheim", "vfl wolfsburg": "wolfsburg",
           "sc freiburg": "freiburg", "fc augsburg": "augsburg", "vfb stuttgart": "vfb stuttgart",
           "hamburger sv": "hamburger sv", "fc st. pauli": "st. pauli", "1. fc heidenheim": "fc heidenheim",
           "real racing club de santander": "racing santander", "deportivo la coruna": "deportivo la coruna",
           "stade rennais": "rennes", "olympique lyonnais": "lyon", "olympique marseille": "marseille",
           "as monaco": "monaco", "ogc nice": "nice", "rc lens": "lens", "rc strasbourg": "strasbourg",
           "stade brestois 29": "brest", "losc lille": "lille", "hellas verona": "verona", "wolverhampton wanderers":
           "wolverhampton wanderers", "brighton and hove albion": "brighton", "nottingham forest": "nottingham forest"}


def soccer_team(form, name):
    import difflib
    n = norm(name)
    n = ALIASES.get(n, n)
    best, score = None, 0.0
    for t in form.h:
        tn = norm(t)
        sc = 1.0 if (n.startswith(tn) or tn.startswith(n)) else difflib.SequenceMatcher(None, n, tn).ratio()
        if sc > score:
            best, score = t, sc
    return best if score >= 0.75 else None


def book_trio(snap, bk):
    b = (snap.get("books") or {}).get(bk) or {}
    if not all(k in b for k in ("home", "draw", "away")):
        return None
    p = fairlib.probs(b, ["home", "draw", "away"])
    return p["home"], p["draw"], p["away"]


def direct_entry(row, side, fair, pattern, why, now):
    """A read priced on one side at the best US price (pull.make_read prices the print book only, and assumes
    two-way moneylines). fair is this side's probability."""
    snap = row["lastSnap"]
    market = row["market"]
    # Line-shop the US books (Pinnacle is the reference, not a place to bet): the best price on this side.
    books = {k: v for k, v in (snap.get("books") or {}).items() if k != "pinnacle" and side in v
             and (market != "total" or v.get("line") == snap.get("line"))}
    if books:
        bk = max(books, key=lambda k: books[k][side])
        price, book_name = books[bk][side], books[bk].get("book", bk)
    else:
        price, book_name = snap[side], snap.get("book")
    edge = fair - pull.implied(price)
    bar = pull.H2H_BAR
    grade = pull.grade_for(edge, bar, "medium")
    kind = {"A": "pick", "B": "pick", "C": "lean", "P": "pass"}[grade]
    if kind == "pass":
        return None
    pid = f"{row['id']}|{side}|{pull.VERSION}|{pattern}" + ("" if kind == "pick" else f"|{kind}|{pull.iso(now)}")
    return {"pickId": pid, "kind": kind, "grade": grade, "rowId": row["id"], "sport": row["sport"], "event": row["event"],
            "commence": row["commence"], "market": market, "side": side,
            "lineAtPick": snap.get("line") if market == "total" else None, "priceAtPick": price,
            "bookAtPick": book_name, "marketNumber": snap.get("line"),
            "marketPrices": {k: snap[k] for k in ("home", "away", "draw", "over", "under") if k in snap},
            "priceTime": snap["time"],
            "pickedAt": pull.iso(now), "fair": round(fair, 4), "projection": round(fair, 4), "edge": round(edge, 4),
            "edgeUnit": "prob", "bar": bar, "fullBar": edge >= bar, "confidence": "medium", "pattern": pattern,
            "reason": why, "falsifier": "The close no-vig on this side ends below the price taken (CLV under 0).",
            "modelVersion": pull.VERSION, "tier": "shadow" if kind == "pick" else None, "stakeUnits": 0.0,
            "by": "learn_live.py", "pinAtPick": pull.pin_at_pick(snap, side), "bestAtPick": pull.best_at_pick(snap, side),
            "priceBook": (pull.best_at_pick(snap, side) or {}).get("book"), "contextAtPick": pull.context_at_pick(row)}


def soccer_reads(rows, now, done):
    global _FORMS
    models = {k: load_model(f"soccer_{k}") for k in ("home", "draw", "away", "over")}
    if not any(models.values()):
        return [], []
    import features_soccer as FS
    if _FORMS is None:
        _FORMS = FS.live_form(now.year if now.month >= 7 else now.year - 1)
    horizon = pull.iso(now + timedelta(hours=48))
    games = defaultdict(dict)
    for r in rows:
        if r.get("sport") in SOCCER_SPORTS and r.get("commence") and pull.iso(now) < r["commence"] <= horizon:
            games[(r["sport"], r["home"], r["away"], r["commence"])][r["market"]] = r
    reads, direct = [], []
    for (league, home, away, when), mk in games.items():
        ml = mk.get("h2h")
        if not ml or not ml.get("openSnap") or not ml.get("lastSnap") or league not in _FORMS:
            continue
        form, promoted = _FORMS[league]
        h, a = soccer_team(form, home), soccer_team(form, away)
        pin = book_trio(ml["openSnap"], "pinnacle")
        if not h or not a or not pin:
            continue
        f = FS.match_features(form, h, a, when[:10], league, promoted)
        others = [t for t in (book_trio(ml["openSnap"], b) for b in ("draftkings", "fanduel", "betmgm", "williamhill_us", "pinnacle")) if t]
        avg = tuple(sum(t[i] for t in others) / len(others) for i in range(3)) if others else None
        tot = mk.get("total")
        pin_over = None
        if tot and tot.get("openSnap") and tot["openSnap"].get("line") == 2.5:
            pb = (tot["openSnap"].get("books") or {}).get("pinnacle") or {}
            if "over" in pb and "under" in pb:
                pin_over = fairlib.probs(pb, ["over", "under"])["over"]
        FS.market_features(f, pin[0], pin[1], pin[2], pin_over, avg=avg)
        cur_pin = book_trio(ml["lastSnap"], "pinnacle") or pin
        cur = dict(zip(("home", "draw", "away"), cur_pin))
        opn = dict(zip(("home", "draw", "away"), pin))
        for side in ("home", "draw", "away"):
            m, pat = models[side], "learned-soccer-1x2"
            if not m:
                continue
            pred = predict(m, f)
            LOG.append({"target": f"soccer_{side}", "rowId": ml["id"], "pred": round(pred, 5), "open": round(opn_of(pin, side), 5),
                        "top": abs(pred - m["center"]) >= m["threshold"], "at": pull.iso(now), "book": "pinnacle"})
            if (ml["id"], pat, side) in done:
                continue
            if abs(pred - m["center"]) < m["threshold"] or pred <= 0:
                continue                         # take the side the model expects to gain
            moved = cur[side] - opn[side]
            remaining = max(0.0, pred - max(0.0, moved))
            if remaining < 0.002:
                continue
            fair = cur[side] + remaining
            why = (f"Learned soccer model ({m['kind']}, {len(m['keys'])} data points) predicts Pinnacle's {side} "
                   f"probability gains {pred:+.3f} from the open; Pinnacle open {opn[side]:.3f}, now {cur[side]:.3f}, "
                   f"{remaining:.3f} still to come. Fair {fair:.3f}. Report: stats/models/soccer_{side}.json.")
            e = direct_entry(ml, side, fair, pat, why, now)
            if e:
                direct.append(e)
        m = models["over"]
        if m and tot and pin_over is not None and (tot["id"], "learned-soccer-over") not in {(x[0], x[1]) for x in done}:
            if tot["lastSnap"].get("line") == 2.5:
                pred = predict(m, f)
                LOG.append({"target": "soccer_over", "rowId": tot["id"], "pred": round(pred, 5), "open": round(pin_over, 5),
                            "top": abs(pred - m["center"]) >= m["threshold"], "at": pull.iso(now), "book": "pinnacle"})
                if abs(pred - m["center"]) >= m["threshold"]:
                    pb = (tot["lastSnap"].get("books") or {}).get("pinnacle") or tot["lastSnap"]
                    cur_o = fairlib.probs(pb, ["over", "under"])["over"] if "over" in pb else pin_over
                    moved = cur_o - pin_over
                    already = max(0.0, moved / pred) * abs(pred) if pred else 0.0
                    remaining = max(0.0, abs(pred) - already)
                    if remaining >= 0.002:
                        fair = min(max(cur_o + (remaining if pred > 0 else -remaining), 0.02), 0.98)
                        reads.append((tot, fair, "learned-soccer-over",
                                      f"Learned soccer model ({m['kind']}) predicts Pinnacle's over 2.5 probability moves "
                                      f"{pred:+.3f} from the open; open {pin_over:.3f}, now {cur_o:.3f}, {remaining:.3f} "
                                      f"still to come. Fair {fair:.3f}. Report: stats/models/soccer_over.json."))
    return reads, direct


def nba_reads(rows, now, done):
    """NBA: learned models on spread/total (points) and moneyline (prob); only those that passed the gate."""
    models = {k: load_model(f"nba_{k}") for k in ("spread", "total", "ml")}
    if not any(models.values()):
        return []
    import features_nba as FB
    g = pull.load(ROOT / "stats" / "nba_games.json", {}).get("games") or {}
    games = sorted([x for x in (g.values() if isinstance(g, dict) else g) if x.get("final")], key=lambda x: x["date"])
    book = FB.Book()
    for x in games:
        book.add(x)
    mt = {x["event"]: x for x in (pull.load(ROOT / "stats" / "nba_matchups.json", {}).get("games") or [])}
    horizon = pull.iso(now + timedelta(hours=WINDOW_H))
    by_game = defaultdict(dict)
    for r in rows:
        if r.get("sport") == "NBA" and r.get("commence") and pull.iso(now) < r["commence"] <= horizon:
            by_game[(r["home"], r["away"], r["commence"])][r["market"]] = r
    out = []
    for (home, away, when), mk in by_game.items():
        sp, tt, ml = mk.get("spread"), mk.get("total"), mk.get("h2h")
        if not sp or not sp.get("openSnap"):
            continue
        so = sp["openSnap"].get("line")
        to = (tt or {}).get("openSnap", {}).get("line") if tt else None
        mo = fairlib.probs(ml["openSnap"], ["home", "away"])["home"] if ml and ml.get("openSnap") and "home" in ml["openSnap"] else None
        raw = (mt.get(sp.get("event")) or {}).get("raw") or {}
        f = FB.game_features(book, home, away, when, so, to, mo, raw.get("margin"), raw.get("total"))
        for name, row in (("spread", sp), ("total", tt), ("ml", ml)):
            m, pat = models[name], f"learned-nba-{name}"
            if not m or not row or not row.get("lastSnap") or (row["id"], pat) in done:
                continue
            pred = predict(m, f)
            LOG.append({"target": f"nba_{name}", "rowId": row["id"], "pred": round(pred, 5),
                        "open": (so if name == "spread" else to if name == "total" else mo), "top": abs(pred - m["center"]) >= m["threshold"],
                        "at": pull.iso(now), "book": "print"})
            if abs(pred - m["center"]) < m["threshold"]:
                continue
            if name == "ml":
                cur = fairlib.probs(row["lastSnap"], ["home", "away"])["home"]
                start = mo
            else:
                cur, start = row["lastSnap"].get("line"), row["openSnap"].get("line")
            if cur is None or start is None:
                continue
            moved = cur - start
            already = max(0.0, moved / pred) * abs(pred) if pred else 0.0
            remaining = max(0.0, abs(pred) - already)
            if remaining < (0.003 if name == "ml" else 0.15):
                continue
            fair = cur + (remaining if pred > 0 else -remaining)
            why = (f"Learned NBA model ({m['kind']}, {len(m['keys'])} data points) predicts the {name} moves {pred:+.2f} "
                   f"from the open; open {start}, now {cur}, {remaining:.2f} still to come. Fair {fair:.2f}. "
                   f"Report: stats/models/nba_{name}.json.")
            out.append((row, fair, pat, why))
    return out


def nfl_reads(rows, now, done):
    """NFL: learned models on spread/total (points) and moneyline (prob) from nflverse + backfilled opening lines."""
    models = {k: load_model(f"nfl_{k}") for k in ("spread", "total", "ml")}
    if not any(models.values()):
        return []
    import features_nfl as FL
    book, upcoming = FL.live_book()
    horizon = pull.iso(now + timedelta(days=7))
    by_game = defaultdict(dict)
    for r in rows:
        if r.get("sport") == "NFL" and r.get("commence") and pull.iso(now) < r["commence"] <= horizon:
            by_game[(r["home"], r["away"])][r["market"]] = r
    out = []
    for g in upcoming:
        mk = by_game.get((FL.NAMES.get(g["home_team"], g["home_team"]), FL.NAMES.get(g["away_team"], g["away_team"])))
        if not mk:
            continue
        sp, tt, ml = mk.get("spread"), mk.get("total"), mk.get("h2h")
        if not sp or not sp.get("openSnap"):
            continue
        so = sp["openSnap"].get("line")
        to = (tt or {}).get("openSnap", {}).get("line") if tt else None
        mo = fairlib.probs(ml["openSnap"], ["home", "away"])["home"] if ml and ml.get("openSnap") and "home" in ml["openSnap"] else None
        f = FL.game_features(book, g, so, to, mo)
        for name, row in (("spread", sp), ("total", tt), ("ml", ml)):
            m, pat = models[name], f"learned-nfl-{name}"
            if not m or not row or not row.get("lastSnap") or (row["id"], pat) in done:
                continue
            pred = predict(m, f)
            LOG.append({"target": f"nfl_{name}", "rowId": row["id"], "pred": round(pred, 5),
                        "open": so if name == "spread" else to if name == "total" else mo,
                        "top": abs(pred - m["center"]) >= m["threshold"], "at": pull.iso(now), "book": "print"})
            if abs(pred - m["center"]) < m["threshold"]:
                continue
            if name == "ml":
                cur, start = fairlib.probs(row["lastSnap"], ["home", "away"])["home"], mo
            else:
                cur, start = row["lastSnap"].get("line"), row["openSnap"].get("line")
            if cur is None or start is None:
                continue
            already = max(0.0, (cur - start) / pred) * abs(pred) if pred else 0.0
            remaining = max(0.0, abs(pred) - already)
            if remaining < (0.003 if name == "ml" else 0.15):
                continue
            fair = cur + (remaining if pred > 0 else -remaining)
            why = (f"Learned NFL model ({m['kind']}, {len(m['keys'])} data points; nflverse closes with backfilled opens) "
                   f"predicts the {name} moves {pred:+.3f} from the open; open {start}, now {cur}, {remaining:.3f} still "
                   f"to come. Fair {fair:.3f}. Report: stats/models/nfl_{name}.json.")
            out.append((row, fair, pat, why))
    return out


def ncaaf_reads(rows, now, done):
    """College football: learned models on spread and total (points), built from CFBD history (features_ncaaf.py).
    Lines open about a week ahead, so the window is 7 days."""
    models = {k: load_model(f"ncaaf_{k}") for k in ("spread", "total")}
    if not any(models.values()):
        return []
    import cfb_qb
    import features_ncaaf as FN
    book, upcoming = FN.live_book()
    horizon = pull.iso(now + timedelta(days=7))
    by_game = defaultdict(dict)
    for r in rows:
        if r.get("sport") == "NCAAF" and r.get("commence") and pull.iso(now) < r["commence"] <= horizon:
            by_game[(r["home"], r["away"])][r["market"]] = r
    if not by_game:
        return []
    to_odds = cfb_qb.school_index(sorted({n for k in by_game for n in k}))
    out = []
    for x in upcoming:
        h, a = to_odds(x["home"]), to_odds(x["away"])
        mk = by_game.get((h, a))
        if not mk:
            continue
        sp, tt = mk.get("spread"), mk.get("total")
        if not sp or not sp.get("openSnap"):
            continue
        so = sp["openSnap"].get("line")
        to = (tt or {}).get("openSnap", {}).get("line") if tt else None
        f = FN.game_features(book, x, so, to)
        for name, row in (("spread", sp), ("total", tt)):
            m, pat = models[name], f"learned-ncaaf-{name}"
            if not m or not row or not row.get("lastSnap") or (row["id"], pat) in done:
                continue
            pred = predict(m, f)
            LOG.append({"target": f"ncaaf_{name}", "rowId": row["id"], "pred": round(pred, 5),
                        "open": so if name == "spread" else to, "top": abs(pred - m["center"]) >= m["threshold"],
                        "at": pull.iso(now), "book": "print"})
            if abs(pred - m["center"]) < m["threshold"]:
                continue
            cur, start = row["lastSnap"].get("line"), row["openSnap"].get("line")
            if cur is None or start is None:
                continue
            moved = cur - start
            already = max(0.0, moved / pred) * abs(pred) if pred else 0.0
            remaining = max(0.0, abs(pred) - already)
            if remaining < 0.15:
                continue
            fair = cur + (remaining if pred > 0 else -remaining)
            why = (f"Learned college model ({m['kind']}, {len(m['keys'])} data points, trained on CFBD history) predicts the "
                   f"{name} moves {pred:+.2f} from the open; open {start}, now {cur}, {remaining:.2f} still to come. "
                   f"Fair {fair:.2f}. Report: stats/models/ncaaf_{name}.json.")
            out.append((row, fair, pat, why))
    return out


def archive_reads(rows, now, done):
    """Models learned from EDGE's own archive (features_archive.py): any sport/market that passed the gate."""
    targets = pull.load(ROOT / "stats" / "features" / "archive_targets.json", {})
    if not targets:
        return [], []
    import features_archive as FA
    reads, direct = [], []
    horizon = pull.iso(now + timedelta(hours=WINDOW_H))
    for name in targets:
        m = load_model(name)
        if not m:
            continue
        sport_l, market = name[len("archive_"):].rsplit("_", 1)
        pat = "learned-" + name.replace("_", "-")
        for r in rows:
            if (r.get("sport") or "").lower() != sport_l or r.get("market") != market or (r.get("id"), pat) in done:
                continue
            if not r.get("commence") or not (pull.iso(now) < r["commence"] <= horizon) or not r.get("openSnap") or not r.get("lastSnap"):
                continue
            f = FA.row_features(r, FA.extras_for(r["sport"], market))
            if not f:
                continue
            if "elo_home" in f and "open_prob" in f:
                f["elo_gap"] = f["elo_home"] - f["open_prob"]
            pred = predict(m, f)
            LOG.append({"target": name, "rowId": r["id"], "pred": round(pred, 5), "open": f.get("open_prob", f.get("open_line")),
                        "top": abs(pred - m["center"]) >= m["threshold"], "at": pull.iso(now), "book": "pinnacle"})
            if abs(pred - m["center"]) < m["threshold"]:
                continue
            why = (f"Model learned from EDGE's own {r['sport']} {market} history ({m['kind']}, {len(m['keys'])} data points) "
                   f"predicts a move of {pred:+.3f} from the open. Report: stats/models/{name}.json.")
            if m.get("unit") == "points":
                cur, start = r["lastSnap"].get("line"), r["openSnap"].get("line")
                if cur is None or start is None:
                    continue
                remaining = max(0.0, abs(pred) - max(0.0, (cur - start) / pred) * abs(pred)) if pred else 0.0
                if remaining >= 0.15:
                    reads.append((r, cur + (remaining if pred > 0 else -remaining), pat, why))
            else:
                keys = FA.side_keys(r)
                cur = fairlib.probs(r["lastSnap"], keys)[keys[0]] if all(k in r["lastSnap"] for k in keys) else None
                if cur is None:
                    continue
                start = f.get("open_prob", cur)
                remaining = max(0.0, abs(pred) - max(0.0, (cur - start) / pred) * abs(pred)) if pred else 0.0
                if remaining < 0.003:
                    continue
                fair1 = min(max(cur + (remaining if pred > 0 else -remaining), 0.02), 0.98)
                side = keys[0] if pred > 0 else keys[1]
                if len(keys) == 3 and side == keys[1]:
                    continue                    # three-way: only the side the model expects to gain
                e = direct_entry(r, side, fair1 if side == keys[0] else 1 - fair1, pat, why, now)
                if e:
                    direct.append(e)
    return reads, direct


def main(dry=False):
    now = datetime.now(timezone.utc)
    rows = pull.load(pull.LEDGER, {"rows": []}).get("rows") or []
    picks = pull.load(pull.PICKS, {"picks": []})["picks"]
    done = {(p.get("rowId"), p.get("pattern")) for p in picks}
    todo = nhl_reads(rows, now, done)
    done3 = {(p.get("rowId"), p.get("pattern"), p.get("side")) for p in picks} | {(r, pt, None) for r, pt in done}
    todo += nba_reads(rows, now, done)
    todo += ncaaf_reads(rows, now, done)
    todo += nfl_reads(rows, now, done)
    s_reads, s_direct = soccer_reads(rows, now, done3)
    a_reads, a_direct = archive_reads(rows, now, done)
    todo += s_reads + a_reads
    s_direct = DIRECT + s_direct + a_direct
    if dry:
        for row, fair, pat, why in todo:
            print(f"WOULD READ {pat} {row['id']} | {why}")
        for e in s_direct:
            print(f"WOULD STAMP {e['grade']} {e['pattern']} {e['rowId']} {e['side']} {e['priceAtPick']:+g} edge {e['edge']:+.3f}")
    else:
        doc = pull.load(pull.PICKS, {"picks": []})
        s_direct = pull.gate_direct(s_direct, doc["picks"], {r.get("id"): r.get("lastSnap") for r in rows})
        if s_direct:
            doc["picks"].extend(s_direct)
            pull.save(pull.PICKS, doc)
        for sport in {r["sport"] for r, _, _, _ in todo}:
            if sport not in pull.READ:
                pull.READ = pull.READ + [sport]
        for row, fair, pat, why in todo:
            args = Namespace(id=row["id"], fair=f"{fair:.3f}", confidence="medium", reason=why,
                             falsifier="The price closes at or past the open on the other side of the prediction.",
                             pattern=pat, stake="0", big=True, by="learn_live.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    logged = 0 if dry else write_log()
    print(json.dumps({"learned": len(todo), "learned3way": len(s_direct), "predictionsLogged": logged, "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
