# What EDGE is learning (2026-10-25 02:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
540 graded reads counted, 1004 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-24 14:27Z): 40 strategies tracking from 7702 hypotheses (0 new this run); 37 graded scan reads, mean CLV -1.5%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 37, CLV +1.2%, t +1.3, last 30d +1.2% on 37; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 23, CLV +1.3%, t +1.9, last 30d +1.3% on 23; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
- ALL pattern=sharp-soft-alt: n 14, CLV +2.4%, t +2.2, last 30d +2.4% on 14; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 297, CLV -1.8%, t -7.2, last 30d -1.8% on 297
  > pocket: pattern=learned-ncaaf-spread inside edgeBar=<0.5x: n 23, CLV +0.2%, t +0.2 (best of 58 tested; a lead to watch) | pair: role=fav + moveBeforePick=against n 9, CLV +0.6% (best of 20)
- ALL moveBeforePick=none: n 265, CLV -1.6%, t -5.2, last 30d -1.6% on 265
  > pocket: pattern=learned-ncaaf-spread inside moveBeforePick=none: n 23, CLV +1.8%, t +1.5 (best of 59 tested; a lead to watch) | pair: venue=home + role=dog n 17, CLV +0.9% (best of 13)
- ALL market=total: n 262, CLV -2.0%, t -7.7, last 30d -2.0% on 262
  > no conditional pocket found in current features (42 combos tested inside market=total) | pair: none (15 pair combos tested)
Observation: edge size is not yet predicting CLV (A -1.4% on 62, B -0.6% on 168, C -1.8% on 310).
  > last 50 graded reads: A -0.8% on 5, B -1.6% on 12, C -1.7% on 33 (A > B > C holds; diagnostic only)
  > pocket: travelEdge=more inside grade A: n 10, CLV +1.3%, t +0.6 (best of 33 tested; a lead to watch)
  > order holds inside travelEdge=more: A +1.3% on 10, B +0.1% on 21, C -1.0% on 41 (9 of 40 features tested)
Why reads lost to the close (autopsy, post-pick; 369 of 540, cause known on 345): news-after-pick 30 (-4.0%), sharps-against-at-pick 7 (-3.5%), sharps-against-at-open 1 (-3.1%), bet-into-steam 8 (-2.3%), late-move 10 (-4.3%), number-off 289 (-3.5%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 82, right-but-unlucky 69, lucky-win 151, market-was-right 176; right-but-unlucky losses hurt most by close-margin, flipped-late, overtime (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 2354 price snapshots stored in the last 26h, latest 10-25 02:24Z, 657 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 148 of 203 graded reads since 10-19 18:00Z; 519 of 666 new reads stamped (Pinnacle at the pick)
- contextAtPick on 203 of 203 graded reads since 10-19 18:00Z; 666 of 666 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 76 of 203 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 512 of 520 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 29 of 540 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 68 of 203 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
