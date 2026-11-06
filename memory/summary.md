# What EDGE is learning (2026-11-06 21:40Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1137 graded reads counted, 2316 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-06 17:53Z): 23 strategies tracking from 4832 hypotheses (0 new this run); 127 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 56, CLV +0.6%, t +0.7, last 30d +0.6% on 56; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
- NCAAF pattern=sharp-soft-alt: n 27, CLV +0.7%, t +1.2, last 30d +0.7% on 27; grade.py needs 12 more graded full-bar picks (has 3), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 621, CLV -1.2%, t -6.4, last 30d -1.2% on 621
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 83 tested; a lead to watch) | pair: venue=home + role=dog n 76, CLV +0.8% (best of 30)
- ALL moveBeforePick=none: n 576, CLV -1.2%, t -5.6, last 30d -1.2% on 576
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 79 tested; a lead to watch) | pair: venue=home + role=dog n 49, CLV +1.6% (best of 21)
- ALL timing=day: n 515, CLV -0.8%, t -4.1, last 30d -0.8% on 515
  > pocket: sharpDiv=pin-for inside timing=day: n 12, CLV +2.9%, t +1.7 (best of 88 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 59, CLV +0.4% (best of 25)
Observation: edge size is not yet predicting CLV (A -0.5% on 104, B -0.2% on 373, C -1.2% on 660).
  > last 50 graded reads: A +1.8% on 4, B +0.7% on 36, C -0.4% on 10 (A > B > C holds; diagnostic only)
  > pocket: sharpGapOpen=<1% inside grade A: n 8, CLV +3.7%, t +2.4 (best of 50 tested; a lead to watch)
  > order holds inside sharpGapOpen=<1%: A +3.7% on 8, B +1.2% on 30, C -0.5% on 38 (20 of 53 features tested)
Why reads lost to the close (autopsy, post-pick; 710 of 1137, cause known on 710): overpaid 306 (-1.6%), news-after-pick 43 (-6.5%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 21 (-4.0%), sharp-move-against 55 (-2.0%), soft-move-against 2 (-3.2%), model-wrong 272 (-5.3%)
Process vs result: right-and-rewarded 227, right-but-unlucky 187, lucky-win 326, market-was-right 377, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 114, CLV -1.0%, t -2.3 (positive = the gate blocks winners); best pocket tzShift=east n 16, CLV +2.2%, t +1.3 (of 50 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 896 price snapshots stored in the last 26h, latest 11-06 21:39Z, 1877 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 479 of 745 graded reads since 10-19 18:00Z; 1320 of 1643 new reads stamped (Pinnacle at the pick)
- contextAtPick on 745 of 745 graded reads since 10-19 18:00Z; 1643 of 1643 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 301 of 745 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1032 of 1047 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 109 of 1137 graded reads since 10-14 00:00Z (Pinnacle at the open)
