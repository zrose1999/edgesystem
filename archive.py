#!/usr/bin/env python3
"""EDGE archive. Moves finished games out of ledger/ledger.json (which the site downloads on every visit) into
permanent per-sport monthly files: ledger/archive/<YYYY-MM>/<sport>.jsonl, one row per line, nothing dropped
(open, last pre-start snapshot with every book incl. Pinnacle, close, score). This is EDGE's own history for
every sport, the data future patterns are tested on.

  python3 archive.py           move rows; prints counts

A row moves when its game started more than KEEP_DAYS ago and it is final (or started more than STALE_DAYS ago).
Rows with a pick or lean stay PICK_KEEP_DAYS, so the Results tab keeps their detail and grading is never cut short.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pull

ROOT = Path(__file__).resolve().parent
ARCH = ROOT / "ledger" / "archive"
KEEP_DAYS, STALE_DAYS, PICK_KEEP_DAYS = 3, 7, 30


def main():
    now = datetime.now(timezone.utc)
    ledger = pull.load(pull.LEDGER, {"rows": []})
    picked = {p.get("rowId") for p in pull.load(pull.PICKS, {"picks": []}).get("picks") or []
              if p.get("kind") in ("pick", "lean")}
    keep, moved = [], {}
    for r in ledger.get("rows") or []:
        c = r.get("commence")
        if not c:
            keep.append(r)
            continue
        age = (now - pull.parse(c)).total_seconds() / 86400
        limit = PICK_KEEP_DAYS if r.get("id") in picked else KEEP_DAYS
        if age > limit and (r.get("final") or age > max(limit, STALE_DAYS)):
            moved.setdefault((c[:7], r.get("sport") or "other"), []).append(r)
        else:
            keep.append(r)
    for (month, sport), rows in moved.items():
        path = ARCH / month / f"{sport}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        have = set()
        if path.exists():
            have = {json.loads(line).get("id") for line in path.read_text().splitlines() if line.strip()}
        with path.open("a") as fh:
            for r in rows:
                if r.get("id") not in have:
                    fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    if moved:
        ledger["rows"] = keep
        pull.save(pull.LEDGER, ledger)
    print(json.dumps({"archived": sum(len(v) for v in moved.values()), "kept": len(keep),
                      "files": sorted(f"{m}/{s}" for m, s in moved)}))


if __name__ == "__main__":
    main()
