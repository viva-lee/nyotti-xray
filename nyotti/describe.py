"""Turn one decision into the plain-English state Jev reads.

Jev is a judgment model, not a calculator, so every number is computed here and handed over
as a named bucket with the figure attached ("fell sharply (-9.6%)"). Nothing after the decision
(later prices, the outcome) ever goes into the state. The trader is never named.
"""
import math

TRADER = 'One anonymous trader on BitMEX, 2018-2021, trading the XBTUSD inverse perpetual with Bitcoin as margin.'
EXPOSURE_NOTE = ('Bitcoin exposure 1.0x means the account moves like plain Bitcoin; 0x means it moves like '
                 'dollars; below 0 means it gains when Bitcoin falls; above 1 means leveraged long.')


def _ok(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def move(r, sharp=8, normal=3, drift=1):
    p = r * 100
    if p <= -sharp: return f'fell sharply ({p:+.1f}%)'
    if p <= -normal: return f'fell ({p:+.1f}%)'
    if p < -drift: return f'drifted lower ({p:+.1f}%)'
    if p <= drift: return f'was roughly flat ({p:+.1f}%)'
    if p < normal: return f'drifted higher ({p:+.1f}%)'
    if p < sharp: return f'rose ({p:+.1f}%)'
    return f'rose sharply ({p:+.1f}%)'


def ratio(x, what):
    if x >= 2.5: return f'{what} about {x:.1f}x its 30-day normal (very heavy)'
    if x >= 1.5: return f'{what} about {x:.1f}x its 30-day normal (heavy)'
    if x <= 0.6: return f'{what} about {x:.1f}x its 30-day normal (light)'
    return f'{what} near its 30-day normal'


def exposure(e):
    if e <= -0.25: return f'a net short bet on Bitcoin ({e:+.2f}x)'
    if e < 0.25: return f'parked in dollars: short contracts offset the Bitcoin held as margin ({e:+.2f}x)'
    if e < 0.85: return f'partly hedged: less exposure than simply holding Bitcoin ({e:.2f}x)'
    if e <= 1.15: return f'about the same as simply holding Bitcoin ({e:.2f}x)'
    return f'a leveraged long on Bitcoin ({e:.2f}x)'


def market(d):
    place = d.range_pos
    where = ('near its 30-day low' if place < .15 else 'near its 30-day high' if place > .85
             else 'in the lower half of its 30-day range' if place < .5 else 'in the upper half of its 30-day range')
    return {
        'last_6_hours': f'Bitcoin {move(d.r6h, 5, 2, 0.7)}',
        'last_24_hours': f'Bitcoin {move(d.r24h)}',
        'last_7_days': f'Bitcoin {move(d.r7d, 15, 5, 2)}',
        'last_30_days': f'Bitcoin {move(d.r30d, 25, 8, 3)}',
        'range_position': f'Price is {where}',
        'volume_last_24_hours': ratio(d.volume_ratio, 'Trading volume was'),
        'volatility_last_24_hours': ratio(d.volatility_ratio, 'Hourly volatility was'),
    }


def account(d):
    out = {}
    if _ok(d.equity_24h):
        out['equity_last_24_hours'] = f'His account equity {move(d.equity_24h, 10, 4, 1.5)}'
    if _ok(d.equity_7d):
        out['equity_last_7_days'] = f'His account equity {move(d.equity_7d, 20, 8, 3)}'
    if _ok(d.drawdown_30d):
        dd = -d.drawdown_30d * 100
        out['from_30_day_peak'] = ('His account was at or near its 30-day peak' if dd < 2
                                   else f'His account was {dd:.0f}% below its 30-day peak')
    if _ok(d.exposure_before):
        out['bitcoin_exposure'] = f'Overall the account was {exposure(d.exposure_before)}'
    return out


def side_word(p):
    return 'flat' if p == 0 else ('net long' if p > 0 else 'net short')


def action(d):
    b, a = d.pos_before, d.pos_after
    if d.kind == 'open': effect = f'opened a new position, leaving him {side_word(a)}'
    elif d.kind == 'close': effect = f'closed his whole position (was {side_word(b)}), leaving him flat'
    elif d.kind == 'flip':
        bigger = 'a larger' if abs(a) > abs(b) else 'a smaller'
        effect = f'flipped from {side_word(b)} to {bigger} {side_word(a)} position'
    elif d.kind == 'add': effect = f'added to his {side_word(b)} position'
    else: effect = f'reduced his {side_word(b)} position'
    rel = d.size_rel
    size = ('much larger than' if rel >= 3 else 'larger than' if rel >= 1.5 else
            'much smaller than' if rel <= 1 / 3 else 'smaller than' if rel <= 2 / 3 else 'about the same as')
    mins = max(1, round(d.minutes))
    out = {
        'direction': 'bought Bitcoin perpetual contracts' if d.side == 'Buy' else 'sold Bitcoin perpetual contracts',
        'effect_on_contracts': effect,
        'size': f'{size} his typical trade that year',
        'execution': ('mostly resting limit orders that waited to be filled' if d.maker >= .7 else
                      'mostly orders that took liquidity immediately' if d.maker <= .3 else
                      'a mix of resting and immediate orders'),
        'duration': f'filled over about {mins} minute{"s" if mins != 1 else ""}',
    }
    if _ok(d.exposure_before) and _ok(d.exposure_after):
        out['effect_on_bitcoin_exposure'] = (f'moved the account from {d.exposure_before:+.2f}x to '
                                             f'{d.exposure_after:+.2f}x Bitcoin exposure')
    return out


def state(d):
    return {
        'trader': TRADER,
        'time_utc': d.start.strftime('%Y-%m-%d %H:%M'),
        'market_before': market(d),
        'account_before': account(d),
        'action': action(d),
        'note': EXPOSURE_NOTE,
    }
