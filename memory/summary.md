# What EDGE is learning (2026-10-21 23:09Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
246 graded reads counted, 506 logged. CLV is mean clvProb. Patterns move only by grade.py.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 14, CLV +0.4%, t +0.6, last 30d +0.4% on 14; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 11, CLV +0.1%, t +0.2, last 30d +0.1% on 11; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 139, CLV -2.0%, t -6.5, last 30d -2.0% on 139
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 11, CLV +0.4%, t +0.5 (best of 43 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 15, CLV +1.2% (best of 11)
- ALL restDays=normal: n 133, CLV -2.4%, t -8.9, last 30d -2.4% on 133
  > pocket: role=dog inside restDays=normal: n 17, CLV +0.4%, t +0.4 (best of 37 tested; a lead to watch) | pair: venue=away + role=dog n 9, CLV +2.2% (best of 20)
- ALL timing=early: n 130, CLV -2.1%, t -6.2, last 30d -2.1% on 130
  > pocket: travelEdge=even inside timing=early: n 10, CLV +0.9%, t +0.6 (best of 40 tested; a lead to watch) | pair: venue=away + role=dog n 18, CLV +1.5% (best of 12)
Observation: edge size is not yet predicting CLV (A -1.9% on 26, B -1.6% on 80, C -2.0% on 140).
  > last 50 graded reads: A -0.3% on 8, B -0.8% on 26, C -3.4% on 16 (A > B > C holds; diagnostic only)
  > no conditional pocket found in current features (13 combos tested inside grade A)
  > order holds inside restDays=2+days: A +1.4% on 5, B -1.2% on 12, C -3.6% on 6 (4 of 18 features tested)
Why reads lost to the close (autopsy, post-pick; 188 of 246, cause known on 164): news-after-pick 7 (-6.0%), sharps-against-at-open 1 (-3.1%), number-off 156 (-3.1%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 32, right-but-unlucky 26, lucky-win 86, market-was-right 102; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1416 price snapshots stored in the last 26h, latest 10-21 23:09Z, 296 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 8 of 9 graded reads since 10-19 18:00Z; 219 of 259 new reads stamped (Pinnacle at the pick)
- contextAtPick on 9 of 9 graded reads since 10-19 18:00Z; 259 of 259 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 5 of 9 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 230 of 230 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 17 of 246 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 5 of 9 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
- travelMilesAway on 160 of 160 graded NBA/NHL/NCAAF reads (schedules + team_venues.json; neutral sites skipped)
Interaction coverage: 6 graded reads have at least two of (sharpDivergenceAtPick, steamBeforePick, daysRest, contextAtPick) populated.
