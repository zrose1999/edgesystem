# What has worked (2026-10-19 17:19Z)
204 graded reads counted, 391 logged. CLV is mean clvProb. Leads and flags only; patterns move by grade.py.

Positive leads (patterns, 8+ graded reads, CLV > 0):
- NHL pattern=learned-nhl-ml: n 11, CLV +0.8%, t +1.1, last 30d +0.8% on 11; promotion needs 15 more graded full-bar picks (has 0) and t >= 2.0, fast track
Kill candidates (n 30+, CLV <= 0; FLAGGED, not retired):
- ALL market=total: n 102, CLV -2.4%, t -10.5, last 30d -2.4% on 102
- NCAAF role=under: n 40, CLV -2.8%, t -9.9, last 30d -2.8% on 40
- ALL role=under: n 65, CLV -2.3%, t -7.8, last 30d -2.3% on 65
- ALL moveBeforePick=none: n 92, CLV -2.2%, t -7.5, last 30d -2.2% on 92
Trending toward a kill (n 15+, t <= -2):
- NFL role=over: n 17, CLV -3.4%, t -6.8, last 30d -3.4% on 17
- NCAAF timing=day: n 25, CLV -2.9%, t -6.6, last 30d -2.9% on 25
- NCAAF wind=10-15: n 20, CLV -2.8%, t -5.1, last 30d -2.8% on 20
GRADE ORDER INVERTED: A -2.4% on 18, B -1.8% on 60, C -1.9% on 126. A should beat B beat C; edge size is not predicting the close.

Other slices, last 30d (context, not leads):
- best: NFL venue=away: n 12, CLV +0.5%, t +0.4, last 30d +0.5% on 12; NCAAF role=dog: n 18, CLV +0.2%, t +0.1, last 30d +0.2% on 18
- worst: NFL role=over: n 17, CLV -3.4%, t -6.8, last 30d -3.4% on 17; NFL keyNumber=yes: n 15, CLV -3.1%, t -4.1, last 30d -3.1% on 15

Data gaps (not collected yet):
- public-pct: needs a betting-splits source (Action Network/VSiN or a paid API); none free in the stack
- late-steam: needs pull.py to append fast-run snaps per row instead of overwriting lastSnap; no extra credits
- travel: needs previous venue joined to stats/venues.json (miles, time zones); free, code only
- guru: needs an account list + reader (Reddit API free, X API paid); log account, number, time, result
- sharp-divergence-at-pick: needs pull.py to stamp Pinnacle's price beside priceAtPick; only the open's is logged
sharpDivergence (at the open) on 13 of 204 graded reads; Pinnacle opens stored since 2026-10-14.
