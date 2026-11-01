import glob, os, sys
import pandas as pd

root = sys.argv[1]
cols = ['date', 'symbol', 'side', 'lastqty', 'lastpx', 'lastliquidityind', 'exectype', 'ordtype',
        'execinst', 'text', 'trdmatchid', 'orderid', 'homenotional', 'foreignnotional', 'timestamp']
frames = []
for f in sorted(glob.glob(os.path.join(root, 'aoa-execution-*.csv'))):
    d = pd.read_csv(f, usecols=cols, dtype=str, encoding='utf-8-sig')
    print(os.path.basename(f), len(d))
    frames.append(d)
x = pd.concat(frames, ignore_index=True)
print('rows', len(x))
print('\nexectype\n', x.exectype.value_counts().to_string())
t = x[x.exectype == 'Trade'].copy()
print('\ntrade fills', len(t), 'orders', t.orderid.nunique(), 'symbols', t.symbol.nunique())
print('\nordtype\n', t.ordtype.value_counts().to_string())
print('\nliquidity\n', t.lastliquidityind.value_counts(normalize=True).round(4).to_string())
print('\ntop symbols (fills)\n', t.symbol.value_counts().head(8).to_string())
t['ts'] = pd.to_datetime(t.timestamp, errors='coerce')
print('\nrange', t.ts.min(), '->', t.ts.max(), 'days with fills', t.ts.dt.date.nunique())
print('\nfills by year\n', t.ts.dt.year.value_counts().sort_index().to_string())
liq = t.text.fillna('').str.contains('Liquidat', case=False)
print('\nliquidation fills', int(liq.sum()), 'orders', t[liq].orderid.nunique(),
      'days', t[liq].ts.dt.date.nunique())
print('trdmatchid null', int(t.trdmatchid.isna().sum()), 'dup', int(t.trdmatchid.duplicated().sum()))
t['usd'] = pd.to_numeric(t.foreignnotional, errors='coerce').abs()
xbt = t[t.symbol == 'XBTUSD']
print('\nXBTUSD fills', len(xbt), 'share', round(len(xbt) / len(t), 3),
      'USD notional total %.3e' % xbt.usd.sum())
hours = t.ts.dt.hour.value_counts().sort_index()
print('\nfills by UTC hour\n', hours.to_string())

w = pd.read_csv(os.path.join(root, 'aoa-wallet-2018-03-01-2021-12-31.csv'), dtype=str, encoding='utf-8-sig')
w['amt'] = pd.to_numeric(w.amount, errors='coerce') / 1e8
print('\nwallet rows', len(w))
print(w.groupby('transacttype').amt.agg(['count', 'sum']).round(3).to_string())
