# What EDGE is learning (2026-11-09 00:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1238 graded reads counted, 2599 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-08 17:00Z): 23 strategies tracking from 4910 hypotheses (0 new this run); 131 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=sharp-soft-alt: n 62, CLV +1.0%, t +2.0, last 30d +1.0% on 62; grade.py needs 10 more graded full-bar picks (has 5), t >= 2.5
- NCAAF pattern=learned-ncaaf-spread: n 58, CLV +0.3%, t +0.4, last 30d +0.3% on 58; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NCAAF pattern=sharp-soft-alt: n 45, CLV +0.8%, t +1.3, last 30d +0.8% on 45; grade.py needs 10 more graded full-bar picks (has 5), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 645, CLV -1.2%, t -6.5, last 30d -1.2% on 645
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 83 tested; a lead to watch) | pair: venue=home + role=dog n 85, CLV +0.7% (best of 31)
- ALL moveBeforePick=none: n 593, CLV -1.2%, t -5.5, last 30d -1.2% on 593
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 549, CLV -0.7%, t -3.6, last 30d -0.7% on 549
  > pocket: sharpDiv=pin-for inside timing=day: n 12, CLV +2.9%, t +1.7 (best of 88 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 63, CLV +0.9% (best of 25)
Observation: edge size is not yet predicting CLV (A -0.2% on 112, B -0.2% on 454, C -1.2% on 672).
  > last 50 graded reads: A +0.9% on 5, B +0.4% on 36, C -1.6% on 9 (A > B > C holds; diagnostic only)
  > pocket: sharpDiv=aligned inside grade A: n 8, CLV +3.7%, t +2.4 (best of 55 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +3.7% on 26, B +0.1% on 123, C -1.3% on 78 (27 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 749 of 1238, cause known on 749): overpaid 306 (-1.6%), news-after-pick 52 (-6.3%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 22 (-3.9%), sharp-move-against 66 (-2.0%), soft-move-against 2 (-3.2%), model-wrong 290 (-5.3%)
Process vs result: right-and-rewarded 253, right-but-unlucky 219, lucky-win 346, market-was-right 396, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 248, CLV -1.8%, t -6.7 (positive = the gate blocks winners); best pocket role=over n 9, CLV +0.1%, t +0.1 (of 61 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 892 price snapshots stored in the last 26h, latest 11-09 00:54Z, 1954 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 575 of 846 graded reads since 10-19 18:00Z; 1482 of 1810 new reads stamped (Pinnacle at the pick)
- contextAtPick on 846 of 846 graded reads since 10-19 18:00Z; 1810 of 1810 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 376 of 846 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1121 of 1136 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 119 of 1238 graded reads since 10-14 00:00Z (Pinnacle at the open)
