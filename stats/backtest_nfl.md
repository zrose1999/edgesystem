# NFL backtest: sizing.md vs 2010-2026 closing lines

4471 games. Written by backtest.py on 2026-11-01. Data: nflverse (CC-BY 4.0).

| Event | Market | Games | Priced at close | Actual effect | sizing.md |
|---|---|---|---|---|---|
| backup for average starter | spread | 682 | +2.36 ± 0.14 | +3.36 ± 0.60 | 3 to 4 |
| backup for elite starter | spread | 148 | +4.79 ± 0.30 | +8.83 ± 1.27 | 6.5 to 8.5 |
| backup for weak starter | spread | 494 | +0.72 ± 0.18 | +0.92 ± 0.76 | 0.5 to 1.5 |
| backup QB (total) | total | 1324 | -1.61 ± 0.08 | -2.26 ± 0.45 | -3 to -1.5 |
| wind 15-19 | total | 274 | -0.84 ± 0.15 | -3.62 ± 0.86 | -3.5 to -2.5 |
| wind 20+ | total | 85 | -1.80 ± 0.26 | -2.18 ± 1.53 | -4 to -3 |

Against the close (does betting the event at the close win?)

| Bucket | Games | Cover / over rate | Mean vs close |
|---|---|---|---|
| backup for average starter (backup side vs spread) | 682 | 46.8% | -1.45 |
| backup for elite starter (backup side vs spread) | 148 | 47.6% | -0.97 |
| backup for weak starter (backup side vs spread) | 494 | 41.6% | -2.27 |
| wind 15-19 (over vs total) | 274 | 44.4% | -1.56 |
| wind 20+ (over vs total) | 85 | 47.6% | +0.01 |
