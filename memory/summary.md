# What EDGE is learning (2026-11-12 19:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1259 graded reads counted, 2747 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-12 18:47Z): 25 strategies tracking from 5010 hypotheses (0 new this run); 136 graded scan reads, mean CLV -0.7%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=sharp-soft-alt: n 65, CLV +0.9%, t +1.9, last 30d +0.9% on 65; grade.py needs 10 more graded full-bar picks (has 5), t >= 2.5
- NCAAF pattern=learned-ncaaf-spread: n 58, CLV +0.3%, t +0.4, last 30d +0.3% on 58; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NCAAF pattern=sharp-soft-alt: n 45, CLV +0.8%, t +1.3, last 30d +0.8% on 45; grade.py needs 10 more graded full-bar picks (has 5), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 648, CLV -1.1%, t -6.4, last 30d -1.1% on 648
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 83 tested; a lead to watch) | pair: venue=home + role=dog n 86, CLV +0.7% (best of 31)
- ALL moveBeforePick=none: n 594, CLV -1.2%, t -5.5, last 30d -1.2% on 594
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 81 tested; a lead to watch) | pair: timing=day + sharpDivPick=pin-for n 9, CLV +2.3% (best of 24)
- ALL timing=day: n 561, CLV -0.7%, t -3.8, last 30d -0.7% on 561
  > pocket: sharpDiv=pin-for inside timing=day: n 13, CLV +2.4%, t +1.4 (best of 88 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 64, CLV +0.8% (best of 25)
Observation: grades rank A > B > C (A -0.1% on 118, B -0.2% on 463, C -1.2% on 678).
  > last 50 graded reads: A +2.4% on 8, B +0.2% on 29, C -1.8% on 13 (A > B > C holds; diagnostic only)
  > pocket: sharpGapPick=<1% inside grade A: n 27, CLV +3.6%, t +4.0 (best of 57 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +3.6% on 27, B +0.1% on 123, C -1.4% on 82 (28 of 56 features tested)
Why reads lost to the close (autopsy, post-pick; 758 of 1259, cause known on 758): overpaid 306 (-1.6%), news-after-pick 51 (-5.8%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 23 (-3.9%), sharp-move-against 68 (-2.1%), soft-move-against 2 (-3.2%), model-wrong 297 (-5.3%)
Process vs result: right-and-rewarded 258, right-but-unlucky 229, lucky-win 353, market-was-right 398, push 4; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 413, CLV -1.6%, t -7.0 (positive = the gate blocks winners); best pocket pattern=scan-nba-spread-away-restedgeawaymore-1e501d n 10, CLV +1.4%, t +0.6 (of 77 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 959 price snapshots stored in the last 26h, latest 11-12 19:09Z, 2190 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 596 of 867 graded reads since 10-19 18:00Z; 1719 of 2047 new reads stamped (Pinnacle at the pick)
- contextAtPick on 867 of 867 graded reads since 10-19 18:00Z; 2047 of 2047 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 392 of 867 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 1142 of 1157 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 124 of 1259 graded reads since 10-14 00:00Z (Pinnacle at the open)
