# Opening-line drift by sport and market (2026-10-14)

How the price moves from the open to the close on average. A consistent drift means the open is biased, and
betting the side the market drifts toward beats the close by that much on average. Small alone (under 1 point);
used by edge_stack.py as one input, never as a pick on its own.

## NHL, DraftKings open and close (ESPN), 2025-26
| Market | Games | Mean move | se | Halves |
|---|---|---|---|---|
| Home win probability | 1,123 | -0.59 pts | 0.09 | -0.91, -0.28 |
| Over probability (same line) | 841 | +0.55 pts | 0.11 | |
| Home on 2nd night of back-to-back vs rested team, extra | 73 | -1.04 pts | 0.53 | -1.1, -1.0 |
| Away team on back-to-back | 169 | +0.96 relative | | -0.4 then +0.8 (not stable, not used) |

## College football, DraftKings open and close (ESPN), Nov 2025 - Oct 2026
| Market | Games | Mean move | se | Halves |
|---|---|---|---|---|
| Total line | 548 | -0.38 points | 0.12 | -0.28, -0.49 |
| Home spread line | 551 | -0.34 points | 0.11 | -0.67, -0.02 (not stable, not used) |

## NBA, DraftKings open and close (ESPN), 2025-26
No stable drift (home win +0.06 pts; total line +0.37 but halves +0.04 and +0.70).

## Soccer, Pinnacle early to close (football-data), 2022-23 to 2025-26
| League | Matches | Home | Draw | Away | Over 2.5 (se) |
|---|---|---|---|---|---|
| EPL | 1,260 | -0.08 | +0.30 | -0.22 | -0.43 (0.08) |
| La Liga | 1,231 | +0.10 | +0.40 | -0.50 | -0.47 (0.09) |
| Bundesliga | 982 | -0.02 | +0.41 | -0.39 | -0.56 (0.10) |
| Serie A | 1,233 | -0.33 | +0.56 | -0.23 | -0.48 (0.08) |
| Ligue 1 | 1,058 | -0.39 | +0.37 | +0.02 | -0.44 (0.10) |
Draws and unders gain late in every league.
