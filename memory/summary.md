# What EDGE is learning (2026-10-27 04:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
719 graded reads counted, 1498 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-26 17:17Z): 40 strategies tracking from 7736 hypotheses (0 new this run); 77 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 38, CLV +1.2%, t +1.3, last 30d +1.2% on 38; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 35, CLV +0.9%, t +1.8, last 30d +0.9% on 35; grade.py needs 13 more graded full-bar picks (has 2), t >= 2.5
- NHL pattern=learned-nhl-ml: n 27, CLV +0.0%, t +0.1, last 30d +0.0% on 27; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 400, CLV -1.4%, t -6.2, last 30d -1.4% on 400
  > pocket: pattern=rest-spot inside edgeBar=<0.5x: n 8, CLV +1.6%, t +0.8 (best of 69 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 53, CLV +0.8% (best of 24)
- ALL moveBeforePick=none: n 372, CLV -1.3%, t -4.8, last 30d -1.3% on 372
  > pocket: injury=qb inside moveBeforePick=none: n 9, CLV +4.0%, t +1.9 (best of 67 tested; a lead to watch) | pair: role=dog + rest=yes n 14, CLV +2.2% (best of 19)
- ALL timing=early: n 331, CLV -1.5%, t -5.2, last 30d -1.5% on 331
  > pocket: travelEdge=even inside timing=early: n 22, CLV +1.6%, t +1.4 (best of 55 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 37, CLV +1.6% (best of 19)
Observation: edge size is not yet predicting CLV (A -1.3% on 79, B -0.8% on 214, C -1.4% on 426).
  > last 50 graded reads: A +3.5% on 4, B -0.9% on 4, C -1.6% on 42 (A > B > C holds; diagnostic only)
  > pocket: restEdge=more inside grade A: n 10, CLV +1.5%, t +1.0 (best of 41 tested; a lead to watch)
  > order holds inside restDays=1day: A +1.1% on 16, B -1.0% on 43, C -1.1% on 111 (7 of 43 features tested)
Why reads lost to the close (autopsy, post-pick; 483 of 719, cause known on 459): news-after-pick 40 (-4.8%), sharps-against-at-pick 8 (-3.4%), sharps-against-at-open 1 (-3.1%), bet-into-steam 10 (-2.2%), late-move 17 (-4.4%), number-off 383 (-3.4%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 125, right-but-unlucky 92, lucky-win 211, market-was-right 248, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, goalie-outlier (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 791 price snapshots stored in the last 26h, latest 10-27 04:54Z, 813 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 234 of 327 graded reads since 10-19 18:00Z; 631 of 897 new reads stamped (Pinnacle at the pick)
- contextAtPick on 327 of 327 graded reads since 10-19 18:00Z; 897 of 897 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 131 of 327 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 682 of 690 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 65 of 719 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 96 of 327 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
