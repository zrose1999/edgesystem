# What EDGE is learning (2026-10-23 01:54Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
353 graded reads counted, 749 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-22 15:53Z): 40 strategies tracking from 7678 hypotheses (40 new this run); 6 graded scan reads, mean CLV -1.4%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 19, CLV +0.2%, t +0.4, last 30d +0.2% on 19; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 16, CLV +0.8%, t +1.4, last 30d +0.8% on 16; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 182, CLV -2.0%, t -7.6, last 30d -2.0% on 182
  > pocket: pattern=learned-nhl-ml inside edgeBar=<0.5x: n 16, CLV +0.2%, t +0.3 (best of 52 tested; a lead to watch) | pair: none (16 pair combos tested)
- ALL market=total: n 182, CLV -2.0%, t -7.8, last 30d -2.0% on 182
  > no conditional pocket found in current features (40 combos tested inside market=total) | pair: none (15 pair combos tested)
- ALL timing=early: n 168, CLV -2.0%, t -6.2, last 30d -2.0% on 168
  > pocket: travelEdge=even inside timing=early: n 13, CLV +0.1%, t +0.1 (best of 46 tested; a lead to watch) | pair: role=under + moveBeforePick=for n 10, CLV +0.2% (best of 16)
Observation: edge size is not yet predicting CLV (A -1.7% on 49, B -1.2% on 117, C -2.0% on 187).
  > last 50 graded reads: A -1.5% on 5, B -1.7% on 17, C -0.9% on 28 (order still wrong; diagnostic only)
  > pocket: travelEdge=more inside grade A: n 8, CLV +1.3%, t +0.5 (best of 27 tested; a lead to watch)
  > order holds inside tzShift=none: A +1.0% on 11, B -0.4% on 14, C -1.8% on 50 (7 of 33 features tested)
Why reads lost to the close (autopsy, post-pick; 252 of 353, cause known on 228): news-after-pick 15 (-4.7%), sharps-against-at-pick 2 (-2.3%), sharps-against-at-open 1 (-3.1%), bet-into-steam 5 (-2.0%), late-move 2 (-2.2%), number-off 203 (-3.3%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 48, right-but-unlucky 37, lucky-win 102, market-was-right 125; right-but-unlucky losses hurt most by flipped-late, close-margin, overtime (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 1667 price snapshots stored in the last 26h, latest 10-23 01:54Z, 515 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 72 of 83 graded reads since 10-19 18:00Z; 379 of 434 new reads stamped (Pinnacle at the pick)
- contextAtPick on 83 of 83 graded reads since 10-19 18:00Z; 434 of 434 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 33 of 83 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 328 of 336 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 20 of 353 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 28 of 83 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
- travelMilesAway on 251 of 259 graded NBA/NHL/NCAAF reads (schedules + team_venues.json; neutral sites skipped)
