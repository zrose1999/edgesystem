# EDGE living memory

Built by `memory.py`, which runs at the end of every `grade.py` run. Do not edit these files by hand.

| File | What it is |
|---|---|
| `summary.md` | Under 30 lines. What has beaten the close lately, what has not, early positive leads, largest early-negative slices (still collecting), the grade-order observation, data gaps. Read first in every session and health check. |
| `research.json` | Feature research ledger: every feature, overall (`ALL`) and per sport, with n, mean CLV, t, beat-close count, last-30-day CLV, record, status and distance to grade.py's bars. |
| `log/<YYYY-MM>.jsonl` | One line per settled read (pick, lean, pass, reread), keyed by `pickId`, upserted, never dropped. |

Log entry fields: sport, date, event, home, away, market, kind, counted, side, pattern, grade, openLine, openPrices,
lineAtPick, priceAtPick, pickedAt, fair (the projected number), edge, bar, closeLine, closePrice, closeNoVig, clvProb,
clvPoints, result, units, score, features, injury, weather, reason, falsifier, by, notes.

`counted` is true for the one test entry per pattern, row and side that grade.py counts. Only counted, graded entries
feed research.json and queries.

## Pre-pick discipline

Every feature is built only from data that existed when the read was stamped (audit 2026-10-19). research.json
`featureTiming` records each feature's pre-pick source; a feature without one does not go in.

Guaranteed pre-pick: pattern, grade, confidence, market (stamped on the read); timing and minutesToKick (pickedAt vs
commence); venue, role, keyNumber, edgeBar (line, price, fair and bar at the pick); moveBeforePick and sharpDiv (the
open snapshot); sharpDivPick and pinAtPick (Pinnacle in the snapshot the read was priced from); injury (contextAtPick
or the read's own reason text); rest (reason text); wind and precip (contextAtPick, or a row forecast whose asOf is
before the pick); bookAtPick.

Post-pick, never features: closeLine, closePrice, closeNoVig, clvProb, clvPoints, result, units, score, and
injuryLatest / weatherLatest (the row's latest text, refreshed until kickoff).

Found and fixed in the audit: wind and injury used the row's latest values, which injury.py and wind.py refresh until
kickoff; only 9 of 211 graded reads had a forecast from before the pick. From 2026-10-19 every read stamps
contextAtPick (weather, injury text, goalie signal as they stood at the pick).

Planned features, timing: late steam before the pick = pre-pick; late steam in the final hour = post-pick (market
studies only, never a read feature); travel and days rest = pre-pick (schedules are known in advance).

Features (known at the pick, never after it): pattern, grade, confidence, market, timing (early >48h, day 6-48h,
late <6h), venue (home/away), role (fav/dog/pk, or over/under), keyNumber (NFL/NCAAF spreads at or across 3 and 7),
moveBeforePick (for/against/none: did the number move for or against our side between the open and the pick),
edgeBar (edge as a multiple of the bar), injury (any, qb, goalie), rest, wind (<10, 10-15, 15+), precip, bookAtPick.

Status: `research` (under 8 graded reads), `early-positive`, `early-negative` (still collecting; never a retirement
call in the learning phase), `at-promotion-bar` (clears grade.py's promotion bar; a lead for review, not a rule).
memory.py never changes a pattern.

Posture (Zack, 2026-10-19): data collection and learning phase. Negative CLV on early features is expected and is
logged to learn from. The grade order (A > B > C) is reported as an observation, not a defect.

Also logged per entry: minutesToKick, and sharpDivergence (Pinnacle minus the print book, no-vig probability of the
picked side, at the open, same line only; Pinnacle opens are stored since 2026-10-14), pinAtPick (Pinnacle's line,
prices, update time and no-vig on the picked side in the snapshot the read was priced from; every read from
2026-10-19 18:00Z) and sharpDivergenceAtPick (the same Pinnacle-minus-print gap at the pick; feature sharpDivPick).

Coverage and breakage: each shipped data feature has a start time (memory.py SHIPPED). summary.md shows how many reads
stamped since then carry it. A shipped feature on 0 of 10+ new reads prints a BREAKAGE line: the health check fixes it
as a broken data path, not a quiet gap. Late steam and travel get the same treatment when they ship.

Grade reliability: summary.md shows mean CLV by grade on the last 50 graded reads and whether A > B > C holds
there, under the full-sample grade order (research.json `gradeReliability`). Diagnostic only.

Conditional pockets: under every early-negative slice in summary.md (and in research.json `pockets` for every
early-negative slice with 15+ reads), memory.py tests each other logged feature inside the slice (and the sport, for
cross-sport slices) and reports the best sub-slice with CLV >= 0 and 8+ reads, or "no conditional pocket found in
current features". For the grade order it checks inside grade A and lists features where A > B > C holds (5+ reads
per grade). Each line says how many combinations were tested: with that many tests some pockets appear by chance, so
a pocket is a lead to keep watching, never a rule.

Before proposing a lean or pattern, query similar past reads:

    python3 memory.py query --sport NFL --market total --feature wind=15+
    python3 memory.py query --pattern news-lag --feature timing=early --since 2026-10-01
