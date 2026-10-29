# What EDGE is learning (2026-10-29 23:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
846 graded reads counted, 1687 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-29 17:25Z): 40 strategies tracking from 7840 hypotheses (0 new this run); 105 graded scan reads, mean CLV -0.5%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- ALL pattern=sharp-soft: n 41, CLV +1.2%, t +1.9, last 30d +1.2% on 41; grade.py needs 11 more graded full-bar picks (has 4), t >= 2.5
- NCAAF pattern=learned-ncaaf-spread: n 38, CLV +1.2%, t +1.3, last 30d +1.2% on 38; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 30, CLV +0.2%, t +0.6, last 30d +0.2% on 30; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 483, CLV -1.3%, t -6.1, last 30d -1.3% on 483
  > pocket: pattern=scan-nba-spread-away-restedgeawaymore-1e501d inside edgeBar=<0.5x: n 9, CLV +3.0%, t +1.2 (best of 75 tested; a lead to watch) | pair: role=fav + moveBeforePick=against n 11, CLV +0.4% (best of 26)
- ALL moveBeforePick=none: n 442, CLV -1.2%, t -4.8, last 30d -1.2% on 442
  > pocket: injury=qb inside moveBeforePick=none: n 9, CLV +4.0%, t +1.9 (best of 73 tested; a lead to watch) | pair: edgeBar=1-2x + timing=day n 12, CLV +0.9% (best of 20)
- ALL timing=day: n 422, CLV -0.9%, t -4.1, last 30d -0.9% on 422
  > pocket: sharpDiv=pin-for inside timing=day: n 11, CLV +3.5%, t +1.9 (best of 77 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 57, CLV +0.4% (best of 21)
Observation: edge size is not yet predicting CLV (A -1.3% on 83, B -0.8% on 246, C -1.3% on 517).
  > last 50 graded reads: A -2.7% on 2, B -1.3% on 18, C -1.4% on 30 (order still wrong; diagnostic only)
  > pocket: restEdge=more inside grade A: n 10, CLV +1.5%, t +1.0 (best of 42 tested; a lead to watch)
  > order holds inside restDays=1day: A +0.9% on 17, B -1.5% on 59, C -1.6% on 161 (8 of 43 features tested)
Why reads lost to the close (autopsy, post-pick; 567 of 846, cause known on 567): overpaid 262 (-1.6%), news-after-pick 35 (-6.9%), sharps-against-at-pick 5 (-5.3%), sharps-against-at-open 1 (-3.1%), bet-into-steam 3 (-3.2%), late-move 15 (-4.6%), sharp-move-against 23 (-2.5%), soft-move-against 1 (-3.4%), model-wrong 222 (-5.4%)
Process vs result: right-and-rewarded 157, right-but-unlucky 121, lucky-win 263, market-was-right 301, push 3; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Gated by the Pinnacle gate (scored, not counted): n 2, CLV -0.5%, t -0.9 (positive = the gate blocks winners)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1778 price snapshots stored in the last 26h, latest 10-29 23:24Z, 1206 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 282 of 454 graded reads since 10-19 18:00Z; 756 of 1079 new reads stamped (Pinnacle at the pick)
- contextAtPick on 454 of 454 graded reads since 10-19 18:00Z; 1079 of 1079 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 164 of 454 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 781 of 795 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 84 of 846 graded reads since 10-14 00:00Z (Pinnacle at the open)
