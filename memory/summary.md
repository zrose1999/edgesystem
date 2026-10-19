# What EDGE is learning (2026-10-19 17:28Z)
Phase: data collection and learning. Samples are small and key features are still being added. Negative CLV is expected and logged to learn from; nothing here retires or prunes a rule.
204 graded reads counted, 391 logged. CLV is mean clvProb. Patterns move only by grade.py.

Early positive leads (one of many being tested; no acceleration):
- NHL pattern=learned-nhl-ml: n 11, CLV +0.8%, t +1.1, last 30d +0.8% on 11; grade.py needs 15 more graded full-bar picks (has 0), t >= 2.0
Early negative, still collecting (largest samples):
- ALL edgeBar=<0.5x: n 125, CLV -1.8%, t -6.3, last 30d -1.8% on 125
- ALL timing=early: n 116, CLV -2.0%, t -6.2, last 30d -2.0% on 116
- ALL market=total: n 102, CLV -2.4%, t -10.5, last 30d -2.4% on 102
- ALL moveBeforePick=none: n 92, CLV -2.2%, t -7.5, last 30d -2.2% on 92
- ALL wind=<10: n 79, CLV -1.6%, t -4.2, last 30d -1.6% on 79
Observation: edge size is not yet predicting CLV (A -2.4% on 18, B -1.8% on 60, C -1.9% on 126).

Other slices, last 30d (context, not leads):
- best: NFL venue=away: n 12, CLV +0.5%, t +0.4, last 30d +0.5% on 12; NCAAF role=dog: n 18, CLV +0.2%, t +0.1, last 30d +0.2% on 18
- worst: NFL role=over: n 17, CLV -3.4%, t -6.8, last 30d -3.4% on 17; NFL keyNumber=yes: n 15, CLV -3.1%, t -4.1, last 30d -3.1% on 15

Data gaps, free (building next):
- late-steam: needs pull.py to append fast-run snaps per row instead of overwriting lastSnap; no extra credits
- travel: needs previous venue joined to stats/venues.json (miles, time zones); free, code only
- sharp-divergence-at-pick: needs pull.py to stamp Pinnacle's price beside priceAtPick; only the open's is logged
Data gaps, waiting on a source:
- public-pct: needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack
- guru: needs an account list + reader (Reddit API free, X API paid); log account, number, time, result
sharpDivergence (at the open) on 13 of 204 graded reads; Pinnacle opens stored since 2026-10-14.
