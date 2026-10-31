# What EDGE is learning (2026-10-31 19:10Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
928 graded reads counted, 1856 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-31 16:02Z): 40 strategies tracking from 8400 hypotheses (0 new this run); 114 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 45, CLV +0.8%, t +0.9, last 30d +0.8% on 45; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
- ALL pattern=sharp-soft-alt: n 24, CLV +1.1%, t +1.4, last 30d +1.1% on 24; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 521, CLV -1.2%, t -5.8, last 30d -1.2% on 521
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 77 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 84, CLV +0.9% (best of 26)
- ALL moveBeforePick=none: n 491, CLV -1.1%, t -4.8, last 30d -1.1% on 491
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 76 tested; a lead to watch) | pair: venue=home + role=dog n 47, CLV +1.6% (best of 21)
- ALL timing=day: n 444, CLV -0.9%, t -4.4, last 30d -0.9% on 444
  > pocket: sharpDiv=pin-for inside timing=day: n 11, CLV +3.5%, t +1.9 (best of 78 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 57, CLV +0.4% (best of 22)
Observation: edge size is not yet predicting CLV (A -0.8% on 92, B -0.7% on 272, C -1.2% on 564).
  > last 50 graded reads: A +3.7% on 9, B +1.1% on 20, C -1.3% on 21 (A > B > C holds; diagnostic only)
  > pocket: pinEdge=2%+ inside grade A: n 9, CLV +3.7%, t +2.5 (best of 46 tested; a lead to watch)
  > order holds inside sharpDiv=aligned: A +4.4% on 6, B +0.9% on 16, C -0.5% on 38 (12 of 48 features tested)
Why reads lost to the close (autopsy, post-pick; 610 of 928, cause known on 610): overpaid 280 (-1.6%), news-after-pick 40 (-6.9%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 16 (-4.5%), sharp-move-against 30 (-2.2%), soft-move-against 1 (-3.4%), model-wrong 232 (-5.4%)
Process vs result: right-and-rewarded 174, right-but-unlucky 127, lucky-win 275, market-was-right 314, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 21, CLV -0.4%, t -0.4 (positive = the gate blocks winners); best pocket venue=away n 8, CLV +1.2%, t +0.5 (of 13 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 2399 price snapshots stored in the last 26h, latest 10-31 19:09Z, 1367 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 335 of 536 graded reads since 10-19 18:00Z; 874 of 1197 new reads stamped (Pinnacle at the pick)
- contextAtPick on 536 of 536 graded reads since 10-19 18:00Z; 1197 of 1197 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 195 of 536 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 856 of 870 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 89 of 928 graded reads since 10-14 00:00Z (Pinnacle at the open)
