# Tennis: surface Elo vs Pinnacle (tennis_backtest.py)

Walk-forward Elo (overall + surface, 50/50), players with 20+ prior matches, completed matches only.
Slope: (result - market) on (model - market); above 0 means the model adds information. Best blend: weight on the model that minimises log loss (0 = trust the market).

| Group | Matches | Log loss market | Log loss model | Slope | se | Best blend | Bets (3+ pts) | Units | ROI |
|---|---|---|---|---|---|---|---|---|---|
