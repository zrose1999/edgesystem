# What EDGE is learning (2026-11-08 03:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1211 graded reads counted, 2531 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-07 16:48Z): 23 strategies tracking from 4886 hypotheses (0 new this run); 131 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=soft-dog: n 76, CLV +0.6%, t +1.9, last 30d +0.6% on 76; grade.py needs 6 more graded full-bar picks (has 9), t >= 2.5
- ALL pattern=sharp-soft-alt: n 60, CLV +0.8%, t +1.7, last 30d +0.8% on 60; grade.py needs 11 more graded full-bar picks (has 4), t >= 2.5
- NCAAF pattern=learned-ncaaf-spread: n 57, CLV +0.4%, t +0.6, last 30d +0.4% on 57; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 639, CLV -1.2%, t -6.5, last 30d -1.2% on 639
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 83 tested; a lead to watch) | pair: venue=home + role=dog n 80, CLV +0.7% (best of 31)
- ALL moveBeforePick=none: n 591, CLV -1.2%, t -5.4, last 30d -1.2% on 591
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 540, CLV -0.7%, t -3.6, last 30d -0.7% on 540
  > pocket: sharpDiv=pin-for inside timing=day: n 12, CLV +2.9%, t +1.7 (best of 88 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 62, CLV +0.9% (best of 25)
Observation: edge size is not yet predicting CLV (A -0.4% on 109, B -0.2% on 431, C -1.2% on 671).
  > last 50 graded reads: A +3.7% on 5, B +0.7% on 36, C -1.6% on 9 (A > B > C holds; diagnostic only)
  > pocket: sharpDiv=aligned inside grade A: n 8, CLV +3.7%, t +2.4 (best of 53 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +3.4% on 25, B +0.1% on 120, C -1.3% on 78 (24 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 741 of 1211, cause known on 741): overpaid 306 (-1.6%), news-after-pick 51 (-6.4%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 22 (-3.9%), sharp-move-against 61 (-1.9%), soft-move-against 2 (-3.2%), model-wrong 288 (-5.3%)
Process vs result: right-and-rewarded 240, right-but-unlucky 204, lucky-win 337, market-was-right 386, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 220, CLV -1.6%, t -5.6 (positive = the gate blocks winners); best pocket role=over n 8, CLV +0.5%, t +0.6 (of 58 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1461 price snapshots stored in the last 26h, latest 11-08 03:24Z, 1930 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 548 of 819 graded reads since 10-19 18:00Z; 1386 of 1714 new reads stamped (Pinnacle at the pick)
- contextAtPick on 819 of 819 graded reads since 10-19 18:00Z; 1714 of 1714 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 356 of 819 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1098 of 1113 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 116 of 1211 graded reads since 10-14 00:00Z (Pinnacle at the open)
