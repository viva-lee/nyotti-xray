"""Case studies: two days minute by minute, the tape's XBTUSD closes with his fills on top."""
import pandas as pd

from . import card
from .proof import tape_days


def _case(ctx, first_day):
    t0 = pd.Timestamp(first_day)
    names = [str((t0 + pd.Timedelta(days=k)).date()) for k in (0, 1)]
    days = {d['day']: d for d in tape_days() if d['day'] in names}
    if len(days) < 2:
        return None
    bars = days[names[0]]['bars']['XBTUSD'] + days[names[1]]['bars']['XBTUSD']
    close = pd.Series([b[3] if b else None for b in bars], dtype=float).ffill().bfill()
    f = ctx.f[(ctx.f.symbol == 'XBTUSD') & (ctx.f.ts >= t0) & (ctx.f.ts < t0 + pd.Timedelta(days=2))]
    minute = ((f.ts - t0).dt.total_seconds() // 60).astype(int)
    buy = f.lastqty.where(f.side == 'Buy', 0).groupby(minute).sum().reindex(range(2880), fill_value=0)
    sell = f.lastqty.where(f.side == 'Sell', 0).groupby(minute).sum().reindex(range(2880), fill_value=0)
    step = 5
    k = len(close) // step
    low_i = int(close.idxmin())
    h = ctx.h.loc[t0 - pd.Timedelta(hours=1): t0 + pd.Timedelta(hours=47)]
    w = ctx.w[ctx.w.transacttype == 'RealisedPNL'].groupby('day').btc.sum()
    return {
        'close': close, 'low_t': t0 + pd.Timedelta(minutes=low_i), 'buy': buy, 'sell': sell,
        'near_low': buy.iloc[max(0, low_i - 60):low_i + 61].sum(),
        'exp_start': h.exposure.iloc[0], 'exp_max': h.exposure.max(), 'exp_end': h.exposure.iloc[-1],
        'eq_start': h.equity.iloc[0], 'eq_min': h.equity.min(),
        'booked': [w.get(t0 + pd.Timedelta(days=d), 0.0) for d in (0, 1, 2)],
        'chart': {'type': 'tape', 'step_minutes': step, 'days': [n[5:] for n in names],
                  'price': [round(float(v), 1) for v in close.iloc[:k * step].to_numpy().reshape(k, step)[:, -1]],
                  'buy': [round(float(v) / 1e6, 3) for v in buy.to_numpy()[:k * step].reshape(k, step).sum(1)],
                  'sell': [round(float(v) / 1e6, 3) for v in sell.to_numpy()[:k * step].reshape(k, step).sum(1)],
                  'legend': {'en': ['XBTUSD price (tape)', 'his buys', 'his sells'],
                             'ko': ['XBTUSD 가격(테이프)', '그의 매수', '그의 매도']}},
    }


def black_thursday(ctx):
    c = _case(ctx, '2020-03-12')
    if c is None:
        return None
    close, b, s = c['close'], c['buy'].sum(), c['sell'].sum()
    b12, b13 = c['booked'][0], c['booked'][1]
    return card(
        'black-thursday',
        {'en': '48 hours of March 2020, minute by minute', 'ko': '2020년 3월의 48시간, 분 단위로'},
        {'value': f'{b13:+,.1f} BTC', 'unit': '', 'label': {'en': 'realised on 2020-03-13, his best day',
                                                             'ko': '2020-03-13 실현손익(최고의 날)'}},
        {'en': f'On 2020-03-12/13 Bitcoin fell from {close.iloc[0]:,.0f} to a low of {close.min():,.0f} at {c["low_t"]:%m-%d %H:%M} UTC '
               f'(tape minute closes) and ended at {close.iloc[-1]:,.0f}. Over the 48 hours he bought {b / 1e6:,.1f}M and sold '
               f'{s / 1e6:,.1f}M XBTUSD contracts; {c["near_low"] / 1e6:,.1f}M of the buys came within an hour of the low. His account '
               f'went from {c["exp_start"]:.2f}x to {c["exp_end"]:.2f}x Bitcoin exposure, peaking at {c["exp_max"]:.2f}x. The wallet '
               f'booked {b12:+,.1f} BTC on the 12th and {b13:+,.1f} BTC on the 13th.',
         'ko': f'2020-03-12~13, 비트코인은 {close.iloc[0]:,.0f}에서 {c["low_t"]:%m-%d %H:%M} UTC에 {close.min():,.0f}까지 떨어졌다가 '
               f'{close.iloc[-1]:,.0f}에 마감했다(테이프 1분 종가). 48시간 동안 그는 XBTUSD {b / 1e6:,.1f}M 계약을 사고 {s / 1e6:,.1f}M '
               f'계약을 팔았다. 매수 중 {c["near_low"] / 1e6:,.1f}M이 저점 전후 1시간 안에 나왔다. 계좌의 BTC 노출도는 '
               f'{c["exp_start"]:.2f}배에서 {c["exp_end"]:.2f}배가 됐고 최고 {c["exp_max"]:.2f}배였다. 지갑에는 12일 {b12:+,.1f} BTC, '
               f'13일 {b13:+,.1f} BTC가 기록됐다.'},
        c['chart'], low=float(close.min()), low_time=str(c['low_t']), bought=float(b), sold=float(s),
        bought_near_low=float(c['near_low']), booked_12=round(float(b12), 2), booked_13=round(float(b13), 2))


def worst_day(ctx):
    """The day his account lost the most, mark-to-market in BTC with transfers removed (from 2019)."""
    r = ctx.daily_return
    r = r[r.index >= '2019-01-01']
    day = r.idxmin()
    c = _case(ctx, str(day.date()))
    if c is None:
        return None
    close, b, s = c['close'], c['buy'].sum(), c['sell'].sum()
    nxt = r.reindex([day + pd.Timedelta(days=k) for k in (1, 2)]).fillna(0).to_numpy()
    en_day = f'{day:%B} {day.day}, {day.year}'
    e0 = c['exp_start']
    start_en = 'mostly in dollars' if e0 < 0.25 else 'partly hedged' if e0 < 0.85 else 'about like holding Bitcoin'
    start_ko = '대부분 달러' if e0 < 0.25 else '일부 헤지' if e0 < 0.85 else '비트코인 보유와 비슷'
    return card(
        'worst-day',
        {'en': f'His worst day: {en_day}', 'ko': f'최악의 날: {day.year}년 {day.month}월 {day.day}일'},
        {'value': f'{r.min():.1%}', 'unit': '', 'label': {'en': 'account equity in BTC in one day, mark-to-market',
                                                          'ko': '하루 동안 BTC 기준 계좌 자산 변화(평가)'}},
        {'en': f'On {day:%Y-%m-%d} Bitcoin fell from {close.iloc[0]:,.0f} to {close.min():,.0f} at {c["low_t"]:%H:%M} UTC. He started '
               f'the day at {c["exp_start"]:.2f}x Bitcoin exposure ({start_en}) and bought into the fall: exposure reached '
               f'{c["exp_max"]:.2f}x. His equity went from {c["eq_start"]:,.0f} BTC to {c["eq_min"]:,.0f} BTC at the worst hour, and the '
               f'day closed {r.min():.1%}. Over the two days he bought {b / 1e6:,.1f}M and sold {s / 1e6:,.1f}M XBTUSD contracts. '
               f'The next two days were {nxt[0]:+.1%} and {nxt[1]:+.1%}.',
         'ko': f'{day:%Y-%m-%d}, 비트코인은 {close.iloc[0]:,.0f}에서 {c["low_t"]:%H:%M} UTC에 {close.min():,.0f}까지 떨어졌다. 그는 BTC '
               f'노출도 {c["exp_start"]:.2f}배({start_ko})로 하루를 시작해 하락 중에 매수했고, 노출도가 {c["exp_max"]:.2f}배까지 올라갔다. '
               f'자산은 {c["eq_start"]:,.0f} BTC에서 가장 나쁜 시간에 {c["eq_min"]:,.0f} BTC가 됐고, 그날 하루 {r.min():.1%}로 끝났다. '
               f'이틀 동안 XBTUSD {b / 1e6:,.1f}M 계약을 사고 {s / 1e6:,.1f}M 계약을 팔았다. 다음 이틀은 {nxt[0]:+.1%}, {nxt[1]:+.1%}였다.'},
        c['chart'], day=str(day.date()), day_return=round(float(r.min()), 4), equity_start=round(float(c['eq_start']), 1),
        equity_min=round(float(c['eq_min']), 1), exposure_start=round(float(c['exp_start']), 2),
        exposure_max=round(float(c['exp_max']), 2), next_two_days=[round(float(v), 4) for v in nxt])
