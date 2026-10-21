# What EDGE is learning (2026-10-21 17:39Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
243 graded reads counted, 503 logged. CLV is mean clvProb. Patterns move only by grade.py.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 14, CLV +0.5%, t +0.9, last 30d +0.5% on 14; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 139, CLV -1.9%, t -6.3, last 30d -1.9% on 139
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 11, CLV +0.7%, t +1.0 (best of 43 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 15, CLV +0.7% (best of 11)
- ALL restDays=normal: n 133, CLV -2.3%, t -9.5, last 30d -2.3% on 133
  > no conditional pocket found in current features (37 combos tested inside restDays=normal) | pair: venue=away + role=dog n 9, CLV +1.1% (best of 20)
- ALL timing=early: n 129, CLV -2.0%, t -6.0, last 30d -2.0% on 129
  > pocket: travelEdge=even inside timing=early: n 10, CLV +0.7%, t +0.5 (best of 40 tested; a lead to watch) | pair: venue=away + role=dog n 18, CLV +1.0% (best of 12)
Observation: grades rank A > B > C (A -1.8% on 25, B -1.8% on 78, C -1.9% on 140).
  > last 50 graded reads: A -0.7% on 9, B -1.0% on 25, C -3.3% on 16 (A > B > C holds; diagnostic only)
  > no conditional pocket found in current features (12 combos tested inside grade A)
  > order holds inside restDays=2+days: A +1.4% on 5, B -1.1% on 12, C -3.7% on 6 (6 of 18 features tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1244 price snapshots stored in the last 26h, latest 10-21 17:39Z, 253 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 6 of 7 graded reads since 10-19 18:00Z; 165 of 205 new reads stamped (Pinnacle at the pick)
- contextAtPick on 7 of 7 graded reads since 10-19 18:00Z; 205 of 205 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 3 of 7 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 230 of 230 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 14 of 243 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 5 of 7 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
- travelMilesAway on 160 of 160 graded NBA/NHL/NCAAF reads (schedules + team_venues.json; neutral sites skipped)
Interaction coverage: 6 graded reads have at least two of (sharpDivergenceAtPick, steamBeforePick, daysRest, contextAtPick) populated.
