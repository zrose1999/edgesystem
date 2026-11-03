# What EDGE is learning (2026-11-03 14:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1088 graded reads counted, 2209 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-03 11:17Z): 40 strategies tracking from 10288 hypotheses (5 new this run); 125 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 55, CLV +0.7%, t +0.8, last 30d +0.7% on 55; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
- NCAAF pattern=sharp-soft-alt: n 25, CLV +0.6%, t +1.0, last 30d +0.6% on 25; grade.py needs 12 more graded full-bar picks (has 3), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 607, CLV -1.2%, t -6.4, last 30d -1.2% on 607
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 83 tested; a lead to watch) | pair: venue=home + role=dog n 71, CLV +0.8% (best of 29)
- ALL moveBeforePick=none: n 566, CLV -1.2%, t -5.5, last 30d -1.2% on 566
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 79 tested; a lead to watch) | pair: venue=home + role=dog n 48, CLV +1.6% (best of 21)
- ALL timing=day: n 498, CLV -0.9%, t -4.4, last 30d -0.9% on 498
  > pocket: sharpDiv=pin-for inside timing=day: n 11, CLV +3.5%, t +1.9 (best of 88 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 58, CLV +0.4% (best of 25)
Observation: edge size is not yet predicting CLV (A -0.6% on 99, B -0.4% on 340, C -1.2% on 649).
  > last 50 graded reads: A +1.1% on 5, B +0.9% on 25, C -0.5% on 20 (A > B > C holds; diagnostic only)
  > pocket: sharpGapOpen=<1% inside grade A: n 8, CLV +3.7%, t +2.4 (best of 49 tested; a lead to watch)
  > order holds inside sharpDiv=aligned: A +3.7% on 8, B +0.9% on 29, C -0.5% on 38 (20 of 53 features tested)
Why reads lost to the close (autopsy, post-pick; 690 of 1088, cause known on 690): overpaid 300 (-1.6%), news-after-pick 41 (-6.8%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 20 (-4.1%), sharp-move-against 49 (-1.9%), soft-move-against 2 (-3.2%), model-wrong 267 (-5.4%)
Process vs result: right-and-rewarded 218, right-but-unlucky 170, lucky-win 318, market-was-right 369, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 84, CLV -0.4%, t -0.8 (positive = the gate blocks winners); best pocket tzShift=east n 13, CLV +2.7%, t +1.3 (of 46 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1181 price snapshots stored in the last 26h, latest 11-03 14:54Z, 1596 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 430 of 696 graded reads since 10-19 18:00Z; 1166 of 1489 new reads stamped (Pinnacle at the pick)
- contextAtPick on 696 of 696 graded reads since 10-19 18:00Z; 1489 of 1489 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 264 of 696 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 999 of 1013 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 107 of 1088 graded reads since 10-14 00:00Z (Pinnacle at the open)
