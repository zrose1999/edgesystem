# EDGE desk

The shared notebook. Every chat in the EDGE project, every scheduled task and every review reads this file and
STATE.md before doing anything, and writes back here before it ends. Nothing Zack says should live only in one chat.

- **STATE.md** (generated after every grade run): what is running, what is waiting, what changed. Never edit it.
- **This file** (written by hand, by Zack or any Claude session): standing rules, decisions, open threads.

How to write here:
- When Zack decides something, sets a rule, approves or declines a change, add one dated line under Decisions log
  (newest first), with where it came from (chat title, scheduled task, PR number). Say what was decided, not the debate.
- If it is a rule that should hold from now on, also add or edit a line under Standing rules.
- Anything started but not finished, or anything to check later, goes under Open threads with who owns it.
  Remove the line when it is done and log the outcome under Decisions log if it settled something.
- Keep each line to one or two sentences. Details belong in changelog.md, patterns.md or the PR.
- Pull before editing (`git pull --rebase`); a data job pushes about every 15 minutes.

## Standing rules
- 2026-10-21: North star (adopted by Zack): EDGE finds prices better than the sharp close and buys them as cheaply as possible. Seven fixed rules: (1) the sharp close is the truth: CLV against Pinnacle's close, print beside it, win rate never decides; (2) start from the market: a model earns weight only by what it adds to the no-vig price, out of sample; (3) cost is half the game: cheapest venue first (maker orders on exchanges), best book price otherwise; (4) one bar plus proof: promotion needs the bar and then a 15-pick confirmation run; (5) small signals stack: a signal proven to move the line feeds edge-stack; (6) nothing changes mid-period: new patterns and rule changes only at the weekly review, one at a time, with evidence; (7) size small and survive. Details in patterns.md ("North star").
- 2026-10-15: Patterns are judged on CLV only, never win rate. Promotion is grade.py's staged rule (15-19 graded full-bar picks t >= 2.5, 20+ t >= 2.0; learned models past the gate: 15+ at t >= 2.0). Retirement: 30+ picks, mean CLV <= 0.
- 2026-10-19: Learning phase. Early negative CLV means "still collecting", never a reason to retire, kill or prune a rule. Leads are not accelerated either.
- 2026-10-19: Claude fixes breakage, logging gaps and data paths directly (tested, own commit, changelog line). Strategy rules, bars, promotion, sizing and trading changes go in a pull request with CLV evidence; Zack merges. Larger new features also go in a PR (2026-10-20).
- 2026-10-14: Real-money Kalshi trading is controlled only by Zack from the site's switch panel (on/off, pause, balance, stop loss, take profit). No chat or task changes it.
- 2026-10-19: Single writer. Only the data job commits generated files: memory/log, memory/research.json, memory/summary.md, memory/hypotheses.md, stats/autopsy_box.json, stats/scan/, stats/modelcheck.json, STATE.md. Sessions restore them with `git checkout --` before committing.
- 2026-10-15: No hand-picked strategies. Patterns come from data (learner.py, scan.py, measured moves); a hand idea must be measured before it takes reads.
- 2026-10-15: The old Rose desk is a failure to learn from, not a template. Its history stays separate (ledger/history-rose-2026.json).
- Budget: stay on The Odds API 20,000-credit plan ($30/mo); no paid college QB/injury source; keep Claude usage lean.
- 2026-10-14: stats-model is off. Minimum expected moves for measured-move patterns are in patterns.md (Zack's call).
- 2026-10-21: Parked patterns (pull.PARKED) take no new reads; one comes back only as a new, measured pattern at a weekly review.
- 2026-10-21: Full-size live money only for confirmed signals: mirrors of official EDGE patterns, or Kalshi sources that cleared the bar and a 15-trade confirmation on paper CLV net of fees. Zack (same day): every other signal may trade as a small live test, 1 contract, maker order, $5 a day max (trading/config.json liveTest). The switch panel can narrow either, and only Zack's switch turns real money on.
- 2026-10-21: Every chat and scheduled task reads STATE.md and DESK.md first and records Zack's decisions here before it ends.

## Decisions log
- 2026-10-21: Zack switched live trading On (bankroll $35, sources official, stop loss $35, take profit 0). The first session stopped itself at once because take profit 0 was read as a limit; fixed (0 = no limit). Zack to switch off and on to start a fresh session. (chat: ideas tested this week)
- 2026-10-21: Zack approved small real-money tests on Kalshi (balance about $35) instead of paper only. Built as liveTest: 1 contract, maker orders, $5 a day. Waiting on Zack to switch trading On and set the panel's live sources to "official" (currently kalshi-sharp only). (chat: ideas tested this week)
- 2026-10-21: Zack: do everything the north star says, scrapping what conflicts. Done: reads priced at the best US book; Kalshi fill bug fixed, current order endpoint, live maker orders built (off), live money only for confirmed signals; stats-model, trend-fade, nba-stats-model, nba-model-fav, luck-reversion, early-number parked; discover.py retired. (chat: ideas tested this week)
- 2026-10-21: First live run with the overhaul (19:51Z) green: bestAtPick on all 4 new reads, 395 picks scored on Pinnacle's close, modelcheck written, 58 Kalshi maker orders resting. (chat: ideas tested this week)
- 2026-10-21: Zack adopted the north-star plan and had Claude build it: best price at pick, Pinnacle-close scoring, confirmation runs, move and model checks feeding edge-stack, fixed scanner roster, Kalshi maker paper book. (chat: ideas tested this week)
- 2026-10-21: Zack had the stale copies of patterns.md, pull.py and grade.py removed from the claude.ai project (the repo is the only copy; START-HERE.md points to it) and the old Rose "Weekly ledger audit" scheduled task turned off (paused, not deleted; it read the Rose Google Sheet). (chat: ideas tested this week)
- 2026-10-21: Zack merged PR #4 (shared desk) and asked Claude to merge PR #2 (weekly review proposals: one lessons.md entry) and PR #3 (results autopsy). Merged together after resolving changelog and memory.py overlaps; grade.py tested end to end. (chat: ideas tested this week)
- 2026-10-21: Zack wants every chat, scheduled task and automated run working from one shared, current picture. Added DESK.md, STATE.md (state.py) and CLAUDE.md. (chat: ideas tested this week)
- 2026-10-21: Strategy scanner approved and built: scan.py tests history every morning and tracks up to 40 survivors as shadow scan-* patterns, stake 0. NFL and MLB added the same day. (chat: strategy scanner)
- 2026-10-20: Results autopsy approved (market autopsy, box-score tags, memory labels). Built as PR #3. (chat: NBA data tracking systems)
- 2026-10-19: Living memory, Pinnacle at pick, late-steam snaps and travel features approved and shipped; daily health check and Tuesday weekly review scheduled. (chat: Project overview)
- 2026-10-19: cs2-elo moved to track-only on Kalshi; free closes and fewer near-game runs to save credits. (chat: Weekend operation maintenance)
- 2026-10-15: Learning engine replaces hand-written strategies; staged promotion rule approved. (chat: Betting app migration from Grok)

## Open threads
- 2026-10-21 Kalshi live orders refused: v2 /portfolio/events/orders answers insufficient_balance for 1-contract YES and NO orders on a $35.02 account (portfolio 0); legacy endpoint is retired (HTTP 410). Live ordering stops after 3 refusals a run, so nothing is spent. Waiting on Zack: is the $35 available to trade, and does a manual 1-contract buy work in the app? If manual works, check the API key's trading permission and sub-account, then the order fields. Owner: next chat or health check.
- Kalshi demo key: the KALSHI_DEMO_PRIVATE_KEY secret does not load (malformed PEM). Optional now: the first real 1-contract test orders also test the order code. Zack can paste a new demo key into that secret and run the "Kalshi self-test (demo)" workflow.
- Live trading (2026-10-21): the switch is Off; panel live sources still kalshi-sharp only and bankroll 49.19 vs a real balance of about $35. Once Zack sets sources to "official", bankroll to about $35 and switches On: unconfirmed signals trade 1-contract maker tests ($5 a day cap), confirmed signals full size. Owner: health check: after the first On run, check test orders post, fill or expire correctly and nothing exceeds the cap. Full-size live maker orders (liveOrderType "maker") wait on the maker-vs-taker comparison. ProphetX or another exchange is built only when a confirmed pattern needs it.
- 2026-10-21: the Netlify clock skipped the 19:39Z fast run (nothing ran 19:24Z to 19:51Z; Claude dispatched one by hand, green). Owner: health check: count gaps over 20 minutes in yesterday's runs and fix the clock if it repeats.
- Kalshi maker vs taker: compare in STATE.md (north-star checks) once 30+ maker fills have closes. Owner: weekly review. A live maker order is Zack's call from that comparison.
- First fixed-roster review day: Tuesday 2026-10-27. The scanner's queuedForReview and wouldLapseAtReview lists get applied that morning; the weekly review reports them.
- Best-price CLV (clvProbBest) starts on reads stamped after 2026-10-21 ~20Z. Owner: health check; BREAKAGE if bestAtPick is missing on new reads after one cycle.
- Autopsy (PR #3) is live from the next grade run: check its two summary lines appear and stats/autopsy_box.json fills. Owner: health check.
- Scanner's first live stamping: morning job 2026-10-22 11:07Z. Owner: health check. If no scan-* reads appear after that run, treat it as breakage.
- news-lag logged 119 rereads 2026-10-19 to 10-21 (injury feed flicker). Dedup keeps them out of the sample; owner: health check, watch whether it grows.
- learned-nfl-*: 2024 season backfill planned after the Odds API credit reset, then the gate decides again.
- Data gaps waiting on a source: public betting % and guru tracking (memory/summary.md lists what each needs).
