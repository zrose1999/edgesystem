# NFL backtest: sizing.md vs 2018-2026 closing lines

2335 games. Written by backtest.py on 2026-11-01. Data: nflverse (CC-BY 4.0).

| Event | Market | Games | Priced at close | Actual effect | sizing.md |
|---|---|---|---|---|---|
| backup for average starter | spread | 403 | +2.80 ± 0.18 | +3.48 ± 0.77 | 3 to 4 |
| backup for elite starter | spread | 84 | +4.98 ± 0.40 | +9.95 ± 1.69 | 6.5 to 8.5 |
| backup for weak starter | spread | 257 | +1.03 ± 0.25 | +0.99 ± 1.04 | 0.5 to 1.5 |
| backup QB (total) | total | 744 | -2.01 ± 0.11 | -2.72 ± 0.59 | -3 to -1.5 |
| wind 15-19 | total | 128 | -1.29 ± 0.23 | -4.97 ± 1.26 | -3.5 to -2.5 |
| wind 20+ | total | 33 | -3.13 ± 0.45 | -3.94 ± 2.45 | -4 to -3 |

Against the close (does betting the event at the close win?)

| Bucket | Games | Cover / over rate | Mean vs close |
|---|---|---|---|
| backup for average starter (backup side vs spread) | 403 | 48.7% | -1.11 |
| backup for elite starter (backup side vs spread) | 84 | 44.0% | -2.27 |
| backup for weak starter (backup side vs spread) | 257 | 45.6% | -1.27 |
| wind 15-19 (over vs total) | 128 | 40.5% | -2.35 |
| wind 20+ (over vs total) | 33 | 51.5% | +0.20 |
