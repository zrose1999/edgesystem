# What EDGE is learning (2026-10-31 02:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
890 graded reads counted, 1792 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-30 17:01Z): 40 strategies tracking from 7858 hypotheses (0 new this run); 112 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 40, CLV +1.4%, t +1.5, last 30d +1.4% on 40; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
- ALL pattern=sharp-soft-alt: n 22, CLV +1.4%, t +1.7, last 30d +1.4% on 22; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 496, CLV -1.2%, t -5.5, last 30d -1.2% on 496
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 77 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 81, CLV +0.8% (best of 26)
- ALL moveBeforePick=none: n 467, CLV -1.1%, t -4.5, last 30d -1.1% on 467
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 76 tested; a lead to watch) | pair: venue=home + role=dog n 46, CLV +1.5% (best of 21)
- ALL timing=day: n 439, CLV -1.0%, t -4.4, last 30d -1.0% on 439
  > pocket: sharpDiv=pin-for inside timing=day: n 11, CLV +3.5%, t +1.9 (best of 78 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 57, CLV +0.4% (best of 22)
Observation: edge size is not yet predicting CLV (A -1.1% on 88, B -0.7% on 261, C -1.2% on 541).
  > last 50 graded reads: A +1.0% on 6, B +0.1% on 23, C -2.3% on 21 (A > B > C holds; diagnostic only)
  > pocket: travelEdge=even inside grade A: n 10, CLV +1.6%, t +2.4 (best of 43 tested; a lead to watch)
  > order holds inside restDays=1day: A +1.3% on 21, B -1.2% on 64, C -1.7% on 176 (4 of 45 features tested)
Why reads lost to the close (autopsy, post-pick; 589 of 890, cause known on 589): overpaid 275 (-1.6%), news-after-pick 36 (-6.9%), sharps-against-at-pick 5 (-5.3%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 15 (-4.6%), sharp-move-against 27 (-2.4%), soft-move-against 1 (-3.4%), model-wrong 225 (-5.4%)
Process vs result: right-and-rewarded 170, right-but-unlucky 125, lucky-win 273, market-was-right 311, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, goalie-outlier (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 5, CLV -1.9%, t -1.8 (positive = the gate blocks winners)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1640 price snapshots stored in the last 26h, latest 10-31 02:24Z, 1322 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 317 of 498 graded reads since 10-19 18:00Z; 811 of 1134 new reads stamped (Pinnacle at the pick)
- contextAtPick on 498 of 498 graded reads since 10-19 18:00Z; 1134 of 1134 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 182 of 498 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 822 of 836 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 86 of 890 graded reads since 10-14 00:00Z (Pinnacle at the open)
