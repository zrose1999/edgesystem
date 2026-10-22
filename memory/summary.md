# What EDGE is learning (2026-10-22 03:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
295 graded reads counted, 596 logged. CLV is mean clvProb. Patterns move only by grade.py.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 15, CLV +0.2%, t +0.3, last 30d +0.2% on 15; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 13, CLV +0.1%, t +0.2, last 30d +0.1% on 13; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 153, CLV -2.0%, t -6.8, last 30d -2.0% on 153
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 12, CLV +0.1%, t +0.2 (best of 47 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 17, CLV +0.5% (best of 14)
- ALL market=total: n 153, CLV -2.1%, t -8.4, last 30d -2.1% on 153
  > no conditional pocket found in current features (37 combos tested inside market=total) | pair: none (14 pair combos tested)
- ALL timing=early: n 149, CLV -2.0%, t -6.1, last 30d -2.0% on 149
  > pocket: travelEdge=even inside timing=early: n 11, CLV +0.9%, t +0.7 (best of 43 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 18, CLV +1.2% (best of 15)
Observation: edge size is not yet predicting CLV (A -1.8% on 41, B -1.4% on 100, C -2.0% on 154).
  > last 50 graded reads: A +1.3% on 6, B -1.2% on 25, C -2.1% on 19 (A > B > C holds; diagnostic only)
  > pocket: tzShift=none inside grade A: n 9, CLV +1.8%, t +0.9 (best of 21 tested; a lead to watch)
  > order holds inside tzShift=none: A +1.8% on 9, B -0.4% on 10, C -1.7% on 39 (8 of 30 features tested)
Why reads lost to the close (autopsy, post-pick; 219 of 295, cause known on 195): news-after-pick 12 (-4.9%), sharps-against-at-pick 1 (-0.9%), sharps-against-at-open 1 (-3.1%), late-move 2 (-2.2%), number-off 179 (-3.2%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 32, right-but-unlucky 26, lucky-win 86, market-was-right 102; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1307 price snapshots stored in the last 26h, latest 10-22 02:54Z, 333 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 36 of 39 graded reads since 10-19 18:00Z; 252 of 296 new reads stamped (Pinnacle at the pick)
- contextAtPick on 39 of 39 graded reads since 10-19 18:00Z; 296 of 296 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 13 of 39 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 278 of 279 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 19 of 295 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 13 of 39 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
- travelMilesAway on 208 of 209 graded NBA/NHL/NCAAF reads (schedules + team_venues.json; neutral sites skipped)
Interaction coverage: 31 graded reads have at least two of (sharpDivergenceAtPick, steamBeforePick, daysRest, contextAtPick) populated.
