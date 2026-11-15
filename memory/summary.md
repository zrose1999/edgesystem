# What EDGE is learning (2026-11-15 23:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1364 graded reads counted, 3072 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-15 17:39Z): 25 strategies tracking from 5066 hypotheses (0 new this run); 142 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=soft-dog: n 134, CLV +0.5%, t +1.8, last 30d +0.5% on 134; grade.py needs 0 more graded full-bar picks (has 19), t >= 2.5
- NCAAF pattern=sharp-soft-alt: n 71, CLV +0.8%, t +1.6, last 30d +0.8% on 71; grade.py needs 9 more graded full-bar picks (has 6), t >= 2.5
- NCAAF pattern=soft-dog: n 60, CLV +0.3%, t +0.8, last 30d +0.3% on 60; grade.py needs 0 more graded full-bar picks (has 19), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 676, CLV -1.1%, t -6.4, last 30d -1.1% on 671
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 10, CLV +2.7%, t +1.2 (best of 86 tested; a lead to watch) | pair: venue=home + role=dog n 98, CLV +0.8% (best of 33)
- ALL moveBeforePick=none: n 615, CLV -1.2%, t -5.6, last 30d -1.2% on 613
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 10, CLV +2.7%, t +1.2 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 600, CLV -0.7%, t -3.8, last 30d -0.7% on 594
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 93 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 67, CLV +0.9% (best of 26)
Observation: edge size is not yet predicting CLV (A -0.2% on 126, B -0.1% on 546, C -1.2% on 692).
  > last 50 graded reads: A -0.8% on 6, B +0.2% on 39, C -1.9% on 5 (order still wrong; diagnostic only)
  > pocket: sharpGapPick=<1% inside grade A: n 30, CLV +3.5%, t +4.4 (best of 59 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +3.5% on 30, B +0.3% on 149, C -1.4% on 82 (26 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 808 of 1364, cause known on 808): overpaid 309 (-1.6%), news-after-pick 54 (-6.3%), sharps-against-at-pick 7 (-4.6%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 28 (-3.6%), sharp-move-against 85 (-2.1%), soft-move-against 2 (-3.2%), model-wrong 318 (-5.1%)
Process vs result: right-and-rewarded 282, right-but-unlucky 257, lucky-win 380, market-was-right 418, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 629, CLV -1.7%, t -8.9 (positive = the gate blocks winners); best pocket pattern=scan-nba-spread-away-restedgeawaymore-1e501d n 17, CLV +2.0%, t +1.0 (of 86 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 990 price snapshots stored in the last 26h, latest 11-15 23:54Z, 2346 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 701 of 972 graded reads since 10-19 18:00Z; 1875 of 2203 new reads stamped (Pinnacle at the pick)
- contextAtPick on 972 of 972 graded reads since 10-19 18:00Z; 2203 of 2203 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 466 of 972 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1246 of 1262 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 133 of 1364 graded reads since 10-14 00:00Z (Pinnacle at the open)
