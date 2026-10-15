# Soccer: what predicts the move from Pinnacle's early price to the close (2026-10-15)

Understat results and xG joined to football-data Pinnacle early (PSH/PSD/PSA, P>2.5) and closing prices,
EPL, La Liga, Bundesliga, Serie A, Ligue 1, 2014-15 to 2025-26 (20,560 matches). Moves in probability points.

| Signal | Matches | Effect | t |
|---|---|---|---|
| Home luck minus away luck in the last match, per goal ((goals - xG) for minus against) | 19,972 | home -0.10 | -9.4 |
| Home team's points minus expected points, last 5, per point | 17,661 | home -0.09 | -10.0 |
| Away team's points minus expected points, last 5, per point | 17,673 | away -0.075 | -9.1 |
| Both teams' last-match total goals, per goal | 11,155 | over 2.5 +0.07 | +5.9 |
| Even match (both sides 30-45%) | 4,386 | draw +0.30 | +15 |
| Promoted team at home, round 8 on | 2,039 | home -0.21 | -3.5 |
| Big home favourite (65%+) | 3,331 | home -0.12 | -2.4 |
| First 3 rounds | 1,009 | over -0.24 | -2.4 |
| Promoted teams, first 8 rounds | ~600 each | none | |
| Short league rest (4 days or less vs 6+) | ~325 each | none | |

The early price leans on recent results and luck; the close corrects toward underlying (xG) quality, and draws and
unders gain late. All effects are under one point, so they are inputs to edge_stack.py (sharp-drift), not picks alone.
Live form: soccer_form.py (Understat, current season).
