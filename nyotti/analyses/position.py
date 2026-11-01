"""What the account was, day by day: Bitcoin, dollars, a leveraged long or a bet on a fall, and how
the same history reads in each currency."""
import numpy as np
import pandas as pd

from . import BUCKETS, bucket, card

BUCKET_TEXT = {
    'short': ('a net short bet (-0.25x or less)', '순숏 베팅(-0.25배 이하)'),
    'dollars': ('parked in dollars (-0.25x to 0.25x)', '달러로 파킹(-0.25~0.25배)'),
    'hedged': ('partly hedged (0.25x to 0.85x)', '일부 헤지(0.25~0.85배)'),
    'bitcoin': ('about like holding Bitcoin (0.85x to 1.15x)', 'BTC 보유와 비슷(0.85~1.15배)'),
    'leveraged': ('a leveraged long (above 1.15x)', '레버리지 롱(1.15배 초과)'),
}


def daily_buckets(ctx):
    e = ctx.h.exposure.resample('1D').median().dropna()
    return pd.Series(bucket(e), index=e.index).astype(int), e


def shape(ctx):
    b, e = daily_buckets(ctx)
    q = pd.crosstab(b.index.to_period('Q'), b, normalize='index').reindex(columns=range(5), fill_value=0)
    y = pd.crosstab(b.index.year, b, normalize='index').reindex(columns=range(5), fill_value=0)
    med = ctx.h.exposure.groupby(ctx.h.index.year).median()
    quarters = [str(p) for p in q.index]
    top_lev = q[4].idxmax()
    top_short = q[0].idxmax()
    years = [str(v) for v in y.index]
    dollars_year = y[1].idxmax()
    return card(
        'account-shape',
        {'en': 'What the account was, quarter by quarter', 'ko': '분기마다 계좌는 무엇이었나'},
        {'value': f'{q[4].max():.0%}', 'unit': '', 'label': {'en': f'of days in {top_lev} the account was a leveraged long',
                                                             'ko': f'{top_lev} 중 레버리지 롱이었던 날의 비중'}},
        {'en': f'Each of the {len(b):,} days goes into one of five buckets by the account\'s median Bitcoin exposure that day: '
               + '; '.join(BUCKET_TEXT[k][0] for k in BUCKETS) + '. The median hour of every year sat almost exactly at 1x ('
               + ', '.join(f'{v:.2f}x' for v in med) + '), like plain Bitcoin, but the mix moved. '
               f'{dollars_year} had the most days parked in dollars ({y.loc[dollars_year, 1]:.0%}). '
               f'{top_short} had the most net short days ({q.loc[top_short, 0]:.0%}). {top_lev} was the most leveraged: '
               f'{q.loc[top_lev, 4]:.0%} of its days above 1.15x.',
         'ko': f'{len(b):,}일 하나하나를 그날 계좌의 BTC 노출도 중앙값으로 다섯 칸에 나눴다: '
               + '; '.join(BUCKET_TEXT[k][1] for k in BUCKETS) + '. 해마다 노출도 중앙값은 거의 정확히 1배('
               + ', '.join(f'{v:.2f}배' for v in med) + '), 즉 BTC를 그냥 들고 있는 것과 같았지만 구성은 계속 바뀌었다. '
               f'달러로 파킹한 날이 가장 많았던 해는 {dollars_year}년({y.loc[dollars_year, 1]:.0%}), 순숏 날이 가장 많았던 분기는 '
               f'{top_short}({q.loc[top_short, 0]:.0%}), 레버리지가 가장 높았던 분기는 {top_lev}(1.15배 초과인 날 {q.loc[top_lev, 4]:.0%})다.'},
        {'type': 'stack', 'labels': {'en': ['Net short', 'Dollars', 'Partly hedged', 'Like Bitcoin', 'Leveraged long'],
                                     'ko': ['순숏', '달러', '일부 헤지', 'BTC와 비슷', '레버리지 롱']},
         'periods': quarters, 'values': [[round(float(v), 3) for v in row] for row in q.to_numpy()]},
        days=len(b), by_year={yy: [round(float(v), 4) for v in y.loc[int(yy)]] for yy in years},
        median_exposure={str(k): round(float(v), 3) for k, v in med.items()}, buckets=BUCKETS)


def drawdowns(ctx, start='2019-01-01'):
    """Flow-adjusted index of the account in BTC and in dollars, and its running drawdown within each year."""
    d = ctx.daily
    d = d[d.index >= pd.Timestamp(start) - pd.Timedelta(days=1)]
    out = {}
    for unit in ('btc', 'usd'):
        idx = (1 + d[f'r_{unit}'].fillna(0)).cumprod()
        dd = idx / idx.groupby(idx.index.year).cummax() - 1
        out[unit] = dd[dd.index >= start]
    return pd.DataFrame(out)


def two_currencies(ctx):
    dd = drawdowns(ctx)
    yr = dd.groupby(dd.index.year)
    worst = yr.min()
    when = yr.idxmin()
    years = [str(v) for v in worst.index]
    eq, usd, px = ctx.daily.equity, ctx.daily.usd, ctx.daily.price
    peak_btc, peak_usd = eq.idxmax(), usd.idxmax()
    y2 = years[1] if len(years) > 1 else years[0]
    tb, tu = when.btc[int(y2)], when.usd[int(y2)]
    run = px[tb] / px[tb - pd.Timedelta(days=30)] - 1  # Bitcoin over the 30 days into the BTC-terms low
    run_en = f'after Bitcoin had {"risen" if run > 0 else "fallen"} {abs(run):.0%} in 30 days'
    run_ko = f'비트코인이 30일 동안 {abs(run):.0%} {"오른" if run > 0 else "내린"} 뒤인'
    if tb == tu:
        then_en = f'. In {y2} both lows fell on {tu:%B %d}'
        then_ko = f'다. {y2}년에는 두 기준의 바닥이 모두 {tu.month}월 {tu.day}일이었다'
    else:
        then_en = (f'. In {y2} the dollar low came on {tu:%B %d}, while counted in bitcoin the account\'s worst stretch '
                   f'ended on {tb:%B %d}, {run_en}')
        then_ko = (f'다. {y2}년 달러 기준 바닥은 {tu.month}월 {tu.day}일이었지만, 비트코인으로 세면 가장 나빴던 구간은 {run_ko} '
                   f'{tb.month}월 {tb.day}일에 끝났다')
    return card(
        'two-currencies',
        {'en': 'Count in dollars and the worst days move', 'ko': '달러로 세면 최악의 날이 바뀐다'},
        {'value': f'{worst.usd[int(y2)]:.0%} vs {worst.btc[int(y2)]:.0%}', 'unit': '',
         'label': {'en': f'deepest {y2} drawdown, in dollars vs in bitcoin', 'ko': f'{y2}년 최대 낙폭, 달러 기준 vs 비트코인 기준'}},
        {'en': 'His margin was Bitcoin, so the record is kept in BTC. The same account counted in dollars tells a different '
               'story, because a hedged account gains bitcoins when the price falls and loses them when it rises. With transfers '
               'removed, the deepest fall within each year was '
               + ', '.join(f'{-b:.0%} in BTC ({b_t:%m-%d}) and {-u:.0%} in dollars ({u_t:%m-%d}) in {y}'
                           for y, b, u, b_t, u_t in zip(years, worst.btc, worst.usd, when.btc, when.usd))
               + then_en + f'. Even his record high depends on the unit: {peak_btc:%Y-%m-%d} in bitcoin, '
               f'{peak_usd:%Y-%m-%d} in dollars.',
         'ko': '증거금이 비트코인이라 기록은 BTC로 남는다. 같은 계좌를 달러로 세면 이야기가 달라진다. 헤지한 계좌는 가격이 내리면 '
               'BTC 개수가 늘고 오르면 줄기 때문이다. 입출금을 뺀 연도별 최대 낙폭은 '
               + ', '.join(f'{y}년 BTC 기준 {-b:.0%}({b_t:%m-%d}), 달러 기준 {-u:.0%}({u_t:%m-%d})'
                           for y, b, u, b_t, u_t in zip(years, worst.btc, worst.usd, when.btc, when.usd))
               + then_ko + f'. 최고 기록도 단위에 따라 다르다: 비트코인 기준 {peak_btc:%Y-%m-%d}, 달러 기준 {peak_usd:%Y-%m-%d}.'},
        {'type': 'pair', 'labels': {'en': ['In bitcoin', 'In dollars'], 'ko': ['비트코인 기준', '달러 기준']},
         'years': years, 'values': [[round(-float(v), 3) for v in worst.btc], [round(-float(v), 3) for v in worst.usd]],
         'unit': '%'},
        worst_btc={y: round(float(v), 4) for y, v in zip(years, worst.btc)}, worst_usd={y: round(float(v), 4) for y, v in zip(years, worst.usd)},
        worst_btc_day={y: str(t.date()) for y, t in zip(years, when.btc)}, worst_usd_day={y: str(t.date()) for y, t in zip(years, when.usd)},
        peak_btc_day=str(peak_btc.date()), peak_usd_day=str(peak_usd.date()))
