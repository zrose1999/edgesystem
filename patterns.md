# Patterns

Hypotheses. Each earns trust only by beating the close. Shadow until grade.py says otherwise.

## news-lag

Idea: starter changes, late scratches, and injury upgrades or downgrades in the window before the market fully moves.
Applies: the line has not yet moved the amount the news implies.
Retire early if: the move is already in the number when the pick is stamped.

## early-number

Idea: early-week lines are softer than the close.
Applies: picks stamped more than 48 hours before kickoff.
Retire early if: CLV on early picks is no better than on late picks.

## wind-total

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
