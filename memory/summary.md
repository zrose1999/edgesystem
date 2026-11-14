# What EDGE is learning (2026-11-14 11:10Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1284 graded reads counted, 2812 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-14 11:10Z): 25 strategies tracking from 5032 hypotheses (0 new this run); 140 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 58, CLV +0.3%, t +0.4, last 30d +0.3% on 58; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NCAAF pattern=sharp-soft-alt: n 48, CLV +1.0%, t +1.7, last 30d +1.0% on 48; grade.py needs 9 more graded full-bar picks (has 6), t >= 2.5
- NBA pattern=sharp-soft: n 44, CLV +1.2%, t +2.0, last 30d +1.2% on 44; grade.py needs 0 more graded full-bar picks (has 20), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 657, CLV -1.1%, t -6.3, last 30d -1.1% on 657
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 10, CLV +2.7%, t +1.2 (best of 83 tested; a lead to watch) | pair: venue=home + role=dog n 88, CLV +0.7% (best of 31)
- ALL moveBeforePick=none: n 599, CLV -1.2%, t -5.5, last 30d -1.2% on 599
  > pocket: sharpGapPick=2%+ inside moveBeforePick=none: n 9, CLV +2.8%, t +2.1 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 577, CLV -0.7%, t -3.6, last 30d -0.7% on 577
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 90 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 64, CLV +0.8% (best of 25)
Observation: grades rank A > B > C (A -0.1% on 121, B -0.2% on 476, C -1.2% on 687).
  > last 50 graded reads: A +2.1% on 9, B +0.7% on 26, C -0.7% on 15 (A > B > C holds; diagnostic only)
  > pocket: sharpGapPick=<1% inside grade A: n 29, CLV +3.6%, t +4.3 (best of 58 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +3.6% on 29, B +0.3% on 126, C -1.4% on 82 (31 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 769 of 1284, cause known on 769): overpaid 306 (-1.6%), news-after-pick 45 (-6.0%), sharps-against-at-pick 7 (-4.6%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 23 (-3.9%), sharp-move-against 72 (-2.1%), soft-move-against 2 (-3.2%), model-wrong 309 (-5.2%)
Process vs result: right-and-rewarded 268, right-but-unlucky 233, lucky-win 358, market-was-right 404, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 453, CLV -1.8%, t -8.3 (positive = the gate blocks winners); best pocket pattern=scan-nba-spread-away-restedgeawaymore-1e501d n 12, CLV +0.9%, t +0.5 (of 78 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1012 price snapshots stored in the last 26h, latest 11-14 11:09Z, 2282 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 621 of 892 graded reads since 10-19 18:00Z; 1809 of 2137 new reads stamped (Pinnacle at the pick)
- contextAtPick on 892 of 892 graded reads since 10-19 18:00Z; 2137 of 2137 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 411 of 892 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1167 of 1182 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 124 of 1284 graded reads since 10-14 00:00Z (Pinnacle at the open)
