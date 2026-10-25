# What EDGE is learning (2026-10-25 13:24Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
570 graded reads counted, 1055 logged. CLV is mean clvProb. Patterns move only by grade.py.
Scanner (scan.py, 10-25 11:11Z): 40 strategies tracking from 7736 hypotheses (0 new this run); 51 graded scan reads, mean CLV -0.3%. Shadow only; grade.py decides promotion.
Early positive leads (one of many being tested; no acceleration):
- NCAAF pattern=learned-ncaaf-spread: n 38, CLV +1.2%, t +1.3, last 30d +1.2% on 38; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
- ALL pattern=sharp-soft: n 23, CLV +1.3%, t +1.9, last 30d +1.3% on 23; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
- ALL pattern=sharp-soft-alt: n 14, CLV +2.4%, t +2.2, last 30d +2.4% on 14; grade.py needs 14 more graded full-bar picks (has 1), t >= 2.5
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 320, CLV -1.5%, t -6.0, last 30d -1.5% on 320
  > pocket: travelEdge=more inside edgeBar=<0.5x: n 48, CLV +0.7%, t +0.8 (best of 59 tested; a lead to watch) | pair: role=fav + rest=yes n 22, CLV +0.5% (best of 20)
- ALL moveBeforePick=none: n 283, CLV -1.4%, t -4.9, last 30d -1.4% on 283
  > pocket: pattern=learned-scan-nba-spread inside moveBeforePick=none: n 9, CLV +3.3%, t +1.6 (best of 60 tested; a lead to watch) | pair: role=fav + rest=yes n 13, CLV +1.1% (best of 14)
- ALL market=total: n 270, CLV -2.0%, t -7.7, last 30d -2.0% on 270
  > no conditional pocket found in current features (42 combos tested inside market=total) | pair: none (15 pair combos tested)
Observation: edge size is not yet predicting CLV (A -1.4% on 63, B -0.7% on 171, C -1.5% on 336).
  > last 50 graded reads: A -0.4% on 1, B +1.1% on 7, C +0.2% on 42 (order still wrong; diagnostic only)
  > pocket: travelEdge=more inside grade A: n 10, CLV +1.3%, t +0.6 (best of 33 tested; a lead to watch)
  > order holds inside restDays=1day: A +0.3% on 12, B -0.9% on 36, C -1.5% on 74 (6 of 40 features tested)
Why reads lost to the close (autopsy, post-pick; 390 of 570, cause known on 366): news-after-pick 30 (-4.4%), sharps-against-at-pick 7 (-3.5%), sharps-against-at-open 1 (-3.1%), bet-into-steam 8 (-2.3%), late-move 10 (-4.3%), number-off 310 (-3.4%), unknown 24 (-4.1%)
Process vs result: right-and-rewarded 97, right-but-unlucky 83, lucky-win 174, market-was-right 216; right-but-unlucky losses hurt most by close-margin, flipped-late, goalie-outlier (results are noise at this sample; CLV decides)
Data gaps, waiting on a source: public-pct (needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack); guru (needs an account list + reader (Reddit API free, X API paid); log account, number, time, result)
Coverage of added features (BREAKAGE if still 0 one health-check cycle after shipping):
- snaps: 2291 price snapshots stored in the last 26h, latest 10-25 13:24Z, 674 games with 2+ (late steam, since 10-19 18:15Z)
- pinAtPick on 155 of 230 graded reads since 10-19 18:00Z; 528 of 722 new reads stamped (Pinnacle at the pick)
- contextAtPick on 230 of 230 graded reads since 10-19 18:00Z; 722 of 722 new reads stamped (weather/injury/goalie as stamped)
- sharpDivergenceAtPick on 79 of 230 graded reads since 10-19 18:00Z (needs Pinnacle on the same line)
- daysRestHome on 542 of 550 graded NBA/NHL/NCAAF/NFL reads (schedules in stats/ (NFL from 2026-10-21))
- sharpDivergence on 29 of 570 graded reads since 10-14 00:00Z (Pinnacle at the open)
- pinMoveBeforePick on 74 of 230 graded reads since 10-19 18:15Z (needs a stored snap 30m-6h before the pick)
