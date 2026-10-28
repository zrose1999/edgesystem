# EDGE living memory

Built by `memory.py`, which runs at the end of every `grade.py` run. Do not edit these files by hand.

**Single writer.** Only the EDGE data job commits memory/log, research.json, summary.md and hypotheses.md (and STATE.md at the repo root, from state.py, and stats/modelcheck.json, from modelcheck.py). Chat
sessions, the health check and the weekly review commit code and docs only: after testing locally, run
`git checkout -- memory/log memory/research.json memory/summary.md memory/hypotheses.md` before committing, and let the
next job run rebuild them. (2026-10-19: three fast runs failed to push because a session committed rebuilt memory
files while they were running; their rebase conflicted on research.json.)

| File | What it is |
|---|---|
| `summary.md` | Under 30 lines. What has beaten the close lately, what has not, early positive leads, largest early-negative slices (still collecting), the grade-order observation, data gaps. Read first in every session and health check. |
| `research.json` | Feature research ledger: every feature, overall (`ALL`) and per sport, with n, mean CLV, t, beat-close count, last-30-day CLV, record, status and distance to grade.py's bars. |
| `hypotheses.md` | Neutral-or-positive conditional pockets, one row the first time each combination is seen (memory.py appends; rows are never edited). Re-checked on the weekly review. Nothing is promoted from it. |
| `log/<YYYY-MM>.jsonl` | One line per settled read (pick, lean, pass, reread), keyed by `pickId`, upserted, never dropped. |

Log entry fields: sport, date, event, home, away, market, kind, counted, side, pattern, grade, openLine, openPrices,
lineAtPick, priceAtPick, pickedAt, fair (the projected number), edge, bar, closeLine, closePrice, closeNoVig, clvProb,
clvPoints, result, units, score, features, injury, weather, reason, falsifier, by, notes.

`counted` is true for the one test entry per pattern, row and side that grade.py counts. Only counted, graded entries
feed research.json and queries.

## Autopsy (post-pick, explanation only)

`autopsy.py` explains each settled read after the fact. It runs inside grade.py (box scores first, then memory.py
attaches an `autopsy` field to every log entry). It is post-pick by definition: never a feature, never a rule.

- **Market autopsy** (the part with signal): why the line moved between the pick and the close. Cause, first match
  wins: `news-after-pick` (injury, goalie or QB change between the pick and the start, valued with the desk's own
  tables: injury.py for NFL starters, nba_player_values for NBA, goalie quality for NHL, cfb_qb changes for NCAAF),
  `sharps-against-at-pick` / `sharps-against-at-open`, `bet-into-steam`, `late-move` (final hour, no news),
  `number-off` (the market moved against us with none of those: our fair number was off), `unknown` (too little
  stored data). Reads that beat the close are `market-agreed` or `news-for-us`.
- **Game autopsy** (mostly noise, labelled so it is not mistaken for signal): verdict `right-and-rewarded`,
  `right-but-unlucky`, `lucky-win`, `market-was-right`, plus box-score variance tags marked helped/hurt
  (close-margin, overtime, flipped-late, turnover-swing, defensive-td, three-point-outlier, free-throw-gap,
  goalie-outlier, empty-net). ESPN box scores are cached in stats/autopsy_box.json (job output).
- research.json `autopsy`: loss causes (n, CLV, sports, patterns) and, for each cause, the pre-pick feature that
  could have warned us with that feature's own CLV. The pre-pick feature is what gets tested; the cause only points
  at it. summary.md carries two lines. Query: `python3 memory.py query --cause news-after-pick`, `--verdict
  right-but-unlucky`, `--tag overtime:hurt`.
- Falsifiers are logged on every entry; judging them is left to the weekly review (free text).

## Pre-pick discipline

Every feature is built only from data that existed when the read was stamped (audit 2026-10-19). research.json
`featureTiming` records each feature's pre-pick source; a feature without one does not go in.

Guaranteed pre-pick: pattern, grade, confidence, market (stamped on the read); timing and minutesToKick (pickedAt vs
commence); venue, role, keyNumber, edgeBar (line, price, fair and bar at the pick); moveBeforePick and sharpDiv (the
open snapshot); sharpDivPick and pinAtPick (Pinnacle in the snapshot the read was priced from); injury (contextAtPick
or the read's own reason text); rest (reason text); wind and precip (contextAtPick, or a row forecast whose asOf is
before the pick); bookAtPick; restDays, restEdge, shortWeek and daysRestHome/Away (schedules in stats/, NBA/NHL/NCAAF); travel,
travelEdge, tzShift and travelMilesHome/Away, tzShiftHome/Away (schedules + stats/team_venues.json).

Post-pick, never features: closeLine, closePrice, closeNoVig, clvProb, clvPoints, result, units, score, and
injuryLatest / weatherLatest (the row's latest text, refreshed until kickoff).

Found and fixed in the audit: wind and injury used the row's latest values, which injury.py and wind.py refresh until
kickoff; only 9 of 211 graded reads had a forecast from before the pick. From 2026-10-19 every read stamps
contextAtPick (weather, injury text, goalie signal as they stood at the pick).

Planned features, timing: late steam before the pick = pre-pick (shipped: steamBeforePick); late steam in the final hour = post-pick (market
studies only, never a read feature); travel and days rest = pre-pick (shipped; schedules are known in advance).

Features (known at the pick, never after it): pattern, grade, confidence, market, timing (early >48h, day 6-48h,
late <6h), venue (home/away), role (fav/dog/pk, or over/under), keyNumber (NFL/NCAAF spreads at or across 3 and 7),
moveBeforePick (for/against/none: did the number move for or against our side between the open and the pick),
edgeBar (edge as a multiple of the bar), injury (any, qb, goalie), rest, wind (<10, 10-15, 15+), precip, bookAtPick.

Status: `research` (under 8 graded reads), `early-positive`, `early-negative` (still collecting; never a retirement
call in the learning phase), `at-promotion-bar` (clears grade.py's promotion bar; a lead for review, not a rule).
memory.py never changes a pattern.
why_not_promoted: features with n >= 30 at or below 0 CLV, or short of their bar, carry a one-line reason in
research.json (CLV and t vs grade.py's bar; for patterns, graded full-bar picks vs needed). Never a retirement call.

Posture (Zack, 2026-10-19): data collection and learning phase. Negative CLV on early features is expected and is
logged to learn from. The grade order (A > B > C) is reported as an observation, not a defect.

Also logged per entry: minutesToKick, and sharpDivergence (Pinnacle minus the print book, no-vig probability of the
picked side, at the open, same line only; Pinnacle opens are stored since 2026-10-14), pinAtPick (Pinnacle's line,
prices, update time and no-vig on the picked side in the snapshot the read was priced from; every read from
2026-10-19 18:00Z) and sharpDivergenceAtPick (the same Pinnacle-minus-print gap at the pick; feature sharpDivPick).

Sharp vs soft: sharpDivergenceAtPick = Pinnacle no-vig minus print-book no-vig on the picked side, same line only.
Positive: Pinnacle rates our side higher than the print book (the print price is soft in our favor). Negative: the
print book rates our side higher than Pinnacle (we are paying above the sharp price). Features: sharpDivPick (direction:
pin-for / aligned / pin-against at 1%) and sharpGapPick (size: <1%, 1-2%, 2%+), with sharpDiv / sharpGapOpen for the
open. Tracked in research.json; never a betting rule.

Late steam (2026-10-19): pull.py appends a compact price snapshot (print book line and prices, Pinnacle line and prices)
to ledger/snaps/<YYYY-MM>/<sport>.jsonl on every run, for games within 72 hours of kickoff, only when a price changed
(row snapSig). pinMoveBeforePick = Pinnacle no-vig on the picked side at the pick (pinAtPick) minus the last stored
snapshot 30 minutes to 6 hours earlier, same line only; feature steamBeforePick (toward / flat / away at 0.5%). Pre-pick.
The final-hour move (last snapshot to the close) is post-pick: market studies only, never a read feature.

Coverage and breakage: every added feature is listed in memory.py COVERED with its start time and scope. summary.md
ends with "<field> on N of M graded reads" for each, plus new reads stamped (SHIPPED fields). A feature still at 0 one
health-check cycle (26 hours) after shipping, or on 0 of 10+ new reads, prints a BREAKAGE line: the health check fixes
it as a broken data path, not a quiet gap. The snapshot writer has its own line (snaps stored in the last 26 hours; BREAKAGE at 0 after the first cycle).
Travel (2026-10-19): stats/team_venues.json holds every NBA, NHL and NCAAF team's home city, coordinates and time zone
(built by hand with team_venues.py from ESPN venues and the offline GeoNames table; rerun when a team moves). For each
team, memory.py measures miles and time zones crossed from its previous game's location to this game's venue
(neutral sites unknown, skipped). Features: travel (none <50 mi, <500, 500-1500, 1500+; totals use the longer trip),
travelEdge (picked team vs opponent, 200-mile band: less/even/more) and tzShift (east/west/none). Pre-pick.

Interaction coverage: the last summary.md line counts graded reads with at least two of sharpDivergenceAtPick,
steamBeforePick (pinMoveBeforePick), daysRest and contextAtPick populated (research.json `interactionCoverage`).

Grade reliability: summary.md shows mean CLV by grade on the last 50 graded reads and whether A > B > C holds
there, under the full-sample grade order (research.json `gradeReliability`). Diagnostic only.

Conditional pockets: under every early-negative slice in summary.md (and in research.json `pockets` for every
early-negative slice with 15+ reads), memory.py tests each other logged feature inside the slice (and the sport, for
cross-sport slices) and reports the best sub-slice with CLV >= 0 and 8+ reads, or "no conditional pocket found in
current features". For the grade order it checks inside grade A and lists features where A > B > C holds (5+ reads
per grade). Each line says how many combinations were tested: with that many tests some pockets appear by chance, so
a pocket is a lead to keep watching, never a rule.
Pairs: the top 3 early-negative slices also test 8 pre-defined feature pairs (memory.py INTERACTIONS), reported after
"| pair:". The list is fixed in advance so the search stays small; the same reads often show up in several slices.

Before proposing a lean or pattern, query similar past reads:

    python3 memory.py query --sport NFL --market total --feature wind=15+
    python3 memory.py query --pattern news-lag --feature timing=early --since 2026-10-01


## memory/losses.md (2026-10-28)
The loss review, rebuilt by memory.py after every grade run (single writer: the data job). Every read that lost to the close, explained by autopsy.py: its CLV split exactly into price paid (fair no-vig at the pick minus the price taken) and market move (fair at the pick to the close), its cause (overpaid, news-after-pick, sharps-against, bet-into-steam, late-move, sharp-move-against, soft-move-against, model-wrong, unknown), a one-line lesson, whether today's rules block it, and what already learns from that cause. Tables cover 30 days; the list covers 7. It explains; it never changes a rule. The weekly review works through it (step 14).
