# What EDGE is learning (2026-11-10 16:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1250 graded reads counted, 2659 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-10 11:09Z): 25 strategies tracking from 4956 hypotheses (3 new this run); 135 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=sharp-soft-alt: n 63, CLV +0.9%, t +1.8, last 30d +0.9% on 63; grade.py needs 10 more graded full-bar picks (has 5), t >= 2.5
- NCAAF pattern=learned-ncaaf-spread: n 58, CLV +0.3%, t +0.4, last 30d +0.3% on 58; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NCAAF pattern=sharp-soft-alt: n 45, CLV +0.8%, t +1.3, last 30d +0.8% on 45; grade.py needs 10 more graded full-bar picks (has 5), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 647, CLV -1.1%, t -6.4, last 30d -1.1% on 647
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 83 tested; a lead to watch) | pair: venue=home + role=dog n 86, CLV +0.7% (best of 31)
- ALL moveBeforePick=none: n 594, CLV -1.2%, t -5.5, last 30d -1.2% on 594
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 556, CLV -0.7%, t -3.8, last 30d -0.7% on 556
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 88 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 64, CLV +0.8% (best of 25)
Observation: edge size is not yet predicting CLV (A -0.2% on 115, B -0.2% on 458, C -1.2% on 677).
  > last 50 graded reads: A +1.9% on 6, B -0.1% on 30, C -1.5% on 14 (A > B > C holds; diagnostic only)
  > pocket: sharpDiv=aligned inside grade A: n 8, CLV +3.7%, t +2.4 (best of 55 tested; a lead to watch)
  > order holds inside sharpDivPick=aligned: A +3.7% on 26, B +0.1% on 123, C -1.4% on 81 (27 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 757 of 1250, cause known on 757): overpaid 306 (-1.6%), news-after-pick 53 (-6.1%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 22 (-3.9%), sharp-move-against 69 (-2.1%), soft-move-against 2 (-3.2%), model-wrong 294 (-5.3%)
Process vs result: right-and-rewarded 255, right-but-unlucky 224, lucky-win 352, market-was-right 398, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 334, CLV -1.6%, t -6.3 (positive = the gate blocks winners); best pocket pattern=rest-spot n 8, CLV +0.9%, t +0.3 (of 68 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 432 price snapshots stored in the last 26h, latest 11-10 15:09Z, 2001 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 587 of 858 graded reads since 10-19 18:00Z; 1600 of 1928 new reads stamped (Pinnacle at the pick)
- contextAtPick on 858 of 858 graded reads since 10-19 18:00Z; 1928 of 1928 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 385 of 858 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1133 of 1148 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 123 of 1250 graded reads since 10-14 00:00Z (Pinnacle at the open)
