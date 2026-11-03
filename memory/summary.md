# What EDGE is learning (2026-11-03 00:31Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1060 graded reads counted, 2115 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-02 20:47Z): 40 strategies tracking from 10258 hypotheses (0 new this run); 117 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 55, CLV +0.7%, t +0.8, last 30d +0.7% on 55; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=soft-dog: n 32, CLV +0.4%, t +1.9, last 30d +0.4% on 32; grade.py needs 12 more graded full-bar picks (has 3), t >= 2.5
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 597, CLV -1.2%, t -6.5, last 30d -1.2% on 597
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 81 tested; a lead to watch) | pair: venue=home + role=dog n 70, CLV +0.7% (best of 29)
- ALL moveBeforePick=none: n 558, CLV -1.2%, t -5.5, last 30d -1.2% on 558
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 78 tested; a lead to watch) | pair: venue=home + role=dog n 48, CLV +1.6% (best of 21)
- ALL timing=day: n 480, CLV -0.9%, t -4.5, last 30d -0.9% on 480
  > pocket: sharpDiv=pin-for inside timing=day: n 11, CLV +3.5%, t +1.9 (best of 86 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 58, CLV +0.4% (best of 25)
Observation: edge size is not yet predicting CLV (A -0.6% on 99, B -0.5% on 328, C -1.3% on 633).
  > last 50 graded reads: A +2.9% on 7, B +0.8% on 32, C -0.9% on 11 (A > B > C holds; diagnostic only)
  > pocket: sharpGapOpen=<1% inside grade A: n 8, CLV +3.7%, t +2.4 (best of 49 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +2.9% on 20, B -0.5% on 69, C -1.4% on 75 (18 of 53 features tested)
Why reads lost to the close (autopsy, post-pick; 677 of 1060, cause known on 677): overpaid 299 (-1.6%), news-after-pick 41 (-6.9%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 18 (-4.4%), sharp-move-against 43 (-2.0%), soft-move-against 2 (-3.2%), model-wrong 263 (-5.4%)
Process vs result: right-and-rewarded 211, right-but-unlucky 163, lucky-win 306, market-was-right 368, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 64, CLV -0.9%, t -2.2 (positive = the gate blocks winners); best pocket restDays=long n 10, CLV +0.6%, t +0.5 (of 37 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1311 price snapshots stored in the last 26h, latest 11-03 00:24Z, 1576 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 405 of 668 graded reads since 10-19 18:00Z; 1147 of 1470 new reads stamped (Pinnacle at the pick)
- contextAtPick on 668 of 668 graded reads since 10-19 18:00Z; 1470 of 1470 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 246 of 668 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 972 of 986 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 105 of 1060 graded reads since 10-14 00:00Z (Pinnacle at the open)
