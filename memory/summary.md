# What EDGE is learning (2026-11-15 02:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1339 graded reads counted, 3018 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-14 16:57Z): 25 strategies tracking from 5032 hypotheses (0 new this run); 140 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=soft-dog: n 120, CLV +0.5%, t +1.8, last 30d +0.5% on 120; grade.py needs 0 more graded full-bar picks (has 17), t >= 2.5
- NCAAF pattern=sharp-soft-alt: n 68, CLV +0.9%, t +1.6, last 30d +0.9% on 68; grade.py needs 9 more graded full-bar picks (has 6), t >= 2.5
- NCAAF pattern=learned-ncaaf-spread: n 58, CLV +0.3%, t +0.4, last 30d +0.4% on 57; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 670, CLV -1.1%, t -6.3, last 30d -1.1% on 665
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 10, CLV +2.7%, t +1.2 (best of 85 tested; a lead to watch) | pair: venue=home + role=dog n 95, CLV +0.8% (best of 33)
- ALL moveBeforePick=none: n 610, CLV -1.2%, t -5.5, last 30d -1.2% on 608
  > pocket: sharpGapPick=2%+ inside moveBeforePick=none: n 9, CLV +2.8%, t +2.1 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 592, CLV -0.7%, t -3.8, last 30d -0.7% on 586
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 93 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 67, CLV +0.9% (best of 26)
Observation: edge size is not yet predicting CLV (A -0.2% on 124, B -0.1% on 525, C -1.2% on 690).
  > last 50 graded reads: A -0.8% on 6, B +0.4% on 34, C -0.5% on 10 (order still wrong; diagnostic only)
  > pocket: sharpDivPick=aligned inside grade A: n 30, CLV +3.5%, t +4.4 (best of 59 tested; a lead to watch)
  > order holds inside sharpDivPick=aligned: A +3.5% on 30, B +0.3% on 142, C -1.4% on 82 (25 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 792 of 1339, cause known on 792): overpaid 307 (-1.6%), news-after-pick 50 (-6.5%), sharps-against-at-pick 7 (-4.6%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 25 (-3.7%), sharp-move-against 78 (-2.1%), soft-move-against 2 (-3.2%), model-wrong 318 (-5.2%)
Process vs result: right-and-rewarded 274, right-but-unlucky 247, lucky-win 366, market-was-right 411, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 604, CLV -1.7%, t -8.5 (positive = the gate blocks winners); best pocket pattern=scan-nba-spread-away-restedgeawaymore-1e501d n 16, CLV +2.2%, t +1.0 (of 85 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1444 price snapshots stored in the last 26h, latest 11-15 02:54Z, 2310 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 676 of 947 graded reads since 10-19 18:00Z; 1841 of 2169 new reads stamped (Pinnacle at the pick)
- contextAtPick on 947 of 947 graded reads since 10-19 18:00Z; 2169 of 2169 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 450 of 947 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1221 of 1237 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 131 of 1339 graded reads since 10-14 00:00Z (Pinnacle at the open)
