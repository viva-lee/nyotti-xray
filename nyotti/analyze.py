"""Run every analysis and write what the viewer loads into site/data."""
import json
import shutil

import numpy as np
import pandas as pd

from . import atlas
from .analyses import Context, usd_notional
from .analyses import behavior, cases, habits, lenses, money, position, proof, review, risk
from .judge import load_lenses
from .paths import CACHE, SITE_DATA

# Grouped the way the atlas reads them: proof, money, position, risk, habits, mind, market.
ANALYSES = [
    proof.verification, habits.by_hand, proof.ledger,
    money.transfers, money.by_coin, money.funding, money.concentration, money.payday,
    money.hedge, position.shape, position.two_currencies,
    money.leverage, money.liquidations, risk.year_2018, risk.distance_to_zero, cases.worst_day,
    habits.holding_time, habits.order_craft, behavior.plain_orders, behavior.winners_first, behavior.underwater_adds, habits.clock,
    lenses.calibration, lenses.regimes, lenses.panic, lenses.tilt, money.after_worst_days, behavior.after_best_days,
    proof.footprint, cases.black_thursday,
]
T0 = pd.Timestamp('2018-03-05')
KINDS = ['open', 'add', 'reduce', 'flip', 'close']


def replay(ctx):
    h = ctx.h[ctx.h.index >= T0]
    f = ctx.f.copy()
    f['hour'] = f.ts.dt.floor('1h')
    f['btc_price'] = h.price.reindex(f.hour).to_numpy()
    f['usd'] = usd_notional(f)
    g = f.groupby(['hour', f.side.astype(str)]).usd.sum().unstack(fill_value=0).reindex(h.index, fill_value=0)
    n = f.groupby('hour').size().reindex(h.index, fill_value=0)
    w = ctx.w
    pnl = w[w.transacttype == 'RealisedPNL'].set_index(w.day[w.transacttype == 'RealisedPNL'] + pd.Timedelta(hours=12)).btc
    pnl = pnl.resample('1h').sum().reindex(h.index, fill_value=0).cumsum()
    wd = w[w.transacttype == 'Withdrawal']
    out = -wd.set_index(wd.day + pd.Timedelta(hours=23)).btc.resample('1h').sum().reindex(h.index, fill_value=0).cumsum()

    def r(s, k):
        return [None if pd.isna(v) else round(float(v), k) for v in s]

    def at(ts):
        return int((pd.Timestamp(ts) - T0) / pd.Timedelta(hours=1))

    dep = w[w.transacttype == 'Deposit']
    daily = w[w.transacttype == 'RealisedPNL'].groupby('day').btc.sum()
    liq = ctx.f[ctx.f.text.astype(str).str.contains('Liquidation')]
    big = liq.assign(btc=liq.homenotional.abs()).groupby([liq.ts.dt.floor('1min'), liq.symbol.astype(str)]).btc.sum()
    (big_ts, big_sym), big_btc = big.idxmax(), big.max()
    first_wd = wd.day.min()
    events = [
        {'i': at(dep.day.min() + pd.Timedelta(hours=8)),
         'text': {'en': f'First deposit: {dep.btc.iloc[0]:.2f} BTC. All {len(dep)} deposits, {dep.btc.sum():.2f} BTC in total, came in 2018.',
                  'ko': f'첫 입금 {dep.btc.iloc[0]:.2f} BTC. 입금 {len(dep)}번, 합계 {dep.btc.sum():.2f} BTC가 모두 2018년이다.'}},
        {'i': at(first_wd + pd.Timedelta(hours=12)),
         'text': {'en': f'First withdrawal, {(first_wd - dep.day.min()).days} days in: {-wd.btc.iloc[0]:.2f} BTC.',
                  'ko': f'시작 {(first_wd - dep.day.min()).days}일 만의 첫 출금: {-wd.btc.iloc[0]:.2f} BTC.'}},
        {'i': at(big_ts),
         'text': {'en': f'Largest liquidation: a {big_sym} position worth {big_btc:.1f} BTC.',
                  'ko': f'가장 큰 강제청산: {big_btc:.1f} BTC 규모의 {big_sym} 포지션.'}},
        {'i': at(daily.idxmax() + pd.Timedelta(hours=12)),
         'text': {'en': f'Best realised day: +{daily.max():.1f} BTC.', 'ko': f'실현손익 최고의 날: +{daily.max():.1f} BTC.'}},
        {'i': at(daily.idxmin() + pd.Timedelta(hours=12)),
         'text': {'en': f'Worst realised day: {daily.min():.1f} BTC.', 'ko': f'실현손익 최악의 날: {daily.min():.1f} BTC.'}},
    ]

    return {
        't0': T0.isoformat(), 'step_hours': 1, 'n': len(h),
        'price': r(h.price, 1), 'buy': r(g.get('Buy', 0) / 1e6, 3), 'sell': r(g.get('Sell', 0) / 1e6, 3),
        'fills': [int(v) for v in n], 'exposure': r(h.exposure.clip(-3, 4), 2), 'equity': r(h.equity, 1),
        'realised': r(pnl, 2), 'withdrawn': r(out, 2), 'events': sorted(events, key=lambda e: e['i']),
    }


def decisions(ctx):
    d = ctx.d
    j = ctx.j
    lens_defs = load_lenses()
    m = d.merge(j, on='id', how='left') if j is not None else d
    out = {
        't': [int((t - T0).total_seconds() // 60) for t in m.start],
        'side': [1 if s == 'Buy' else 0 for s in m.side],
        'kind': [KINDS.index(k) for k in m.kind],
        'usd': [round(v / 1e6, 3) for v in m.size_usd],
        'px': [round(v, 1) for v in m.vwap],
        'exp0': [None if pd.isna(v) else round(v, 2) for v in m.exposure_before],
        'exp1': [None if pd.isna(v) else round(v, 2) for v in m.exposure_after],
        'id': [int(v) for v in m.id],
    }
    lenses_out = []
    for lens in lens_defs:
        k = lens['key']
        if k not in m:
            continue
        meta = {kk: lens[kk] for kk in ('key', 'label', 'label_ko', 'hint', 'type') if kk in lens}
        if lens['type'] == 'choice':
            opts = list(lens['criteria'])
            meta['options'] = opts
            out[k] = [opts.index(v) if isinstance(v, str) else None for v in m[k]]
            out[k + '_conf'] = [None if pd.isna(v) else round(v, 2) for v in m[k + '_conf']]
        elif lens['type'] == 'score':
            meta['levels'] = len(lens['criteria'])
            out[k] = [None if pd.isna(v) else round(v, 2) for v in m[k]]
        else:
            out[k] = [None if pd.isna(v) else round(v, 3) for v in m[k]]
        lenses_out.append(meta)
    out['lenses'] = lenses_out
    return out


def states():
    path = CACHE / 'jev' / 'states.jsonl'
    if not path.exists():
        return 0
    target = SITE_DATA / 'states'
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    rows = [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l]
    chunks = {}
    for row in rows:
        st = {k: v for k, v in row['state'].items() if k not in ('trader', 'note')}
        chunks.setdefault(row['id'] // 500, {})[row['id']] = st
    for c, data in chunks.items():
        (target / f'{c:03d}.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return len(rows)


def write(name, obj):
    (SITE_DATA / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def run(log=print):
    ctx = Context()
    cards = []
    chapter = atlas.chapter_of()
    for fn in ANALYSES:
        c = fn(ctx)
        if c is not None:
            c['chapter'] = chapter.get(c['id'])
            c['new'] = c['id'] in atlas.NEW
            cards.append(c)
            log(f'card {c["id"]}: {c["stat"]["value"]} {c["stat"]["label"]["en"]}')
    review.run(ctx, cards, log=log)
    jev_run = CACHE / 'jev' / 'run.json'
    meta = {
        'fills': int(len(ctx.f)), 'orders': int(ctx.f.orderid.nunique()), 'symbols': int(ctx.f.symbol.nunique()),
        'first_fill': str(ctx.f.ts.min()), 'last_fill': str(ctx.f.ts.max()),
        'deposits': round(float(ctx.w[ctx.w.transacttype == 'Deposit'].btc.sum()), 4),
        'realised': round(float(ctx.w[ctx.w.transacttype == 'RealisedPNL'].btc.sum()), 4),
        'withdrawn': round(float(-ctx.w[ctx.w.transacttype == 'Withdrawal'].btc.sum()), 4),
        'decisions': int(len(ctx.d)),
        'jev': json.loads(jev_run.read_text()) if jev_run.exists() else None,
    }
    write('insights.json', {'meta': meta, 'cards': cards})
    write('replay.json', replay(ctx))
    write('decisions.json', decisions(ctx))
    write('atlas.json', atlas.build(ctx, cards))
    n = states()
    sizes = {p.name: p.stat().st_size for p in SITE_DATA.glob('*.json')}
    log(f'site/data: {sizes} + {n} states')
