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
- 2026-10-31 refresh (health check): no fresh favourite-spread reads since 10-30 12:24Z (3 dog spreads, +0.1%); memory
  query unchanged (fav n 153, -1.7%, t -4.1; dog n 159, +0.3%). Mechanism revised: it is direction, not price. The
  autopsy split shows both sides paid the same price (fav -2.1%, dog -2.1% vs fair) but the market moved our way +2.4%
  on dog spreads (t 4.5) and only +0.4% on favourite spreads (t 1.0). DraftKings snapshots agree: at the same number
  DK's margin is split evenly by spread side (fav +2.2 to +2.6%, dog +2.2 to +2.6%, NBA/NCAAF/NFL, ~1,900 snaps), so
  there is no favourite price shade to avoid. A margin on the gate would not fix it; a side filter (or soft-dog) would.

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
- 2026-10-31: 16 reads, 4 graded (all NBA), CLV +1.5% (t 3.5). Snapshot check of the mechanism: DK moneyline dogs whose
  price beat Pinnacle's no-vig by 0.5%+ (30+ min before the start, close = Pinnacle's last snap within 45 min) scored
  +0.6% (n 31, t 1.5, halves +0.6/+0.7); at 1%+ +1.5% (n 10). DK's moneyline margin sits on favourites (next idea),
  which is why soft dogs exist on moneylines.

## Killed

### Express spread reads on the moneyline (2026-10-31, killed)
- Observation: spread and total reads pay ~2.1% vs fair at the pick (autopsy split, n 312 spreads, 391 totals), moneyline
  reads only ~0.8% (n 188). Idea: when a spread read fires, take the same side's moneyline instead.
- Test: 67 counted NBA/NFL/NCAAF spread reads with DK and Pinnacle moneyline snapshots within an hour of the pick and of
  the start. Same side on DK's moneyline: dogs +0.3% (n 39) vs the spread read +1.1%; favourites -2.4% (n 28, t -6.4)
  vs -1.5%. Worse on both sides. The direction is real on the moneyline too (Pinnacle ML moved +1.6% our way on the
  dog reads, t 2.7), but DK's moneyline margin eats it. Re-test only if best-US-book moneyline prices are stored at
  spread picks.
- Side fact found (DK vs Pinnacle no-vig at the same line, all October snaps): DK loads its moneyline margin on
  favourites (NBA +2.5% vs dogs +1.7%, NCAAF +2.7 vs +1.6, soccer/tennis +3.1 vs +1.7; NFL +2.2 vs +2.1); spreads and
  totals are split evenly by side (within 0.4%), so there is no over or under shade at DK to exploit (DK's under price
  beat Pinnacle's no-vig at the same total on almost no snapshots).

### Pinnacle follows DraftKings (2026-10-31, killed)
- Idea: when DK and Pinnacle disagree by 1.5%+ no-vig on a moneyline, Pinnacle moves toward DK by the start.
- Test (first disagreement per game, two-way moneylines only; soccer three-way excluded): Pinnacle moved +0.3% toward DK
  (n 177; NFL +1.4% n 17, NBA +0.7% n 47, tennis -0.4% n 53), while DK's side lost -1.5 to -2.3% to Pinnacle's close.
  Pinnacle is the truth here; the gate is right. Four variants tried today (this, margin by side, ML expression, under shade).


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
