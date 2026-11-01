"""What the atlas page (site/atlas.html) loads besides the cards: chapters, and the raw units its dots stand for.

Every dot in the atlas is one real unit from the record: a day, an order, a decision, a bitcoin, or a sampled
piece of a closed position. This module writes those units as compact columns. Nothing here looks past 2021.
"""
import numpy as np
import pandas as pd

from .analyses import btc_value, bucket
from .analyses.behavior import add_entries
from .analyses.position import drawdowns
from .analyses.proof import tape_days
from .analyses.risk import distance
from .judge import CHECKS

T0 = pd.Timestamp('2018-03-05')

CHAPTERS = [
    ('proof', {'en': 'Proof', 'ko': '증거'}, {'en': 'Is the record real?', 'ko': '기록은 진짜인가?'},
     ['verified', 'by-hand', 'ledger']),
    ('money', {'en': 'Money', 'ko': '돈'},
     {'en': 'Where did the bitcoin come from, and where did it go?', 'ko': '비트코인은 어디서 와서 어디로 갔나?'},
     ['transfers', 'by-coin', 'funding', 'concentration', 'payday']),
    ('position', {'en': 'Position', 'ko': '포지션'}, {'en': 'Was the account Bitcoin, or dollars?', 'ko': '계좌는 비트코인이었나, 달러였나?'},
     ['short-is-not-bearish', 'account-shape', 'two-currencies']),
    ('risk', {'en': 'Risk', 'ko': '위험'}, {'en': 'How close did it come to zero?', 'ko': '0에 얼마나 가까이 갔나?'},
     ['leverage', 'liquidations', 'year-2018', 'distance-to-zero', 'worst-day']),
    ('habits', {'en': 'Habits', 'ko': '습관'},
     {'en': 'How did he place orders, and how long did he hold?', 'ko': '어떻게 주문했고, 얼마나 들고 있었나?'},
     ['scalps-to-swings', 'order-craft', 'plain-orders', 'winners-first', 'underwater-adds', 'clock']),
    ('mind', {'en': 'Mind', 'ko': '판단'}, {'en': 'What did the market look like when he acted?', 'ko': '그가 움직일 때 시장은 어땠나?'},
     ['jev-check', 'regimes', 'into-the-panic', 'tilt-check', 'after-the-worst-days', 'after-the-best-days']),
    ('market', {'en': 'Market', 'ko': '시장'}, {'en': 'How big was he on the exchange?', 'ko': '거래소에서 그는 얼마나 컸나?'},
     ['footprint', 'black-thursday']),
]
NEW = {'ledger', 'payday', 'account-shape', 'two-currencies', 'year-2018', 'distance-to-zero', 'plain-orders',
       'winners-first', 'underwater-adds', 'after-the-best-days'}
SOURCES = ['website', 'amended', 'close', 'stop', 'liquidation']


def chapter_of():
    return {cid: key for key, _, _, ids in CHAPTERS for cid in ids}


def col(s, digits):
    """A column as a JSON list, NaN and inf as null."""
    v = np.asarray(s, dtype=float)
    return [None if not np.isfinite(x) else (int(round(x)) if digits == 0 else round(float(x), digits)) for x in v]


def days(ctx, cards):
    by_id = {c['id']: c for c in cards}
    d = ctx.daily
    d = d[(d.index >= T0) & (d.index < '2022-01-01')]
    idx = d.index
    h = ctx.h
    e = h.exposure.resample('1D').median().reindex(idx)
    frac, side = distance(h.exposure)
    hz = pd.DataFrame({'d': frac * side, 'a': frac}, index=h.index).replace([np.inf, -np.inf], np.nan)
    # Closest hour of each day, signed: + a fall would empty the account, - a rise would.
    dz = hz.groupby(hz.index.floor('1D')).apply(lambda g: g.d[g.a.idxmin()] if g.a.notna().any() else np.nan).reindex(idx)
    tape = pd.Series({t['day']: t['totals'].get('XBTUSD', [0, 0, 0])[1] for t in tape_days() if not t.get('missing')})
    tape.index = pd.to_datetime(tape.index)
    xf = ctx.f[ctx.f.symbol == 'XBTUSD']
    share = (xf.groupby(xf.ts.dt.floor('1D')).lastqty.sum() / tape).reindex(idx)
    v = by_id['verified']['chart']
    ver = pd.DataFrame({'total': v['total'], 'ok': v['ok']}, index=pd.to_datetime(v['days'])).reindex(idx).fillna(0)
    w = ctx.w
    pnl = w[w.transacttype == 'RealisedPNL'].groupby('day').btc.sum().reindex(idx)
    wd = (-w[w.transacttype == 'Withdrawal'].groupby('day').btc.sum()).reindex(idx).fillna(0)
    dec = ctx.d.groupby(ctx.d.start.dt.floor('1D')).size().reindex(idx).fillna(0)
    base = dec.rolling(30, min_periods=10).median()
    with np.errstate(divide='ignore', invalid='ignore'):
        act = dec.shift(-1) / base
    dd = drawdowns(ctx).reindex(idx)
    return {
        'start': str(idx[0].date()), 'n': len(idx),
        'price': col(d.price, 0), 'eq': col(d.equity, 2), 'usd': col(d.usd / 1e6, 3), 'exp': col(e, 2),
        'bucket': col(bucket(e), 0), 'dz': col(dz, 3), 'lev': col(h.gross_leverage.resample('1D').max().reindex(idx), 2),
        'share': col(share, 5), 'fills': col(ver.total, 0), 'ok': col(ver.ok, 0), 'pnl': col(pnl, 3), 'r': col(d.r_btc, 4),
        'dd_btc': col(dd.btc, 4), 'dd_usd': col(dd.usd, 4), 'wd': col(wd, 3), 'dec': col(dec, 0), 'act': col(act, 3),
    }


def orders(ctx):
    o = ctx.orders
    flag = o.active.astype(int) + 2 * o.hidden.astype(int) + 4 * (o.ordtype == 'Market').astype(int)
    return {
        't': [int(v) for v in ((o.ts - T0) / pd.Timedelta(minutes=1)).astype(int)],
        'lu': col(np.log10(o.usd.clip(lower=1)), 2), 'src': [SOURCES.index(s) for s in o.source],
        'flag': [int(v) for v in flag], 'mk': col(o.maker, 1), 'sources': SOURCES,
    }


def decision_extras(ctx):
    """Extra columns for each decision, in the same order as decisions.json."""
    d = ctx.d
    hour = d.start.dt.floor('1h') - pd.Timedelta(hours=1)
    entry = add_entries(ctx)
    long_ = d.pos_before > 0
    gap = np.where(long_, 1 - d.vwap / entry, d.vwap / entry - 1) * 100  # > 0: the price was already against the position
    gap = np.where(d.kind == 'add', gap, np.nan)
    # The code answer to "against the 24h move" (0 against, 1 roughly flat, 2 with the move), exactly as the cards count it.
    against = CHECKS['against_move'](d).to_numpy()
    with_move = (((d.side == 'Buy') & (d.r24h > 0.01)) | ((d.side == 'Sell') & (d.r24h < -0.01))).to_numpy()
    move = np.where(against, 0, np.where(with_move, 2, 1))
    move = np.where(d.r24h.isna().to_numpy(), -1, move)
    return {
        'r24': col(d.r24h * 100, 1), 'vol': col(d.volume_ratio, 2), 'rel': col(d.size_rel, 2),
        'lev': col(ctx.h.gross_leverage.reindex(hour).to_numpy(), 2), 'gap': col(np.clip(gap, -20, 20), 2), 'mk': col(d.maker, 1),
        'move': [int(v) for v in move],
    }


def lots(ctx, per_year=2000, seed=7):
    """A contract-weighted sample of closed pieces per year: each dot stands for an equal share of that year's contracts."""
    rng = np.random.default_rng(seed)
    out = {}
    for name, m in (('fifo', ctx.lots_fifo), ('lifo', ctx.lots_lifo)):
        if name == 'lifo':
            m = m[m.pnl != 0]
        ys, hs, ws = [], [], []
        years = sorted(m.year.unique())
        for i, y in enumerate(years):
            g = m[m.year == y]
            pick = rng.choice(len(g), size=per_year, replace=True, p=(g.qty / g.qty.sum()).to_numpy())
            ys += [i] * per_year
            hs += col(np.clip(g.hours.to_numpy()[pick], 1 / 60, None), 4)
            ws += [int(v > 0) for v in g.pnl.to_numpy()[pick]]
        out[name] = {'years': [int(y) for y in years], 'y': ys, 'h': hs}
        if name == 'lifo':
            out[name]['w'] = ws
    return out


def short_hours(ctx):
    h = ctx.h[ctx.h.index >= '2019-01-01'].dropna(subset=['exposure'])
    return col(h.exposure[h.net < 0], 2)


def liquidation_events(ctx):
    f = ctx.f
    liq = f[f.text.astype(str).str.contains('Liquidation')].assign(btc=btc_value)
    ev = (liq.groupby([liq.ts.dt.floor('1min'), liq.symbol.astype(str)])
          .agg(qty=('lastqty', 'sum'), btc=('btc', 'sum')).reset_index())
    return [{'t': int((r.ts - T0) / pd.Timedelta(minutes=1)), 'sym': r.symbol, 'qty': float(r.qty), 'btc': round(float(r.btc), 3)}
            for r in ev.itertuples()]


def build(ctx, cards):
    return {
        't0': T0.isoformat(),
        'chapters': [{'key': k, 'title': t, 'question': q, 'cards': ids} for k, t, q, ids in CHAPTERS],
        'days': days(ctx, cards), 'orders': orders(ctx), 'dx': decision_extras(ctx), 'lots': lots(ctx),
        'short_hours': short_hours(ctx), 'liq': liquidation_events(ctx),
    }
