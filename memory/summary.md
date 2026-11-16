# What EDGE is learning (2026-11-16 15:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1370 graded reads counted, 3096 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-16 11:10Z): 25 strategies tracking from 5094 hypotheses (0 new this run); 142 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=soft-dog: n 136, CLV +0.5%, t +1.8, last 30d +0.5% on 136; grade.py needs 0 more graded full-bar picks (has 19), t >= 2.5
- NCAAF pattern=sharp-soft-alt: n 71, CLV +0.8%, t +1.6, last 30d +0.8% on 71; grade.py needs 8 more graded full-bar picks (has 7), t >= 2.5
- NCAAF pattern=soft-dog: n 60, CLV +0.3%, t +0.8, last 30d +0.3% on 60; grade.py needs 0 more graded full-bar picks (has 19), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 677, CLV -1.1%, t -6.4, last 30d -1.1% on 663
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 10, CLV +2.7%, t +1.2 (best of 86 tested; a lead to watch) | pair: venue=home + role=dog n 99, CLV +0.8% (best of 33)
- ALL moveBeforePick=none: n 617, CLV -1.2%, t -5.6, last 30d -1.2% on 613
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 10, CLV +2.7%, t +1.2 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 602, CLV -0.7%, t -3.7, last 30d -0.6% on 586
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 93 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 67, CLV +0.9% (best of 26)
Observation: edge size is not yet predicting CLV (A -0.2% on 128, B -0.1% on 549, C -1.2% on 693).
  > last 50 graded reads: A -1.1% on 8, B -0.1% on 38, C -0.8% on 4 (order still wrong; diagnostic only)
  > pocket: sharpGapPick=<1% inside grade A: n 30, CLV +3.5%, t +4.4 (best of 59 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +3.5% on 30, B +0.3% on 150, C -1.4% on 82 (25 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 813 of 1370, cause known on 813): overpaid 309 (-1.6%), news-after-pick 56 (-6.0%), sharps-against-at-pick 7 (-4.6%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 29 (-3.6%), sharp-move-against 86 (-2.1%), soft-move-against 2 (-3.2%), model-wrong 319 (-5.1%)
Process vs result: right-and-rewarded 284, right-but-unlucky 259, lucky-win 381, market-was-right 425, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 646, CLV -1.7%, t -8.8 (positive = the gate blocks winners); best pocket pattern=scan-nba-spread-away-restedgeawaymore-1e501d n 17, CLV +2.0%, t +1.0 (of 87 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 590 price snapshots stored in the last 26h, latest 11-16 11:09Z, 2369 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 707 of 978 graded reads since 10-19 18:00Z; 2011 of 2339 new reads stamped (Pinnacle at the pick)
- contextAtPick on 978 of 978 graded reads since 10-19 18:00Z; 2339 of 2339 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 469 of 978 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1252 of 1268 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 137 of 1370 graded reads since 10-14 00:00Z (Pinnacle at the open)
