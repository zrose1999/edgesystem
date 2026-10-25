# What EDGE is learning (2026-10-25 21:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
625 graded reads counted, 1281 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-25 14:57Z): 40 strategies tracking from 7736 hypotheses (0 new this run); 52 graded scan reads, mean CLV -0.3%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 38, CLV +1.2%, t +1.3, last 30d +1.2% on 38; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 31, CLV +0.9%, t +1.6, last 30d +0.9% on 31; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
- ALL pattern=sharp-soft-alt: n 14, CLV +2.4%, t +2.2, last 30d +2.4% on 14; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 344, CLV -1.4%, t -5.5, last 30d -1.4% on 344
  > pocket: keyNumber=yes inside edgeBar=<0.5x: n 31, CLV +1.0%, t +0.9 (best of 60 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 41, CLV +0.7% (best of 21)
- ALL moveBeforePick=none: n 316, CLV -1.2%, t -4.2, last 30d -1.2% on 316
  > pocket: injury=qb inside moveBeforePick=none: n 8, CLV +4.0%, t +1.7 (best of 61 tested; a lead to watch) | pair: venue=away + role=dog n 39, CLV +1.6% (best of 15)
- ALL timing=early: n 307, CLV -1.3%, t -4.7, last 30d -1.3% on 307
  > pocket: travelEdge=even inside timing=early: n 22, CLV +1.6%, t +1.4 (best of 54 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 36, CLV +1.9% (best of 19)
Observation: edge size is not yet predicting CLV (A -1.6% on 70, B -0.7% on 195, C -1.3% on 360).
  > last 50 graded reads: A -0.4% on 1, B +0.9% on 9, C +0.4% on 40 (order still wrong; diagnostic only)
  > pocket: travelEdge=more inside grade A: n 10, CLV +1.3%, t +0.6 (best of 35 tested; a lead to watch)
  > order holds inside restDays=1day: A +0.3% on 12, B -0.9% on 36, C -1.5% on 74 (4 of 41 features tested)
Why reads lost to the close (autopsy, post-pick; 424 of 625, cause known on 400): news-after-pick 34 (-4.8%), sharps-against-at-pick 7 (-3.5%), sharps-against-at-open 1 (-3.1%), bet-into-steam 8 (-2.3%), late-move 10 (-4.3%), number-off 340 (-3.3%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 102, right-but-unlucky 85, lucky-win 176, market-was-right 220; right-but-unlucky losses hurt most by close-margin, flipped-late, goalie-outlier (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1546 price snapshots stored in the last 26h, latest 10-25 21:24Z, 690 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 173 of 249 graded reads since 10-19 18:00Z; 543 of 777 new reads stamped (Pinnacle at the pick)
- contextAtPick on 249 of 249 graded reads since 10-19 18:00Z; 777 of 777 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 92 of 249 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 592 of 600 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 34 of 625 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 77 of 249 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
