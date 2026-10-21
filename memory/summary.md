# What EDGE is learning (2026-10-21 02:39Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
233 graded reads counted, 471 logged. CLV is mean clvProb. Patterns move only by grade.py.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 13, CLV +0.7%, t +1.1, last 30d +0.7% on 13; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 137, CLV -1.8%, t -6.1, last 30d -1.8% on 137
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 11, CLV +0.7%, t +1.0 (best of 43 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 15, CLV +0.7% (best of 10)
- ALL timing=early: n 128, CLV -1.9%, t -5.9, last 30d -1.9% on 128
  > pocket: travelEdge=even inside timing=early: n 10, CLV +0.7%, t +0.5 (best of 38 tested; a lead to watch) | pair: venue=away + role=dog n 18, CLV +1.0% (best of 12)
- ALL market=total: n 120, CLV -2.3%, t -9.6, last 30d -2.3% on 120
  > no conditional pocket found in current features (31 combos tested inside market=total) | pair: none (10 pair combos tested)
Observation: edge size is not yet predicting CLV (A -2.2% on 24, B -1.9% on 71, C -1.8% on 138).
  > last 50 graded reads: A -2.0% on 9, B -0.8% on 22, C -2.4% on 19 (order still wrong; diagnostic only)
  > no conditional pocket found in current features (10 combos tested inside grade A)
  > order holds inside role=under: A -2.1% on 9, B -2.2% on 26, C -2.5% on 39 (1 of 17 features tested)
Data gaps, free (building next):
- nfl-rest: needs stats.py to save the free nflverse schedule (stats/nfl_schedule.json); code only
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1163 price snapshots stored in the last 26h, latest 10-21 02:24Z, 208 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 2 of 3 graded reads since 10-19 18:00Z; 148 of 175 new reads stamped (Pinnacle at the pick)
- contextAtPick on 3 of 3 graded reads since 10-19 18:00Z; 175 of 175 new reads stamped (weather/injury/goalie as stamped)
- BREAKAGE: sharpDivergenceAtPick on 0 of 3 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 150 of 150 graded NBA/NHL/NCAAF reads (schedules in stats/; NFL is a gap)
- sharpDivergence on 14 of 233 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 2 of 3 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
- travelMilesAway on 150 of 150 graded NBA/NHL/NCAAF reads (schedules + team_venues.json; neutral sites skipped)
Interaction coverage: 2 graded reads have at least two of (sharpDivergenceAtPick, steamBeforePick, daysRest, contextAtPick) populated.
