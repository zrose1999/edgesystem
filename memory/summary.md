# What EDGE is learning (2026-10-28 00:43Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
733 graded reads counted, 1526 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-27 16:27Z): 40 strategies tracking from 7762 hypotheses (0 new this run); 77 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 38, CLV +1.2%, t +1.3, last 30d +1.2% on 38; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 27, CLV +0.0%, t +0.1, last 30d +0.0% on 27; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
- ALL pattern=sharp-soft-alt: n 15, CLV +2.1%, t +2.1, last 30d +2.1% on 15; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 409, CLV -1.4%, t -6.1, last 30d -1.4% on 409
  > pocket: pattern=rest-spot inside edgeBar=<0.5x: n 8, CLV +1.6%, t +0.8 (best of 71 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 55, CLV +0.9% (best of 25)
- ALL moveBeforePick=none: n 375, CLV -1.2%, t -4.5, last 30d -1.2% on 375
  > pocket: injury=qb inside moveBeforePick=none: n 9, CLV +4.0%, t +1.9 (best of 67 tested; a lead to watch) | pair: role=dog + rest=yes n 14, CLV +2.2% (best of 19)
- ALL timing=early: n 334, CLV -1.4%, t -4.8, last 30d -1.4% on 334
  > pocket: travelEdge=even inside timing=early: n 25, CLV +2.6%, t +2.3 (best of 55 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 39, CLV +2.1% (best of 19)
Observation: edge size is not yet predicting CLV (A -1.2% on 80, B -0.7% on 217, C -1.3% on 436).
  > last 50 graded reads: A +4.1% on 4, B +2.6% on 6, C -1.6% on 40 (A > B > C holds; diagnostic only)
  > pocket: sharpDivPick=aligned inside grade A: n 9, CLV +1.5%, t +0.9 (best of 41 tested; a lead to watch)
  > order holds inside restDays=1day: A +1.1% on 16, B -1.0% on 43, C -1.1% on 113 (4 of 43 features tested)
Why reads lost to the close (autopsy, post-pick; 491 of 733, cause known on 467): news-after-pick 39 (-4.8%), sharps-against-at-pick 9 (-3.8%), sharps-against-at-open 1 (-3.1%), bet-into-steam 10 (-2.2%), late-move 17 (-4.4%), number-off 391 (-3.3%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 139, right-but-unlucky 99, lucky-win 224, market-was-right 265, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1022 price snapshots stored in the last 26h, latest 10-28 00:43Z, 891 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 245 of 341 graded reads since 10-19 18:00Z; 662 of 985 new reads stamped (Pinnacle at the pick)
- contextAtPick on 341 of 341 graded reads since 10-19 18:00Z; 985 of 985 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 141 of 341 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 687 of 695 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 76 of 733 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 100 of 341 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
