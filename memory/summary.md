# What EDGE is learning (2026-11-15 15:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1347 graded reads counted, 3036 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-15 11:09Z): 25 strategies tracking from 5066 hypotheses (0 new this run); 140 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=soft-dog: n 126, CLV +0.4%, t +1.5, last 30d +0.4% on 126; grade.py needs 0 more graded full-bar picks (has 18), t >= 2.5
- NCAAF pattern=sharp-soft-alt: n 69, CLV +0.9%, t +1.7, last 30d +0.9% on 69; grade.py needs 9 more graded full-bar picks (has 6), t >= 2.5
- NCAAF pattern=soft-dog: n 59, CLV +0.2%, t +0.6, last 30d +0.2% on 59; grade.py needs 0 more graded full-bar picks (has 18), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 671, CLV -1.1%, t -6.4, last 30d -1.1% on 666
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 10, CLV +2.7%, t +1.2 (best of 85 tested; a lead to watch) | pair: venue=home + role=dog n 95, CLV +0.8% (best of 33)
- ALL moveBeforePick=none: n 611, CLV -1.2%, t -5.5, last 30d -1.2% on 609
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 10, CLV +2.7%, t +1.2 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 595, CLV -0.7%, t -3.8, last 30d -0.7% on 589
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 93 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 67, CLV +0.9% (best of 26)
Observation: edge size is not yet predicting CLV (A -0.2% on 125, B -0.1% on 532, C -1.2% on 690).
  > last 50 graded reads: A -0.8% on 6, B +0.2% on 36, C -0.7% on 8 (order still wrong; diagnostic only)
  > pocket: sharpDivPick=aligned inside grade A: n 30, CLV +3.5%, t +4.4 (best of 59 tested; a lead to watch)
  > order holds inside sharpDivPick=aligned: A +3.5% on 30, B +0.2% on 145, C -1.4% on 82 (25 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 798 of 1347, cause known on 798): overpaid 307 (-1.6%), news-after-pick 51 (-6.5%), sharps-against-at-pick 7 (-4.6%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 28 (-3.6%), sharp-move-against 81 (-2.1%), soft-move-against 2 (-3.2%), model-wrong 317 (-5.2%)
Process vs result: right-and-rewarded 280, right-but-unlucky 254, lucky-win 376, market-was-right 415, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 612, CLV -1.7%, t -8.7 (positive = the gate blocks winners); best pocket pattern=scan-nba-spread-away-restedgeawaymore-1e501d n 16, CLV +2.2%, t +1.0 (of 85 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1482 price snapshots stored in the last 26h, latest 11-15 15:24Z, 2344 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 684 of 955 graded reads since 10-19 18:00Z; 1865 of 2193 new reads stamped (Pinnacle at the pick)
- contextAtPick on 955 of 955 graded reads since 10-19 18:00Z; 2193 of 2193 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 457 of 955 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1229 of 1245 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 131 of 1347 graded reads since 10-14 00:00Z (Pinnacle at the open)
