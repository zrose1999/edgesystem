# What EDGE is learning (2026-11-19 04:03Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1393 graded reads counted, 3237 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-18 19:21Z): 34 strategies tracking from 5102 hypotheses (0 new this run); 148 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=soft-dog: n 140, CLV +0.4%, t +1.5, last 30d +0.4% on 140; grade.py needs 0 more graded full-bar picks (has 21), t >= 2.0
- ALL pattern=sharp-soft-alt: n 102, CLV +0.8%, t +1.9, last 30d +0.7% on 98; grade.py needs 8 more graded full-bar picks (has 7), t >= 2.5
- NCAAF pattern=sharp-soft-alt: n 72, CLV +0.8%, t +1.6, last 30d +0.7% on 69; grade.py needs 8 more graded full-bar picks (has 7), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 686, CLV -1.1%, t -6.4, last 30d -0.9% on 559
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 10, CLV +2.7%, t +1.2 (best of 88 tested; a lead to watch) | pair: venue=home + role=dog n 101, CLV +0.7% (best of 33)
- ALL moveBeforePick=none: n 622, CLV -1.2%, t -5.5, last 30d -0.9% on 528
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 10, CLV +2.7%, t +1.2 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 25)
- ALL timing=day: n 618, CLV -0.7%, t -3.7, last 30d -0.5% on 548
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 93 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 68, CLV +0.8% (best of 26)
Observation: edge size is not yet predicting CLV (A -0.3% on 132, B -0.1% on 558, C -1.2% on 703).
  > last 50 graded reads: A -3.3% on 9, B -0.6% on 28, C -0.1% on 13 (order still wrong; diagnostic only)
  > pocket: sharpDivPick=aligned inside grade A: n 32, CLV +3.2%, t +4.0 (best of 61 tested; a lead to watch)
  > order holds inside sharpDivPick=aligned: A +3.2% on 32, B +0.3% on 151, C -1.4% on 83 (24 of 57 features tested)
Why reads lost to the close (autopsy, post-pick; 827 of 1393, cause known on 827): overpaid 310 (-1.6%), news-after-pick 61 (-5.8%), sharps-against-at-pick 7 (-4.6%), sharps-against-at-open 2 (-2.1%), bet-into-steam 4 (-3.1%), late-move 28 (-3.5%), sharp-move-against 93 (-2.2%), soft-move-against 3 (-4.2%), model-wrong 319 (-5.1%)
Process vs result: right-and-rewarded 288, right-but-unlucky 260, lucky-win 389, market-was-right 431, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 764, CLV -1.6%, t -9.2 (positive = the gate blocks winners); best pocket pattern=rest-spot n 24, CLV +1.4%, t +0.8 (of 92 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 852 price snapshots stored in the last 26h, latest 11-19 04:02Z, 2511 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 730 of 1001 graded reads since 10-19 18:00Z; 2265 of 2593 new reads stamped (Pinnacle at the pick)
- contextAtPick on 1001 of 1001 graded reads since 10-19 18:00Z; 2593 of 2593 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 481 of 1001 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1275 of 1291 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 139 of 1393 graded reads since 10-14 00:00Z (Pinnacle at the open)
