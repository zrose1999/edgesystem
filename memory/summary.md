# What EDGE is learning (2026-11-02 01:01Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
1053 graded reads counted, 2091 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 11-01 17:06Z): 40 strategies tracking from 10242 hypotheses (0 new this run); 117 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 55, CLV +0.7%, t +0.8, last 30d +0.7% on 55; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
- NCAAF pattern=sharp-soft-alt: n 25, CLV +0.6%, t +1.0, last 30d +0.6% on 25; grade.py needs 12 more graded full-bar picks (has 3), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 596, CLV -1.3%, t -6.5, last 30d -1.3% on 596
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 81 tested; a lead to watch) | pair: venue=home + role=dog n 69, CLV +0.7% (best of 29)
- ALL moveBeforePick=none: n 558, CLV -1.2%, t -5.5, last 30d -1.2% on 558
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside moveBeforePick=none: n 9, CLV +3.0%, t +1.2 (best of 78 tested; a lead to watch) | pair: venue=home + role=dog n 48, CLV +1.6% (best of 21)
- ALL timing=day: n 477, CLV -0.9%, t -4.5, last 30d -0.9% on 477
  > pocket: sharpDiv=pin-for inside timing=day: n 11, CLV +3.5%, t +1.9 (best of 86 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 58, CLV +0.4% (best of 25)
Observation: edge size is not yet predicting CLV (A -0.6% on 99, B -0.6% on 321, C -1.3% on 633).
  > last 50 graded reads: A +2.9% on 11, B -0.2% on 28, C -0.9% on 11 (A > B > C holds; diagnostic only)
  > pocket: sharpGapOpen=<1% inside grade A: n 8, CLV +3.7%, t +2.4 (best of 49 tested; a lead to watch)
  > order holds inside sharpGapPick=<1%: A +2.9% on 20, B -1.0% on 65, C -1.4% on 75 (15 of 52 features tested)
Why reads lost to the close (autopsy, post-pick; 677 of 1053, cause known on 677): overpaid 299 (-1.6%), news-after-pick 43 (-6.8%), sharps-against-at-pick 6 (-5.1%), sharps-against-at-open 1 (-3.1%), bet-into-steam 4 (-3.1%), late-move 18 (-4.4%), sharp-move-against 42 (-2.0%), soft-move-against 2 (-3.2%), model-wrong 262 (-5.5%)
Process vs result: right-and-rewarded 206, right-but-unlucky 160, lucky-win 302, market-was-right 360, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 53, CLV -0.5%, t -1.1 (positive = the gate blocks winners); best pocket pattern=tennis-elo n 9, CLV +0.8%, t +0.4 (of 35 tested)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1459 price snapshots stored in the last 26h, latest 11-02 01:00Z, 1481 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 398 of 661 graded reads since 10-19 18:00Z; 1014 of 1337 new reads stamped (Pinnacle at the pick)
- contextAtPick on 661 of 661 graded reads since 10-19 18:00Z; 1337 of 1337 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 239 of 661 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 972 of 986 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 101 of 1053 graded reads since 10-14 00:00Z (Pinnacle at the open)
