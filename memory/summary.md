# What EDGE is learning (2026-11-01 02:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
998 graded reads counted, 1966 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-31 16:02Z): 40 strategies tracking from 8400 hypotheses (0 new this run); 117 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 54, CLV +0.8%, t +1.0, last 30d +0.8% on 54; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
- NCAAF pattern=sharp-soft-alt: n 25, CLV +0.6%, t +1.0, last 30d +0.6% on 25; grade.py needs 12 more graded full-bar picks (has 3), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 556, CLV -1.2%, t -5.9, last 30d -1.2% on 556
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 81 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 85, CLV +0.9% (best of 26)
- ALL moveBeforePick=none: n 527, CLV -1.1%, t -4.9, last 30d -1.1% on 527
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 77 tested; a lead to watch) | pair: venue=home + role=dog n 47, CLV +1.6% (best of 21)
- ALL timing=day: n 466, CLV -0.9%, t -4.3, last 30d -0.9% on 466
  > pocket: sharpDiv=pin-for inside timing=day: n 11, CLV +3.5%, t +1.9 (best of 84 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 58, CLV +0.4% (best of 25)
Observation: edge size is not yet predicting CLV (A -0.7% on 96, B -0.5% on 305, C -1.2% on 597).
  > last 50 graded reads: A +3.8% on 8, B +0.9% on 36, C -0.3% on 6 (A > B > C holds; diagnostic only)
  > pocket: pinEdge=2%+ inside grade A: n 13, CLV +3.3%, t +3.2 (best of 46 tested; a lead to watch)
  > order holds inside sharpGapOpen=<1%: A +4.4% on 6, B +0.6% on 21, C -0.5% on 38 (15 of 50 features tested)
Why reads lost to the close (autopsy, post-pick; 643 of 998, cause known on 643): overpaid 289 (-1.6%), news-after-pick 41 (-6.8%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 18 (-4.4%), sharp-move-against 36 (-2.2%), soft-move-against 1 (-3.4%), model-wrong 247 (-5.3%)
Process vs result: right-and-rewarded 197, right-but-unlucky 149, lucky-win 291, market-was-right 334, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 40, CLV -0.6%, t -1.1 (positive = the gate blocks winners); best pocket venue=away n 15, CLV +1.1%, t +0.8 (of 29 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 2027 price snapshots stored in the last 26h, latest 11-01 02:54Z, 1398 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 372 of 606 graded reads since 10-19 18:00Z; 899 of 1222 new reads stamped (Pinnacle at the pick)
- contextAtPick on 606 of 606 graded reads since 10-19 18:00Z; 1222 of 1222 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 224 of 606 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 921 of 935 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 95 of 998 graded reads since 10-14 00:00Z (Pinnacle at the open)
