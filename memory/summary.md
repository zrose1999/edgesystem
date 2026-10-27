# What EDGE is learning (2026-10-27 01:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
674 graded reads counted, 1426 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-26 17:17Z): 40 strategies tracking from 7736 hypotheses (0 new this run); 59 graded scan reads, mean CLV -0.3%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 38, CLV +1.2%, t +1.3, last 30d +1.2% on 38; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 33, CLV +0.9%, t +1.5, last 30d +0.9% on 33; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
- ALL pattern=sharp-soft-alt: n 14, CLV +2.4%, t +2.2, last 30d +2.4% on 14; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 375, CLV -1.4%, t -5.8, last 30d -1.4% on 375
  > pocket: pattern=learned-nba-total inside edgeBar=<0.5x: n 8, CLV +1.2%, t +1.0 (best of 64 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 46, CLV +0.7% (best of 22)
- ALL moveBeforePick=none: n 345, CLV -1.2%, t -4.4, last 30d -1.2% on 345
  > pocket: injury=qb inside moveBeforePick=none: n 9, CLV +4.0%, t +1.9 (best of 62 tested; a lead to watch) | pair: role=dog + rest=yes n 8, CLV +2.6% (best of 17)
- ALL timing=early: n 326, CLV -1.4%, t -5.1, last 30d -1.4% on 326
  > pocket: travelEdge=even inside timing=early: n 22, CLV +1.6%, t +1.4 (best of 55 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 37, CLV +1.6% (best of 19)
Observation: edge size is not yet predicting CLV (A -1.5% on 73, B -0.7% on 207, C -1.4% on 394).
  > last 50 graded reads: A -0.4% on 1, B -1.0% on 10, C -1.1% on 39 (A > B > C holds; diagnostic only)
  > pocket: restEdge=more inside grade A: n 9, CLV +1.5%, t +0.9 (best of 35 tested; a lead to watch)
  > order holds inside restDays=1day: A +0.3% on 12, B -1.0% on 39, C -1.3% on 90 (5 of 41 features tested)
Why reads lost to the close (autopsy, post-pick; 458 of 674, cause known on 434): news-after-pick 36 (-4.7%), sharps-against-at-pick 8 (-3.4%), sharps-against-at-open 1 (-3.1%), bet-into-steam 9 (-2.1%), late-move 15 (-4.3%), number-off 365 (-3.3%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 124, right-but-unlucky 91, lucky-win 209, market-was-right 247, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, goalie-outlier (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 828 price snapshots stored in the last 26h, latest 10-27 01:24Z, 811 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 200 of 287 graded reads since 10-19 18:00Z; 629 of 887 new reads stamped (Pinnacle at the pick)
- contextAtPick on 287 of 287 graded reads since 10-19 18:00Z; 887 of 887 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 107 of 287 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 637 of 645 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 41 of 674 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 86 of 287 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
