# What EDGE is learning (2026-11-15 00:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1321 graded reads counted, 2926 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-14 16:57Z): 25 strategies tracking from 5032 hypotheses (0 new this run); 140 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 58, CLV +0.3%, t +0.4, last 30d +0.4% on 57; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NCAAF pattern=soft-dog: n 51, CLV +0.4%, t +1.1, last 30d +0.4% on 51; grade.py needs 0 more graded full-bar picks (has 16), t >= 2.5
- NBA pattern=sharp-soft: n 44, CLV +1.2%, t +2.0, last 30d +1.2% on 44; grade.py needs 0 more graded full-bar picks (has 20), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 667, CLV -1.1%, t -6.3, last 30d -1.1% on 662
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 10, CLV +2.7%, t +1.2 (best of 85 tested; a lead to watch) | pair: venue=home + role=dog n 94, CLV +0.8% (best of 33)
- ALL moveBeforePick=none: n 608, CLV -1.2%, t -5.4, last 30d -1.2% on 606
  > pocket: sharpGapPick=2%+ inside moveBeforePick=none: n 9, CLV +2.8%, t +2.1 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 587, CLV -0.6%, t -3.6, last 30d -0.6% on 581
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 92 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 67, CLV +0.9% (best of 26)
Observation: grades rank A > B > C (A -0.0% on 122, B -0.1% on 510, C -1.2% on 689).
  > last 50 graded reads: A +2.9% on 7, B +1.0% on 32, C -0.7% on 11 (A > B > C holds; diagnostic only)
  > pocket: sharpDivPick=aligned inside grade A: n 30, CLV +3.5%, t +4.4 (best of 59 tested; a lead to watch)
  > order holds inside sharpDivPick=aligned: A +3.5% on 30, B +0.3% on 135, C -1.4% on 82 (28 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 785 of 1321, cause known on 785): overpaid 307 (-1.6%), news-after-pick 47 (-5.9%), sharps-against-at-pick 7 (-4.6%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 24 (-3.8%), sharp-move-against 78 (-2.1%), soft-move-against 2 (-3.2%), model-wrong 315 (-5.1%)
Process vs result: right-and-rewarded 270, right-but-unlucky 239, lucky-win 363, market-was-right 407, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 530, CLV -1.9%, t -9.9 (positive = the gate blocks winners); best pocket pattern=scan-nba-spread-away-restedgeawaymore-1e501d n 12, CLV +0.9%, t +0.5 (of 83 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1551 price snapshots stored in the last 26h, latest 11-15 00:24Z, 2310 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 658 of 929 graded reads since 10-19 18:00Z; 1831 of 2159 new reads stamped (Pinnacle at the pick)
- contextAtPick on 929 of 929 graded reads since 10-19 18:00Z; 2159 of 2159 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 436 of 929 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1203 of 1219 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 124 of 1321 graded reads since 10-14 00:00Z (Pinnacle at the open)
