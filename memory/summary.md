# What EDGE is learning (2026-10-24 22:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
474 graded reads counted, 931 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-24 14:27Z): 40 strategies tracking from 7702 hypotheses (0 new this run); 18 graded scan reads, mean CLV -1.1%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 32, CLV +0.8%, t +0.9, last 30d +0.8% on 32; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- NHL pattern=learned-nhl-ml: n 21, CLV +0.2%, t +0.5, last 30d +0.2% on 21; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft-alt: n 11, CLV +2.5%, t +1.9, last 30d +2.5% on 11; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 249, CLV -1.7%, t -6.6, last 30d -1.7% on 249
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 18, CLV +0.2%, t +0.4 (best of 56 tested; a lead to watch) | pair: venue=home + role=dog n 17, CLV +1.0% (best of 17)
- ALL market=total: n 240, CLV -1.9%, t -7.5, last 30d -1.9% on 240
  > no conditional pocket found in current features (41 combos tested inside market=total) | pair: edgeBar=1-2x + timing=day n 10, CLV +0.1% (best of 15)
- ALL moveBeforePick=none: n 230, CLV -1.5%, t -5.2, last 30d -1.5% on 230
  > pocket: pattern=learned-ncaaf-spread inside moveBeforePick=none: n 19, CLV +1.1%, t +0.9 (best of 57 tested; a lead to watch) | pair: venue=home + role=dog n 9, CLV +1.4% (best of 12)
Observation: edge size is not yet predicting CLV (A -1.4% on 59, B -0.7% on 155, C -1.7% on 260).
  > last 50 graded reads: A -1.5% on 7, B -1.7% on 19, C -0.3% on 24 (order still wrong; diagnostic only)
  > pocket: travelEdge=more inside grade A: n 9, CLV +1.0%, t +0.5 (best of 33 tested; a lead to watch)
  > order holds inside restDays=1day: A +0.5% on 11, B -0.8% on 32, C -1.3% on 45 (6 of 39 features tested)
Why reads lost to the close (autopsy, post-pick; 323 of 474, cause known on 299): news-after-pick 18 (-4.3%), sharps-against-at-pick 4 (-2.9%), sharps-against-at-open 1 (-3.1%), bet-into-steam 8 (-2.3%), late-move 7 (-3.8%), number-off 261 (-3.4%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 71, right-but-unlucky 66, lucky-win 142, market-was-right 160; right-but-unlucky losses hurt most by flipped-late, close-margin, goalie-outlier (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 2447 price snapshots stored in the last 26h, latest 10-24 22:54Z, 642 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 127 of 156 graded reads since 10-19 18:00Z; 513 of 652 new reads stamped (Pinnacle at the pick)
- contextAtPick on 156 of 156 graded reads since 10-19 18:00Z; 652 of 652 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 61 of 156 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 446 of 454 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 26 of 474 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 59 of 156 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
