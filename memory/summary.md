# What EDGE is learning (2026-10-24 02:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
388 graded reads counted, 808 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-23 16:00Z): 40 strategies tracking from 7702 hypotheses (0 new this run); 9 graded scan reads, mean CLV +0.8%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 21, CLV +0.2%, t +0.5, last 30d +0.2% on 21; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 16, CLV +0.8%, t +1.4, last 30d +0.8% on 16; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
- NBA pattern=learned-nba-total: n 12, CLV +0.3%, t +0.2, last 30d +0.3% on 12; grade.py needs 13 more graded full-bar picks (has 2), t >= 2.0
Early negative, still collecting (largest samples):
- ALL market=total: n 199, CLV -1.8%, t -6.8, last 30d -1.8% on 199
  > pocket: pattern=learned-nba-total inside market=total: n 12, CLV +0.3%, t +0.2 (best of 41 tested; a lead to watch) | pair: none (15 pair combos tested)
- ALL edgeBar=<0.5x: n 197, CLV -1.8%, t -6.8, last 30d -1.8% on 197
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 18, CLV +0.2%, t +0.4 (best of 54 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 27, CLV +0.0% (best of 16)
- ALL moveBeforePick=none: n 184, CLV -1.7%, t -5.3, last 30d -1.7% on 184
  > pocket: travelEdge=more inside moveBeforePick=none: n 17, CLV +1.0%, t +0.8 (best of 54 tested; a lead to watch) | pair: edgeBar=1-2x + timing=day n 8, CLV +0.7% (best of 10)
Observation: edge size is not yet predicting CLV (A -1.6% on 55, B -1.0% on 130, C -1.8% on 203).
  > last 50 graded reads: A +1.3% on 5, B -0.1% on 16, C -0.1% on 29 (A > B > C holds; diagnostic only)
  > pocket: travelEdge=more inside grade A: n 9, CLV +1.0%, t +0.5 (best of 30 tested; a lead to watch)
  > order holds inside timing=day: A +0.0% on 18, B -0.8% on 66, C -1.5% on 99 (5 of 36 features tested)
Why reads lost to the close (autopsy, post-pick; 271 of 388, cause known on 247): news-after-pick 16 (-4.9%), sharps-against-at-pick 4 (-2.9%), sharps-against-at-open 1 (-3.1%), bet-into-steam 5 (-2.0%), late-move 2 (-2.2%), number-off 219 (-3.4%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 54, right-but-unlucky 51, lucky-win 122, market-was-right 139; right-but-unlucky losses hurt most by flipped-late, close-margin, goalie-outlier (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1635 price snapshots stored in the last 26h, latest 10-24 02:24Z, 600 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 94 of 116 graded reads since 10-19 18:00Z; 479 of 591 new reads stamped (Pinnacle at the pick)
- contextAtPick on 116 of 116 graded reads since 10-19 18:00Z; 591 of 591 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 39 of 116 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 363 of 371 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 21 of 388 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 38 of 116 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
