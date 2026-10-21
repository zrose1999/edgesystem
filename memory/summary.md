# What EDGE is learning (2026-10-21 00:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
220 graded reads counted, 450 logged. CLV is mean clvProb. Patterns move only by grade.py.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 12, CLV +0.8%, t +1.2, last 30d +0.8% on 12; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 131, CLV -1.9%, t -6.7, last 30d -1.9% on 131
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 10, CLV +0.9%, t +1.1 (best of 42 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 15, CLV +0.7% (best of 10)
- ALL timing=early: n 125, CLV -2.0%, t -6.4, last 30d -2.0% on 125
  > pocket: travelEdge=even inside timing=early: n 10, CLV +0.7%, t +0.5 (best of 38 tested; a lead to watch) | pair: venue=away + role=dog n 17, CLV +1.1% (best of 12)
- ALL market=total: n 111, CLV -2.5%, t -11.1, last 30d -2.5% on 111
  > no conditional pocket found in current features (30 combos tested inside market=total) | pair: none (10 pair combos tested)
Observation: edge size is not yet predicting CLV (A -2.2% on 23, B -1.9% on 65, C -2.0% on 132).
  > last 50 graded reads: A -2.2% on 10, B -1.0% on 23, C -3.4% on 17 (order still wrong; diagnostic only)
  > no conditional pocket found in current features (7 combos tested inside grade A)
  > order holds inside market=total: A -2.1% on 13, B -2.5% on 32, C -2.6% on 66 (2 of 16 features tested)
Data gaps, free (building next):
- nfl-rest: needs stats.py to save the free nflverse schedule (stats/nfl_schedule.json); code only
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1209 price snapshots stored in the last 26h, latest 10-21 00:24Z, 199 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 2 of 2 graded reads since 10-19 18:00Z; 146 of 171 new reads stamped (Pinnacle at the pick)
- contextAtPick on 2 of 2 graded reads since 10-19 18:00Z; 171 of 171 new reads stamped (weather/injury/goalie as stamped)
- BREAKAGE: sharpDivergenceAtPick on 0 of 2 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 137 of 137 graded NBA/NHL/NCAAF reads (schedules in stats/; NFL is a gap)
- sharpDivergence on 14 of 220 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 2 of 2 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
- travelMilesAway on 137 of 137 graded NBA/NHL/NCAAF reads (schedules + team_venues.json; neutral sites skipped)
Interaction coverage: 2 graded reads have at least two of (sharpDivergenceAtPick, steamBeforePick, daysRest, contextAtPick) populated.
