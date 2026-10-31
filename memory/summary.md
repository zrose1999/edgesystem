# What EDGE is learning (2026-10-31 00:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
878 graded reads counted, 1774 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-30 17:01Z): 40 strategies tracking from 7858 hypotheses (0 new this run); 112 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=sharp-soft: n 42, CLV +1.3%, t +2.0, last 30d +1.3% on 42; grade.py needs 11 more graded full-bar picks (has 4), t >= 2.5
- NCAAF pattern=learned-ncaaf-spread: n 40, CLV +1.4%, t +1.5, last 30d +1.4% on 40; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 495, CLV -1.2%, t -5.5, last 30d -1.2% on 495
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 75 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 81, CLV +0.8% (best of 26)
- ALL moveBeforePick=none: n 467, CLV -1.1%, t -4.5, last 30d -1.1% on 467
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 76 tested; a lead to watch) | pair: venue=home + role=dog n 46, CLV +1.5% (best of 21)
- ALL timing=day: n 437, CLV -1.0%, t -4.4, last 30d -1.0% on 437
  > pocket: sharpDiv=pin-for inside timing=day: n 11, CLV +3.5%, t +1.9 (best of 78 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 57, CLV +0.4% (best of 22)
Observation: edge size is not yet predicting CLV (A -1.3% on 84, B -0.7% on 253, C -1.2% on 541).
  > last 50 graded reads: A -2.7% on 2, B -1.2% on 18, C -3.1% on 30 (order still wrong; diagnostic only)
  > pocket: restEdge=more inside grade A: n 10, CLV +1.5%, t +1.0 (best of 42 tested; a lead to watch)
  > order holds inside restDays=1day: A +0.9% on 17, B -1.5% on 59, C -1.7% on 176 (3 of 44 features tested)
Why reads lost to the close (autopsy, post-pick; 586 of 878, cause known on 586): overpaid 275 (-1.6%), news-after-pick 36 (-6.9%), sharps-against-at-pick 5 (-5.3%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 15 (-4.6%), sharp-move-against 25 (-2.4%), soft-move-against 1 (-3.4%), model-wrong 224 (-5.4%)
Process vs result: right-and-rewarded 164, right-but-unlucky 123, lucky-win 272, market-was-right 311, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, goalie-outlier (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 4, CLV -1.7%, t -1.3 (positive = the gate blocks winners)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1729 price snapshots stored in the last 26h, latest 10-31 00:24Z, 1308 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 305 of 486 graded reads since 10-19 18:00Z; 809 of 1132 new reads stamped (Pinnacle at the pick)
- contextAtPick on 486 of 486 graded reads since 10-19 18:00Z; 1132 of 1132 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 171 of 486 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 810 of 824 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 86 of 878 graded reads since 10-14 00:00Z (Pinnacle at the open)
