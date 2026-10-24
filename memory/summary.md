# What EDGE is learning (2026-10-24 23:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
493 graded reads counted, 952 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-24 14:27Z): 40 strategies tracking from 7702 hypotheses (0 new this run); 21 graded scan reads, mean CLV -1.5%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 34, CLV +0.8%, t +0.9, last 30d +0.8% on 34; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 22, CLV +0.1%, t +0.2, last 30d +0.1% on 22; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft-alt: n 13, CLV +2.5%, t +2.2, last 30d +2.5% on 13; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 262, CLV -1.8%, t -7.2, last 30d -1.8% on 262
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 18, CLV +0.2%, t +0.4 (best of 57 tested; a lead to watch) | pair: role=fav + moveBeforePick=against n 8, CLV +0.2% (best of 18)
- ALL market=total: n 248, CLV -2.0%, t -7.9, last 30d -2.0% on 248
  > no conditional pocket found in current features (41 combos tested inside market=total) | pair: edgeBar=1-2x + timing=day n 10, CLV +0.1% (best of 15)
- ALL moveBeforePick=none: n 241, CLV -1.7%, t -5.7, last 30d -1.7% on 241
  > pocket: pattern=learned-ncaaf-spread inside moveBeforePick=none: n 21, CLV +1.1%, t +0.9 (best of 57 tested; a lead to watch) | pair: edgeBar=1-2x + timing=day n 8, CLV +0.7% (best of 13)
Observation: edge size is not yet predicting CLV (A -1.4% on 60, B -0.8% on 160, C -1.8% on 273).
  > last 50 graded reads: A -0.9% on 8, B -2.6% on 18, C -1.3% on 24 (order still wrong; diagnostic only)
  > pocket: travelEdge=more inside grade A: n 10, CLV +1.3%, t +0.6 (best of 33 tested; a lead to watch)
  > order holds inside timing=day: A +0.3% on 20, B -1.1% on 78, C -1.6% on 115 (10 of 39 features tested)
Why reads lost to the close (autopsy, post-pick; 337 of 493, cause known on 313): news-after-pick 18 (-4.3%), sharps-against-at-pick 4 (-2.9%), sharps-against-at-open 1 (-3.1%), bet-into-steam 8 (-2.3%), late-move 10 (-4.3%), number-off 272 (-3.4%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 78, right-but-unlucky 68, lucky-win 147, market-was-right 168; right-but-unlucky losses hurt most by close-margin, flipped-late, goalie-outlier (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 2513 price snapshots stored in the last 26h, latest 10-24 23:24Z, 642 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 131 of 165 graded reads since 10-19 18:00Z; 514 of 655 new reads stamped (Pinnacle at the pick)
- contextAtPick on 165 of 165 graded reads since 10-19 18:00Z; 655 of 655 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 63 of 165 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 465 of 473 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 26 of 493 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 60 of 165 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
