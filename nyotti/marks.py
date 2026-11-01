"""Hourly mark prices for every symbol he traded, taken from the public-tape pass.

Where the tape pass has not covered an hour (or the symbol did not trade), the last known
price carries forward; before the first tape price, his own fill prices fill the gap.
"""
import json

import pandas as pd

from .paths import CACHE, TAPE


def from_tape():
    rows = {}
    for path in sorted(TAPE.glob('*.json')):
        day = json.loads(path.read_text(encoding='ascii'))
        if day.get('v', 1) < 2 or day.get('missing'):
            continue
        base = pd.Timestamp(day['day'])
        for sym, prices in day['hourly'].items():
            for h, p in enumerate(prices):
                if p is not None:
                    rows[(base + pd.Timedelta(hours=h), sym)] = p
    if not rows:
        return pd.DataFrame()
    s = pd.Series(rows)
    s.index.names = ['hour', 'symbol']
    return s.unstack('symbol').sort_index()


def hourly(fills, hours):
    """DataFrame indexed by `hours`, one column per symbol in `fills`."""
    symbols = sorted(fills.symbol.astype(str).unique())
    own = (fills.assign(hour=fills.ts.dt.floor('1h'), symbol=fills.symbol.astype(str))
           .groupby(['hour', 'symbol']).lastpx.last().unstack('symbol'))
    tape = from_tape()
    m = pd.DataFrame(index=hours, columns=symbols, dtype=float)
    for sym in symbols:
        col = tape[sym] if sym in tape else pd.Series(dtype=float)
        mine = own[sym] if sym in own else pd.Series(dtype=float)
        m[sym] = col.reindex(hours).combine_first(mine.reindex(hours)).ffill()
    m.attrs['tape_hours'] = len(tape)
    m.to_parquet(CACHE / 'marks_hourly.parquet')
    return m
