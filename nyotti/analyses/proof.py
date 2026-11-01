"""What the public tape says: were his fills real, and how big was he on BitMEX?"""
import json
from collections import Counter

import pandas as pd

from . import card, fmt
from ..paths import TAPE
from ..tape import BAD_PRICE, BAD_SIDE, BAD_SIZE, BAD_SYMBOL, BAD_TIME, VERSION


def tape_days():
    days = []
    for path in sorted(TAPE.glob('*.json')):
        day = json.loads(path.read_text(encoding='ascii'))
        if day.get('v', 1) >= VERSION:
            days.append(day)
    return days


def verification(ctx):
    days = tape_days()
    f = ctx.f
    covered = {d['day'] for d in days}
    mine = f[f.ts.dt.date.astype(str).isin(covered)]
    found = {}
    for d in days:
        for mid, bad, dt in d['found']:
            found[mid] = (bad, dt)  # a neighbouring day may list it too; same verdict
    ids = mine.trdmatchid.to_numpy()
    hit = [found.get(i) for i in ids]
    n_found = sum(h is not None for h in hit)
    flags = Counter()
    for h in hit:
        if h is not None:
            for bit, name in ((BAD_SYMBOL, 'symbol'), (BAD_PRICE, 'price'), (BAD_SIZE, 'size'),
                              (BAD_SIDE, 'side'), (BAD_TIME, 'time')):
                if h[0] & bit:
                    flags[name] += 1
    exact = sum(h is not None and h[0] == 0 for h in hit)
    missing = mine[[h is None for h in hit]]
    miss_kinds = missing.text.astype(str).str.contains('Liquidation').sum()
    # A self-trade (his own buy crossing his own sell) appears twice in the release with one trade id.
    self_ids = missing.trdmatchid[missing.trdmatchid.duplicated(keep=False)]
    self_fills = len(self_ids)
    other = len(missing) - miss_kinds - self_fills
    explained = other == 0
    per_day = (pd.DataFrame({'day': mine.ts.dt.date.astype(str), 'ok': [h is not None and h[0] == 0 for h in hit]})
               .groupby('day').ok.agg(['size', 'sum']))
    complete = len(covered) >= 1402
    scope_en = 'every fill' if complete else f'fills on the {len(covered):,} days scanned so far'
    scope_ko = '전체 체결' if complete else f'지금까지 스캔한 {len(covered):,}일의 체결'
    return card(
        'verified',
        {'en': 'Checked against BitMEX\'s public tape', 'ko': 'BitMEX 공개 체결 테이프와 대조'},
        {'value': fmt(exact), 'unit': '', 'label': {'en': f'of {fmt(len(mine))} fills found on the tape, every field matching',
                                                    'ko': f'건이 테이프에 있고 모든 필드 일치 ({fmt(len(mine))}건 중)'}},
        {'en': f'BitMEX publishes every trade on the exchange, anonymously, one file per day. We streamed {len(covered):,} '
               f'days of it ({sum(d.get("lines", 0) for d in days):,} trades) and looked up the trade id of {scope_en}. '
               f'{fmt(n_found)} of {fmt(len(mine))} ids are on the tape; {fmt(exact)} match on symbol, price, size, '
               'timestamp and maker/taker side. '
               + (f'The {fmt(len(missing))} not on the tape are {fmt(miss_kinds)} liquidation fills, which go to the '
                  f'exchange\'s liquidation engine instead of the order book, and {fmt(self_fills)} fills from {self_fills // 2} self-trades, '
                  'where his own buy crossed his own sell under one trade id. '
                  + (f'{fmt(other)} more are unexplained. ' if other else '') if len(missing) else '')
               + ('Mismatched fields: ' + ', '.join(f'{k} {v:,}' for k, v in flags.items()) + '.' if flags else
                  'No field disagreed.'),
         'ko': f'BitMEX는 거래소의 모든 체결을 익명으로 하루 한 파일씩 공개한다. {len(covered):,}일치(체결 '
               f'{sum(d.get("lines", 0) for d in days):,}건)를 스트리밍하며 {scope_ko}의 체결 ID를 찾았다. {fmt(len(mine))}건 중 '
               f'{fmt(n_found)}건이 테이프에 있고, {fmt(exact)}건이 종목, 가격, 수량, 시각, 메이커/테이커 방향까지 일치한다. '
               + (f'테이프에 없는 {fmt(len(missing))}건은 호가창이 아니라 청산 엔진으로 넘어가는 강제청산 체결 {fmt(miss_kinds)}건과, '
                  f'자기 매수 주문과 자기 매도 주문이 하나의 거래 ID로 맞붙은 자전거래 {self_fills // 2}쌍({fmt(self_fills)}건)이다. '
                  + (f'설명되지 않는 체결이 {fmt(other)}건 더 있다. ' if other else '') if len(missing) else '')
               + ('불일치 필드: ' + ', '.join(f'{k} {v:,}' for k, v in flags.items()) + '.' if flags else '어긋난 필드는 없다.')},
        {'type': 'calendar', 'days': per_day.index.tolist(), 'total': per_day['size'].astype(int).tolist(),
         'ok': per_day['sum'].astype(int).tolist(),
         'legend': {'en': ['every fill on the tape', 'a liquidation or self-trade missing' if explained else 'some fills missing'],
                    'ko': ['전부 테이프에 있는 날', '청산 · 자전거래 체결이 빠진 날' if explained else '일부 체결이 빠진 날']}},
        days_scanned=len(covered), tape_trades=sum(d.get('lines', 0) for d in days), checked=len(mine),
        found=n_found, exact=exact, not_found=len(missing), not_found_liquidations=int(miss_kinds),
        not_found_self_trade_fills=int(self_fills), unexplained=int(other),
        flags=dict(flags), complete=complete)


def ledger(ctx):
    """Replay every fill through the average-cost book and compare its realised PnL with the wallet's."""
    # The wallet's daily numbers line up when each day runs noon to noon UTC, so years do too.
    noon = pd.Timedelta(hours=12)
    bk = ctx.book
    year_end = bk.realized.groupby((bk.ts + noon).dt.year).last()
    fills = year_end.diff()
    fills.iloc[0] = year_end.iloc[0]
    fees = (ctx.x.execcomm.fillna(0) / 1e8).groupby((ctx.x.ts + noon).dt.year).sum()
    rebuilt = fills - fees.reindex(fills.index, fill_value=0)
    w = ctx.w[ctx.w.transacttype == 'RealisedPNL']
    wallet = w.btc.groupby(w.day.dt.year).sum().reindex(rebuilt.index, fill_value=0)
    total_r, total_w = rebuilt.sum(), wallet.sum()
    gap = total_r - total_w
    years = [str(y) for y in rebuilt.index]
    return card(
        'ledger',
        {'en': 'The book balances', 'ko': '장부가 맞아떨어진다'},
        {'value': f'{abs(gap) / total_w:.2%}', 'unit': '', 'label': {'en': 'gap between the rebuilt book and the wallet\'s realised PnL',
                                                                    'ko': '재구성한 장부와 지갑 실현손익의 차이'}},
        {'en': f'The wallet file only reports one realised-PnL number a day. Replaying all {fmt(len(ctx.f))} fills through an '
               'average-cost book, one per symbol, and subtracting every fee and funding payment gives '
               f'{total_r:,.2f} BTC of realised PnL; the wallet says {total_w:,.2f}. The gap is {gap:+.2f} BTC over four years. '
               'The wallet\'s daily numbers line up when each day runs from noon to noon UTC, so the years here do too. '
               'Year by year, rebuilt vs wallet: ' + ', '.join(f'{a:,.1f} vs {b:,.1f} ({y})' for y, a, b in zip(years, rebuilt, wallet))
               + f'. The largest yearly difference is {(rebuilt - wallet).abs().max():.2f} BTC.',
         'ko': f'지갑 파일에는 하루 한 번 실현손익 숫자만 있다. 체결 {fmt(len(ctx.f))}건 전부를 종목별 평균단가 장부로 재생하고 '
               f'수수료와 펀딩을 모두 빼면 실현손익은 {total_r:,.2f} BTC, 지갑은 {total_w:,.2f} BTC다. 4년 동안의 차이는 '
               f'{gap:+.2f} BTC다. 지갑의 일별 숫자는 하루를 UTC 정오부터 다음 날 정오까지로 볼 때 맞아떨어져서 연도도 그렇게 나눴다. '
               '연도별(재구성 대 지갑): ' + ', '.join(f'{y}년 {a:,.1f} 대 {b:,.1f}' for y, a, b in zip(years, rebuilt, wallet))
               + f'. 한 해 차이가 가장 큰 경우도 {(rebuilt - wallet).abs().max():.2f} BTC다.'},
        {'type': 'pair', 'labels': {'en': ['Rebuilt from fills', 'Wallet'], 'ko': ['체결로 재구성', '지갑']},
         'years': years, 'values': [[round(float(v), 1) for v in rebuilt], [round(float(v), 1) for v in wallet]], 'unit': 'BTC'},
        rebuilt=round(float(total_r), 3), wallet=round(float(total_w), 3), gap=round(float(gap), 3),
        by_year={y: [round(float(a), 3), round(float(b), 3)] for y, a, b in zip(years, rebuilt, wallet)})


def footprint(ctx):
    days = tape_days()
    tape = pd.Series({d['day']: d['totals'].get('XBTUSD', [0, 0, 0])[1] for d in days if not d.get('missing')})
    f = ctx.f[ctx.f.symbol == 'XBTUSD']
    mine = f.groupby(f.ts.dt.date.astype(str)).lastqty.sum()
    share = (mine / tape.reindex(mine.index)).dropna()
    share = share[share.index.isin(tape.index)]
    if share.empty:
        return None
    yr = share.groupby(pd.to_datetime(share.index).year)
    med, top = yr.median(), share.sort_values(ascending=False)
    years = [str(y) for y in med.index]
    return card(
        'footprint',
        {'en': 'His share of all XBTUSD volume', 'ko': 'XBTUSD 전체 거래량 중 그의 몫'},
        {'value': f'{top.iloc[0]:.1%}', 'unit': '', 'label': {'en': f'of the exchange\'s XBTUSD volume on {top.index[0]}',
                                                              'ko': f'{top.index[0]} BitMEX XBTUSD 거래량 중 비중'}},
        {'en': 'Dividing his XBTUSD contracts by every XBTUSD contract on the tape the same day: the median day went '
               + ' → '.join(f'{v:.2%} ({y})' for y, v in zip(years, med)) + f'. His biggest day was {top.index[0]} at '
               f'{top.iloc[0]:.1%} of the exchange\'s volume.',
         'ko': '그날 그의 XBTUSD 계약 수를 테이프 전체 XBTUSD 계약 수로 나눴다. 중앙값은 '
               + ' → '.join(f'{v:.2%}({y})' for y, v in zip(years, med)) + f'로 커졌고, 가장 큰 날은 {top.index[0]}에 거래소 '
               f'거래량의 {top.iloc[0]:.1%}였다.'},
        {'type': 'bars', 'labels': {'en': years, 'ko': years}, 'values': [round(v * 100, 3) for v in med], 'unit': '%'},
        median_share={y: round(v, 5) for y, v in zip(years, med)}, max_day=top.index[0], max_share=round(top.iloc[0], 4))
