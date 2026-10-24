# What EDGE is learning (2026-10-24 12:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
410 graded reads counted, 866 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-24 11:10Z): 40 strategies tracking from 7702 hypotheses (0 new this run); 11 graded scan reads, mean CLV -0.6%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 21, CLV +0.2%, t +0.5, last 30d +0.2% on 21; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 18, CLV +1.2%, t +1.7, last 30d +1.2% on 18; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
- ALL pattern=sharp-soft-alt: n 8, CLV +4.0%, t +2.8, last 30d +4.0% on 8; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.5
Early negative, still collecting (largest samples):
- ALL market=total: n 208, CLV -1.8%, t -6.9, last 30d -1.8% on 208
  > no conditional pocket found in current features (41 combos tested inside market=total) | pair: none (15 pair combos tested)
- ALL edgeBar=<0.5x: n 205, CLV -1.8%, t -7.1, last 30d -1.8% on 205
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 18, CLV +0.2%, t +0.4 (best of 54 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 27, CLV +0.0% (best of 16)
- ALL timing=day: n 195, CLV -1.1%, t -4.0, last 30d -1.1% on 195
  > pocket: sharpDivPick=pin-for inside timing=day: n 9, CLV +2.4%, t +1.4 (best of 55 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 12, CLV +1.6% (best of 16)
Observation: edge size is not yet predicting CLV (A -1.5% on 57, B -1.1% on 142, C -1.8% on 211).
  > last 50 graded reads: A -2.4% on 5, B -1.5% on 21, C +0.3% on 24 (order still wrong; diagnostic only)
  > pocket: travelEdge=more inside grade A: n 9, CLV +1.0%, t +0.5 (best of 30 tested; a lead to watch)
  > order holds inside restEdge=less: A -1.0% on 12, B -1.1% on 16, C -3.3% on 17 (7 of 38 features tested)
Why reads lost to the close (autopsy, post-pick; 287 of 410, cause known on 263): news-after-pick 15 (-4.7%), sharps-against-at-pick 4 (-2.9%), sharps-against-at-open 1 (-3.1%), bet-into-steam 7 (-2.5%), late-move 4 (-4.5%), number-off 232 (-3.4%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 63, right-but-unlucky 60, lucky-win 133, market-was-right 153; right-but-unlucky losses hurt most by flipped-late, close-margin, goalie-outlier (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1954 price snapshots stored in the last 26h, latest 10-24 12:54Z, 632 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 109 of 134 graded reads since 10-19 18:00Z; 480 of 592 new reads stamped (Pinnacle at the pick)
- contextAtPick on 134 of 134 graded reads since 10-19 18:00Z; 592 of 592 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 47 of 134 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 384 of 392 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 24 of 410 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 50 of 134 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
