"""Each analysis takes the shared Context and returns one card for the viewer.

A card is plain JSON: {id, title{en,ko}, stat{value, unit, label{en,ko}}, body{en,ko}, chart, numbers}.
Every figure in a card's text is computed in the same function, never typed by hand. Cards describe
what happened in 2018-2021; none of them says anything about what to do in a market.
"""
from collections import deque
from functools import cached_property

import numpy as np
import pandas as pd

from .. import load
from ..paths import CACHE

# Account Bitcoin exposure buckets, the same cut points describe.exposure() uses for Jev.
BUCKETS = ['short', 'dollars', 'hedged', 'bitcoin', 'leveraged']


def bucket(e):
    """0 net short bet (<= -0.25x), 1 parked in dollars, 2 partly hedged, 3 like Bitcoin (0.85-1.15x), 4 leveraged long."""
    e = np.asarray(e, dtype=float)
    out = np.select([e <= -0.25, e < 0.25, e < 0.85, e <= 1.15], [0, 1, 2, 3], 4).astype(float)
    out[np.isnan(e)] = np.nan
    return out


def usd_notional(f):
    """USD value of each fill: USD- and USDT-quoted contracts directly, BTC-quoted alt futures via the BTC price."""
    sym = f.symbol.astype(str)
    usd_quoted = sym.str.startswith('XBT') | sym.str.contains('USD')
    return np.where(usd_quoted, f.foreignnotional.abs(), f.foreignnotional.abs() * f.btc_price)


def btc_value(f):
    """BTC value of each fill for every contract type. homeNotional is BTC only for XBT contracts (XRP for
    XRPU18), but execCost is booked in satoshis for inverse, linear and quanto contracts alike."""
    return f.execcost.abs() / 1e8


def match_lots(t, lifo=False):
    """Pair every closing contract with an opening one, oldest first (FIFO) or newest first (LIFO).

    `t` holds one symbol's fills in time order (ts, side, lastqty, lastpx). Returns one row per matched
    piece: when it closed, when its opening lot was entered, contracts, the opening lot's direction
    (+1 long, -1 short), entry and exit price, and the piece's PnL in BTC for an inverse contract.
    """
    lots, out = deque(), []
    take = lots.pop if lifo else lots.popleft
    end = -1 if lifo else 0
    for q, ts, px in zip(np.where(t.side == 'Buy', t.lastqty, -t.lastqty).astype(float), t.ts.to_numpy(),
                         t.lastpx.to_numpy()):
        while q != 0 and lots and (lots[end][0] > 0) != (q > 0):
            lq, lts, lpx = lots[end]
            k = min(abs(q), abs(lq))
            sign = 1.0 if lq > 0 else -1.0
            out.append((ts, lts, k, sign, lpx, px))
            lq -= sign * k
            q += sign * k
            if lq == 0:
                take()
            else:
                lots[end] = (lq, lts, lpx)
        if q != 0:
            lots.append((q, ts, px))
    m = pd.DataFrame(out, columns=['ts', 'entry_ts', 'qty', 'dir', 'entry_px', 'exit_px'])
    m['pnl'] = m.dir * m.qty * (1 / m.entry_px - 1 / m.exit_px)
    m['hours'] = (m.ts - m.entry_ts) / pd.Timedelta(hours=1)
    m['year'] = m.ts.dt.year
    return m


def wmedian(values, weights):
    """Weighted median: the value where half the weight sits below."""
    o = np.argsort(np.asarray(values, dtype=float))
    v, w = np.asarray(values, dtype=float)[o], np.asarray(weights, dtype=float)[o]
    c = np.cumsum(w)
    return float(v[np.searchsorted(c, c[-1] / 2)])


class Context:
    @cached_property
    def x(self):
        return load.executions()

    @cached_property
    def f(self):
        x = self.x
        return x[x.exectype == 'Trade'].reset_index(drop=True)

    @cached_property
    def w(self):
        return load.wallet()

    @cached_property
    def h(self):
        h = pd.read_parquet(CACHE / 'account_hourly.parquet')
        return h[h.index >= '2018-03-05']

    @cached_property
    def d(self):
        return pd.read_parquet(CACHE / 'decisions_xbtusd.parquet')

    @cached_property
    def j(self):
        path = CACHE / 'judgments.parquet'
        return pd.read_parquet(path) if path.exists() else None

    @cached_property
    def daily_return(self):
        """Mark-to-market daily return of the whole account, transfers removed."""
        eq = self.h.equity.resample('1D').last()
        flow = self.h.flows.resample('1D').last().diff().fillna(0)
        r = (eq.diff() - flow) / eq.shift()
        return r[eq.shift() > 1].dropna()

    @cached_property
    def daily(self):
        """One row per day: closing equity in BTC and in dollars, transfers, and the day's return in each
        unit with transfers removed (blank until the account held more than 1 BTC)."""
        eq = self.h.equity.resample('1D').last()
        px = self.h.price.resample('1D').last()
        flow = self.h.flows.resample('1D').last().diff().fillna(0)
        usd = eq * px
        d = pd.DataFrame({'equity': eq, 'price': px, 'flow': flow, 'usd': usd,
                          'r_btc': (eq.diff() - flow) / eq.shift(), 'r_usd': (usd.diff() - flow * px) / usd.shift()})
        d.loc[~(eq.shift() > 1), ['r_btc', 'r_usd']] = np.nan
        return d

    @cached_property
    def book(self):
        return pd.read_parquet(CACHE / 'book.parquet')

    @cached_property
    def fills_usd(self):
        """USD notional of every fill, aligned with self.f."""
        price = self.h.price.reindex(self.f.ts.dt.floor('1h')).to_numpy()
        return pd.Series(usd_notional(self.f.assign(btc_price=price)), index=self.f.index)

    @cached_property
    def orders(self):
        """One row per order, in the order of its first fill: what kind of order it was and how it filled.

        `active` marks orders whose first fill took liquidity and was not a stop or a liquidation: an order
        that traded the moment it was sent, so someone clicked at that time. Resting orders can fill while
        nobody is watching.
        """
        f = self.f
        text = f.text.astype(str)
        g = pd.DataFrame({
            'orderid': f.orderid, 'ts': f.ts, 'symbol': f.symbol.astype(str), 'ordtype': f.ordtype.astype(str),
            'taker': f.lastliquidityind == 'RemovedLiquidity', 'usd': self.fills_usd,
            'amended': text.str.contains('Amend'), 'close': text.str.contains('Position Close'),
            'liq': text.str.contains('Liquidation'), 'stop': f.ordtype.isin(['Stop', 'StopLimit']),
            'hidden': f.displayqty.notna() & (f.displayqty == 0), 'iceberg': f.displayqty.fillna(0) > 0,
        }).groupby('orderid', sort=False)
        o = g.agg(ts=('ts', 'first'), symbol=('symbol', 'first'), ordtype=('ordtype', 'first'),
                  taker_first=('taker', 'first'), maker=('taker', 'mean'), fills=('taker', 'size'), usd=('usd', 'sum'),
                  amended=('amended', 'max'), close=('close', 'max'), liq=('liq', 'max'), stop=('stop', 'max'),
                  hidden=('hidden', 'max'), iceberg=('iceberg', 'max'))
        o['maker'] = 1 - o.maker
        o['active'] = o.taker_first & ~o.stop & ~o.liq
        o['source'] = np.select([o.liq, o.stop, o.close, o.amended], ['liquidation', 'stop', 'close', 'amended'], 'website')
        return o.sort_values('ts', kind='stable').reset_index()

    @cached_property
    def xbt_fills(self):
        return self.f[self.f.symbol == 'XBTUSD'][['ts', 'side', 'lastqty', 'lastpx']]

    @cached_property
    def lots_fifo(self):
        return match_lots(self.xbt_fills, lifo=False)

    @cached_property
    def lots_lifo(self):
        return match_lots(self.xbt_fills, lifo=True)


def card(id, title, stat, body, chart=None, **numbers):
    return {'id': id, 'title': title, 'stat': stat, 'body': body, 'chart': chart, 'numbers': numbers}


def fmt(n, digits=0):
    return f'{n:,.{digits}f}'
