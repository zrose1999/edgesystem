# EDGE ideas ledger

Claude's own strategy ideas, drawn from the data rather than asked for (Zack 2026-10-30: "I want you to come up with
ideas for winning strategies 100% on your own... it should come to you out of the data"). Every chat and the daily
health check add here; the weekly review takes the strongest live idea and proposes it (one change at a time, CLV only).

How an idea is written: the observation that suggested it, the mechanism (why the market would leave this edge), the
test (data, sample, CLV, t, both halves), what would kill it, and status: testing, lead, proposed, killed.
Killed ideas stay listed so nobody re-tests them blind. Never build a feature from a post-pick field.

## Leads

### 1. Spread favourites pay a tax (2026-10-30, lead, for the weekly review)
- Observation: EDGE's counted reads on spread favourites lose -1.7% CLV (n 153, t -4.1); spread underdogs are flat (+0.1%, n 153).
  It holds in every sport (NFL -3.3% n 41, NCAAF -1.4% n 48, NBA -1.0% n 64), in both halves (-2.1% n 99, -1.0% n 54),
  for parked (-2.5%) and live patterns (-1.1%), and even inside sharp-soft (favourite spreads -1.6% n 6, dog spreads +2.2% n 9).
  Moneyline favourites do not show it (+0.1%, n 73).
- Mechanism: public money goes to favourites against the spread, so books shade the favourite's spread price and number.
  A model that likes the favourite buys that shade; the close removes part of it.
- Test of the other side: soft-book snapshots where the price beat Pinnacle's no-vig: underdogs +1.0% (n 42, t 2.3),
  favourites +0.1% (n 17).
- Kill it if: fresh favourite-spread reads after 10-30 come in at or above the dog-spread mean over 30+ reads.
- Possible change (Zack decides at a weekly review): spread favourites need the Pinnacle gate plus a margin, or a
  shadow pattern "soft-dog" that takes soft-book underdog prices at or better than Pinnacle's fair.

### 2. Away teams travelling east (2026-10-30, lead, waits on the NFL backfill)
- NFL history 2015-2026 (PR #8): home moneyline when the away team travels east ROI -11.1% at the close (n 847, t -3.2,
  both halves). A result, not a move; the CLV test needs the 2020-2024 opening lines (after the credit reset).
- Mechanism (cross-sport): findings.py's strongest theme is travel edge (+3.6% vs -1.0%, n 35); the market prices rest
  days but probably not distance and body clock.

## Experiments (live shadow patterns, stake 0)

### soft-dog (launched 2026-10-30, from lead 1)
- sharp.py stamps the underdog side when a soft book's same-line price is at least 0.5% better than Pinnacle's no-vig
  fair (grade A at 1.5%), two-way spreads and moneylines, every sport sharp.py scans. Shadow, stake 0, Pinnacle gate as usual.
- Launch check: dry run on the live ledger 10-30 20:30Z would stamp 7 (NFL 1, NCAAF 6), edges +0.6% to +0.9%.
- Judge on CLV at 30 graded: holds if mean CLV > 0 with t >= 1.5 in both halves; tweak the floor (SOFT_DOG_MIN) once
  if the 0.5-1% bucket loses while 1%+ wins; kill if mean CLV <= 0 at 50 graded.

## Killed

### Steam chase at run cadence (2026-10-30, killed)
- Idea: after Pinnacle moves 1.5+ points of no-vig, take the soft book before it follows.
- Test (snapshots 10-19 to 10-30, two-way markets): the soft book had already matched by the next snapshot in 221 of
  232 moves (CLV -1.9% when taking it anyway); only 11 stale prices (+1.0%). Needs minute-level polling, which the credit
  budget cannot buy.

### Pinnacle momentum (2026-10-30, killed)
- Idea: a Pinnacle move keeps going to the close. Test: -0.17% after a 1.5-point move (n 232, t -1.1). No momentum.

### Systematic drift by side (2026-10-30, killed for now)
- Idea: favourites or overs firm into the close every day. Test: Pinnacle no-vig drift first to last snapshot was within
  half a point of zero in every sport (largest: NCAAF spread favourites -0.3%, n 36, t -2.1). Re-test with a full season.
