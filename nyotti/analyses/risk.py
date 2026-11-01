"""Risk lenses: how far the account sat from zero, and the year he was liquidated 27 times."""
import numpy as np
import pandas as pd

from . import card


def distance(exposure):
    """The Bitcoin move that would take a BTC-margined account's equity to zero, as a fraction of the price.

    Equity E in BTC with net inverse contracts N at price P has exposure e = 1 + N / (P * E). Equity reaches
    zero at P' with P' / P = (e - 1) / e: a fall of 1/e when e > 1, a rise of 1/|e| when e < 0, and never
    when 0 <= e <= 1. Returns (fraction, side) with side +1 for a fall, -1 for a rise, 0 when no move does it.
    """
    e = np.asarray(exposure, dtype=float)
    with np.errstate(divide='ignore'):
        frac = np.where(e > 1, 1 / e, np.where(e < 0, -1 / e, np.inf))
    side = np.where(e > 1, 1, np.where(e < 0, -1, 0))
    return frac, side


def distance_to_zero(ctx):
    h = ctx.h.dropna(subset=['exposure'])
    frac, side = distance(h.exposure)
    s = pd.DataFrame({'d': frac, 'side': side}, index=h.index)
    yr = s.groupby(s.index.year)
    years = [str(y) for y in yr.groups]
    closest = yr.d.min()
    when = yr.d.idxmin()
    safe = yr.side.apply(lambda v: (v == 0).mean())
    within = yr.d.apply(lambda v: (v < 0.5).mean())
    within25 = yr.d.apply(lambda v: (v < 0.25).mean())
    later = s[s.index >= f'{int(years[1])}-07-01']
    floor_later = later.d.min()
    word = {1: ('fall', '하락'), -1: ('rise', '상승')}
    return card(
        'distance-to-zero',
        {'en': 'How far the account sat from zero', 'ko': '계좌는 0에서 얼마나 떨어져 있었나'},
        {'value': f'{closest.iloc[0]:.0%} → {closest.iloc[-1]:.0%}', 'unit': '',
         'label': {'en': f'smallest Bitcoin move that could have emptied the account, {years[0]} vs {years[-1]}',
                   'ko': f'계좌를 0으로 만들 수 있었던 가장 작은 BTC 변동폭, {years[0]} vs {years[-1]}'}},
        {'en': 'With Bitcoin as margin, the account goes to zero only if Bitcoin moves far enough against its net '
               'exposure: a fall of 1/e at e times exposure, a rise of 1/|e| when net short, and no move at all between '
               '0x and 1x. Hour by hour, the smallest such move by year was '
               + ', '.join(f'{v:.1%} ({y}, a {word[int(s.side[t])][0]} on {t:%Y-%m-%d})' for y, v, t in zip(years, closest, when))
               + '. In ' + ', '.join(f'{v:.0%}' for v in safe) + ' of hours (by year) no Bitcoin move could have done it, and '
               f'after June {years[1]} it never came within {floor_later:.0%}. Hours within a 25% move: '
               + ', '.join(f'{v:.1%}' for v in within25) + '. This counts Bitcoin contracts only; altcoin positions and '
               'maintenance margin are left out, and an isolated position, as in the 2018 liquidations, can fail long before '
               'the whole account would.',
         'ko': 'BTC가 증거금이면 계좌는 비트코인이 순노출의 반대 방향으로 충분히 움직여야만 0이 된다. 노출도가 e배면 1/e만큼 하락, '
               '순숏이면 1/|e|만큼 상승해야 하고, 0~1배 사이에서는 어떤 움직임으로도 0이 되지 않는다. 시간 단위로 본 연도별 최소 '
               '변동폭은 ' + ', '.join(f'{y}년 {v:.1%}({t:%Y-%m-%d} {word[int(s.side[t])][1]})' for y, v, t in zip(years, closest, when))
               + '. 연도별로 ' + ', '.join(f'{v:.0%}' for v in safe) + '의 시간은 BTC가 어떻게 움직여도 0이 될 수 없었고, '
               f'{years[1]}년 6월 이후로는 한 번도 {floor_later:.0%} 안쪽으로 들어오지 않았다. 25% 변동이면 0이 되는 시간의 비중: '
               + ', '.join(f'{v:.1%}' for v in within25) + '. 비트코인 계약만 셌다. 알트 포지션과 유지증거금은 빠져 있고, '
               '2018년 강제청산처럼 격리 마진 포지션은 계좌 전체보다 훨씬 먼저 무너질 수 있다.'},
        {'type': 'bars', 'labels': {'en': years, 'ko': years}, 'values': [round(v * 100, 1) for v in closest], 'unit': '%'},
        closest={y: round(float(v), 4) for y, v in zip(years, closest)}, closest_at={y: str(t) for y, t in zip(years, when)},
        safe_share={y: round(float(v), 4) for y, v in zip(years, safe)}, within_50={y: round(float(v), 4) for y, v in zip(years, within)},
        within_25={y: round(float(v), 4) for y, v in zip(years, within25)}, floor_after_mid_year_two=round(float(floor_later), 4))


def year_2018(ctx):
    h = ctx.h.loc['2018']
    f = ctx.f
    liq = f[f.text.astype(str).str.contains('Liquidation')]
    ev = liq.groupby([liq.ts.dt.floor('1min'), liq.symbol.astype(str)]).size().reset_index()
    ev = ev[ev.ts.dt.year == 2018]
    months = pd.date_range('2018-03-01', '2018-12-01', freq='MS')
    m = pd.DataFrame({
        'p95': h.gross_leverage.resample('MS').quantile(.95),
        'equity': h.equity.resample('MS').median(),
        'liqs': ev.groupby(ev.ts.dt.to_period('M').dt.to_timestamp()).size(),
    }).reindex(months)
    m['liqs'] = m.liqs.fillna(0).astype(int)
    labels_en = [f'{t:%b}' for t in m.index]
    labels_ko = [f'{t.month}월' for t in m.index]
    first, last = m.iloc[0], m.iloc[-1]
    quiet = [f'{t:%b}' for t, v in m.liqs.items() if v == 0]
    quiet_ko = [f'{t.month}월' for t, v in m.liqs.items() if v == 0]
    return card(
        'year-2018',
        {'en': '2018, month by month', 'ko': '2018년, 한 달씩'},
        {'value': f'{first.p95:.0f}x → {last.p95:.1f}x', 'unit': '',
         'label': {'en': '95th-percentile gross leverage, March vs December 2018', 'ko': '총 레버리지 95백분위, 2018년 3월 vs 12월'}},
        {'en': f'His first year, zoomed in. In March the account held a median {first.equity:.2f} BTC, gross leverage reached '
               f'{first.p95:.0f}x at the 95th percentile and he was liquidated {int(first.liqs)} times. Month by month the '
               'leverage came down: ' + ', '.join(f'{lab} {v:.1f}x' for lab, v in zip(labels_en, m.p95)) + '. Liquidations by '
               'month: ' + ', '.join(f'{lab} {v}' for lab, v in zip(labels_en, m.liqs)) + f'. By December the median balance '
               f'was {last.equity:,.0f} BTC; {", ".join(quiet)} had no liquidation at all.',
         'ko': f'첫해를 확대했다. 3월 계좌 잔고 중앙값은 {first.equity:.2f} BTC, 총 레버리지 95백분위는 {first.p95:.0f}배였고 강제청산을 '
               f'{int(first.liqs)}번 당했다. 레버리지는 달마다 내려왔다: ' + ', '.join(f'{lab} {v:.1f}배' for lab, v in zip(labels_ko, m.p95))
               + '. 월별 강제청산: ' + ', '.join(f'{lab} {v}번' for lab, v in zip(labels_ko, m.liqs)) + f'. 12월 잔고 중앙값은 '
               f'{last.equity:,.0f} BTC였고, {", ".join(quiet_ko)}에는 강제청산이 한 번도 없었다.'},
        {'type': 'bars', 'labels': {'en': labels_en, 'ko': labels_ko}, 'values': [round(v, 2) for v in m.p95], 'unit': 'x', 'log': True},
        p95={str(t.date()): round(float(v), 3) for t, v in m.p95.items()},
        median_equity={str(t.date()): round(float(v), 3) for t, v in m.equity.items()},
        liquidations={str(t.date()): int(v) for t, v in m.liqs.items()})
