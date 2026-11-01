"""How does his XBTUSD exposure behave over time, and what is a sensible decision unit?"""
import glob, os, sys
import numpy as np
import pandas as pd

root, out = sys.argv[1], sys.argv[2]
cols = ['symbol', 'side', 'lastqty', 'lastpx', 'exectype', 'ordtype', 'lastliquidityind', 'orderid', 'timestamp']
x = pd.concat([pd.read_csv(f, usecols=cols, dtype=str, encoding='utf-8-sig')
               for f in sorted(glob.glob(os.path.join(root, 'aoa-execution-*.csv')))], ignore_index=True)
t = x[(x.exectype == 'Trade') & (x.symbol == 'XBTUSD')].copy()
t['ts'] = pd.to_datetime(t.timestamp)
t['qty'] = pd.to_numeric(t.lastqty) * t.side.map({'Buy': 1, 'Sell': -1})
t['px'] = pd.to_numeric(t.lastpx)
t = t.sort_values('ts', kind='stable').reset_index(drop=True)
t['pos'] = t.qty.cumsum()

# Exposure sampled hourly (last value in each hour, forward filled).
h = t.set_index('ts').pos.resample('1h').last().ffill()
yr = h.groupby(h.index.year)
print('hourly net XBTUSD exposure (USD contracts)')
print(pd.DataFrame({
    'share_flat': yr.apply(lambda s: (s == 0).mean()),
    'share_long': yr.apply(lambda s: (s > 0).mean()),
    'share_short': yr.apply(lambda s: (s < 0).mean()),
    'median_abs': yr.apply(lambda s: s.abs().median()),
    'p95_abs': yr.apply(lambda s: s.abs().quantile(.95)),
}).round(3).to_string())

# Decision unit: consecutive fills with gaps under 20 minutes and the same side form one "action".
gap = t.ts.diff().dt.total_seconds().fillna(1e9)
new = (gap > 20 * 60) | (t.side != t.side.shift())
t['aid'] = new.cumsum()
g = t.groupby('aid')
A = pd.DataFrame({
    'start': g.ts.first(), 'end': g.ts.last(), 'side': g.side.first(),
    'qty': g.qty.sum(), 'fills': g.size(), 'orders': g.orderid.nunique(),
    'vwap': g.apply(lambda d: (d.px * d.qty.abs()).sum() / d.qty.abs().sum(), include_groups=False),
    'pos_before': g.pos.first() - g.qty.first(), 'pos_after': g.pos.last(),
    'maker': g.lastliquidityind.apply(lambda s: (s == 'AddedLiquidity').mean()),
})
before, after = A.pos_before, A.pos_after
A['kind'] = np.select(
    [(before == 0), (after == 0), (np.sign(before) != np.sign(after)) & (after != 0),
     after.abs() > before.abs()],
    ['open', 'close', 'flip', 'add'], 'reduce')
A['size_usd'] = A.qty.abs()
print('\nactions', len(A))
print(A.groupby([A.start.dt.year, 'kind']).size().unstack(fill_value=0).to_string())
print('\nmedian action size (USD) by year\n', A.groupby(A.start.dt.year).size_usd.median().to_string())
A.to_parquet(os.path.join(out, 'actions_xbtusd.parquet'))
