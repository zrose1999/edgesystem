# What EDGE is learning (2026-10-22 22:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
312 graded reads counted, 655 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-22 15:53Z): 40 strategies tracking from 7678 hypotheses (40 new this run); 0 graded scan reads. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=sharp-soft: n 15, CLV +0.5%, t +1.0, last 30d +0.5% on 15; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
- NHL pattern=learned-nhl-ml: n 15, CLV +0.2%, t +0.3, last 30d +0.2% on 15; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
Early negative, still collecting (largest samples):
- ALL market=total: n 161, CLV -2.2%, t -8.5, last 30d -2.2% on 161
  > no conditional pocket found in current features (37 combos tested inside market=total) | pair: none (14 pair combos tested)
- ALL edgeBar=<0.5x: n 159, CLV -2.0%, t -7.0, last 30d -2.0% on 159
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 12, CLV +0.1%, t +0.2 (best of 47 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 18, CLV +0.2% (best of 14)
- ALL timing=early: n 155, CLV -2.0%, t -6.1, last 30d -2.0% on 155
  > pocket: travelEdge=even inside timing=early: n 11, CLV +0.9%, t +0.7 (best of 45 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 19, CLV +0.9% (best of 15)
Observation: edge size is not yet predicting CLV (A -1.8% on 46, B -1.3% on 106, C -2.0% on 160).
  > last 50 graded reads: A +0.8% on 8, B -1.4% on 22, C -2.4% on 20 (A > B > C holds; diagnostic only)
  > pocket: tzShift=none inside grade A: n 9, CLV +1.8%, t +0.9 (best of 26 tested; a lead to watch)
  > order holds inside tzShift=none: A +1.8% on 9, B +0.1% on 12, C -1.8% on 41 (8 of 30 features tested)
Why reads lost to the close (autopsy, post-pick; 227 of 312, cause known on 203): news-after-pick 14 (-4.4%), sharps-against-at-pick 1 (-0.9%), sharps-against-at-open 1 (-3.1%), late-move 2 (-2.2%), number-off 185 (-3.3%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 48, right-but-unlucky 37, lucky-win 102, market-was-right 125; right-but-unlucky losses hurt most by flipped-late, close-margin, overtime (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1831 price snapshots stored in the last 26h, latest 10-22 22:54Z, 505 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 49 of 52 graded reads since 10-19 18:00Z; 356 of 411 new reads stamped (Pinnacle at the pick)
- contextAtPick on 52 of 52 graded reads since 10-19 18:00Z; 411 of 411 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 18 of 52 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 288 of 295 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 20 of 312 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 16 of 52 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
- travelMilesAway on 218 of 225 graded NBA/NHL/NCAAF reads (schedules + team_venues.json; neutral sites skipped)
