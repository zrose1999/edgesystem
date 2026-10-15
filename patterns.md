# Patterns

Hypotheses. Each earns trust only by beating the close. Shadow until grade.py says otherwise.

## news-lag

Starter news is stamped by injury.py, never by hand: status history from the ESPN injury report with this desk's own first-seen times (stats/injuries.json), starters from ESPN depth charts refreshed daily (stats/nfl_depth.json, a starter in the last 10 days still counts), and the sizing.md values at the low end of each range (QB elite 6.0 / average 3.75 / weak 1.75 by EPA tier; WR1 0.5; RB1 0.25; LT or C 0.5; other OL 0.25; two+ OL out +0.5; kicker 0.5; defensive starter 0.25; totals QB -2.25, WR1 or RB1 -0.5, two+ OL -0.5). Only news after the open counts.
Idea: starter changes, late scratches, and injury upgrades or downgrades in the window before the market fully moves.
Applies: the line has not yet moved the amount the news implies.
Retire early if: the move is already in the number when the pick is stamped.
NBA (injury_nba.py): same rule, NBA values. Player value = production per 36 minutes above replacement (Game Score 9) x share of 36 minutes x 0.30, capped at 7 (Jokic about 6, a rotation starter about 1.5). Status weight from the ESPN comment: out 1.0, doubtful 0.75, questionable or game-time 0.5, probable 0.1, other day-to-day 0.4. Totals: 0.6 of the spread value off the total. Tracking began 2026-10-14. Shares the news-lag record with NFL; split it if one sport drags the other.

## early-number

Idea: early-week lines are softer than the close.
Applies: picks stamped more than 48 hours before kickoff.
Retire early if: CLV on early picks is no better than on late picks.

## wind-total

Stamped by wind.py, never by hand. Forecast from weather.gov, written on every outdoor NFL and NCAAF row inside 72 hours. Valued inside 36 hours with the sizing.md midpoints (15 to 19 mph -2.0, 20+ mph -3.5, heavy rain or snow -1.0). One read per row inside 24 hours, fair = open total + value, skipped when the open was taken inside 36 hours.
Idea: kickoff wind of 15 mph or more is underpriced on outdoor totals.
Applies: outdoor NFL or NCAAF totals with a real forecast within 24 hours of kickoff.
Retire early if: totals already move the full amount before the forecast firms up.

## luck-reversion

Status: parked until k is above 0. Do not stamp.
Idea: teams whose record runs well ahead of or behind their efficiency (turnover margin, one-score games) are priced toward the record.
Applies: a gap between record and efficiency that the reason can name.
Retire early if: CLV is flat after 30 picks.

## stats-model

Stamped by model.py, never by hand.
Idea: the stats.py efficiency model's own number, using a quarter of its gap from the market.
Applies: every NFL spread and total the model projects. One read per game and market.
Retire early if: CLV is below 0 after 30 picks. The backtest expects this; the live test decides.

## trend-fade

Stamped by model.py, never by hand.
Idea: when both teams have gone over (or under) in most games this season, the total is priced too far that way. Lean against the trend.
Applies: NFL totals where both teams have at least 3 decisions and their combined over rate is 65% or more (lean under) or 35% or less (lean over).
Backtest: 2010 to 2025 at the closing total, fading went 321-267 (54.6%). Following went 267-321.
Retire early if: CLV is below 0 after 30 picks.

## sharp-soft

Stamped by sharp.py, never by hand.
Idea: Pinnacle moves first. When a retail book (DraftKings, FanDuel, BetMGM, Caesars) hangs a better price than Pinnacle's no-vig probability on the same line, the retail price is stale and should beat the close.
Applies: every pulled sport. Same line at both books, Pinnacle updated within 60 minutes of the soft book. A at a 3.0% probability edge, B at 1.5%. Over 10% is a data error and is skipped.
Retire early if: CLV is below 0 after 30 picks.

## sharp-soft-alt

Stamped by sharp.py, never by hand.
Idea: same as sharp-soft, but the retail book sits on a different spread or total number than Pinnacle, at most 1 point away. Pinnacle's fair probability is moved to the retail line with the per-point and key-number values grade.py uses (0.03 per crossing of 3 or 7 on NFL and NCAAF spreads).
Applies: NFL, NCAAF and NBA spreads and totals only. Goal and run totals are not priced this way.
Retire early if: CLV is below 0 after 30 picks. If it trails sharp-soft by a wide margin, the per-point values are wrong, not the idea.

## nba-stats-model

Stamped by model_nba.py on the morning run, never by hand.
Idea: the NBA team ratings in stats_more.py, at a quarter of their gap from the market (fair = market + 0.25 x (raw - market)), same as the NFL stats-model. Its own record, so NBA does not borrow NFL's.
Applies: NBA spreads and totals tipping within 48 hours. Calibration k is 0 on both (stats/nba_matchups.json), so these start as a test of the raw number, not a proven edge. Early-season ratings lean on last season.
Retire early if: CLV is below 0 after 30 picks.

## nba-model-fav

Stamped by model_nba.py, never by hand.
Idea: the nba-stats-model spread read, kept only when the model's side is the market favourite. The live test of the Rose desk's NBA spreads bucket (15-13, +1.06 pts CLV on 4 real closes; see stats/history_audit.md).
Applies: NBA spreads within 48 hours where the model takes the favourite.
Retire early if: CLV is below 0 after 30 picks, or it tracks nba-stats-model so closely that it adds nothing.

## rest-spot

Stamped by rest_nba.py, never by hand.
Idea: NBA lines open without fully pricing a back-to-back. Second night of a back-to-back against a team with 2+ days off: in 2025-26 the home line moved 0.93 points toward the rested home team (se 0.19, n 123) and 0.50 toward a rested away team (se 0.18, n 111), in both halves of the season. At the close neither spot beat the spread, so the edge is beating the move. See stats/backtest_nba_rest.md.
Applies: NBA spreads within 36 hours. Fair = current line + the part of the usual move (0.9 or 0.5) not yet made since this desk's open. Drift the other way is never counted.
Note: edges are at most 0.9 points, under the NBA spread half-bar (1.0), so under the current bars these log as leans: graded on CLV in the pattern's full test, never promoted. A pattern bar change is Zack's call.
Retire early if: CLV is below 0 after 30 reads.

## goalie-news

Stamped by goalie_nhl.py, never by hand.
Idea: NHL starting-goalie news (ESPN probable starters, expected or confirmed) moves the moneyline and total before the market fully adjusts. Backtest 2025-26 (1,018 games, quality from the season before): the home moneyline moved 1.85 points of win probability per goal of GSAx/60 gap between the starter and the team's No. 1 (se 0.29); the close priced it. Totals moved 0.12 goals down per goal of combined gap (se 0.05).
Applies: NHL moneylines and totals within 30 hours. Only goalie news this desk first saw after the open counts (tracking began 2026-10-14). Totals only while the line is still the open line. Values in sizing.md.
Retire early if: CLV is below 0 after 30 picks.

## cs2-elo (Kalshi source)

Run by cs2.py and kalshi.py, never by hand. Not a sportsbook pattern: no odds feed covers CS2, so it lives on the Kalshi paper book only.
Idea: a map-level Elo built from every finished CS2 map in PandaScore (K 24, 40 for a team's first 15 maps, idle teams drift back toward 1500), turned into best-of-1/3/5 series odds, against Kalshi's CS2 match markets (KXCS2GAME).
Applies: both teams with 10+ rated maps, Kalshi bid-ask spread 10 cents or less on the side bought, edge 2 to 15 cents after fee. Paper-only.
Judged on: Kalshi CLV (the same-side mid last seen before start minus the price paid), plus the walk-forward calibration report stats/backtest_cs2.md.
Retire early if: mean Kalshi CLV is below 0 after 30 trades.

## ncaaf-total-move

Stamped by model_ncaaf.py on the morning run, never by hand.
Idea: the NCAAF ratings' total knows where the line is going, not where the game lands. Walk-forward backtest, 540 games: close - open = 0.18 x (model - open), se 0.029; 0.13 and 0.24 in the two halves; with the model 4+ points off the open, the total moved toward it 1.3 points on average, about 60% of the time. Against the close the model has no edge (kTotal 0).
Applies: NCAAF totals within 7 days, model 4+ points from the open. Fair = current total + the part of the expected move (0.18 x gap) not yet made. K fixed at 0.18; the weekly review can propose a new value.
Note: edges are usually 0.7 to 1.5 points, mostly under the NCAAF totals half-bar (1.5), so most log as leans graded on CLV. A bar for measured-move patterns (with rest-spot) is Zack's call.
Retire early if: CLV is below 0 after 30 reads.

## nhl-ml-move and nhl-total-move

Stamped by move_nhl.py on the morning run. The NHL ratings used only for where the price goes between the open and the close: moneyline k 0.10 (backtest 0.104, se 0.015; halves 0.12, 0.06), total k 0.20 (0.236, se 0.018; halves 0.28, 0.16). Gap 4+ points from the open. Fair = current + the part of the expected move not yet made.
Retire early if: CLV is below 0 after 30 reads.

## edge-stack

Stamped by edge_stack.py. The expected remaining moves of every measured pattern on one game and side (news-lag, rest-spot, goalie-news, wind-total, ncaaf-total-move, nhl-ml-move, nhl-total-move), plus the measured opening drift and NHL home back-to-back (stats/backtest_drift.md), summed x0.85 for overlap. Two or more sources, all the same direction. Model-only patterns without proven CLV (stats-model, nba-stats-model, trend-fade) and price gaps are not stacked.
Retire early if: CLV is below 0 after 30 reads, or below the best single source it is built from.

## sharp-drift

Stamped by edge_stack.py. Pinnacle no-vig now plus the part of the measured open-to-close drift still to come (NHL, NCAAF totals, five soccer leagues incl. draws), against the best retail price on the same line. Bar as sharp-soft.
Retire early if: CLV is below 0 after 30 picks.

## tennis-elo and tennis-fatigue

Stamped by tennis.py every run (history refreshed from ESPN twice a day: every ATP and WTA singles match since 2024, 28,575 at launch). Surface Elo (overall + surface, FiveThirtyEight K), walk-forward calibration in stats/backtest_tennis.md (70-80% favourites won 71.1%, 80-90% won 80.5%: slightly overconfident at the top). tennis-elo: fair = market no-vig + 0.20 x (Elo - market), gap 5+ points. tennis-fatigue: opponent played 30+ more games in the last 2 days, fair +0.02 toward the fresher player (starting value, unmeasured).
No tennis market history exists yet; the archive builds it and the weekly review sets the weight from CLV.
Retire early if: CLV is below 0 after 30 reads.
