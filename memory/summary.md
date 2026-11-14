# What EDGE is learning (2026-11-14 03:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1281 graded reads counted, 2805 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-13 18:28Z): 25 strategies tracking from 5028 hypotheses (0 new this run); 140 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 58, CLV +0.3%, t +0.4, last 30d +0.3% on 58; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NCAAF pattern=sharp-soft-alt: n 47, CLV +0.8%, t +1.4, last 30d +0.8% on 47; grade.py needs 9 more graded full-bar picks (has 6), t >= 2.5
- NBA pattern=sharp-soft: n 44, CLV +1.2%, t +2.0, last 30d +1.2% on 44; grade.py needs 0 more graded full-bar picks (has 20), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 657, CLV -1.1%, t -6.3, last 30d -1.1% on 657
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 10, CLV +2.7%, t +1.2 (best of 83 tested; a lead to watch) | pair: venue=home + role=dog n 88, CLV +0.7% (best of 31)
- ALL moveBeforePick=none: n 598, CLV -1.2%, t -5.5, last 30d -1.2% on 598
  > pocket: sharpGapPick=2%+ inside moveBeforePick=none: n 9, CLV +2.8%, t +2.1 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 575, CLV -0.7%, t -3.6, last 30d -0.7% on 575
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 90 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 64, CLV +0.8% (best of 25)
Observation: grades rank A > B > C (A -0.1% on 121, B -0.2% on 474, C -1.2% on 686).
  > last 50 graded reads: A +2.1% on 9, B +0.4% on 27, C -0.5% on 14 (A > B > C holds; diagnostic only)
  > pocket: sharpGapPick=<1% inside grade A: n 29, CLV +3.6%, t +4.3 (best of 58 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +3.6% on 29, B +0.2% on 125, C -1.4% on 82 (32 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 768 of 1281, cause known on 768): overpaid 306 (-1.6%), news-after-pick 47 (-5.8%), sharps-against-at-pick 7 (-4.6%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 23 (-3.9%), sharp-move-against 72 (-2.1%), soft-move-against 2 (-3.2%), model-wrong 306 (-5.2%)
Process vs result: right-and-rewarded 261, right-but-unlucky 232, lucky-win 356, market-was-right 402, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 449, CLV -1.8%, t -8.2 (positive = the gate blocks winners); best pocket pattern=scan-nba-spread-away-restedgeawaymore-1e501d n 12, CLV +0.9%, t +0.5 (of 78 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 928 price snapshots stored in the last 26h, latest 11-14 03:27Z, 2279 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 618 of 889 graded reads since 10-19 18:00Z; 1774 of 2102 new reads stamped (Pinnacle at the pick)
- contextAtPick on 889 of 889 graded reads since 10-19 18:00Z; 2102 of 2102 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 409 of 889 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1164 of 1179 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 124 of 1281 graded reads since 10-14 00:00Z (Pinnacle at the open)
