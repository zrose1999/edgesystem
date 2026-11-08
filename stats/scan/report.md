# Strategy scanner (scan.py)

2026-11-08T11:11:47Z. 24384 game-markets; 4910 hypotheses tested (move 1470, resClose 1976, resOpen 1464). Survivors pass a Benjamini-Hochberg cut at q 0.1 per test kind, the same sign in both time-ordered halves, and a minimum effect. 24 survivors; the strongest 24 are tracked as shadow strategies (stake 0) and stamp live reads, so their CLV builds on its own. grade.py alone decides promotion.

| Strategy | Side | Conditions | Move (CLV) | Result at open | Result at close | Status |
|---|---|---|---|---|---|---|
| NCAAF spread | home | line home fav 21+; month Sep | +0.44 pts (n 587, t +5.1) | ROI +0.5% (n 581, t +0.1) | ROI +0.7% (n 578, t +0.2) | tracking |
| NBA spread | home | restAway b2b; restEdge home more | +0.88 pts (n 135, t +4.8) | ROI -6.7% (n 135, t -0.8) | ROI -8.1% (n 135, t -1.0) | tracking |
| NFL spread | away | line home fav 0.5-3 | +0.56 pts (n 200, t +4.5) | ROI +1.6% (n 197, t +0.2) | ROI +4.1% (n 198, t +0.6) | tracking |
| NFL spread | away | closeLine home dog 0.5-3 | +0.57 pts (n 172, t +4.4) | ROI -4.8% (n 170, t -0.7) | ROI -3.1% (n 335, t -0.6) | tracking |
| NFL spread | home | line home dog 0.5-3 | +0.60 pts (n 172, t +4.3) | ROI -6.6% (n 172, t -0.9) | ROI -7.4% (n 169, t -1.0) | tracking |
| NCAAF spread | home | line home fav 21+ | +0.31 pts (n 913, t +4.2) | ROI -2.4% (n 906, t -0.8) | ROI -1.8% (n 902, t -0.6) | tracking |
| NBA spread | home | restEdge home more | +0.52 pts (n 271, t +4.2) | ROI -7.0% (n 271, t -1.2) | ROI -6.3% (n 271, t -1.1) | tracking |
| NBA spread | away | restEdge away more | +0.50 pts (n 228, t +4.1) | ROI -4.5% (n 228, t -0.7) | ROI -7.9% (n 228, t -1.2) | tracking |
| NBA spread | home | restAway b2b | +0.63 pts (n 207, t +4.1) | ROI -6.9% (n 207, t -1.0) | ROI -8.7% (n 207, t -1.3) | tracking |
| NBA h2h | home | restAway b2b; restEdge home more | +1.84% (n 135, t +4.0) | ROI -6.9% (n 135, t -0.8) | ROI -9.8% (n 135, t -1.1) | tracking |
| NCAAF spread | home | month Aug | +0.50 pts (n 206, t +3.9) | ROI -6.9% (n 205, t -1.0) | ROI -10.5% (n 207, t -1.6) | tracking |
| NCAAF h2h | away | homePrice 75%+; restHome normal | +1.13% (n 155, t +3.6) | ROI -32.1% (n 155, t -1.9) | ROI -40.8% (n 155, t -2.8) | tracking |
| NBA h2h | home | restEdge home more | +1.06% (n 270, t +3.6) | ROI -9.0% (n 270, t -1.5) | ROI -10.3% (n 270, t -1.7) | tracking |
| NBA total | over | month Mar; restHome 1day | +0.83 pts (n 150, t +3.4) | ROI +0.6% (n 150, t +0.1) | ROI -8.3% (n 150, t -1.1) | tracking |
| NBA h2h | home | restAway b2b | +1.28% (n 207, t +3.3) | ROI -5.5% (n 207, t -0.7) | ROI -10.1% (n 207, t -1.4) | tracking |
| NBA spread | away | dow Tue | +0.46 pts (n 152, t +3.2) | ROI -13.3% (n 152, t -1.7) | ROI -15.9% (n 152, t -2.1) | tracking |
| NCAAF spread | home | restHome long | +0.50 pts (n 303, t +3.2) | ROI +5.0% (n 300, t +0.9) | ROI +2.7% (n 301, t +0.5) | tracking |
| NCAAF h2h | away | homePrice 75%+ | +0.73% (n 244, t +3.2) | ROI -33.8% (n 244, t -2.0) | ROI -40.6% (n 244, t -2.8) | tracking |
| NCAAF h2h | away | homePrice 75%+; restAway normal | +1.12% (n 129, t +3.0) | ROI -31.2% (n 129, t -1.7) | ROI -41.6% (n 129, t -2.8) | tracking |
| NCAAF total | under | dow Sat; restAway normal | +0.38 pts (n 432, t +2.9) | ROI -0.7% (n 431, t -0.2) | ROI -3.2% (n 845, t -1.0) | tracking |
| NBA h2h | away | dow Tue | +1.03% (n 151, t +2.9) | ROI -12.3% (n 151, t -1.2) | ROI -15.5% (n 151, t -1.6) | tracking |
| NBA total | under | month Jan | +0.59 pts (n 233, t +2.8) | ROI +16.3% (n 233, t +2.7) | ROI +14.6% (n 233, t +2.4) | tracking |
| NFL total | under | closeTotal 40-43; dow Sun | +0.24 pts (n 244, t +2.8) | ROI -6.9% (n 242, t -1.1) | ROI -6.5% (n 489, t -1.5) | tracking |
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
| LaLiga total | over | line 2.5; overPrice 65%-75% | +0.80% (n 123, t +3.3) | ROI -10.2% (n 123, t -1.7) | ROI -10.5% (n 123, t -1.7) | lapsed |
| LaLiga h2h | away | dow Sat; homePrice <25% | +0.79% (n 206, t +3.3) | ROI -0.2% (n 206, t -0.0) | ROI -0.9% (n 206, t -0.2) | lapsed |
| EPL total | under | month Mar | +0.69% (n 160, t +3.2) | ROI +1.3% (n 160, t +0.2) | ROI -0.7% (n 160, t -0.1) | lapsed |
| SerieA total | under | month Nov | +0.62% (n 239, t +3.2) | ROI +5.2% (n 239, t +0.7) | ROI +3.6% (n 239, t +0.5) | lapsed |
