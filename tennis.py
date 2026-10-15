#!/usr/bin/env python3
"""EDGE tennis (v1). Results history, surface Elo, fatigue, and reads on ATP and WTA match moneylines.

  python3 tennis.py              update history (ESPN, free), ratings, stamp reads
  python3 tennis.py --dry        show reads
  python3 tennis.py --backtest   walk-forward calibration of the ratings (stats/backtest_tennis.md)

Data: ESPN tennis scoreboards (every ATP and WTA singles match with set scores and round), back to 2024, kept in
stats/tennis_matches.json and extended every run. Surface comes from the tournament (clay and grass lists below,
hard otherwise).

Model (FiveThirtyEight style): Elo per player overall and per surface, K = 250 / (matches + 5)^0.4, win probability
= 50/50 blend of overall and surface Elo. Players need 20+ rated matches. Retirements and walkovers are not rated.
Fatigue (recorded on every read, tested by the discovery engine): games played in the previous 2 days.

Patterns (both shadow, judged on CLV like everything else):
  tennis-elo      fair home win = market no-vig + WEIGHT x (Elo - market). A model with no market history yet,
                  so a small weight; the archive builds the history that will calibrate it.
  tennis-fatigue  the opponent played 30+ more games in the last 2 days: fair shifts FATIGUE toward the fresher player
                  (starting value, unmeasured; the archive and discovery engine will measure it).
"""

import json
import sys
import urllib.request
from argparse import Namespace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import fair as fairlib
import pull

ROOT = Path(__file__).resolve().parent
HIST = ROOT / "stats" / "tennis_matches.json"
REPORT = ROOT / "stats" / "backtest_tennis.md"
BOARD = "https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard?dates={d}"
START = date(2024, 1, 1)
MAX_REQ = 120
MIN_MATCHES = 20
WEIGHT = 0.20
FATIGUE_GAMES, FATIGUE = 30, 0.02
WINDOW_H = 36
CLAY = ["roland garros", "french open", "madrid", "rome", "internazionali", "monte", "barcelona", "hamburg", "geneva",
        "lyon", "estoril", "munich", "bmw open", "bucharest", "marrakech", "houston", "buenos aires", "argentina open",
        "rio", "santiago", "chile", "cordoba", "bastad", "nordea", "gstaad", "swiss open", "kitzbuhel", "kitzbühel",
        "umag", "croatia", "palermo", "prague", "rabat", "strasbourg", "charleston", "bogota", "parma", "iasi", "lausanne",
        "budapest", "warsaw", "hamburg", "stuttgart porsche", "porsche tennis", "rouen", "saint-malo", "cluj", "bogotá"]
GRASS = ["wimbledon", "queen", "halle", "hertogenbosch", "libema", "eastbourne", "mallorca", "berlin", "bad homburg",
         "nottingham", "birmingham", "newport", "hall of fame", "stuttgart open", "boss open"]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "EDGE desk"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def surface(name, when):
    n = (name or "").lower()
    if any(k in n for k in GRASS):
        return "Grass"
    if any(k in n for k in CLAY):
        return "Clay"
    return "Hard"


def parse_board(tour, d):
    out = []
    for e in d.get("events") or []:
        for g in e.get("groupings") or []:
            gname = ((g.get("grouping") or {}).get("displayName") or "").lower()
            if "singles" not in gname:
                continue
            for c in g.get("competitions") or []:
                st = (c.get("status") or {}).get("type") or {}
                comps = c.get("competitors") or []
                if len(comps) != 2:
                    continue
                names = [((x.get("athlete") or {}).get("displayName")) for x in comps]
                if not all(names):
                    continue
                games = [sum(int(l.get("value") or 0) for l in x.get("linescores") or []) for x in comps]
                win = [bool(x.get("winner")) for x in comps]
                detail = (st.get("detail") or st.get("description") or "").lower()
                out.append({"id": c.get("id"), "tour": tour, "date": c.get("date"), "event": e.get("name"),
                            "surface": surface(e.get("name"), c.get("date")), "round": (c.get("round") or {}).get("displayName", "")[:20],
                            "p": names, "won": win, "games": games, "final": bool(st.get("completed")),
                            "retired": any(w in detail for w in ("ret", "walkover", "w/o", "default"))})
    return out


def update(hist, now):
    have = {m["id"] for m in hist.get("matches") or []}
    todo = hist.setdefault("todo", [])
    if not hist.get("seeded"):
        d = START
        while d <= now.date():
            for tour in ("atp", "wta"):
                todo.append([tour, d.strftime("%Y%m%d")])
            d += timedelta(days=3)
        hist["seeded"] = True
    recent = [[t, (now.date() - timedelta(days=k)).strftime("%Y%m%d")] for k in (0, 1, 2) for t in ("atp", "wta")]
    queue = recent + todo
    done, added = 0, 0
    for tour, d in queue[:MAX_REQ]:
        try:
            board = fetch(BOARD.format(tour=tour, d=d))
        except Exception as exc:  # noqa: BLE001
            print("espn tennis", tour, d, exc)
            continue
        done += 1
        for m in parse_board(tour.upper(), board):
            if m["final"] and m["id"] not in have:
                hist.setdefault("matches", []).append(m)
                have.add(m["id"])
                added += 1
    hist["todo"] = [x for x in todo if x not in queue[:MAX_REQ]]
    hist["matches"].sort(key=lambda m: m["date"] or "")
    hist["asOf"] = pull.iso(now)
    return added, len(hist["todo"])


def k_factor(n):
    return 250 / (n + 5) ** 0.4


def ratings(matches, collect=False):
    E, S, N, SN, preds = {}, {}, {}, {}, []
    for m in matches:
        if m["retired"] or not m["final"] or sum(m["won"]) != 1:
            continue
        w = m["p"][0] if m["won"][0] else m["p"][1]
        l = m["p"][1] if m["won"][0] else m["p"][0]
        sf = m["surface"]
        pe = 1 / (1 + 10 ** ((E.get(l, 1500) - E.get(w, 1500)) / 400))
        ps = 1 / (1 + 10 ** ((S.get((l, sf), 1500) - S.get((w, sf), 1500)) / 400))
        if collect and min(N.get(w, 0), N.get(l, 0)) >= MIN_MATCHES:
            preds.append((0.5 * pe + 0.5 * ps, m["tour"], sf))
        E[w] = E.get(w, 1500) + k_factor(N.get(w, 0)) * (1 - pe)
        E[l] = E.get(l, 1500) - k_factor(N.get(l, 0)) * (1 - pe)
        S[(w, sf)] = S.get((w, sf), 1500) + k_factor(SN.get((w, sf), 0)) * (1 - ps)
        S[(l, sf)] = S.get((l, sf), 1500) - k_factor(SN.get((l, sf), 0)) * (1 - ps)
        for p in (w, l):
            N[p] = N.get(p, 0) + 1
        SN[(w, sf)] = SN.get((w, sf), 0) + 1
        SN[(l, sf)] = SN.get((l, sf), 0) + 1
    return (E, S, N), preds


def prob(R, a, b, sf):
    E, S, N = R
    if min(N.get(a, 0), N.get(b, 0)) < MIN_MATCHES:
        return None
    pe = 1 / (1 + 10 ** ((E.get(b, 1500) - E.get(a, 1500)) / 400))
    ps = 1 / (1 + 10 ** ((S.get((b, sf), 1500) - S.get((a, sf), 1500)) / 400))
    return 0.5 * pe + 0.5 * ps


def recent_games(matches, player, before, days=2):
    lo = pull.iso(before - timedelta(days=days))
    hi = pull.iso(before)
    tot = 0
    for m in matches:
        if m["date"] and lo <= m["date"] < hi and player in m["p"]:
            tot += sum(m["games"])
    return tot


def norm(s):
    import unicodedata
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()


def main(dry=False):
    now = datetime.now(timezone.utc)
    hist = pull.load(HIST, {"matches": []})
    added, left = 0, len(hist.get("todo") or [])
    if not hist.get("asOf") or (now - pull.parse(hist["asOf"])).total_seconds() > 12 * 3600:
        added, left = update(hist, now)              # history refresh twice a day at most
        if not dry:
            HIST.write_text(json.dumps(hist, separators=(",", ":"), ensure_ascii=False))
    matches = hist["matches"]
    R, _ = ratings(matches)
    names = {norm(n): n for n in R[2]}
    ledger = pull.load(pull.LEDGER, {"rows": []})
    picks = pull.load(pull.PICKS, {"picks": []})["picks"]
    done = {(p.get("rowId"), p.get("pattern")) for p in picks}
    horizon = pull.iso(now + timedelta(hours=WINDOW_H))
    todo = []
    for row in ledger.get("rows") or []:
        if row.get("sport") not in ("ATP", "WTA") or row.get("market") != "h2h":
            continue
        if not row.get("commence") or not (pull.iso(now) < row["commence"] <= horizon) or not row.get("lastSnap"):
            continue
        home, away = names.get(norm(row["home"])), names.get(norm(row["away"]))
        if not home or not away:
            continue
        sf = surface(row.get("sportKey", "").replace("tennis_atp_", "").replace("tennis_wta_", "").replace("_", " "), None)
        pm = prob(R, home, away, sf)
        mk = fairlib.probs(row["lastSnap"], ["home", "away"]) if "home" in row["lastSnap"] else None
        if pm is None or not mk:
            continue
        gh, ga = recent_games(matches, home, now), recent_games(matches, away, now)
        note = f"{sf}. Games in the last 2 days: {row['home']} {gh}, {row['away']} {ga}."
        if (row["id"], "tennis-elo") not in done and abs(pm - mk["home"]) >= 0.05:
            fair = mk["home"] + WEIGHT * (pm - mk["home"])
            todo.append((row, fair, "tennis-elo", f"Surface Elo home win {pm:.3f}, market no-vig {mk['home']:.3f}; "
                                                  f"fair = market + {WEIGHT} x gap = {fair:.3f}. {note}"))
        if (row["id"], "tennis-fatigue") not in done and abs(gh - ga) >= FATIGUE_GAMES:
            shift = FATIGUE if ga > gh else -FATIGUE
            fair = mk["home"] + shift
            todo.append((row, fair, "tennis-fatigue", f"{'Away' if shift > 0 else 'Home'} player played {abs(gh - ga)} "
                                                      f"more games in the last 2 days; fair {fair:.3f} "
                                                      f"(starting value {FATIGUE}). {note}"))
    if dry:
        for row, fair, pat, why in todo:
            print(f"WOULD READ {pat} {row['id']} | {why}")
    else:
        for s in ("ATP", "WTA"):
            if s not in pull.READ:
                pull.READ = pull.READ + [s]
        for row, fair, pat, why in todo:
            args = Namespace(id=row["id"], fair=f"{min(max(fair, 0.02), 0.98):.3f}", confidence="medium", reason=why,
                             falsifier="The price closes at or past the market's open on the other side.",
                             pattern=pat, stake="0", big=True, by="tennis.py")
            try:
                pull.make_read(args)
            except SystemExit as exc:
                print(f"read not stamped {row['id']}: {exc}")
    print(json.dumps({"tennis": "ok", "added": added, "matches": len(matches), "backfillLeft": left,
                      "players": len(R[2]), "reads": len(todo), "dry": dry}))


def backtest():
    hist = pull.load(HIST, {"matches": []})
    _, preds = ratings(hist["matches"], collect=True)
    import math
    if not preds:
        print("no history")
        return
    ll = -sum(math.log(max(p, 1e-6)) for p, _, _ in preds) / len(preds)
    rows = ["# Tennis surface Elo, walk-forward (tennis.py --backtest)", "",
            f"{len(preds)} matches with both players on {MIN_MATCHES}+ rated matches. Log loss {ll:.4f} "
            "(coin flip 0.6931). No market history yet: the archive builds it.", "",
            "| Favourite's probability | Matches | Model average | Won |", "|---|---|---|---|"]
    for lo in (0.5, 0.6, 0.7, 0.8, 0.9):
        xs = [(max(p, 1 - p), 1.0 if p >= 0.5 else 0.0) for p, _, _ in preds if lo <= max(p, 1 - p) < lo + 0.1]
        if xs:
            rows.append(f"| {lo:.0%} to {lo + 0.1:.0%} | {len(xs)} | {sum(a for a, _ in xs) / len(xs):.1%} | "
                        f"{sum(b for _, b in xs) / len(xs):.1%} |")
    REPORT.write_text("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    if "--backtest" in sys.argv[1:]:
        backtest()
    else:
        main(dry="--dry" in sys.argv[1:])
