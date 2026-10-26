# What EDGE is learning (2026-10-26 01:39Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
670 graded reads counted, 1402 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-25 14:57Z): 40 strategies tracking from 7736 hypotheses (0 new this run); 59 graded scan reads, mean CLV -0.3%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 38, CLV +1.2%, t +1.3, last 30d +1.2% on 38; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 33, CLV +0.9%, t +1.5, last 30d +0.9% on 33; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
- ALL pattern=sharp-soft-alt: n 14, CLV +2.4%, t +2.2, last 30d +2.4% on 14; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 372, CLV -1.4%, t -5.8, last 30d -1.4% on 372
  > pocket: pattern=learned-nba-total inside edgeBar=<0.5x: n 8, CLV +1.2%, t +1.0 (best of 64 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 46, CLV +0.7% (best of 22)
- ALL moveBeforePick=none: n 343, CLV -1.2%, t -4.4, last 30d -1.2% on 343
  > pocket: injury=qb inside moveBeforePick=none: n 9, CLV +4.0%, t +1.9 (best of 62 tested; a lead to watch) | pair: role=dog + rest=yes n 8, CLV +2.6% (best of 17)
- ALL timing=early: n 326, CLV -1.4%, t -5.1, last 30d -1.4% on 326
  > pocket: travelEdge=even inside timing=early: n 22, CLV +1.6%, t +1.4 (best of 55 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 37, CLV +1.6% (best of 19)
Observation: edge size is not yet predicting CLV (A -1.5% on 73, B -0.7% on 206, C -1.4% on 391).
  > last 50 graded reads: A -0.4% on 1, B -0.6% on 9, C -0.9% on 40 (A > B > C holds; diagnostic only)
  > pocket: restEdge=more inside grade A: n 9, CLV +1.5%, t +0.9 (best of 35 tested; a lead to watch)
  > order holds inside restDays=1day: A +0.3% on 12, B -0.9% on 38, C -1.3% on 89 (5 of 41 features tested)
Why reads lost to the close (autopsy, post-pick; 456 of 670, cause known on 432): news-after-pick 35 (-4.8%), sharps-against-at-pick 8 (-3.4%), sharps-against-at-open 1 (-3.1%), bet-into-steam 9 (-2.1%), late-move 15 (-4.3%), number-off 364 (-3.3%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 117, right-but-unlucky 90, lucky-win 204, market-was-right 239, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1274 price snapshots stored in the last 26h, latest 10-26 01:24Z, 708 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 197 of 283 graded reads since 10-19 18:00Z; 561 of 799 new reads stamped (Pinnacle at the pick)
- contextAtPick on 283 of 283 graded reads since 10-19 18:00Z; 799 of 799 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 106 of 283 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 634 of 642 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 39 of 670 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 85 of 283 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
