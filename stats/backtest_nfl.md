# NFL backtest: sizing.md vs 2010-2026 closing lines

4442 games. Written by backtest.py on 2026-10-14. Data: nflverse (CC-BY 4.0).

| Event | Market | Games | Priced at close | Actual effect | sizing.md |
|---|---|---|---|---|---|
| backup for average starter | spread | 686 | +2.37 ± 0.14 | +3.48 ± 0.60 | 3 to 4.5 |
| backup for elite starter | spread | 141 | +4.81 ± 0.30 | +8.41 ± 1.30 | 5 to 7 |
| backup for weak starter | spread | 491 | +0.70 ± 0.18 | +0.88 ± 0.77 | 1 to 2.5 |
| backup QB (total) | total | 1318 | -1.60 ± 0.08 | -2.21 ± 0.46 | -3 to -1.5 |
| wind 15-19 | total | 274 | -0.84 ± 0.15 | -3.62 ± 0.86 | -2.5 to -1.5 |
| wind 20+ | total | 85 | -1.80 ± 0.26 | -2.18 ± 1.53 | -4 to -3 |

Against the close (does betting the event at the close win?)

| Bucket | Games | Cover / over rate | Mean vs close |
|---|---|---|---|
| backup for average starter (backup side vs spread) | 686 | 46.7% | -1.50 |
| backup for elite starter (backup side vs spread) | 141 | 48.6% | -0.68 |
| backup for weak starter (backup side vs spread) | 491 | 41.7% | -2.29 |
| wind 15-19 (over vs total) | 274 | 44.4% | -1.56 |
| wind 20+ (over vs total) | 85 | 47.6% | +0.01 |
