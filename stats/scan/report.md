# Strategy scanner (scan.py)

2026-11-19T11:10:12Z. 25051 game-markets; 5110 hypotheses tested (move 1538, resClose 2046, resOpen 1526). Survivors pass a Benjamini-Hochberg cut at q 0.1 per test kind, the same sign in both time-ordered halves, and a minimum effect. 34 survivors; the strongest 34 are tracked as shadow strategies (stake 0) and stamp live reads, so their CLV builds on its own. grade.py alone decides promotion.

| Strategy | Side | Conditions | Move (CLV) | Result at open | Result at close | Status |
|---|---|---|---|---|---|---|
| NBA spread | home | restAway b2b; restEdge home more | +0.92 pts (n 146, t +5.2) | ROI -5.9% (n 146, t -0.7) | ROI -8.5% (n 146, t -1.1) | tracking |
| NCAAF spread | home | line home fav 21+; month Sep | +0.43 pts (n 587, t +4.9) | ROI +0.5% (n 581, t +0.1) | ROI +0.7% (n 578, t +0.2) | tracking |
| NBA spread | home | restEdge home more | +0.55 pts (n 298, t +4.7) | ROI -5.2% (n 298, t -0.9) | ROI -5.2% (n 298, t -0.9) | tracking |
| NBA spread | away | restEdge away more | +0.56 pts (n 252, t +4.6) | ROI -3.8% (n 252, t -0.6) | ROI -8.3% (n 252, t -1.4) | tracking |
| NBA spread | home | restAway b2b | +0.68 pts (n 222, t +4.6) | ROI -7.1% (n 222, t -1.1) | ROI -9.7% (n 222, t -1.5) | tracking |
| NFL spread | away | line home fav 0.5-3 | +0.56 pts (n 200, t +4.5) | ROI +1.6% (n 197, t +0.2) | ROI +4.1% (n 198, t +0.6) | tracking |
| NFL spread | away | closeLine home dog 0.5-3 | +0.57 pts (n 172, t +4.4) | ROI -4.8% (n 170, t -0.7) | ROI -3.1% (n 335, t -0.6) | tracking |
| NBA h2h | home | restAway b2b; restEdge home more | +1.93% (n 146, t +4.4) | ROI -9.0% (n 146, t -1.1) | ROI -11.8% (n 146, t -1.4) | tracking |
| NFL spread | home | line home dog 0.5-3 | +0.60 pts (n 172, t +4.3) | ROI -6.6% (n 172, t -0.9) | ROI -7.4% (n 169, t -1.0) | tracking |
| NCAAF spread | home | line home fav 21+ | +0.29 pts (n 917, t +3.9) | ROI -2.5% (n 910, t -0.8) | ROI -1.8% (n 906, t -0.6) | tracking |
| NBA h2h | home | restEdge home more | +1.11% (n 297, t +3.9) | ROI -9.5% (n 297, t -1.6) | ROI -10.8% (n 297, t -1.8) | tracking |
| NBA h2h | home | restAway b2b | +1.43% (n 222, t +3.8) | ROI -6.9% (n 222, t -0.9) | ROI -11.6% (n 222, t -1.7) | tracking |
| NCAAF spread | home | month Aug | +0.49 pts (n 206, t +3.8) | ROI -6.9% (n 205, t -1.0) | ROI -10.5% (n 207, t -1.6) | tracking |
| NBA total | over | month Mar; restHome 1day | +0.87 pts (n 150, t +3.6) | ROI +0.6% (n 150, t +0.1) | ROI -8.3% (n 150, t -1.1) | tracking |
| NCAAF h2h | away | homePrice 75%+; restHome normal | +1.08% (n 171, t +3.5) | ROI -28.0% (n 171, t -1.7) | ROI -34.0% (n 171, t -2.3) | tracking |
| NCAAF h2h | away | homePrice 75%+ | +0.79% (n 262, t +3.5) | ROI -31.5% (n 262, t -1.9) | ROI -36.6% (n 262, t -2.6) | tracking |
| NBA h2h | away | restEdge away more | +1.02% (n 249, t +3.3) | ROI -1.3% (n 249, t -0.2) | ROI -4.2% (n 249, t -0.5) | tracking |
| NBA spread | home | line home dog 0.5-3 | +0.70 pts (n 157, t +3.2) | ROI -5.2% (n 157, t -0.7) | ROI -3.9% (n 157, t -0.5) | tracking |
| NCAAF total | under | restEdge even; total 50-55 | +0.57 pts (n 175, t +2.3) | ROI +22.0% (n 174, t +3.1) | ROI +15.8% (n 175, t +2.2) | tracking |
| NCAAF h2h | away | homePrice 75%+; restEdge even | +1.27% (n 124, t +3.1) | ROI -29.8% (n 124, t -1.6) | ROI -39.6% (n 124, t -2.6) | tracking |
| NCAAF spread | home | restEdge home more; restHome long | +0.59 pts (n 174, t +3.0) | ROI -4.0% (n 173, t -0.5) | ROI -7.9% (n 172, t -1.1) | tracking |
| NCAAF spread | home | restHome long | +0.46 pts (n 310, t +3.0) | ROI +5.7% (n 307, t +1.1) | ROI +4.1% (n 308, t +0.8) | tracking |
| NBA spread | away | dow Tue | +0.41 pts (n 163, t +3.0) | ROI -11.0% (n 163, t -1.5) | ROI -13.3% (n 163, t -1.8) | tracking |
| NBA total | over | month Mar | +0.56 pts (n 239, t +2.9) | ROI -3.3% (n 239, t -0.5) | ROI -8.0% (n 239, t -1.3) | tracking |
| NCAAF total | under | month Nov; restEdge even | +0.25 pts (n 123, t +0.8) | ROI +24.1% (n 123, t +2.9) | ROI +9.0% (n 254, t +1.5) | tracking |
| NBA total | under | month Nov | +0.68 pts (n 181, t +2.9) | ROI -2.8% (n 181, t -0.4) | ROI +0.4% (n 181, t +0.1) | tracking |
| NCAAF h2h | away | homePrice 75%+; restAway normal | +1.05% (n 142, t +2.9) | ROI -29.8% (n 142, t -1.7) | ROI -37.1% (n 142, t -2.5) | tracking |
| NBA h2h | away | dow Tue | +0.99% (n 157, t +2.8) | ROI -12.6% (n 157, t -1.3) | ROI -15.8% (n 157, t -1.7) | tracking |
| NFL total | under | closeTotal 40-43; dow Sun | +0.24 pts (n 244, t +2.8) | ROI -6.9% (n 242, t -1.1) | ROI -6.5% (n 493, t -1.5) | tracking |
| NCAAF spread | home | restAway normal; restHome long | +0.60 pts (n 147, t +2.8) | ROI +0.7% (n 146, t +0.1) | ROI -3.9% (n 145, t -0.5) | tracking |
| NCAAF spread | away | line home fav 0.5-3 | +0.36 pts (n 357, t +2.8) | ROI -5.4% (n 355, t -1.1) | ROI -4.5% (n 344, t -0.9) | tracking |
| NFL total | under | awayTz none; closeTotal 40-43 | +0.34 pts (n 126, t +2.7) | ROI -14.5% (n 125, t -1.7) | ROI -13.5% (n 253, t -2.2) | tracking |
| NBA total | under | dow Fri; restHome 1day | +0.91 pts (n 131, t +2.7) | ROI +10.6% (n 131, t +1.3) | ROI +6.4% (n 131, t +0.8) | tracking |
| NFL total | under | awayTz none; dow Sun | +0.18 pts (n 518, t +2.7) | ROI +1.4% (n 514, t +0.3) | ROI -1.3% (n 1033, t -0.4) | tracking |
| NHL total | over | overPrice 55%-65% | +2.33% (n 186, t +6.6) | ROI +4.1% (n 186, t +0.7) | ROI +7.0% (n 186, t +1.0) | lapsed |
| MLB total | over | month Jun | +1.27% (n 394, t +6.5) | ROI -0.1% (n 370, t -0.0) | ROI -3.0% (n 378, t -0.6) | lapsed |
| LaLiga total | under | overPrice 25%-35% | +0.95% (n 190, t +5.8) | ROI +0.4% (n 190, t +0.1) | ROI -1.3% (n 190, t -0.3) | lapsed |
| MLB total | under | month Aug | +1.13% (n 417, t +5.7) | ROI +1.1% (n 406, t +0.2) | ROI -3.8% (n 396, t -0.8) | lapsed |
| NHL total | over | total 5.5 | +1.05% (n 566, t +5.1) | ROI -0.3% (n 567, t -0.1) | ROI +0.3% (n 567, t +0.1) | lapsed |
| Ligue1 total | over | month Apr | +1.06% (n 212, t +5.0) | ROI +13.9% (n 212, t +2.1) | ROI +12.1% (n 212, t +1.9) | lapsed |
| MLB total | over | month Jul | +1.05% (n 372, t +4.7) | ROI -14.5% (n 362, t -2.9) | ROI -15.2% (n 363, t -3.1) | lapsed |
| MLB h2h | away | homePrice 55%-65%; month May | +0.83% (n 151, t +4.6) | ROI +3.7% (n 151, t +0.4) | ROI +2.7% (n 151, t +0.3) | lapsed |
| Ligue1 total | over | month May | +1.05% (n 172, t +4.1) | ROI +8.6% (n 172, t +1.3) | ROI +6.8% (n 172, t +1.1) | lapsed |
| SerieA total | over | dow Sun; month Oct | +0.91% (n 129, t +4.0) | ROI +8.7% (n 129, t +1.0) | ROI +9.4% (n 130, t +1.1) | lapsed |
| NHL total | under | month Dec; overPrice 45%-55% | +1.50% (n 168, t +3.9) | ROI +1.7% (n 168, t +0.2) | ROI -0.7% (n 168, t -0.1) | lapsed |
| Ligue1 total | under | dow Sun; month Feb | +1.02% (n 140, t +3.9) | ROI -1.3% (n 140, t -0.2) | ROI -3.5% (n 140, t -0.4) | lapsed |
| NHL total | over | dow Thu; total 5.5 | +1.52% (n 123, t +3.8) | ROI +0.3% (n 123, t +0.0) | ROI -4.5% (n 123, t -0.5) | lapsed |
| Ligue1 total | under | month Jan | +0.70% (n 205, t +3.8) | ROI +2.1% (n 205, t +0.3) | ROI +2.4% (n 206, t +0.3) | lapsed |
| EPL h2h | draw | month Jan | +0.28% (n 362, t +3.7) | ROI +11.2% (n 362, t +1.1) | ROI +10.4% (n 362, t +1.0) | lapsed |
| MLB h2h | home | homePrice 55%-65%; month Aug | +0.80% (n 150, t +3.7) | ROI +3.5% (n 150, t +0.5) | ROI +4.2% (n 150, t +0.6) | lapsed |
| NHL h2h | away | restEdge away more | +0.94% (n 205, t +3.7) | ROI -2.8% (n 205, t -0.4) | ROI -5.8% (n 205, t -0.8) | lapsed |
| SerieA total | under | month Feb | +0.67% (n 244, t +3.6) | ROI -0.1% (n 244, t -0.0) | ROI -2.2% (n 244, t -0.3) | lapsed |
| LaLiga h2h | draw | dow Sat; homePrice 35%-45% | +0.24% (n 259, t +3.6) | ROI +4.3% (n 259, t +0.4) | ROI +2.9% (n 259, t +0.3) | lapsed |
| MLB h2h | home | restHome day off | +0.46% (n 320, t +3.5) | ROI -0.3% (n 320, t -0.1) | ROI -1.7% (n 320, t -0.3) | lapsed |
| NHL total | over | restEdge home more; total 5.5 | +1.36% (n 149, t +3.5) | ROI +1.6% (n 149, t +0.2) | ROI +3.9% (n 149, t +0.5) | lapsed |
| Ligue1 h2h | draw | dow Sun; homePrice 35%-45% | +0.20% (n 377, t +3.5) | ROI +0.1% (n 377, t +0.0) | ROI -1.3% (n 377, t -0.2) | lapsed |
| NHL total | under | month Mar; total 6.5 | +1.31% (n 142, t +3.4) | ROI +6.5% (n 142, t +0.9) | ROI +12.0% (n 142, t +1.5) | lapsed |
| SerieA h2h | draw | dow Sun; month Jan | +0.29% (n 191, t +3.4) | ROI +3.0% (n 191, t +0.2) | ROI +2.3% (n 191, t +0.2) | lapsed |
| SerieA total | under | month Jan | +0.56% (n 295, t +3.4) | ROI -3.5% (n 295, t -0.6) | ROI -5.6% (n 296, t -0.9) | lapsed |
| SerieA total | under | dow Sun; month Jan | +0.85% (n 133, t +3.4) | ROI -0.3% (n 133, t -0.0) | ROI -2.0% (n 133, t -0.2) | lapsed |
