# Soccer history (research data, not read by the live desk)

- `fd_<league>_<season>.csv`: football-data.co.uk results with Pinnacle early (PSH/PSD/PSA, P>2.5) and closing
  (PSCH..., PC>2.5) prices, plus Bet365, market average and max. E0 EPL, SP1 La Liga, D1 Bundesliga, I1 Serie A,
  F1 Ligue 1. Seasons 2022-23 to 2025-26.
- `understat_<league>_<year>.json`: Understat match list with goals and xG per team (year = season start).

Used for stats/backtest_soccer_xg.md and the lineup study in changelog.md (2026-10-14).
EDGE's own soccer history (every book's open, last pre-start and close price, plus scores) builds in
ledger/archive/<month>/<league>.jsonl from 2026-10-14 on.
