# EDGE living memory

Built by `memory.py`, which runs at the end of every `grade.py` run. Do not edit these files by hand.

| File | What it is |
|---|---|
| `summary.md` | Under 30 lines. What has beaten the close lately, what has not, closest to promotion, kill candidates, gaps. Read first in every session and health check. |
| `research.json` | Feature research ledger: every feature, overall (`ALL`) and per sport, with n, mean CLV, t, beat-close count, last-30-day CLV, record, status and distance to grade.py's bars. |
| `log/<YYYY-MM>.jsonl` | One line per settled read (pick, lean, pass, reread), keyed by `pickId`, upserted, never dropped. |

Log entry fields: sport, date, event, home, away, market, kind, counted, side, pattern, grade, openLine, openPrices,
lineAtPick, priceAtPick, pickedAt, fair (the projected number), edge, bar, closeLine, closePrice, closeNoVig, clvProb,
clvPoints, result, units, score, features, injury, weather, reason, falsifier, by, notes.

`counted` is true for the one test entry per pattern, row and side that grade.py counts. Only counted, graded entries
feed research.json and queries.

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
picked side, at the open, same line only; Pinnacle opens are stored since 2026-10-14).

Before proposing a lean or pattern, query similar past reads:

    python3 memory.py query --sport NFL --market total --feature wind=15+
    python3 memory.py query --pattern news-lag --feature timing=early --since 2026-10-01
