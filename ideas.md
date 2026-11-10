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
- 2026-11-01 refresh (health check): holding on fresh reads. Since 10-30: favourite spreads -1.0% (n 30, t -1.1), dog
  spreads +2.6% (n 18, t 1.9). All counted: favourites -1.6% (n 182, t -4.3), dogs +0.4% (n 170, t 0.8).
- 2026-11-02 refresh (health check): all counted: favourites -1.6% (n 190, t -4.3), dogs +0.2% (n 184, t 0.4). Since
  10-30 12Z only 3 favourite spreads (+2.7%) and 12 dog spreads (+0.2%): too few fresh reads to move it either way.
- 2026-11-03 refresh (health check): all counted: favourites -1.5% (n 192, t -4.2; memory query same), dogs +0.2%
  (n 185, t 0.4). Since 10-30 12Z: 4 favourite spreads (+2.6%), 12 dog spreads (+0.2%). Still too few fresh reads.
- 2026-11-07 refresh (health check, memory/log counted NFL/NCAAF/NBA): all counted favourites -1.5% (n 197,
  t -4.3), dogs +0.3% (n 193, t 0.7). Since 10-30: favourites +0.8% (n 10, t 0.8), dogs +1.8% (n 20, t 1.7): the
  gap is in the same direction on fresh reads but favourites are no longer losing; 20 more fresh favourite spreads to the kill test.

### 2. Away teams travelling east (2026-10-30, lead, waits on the NFL backfill)
- NFL history 2015-2026 (PR #8): home moneyline when the away team travels east ROI -11.1% at the close (n 847, t -3.2,
  both halves). A result, not a move; the CLV test needs the 2020-2024 opening lines (after the credit reset).
- Mechanism (cross-sport): findings.py's strongest theme is travel edge (+3.6% vs -1.0%, n 35); the market prices rest
  days but probably not distance and body clock.
- 2026-11-01 correction (health check): findings.py's travel labels were inverted. memory.py's travelEdge "more" means
  OUR side travelled 200+ miles further; findings.py printed it as "the opponent travelled further". So EDGE's read-level
  schedule theme says reads on the side that travelled further beat the close (+1.1% vs -0.9%, n 110; with 2+ days rest
  +5.7%, n 21), the opposite of this lead's mechanism. Market-wide check on Pinnacle snapshots (first snap to the last
  within 3h of the start, h2h, NBA/NHL/NCAAF/NFL): Pinnacle moved toward the side that travelled further by only +0.26%
  (n 186, t 1.1; NBA with 2+ days rest +1.2%, n 18). So the read-level travel findings are mostly which patterns took
  those spots, not a market-wide mispricing. NFL east-travel ROI stays a result-only lead; the backfill (run 11-01)
  gives the scanner its move test.

### 3. Road moneylines firm into the close, NHL and NBA (2026-11-01, lead, testing)
- Observation: on Pinnacle snapshots, the home side's no-vig moneyline fell from the first snapshot to the last one
  within 3h of the start: NHL -0.66% (n 65, t -2.6, halves -0.95/-0.37, home favourites and home dogs alike), NBA -0.60%
  (n 62, t -1.3); together -0.63% (n 127, t -2.4, both halves). Not in NCAAF (+0.09%, n 106) or NFL (n 16). Spreads
  show the same sign but weaker (NBA -0.59%, n 62, t -0.9). findings.py agrees on EDGE's own reads: moneylines on the
  away side +0.5% vs -0.8% (n 116, t 3.6, new 11-01).
- Mechanism: early pro-league moneylines are bet by local and recreational money that leans home; sharper money that
  arrives near the start, with confirmed goalies and lineups, has no home lean, so the close drifts toward the road side.
- Living memory: away moneyline reads +0.5% (n 116, t 1.8); NHL away -0.2% (n 51), NHL home -1.2% (n 14, 1 beat the
  close); NBA away +1.6% (n 9), NBA home -0.0% (n 45). Partial support: the home side loses, the road side is only flat.
- Variants tried this run: ~50 (24 travel splits, ~30 home-drift splits by sport, market and favourite/dog). At that
  count a t of -2.4 is borderline, so no shadow pattern yet.
- 2026-11-02: not re-run (snapshots grew ~15% since 11-01; waits for the double).
- Test next: re-run on the snapshots when they double (late November); if the NHL+NBA drift holds at t <= -2.5 in both
  halves, launch a shadow pattern (road side of NHL/NBA moneylines when a soft price is at or better than Pinnacle's
  fair, stamped early). Kill it if the combined drift is above -0.3% on 250+ games.

### 4. NBA totals drift down before the final hour (2026-11-02, lead, testing)
- Observation: on Pinnacle snapshots, NBA totals taken 6h+ before tip fell -0.61 points by the final hour (n 73, t -2.3;
  halves -0.69 and -0.53, t -1.7 and -1.6). From 3-6h out the drift is only -0.12 (n 69, t -1.2), so it happens while
  injury reports settle. NHL (+0.01, n 59) and NFL (0.00, n 27) show none; NCAAF rose +0.31 (n 78, t 2.2) but only in
  the first half (+0.65 vs +0.06).
- Mechanism: early NBA totals price full rosters. Late scratches and rest days remove scorers more often than surprise
  returns add them, so news skews the total down; the line pays for it only once the reports are out.
- Living memory agrees on direction: EDGE's counted NBA unders stamped 6h+ early gained +1.6% of market move (n 39,
  t 1.9), overs -0.2% (n 53); all NBA over reads 6h+ (gated included) moved -0.9% (n 113, t -1.9). Overs lose -2.3%
  CLV early (n 53, t -2.8), unders -0.6% (n 39).
- Tradeable? Not at a US book: a soft-book under taken 6h+ early still lost -1.3% to Pinnacle's final-hour no-vig
  (n 73, t -2.3; slope 0.021 per point), because the ~2.5% vig is bigger than the ~1.2% move. The early over lost
  -3.5% (n 73, t -6.2). Only 3 early unders passed the Pinnacle gate. It could pay where the cost is low (Kalshi maker
  orders, which kalshi-sharp-alt already places on NBA totals at Pinnacle's fair), or as a filter: no NBA overs 6h+ out.
- Variants tried: ~40 (totals drift by sport and half, NCAAF bands and Saturday, NBA windows, size, book, CLV by side).
- 2026-11-06 (health check): the 6h+ drift concentrates in games with an early Pinnacle spread under 8 points
  (-0.82, n 54, t -2.9) vs 8+ (+0.08, n 19); one post-hoc split, not a new lead.
- Test next: re-run when NBA snapshots reach 150 games; if the 6h+ drift holds at t <= -2.5 in both halves, propose
  for the weekly review either a shadow over-filter on learned-nba-total or a Kalshi maker under test. Kill it if the
  drift is above -0.3 points on 150+ games.

### 5. Rested road teams firm into the close, NBA (2026-11-05, lead, testing)
- Observation: on Pinnacle snapshots (first snap 6h+ before tip to last snap within 2h), when the away team had more
  days of rest than the home team, Pinnacle's no-vig moved toward the away side: moneyline home drift -2.9% (n 17,
  t -2.3, halves -0.9/-4.7), spread -3.7% (same games, n 17, t -2.6, halves -2.0/-5.3). Home more rested: +0.1% (n 20);
  even rest -0.3% (n 65); all NBA -0.7% (n 102, t -1.9, the lead-3 road drift). findings.py agrees on EDGE's reads
  (NBA, our side 2+ days rest and travelled 500-1500 miles +5.6% n 25, holding since 11-05; more rested and did not
  travel -2.5% n 44).
- Mechanism: openers price home court plus a generic rest term; the rested road side's edge shows up late, as the
  tired home team's minutes limits and rest days are announced and sharper money arrives, so the close moves road.
- Tradeable? Away moneyline at the soft book on the first 6h+ snapshot vs Pinnacle's final no-vig: +0.8% (n 25, t 0.8;
  Pinnacle's own early price +0.9%, fair move +2.2% t 2.3). Positive after vig but not yet significant.
- Living memory (memory.py query --sport NBA --feature restEdge=more --feature venue=away): n 45, +0.2% CLV, t 0.2,
  27-18: EDGE's own rested-road reads do not capture the move yet (stamped late or at worse prices).
- Overlap: scan-nba-spread-away-restedgeawaymore-1e501d already tests the spread side (+3.0% n 9); no moneyline twin
  and no early-timing condition. rest-spot covers only back-to-backs.
- Variants tried: ~30 (rest edge by direction, b2b by side, h2h vs spread, soft vs Pinnacle entry, NCAAF has 2 games).
- Test next: re-run when NBA snapshots with rest reach 40 away-more-rested games; if the soft-book early away price
  holds +0.5%+ at t >= 2 in both halves, launch a shadow h2h pattern (away more rested, stamped 6h+ early). Kill if
  the fair move is under +0.5% on 40+ games.

### 6. Caesars is a slow book on NBA moneylines (2026-11-07, lead, testing)
- Observation: findings.py flagged "the price came from Caesars" as a new condition today. On counted NFL/NCAAF/NBA
  reads with Pinnacle at the pick (memory/log, n 280), reads whose best price was at Caesars beat the Pinnacle close
  +1.7% (n 28, t 2.1, 22 games), and +1.8% (t 2.2) after holding the price gap vs Pinnacle's fair equal (CLV regressed
  on gap, slope 0.38). Halves: +0.5% (n 14, t 0.7) then +3.1% (n 14, t 2.2). DraftKings -0.5% (n 107), FanDuel -0.2%
  (n 103), BetMGM -0.8% (n 42; -0.3% gap-adjusted, halves -2.2% then +1.7%, so no stable BetMGM effect on this sample).
- Mechanism: Caesars (added to pull.BOOKS 10-28) moves its NBA moneylines later than DK/FD and Pinnacle, so when it is
  the best price the read is often taking a stale number that the close then removes from it. Half of the Caesars reads are
  NBA h2h and 11 of 28 are soft-dog, so it may be soft-dog's edge showing up through the book that most often lags.
- Living memory: memory.py query --feature bookAtPick=Caesars n 22, +1.0%, t 1.6; NBA h2h n 3, +1.3%.
- Variants tried: 4 (2 books x raw and gap-adjusted).
- Test next: at 50 Caesars-priced counted reads, split by soft-dog vs everything else; if non-soft-dog Caesars reads stay
  +1%+ at t >= 2 in both halves, it is a book effect and the weekly review can weigh a book-aware bar for sharp-soft.
  Kill if the gap-adjusted mean falls under +0.5% on 50.
- Refresh 2026-11-09 (health check; counted NFL/NCAAF/NBA reads with Pinnacle at the pick, vs Pinnacle close): Caesars
  +1.6% (n 39, t 2.9), not soft-dog +1.5% (n 23, t 2.0), soft-dog +1.9% (n 16); DraftKings -0.1% (n 129), FanDuel -0.4%
  (n 141), BetMGM -0.6% (n 47). Holding; 11 more to the 50-read split.

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
- 2026-11-01: 28 reads in 7 days, 20 graded, CLV +0.5% (t 2.1), 14 of 20 beat the close. On track; judged at 30.
- 2026-11-02: 28 graded. STATE showed -0.7% (t -0.6), but one read (ATP Hanfmann +140, 11-01) was scored on an in-play
  close (+720, four minutes before the listed start): fixed in pull.py (tennis in-play close guard). Rescored: +0.4%
  (n 28, t 1.9), halves +0.4% and +0.4%; 0.5-1% edges +0.3% (n 22), 1%+ +0.8% (n 6); NBA +1.2% (n 7), NCAAF +0.1%
  (n 11), NFL -0.2% (n 6). Price paid +0.9% (beats Pinnacle by construction), market move -1.6% (n 28, t -1.5): the
  edge is the price, and the move runs mildly against dogs here. Judged at 30, from the next full run's numbers.
- 2026-11-03 judgement at 30+ (health check): 38 graded, +0.5% (t 2.0); halves +0.4% (n 19, t 1.45) and +0.6%
  (n 19, t 1.44): positive in both but just under the 1.5 bar, so neither "holds" nor kill; keep running, judge again
  at 50 (kill if <= 0). No floor tweak: the 1%+ bucket is not the better one (+0.8% under 1% n 12, -0.6% at 1%+ n 5,
  where Pinnacle at the pick is stored). By market: moneylines +0.6% (n 31, t 2.0), spreads +0.1% (n 7); by sport NBA
  +0.7% (n 11), ATP +1.1% (n 7), NCAAF +0.1% (n 11), NFL -0.2% (n 6), NHL +0.9% (n 3). Each read is its own game-side.
- 2026-11-05: 49 graded, +0.4% (t 1.7), 68 reads in 7 days; the 50-graded judgement falls to the next health check.
- 2026-11-06 judgement at 50 (health check): 53 graded, +0.7% (t 2.2), 35 of 53 beat the close; halves +0.2% (n 26,
  t 1.1) and +1.1% (n 27, t 1.95); without the best read (Miami at GSW ML +11.4%) +0.45% (t 2.1). Not <= 0, so not
  killed; keeps running. Moneylines carry it (+0.8%, n 45, t 2.3), spreads +0.0% (n 8): too few spreads to tweak to
  moneylines only; revisit at 15 graded spreads. Focus sports +0.7% (n 39, t 1.9): NBA +1.5% (n 16, t 2.0), NFL +0.3%
  (n 8), NCAAF +0.1% (n 15). Next look at 80 graded.

## Killed

### The final quarter-hour before the start (2026-11-10, killed)
- Observation: fast runs land at :24/:54, so the last stored snap is usually 15-16 minutes before an NBA tip; the
  close comes from a history call at the start. Idea: late scratches and lineup news in that last quarter-hour move
  prices one way (unders or dogs), which a maker order could sit in front of.
- Test (rows with a paid history close and a last snap 10-40 minutes before the start, Pinnacle no-vig, archive plus
  ledger): NBA totals over +0.24% (n 37, t 1.7; halves +0.31/+0.17), NBA moneyline favourite -0.01% (n 42), NBA spread
  favourite +0.01% (n 41), NCAAF spread favourite +0.22% (n 22, t 1.0), NCAAF/NFL totals and NFL spreads |t| <= 1.5;
  mean absolute move 0.15-0.49%. 8 variants. Memory: NBA totals timing=late n 15, -2.4% (t -5.2).
- Verdict: no direction in the last quarter-hour, and the NBA over sign runs against lead 4's earlier downward drift,
  so the drift there is earlier (injury reports), not at the tip. Side use: it shows a last snap 15-25 minutes out is
  a fair close for research (bias under 0.25%), which backs the 11-10 lastSnapWide fix for gated rows.

### Pinnacle's quote age at the pick (2026-11-09, killed for now)
- Observation: the gate trusts Pinnacle's price at the pick, but pinAtPick.updated is sometimes an hour or more before
  pickedAt. Idea: a stale Pinnacle quote is a weaker fair price (low early limits, nobody re-pricing), so reads made
  against one should lose more, and the gate should demand a fresh quote.
- Test (memory/log, NFL/NCAAF/NBA reads with pinAtPick.updated and a CLV, n 1008): quote 60+ min old -2.2% (n 182,
  t -9.0; per game -2.3%, n 90) vs under 15 min -0.2 to -1.2%; both halves (-2.2% / -2.2%). But stale quotes are
  far-from-kick NFL reads (median 69h to kick vs 24h). Held at the same time to kick: 1-3 days stale -2.0% (n 107) vs
  fresh -1.7% (n 218), no difference; 3+ days -2.4% (n 59) vs -1.4% (n 129), diff ~1.0 (t ~1.7); NFL 1+ day -2.3%
  (n 118) vs -1.2% (n 75), t ~2.2. Stale counted picks -3.4% (n 17). 11 variants (5 age buckets, 4 time controls,
  3 sports). Memory: NFL timing=early n 178, -1.7%.
- Verdict: the age effect is mostly time to kick, which the timing feature and the gate's 3h wait already carry.
  Re-test only the 3+ day NFL slice at 120 stale reads; if quote age still costs 1%+ at t >= 2.5 after holding time
  to kick, propose a freshness rule for the gate to Zack (gate constants are his).

### Pinnacle follows the US-book consensus (2026-11-08, killed for now)
- Observation: sharp-soft assumes the US books move to Pinnacle. The reverse was never tested: when the median of the
  US books (FanDuel, DraftKings, Caesars, BetMGM, BetRivers, Fanatics, theScore, Hard Rock, Bally) disagrees with
  Pinnacle at the open, does Pinnacle drift toward them by the last snapshot? Mechanism if true: US books see their
  own limited-but-informed action (and local injury news) first and Pinnacle's early NCAAF/NBA limits are low.
- Test (ledger rows with an all-book openSnap, since the five books were added 10-28; Pinnacle no-vig open vs
  lastSnap, moneylines, NBA/NCAAF/NFL): |gap| 0.5%+ Pinnacle moves toward the US median +0.72% (n 59, t 1.5; NCAAF
  +1.15% n 24 t 2.7, NBA +0.20% n 27); halves +1.38% / +0.09%; |gap| 1%+ +0.19% (n 30, t 0.2); placebo |gap| < 0.5%
  +0.58% (n 45, t 1.5), so no dose response. 6 variants (3 thresholds, h2h and spread; spread rows did not parse on a
  shared line, n 1). Memory: sharpDiv=pin-against h2h n 9, -0.5%; sharpGapOpen=1-2% h2h n 17, -0.3%.
- Verdict: no edge on 104 games and the first half carries it; sharp-soft's premise stands. Re-test at 300+ rows
  with full-book opens, NCAAF moneylines first (the only slice near t 2.5).

### Totals regress by level (2026-11-06, killed)
- Observation: every focus sport's totals reads lose (memory: NFL n 89 -2.1% t -5.3, NCAAF n 141 -2.0% t -6.2, NBA
  n 110 -1.5% t -3.0) and no totals pattern works. Idea: openers overshoot at the extremes (high totals for hyped
  offences, low ones for defences), so the market drags high totals down and low ones up by the close.
- Test (Pinnacle snapshots, first total snap 6h+ before the start vs last within 2h): open total level does not predict
  the move in any sport (slope NFL +0.03 n 24, NCAAF +0.00 n 63, NBA -0.01 n 73; all |t| < 0.4); terciles flat or
  noisy (no tercile holds in both halves). Variant by early spread size (blowout risk): NFL 7+ -1.1 (n 4), NCAAF 14+
  +0.1 (n 12), NBA 8+ +0.1 (n 19); NBA's lead-4 down-drift sits in games under 8 points (-0.82, n 54, t -2.9), noted
  under lead 4. About 12 variants.
- Verdict: no level effect; totals losses are the vig and the early-total drift already in lead 4. Re-test with a
  season of snapshots.

### Pinnacle's moneyline lags its own spread (2026-11-04, killed)
- Observation: Pinnacle prices a game's spread and moneyline separately, and college moneylines are thinner than the
  spread. Idea: when the spread-implied win chance and the moneyline's no-vig disagree 6h+ out, the thinner moneyline
  catches up by the close, so a soft moneyline on the side the spread favours carries value.
- Test (Pinnacle snapshots, NFL/NCAAF/NBA, first paired spread+moneyline snap 6h+ before the start vs last within 3h,
  moved rows dropped; spread converted with a normal margin, sd 13.5/15.5/12, juice as points; gap centred per sport):
  184 games, 75 with a gap of 2%+. Moneyline toward the spread +0.06% (t 0.1; NFL -0.6% n 18, NCAAF +0.7% n 26, NBA
  -0.1% n 31; halves -0.3% and +0.4%); slope of the moneyline move on the gap -0.05. The spread toward the moneyline
  +0.9% (t 1.6), the opposite way and not clean. 4 variants (3 sports, 2 directions).
- Living memory (moneyline reads): NFL n 5 +0.2%, NCAAF n 45 +0.2% (t 0.5), NBA n 73 +0.3% (t 0.7): no moneyline edge
  to explain either.
- Verdict: Pinnacle keeps its two markets consistent; nothing to trade. Re-test only with a season of snapshots.

### Pattern consensus (2026-11-03, killed)
- Observation: findings.py's strongest new finding (NBA, 2+ days of rest and our side travelled further, +6.4% on 19)
  came from 10 game-sides, and one game (GSW at PHX 10-25) supplied 8 of the 19 reads: rest-spot, edge-stack, five
  scan-nba-rest* patterns and learned-scan-nba-spread all took the same side. Idea: when several independent pattern
  families agree on one game-side, the read is better (agreement as evidence).
- Mechanism tried: separate families (scan, learned, sharp-soft, soft-dog, situational) see different information;
  agreement should filter noise.
- Test (memory log, non-parked picks, leans and gated reads, one row per game-side, first read's CLV): 1 family -0.7%
  (n 512, t -3.6); 2 families -0.4% (n 105, t -1.0); 3 -0.6% (n 20); 4+ +3.0% (n 7). Halves for 2+: -1.4% (n 52), then
  +0.5% (n 80). By sport 2+: NBA +1.9% (n 30), NCAAF -1.1% (n 58), NHL -1.2% (n 33). No consistent lift; 6 variants.
  72 of 572 game-markets had patterns on both sides.
- Kept from it: read-level counts overstate evidence. 780 counted reads are 593 game-sides; collapsing to one value per
  game-side, findings.py clears 37 conditions vs ~19.9 by chance (was 71 vs ~30.7), and 30 of the 71 survive the full
  re-scan. findings.py now prints each finding's game count and per-game t (byGame), report-only.
- Re-test when there are 1,500+ game-sides.

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
