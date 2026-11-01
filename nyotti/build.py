"""Derive the tables every analysis and the viewer read: market candles, the account book, decisions."""
import json
import time
import urllib.request

import numpy as np
import pandas as pd

from . import load
from .paths import CACHE

START, END = pd.Timestamp('2018-03-01'), pd.Timestamp('2022-01-01')
DECISION_GAP = pd.Timedelta(minutes=20)


# ---------------------------------------------------------------- market

def candles(symbol='XBTUSD'):
    """Hourly OHLCV from BitMEX's public REST API, indexed by the hour each candle starts."""
    path = CACHE / f'candles_{symbol}_1h.parquet'
    if path.exists():
        return pd.read_parquet(path)
    rows, start = [], START - pd.Timedelta(days=40)
    while start < END:
        url = ('https://www.bitmex.com/api/v1/trade/bucketed?binSize=1h&count=1000'
               f'&symbol={symbol}&startTime={start.isoformat()}')
        batch = json.load(urllib.request.urlopen(url, timeout=30))
        if not batch:
            break
        rows += batch
        start = pd.Timestamp(batch[-1]['timestamp']).tz_localize(None) + pd.Timedelta(hours=1)
        time.sleep(2.1)  # stay under the anonymous rate limit
    c = pd.DataFrame(rows)[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    # BitMEX stamps a bucket with its END time.
    c['timestamp'] = pd.to_datetime(c.timestamp).dt.tz_localize(None) - pd.Timedelta(hours=1)
    c = c.drop_duplicates('timestamp').set_index('timestamp').sort_index()
    c.to_parquet(path)
    return c


# ---------------------------------------------------------------- account

def is_xbt_inverse(symbol):
    """XBTUSD and the dated XBT futures: $1 contracts, margined and settled in BTC."""
    return symbol.startswith('XBT') and not symbol.startswith('XBT7D')


def multipliers(x):
    """BTC value of one linear or quanto contract per unit of price (1 for XRPU18, 1e-6 for ETHUSD)."""
    t = x[(x.exectype == 'Trade') & (x.lastqty > 0) & (x.lastpx > 0)]
    return (t.execcost.abs() / (t.lastqty * t.lastpx) / 1e8).groupby(t.symbol.astype(str), observed=True).median()


def book(x):
    """Replay every fill and settlement through an average-cost book, one per symbol.

    Inverse (XBT) contracts: n contracts entered at p cost n/p BTC, unrealised at P is cost - n/P.
    Linear and quanto contracts: n contracts at p cost n*p*m BTC, unrealised at P is n*P*m - cost.
    Closing k contracts realises the matching share of the cost. Returns one row per fill.
    """
    mult = multipliers(x).to_dict()
    t = x[x.exectype.isin(['Trade', 'Settlement']) & (x.lastqty > 0) & (x.lastpx > 0)].copy()
    t['q'] = np.where(t.side == 'Buy', t.lastqty, -t.lastqty)
    books = {}
    realized = xbt_net = 0.0
    out = []
    for sym, q, p in zip(t.symbol.astype(str).to_numpy(), t.q.to_numpy(), t.lastpx.to_numpy()):
        inv = is_xbt_inverse(sym)
        m = mult.get(sym, 1.0)
        cost = (lambda k: k / p) if inv else (lambda k: k * p * m)
        n, c = books.get(sym, (0.0, 0.0))
        before = n
        if n == 0 or (q > 0) == (n > 0):
            n, c = n + q, c + cost(q)
        else:
            k = min(abs(q), abs(n))
            ck = c * k / abs(n)
            nk = k if n > 0 else -k
            realized += (ck - cost(nk)) if inv else (cost(nk) - ck)
            n, c = n - nk, c - ck
            rest = abs(q) - k
            if rest > 0:
                n = rest if q > 0 else -rest
                c = cost(n)
        if abs(n) < 1e-9:
            n, c = 0.0, 0.0
        books[sym] = (n, c)
        if inv:
            xbt_net += n - before
        out.append((n, c, realized, xbt_net))
    t[['n', 'cost', 'realized', 'xbt_net']] = np.array(out)
    return t[['ts', 'symbol', 'side', 'q', 'lastpx', 'n', 'cost', 'realized', 'xbt_net']].reset_index(drop=True), mult


def account(x, w, px):
    """Hourly account: BTC equity, XBT net contracts, effective leverage and BTC exposure.

    equity   = deposits - withdrawals + realised (all fills) - fees and funding + unrealised (all symbols)
    leverage = XBT net contracts / (price * equity)     signed; short < 0
    exposure = 1 + leverage    1 = like holding BTC, 0 = parked in dollars, < 0 = net short BTC
    alt      = signed BTC notional of every non-XBT position / equity
    gross_leverage = (|XBT notional| + |every altcoin notional|) / equity
    """
    from . import marks as marks_mod
    bk, mult = book(x)
    hours = pd.date_range(START, END, freq='1h', inclusive='left')
    marks = marks_mod.hourly(x[x.exectype == 'Trade'], hours)
    h = pd.DataFrame(index=hours)
    h['price'] = px.close.reindex(hours).ffill()

    per = bk.assign(hour=bk.ts.dt.floor('1h'), symbol=bk.symbol.astype(str))
    pos = per.groupby(['hour', 'symbol'])[['n', 'cost']].last().unstack('symbol')
    n = pos['n'].reindex(hours).ffill().fillna(0.0)
    c = pos['cost'].reindex(hours).ffill().fillna(0.0)
    unreal = pd.DataFrame(0.0, index=hours, columns=n.columns)
    alt = pd.Series(0.0, index=hours)
    alt_gross = pd.Series(0.0, index=hours)
    for sym in n.columns:
        mk = h.price if sym == 'XBTUSD' else marks[sym].fillna(h.price if is_xbt_inverse(sym) else np.nan)
        if is_xbt_inverse(sym):
            unreal[sym] = c[sym] - n[sym] / mk
        else:
            unreal[sym] = (n[sym] * mk * mult.get(sym, 1.0) - c[sym]).fillna(0.0)
            alt += (n[sym] * mk * mult.get(sym, 1.0)).fillna(0.0)
            alt_gross += (n[sym] * mk * mult.get(sym, 1.0)).abs().fillna(0.0)
    unreal = unreal.where(n != 0, 0.0)
    h['unrealized'] = unreal.sum(axis=1)
    h['unrealized_alt'] = unreal[[s for s in n.columns if not is_xbt_inverse(s)]].sum(axis=1)
    last = bk.set_index('ts')[['realized', 'xbt_net']].groupby(level=0).last().resample('1h').last()
    h = h.join(last.reindex(hours).ffill().fillna(0.0))
    h = h.rename(columns={'xbt_net': 'net'})

    fees = (x.set_index('ts').execcomm.fillna(0) / 1e8).resample('1h').sum()  # trading fees and funding
    h['fees'] = fees.reindex(hours).fillna(0).cumsum()
    # The release lost the hour of each transfer (Excel kept only mm:ss). Count deposits from the
    # start of their day and withdrawals from its end, so equity is never drained before it existed.
    fl = w[w.transacttype.isin(['Deposit', 'Withdrawal'])].copy()
    fl['at'] = fl.day + np.where(fl.transacttype == 'Withdrawal', pd.Timedelta(hours=23), pd.Timedelta(0))
    flows = fl.set_index('at').btc.resample('1h').sum()
    h['flows'] = flows.reindex(hours).fillna(0).cumsum()
    h['equity'] = h.flows + h.realized - h.fees + h.unrealized
    h['leverage'] = h.net / (h.price * h.equity)
    h['exposure'] = 1 + h.leverage
    h['alt'] = alt / h.equity
    h['gross_leverage'] = (h.net.abs() / h.price + alt_gross) / h.equity
    h.loc[h.equity <= 0, ['leverage', 'exposure', 'alt', 'gross_leverage']] = np.nan
    h.attrs['tape_hours'] = marks.attrs.get('tape_hours', 0)
    return h, bk


# ---------------------------------------------------------------- decisions

def decisions(x, h, px, book):
    """Group XBTUSD fills into decisions: same side, no gap longer than 20 minutes."""
    t = x[(x.exectype == 'Trade') & (x.symbol == 'XBTUSD')].copy()
    t['q'] = np.where(t.side == 'Buy', t.lastqty, -t.lastqty)
    t['pos'] = t.q.cumsum()
    new = (t.ts.diff() > DECISION_GAP) | (t.side != t.side.shift())
    t['did'] = new.cumsum() - 1
    text = t.text.astype(str)
    t['maker'] = t.lastliquidityind == 'AddedLiquidity'
    t['amended'] = text.str.contains('Amend')
    t['stop'] = t.ordtype.isin(['Stop', 'StopLimit'])
    t['postonly'] = t.execinst.astype(str).str.contains('ParticipateDoNotInitiate')
    t['notional'] = t.lastpx * t.lastqty
    g = t.groupby('did')
    d = pd.DataFrame({
        'start': g.ts.first(), 'end': g.ts.last(), 'side': g.side.first().astype(str),
        'qty': g.q.sum(), 'fills': g.size(), 'orders': g.orderid.nunique(),
        'vwap': g.notional.sum() / g.lastqty.sum(),
        'pos_before': g.pos.first() - g.q.first(), 'pos_after': g.pos.last(),
        'maker': g.maker.mean(), 'amended': g.amended.mean(), 'stop': g.stop.mean(), 'postonly': g.postonly.mean(),
    })
    d['size_usd'] = d.qty.abs()
    b, a = d.pos_before, d.pos_after
    d['kind'] = np.select(
        [b == 0, a == 0, (np.sign(b) != np.sign(a)) & (a != 0), a.abs() > b.abs()],
        ['open', 'close', 'flip', 'add'], 'reduce')
    d['minutes'] = (d.end - d.start).dt.total_seconds() / 60
    d['gap_hours'] = (d.start - d.end.shift()).dt.total_seconds() / 3600
    d['year'] = d.start.dt.year
    d['size_rel'] = d.size_usd / d.groupby('year').size_usd.transform('median')

    # Account state just before the decision, and its effect on BTC exposure. Net contracts come
    # from the fill-level book (all XBT contracts) so an earlier decision in the same hour counts.
    hour = d.start.dt.floor('1h') - pd.Timedelta(hours=1)
    acct = h.reindex(hour)
    d['equity'] = acct.equity.to_numpy()
    bt, bn = book.ts.to_numpy(), book.xbt_net.to_numpy()
    i0 = np.searchsorted(bt, d.start.to_numpy(), side='left') - 1
    i1 = np.searchsorted(bt, d.end.to_numpy(), side='right') - 1
    d['xbt_net_before'] = np.where(i0 >= 0, bn[np.clip(i0, 0, None)], 0.0)
    d['xbt_net_after'] = bn[i1]
    lev = lambda n: n / (d.vwap * d.equity)
    d['exposure_before'] = 1 + lev(d.xbt_net_before)
    d['exposure_after'] = 1 + lev(d.xbt_net_after)
    d.loc[d.equity <= 0, ['exposure_before', 'exposure_after']] = np.nan
    eq = h.equity
    d['equity_24h'] = (acct.equity.to_numpy() / eq.reindex(hour - pd.Timedelta(hours=24)).to_numpy() - 1)
    d['equity_7d'] = (acct.equity.to_numpy() / eq.reindex(hour - pd.Timedelta(days=7)).to_numpy() - 1)
    peak = eq.rolling('30D').max()
    d['drawdown_30d'] = acct.equity.to_numpy() / peak.reindex(hour).to_numpy() - 1

    # Market just before the decision: only candles that had closed.
    c = px.close
    def ret(lag):
        return (c.reindex(hour).to_numpy() / c.reindex(hour - lag).to_numpy() - 1)
    d['r6h'], d['r24h'] = ret(pd.Timedelta(hours=5)), ret(pd.Timedelta(hours=23))
    d['r7d'], d['r30d'] = ret(pd.Timedelta(days=7)), ret(pd.Timedelta(days=30))
    hi30 = px.high.rolling(720).max().reindex(hour).to_numpy()
    lo30 = px.low.rolling(720).min().reindex(hour).to_numpy()
    d['range_pos'] = (c.reindex(hour).to_numpy() - lo30) / (hi30 - lo30)
    vol24 = px.volume.rolling(24).mean() / px.volume.rolling(720).mean()
    rets = c.pct_change()
    rv24 = rets.rolling(24).std() / rets.rolling(720).std()
    d['volume_ratio'] = vol24.reindex(hour).to_numpy()
    d['volatility_ratio'] = rv24.reindex(hour).to_numpy()

    # Hindsight, for analyses only. Never sent to Jev.
    after = d.end.dt.floor('1h') + pd.Timedelta(hours=1)
    for name, lag in (('1h', 0), ('24h', 23), ('7d', 167)):
        p_later = c.reindex(after + pd.Timedelta(hours=lag)).to_numpy()
        d[f'next_{name}'] = p_later / d.vwap - 1
        d[f'pnl_{name}_btc'] = d.qty * (1 / d.vwap - 1 / p_later)
    d.index.name = 'id'
    return d.reset_index()


def run(log=print):
    x = load.executions()
    w = load.wallet()
    px = candles('XBTUSD')
    log(f'candles: {len(px)} hourly XBTUSD bars')
    h, book = account(x, w, px)
    h.to_parquet(CACHE / 'account_hourly.parquet')
    book.to_parquet(CACHE / 'book.parquet')
    wallet_pnl = w[w.transacttype == 'RealisedPNL'].btc.sum()
    log(f'account: realised from fills {book.realized.iloc[-1]:.2f} BTC, fees and funding {h.fees.iloc[-1]:.2f} BTC, '
        f'net {book.realized.iloc[-1] - h.fees.iloc[-1]:.2f} vs wallet RealisedPNL {wallet_pnl:.2f}; '
        f'final equity {h.equity.iloc[-1]:.2f} BTC (wallet {w.balance.iloc[-1]:.2f} + unrealised '
        f'{h.unrealized.iloc[-1]:.2f}); marks from tape for {h.attrs["tape_hours"]} hours')
    d = decisions(x, h, px, book)
    d.to_parquet(CACHE / 'decisions_xbtusd.parquet')
    log(f'decisions: {len(d)} XBTUSD decisions')

