# Rose history audit (2026-10-14)

Source: Master Results Log (Active), 263 rows, Apr 30 to Sep 15 2026 (most dated rows Apr 30 to Jul 6), plus an 83-row Shadow Log. Saved as ledger/history-rose-2026.json. History only: it never counts toward EDGE promotion.

## Data quality
- 235 graded bets (27 voids). 142 have a closing price.
- 68 of those 142 closes (48%) equal the price taken, which is unlikely for real closes. Treat them as missing. 74 closes actually moved.
- No-vig closes were not recorded, so CLV here is single-side implied probability (close minus taken).

## Overall
235 bets, 120-114-1, -18.4 units flat (-7.8% ROI). Mean CLV +0.08pp (t 0.3). The old desk did not beat the market overall.

## By bucket (flat 1 unit; CLV on closes that moved)
| Bucket | Bets | Record | Units | ROI | CLV (moved closes) |
|---|---|---|---|---|---|
| MLB ML fav -110 to -139 | 37 | 25-12 | +7.5 | +20% | +1.50pp, 9 of 11 beat |
| NBA spreads | 28 | 15-13 | +0.7 | +2% | +1.06pp, 4 of 4 beat |
| MLB ML fav -140 to -179 | 41 | 24-17 | -1.5 | -4% | -0.38pp |
| MLB ML fav -180 or shorter | 21 | 13-8 | -1.6 | -8% | -2.11pp |
| MLB ML underdogs | 18 | 4-14 | -9.4 | -52% | +1.68pp (4 closes) |
| MLB totals (mostly unders) | 28 | 12-16 | -5.1 | -18% | +0.05pp |
| NHL totals | 18 | 9-9 | -1.3 | -7% | +2.55pp (5 closes) |
| NHL moneyline | 15 | 5-10 | -6.7 | -45% | -0.85pp |
| Soccer totals | 5 | 0-5 | -5.0 | -100% | -0.58pp |

## Out-of-sample check
The old Pattern Engine chose its core buckets on 2026-06-23 from bets before that date. After it:
- MLB ML fav -100..-139: 2-3, -1.5 units (34 bets before: 24-10, +9.0).
- All bets: 15-22, -9.8 units.
The best-looking bucket did not hold up in the small sample after it was chosen.

## Verdict
No bucket meets EDGE's bar (30 graded bets with real closes, mean CLV above 0, t at least 1.5). Candidates worth a live test, not promotion:
- MLB ML favourites -110 to -139: best record and positive CLV on the closes that moved, but chosen in hindsight and failed its short out-of-sample stretch. MLB season ends this month; revisit in April.
- NBA spreads: positive CLV on every moved close, but only 4. NBA season is starting; worth tracking.
Clear negatives, consistent with the old rules: MLB ML underdogs, NHL moneylines, soccer totals.
