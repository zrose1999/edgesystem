# What EDGE is learning (2026-11-03 19:09Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1092 graded reads counted, 2217 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-03 18:22Z): 23 strategies tracking from 4820 hypotheses (11 new this run); 125 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 55, CLV +0.7%, t +0.8, last 30d +0.7% on 55; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=soft-dog: n 40, CLV +0.4%, t +1.6, last 30d +0.4% on 40; grade.py needs 11 more graded full-bar picks (has 4), t >= 2.5
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 607, CLV -1.2%, t -6.4, last 30d -1.2% on 607
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 83 tested; a lead to watch) | pair: venue=home + role=dog n 71, CLV +0.8% (best of 29)
- ALL moveBeforePick=none: n 566, CLV -1.2%, t -5.5, last 30d -1.2% on 566
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 79 tested; a lead to watch) | pair: venue=home + role=dog n 48, CLV +1.6% (best of 21)
- ALL timing=day: n 498, CLV -0.9%, t -4.4, last 30d -0.9% on 498
  > pocket: sharpDiv=pin-for inside timing=day: n 11, CLV +3.5%, t +1.9 (best of 88 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 58, CLV +0.4% (best of 25)
Observation: edge size is not yet predicting CLV (A -0.6% on 100, B -0.4% on 343, C -1.2% on 649).
  > last 50 graded reads: A +0.4% on 3, B +0.8% on 27, C -0.5% on 20 (order still wrong; diagnostic only)
  > pocket: sharpDiv=aligned inside grade A: n 8, CLV +3.7%, t +2.4 (best of 49 tested; a lead to watch)
  > order holds inside sharpGapOpen=<1%: A +3.7% on 8, B +0.9% on 29, C -0.5% on 38 (20 of 53 features tested)
Why reads lost to the close (autopsy, post-pick; 693 of 1092, cause known on 693): overpaid 300 (-1.6%), news-after-pick 41 (-6.8%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 21 (-4.0%), sharp-move-against 49 (-1.9%), soft-move-against 2 (-3.2%), model-wrong 269 (-5.3%)
Process vs result: right-and-rewarded 218, right-but-unlucky 170, lucky-win 318, market-was-right 369, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 88, CLV -0.3%, t -0.8 (positive = the gate blocks winners); best pocket tzShift=east n 13, CLV +2.7%, t +1.3 (of 46 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1294 price snapshots stored in the last 26h, latest 11-03 19:09Z, 1615 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 434 of 700 graded reads since 10-19 18:00Z; 1180 of 1503 new reads stamped (Pinnacle at the pick)
- contextAtPick on 700 of 700 graded reads since 10-19 18:00Z; 1503 of 1503 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 268 of 700 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 999 of 1013 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 107 of 1092 graded reads since 10-14 00:00Z (Pinnacle at the open)
