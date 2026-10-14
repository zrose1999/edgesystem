# Soccer expected-goals model vs Pinnacle (2026-10-14)

Data: Understat match xG and football-data.co.uk Pinnacle early (PSH/PSD/PSA, P>2.5) and closing (PSCH..., PC>2.5) prices.
EPL, La Liga, Bundesliga, Serie A, Ligue 1, 2014-15 to 2025-26. 19,631 matches with both prices (over/under 11,259).
Model: exponentially weighted team attack and defence from xG (half-life 15 matches, 30% pull to average each summer),
Poisson scorelines. Margin removed with Shin's method.

| Test | n | Slope | se | t |
|---|---|---|---|---|
| Home win: early-to-close move vs model gap from early | 19,631 | +0.028 | 0.003 | +10.6 |
| Away win: same | 19,631 | +0.023 | 0.003 | +8.6 |
| Home win: result minus close vs model gap from close | 19,631 | -0.031 | 0.040 | -0.8 |
| Over 2.5: move vs model gap | 11,259 | +0.009 | 0.005 | +1.8 |
| Over 2.5: result minus close vs model gap from close | 11,259 | -0.016 | 0.070 | -0.2 |

Every league and both halves (2014-19, 2020-26) show the same small home-win slope (0.018 to 0.040).

Verdict: the market already prices xG. A 10-point model gap predicts a 0.3-point move toward the model, far below any
bar, and nothing is left at the close. No soccer model pattern. Soccer edges for EDGE come from price gaps (sharp-soft,
Kalshi vs Pinnacle), and later possibly lineup news, which this data cannot test.
