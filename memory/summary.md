# What EDGE is learning (2026-10-20 01:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
204 graded reads counted, 391 logged. CLV is mean clvProb. Patterns move only by grade.py.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 11, CLV +0.8%, t +1.1, last 30d +0.8% on 11; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 125, CLV -1.8%, t -6.3, last 30d -1.8% on 125
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 10, CLV +0.9%, t +1.1 (best of 41 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 14, CLV +0.8% (best of 9)
- ALL timing=early: n 116, CLV -2.0%, t -6.2, last 30d -2.0% on 116
  > pocket: travelEdge=even inside timing=early: n 10, CLV +0.7%, t +0.5 (best of 36 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 15, CLV +0.9% (best of 11)
- ALL market=total: n 102, CLV -2.4%, t -10.5, last 30d -2.4% on 102
  > no conditional pocket found in current features (30 combos tested inside market=total) | pair: none (10 pair combos tested)
Observation: edge size is not yet predicting CLV (A -2.4% on 18, B -1.8% on 60, C -1.9% on 126).
  > last 50 graded reads: A -2.6% on 9, B -1.3% on 27, C -2.3% on 14 (order still wrong; diagnostic only)
  > no conditional pocket found in current features (4 combos tested inside grade A)
  > order holds inside market=total: A -1.6% on 10, B -2.3% on 29, C -2.5% on 63 (2 of 13 features tested)
Data gaps, free (building next):
- nfl-rest: needs stats.py to save the free nflverse schedule (stats/nfl_schedule.json); code only
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 411 price snapshots stored in the last 26h, latest 10-20 01:24Z, 114 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 0 of 0 graded reads since 10-19 18:00Z; 35 of 42 new reads stamped (Pinnacle at the pick)
- contextAtPick on 0 of 0 graded reads since 10-19 18:00Z; 42 of 42 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 0 of 0 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 128 of 128 graded NBA/NHL/NCAAF reads (schedules in stats/; NFL is a gap)
- sharpDivergence on 13 of 204 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 0 of 0 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
- travelMilesAway on 128 of 128 graded NBA/NHL/NCAAF reads (schedules + team_venues.json; neutral sites skipped)
Interaction coverage: 0 graded reads have at least two of (sharpDivergenceAtPick, steamBeforePick, daysRest, contextAtPick) populated.
