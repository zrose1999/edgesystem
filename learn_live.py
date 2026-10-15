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
            out.append((row, fair, pat, why))
    return out


def main(dry=False):
    now = datetime.now(timezone.utc)
    rows = pull.load(pull.LEDGER, {"rows": []}).get("rows") or []
    picks = pull.load(pull.PICKS, {"picks": []})["picks"]
    done = {(p.get("rowId"), p.get("pattern")) for p in picks}
    todo = nhl_reads(rows, now, done)
    if dry:
        for row, fair, pat, why in todo:
            print(f"WOULD READ {pat} {row['id']} | {why}")
    else:
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
    print(json.dumps({"learned": len(todo), "dry": dry}))


if __name__ == "__main__":
    main(dry="--dry" in sys.argv[1:])
