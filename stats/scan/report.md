# Strategy scanner (scan.py)

2026-10-30T11:12:55Z. 59578 game-markets; 7858 hypotheses tested (move 2432, resClose 3002, resOpen 2424). Survivors pass a Benjamini-Hochberg cut at q 0.1 per test kind, the same sign in both time-ordered halves, and a minimum effect. 78 survivors; the strongest 40 are tracked as shadow strategies (stake 0) and stamp live reads, so their CLV builds on its own. grade.py alone decides promotion.

| Strategy | Side | Conditions | Move (CLV) | Result at open | Result at close | Status |
|---|---|---|---|---|---|---|
| NHL total | over | overPrice 55%-65% | +2.33% (n 184, t +6.5) | ROI +4.3% (n 184, t +0.7) | ROI +7.0% (n 184, t +1.0) | tracking |
| MLB total | over | month Jun | +1.27% (n 394, t +6.5) | ROI -0.1% (n 370, t -0.0) | ROI -3.0% (n 378, t -0.6) | tracking |
| LaLiga total | under | overPrice 25%-35% | +0.95% (n 190, t +5.8) | ROI +0.4% (n 190, t +0.1) | ROI -1.3% (n 190, t -0.3) | tracking |
| MLB total | under | month Aug | +1.13% (n 417, t +5.7) | ROI +1.1% (n 406, t +0.2) | ROI -3.8% (n 396, t -0.8) | tracking |
| NHL total | over | total 5.5 | +1.06% (n 559, t +5.1) | ROI -0.6% (n 560, t -0.2) | ROI -0.2% (n 560, t -0.1) | tracking |
| Ligue1 total | over | month Apr | +1.06% (n 212, t +5.0) | ROI +13.9% (n 212, t +2.1) | ROI +12.1% (n 212, t +1.9) | tracking |
| NCAAF spread | home | line home fav 21+; month Sep | +0.43 pts (n 587, t +5.0) | ROI +0.5% (n 581, t +0.1) | ROI +0.7% (n 578, t +0.2) | tracking |
| NBA spread | home | restAway b2b; restEdge home more | +0.91 pts (n 131, t +4.8) | ROI -6.7% (n 131, t -0.8) | ROI -8.2% (n 131, t -1.0) | tracking |
| MLB total | over | month Jul | +1.05% (n 372, t +4.7) | ROI -14.5% (n 362, t -2.9) | ROI -15.2% (n 363, t -3.1) | tracking |
| MLB h2h | away | homePrice 55%-65%; month May | +0.83% (n 151, t +4.6) | ROI +3.7% (n 151, t +0.4) | ROI +2.7% (n 151, t +0.3) | tracking |
| NCAAF spread | home | line home fav 21+ | +0.32 pts (n 894, t +4.3) | ROI -2.5% (n 887, t -0.8) | ROI -2.1% (n 883, t -0.6) | tracking |
| NBA spread | home | restEdge home more | +0.54 pts (n 260, t +4.2) | ROI -5.3% (n 260, t -0.9) | ROI -3.8% (n 260, t -0.6) | tracking |
| NBA spread | home | restAway b2b | +0.66 pts (n 199, t +4.1) | ROI -6.0% (n 199, t -0.9) | ROI -7.9% (n 199, t -1.2) | tracking |
| Ligue1 total | over | month May | +1.05% (n 172, t +4.1) | ROI +8.6% (n 172, t +1.3) | ROI +6.8% (n 172, t +1.1) | tracking |
| SerieA total | over | dow Sun; month Oct | +0.91% (n 129, t +4.0) | ROI +8.7% (n 129, t +1.0) | ROI +9.4% (n 130, t +1.1) | tracking |
| NBA h2h | home | restAway b2b; restEdge home more | +1.88% (n 131, t +4.0) | ROI -8.2% (n 131, t -0.9) | ROI -11.2% (n 131, t -1.3) | tracking |
| Ligue1 total | under | dow Sun; month Feb | +1.02% (n 140, t +3.9) | ROI -1.3% (n 140, t -0.2) | ROI -3.5% (n 140, t -0.4) | tracking |
| NHL total | under | month Dec; overPrice 45%-55% | +1.48% (n 168, t +3.9) | ROI +1.7% (n 168, t +0.2) | ROI -0.7% (n 168, t -0.1) | tracking |
| NBA spread | away | restEdge away more | +0.49 pts (n 217, t +3.8) | ROI -4.1% (n 217, t -0.6) | ROI -6.7% (n 217, t -1.0) | tracking |
| NHL h2h | away | restEdge away more | +0.97% (n 202, t +3.8) | ROI -3.0% (n 202, t -0.4) | ROI -6.1% (n 202, t -0.9) | tracking |
| NCAAF spread | home | month Aug | +0.49 pts (n 206, t +3.8) | ROI -6.9% (n 205, t -1.0) | ROI -10.5% (n 207, t -1.6) | tracking |
| Ligue1 total | under | month Jan | +0.70% (n 205, t +3.8) | ROI +2.1% (n 205, t +0.3) | ROI +2.4% (n 206, t +0.3) | tracking |
| EPL h2h | draw | month Jan | +0.28% (n 362, t +3.7) | ROI +11.2% (n 362, t +1.1) | ROI +10.4% (n 362, t +1.0) | tracking |
| MLB h2h | home | homePrice 55%-65%; month Aug | +0.80% (n 150, t +3.7) | ROI +3.5% (n 150, t +0.5) | ROI +4.2% (n 150, t +0.6) | tracking |
| SerieA total | under | month Feb | +0.67% (n 244, t +3.6) | ROI -0.1% (n 244, t -0.0) | ROI -2.2% (n 244, t -0.3) | tracking |
| NBA h2h | home | restEdge home more | +1.12% (n 259, t +3.6) | ROI -7.7% (n 259, t -1.2) | ROI -9.0% (n 259, t -1.4) | tracking |
| LaLiga h2h | draw | dow Sat; homePrice 35%-45% | +0.24% (n 259, t +3.6) | ROI +4.3% (n 259, t +0.4) | ROI +2.9% (n 259, t +0.3) | tracking |
| MLB h2h | home | restHome day off | +0.46% (n 320, t +3.5) | ROI -0.3% (n 320, t -0.1) | ROI -1.7% (n 320, t -0.3) | tracking |
| Ligue1 h2h | draw | dow Sun; homePrice 35%-45% | +0.20% (n 377, t +3.5) | ROI +0.1% (n 377, t +0.0) | ROI -1.3% (n 377, t -0.2) | tracking |
| SerieA h2h | draw | dow Sun; month Jan | +0.29% (n 191, t +3.4) | ROI +3.0% (n 191, t +0.2) | ROI +2.3% (n 191, t +0.2) | tracking |
| SerieA total | under | month Jan | +0.56% (n 295, t +3.4) | ROI -3.5% (n 295, t -0.6) | ROI -5.6% (n 296, t -0.9) | tracking |
| NHL total | under | month Mar; total 6.5 | +1.29% (n 142, t +3.4) | ROI +6.5% (n 142, t +0.9) | ROI +12.0% (n 142, t +1.5) | tracking |
| NBA h2h | home | restAway b2b | +1.35% (n 199, t +3.4) | ROI -5.1% (n 199, t -0.6) | ROI -9.8% (n 199, t -1.3) | tracking |
| SerieA total | under | dow Sun; month Jan | +0.85% (n 133, t +3.4) | ROI -0.3% (n 133, t -0.0) | ROI -2.0% (n 133, t -0.2) | tracking |
| NBA total | under | month Jan | +0.70 pts (n 233, t +3.3) | ROI +16.3% (n 233, t +2.7) | ROI +14.6% (n 233, t +2.4) | tracking |
| LaLiga total | over | line 2.5; overPrice 65%-75% | +0.80% (n 123, t +3.3) | ROI -10.2% (n 123, t -1.7) | ROI -10.5% (n 123, t -1.7) | tracking |
| NCAAF h2h | away | homePrice 75%+; restHome normal | +1.10% (n 141, t +3.3) | ROI -30.5% (n 141, t -1.7) | ROI -38.9% (n 141, t -2.5) | tracking |
| LaLiga h2h | away | dow Sat; homePrice <25% | +0.79% (n 206, t +3.3) | ROI -0.2% (n 206, t -0.0) | ROI -0.9% (n 206, t -0.2) | tracking |
| EPL total | under | month Mar | +0.69% (n 160, t +3.2) | ROI +1.3% (n 160, t +0.2) | ROI -0.7% (n 160, t -0.1) | tracking |
| SerieA total | under | month Nov | +0.62% (n 239, t +3.2) | ROI +5.2% (n 239, t +0.7) | ROI +3.6% (n 239, t +0.5) | tracking |
