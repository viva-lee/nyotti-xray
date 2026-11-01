"""Pilot: describe 40 of his XBTUSD decisions in words, ask Jev typed questions, check one against code."""
import json, os, sys, time, urllib.request
import numpy as np
import pandas as pd

derived, env_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
env = dict(l.strip().split('=', 1) for l in open(env_path, encoding='utf-8') if '=' in l and not l.startswith('#'))
KEY, MODEL = env['TYPESAFE_API_KEY'].strip().strip('"'), env.get('JEV_MODEL', 'jev-latest').strip().strip('"')

A = pd.read_parquet(os.path.join(derived, 'actions_xbtusd.parquet'))
C = pd.read_parquet(os.path.join(derived, 'xbtusd_1h.parquet')).set_index('timestamp').sort_index()
# BitMEX bucketed rows are stamped at the bucket END; shift so index = bucket start.
C.index = C.index - pd.Timedelta(hours=1)
typical = A.groupby(A.start.dt.year).size_usd.median()


def pct(a, b):
    return (b / a - 1) * 100


def move_words(r):
    if r <= -8: return f'fell sharply ({r:+.1f}%)'
    if r <= -3: return f'fell ({r:+.1f}%)'
    if r < -1: return f'drifted lower ({r:+.1f}%)'
    if r <= 1: return f'was roughly flat ({r:+.1f}%)'
    if r < 3: return f'drifted higher ({r:+.1f}%)'
    if r < 8: return f'rose ({r:+.1f}%)'
    return f'rose sharply ({r:+.1f}%)'


def ratio_words(x, what):
    if x >= 2.5: return f'{what} about {x:.1f}x its 30-day normal (very heavy)'
    if x >= 1.5: return f'{what} about {x:.1f}x its 30-day normal (heavy)'
    if x <= 0.6: return f'{what} about {x:.1f}x its 30-day normal (light)'
    return f'{what} near its 30-day normal'


def context(ts):
    hist = C.loc[:ts.floor('h') - pd.Timedelta(hours=1)]  # only candles fully closed before the action
    if len(hist) < 24 * 31:
        return None
    px = hist.close.iloc[-1]
    r6, r24 = pct(hist.close.iloc[-7], px), pct(hist.close.iloc[-25], px)
    r7d, r30d = pct(hist.close.iloc[-169], px), pct(hist.close.iloc[-721], px)
    m30 = hist.iloc[-720:]
    hi, lo = m30.high.max(), m30.low.min()
    where = (px - lo) / (hi - lo) if hi > lo else .5
    vol = hist.volume.iloc[-24:].mean() / m30.volume.mean()
    rv = hist.close.pct_change().iloc[-24:].std() / hist.close.pct_change().iloc[-720:].std()
    place = ('near its 30-day low' if where < .15 else 'near its 30-day high' if where > .85
             else 'in the lower half of its 30-day range' if where < .5 else 'in the upper half of its 30-day range')
    return {
        'price_now': f'{px:,.0f} USD',
        'last_6_hours': f'Bitcoin {move_words(r6)}',
        'last_24_hours': f'Bitcoin {move_words(r24)}',
        'last_7_days': f'Bitcoin {move_words(r7d)}',
        'last_30_days': f'Bitcoin {move_words(r30d)}',
        'range_position': f'Price is {place}',
        'volume_last_24_hours': ratio_words(vol, 'Trading volume was'),
        'volatility_last_24_hours': ratio_words(rv, 'Hourly volatility was'),
    }, r24


def exposure_words(before, after):
    def side(p):
        return 'flat' if p == 0 else ('net long' if p > 0 else 'net short')
    if before == 0: return f'opened a new position, leaving him {side(after)}'
    if after == 0: return f'closed his whole position (was {side(before)}), leaving him flat'
    if np.sign(before) != np.sign(after): return f'flipped from {side(before)} to {side(after)}'
    if abs(after) > abs(before): return f'added to his {side(before)} position'
    return f'reduced his {side(before)} position'


def action(a):
    rel = a.size_usd / typical[a.start.year]
    size = ('much larger than' if rel >= 3 else 'larger than' if rel >= 1.5 else
            'much smaller than' if rel <= 1 / 3 else 'smaller than' if rel <= 2 / 3 else 'about the same as')
    mins = max(1, round((a.end - a.start).total_seconds() / 60))
    return {
        'direction': 'bought Bitcoin perpetual contracts' if a.side == 'Buy' else 'sold Bitcoin perpetual contracts',
        'effect': exposure_words(a.pos_before, a.pos_after),
        'size': f'{size} his typical action that year',
        'execution': ('mostly resting limit orders that waited to be filled' if a.maker >= .7 else
                      'mostly orders that took liquidity immediately' if a.maker <= .3 else 'a mix of resting and immediate orders'),
        'duration': f'filled over about {mins} minute(s)',
    }


QUESTIONS = {
    'against_24h': {
        'type': 'noul',
        'instructions': 'The trade in `action` goes against the 24-hour price move in `market_before.last_24_hours`: '
                        'it bought after Bitcoin fell, or sold after Bitcoin rose.',
        'criteria': {'true': 'Bought after a fall, or sold after a rise.',
                     'false': 'Bought after a rise, sold after a fall, or the market was roughly flat.'},
    },
    'regime': {
        'type': 'choice',
        'instructions': 'Which description best fits the market in `market_before` at the moment of the trade?',
        'criteria': {
            'uptrend': 'A steady climb over days and weeks without a violent spike.',
            'downtrend': 'A steady decline over days and weeks without a violent crash.',
            'range': 'Sideways: no clear direction over the past week, ordinary volume.',
            'selloff': 'A sharp, fast drop in the last hours or day, often on heavy volume.',
            'squeeze': 'A sharp, fast rise in the last hours or day, often on heavy volume.',
        },
    },
    'panic': {
        'type': 'noul',
        'instructions': 'At the moment of the trade, `market_before` shows panic selling: a sharp fall on unusually heavy volume.',
        'criteria': {'true': 'Sharp recent fall together with heavy or very heavy volume.',
                     'false': 'No sharp recent fall, or the fall happened on normal or light volume.'},
    },
    'boldness': {
        'type': 'score',
        'instructions': 'How bold is the trade in `action`, given the market in `market_before`?',
        'criteria': [
            'Cautious: a small, passive trade that reduces risk.',
            'Measured: an ordinary-sized trade placed patiently.',
            'Assertive: a larger trade or one that adds risk.',
            'Bold: a large trade that adds risk against a strong move.',
            'Very bold: a very large, fast trade into a violent market.',
        ],
    },
}


def jev(state):
    body = json.dumps({'model': MODEL, 'state': state, 'questions': QUESTIONS}).encode()
    req = urllib.request.Request('https://api.typesafe.ai/v1/systemone', data=body, method='POST',
                                 headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
    t0 = time.perf_counter()
    res = json.load(urllib.request.urlopen(req, timeout=60))
    return res, (time.perf_counter() - t0) * 1000


rng = np.random.default_rng(7)
A = A[A.start >= '2018-04-10']
sample = (A.assign(year=A.start.dt.year).sample(frac=1, random_state=7)
          .groupby(['year', 'kind']).head(2))
sample = sample.sample(n=min(40, len(sample)), random_state=7).sort_values('start')

rows, first = [], True
for _, a in sample.iterrows():
    ctx = context(a.start)
    if not ctx:
        continue
    market, r24 = ctx
    state = {'trader': 'One anonymous trader on BitMEX, 2018-2021, trading the XBTUSD inverse perpetual.',
             'time_utc': a.start.strftime('%Y-%m-%d %H:%M'), 'market_before': market, 'action': action(a)}
    res, ms = jev(state)
    ans = res['answers']
    truth = (a.side == 'Buy' and r24 < -1) or (a.side == 'Sell' and r24 > 1)
    rows.append({'start': str(a.start), 'kind': a.kind, 'side': a.side, 'r24': round(r24, 2),
                 'truth_against': truth, 'state': state, 'answers': ans, 'ms': round(ms),
                 'tokens': res.get('usage', {}).get('input_tokens')})
json.dump(rows, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print('calls', len(rows), 'model', res.get('model'))
