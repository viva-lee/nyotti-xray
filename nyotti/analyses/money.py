"""The account: hedging with inverse shorts, leverage, funding, transfers, and where the PnL came from."""
import numpy as np
import pandas as pd

from . import btc_value, bucket, card, fmt


def hedge(ctx):
    h = ctx.h[ctx.h.index >= '2019-01-01'].dropna(subset=['exposure'])
    short = h[h.net < 0]
    share_short = len(short) / len(h)
    hedged = ((short.exposure >= 0) & (short.exposure <= 1)).mean()
    bet = (short.exposure < 0).mean()
    ratio = (-short.leverage).median()
    split = pd.Series(bucket(short.exposure)).value_counts(normalize=True).reindex(range(5), fill_value=0)
    yr = h.groupby(h.index.year)
    by_year = pd.DataFrame({
        'short_contracts': yr.net.apply(lambda s: (s < 0).mean()),
        'net_short_btc': yr.exposure.apply(lambda s: (s < 0).mean()),
    })
    years = [str(y) for y in by_year.index]
    return card(
        'short-is-not-bearish',
        {'en': 'Most "short" hours were not a bet on a fall', 'ko': '숏 시간의 대부분은 하락 베팅이 아니었다'},
        {'value': f'{hedged:.0%}', 'unit': '', 'label': {'en': 'of his short hours left the whole account net long Bitcoin',
                                                          'ko': '숏 시간 중 계좌 전체로는 BTC 순매수였던 비중'}},
        {'en': f'From 2019 to 2021 he held net short XBTUSD contracts {share_short:.0%} of the time, right through '
               'the bull run. But his margin was Bitcoin. On an inverse contract, a short as large as your BTC balance '
               'turns the account into dollars. Sorting those short hours by the whole account\'s exposure: '
               f'{split[0]:.0%} were a real bet on a fall (-0.25x or less), {split[1]:.0%} parked the account in dollars '
               f'(-0.25x to 0.25x), {split[2]:.0%} hedged part of it, and in {split[3]:.0%} the short only trimmed an account '
               f'still about like holding Bitcoin. In {hedged:.0%} of short hours the account was net long Bitcoin; '
               f'{bet:.0%} were net short. The median short covered {ratio:.0%} of equity.',
         'ko': f'2019~2021년 그는 강세장 내내 {share_short:.0%}의 시간 동안 XBTUSD 순숏이었다. 하지만 증거금이 '
               '비트코인이었다. 인버스 계약에서 BTC 잔고만큼 숏을 잡으면 계좌가 달러가 된다. 숏인 시간을 계좌 전체의 노출도로 '
               f'나누면 {split[0]:.0%}는 실제 하락 베팅(-0.25배 이하), {split[1]:.0%}는 계좌를 달러로 파킹(-0.25~0.25배), '
               f'{split[2]:.0%}는 일부 헤지였고, {split[3]:.0%}는 여전히 BTC 보유와 비슷한 계좌를 숏이 조금 덜어냈을 뿐이다. '
               f'숏 시간의 {hedged:.0%}는 계좌 전체로 BTC 순매수였고 {bet:.0%}는 순매도였다. 숏 규모 중앙값은 자산의 '
               f'{ratio:.0%}였다.'},
        {'type': 'pair', 'labels': {'en': ['Net short contracts', 'Net short Bitcoin'], 'ko': ['계약상 순숏', '실제 BTC 순숏']},
         'years': years, 'values': [[round(v, 3) for v in by_year.short_contracts], [round(v, 3) for v in by_year.net_short_btc]],
         'unit': '%'},
        share_short_contracts=round(share_short, 4), hedged_share=round(hedged, 4), bet_share=round(bet, 4),
        median_hedge_ratio=round(ratio, 3), exposure_split=[round(float(v), 4) for v in split])


def leverage(ctx):
    h = ctx.h.dropna(subset=['gross_leverage'])
    yr = h.gross_leverage.groupby(h.index.year)
    p50, p95, mx = yr.median(), yr.quantile(.95), yr.max()
    eq = ctx.h.equity.groupby(ctx.h.index.year).median()
    early = h[h.index < '2018-04-01']
    years = [str(y) for y in p95.index]
    return card(
        'leverage',
        {'en': 'Leverage fell as the account grew', 'ko': '계좌가 커질수록 레버리지는 줄었다'},
        {'value': f'{p95.iloc[-1]:.1f}x', 'unit': '', 'label': {'en': f'95th-percentile gross leverage in {years[-1]}',
                                                                 'ko': f'{years[-1]}년 총 레버리지 95백분위'}},
        {'en': 'Gross leverage here is every open position, Bitcoin and altcoins, divided by account equity, hour by '
               f'hour. In March 2018, with a few hundred dollars in the account, it reached {early.gross_leverage.max():.0f}x. '
               'After that the 95th percentile went ' + ' → '.join(f'{v:.1f}x ({y})' for y, v in zip(years, p95)) +
               ', while median equity grew ' + ' → '.join(f'{v:,.0f}' for v in eq) + ' BTC.',
         'ko': '여기서 총 레버리지는 비트코인과 알트를 합친 모든 포지션을 자산으로 나눈 값이다(시간 단위). 계좌에 수백 '
               f'달러뿐이던 2018년 3월에는 최대 {early.gross_leverage.max():.0f}배까지 갔다. 이후 95백분위는 '
               + ' → '.join(f'{v:.1f}배({y})' for y, v in zip(years, p95)) + '로 내려갔고, 같은 기간 자산 중앙값은 '
               + ' → '.join(f'{v:,.0f}' for v in eq) + ' BTC로 커졌다.'},
        {'type': 'bars', 'labels': {'en': years, 'ko': years}, 'values': [round(v, 2) for v in p95], 'unit': 'x'},
        p50={y: round(v, 3) for y, v in zip(years, p50)}, p95={y: round(v, 3) for y, v in zip(years, p95)},
        max={y: round(v, 2) for y, v in zip(years, mx)}, median_equity_btc={y: round(v, 1) for y, v in zip(years, eq)},
        march_2018_max=round(float(early.gross_leverage.max()), 1))


def funding(ctx):
    x = ctx.x
    fu = x[x.exectype == 'Funding']
    fees = x[x.exectype == 'Trade']
    fy = (fu.execcomm / 1e8).groupby(fu.ts.dt.year).sum()
    ty = (fees.execcomm / 1e8).groupby(fees.ts.dt.year).sum()
    by_sym = (fu.execcomm / 1e8).groupby(fu.symbol.astype(str), observed=True).sum().sort_values()
    total = -(fy.sum() + ty.sum())
    years = [str(y) for y in fy.index]
    top = by_sym.head(3)
    return card(
        'funding',
        {'en': 'In 2021 the market paid him to hold', 'ko': '2021년에는 시장이 그에게 돈을 냈다'},
        {'value': f'{-fy.iloc[-1]:,.0f} BTC', 'unit': '', 'label': {'en': f'funding received in {years[-1]}',
                                                                     'ko': f'{years[-1]}년 받은 펀딩비'}},
        {'en': 'Perpetual swaps charge funding every eight hours, paid from the crowded side to the other. He paid '
               + ', '.join(f'{v:.1f} BTC ({y})' for y, v in zip(years[:-1], fy.iloc[:-1])) +
               f'. In 2021, when longs were crowded and his books leaned short, he received {-fy.iloc[-1]:.1f} BTC, mostly on '
               + ', '.join(f'{s} ({-v:.1f})' for s, v in top.items()) + f'. Maker rebates added {-ty.iloc[-1]:.1f} BTC '
               f'that year. Over four years fees and funding together paid him {total:.1f} BTC instead of costing him.',
         'ko': '무기한 선물은 8시간마다 몰린 쪽이 반대쪽에 펀딩비를 낸다. 그는 '
               + ', '.join(f'{y}년 {v:.1f} BTC' for y, v in zip(years[:-1], fy.iloc[:-1])) +
               f'를 냈다. 롱이 몰리고 그의 장부가 숏으로 기울었던 2021년에는 {-fy.iloc[-1]:.1f} BTC를 받았다. 주로 '
               + ', '.join(f'{s}({-v:.1f})' for s, v in top.items()) + f'에서다. 그해 메이커 리베이트도 {-ty.iloc[-1]:.1f} BTC다. '
               f'4년 합계로 수수료와 펀딩은 비용이 아니라 {total:.1f} BTC의 수입이었다.'},
        {'type': 'bars', 'labels': {'en': years, 'ko': years}, 'values': [round(-v, 2) for v in fy], 'unit': 'BTC',
         'signed': True},
        funding_by_year={y: round(v, 3) for y, v in zip(years, fy)}, fees_by_year={str(y): round(v, 3) for y, v in ty.items()},
        net_received=round(total, 2))


def transfers(ctx):
    w = ctx.w
    dep = w[w.transacttype == 'Deposit']
    wd = w[w.transacttype == 'Withdrawal']
    pnl = w[w.transacttype == 'RealisedPNL'].btc.sum()
    final = w.btc.sum()
    first_wd = wd.day.min()
    by_year = (-wd.btc).groupby(wd.day.dt.year).sum()
    in_2018 = by_year.get(2018, 0)
    years = [str(y) for y in by_year.index]
    return card(
        'transfers',
        {'en': '14.5 BTC in, 2,814.5 BTC out', 'ko': '14.5 BTC 입금, 2,814.5 BTC 출금'},
        {'value': f'{-wd.btc.sum() / dep.btc.sum():,.0f}x', 'unit': '', 'label': {'en': 'withdrawn vs deposited',
                                                                                  'ko': '입금 대비 출금'}},
        {'en': f'{len(dep)} deposits, all in 2018, add up to {dep.btc.sum():.3f} BTC; he never added money after '
               f'{dep.day.max():%B %Y}. The first withdrawal came on {first_wd:%Y-%m-%d}, {(first_wd - dep.day.min()).days} '
               f'days after the first deposit. By the end of 2018 he had taken out {in_2018:.1f} BTC. In total, {len(wd)} '
               f'completed withdrawals took out {-wd.btc.sum():,.2f} BTC, {(-wd.btc.sum()) / pnl:.1%} of the realised '
               f'PnL ({pnl:,.2f} BTC), leaving {final:,.2f} BTC in the wallet at the end of 2021.',
         'ko': f'입금은 {len(dep)}번, 전부 2018년에 있었고 합계 {dep.btc.sum():.3f} BTC다. {dep.day.max():%Y년 %m월} 이후로는 '
               f'돈을 넣지 않았다. 첫 출금은 첫 입금 {(first_wd - dep.day.min()).days}일 뒤인 {first_wd:%Y-%m-%d}. 2018년 말까지 '
               f'{in_2018:.1f} BTC를 뺐다. 완료된 출금 {len(wd)}번의 합계는 {-wd.btc.sum():,.2f} BTC로 실현손익 '
               f'({pnl:,.2f} BTC)의 {(-wd.btc.sum()) / pnl:.1%}이고, 2021년 말 지갑에는 {final:,.2f} BTC가 남았다.'},
        {'type': 'bars', 'labels': {'en': years, 'ko': years}, 'values': [round(v, 2) for v in by_year], 'unit': 'BTC'},
        deposits=round(dep.btc.sum(), 4), withdrawals=round(-wd.btc.sum(), 4), realised=round(pnl, 4),
        final_wallet=round(final, 4), first_withdrawal=str(first_wd.date()))


def concentration(ctx):
    w = ctx.w
    r = w[w.transacttype == 'RealisedPNL'].groupby('day').btc.sum()
    net = r.sum()
    top = r.sort_values(ascending=False)
    cum = top.cumsum() / net
    n_half = int((cum < 0.5).sum() + 1)
    n_all = int((cum < 1.0).sum() + 1) if (cum >= 1.0).any() else len(top)
    best, worst = top.index[0], r.idxmin()
    win_days = (r > 0).mean()
    curve = [round(float(v), 4) for v in cum.iloc[:200]]
    after_crash = str(best.date()) == '2020-03-13'  # BitMEX's "Black Thursday" was 2020-03-12
    crash_en = ', the day after the March 2020 crash' if after_crash else ''
    crash_ko = '2020년 3월 폭락 다음 날인 ' if after_crash else ''
    return card(
        'concentration',
        {'en': f'Half the profit came from {n_half} days', 'ko': f'수익의 절반은 {n_half}일에서 나왔다'},
        {'value': str(n_half), 'unit': '', 'label': {'en': f'of {len(r):,} days made 50% of net realised PnL',
                                                     'ko': f'일({len(r):,}일 중)이 순실현손익의 50%'}},
        {'en': f'{win_days:.0%} of his {len(r):,} realised-PnL days were green, but the profit was lumpy. Sorting days from '
               f'best to worst, the top {n_half} reach half of the {net:,.0f} BTC net and the top {n_all} reach all of it; '
               f'the rest net to roughly zero. Best day: {best:%Y-%m-%d}, +{top.iloc[0]:.1f} BTC{crash_en}. '
               f'Worst: {worst:%Y-%m-%d}, {r.min():.1f} BTC.',
         'ko': f'실현손익이 기록된 {len(r):,}일 중 {win_days:.0%}가 플러스였지만 수익은 몰려 있었다. 좋은 날부터 정렬하면 '
               f'상위 {n_half}일이 순이익 {net:,.0f} BTC의 절반, 상위 {n_all}일이 전부를 채운다. 나머지 날들의 합은 거의 0이다. '
               f'최고의 날은 {crash_ko}{best:%Y-%m-%d}(+{top.iloc[0]:.1f} BTC), 최악은 {worst:%Y-%m-%d}'
               f'({r.min():.1f} BTC).'},
        {'type': 'curve', 'values': curve, 'mark': 0.5,
         'x': {'en': 'days, best first', 'ko': '일수(좋은 날부터)'}, 'y': {'en': 'share of net PnL', 'ko': '순손익 비중'}},
        days=len(r), win_days=round(win_days, 4), days_to_half=n_half, days_to_all=n_all,
        best_day=str(best.date()), best_btc=round(top.iloc[0], 2), worst_day=str(worst.date()), worst_btc=round(r.min(), 2))


def after_worst_days(ctx):
    """What he did the day after his 20 worst mark-to-market days (from 2019, once equity was material)."""
    r = ctx.daily_return
    r = r[r.index >= '2019-01-01']
    d = ctx.d.assign(day=ctx.d.start.dt.floor('1D'))
    d['size_eq'] = d.size_usd / (d.vwap * d.equity)  # size as a share of equity
    per = d.groupby('day').agg(n=('id', 'size'), size=('size_eq', 'median'),
                               adds=('kind', lambda k: k.isin(['open', 'add', 'flip']).mean()))
    per = per.reindex(r.index)
    per['n'] = per.n.fillna(0)
    base_n = per.n.rolling(30, min_periods=10).median()
    worst = r.sort_values().head(20).index
    nxt = [day + pd.Timedelta(days=1) for day in worst]
    act = np.array([per.n.get(n, np.nan) / base_n.get(w, np.nan) for n, w in zip(nxt, worst)])
    size_after = per['size'].reindex(nxt).median()
    size_all = per['size'].median()
    adds_after = per.adds.reindex(nxt).mean()
    adds_all = per.adds.mean()
    quiet = float(np.mean([per.n.get(n, 0) == 0 for n in nxt]))
    return card(
        'after-the-worst-days',
        {'en': 'The day after his worst days', 'ko': '최악의 날 다음 날'},
        {'value': f'{size_after / size_all:.2f}x', 'unit': '', 'label': {'en': 'median trade size the next day, vs his usual',
                                                                          'ko': '다음 날 거래 크기 중앙값(평소 대비)'}},
        {'en': f'Take his 20 worst days by mark-to-market return, 2019-2021, worst {r.min():.1%}. The next day he made '
               f'{np.nanmedian(act):.1f}x his usual number of XBTUSD decisions, and on {quiet:.0%} of those days none at all. '
               f'His median trade was {size_after / size_all:.2f}x his usual size relative to equity, and {adds_after:.0%} of '
               f'his decisions opened or grew a position, against {adds_all:.0%} on an ordinary day.',
         'ko': f'2019~2021년 일간 평가손익 기준 최악의 20일(최저 {r.min():.1%})을 골랐다. 그다음 날 XBTUSD 결정 수는 평소의 '
               f'{np.nanmedian(act):.1f}배였고, {quiet:.0%}의 날은 아예 거래가 없었다. 자산 대비 거래 크기 중앙값은 평소의 '
               f'{size_after / size_all:.2f}배, 포지션을 열거나 키운 결정 비중은 {adds_after:.0%}(평소 {adds_all:.0%})였다.'},
        None,
        worst_return=round(float(r.min()), 4), next_day_activity=round(float(np.nanmedian(act)), 3),
        next_day_quiet_share=round(quiet, 3), size_ratio=round(float(size_after / size_all), 3),
        adds_after=round(float(adds_after), 3), adds_all=round(float(adds_all), 3))


def payday(ctx):
    """When he withdrew: each withdrawal against the equity just before it and its 30-day high."""
    w = ctx.w
    wd = w[w.transacttype == 'Withdrawal']
    eq = ctx.h.equity
    rows = []
    for day, btc in zip(wd.day, -wd.btc):
        t = day + pd.Timedelta(hours=22)  # transfers are booked at 23:00 of their day (the release lost the hour)
        before = eq.asof(t)
        high = eq[t - pd.Timedelta(days=30):t].max()
        rows.append((day, btc, btc / before, before / high - 1))
    p = pd.DataFrame(rows, columns=['day', 'btc', 'share', 'from_high'])
    near = (p.from_high > -0.05).mean()
    r = w[w.transacttype == 'RealisedPNL']
    realised = r.btc.groupby(r.day.dt.year).sum()
    out = p.btc.groupby(p.day.dt.year).sum()
    kept = (out / realised.reindex(out.index)).dropna()
    years = [str(y) for y in kept.index]
    gaps = p.day.diff().dt.days
    return card(
        'payday',
        {'en': 'Withdrawals came near the highs', 'ko': '출금은 고점 근처에서 나갔다'},
        {'value': f'{near:.0%}', 'unit': '', 'label': {'en': f'of {len(p)} withdrawals came within 5% of a 30-day equity high',
                                                       'ko': f'출금 {len(p)}번 중 30일 고점의 5% 이내에서 나간 비중'}},
        {'en': f'Each of the {len(p)} completed withdrawals, set against the account just before it: the median took '
               f'{p.share.median():.0%} of equity, and {near:.0%} came within 5% of the highest equity of the previous 30 days, '
               'not after a drop. Withdrawals came a median ' f'{gaps.median():.0f} days apart. As a share of each year\'s '
               'realised PnL he took out ' + ' → '.join(f'{v:.0%} ({y})' for y, v in zip(years, kept)) + f'. The very first one, '
               f'on {p.day.iloc[0]:%Y-%m-%d}, took {p.share.iloc[0]:.0%} of what the account held at the time.',
         'ko': f'완료된 출금 {len(p)}번을 각각 직전 계좌와 비교했다. 한 번에 자산의 중앙값 {p.share.median():.0%}를 뺐고, '
               f'{near:.0%}는 하락 뒤가 아니라 직전 30일 최고 자산의 5% 이내에서 나갔다. 출금 간격 중앙값은 {gaps.median():.0f}일. '
               '그해 실현손익 대비 출금 비중은 ' + ' → '.join(f'{v:.0%}({y})' for y, v in zip(years, kept)) + f'로 커졌다. '
               f'첫 출금({p.day.iloc[0]:%Y-%m-%d})은 그때 계좌에 있던 것의 {p.share.iloc[0]:.0%}를 가져갔다.'},
        {'type': 'bars', 'labels': {'en': years, 'ko': years}, 'values': [round(v * 100, 1) for v in kept], 'unit': '%'},
        withdrawals=len(p), median_share=round(float(p.share.median()), 4), near_high_share=round(float(near), 4),
        median_gap_days=float(gaps.median()), withdrawn_over_realised={y: round(float(v), 4) for y, v in zip(years, kept)},
        events=[{'day': str(d.date()), 'btc': round(float(b), 3), 'share': round(float(s), 4), 'near': bool(h > -0.05)}
                for d, b, s, h in rows])


def liquidations(ctx):
    f = ctx.f
    liq = f[f.text.astype(str).str.contains('Liquidation')].copy()
    liq['usd'] = np.where(liq.symbol.astype(str).str.startswith('XBT') | liq.symbol.astype(str).str.contains('USD'),
                          liq.foreignnotional.abs(), np.nan)
    liq['btc'] = btc_value(liq)
    ev = (liq.groupby([liq.ts.dt.floor('1min'), liq.symbol.astype(str)])
          .agg(qty=('lastqty', 'sum'), btc=('btc', 'sum'), usd=('usd', 'sum'))
          .reset_index())
    by_year = ev.groupby(ev.ts.dt.year).size()
    after = ev[ev.ts.dt.year > 2018]
    last18 = ev[ev.ts.dt.year == 2018].ts.max()
    biggest = ev.loc[ev.btc.idxmax()] if ev.btc.notna().any() else None
    years = [str(y) for y in range(2018, 2022)]
    counts = [int(by_year.get(int(y), 0)) for y in years]
    later_en = ', '.join(f'{r.ts:%Y-%m-%d} ({r.symbol}, {r.qty:,.0f} contracts)' for r in after.itertuples())
    later_ko = ', '.join(f'{r.ts:%Y-%m-%d}({r.symbol}, {r.qty:,.0f}계약)' for r in after.itertuples())
    return card(
        'liquidations',
        {'en': 'Liquidated 27 times in 2018, then almost never', 'ko': '2018년 27번 청산, 이후로는 거의 없다'}
        if counts[0] == 27 else {'en': 'Liquidations by year', 'ko': '연도별 강제청산'},
        {'value': str(counts[0]), 'unit': '', 'label': {'en': 'liquidation events in 2018', 'ko': '2018년 강제청산 횟수'}},
        {'en': f'{len(liq)} fills are marked "Liquidation": {len(ev)} events in all, {counts[0]} of them in 2018. '
               f'The largest, on {biggest.ts:%Y-%m-%d}, closed {biggest.qty:,.0f} {biggest.symbol} contracts worth '
               f'{biggest.btc:.1f} BTC. After '
               f'{last18:%B %Y} there are only {len(after)}: {later_en}. These fills are also the only ones missing from '
               'the public tape, because a liquidation hands the position to the exchange\'s engine instead of '
               'trading on the book.',
         'ko': f'"Liquidation" 표시가 붙은 체결은 {len(liq)}건, 사건으로는 {len(ev)}번이고 그중 {counts[0]}번이 2018년이다. '
               f'가장 컸던 {biggest.ts:%Y-%m-%d}에는 {biggest.symbol} {biggest.qty:,.0f}계약({biggest.btc:.1f} BTC)이 청산됐다. '
               f'{last18:%Y년 %m월} '
               f'이후로는 {len(after)}번뿐이다: {later_ko}. 이 체결들은 공개 테이프에서 빠진 유일한 체결이기도 하다. 강제청산은 '
               '호가창 거래가 아니라 거래소 청산 엔진으로 포지션을 넘기는 것이기 때문이다.'},
        {'type': 'bars', 'labels': {'en': years, 'ko': years}, 'values': counts, 'unit': 'events'},
        events=len(ev), fills=len(liq), by_year=dict(zip(years, counts)),
        biggest={'day': str(biggest.ts.date()), 'symbol': biggest.symbol, 'contracts': float(biggest.qty),
                 'btc': round(float(biggest.btc), 3)})


def by_coin(ctx):
    w = ctx.w
    r = w[w.transacttype == 'RealisedPNL']
    coin = r.symbol.str.replace(r'(USDM21|USDTZ20|USDT|USD|_U110|[FGHJKMNQUVXZ]\d\d)$', '', regex=True)
    coin = coin.str.replace('XBT7D', 'XBT').replace('XBT', 'BTC')
    by = r.btc.groupby(coin).sum().sort_values(ascending=False)
    total = by.sum()
    winners, losers = by[by > 0], by[by < 0]
    show = pd.concat([winners.head(6), losers.sort_values().head(2).sort_values(ascending=False)])
    return card(
        'by-coin',
        {'en': f'Where the {total:,.0f} BTC came from', 'ko': f'{total:,.0f} BTC는 어디서 나왔나'},
        {'value': f'{by.get("BTC", 0) / total:.0%}', 'unit': '', 'label': {'en': 'of realised PnL from Bitcoin contracts',
                                                                           'ko': '실현손익 중 비트코인 계약 비중'}},
        {'en': f'Grouping the wallet\'s realised PnL by underlying coin (perpetuals and dated futures together): '
               + ', '.join(f'{c} {v:+,.1f}' for c, v in winners.head(5).items()) + f' BTC. {len(losers)} coins lost money, '
               f'the worst {losers.idxmin()} at {losers.min():,.1f} BTC. Altcoins added {by.drop("BTC", errors="ignore").sum():,.1f} BTC '
               f'in total, nearly all of it from Ethereum.',
         'ko': '지갑의 실현손익을 기초 코인별로 묶었다(무기한과 만기 선물 합산): '
               + ', '.join(f'{c} {v:+,.1f}' for c, v in winners.head(5).items()) + f' BTC. 손실 코인은 {len(losers)}개이고 '
               f'가장 큰 손실은 {losers.idxmin()} {losers.min():,.1f} BTC다. 알트 전체로는 {by.drop("BTC", errors="ignore").sum():,.1f} BTC를 '
               '더했고 거의 전부가 이더리움에서 나왔다.'},
        {'type': 'bars', 'labels': {'en': list(show.index), 'ko': list(show.index)}, 'values': [round(v, 1) for v in show],
         'unit': 'BTC', 'signed': True},
        by_coin={c: round(v, 3) for c, v in by.items()})
