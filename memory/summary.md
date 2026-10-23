# What EDGE is learning (2026-10-23 16:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
361 graded reads counted, 776 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-23 16:00Z): 40 strategies tracking from 7702 hypotheses (0 new this run); 6 graded scan reads, mean CLV -1.4%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 21, CLV +0.2%, t +0.5, last 30d +0.2% on 21; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 16, CLV +0.8%, t +1.4, last 30d +0.8% on 16; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 186, CLV -2.0%, t -7.6, last 30d -2.0% on 186
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 18, CLV +0.2%, t +0.4 (best of 53 tested; a lead to watch) | pair: none (16 pair combos tested)
- ALL market=total: n 185, CLV -1.9%, t -7.8, last 30d -1.9% on 185
  > no conditional pocket found in current features (41 combos tested inside market=total) | pair: none (15 pair combos tested)
- ALL timing=early: n 170, CLV -2.0%, t -6.2, last 30d -2.0% on 170
  > pocket: travelEdge=even inside timing=early: n 13, CLV +0.1%, t +0.1 (best of 46 tested; a lead to watch) | pair: role=under + moveBeforePick=for n 10, CLV +0.2% (best of 16)
Observation: edge size is not yet predicting CLV (A -1.7% on 51, B -1.1% on 119, C -2.0% on 191).
  > last 50 graded reads: A -1.5% on 7, B -2.0% on 14, C -0.8% on 29 (order still wrong; diagnostic only)
  > pocket: travelEdge=more inside grade A: n 8, CLV +1.3%, t +0.5 (best of 27 tested; a lead to watch)
  > order holds inside travelEdge=more: A +1.3% on 8, B -0.1% on 12, C -1.3% on 19 (7 of 36 features tested)
Why reads lost to the close (autopsy, post-pick; 258 of 361, cause known on 234): news-after-pick 16 (-4.9%), sharps-against-at-pick 3 (-2.4%), sharps-against-at-open 1 (-3.1%), bet-into-steam 5 (-2.0%), late-move 2 (-2.2%), number-off 207 (-3.3%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 53, right-but-unlucky 50, lucky-win 120, market-was-right 138; right-but-unlucky losses hurt most by flipped-late, close-margin, goalie-outlier (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1764 price snapshots stored in the last 26h, latest 10-23 16:54Z, 562 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 76 of 91 graded reads since 10-19 18:00Z; 397 of 467 new reads stamped (Pinnacle at the pick)
- contextAtPick on 91 of 91 graded reads since 10-19 18:00Z; 467 of 467 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 36 of 91 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 336 of 344 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 20 of 361 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 30 of 91 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
- travelMilesAway on 259 of 267 graded NBA/NHL/NCAAF reads (schedules + team_venues.json; neutral sites skipped)
