# NFL backtest: sizing.md vs 2018-2026 closing lines

2306 games. Written by backtest.py on 2026-10-14. Data: nflverse (CC-BY 4.0).

| Event | Market | Games | Priced at close | Actual effect | sizing.md |
|---|---|---|---|---|---|
| backup for average starter | spread | 407 | +2.82 ± 0.18 | +3.67 ± 0.77 | 3 to 4.5 |
| backup for elite starter | spread | 77 | +5.03 ± 0.42 | +9.26 ± 1.76 | 5 to 7 |
| backup for weak starter | spread | 254 | +1.00 ± 0.25 | +0.94 ± 1.05 | 1 to 2.5 |
| backup QB (total) | total | 738 | -2.01 ± 0.11 | -2.64 ± 0.60 | -3 to -1.5 |
| wind 15-19 | total | 128 | -1.29 ± 0.23 | -4.97 ± 1.26 | -2.5 to -1.5 |
| wind 20+ | total | 33 | -3.13 ± 0.45 | -3.94 ± 2.45 | -4 to -3 |

Against the close (does betting the event at the close win?)

| Bucket | Games | Cover / over rate | Mean vs close |
|---|---|---|---|
| backup for average starter (backup side vs spread) | 407 | 48.5% | -1.19 |
| backup for elite starter (backup side vs spread) | 77 | 45.5% | -1.85 |
| backup for weak starter (backup side vs spread) | 254 | 45.7% | -1.30 |
| wind 15-19 (over vs total) | 128 | 40.5% | -2.35 |
| wind 20+ (over vs total) | 33 | 51.5% | +0.20 |
