"""Rebuild XBTUSD flat-to-flat positions from fills, and fetch hourly candles."""
import glob, json, os, sys, time, urllib.request
import pandas as pd

root, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

cols = ['symbol', 'side', 'lastqty', 'lastpx', 'exectype', 'ordtype', 'lastliquidityind',
        'text', 'orderid', 'execcomm', 'timestamp']
x = pd.concat([pd.read_csv(f, usecols=cols, dtype=str, encoding='utf-8-sig')
               for f in sorted(glob.glob(os.path.join(root, 'aoa-execution-*.csv')))], ignore_index=True)
t = x[(x.exectype == 'Trade') & (x.symbol == 'XBTUSD')].copy()
t['ts'] = pd.to_datetime(t.timestamp)
t['qty'] = pd.to_numeric(t.lastqty) * t.side.map({'Buy': 1, 'Sell': -1})
t['px'] = pd.to_numeric(t.lastpx)
t = t.sort_values('ts', kind='stable').reset_index(drop=True)
t['pos'] = t.qty.cumsum()

# A position runs from the first fill after flat to the fill that returns it to flat (or flips it).
pos_id, cur, prev = [], 0, 0
for p in t.pos.to_numpy():
    if prev == 0:
        cur += 1
    pos_id.append(cur)
    if p != 0 and prev != 0 and (p > 0) != (prev > 0):  # flipped through zero
        cur += 1
    prev = p
t['pid'] = pos_id

# Inverse contract PnL in XBT: qty * (1/entry - 1/exit). Approximate with fill-level cash flow.
t['xbt_flow'] = t.qty / t.px  # buying USD contracts costs XBT at 1/px each
g = t.groupby('pid')
P = pd.DataFrame({
    'open': g.ts.first(), 'close': g.ts.last(),
    'side': g.qty.first().map(lambda q: 'long' if q > 0 else 'short'),
    'fills': g.size(), 'orders': g.orderid.nunique(),
    'max_size_usd': g.pos.apply(lambda s: s.abs().max()),
    'entry_px': g.apply(lambda d: (d.px * d.qty.abs())[d.qty * (1 if d.qty.iloc[0] > 0 else -1) > 0].sum()
                        / d.qty.abs()[d.qty * (1 if d.qty.iloc[0] > 0 else -1) > 0].sum()),
    'maker_share': g.lastliquidityind.apply(lambda s: (s == 'AddedLiquidity').mean()),
    'market_or_stop': g.ordtype.apply(lambda s: s.isin(['Market', 'Stop']).mean()),
    'liquidation': g.text.apply(lambda s: s.fillna('').str.contains('Liquidat').any()),
    'flat_at_end': g.pos.last() == 0,
    'pnl_xbt': g.xbt_flow.sum(),  # exact only for positions that end flat
})
P['hold_h'] = (P.close - P.open).dt.total_seconds() / 3600
P = P[P.flat_at_end]
P.to_parquet(os.path.join(out, 'positions_xbtusd.parquet'))
print('positions (flat-to-flat)', len(P))
print(P.groupby(P.open.dt.year).agg(n=('fills', 'size'), win=('pnl_xbt', lambda s: (s > 0).mean()),
                                    med_hold_h=('hold_h', 'median'), pnl=('pnl_xbt', 'sum')).round(3))

# Hourly candles from BitMEX's public REST API (no key needed).
path = os.path.join(out, 'xbtusd_1h.parquet')
if not os.path.exists(path):
    rows, start = [], pd.Timestamp('2018-02-20')
    end = pd.Timestamp('2022-01-01')
    while start < end:
        url = ('https://www.bitmex.com/api/v1/trade/bucketed?binSize=1h&symbol=XBTUSD&count=1000'
               f'&startTime={start.isoformat()}')
        batch = json.load(urllib.request.urlopen(url, timeout=30))
        if not batch:
            break
        rows += batch
        start = pd.Timestamp(batch[-1]['timestamp']).tz_localize(None) + pd.Timedelta(hours=1)
        time.sleep(1.2)
    c = pd.DataFrame(rows)[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    c['timestamp'] = pd.to_datetime(c.timestamp).dt.tz_localize(None)
    c.to_parquet(path)
    print('candles', len(c), c.timestamp.min(), c.timestamp.max())
