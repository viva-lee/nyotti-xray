"""One streaming pass over BitMEX's public trade tape.

The tape is anonymous, so his fills cannot be pulled out of it. What it can do is confirm them:
every fill in the release carries a `trdmatchid`, and the tape lists every trade on the exchange
with the same id. For each day we check that each of his ids is on the tape with the same symbol,
price, size and timestamp, and that the tape's aggressor side agrees with whether he was the maker
or the taker. The same pass collects the market around him: daily volume per symbol and one-minute
bars for XBTUSD and ETHUSD, and the last price of every symbol in every hour (to mark his altcoin
positions to market). Nothing from the tape is kept on disk except those aggregates.
"""
import gzip
import io
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime, timedelta

from .paths import TAPE

URL = 'https://s3-eu-west-1.amazonaws.com/public.bitmex.com/data/trade/{}.csv.gz'
BAR_SYMBOLS = ('XBTUSD', 'ETHUSD')
FIRST, LAST = date(2018, 3, 1), date(2021, 12, 31)
VERSION = 2

# Bit flags for a matched id whose fields disagree with the release.
BAD_SYMBOL, BAD_PRICE, BAD_SIZE, BAD_SIDE, BAD_TIME = 1, 2, 4, 8, 16


def _ts(s):
    # Tape: 2019-06-01D00:00:19.658602000  Release: 2019-06-01 00:00:19.658602
    return datetime.fromisoformat(s.replace('D', ' ')[:26])


def _scan(day, mine):
    """Stream one day of the tape. `mine` maps trdmatchid -> (symbol, side, qty, px, ts, maker)."""
    bars = {s: [None] * 1440 for s in BAR_SYMBOLS}
    totals = {}
    hourly = {}
    found = []
    lines = 0
    res = urllib.request.urlopen(URL.format(day.strftime('%Y%m%d')), timeout=90)
    with gzip.GzipFile(fileobj=res) as gz:
        text = io.TextIOWrapper(gz, encoding='ascii', newline='')
        next(text)  # header
        for line in text:
            lines += 1
            ts, sym, side, size, price, _tick, mid, _gross, _home, foreign = line.rstrip('\n').split(',')
            t = totals.get(sym)
            if t is None:
                t = totals[sym] = [0, 0.0, 0.0]
            sz = float(size)
            last = hourly.get(sym)
            if last is None:
                last = hourly[sym] = [None] * 24
            last[int(ts[11:13])] = price
            t[0] += 1
            t[1] += sz
            if foreign:
                t[2] += abs(float(foreign))
            if sym in bars:
                px = float(price)
                m = int(ts[11:13]) * 60 + int(ts[14:16])
                b = bars[sym][m]
                if b is None:
                    bars[sym][m] = [px, px, px, px, sz, 1]
                else:
                    if px > b[1]: b[1] = px
                    if px < b[2]: b[2] = px
                    b[3] = px
                    b[4] += sz
                    b[5] += 1
            rec = mine.get(mid)
            if rec is not None:
                r_sym, r_side, r_qty, r_px, r_ts, r_maker = rec
                bad = 0
                if sym != r_sym: bad |= BAD_SYMBOL
                if abs(float(price) - r_px) > 1e-9 * max(1.0, r_px): bad |= BAD_PRICE
                if abs(sz - r_qty) > 1e-9: bad |= BAD_SIZE
                # The tape's side is the aggressor. A maker fill sits on the opposite side.
                if (side == r_side) == r_maker: bad |= BAD_SIDE
                dt = (_ts(ts) - _ts(r_ts)).total_seconds()
                if abs(dt) > 1: bad |= BAD_TIME
                found.append([mid, bad, round(dt, 6)])
    return {'v': VERSION, 'day': day.isoformat(), 'lines': lines, 'found': found, 'totals': totals,
            'bars': bars, 'hourly': {s: [None if p is None else float(p) for p in v] for s, v in hourly.items()}}


def scan_day(day, mine):
    for attempt in range(8):
        try:
            return _scan(day, mine)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return {'v': VERSION, 'day': day.isoformat(), 'missing': True, 'found': [], 'totals': {},
                        'bars': {}, 'hourly': {}}
            err = e
        except Exception as e:  # dropped stream: start the day over
            err = e
        time.sleep(min(60, 2 ** attempt))
    raise RuntimeError(f'{day}: gave up after retries: {err}')


def done_already(day):
    path = TAPE / f'{day.isoformat()}.json'
    if not path.exists():
        return False
    with open(path, encoding='ascii') as f:
        return f.read(12).startswith(f'{{"v":{VERSION},')


def run(fills, workers=8, log=print):
    """`fills` is the trades DataFrame from load.fills()."""
    f = fills[['trdmatchid', 'symbol', 'side', 'lastqty', 'lastpx', 'ts', 'lastliquidityind']].copy()
    f['day'] = f.ts.dt.date
    f['ts_s'] = f.ts.dt.strftime('%Y-%m-%d %H:%M:%S.%f')
    f['maker'] = f.lastliquidityind == 'AddedLiquidity'
    by_day = {d: g for d, g in f.groupby('day')}

    def mine_for(day):
        # Include the neighbouring days so a timezone or midnight edge cannot hide a match.
        out = {}
        for d in (day - timedelta(days=1), day, day + timedelta(days=1)):
            g = by_day.get(d)
            if g is not None:
                out.update(zip(g.trdmatchid, zip(g.symbol.astype(str), g.side.astype(str), g.lastqty,
                                                 g.lastpx, g.ts_s, g.maker)))
        return out

    days = [FIRST + timedelta(days=i) for i in range((LAST - FIRST).days + 1)]
    todo = [d for d in days if not done_already(d)]
    log(f'tape: {len(days)} days in range, {len(todo)} to scan with {workers} workers')
    started, done = time.time(), 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(scan_day, d, mine_for(d)): d for d in todo}
        for job in as_completed(jobs):
            out = job.result()
            path = TAPE / f"{out['day']}.json"
            tmp = path.with_suffix('.part')
            tmp.write_text(json.dumps(out, separators=(',', ':')))
            tmp.replace(path)
            done += 1
            if done % 10 == 0 or done == len(todo):
                rate = done / (time.time() - started)
                log(f'tape: {done}/{len(todo)} days · {out["day"]} · {len(out["found"])} of his fills found'
                    f' · eta {(len(todo) - done) / rate / 60:.0f} min', flush=True)
