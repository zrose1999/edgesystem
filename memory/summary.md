# What EDGE is learning (2026-10-24 18:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
439 graded reads counted, 895 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-24 14:27Z): 40 strategies tracking from 7702 hypotheses (0 new this run); 14 graded scan reads, mean CLV -0.8%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 21, CLV +0.2%, t +0.5, last 30d +0.2% on 21; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft-alt: n 10, CLV +3.3%, t +2.7, last 30d +3.3% on 10; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 225, CLV -1.9%, t -7.4, last 30d -1.9% on 225
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 18, CLV +0.2%, t +0.4 (best of 54 tested; a lead to watch) | pair: role=dog + moveBeforePick=none n 29, CLV +0.2% (best of 16)
- ALL market=total: n 224, CLV -1.9%, t -7.3, last 30d -1.9% on 224
  > no conditional pocket found in current features (41 combos tested inside market=total) | pair: edgeBar=1-2x + timing=day n 10, CLV +0.1% (best of 15)
- ALL moveBeforePick=none: n 211, CLV -1.7%, t -5.8, last 30d -1.7% on 211
  > pocket: travelEdge=more inside moveBeforePick=none: n 19, CLV +0.9%, t +0.8 (best of 57 tested; a lead to watch) | pair: edgeBar=1-2x + timing=day n 8, CLV +0.7% (best of 12)
Observation: edge size is not yet predicting CLV (A -1.5% on 58, B -0.9% on 149, C -1.9% on 232).
  > last 50 graded reads: A -1.7% on 6, B -1.9% on 20, C -0.7% on 24 (order still wrong; diagnostic only)
  > pocket: travelEdge=more inside grade A: n 9, CLV +1.0%, t +0.5 (best of 31 tested; a lead to watch)
  > order holds inside restEdge=less: A -1.0% on 12, B -1.1% on 16, C -3.3% on 17 (8 of 38 features tested)
Why reads lost to the close (autopsy, post-pick; 302 of 439, cause known on 278): news-after-pick 16 (-4.5%), sharps-against-at-pick 4 (-2.9%), sharps-against-at-open 1 (-3.1%), bet-into-steam 7 (-2.5%), late-move 4 (-4.5%), number-off 246 (-3.5%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 63, right-but-unlucky 61, lucky-win 134, market-was-right 153; right-but-unlucky losses hurt most by flipped-late, close-margin, goalie-outlier (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 2458 price snapshots stored in the last 26h, latest 10-24 18:24Z, 634 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 116 of 143 graded reads since 10-19 18:00Z; 494 of 625 new reads stamped (Pinnacle at the pick)
- contextAtPick on 143 of 143 graded reads since 10-19 18:00Z; 625 of 625 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 51 of 143 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 411 of 419 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 26 of 439 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 52 of 143 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
- travelMilesAway on 332 of 342 graded NBA/NHL/NCAAF reads (schedules + team_venues.json; neutral sites skipped)
