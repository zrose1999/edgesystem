#!/usr/bin/env python3
"""EDGE CS2 ratings (v1). Map-level Elo from every finished CS2 map in PandaScore, turned into series win
probabilities for upcoming matches. kalshi.py prices Kalshi's CS2 match markets (KXCS2GAME) from these as the
cs2-elo source, paper-only, judged on Kalshi's own closing price.

  python3 cs2.py              update history, ratings, upcoming fair prices
  python3 cs2.py --backtest   walk-forward calibration report (stats/backtest_cs2.md)

Needs PANDASCORE_TOKEN (free PandaScore account). Without it the script does nothing.

Model
  Every finished, non-forfeit map is one Elo game: expected = 1 / (1 + 10^(-(Ra - Rb) / 400)).
  K = K_NEW for a team's first NEW_MAPS maps, then K. New teams start at START.
  Teams idle for more than IDLE_DAYS drift IDLE_PULL of the way back to START (rosters change).
  Series: best of 1, 3 or 5 from the map probability (maps treated as independent).
  These are starting values; the backtest report shows calibration, CLV on Kalshi decides.
"""

import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HIST = ROOT / "stats" / "cs2_matches.json"
OUT = ROOT / "stats" / "cs2_ratings.json"
REPORT = ROOT / "stats" / "backtest_cs2.md"
API = "https://api.pandascore.co"
START, K, K_NEW, NEW_MAPS = 1500.0, 24.0, 40.0, 15
IDLE_DAYS, IDLE_PULL = 60, 0.3
BACKFILL_DAYS = 400
MAX_PAGES = 60                 # per run; the free plan allows 1,000 requests an hour


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False))


def get(path, params, token):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(f"{API}{path}?{q}", headers={"Authorization": f"Bearer {token}",
                                                              "Accept": "application/json", "User-Agent": "EDGE desk"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 3:
                time.sleep(20 * (attempt + 1))
                continue
            raise


def slim(m):
    """Only what the model needs from a PandaScore match."""
    opp = [o.get("opponent") or {} for o in m.get("opponents") or []]
    if len(opp) != 2:
        return None
    games = [{"pos": g.get("position"), "winner": (g.get("winner") or {}).get("id")}
             for g in m.get("games") or [] if g.get("finished") and not g.get("forfeit") and (g.get("winner") or {}).get("id")]
    return {"id": m["id"], "begin": m.get("begin_at") or m.get("scheduled_at"), "bestOf": m.get("number_of_games"),
            "status": m.get("status"),
            "teams": [{"id": o.get("id"), "name": o.get("name"), "acronym": o.get("acronym")} for o in opp],
            "winner": m.get("winner_id"), "forfeit": bool(m.get("forfeit")), "games": sorted(games, key=lambda g: g["pos"] or 0),
            "tier": (m.get("tournament") or {}).get("tier"), "league": (m.get("league") or {}).get("name"),
            "score": {str(r.get("team_id")): r.get("score") for r in m.get("results") or []}}


def save_sample(token):
    """A few raw matches, so what the PandaScore plan returns can be checked (stats/cs2_sample.json)."""
    try:
        out = {}
        for name, path, params in (("page1", "/csgo/matches/past", {"filter%5Bstatus%5D": "finished", "sort": "-begin_at",
                                                                     "per_page": 100, "page": 1}),
                                   ("page2", "/csgo/matches/past", {"filter%5Bstatus%5D": "finished", "sort": "-begin_at",
                                                                     "per_page": 100, "page": 2}),
                                   ("furia", "/csgo/matches/past", {"search%5Bname%5D": "FURIA", "per_page": 3}),
                                   ("upcoming", "/csgo/matches/upcoming", {"sort": "begin_at", "per_page": 5})):
            try:
                out[name] = get(path, params, token)
            except Exception as exc:  # noqa: BLE001
                out[name] = {"error": str(exc)}
        for k in ("page1", "page2"):
            if isinstance(out.get(k), list):
                out[k] = [{"id": m.get("id"), "begin": m.get("begin_at"), "end": m.get("end_at"), "status": m.get("status"),
                           "tier": (m.get("tournament") or {}).get("tier"), "name": m.get("name")} for m in out[k]]
        save(ROOT / "stats" / "cs2_sample.json", out)
    except Exception as exc:  # noqa: BLE001
        save(ROOT / "stats" / "cs2_sample.json", {"error": str(exc)})


def update_history(hist, token, now):
    """Newest finished matches first, page by page, until a known id or the backfill limit."""
    known = {m["id"] for m in hist.get("matches") or []}
    oldest_wanted = iso(now - timedelta(days=BACKFILL_DAYS))
    added, page = [], hist.get("resumePage") or 1
    resuming = page > 1
    for _ in range(MAX_PAGES):
        batch = get("/csgo/matches/past", {"filter%5Bstatus%5D": "finished", "sort": "-begin_at",
                                           "per_page": 100, "page": page}, token)
        if not batch:
            hist["resumePage"] = None
            break
        # Stop once a whole page is already known (a match that ran long can land below known ones).
        stop = not resuming and all(m["id"] in known for m in batch)
        older = 0
        for m in batch:
            s = slim(m)
            if not s or not s["begin"]:
                continue
            if s["begin"] < oldest_wanted:
                older += 1
                continue
            if s["status"] == "finished" and m["id"] not in known:
                added.append(s)
                known.add(m["id"])
        # Canceled and rescheduled matches carry stray dates; stop only once most of a page is past the limit.
        if older > len(batch) // 2:
            stop = True
        page += 1
        if stop:
            hist["resumePage"] = None
            break
    else:
        hist["resumePage"] = page            # backfill continues next run
    hist["matches"] = sorted((hist.get("matches") or []) + added, key=lambda m: m["begin"] or "")
    return len(added)


def map_prob(ra, rb):
    return 1 / (1 + 10 ** (-(ra - rb) / 400))


def series_prob(p, best_of):
    n = best_of if best_of in (1, 3, 5) else 1
    need = n // 2 + 1
    return sum(math.comb(need - 1 + k, k) * p ** need * (1 - p) ** k for k in range(need))


class Ratings:
    def __init__(self):
        self.r, self.n, self.last = {}, {}, {}

    def get(self, tid, when):
        r = self.r.get(tid, START)
        last = self.last.get(tid)
        if last and (parse(when) - parse(last)).days > IDLE_DAYS:
            r = r + IDLE_PULL * (START - r)
            self.r[tid] = r
        return r

    def play(self, a, b, a_won, when):
        ra, rb = self.get(a, when), self.get(b, when)
        e = map_prob(ra, rb)
        ka = K_NEW if self.n.get(a, 0) < NEW_MAPS else K
        kb = K_NEW if self.n.get(b, 0) < NEW_MAPS else K
        self.r[a] = ra + ka * ((1.0 if a_won else 0.0) - e)
        self.r[b] = rb + kb * ((0.0 if a_won else 1.0) - (1 - e))
        for t in (a, b):
            self.n[t] = self.n.get(t, 0) + 1
            self.last[t] = when


def run_model(matches, collect=False):
    R, preds = Ratings(), []
    for m in matches:
        if m.get("status", "finished") != "finished" or m["forfeit"] or not m["games"] or not m["begin"]:
            continue
        a, b = m["teams"][0]["id"], m["teams"][1]["id"]
        if collect and m["winner"] in (a, b) and min(R.n.get(a, 0), R.n.get(b, 0)) >= 10:
            p = series_prob(map_prob(R.get(a, m["begin"]), R.get(b, m["begin"])), m["bestOf"])
            preds.append((p, 1.0 if m["winner"] == a else 0.0, m["tier"]))
        for g in m["games"]:
            if g["winner"] in (a, b):
                R.play(a, b, g["winner"] == a, m["begin"])
    return R, preds


def main():
    token = os.environ.get("PANDASCORE_TOKEN", "").strip()
    if not token:
        print(json.dumps({"cs2": "PANDASCORE_TOKEN not set; skipped"}))
        return
    now = datetime.now(timezone.utc)
    hist = load(HIST, {"matches": []})
    try:
        added = update_history(hist, token, now)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"cs2": f"history: {exc}"}))
        added = 0
    save(HIST, hist)
    save_sample(token)
    R, _ = run_model(hist["matches"])
    upcoming = []
    try:
        for page in (1, 2):
            batch = get("/csgo/matches/upcoming", {"sort": "begin_at", "per_page": 100, "page": page}, token)
            for m in batch:
                s = slim(m)
                if not s or not s["begin"] or s["begin"] > iso(now + timedelta(days=3)):
                    continue
                a, b = s["teams"]
                if min(R.n.get(a["id"], 0), R.n.get(b["id"], 0)) < 10:
                    continue                      # too few maps to rate
                p = series_prob(map_prob(R.get(a["id"], s["begin"]), R.get(b["id"], s["begin"])), s["bestOf"])
                upcoming.append({"id": s["id"], "begin": s["begin"], "bestOf": s["bestOf"], "tier": s["tier"],
                                 "league": s["league"], "a": a, "b": b, "pA": round(p, 4),
                                 "mapsA": R.n.get(a["id"], 0), "mapsB": R.n.get(b["id"], 0)})
            if len(batch) < 100:
                break
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"cs2": f"upcoming: {exc}"}))
    save(OUT, {"asOf": iso(now), "model": {"start": START, "k": K, "kNew": K_NEW}, "upcoming": upcoming,
               "teams": len(R.r), "backfillPending": bool(hist.get("resumePage"))})
    print(json.dumps({"cs2": "ok", "added": added, "matches": len(hist["matches"]), "upcoming": len(upcoming),
                      "backfillPending": bool(hist.get("resumePage"))}))


def backtest():
    hist = load(HIST, {"matches": []})
    _, preds = run_model(hist["matches"], collect=True)
    if not preds:
        print("no history yet")
        return
    ll = -sum(y * math.log(max(p, 1e-6)) + (1 - y) * math.log(max(1 - p, 1e-6)) for p, y, _ in preds) / len(preds)
    brier = sum((p - y) ** 2 for p, y, _ in preds) / len(preds)
    rows = ["# CS2 map Elo, walk-forward (cs2.py --backtest)", "",
            f"{len(preds)} series with both teams on 10+ rated maps. Log loss {ll:.4f} (coin flip 0.6931), Brier {brier:.4f}.", "",
            "| Model favourite's probability | Series | Model average | Won |", "|---|---|---|---|"]
    for lo in (0.5, 0.6, 0.7, 0.8, 0.9):
        xs = [(max(p, 1 - p), y if p >= 0.5 else 1 - y) for p, y, _ in preds if lo <= max(p, 1 - p) < lo + 0.1]
        if xs:
            rows.append(f"| {lo:.0%} to {lo + 0.1:.0%} | {len(xs)} | {sum(p for p, _ in xs) / len(xs):.1%} | "
                        f"{sum(y for _, y in xs) / len(xs):.1%} |")
    REPORT.write_text("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    backtest() if "--backtest" in sys.argv[1:] else main()
