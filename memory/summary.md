# What EDGE is learning (2026-10-28 03:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
766 graded reads counted, 1563 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-27 16:27Z): 40 strategies tracking from 7762 hypotheses (0 new this run); 86 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 38, CLV +1.2%, t +1.3, last 30d +1.2% on 38; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 29, CLV +0.2%, t +0.5, last 30d +0.2% on 29; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
- ALL pattern=sharp-soft-alt: n 15, CLV +2.1%, t +2.1, last 30d +2.1% on 15; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 433, CLV -1.4%, t -6.5, last 30d -1.4% on 433
  > pocket: travelEdge=more inside edgeBar=<0.5x: n 63, CLV +0.9%, t +1.2 (best of 73 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 61, CLV +0.4% (best of 26)
- ALL moveBeforePick=none: n 398, CLV -1.3%, t -5.0, last 30d -1.3% on 398
  > pocket: injury=qb inside moveBeforePick=none: n 9, CLV +4.0%, t +1.9 (best of 70 tested; a lead to watch) | pair: venue=home + role=dog n 27, CLV +1.5% (best of 19)
- ALL timing=day: n 359, CLV -0.9%, t -4.0, last 30d -0.9% on 359
  > pocket: sharpDiv=pin-for inside timing=day: n 11, CLV +3.5%, t +1.9 (best of 75 tested; a lead to watch) | pair: role=dog + rest=yes n 25, CLV +0.3% (best of 20)
Observation: edge size is not yet predicting CLV (A -1.2% on 81, B -0.7% on 220, C -1.3% on 465).
  > last 50 graded reads: A +1.3% on 4, B +2.1% on 6, C -2.0% on 40 (order still wrong; diagnostic only)
  > pocket: restEdge=more inside grade A: n 10, CLV +1.5%, t +1.0 (best of 42 tested; a lead to watch)
  > order holds inside restDays=1day: A +1.1% on 16, B -1.0% on 46, C -1.3% on 131 (6 of 43 features tested)
Why reads lost to the close (autopsy, post-pick; 516 of 766, cause known on 492): news-after-pick 38 (-4.7%), sharps-against-at-pick 9 (-3.8%), sharps-against-at-open 1 (-3.1%), bet-into-steam 10 (-2.2%), late-move 19 (-4.2%), number-off 415 (-3.3%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 139, right-but-unlucky 99, lucky-win 227, market-was-right 267, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1000 price snapshots stored in the last 26h, latest 10-28 03:24Z, 905 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 258 of 374 graded reads since 10-19 18:00Z; 666 of 989 new reads stamped (Pinnacle at the pick)
- contextAtPick on 374 of 374 graded reads since 10-19 18:00Z; 989 of 989 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 149 of 374 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 719 of 727 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 76 of 766 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 113 of 374 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
