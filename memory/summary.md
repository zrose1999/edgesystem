# What EDGE is learning (2026-11-18 01:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1374 graded reads counted, 3132 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-17 19:44Z): 34 strategies tracking from 5096 hypotheses (10 new this run); 143 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=soft-dog: n 138, CLV +0.4%, t +1.6, last 30d +0.4% on 138; grade.py needs 0 more graded full-bar picks (has 19), t >= 2.5
- NCAAF pattern=sharp-soft-alt: n 71, CLV +0.8%, t +1.6, last 30d +0.7% on 68; grade.py needs 8 more graded full-bar picks (has 7), t >= 2.5
- NCAAF pattern=soft-dog: n 60, CLV +0.3%, t +0.8, last 30d +0.3% on 60; grade.py needs 0 more graded full-bar picks (has 19), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 678, CLV -1.1%, t -6.4, last 30d -0.9% on 555
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 10, CLV +2.7%, t +1.2 (best of 88 tested; a lead to watch) | pair: venue=home + role=dog n 100, CLV +0.8% (best of 33)
- ALL moveBeforePick=none: n 617, CLV -1.2%, t -5.6, last 30d -1.0% on 528
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 10, CLV +2.7%, t +1.2 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 604, CLV -0.7%, t -3.8, last 30d -0.5% on 541
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 93 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 67, CLV +0.9% (best of 26)
Observation: edge size is not yet predicting CLV (A -0.2% on 128, B -0.1% on 552, C -1.2% on 694).
  > last 50 graded reads: A -1.1% on 8, B -0.3% on 37, C -0.9% on 5 (order still wrong; diagnostic only)
  > pocket: sharpGapPick=<1% inside grade A: n 30, CLV +3.5%, t +4.4 (best of 59 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +3.5% on 30, B +0.3% on 151, C -1.4% on 83 (25 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 816 of 1374, cause known on 816): overpaid 309 (-1.6%), news-after-pick 59 (-6.2%), sharps-against-at-pick 7 (-4.6%), sharps-against-at-open 2 (-2.1%), bet-into-steam 4 (-3.1%), late-move 28 (-3.6%), sharp-move-against 89 (-2.1%), soft-move-against 2 (-3.2%), model-wrong 316 (-5.1%)
Process vs result: right-and-rewarded 284, right-but-unlucky 260, lucky-win 383, market-was-right 426, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 678, CLV -1.6%, t -9.0 (positive = the gate blocks winners); best pocket pattern=scan-nba-h2h-away-restedgeawaymore-b31fe9 n 11, CLV +1.8%, t +0.7 (of 89 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 344 price snapshots stored in the last 26h, latest 11-18 01:54Z, 2411 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 711 of 982 graded reads since 10-19 18:00Z; 2109 of 2437 new reads stamped (Pinnacle at the pick)
- contextAtPick on 982 of 982 graded reads since 10-19 18:00Z; 2437 of 2437 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 471 of 982 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1256 of 1272 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 139 of 1374 graded reads since 10-14 00:00Z (Pinnacle at the open)
