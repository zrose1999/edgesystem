import json, math, sys
sys.path.insert(0, '/root/edgesystem')
import matchups as MX
L = {r['market']: r for r in json.load(open('/root/edgesystem/ledger/ledger.json')) if isinstance(r, dict) and r.get('event') == "Alabama Crimson Tide at LSU Tigers"} \
    if isinstance(json.load(open('/root/edgesystem/ledger/ledger.json')), list) else None
if L is None:
    raw = json.load(open('/root/edgesystem/ledger/ledger.json'))
    it = raw.get('rows', raw); it = it.values() if isinstance(it, dict) else it
    L = {r['market']: r for r in it if isinstance(r, dict) and r.get('event') == "Alabama Crimson Tide at LSU Tigers"}
cal = json.load(open('/root/edgesystem/stats/ncaaf_calibration.json'))
d = json.load(open('slate.json')); g = d['games'][0]
P = g['projection']; EM = g['edgeModel']
SD_M = round(cal['maeMarketSide'] * 1.2533, 1)   # normal: SD = MAE * sqrt(pi/2)
SD_T = 15.5
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
imp = lambda a: (-a / (-a + 100)) if a < 0 else (100 / (a + 100))
def amer(p):
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)
NAMES = {'draftkings': 'DraftKings', 'fanduel': 'FanDuel', 'betmgm': 'BetMGM', 'fanatics': 'Fanatics', 'espnbet': 'theScore Bet',
         'hardrockbet': 'Hard Rock', 'ballybet': 'Bally Bet', 'betrivers': 'BetRivers', 'pinnacle': 'Pinnacle'}
def books(m, a, b):
    out = []
    for k, v in L[m]['lastSnap']['books'].items():
        out.append({'book': NAMES.get(k, v.get('book')), 'line': v.get('line'), a: v.get(a), b: v.get(b), 'sharp': k == 'pinnacle'})
    return out
def best(bk, key):
    us = [x for x in bk if not x['sharp'] and x[key] is not None]
    m = max(us, key=lambda x: x[key])
    return {'book': ', '.join(x['book'] for x in us if x[key] == m[key]), 'price': m[key], 'line': m['line']}
def novig(a, b):
    pa, pb = imp(a), imp(b); return pa / (pa + pb)
def ev(p, price):
    dec = (100 / -price + 1) if price < 0 else (price / 100 + 1)
    return p * dec - 1

out = {'sdMargin': SD_M, 'sdTotal': SD_T, 'snapTime': L['spread']['lastSnap']['time'], 'calibration': {
    'games': cal['backtestGames'], 'kSide': cal['side']['kRaw'], 'kTotal': cal['total']['kRaw'], 'kTotalSe': cal['total']['se'],
    'kMoveTotal': cal['moveTotal']['kMove'], 'maeMarket': cal['maeMarketSide'], 'maeModel': cal['maeRawSide']}}
mem = {m: {s: MX.memory_check('NCAAF', m, s)['sameSide'] for s in ('home', 'away', 'over', 'under')} for m in ('h2h', 'spread', 'total')}

# moneyline
bk = books('h2h', 'home', 'away'); pin = L['h2h']['lastSnap']['books']['pinnacle']
pm = novig(pin['home'], pin['away']); pv = Phi(P['margin'] / SD_M); pe = Phi(EM['rawMargin'] / SD_M)
bh, ba = best(bk, 'home'), best(bk, 'away')
out['ml'] = {'open': {'home': L['h2h']['openSnap']['home'], 'away': L['h2h']['openSnap']['away'], 'book': 'FanDuel', 'time': L['h2h']['openTime']},
    'espnOpen': {'home': -180, 'book': 'DraftKings'}, 'pin': pin, 'marketProb': round(pm, 3), 'viewProb': round(pv, 3), 'modelProb': round(pe, 3),
    'fpiProb': 0.57, 'fairView': amer(pv), 'fairMarket': amer(pm), 'bestHome': bh, 'bestAway': ba,
    'evHomeView': round(ev(pv, bh['price']), 3), 'evAwayView': round(ev(1 - pv, ba['price']), 3),
    'evHomeMarket': round(ev(pm, bh['price']), 3), 'evAwayMarket': round(ev(1 - pm, ba['price']), 3), 'books': bk, 'memory': mem['h2h']}
# spread
bk = books('spread', 'home', 'away'); pin = L['spread']['lastSnap']['books']['pinnacle']
line = -5.5
pc_view = Phi((P['margin'] + line) / SD_M); pc_model = Phi((EM['rawMargin'] + line) / SD_M)
bh, ba = best(bk, 'home'), best(bk, 'away')
out['spread'] = {'open': L['spread']['openLine'], 'openBook': 'FanDuel', 'openTime': L['spread']['openTime'], 'espnOpen': -4.0, 'now': line,
    'pin': pin, 'pinNoVig': round(novig(pin['home'], pin['away']), 3), 'viewCover': round(pc_view, 3), 'modelCover': round(pc_model, 3),
    'bestHome': bh, 'bestAway': ba, 'evHomeView': round(ev(pc_view, bh['price']), 3), 'evAwayView': round(ev(1 - pc_view, ba['price']), 3),
    'books': bk, 'memory': mem['spread'], 'viewFair': -P['margin'], 'modelFair': -EM['rawMargin']}
# total
bk = books('total', 'over', 'under'); pin = L['total']['lastSnap']['books']['pinnacle']
t = 52.5
pu_view = Phi((t - P['total']) / SD_T); pu_model = Phi((t - EM['rawTotal']) / SD_T)
bo, bu = best(bk, 'over'), best(bk, 'under')
out['total'] = {'open': L['total']['openLine'], 'openBook': 'FanDuel', 'openTime': L['total']['openTime'], 'espnOpen': 54.5, 'now': t, 'pin': pin,
    'pinNoVigOver': round(novig(pin['over'], pin['under']), 3), 'viewUnder': round(pu_view, 3), 'modelUnder': round(pu_model, 3),
    'bestOver': bo, 'bestUnder': bu, 'evUnderView': round(ev(pu_view, bu['price']), 3), 'evOverModel': round(ev(1 - pu_model, bo['price']), 3),
    'books': bk, 'memory': mem['total'], 'viewFair': P['total'], 'modelFair': EM['rawTotal'],
    'edgeReads': ["ncaaf-spot under 52.5 (BetMGM -108, 11-01): gated, Pinnacle gate blocked (-1.9% vs Pinnacle).",
                  "learned-ncaaf-total under 52.5 (11-01): model expected the total to drift 1.0 below the open; gated, not a play."],
    'kMovePred': round(cal['moveTotal']['kMove'] * (EM['rawTotal'] - L['total']['openLine']), 2)}
g['gameLines'] = out
json.dump(d, open('slate.json', 'w'), indent=1)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ('books', 'pin')} if isinstance(v, dict) else v for k, v in out.items()}, indent=1))
