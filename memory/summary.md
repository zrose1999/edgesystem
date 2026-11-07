# What EDGE is learning (2026-11-07 23:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1186 graded reads counted, 2457 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-07 16:48Z): 23 strategies tracking from 4886 hypotheses (0 new this run); 129 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 57, CLV +0.4%, t +0.6, last 30d +0.4% on 57; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NBA pattern=sharp-soft: n 31, CLV +1.4%, t +1.7, last 30d +1.4% on 31; grade.py needs 1 more graded full-bar picks (has 14), t >= 2.5
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 633, CLV -1.2%, t -6.5, last 30d -1.2% on 633
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 83 tested; a lead to watch) | pair: venue=home + role=dog n 80, CLV +0.7% (best of 30)
- ALL moveBeforePick=none: n 585, CLV -1.2%, t -5.4, last 30d -1.2% on 585
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 80 tested; a lead to watch) | pair: venue=home + role=dog n 51, CLV +2.1% (best of 23)
- ALL timing=day: n 529, CLV -0.7%, t -3.7, last 30d -0.7% on 529
  > pocket: sharpDiv=pin-for inside timing=day: n 12, CLV +2.9%, t +1.7 (best of 88 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 61, CLV +0.9% (best of 25)
Observation: edge size is not yet predicting CLV (A -0.3% on 107, B -0.2% on 413, C -1.2% on 666).
  > last 50 graded reads: A +5.1% on 5, B +0.8% on 38, C -1.6% on 7 (A > B > C holds; diagnostic only)
  > pocket: pinEdge=2%+ inside grade A: n 18, CLV +3.8%, t +3.8 (best of 52 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +3.3% on 24, B +0.4% on 111, C -1.3% on 78 (25 of 54 features tested)
Why reads lost to the close (autopsy, post-pick; 728 of 1186, cause known on 728): overpaid 306 (-1.6%), news-after-pick 46 (-6.5%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 22 (-3.9%), sharp-move-against 58 (-2.0%), soft-move-against 2 (-3.2%), model-wrong 283 (-5.3%)
Process vs result: right-and-rewarded 234, right-but-unlucky 193, lucky-win 329, market-was-right 383, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 189, CLV -1.8%, t -6.0 (positive = the gate blocks winners)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1583 price snapshots stored in the last 26h, latest 11-07 23:54Z, 1921 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 523 of 794 graded reads since 10-19 18:00Z; 1374 of 1702 new reads stamped (Pinnacle at the pick)
- contextAtPick on 794 of 794 graded reads since 10-19 18:00Z; 1702 of 1702 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 336 of 794 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1077 of 1092 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 113 of 1186 graded reads since 10-14 00:00Z (Pinnacle at the open)
