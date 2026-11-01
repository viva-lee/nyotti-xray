"""Behavioral lenses on the record: which orders he used, what he held, what he added to, and the day after."""
import numpy as np
import pandas as pd

from . import card, fmt, wmedian

KINDS_GROW = ['open', 'add', 'flip']


def _human(h):
    return f'{h * 60:.0f} min' if h < 1 else f'{h:.1f} h'


def _human_ko(h):
    return f'{h * 60:.0f}분' if h < 1 else f'{h:.1f}시간'


def plain_orders(ctx):
    """Stop orders, hidden orders and icebergs: the order types that work without a hand on the mouse."""
    o = ctx.orders
    y = o.ts.dt.year
    years = [str(v) for v in sorted(y.unique())]
    # Liquidation fills sit under two exchange-side order ids, one of which also holds a stop fill; they are not his orders.
    stop = o.source == 'stop'
    stops = stop.groupby(y).sum().reindex([int(v) for v in years], fill_value=0)
    n_stop, n_hidden, n_ice = int(stop.sum()), int((o.hidden & ~o.liq).sum()), int((o.iceberg & ~o.liq).sum())
    hidden_fills = float((ctx.f.displayqty.notna() & (ctx.f.displayqty == 0)).mean())
    market = int((o.ordtype == 'Market').sum())
    close = int(o.close.sum())
    last = years[-1]
    none_last = int(stops.iloc[-1]) == 0
    tail_en = f'none in {last}' if none_last else f'{int(stops.iloc[-1])} in {last}'
    tail_ko = f'{last}년에는 하나도 없다' if none_last else f'{last}년 {int(stops.iloc[-1])}개'
    return card(
        'plain-orders',
        {'en': f'{n_stop} stop orders in four years', 'ko': f'4년 동안 스톱 주문 {n_stop}개'},
        {'value': str(n_stop), 'unit': '', 'label': {'en': f'stop orders out of {fmt(len(o))}',
                                                     'ko': f'개가 스톱 주문 (전체 {fmt(len(o))}개 중)'}},
        {'en': f'A stop order waits for a price and then fires on its own; it is the usual way to cap a loss without '
               f'watching. Of his {fmt(len(o))} orders, {n_stop} were stops: '
               + ', '.join(f'{int(v)} in {k}' for k, v in zip(years[:-1], stops.iloc[:-1])) + f', {tail_en}. '
               f'None was an iceberg, and orders hidden from the book account for {hidden_fills:.1%} of fills. '
               f'Over the same four years he sent {fmt(market)} market orders and pressed the Close button {fmt(close)} times.',
         'ko': f'스톱 주문은 정해 둔 가격에 닿으면 저절로 나가는 주문으로, 화면을 보지 않고 손실을 끊는 보통의 방법이다. '
               f'그의 주문 {fmt(len(o))}개 중 스톱은 {n_stop}개다: '
               + ', '.join(f'{k}년 {int(v)}개' for k, v in zip(years[:-1], stops.iloc[:-1])) + f', {tail_ko}. '
               f'빙산(아이스버그) 주문은 하나도 없고, 호가창에 숨긴 주문의 체결은 {hidden_fills:.1%}뿐이다. '
               f'같은 4년 동안 시장가 주문은 {fmt(market)}개, 포지션 종료 버튼은 {fmt(close)}번 썼다.'},
        {'type': 'bars', 'labels': {'en': years, 'ko': years}, 'values': [int(v) for v in stops], 'unit': 'orders'},
        orders=len(o), stops=n_stop, stops_by_year=dict(zip(years, [int(v) for v in stops])), hidden_orders=n_hidden,
        hidden_fill_share=round(hidden_fills, 5), icebergs=n_ice, market_orders=market, close_button_orders=close)


def winners_first(ctx):
    """LIFO: pair each closing XBTUSD contract with the newest open one, then compare how long the
    pieces closed at a gain and at a loss had been held."""
    rows, fifo_same = [], []
    for name, lots in (('lifo', ctx.lots_lifo), ('fifo', ctx.lots_fifo)):
        for y, g in lots.groupby('year'):
            win, lose = g[g.pnl > 0], g[g.pnl < 0]
            row = {'year': int(y), 'win_h': wmedian(win.hours, win.qty), 'lose_h': wmedian(lose.hours, lose.qty),
                   'win_share': win.qty.sum() / g.qty.sum(),
                   'payoff': -(lose.pnl.sum() / lose.qty.sum()) / (win.pnl.sum() / win.qty.sum())}
            if name == 'lifo':
                rows.append(row)
            else:
                fifo_same.append(row['lose_h'] > row['win_h'])
    r = pd.DataFrame(rows)
    ratio = r.lose_h / r.win_h
    years = [str(v) for v in r.year]
    every = bool((ratio > 1).all())
    fifo_all = all(fifo_same)
    return card(
        'winners-first',
        {'en': 'Winners closed sooner than losers', 'ko': '이긴 계약은 빨리, 진 계약은 오래'},
        {'value': f'{ratio.min():.1f}-{ratio.max():.1f}x', 'unit': '',
         'label': {'en': 'longer median hold for pieces closed at a loss, every year',
                   'ko': '손실로 닫힌 계약의 보유시간이 더 길었다(매년, 중앙값)'}},
        {'en': 'Pairing each closing XBTUSD contract with the most recent opening one (LIFO), the pieces closed at a loss '
               'had been held longer than the pieces closed at a gain' + (' in every year: ' if every else ': ')
               + ', '.join(f'{_human(a)} vs {_human(b)} ({y})' for y, a, b in zip(years, r.win_h, r.lose_h)) + '. '
               f'Gains were more common, {" → ".join(f"{v:.0%}" for v in r.win_share)} of contracts, and smaller: a losing '
               f'contract lost {r.payoff.min():.1f}-{r.payoff.max():.1f}x what a winning one gained. Behavioral finance calls '
               'holding losers longer than winners the disposition effect. '
               + ('Matching oldest-first (FIFO) instead gives the same order in every year.' if fifo_all else
                  'Matching oldest-first (FIFO) does not give the same order in every year.'),
         'ko': '청산되는 XBTUSD 계약을 가장 최근 진입분과 짝지으면(LIFO), 손실로 닫힌 계약이 이익으로 닫힌 계약보다 '
               + ('매년 ' if every else '') + '더 오래 보유됐다: '
               + ', '.join(f'{y}년 {_human_ko(a)} 대 {_human_ko(b)}' for y, a, b in zip(years, r.win_h, r.lose_h)) + '. '
               f'이익은 더 자주 났고(계약 기준 {" → ".join(f"{v:.0%}" for v in r.win_share)}) 더 작았다: 손실 계약 하나가 잃은 '
               f'금액은 이익 계약 하나가 번 금액의 {r.payoff.min():.1f}~{r.payoff.max():.1f}배다. 행동재무학은 진 포지션을 이긴 '
               '포지션보다 오래 쥐는 경향을 처분 효과라고 부른다. '
               + ('가장 오래된 진입분부터 짝지어도(FIFO) 매년 같은 순서가 나온다.' if fifo_all else
                  '가장 오래된 진입분부터 짝지으면(FIFO) 해마다 순서가 같지는 않다.')},
        {'type': 'pair', 'labels': {'en': ['Closed at a gain', 'Closed at a loss'], 'ko': ['이익으로 닫힘', '손실로 닫힘']},
         'years': years, 'values': [[round(v, 3) for v in r.win_h], [round(v, 3) for v in r.lose_h]], 'unit': 'h', 'log': True},
        win_hours={y: round(v, 3) for y, v in zip(years, r.win_h)}, loss_hours={y: round(v, 3) for y, v in zip(years, r.lose_h)},
        win_share={y: round(v, 4) for y, v in zip(years, r.win_share)}, loss_to_gain={y: round(v, 3) for y, v in zip(years, r.payoff)},
        fifo_same_order=fifo_all)


def add_entries(ctx):
    """For every XBTUSD decision, the average entry price of the position just before it (NaN when flat)."""
    bk = ctx.book
    bx = bk[bk.symbol == 'XBTUSD'].reset_index(drop=True)
    t = ctx.xbt_fills.reset_index(drop=True)
    if len(bx) != len(t) or not (bx.ts.to_numpy() == t.ts.to_numpy()).all():
        raise ValueError('book and XBTUSD fills are out of step')
    new = (t.ts.diff() > pd.Timedelta(minutes=20)) | (t.side != t.side.shift())
    first = pd.Series(np.arange(len(t))).groupby((new.cumsum() - 1).to_numpy()).first().to_numpy()
    prev = np.clip(first - 1, 0, None)
    n = np.where(first > 0, bx.n.to_numpy()[prev], 0.0)
    c = np.where(first > 0, bx.cost.to_numpy()[prev], 0.0)
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(c != 0, n / c, np.nan)  # inverse contracts: n / (sum of n_i / p_i)


def underwater_adds(ctx):
    """When he added to a position, was the price already against it?"""
    d = ctx.d.assign(entry=add_entries(ctx))
    a = d[d.kind == 'add'].copy()
    long_ = a.pos_before > 0
    a['against'] = np.where(long_, a.vwap / a.entry - 1, 1 - a.vwap / a.entry) * -1  # > 0: price beyond the entry, against him
    a['under'] = a.against > 0
    yr = a.groupby('year')
    share = yr.under.mean()
    usd_share = a.size_usd[a.under].sum() / a.size_usd.sum()
    years = [str(v) for v in share.index]
    gap = a.against[a.under].median()
    return card(
        'underwater-adds',
        {'en': 'Two of three adds went into a losing position', 'ko': '추가 매매 세 번 중 두 번은 손실 중인 포지션에'},
        {'value': f'{a.under.mean():.0%}', 'unit': '', 'label': {'en': f'of his {fmt(len(a))} adds came while the position was underwater',
                                                                'ko': f'추가 매매 {fmt(len(a))}번 중 포지션이 손실 상태일 때'}},
        {'en': f'{fmt(len(a))} of his XBTUSD decisions added to an open position. Comparing each one with the average entry '
               f'price of the position it joined: {a.under.mean():.0%} of them ({usd_share:.0%} by size) came when the price had '
               f'already moved against the position, a median {gap:.1%} past the entry. By year: '
               + ', '.join(f'{v:.0%} ({y})' for y, v in zip(years, share)) + f'. Long adds {a.under[long_].mean():.0%}, '
               f'short adds {a.under[~long_].mean():.0%}. Some short adds were not bets at all: on an inverse contract, '
               'keeping the account in dollars after a rise takes more short contracts.',
         'ko': f'그의 XBTUSD 결정 중 {fmt(len(a))}개가 이미 열린 포지션에 추가한 매매다. 각각을 그 포지션의 평균 진입가와 '
               f'비교하면 {a.under.mean():.0%}(금액 기준 {usd_share:.0%})가 가격이 이미 포지션 반대로 움직인 뒤였다. 진입가에서 '
               f'중앙값 {gap:.1%} 벗어난 지점이다. 연도별로 ' + ', '.join(f'{v:.0%}({y})' for y, v in zip(years, share))
               + f'. 롱 추가는 {a.under[long_].mean():.0%}, 숏 추가는 {a.under[~long_].mean():.0%}였다. 숏 추가 중 일부는 '
               '베팅이 아니다. 인버스 계약에서 가격이 오른 뒤 계좌를 달러로 유지하려면 숏 계약이 더 필요하다.'},
        {'type': 'bars', 'labels': {'en': years, 'ko': years}, 'values': [round(v * 100, 1) for v in share], 'unit': '%'},
        adds=len(a), underwater_share=round(float(a.under.mean()), 4), underwater_usd_share=round(float(usd_share), 4),
        by_year={y: round(v, 4) for y, v in zip(years, share)}, long_share=round(float(a.under[long_].mean()), 4),
        short_share=round(float(a.under[~long_].mean()), 4), median_gap=round(float(gap), 5))


def day_after(ctx, best):
    """Next-day behavior after his 20 best or worst days (mark-to-market in BTC, from 2019)."""
    r = ctx.daily_return
    r = r[r.index >= '2019-01-01']
    days = r.sort_values(ascending=not best).head(20).index
    d = ctx.d.assign(day=ctx.d.start.dt.floor('1D'))
    per = d.groupby('day').agg(n=('id', 'size'), rel=('size_rel', 'median')).reindex(r.index)
    per['n'] = per.n.fillna(0)
    base = per.n.rolling(30, min_periods=10).median()
    nxt = [x + pd.Timedelta(days=1) for x in days]
    with np.errstate(divide='ignore', invalid='ignore'):
        act = np.nanmedian([per.n.get(n, np.nan) / base.get(x, np.nan) for n, x in zip(nxt, days)])
    net = ctx.h.net.resample('1D').last()
    usd = ctx.daily.usd
    move = np.nanmedian([(net.get(n, np.nan) - net.get(x, np.nan)) / usd.get(x, np.nan) for n, x in zip(nxt, days)])
    return {'days': days, 'activity': float(act), 'size': float(per.rel.reindex(nxt).median()),
            'quiet': float(np.mean([per.n.get(n, 0) == 0 for n in nxt])), 'exposure_move': float(move),
            'low': float(r[days].min()), 'high': float(r[days].max())}


def after_best_days(ctx):
    b, w = day_after(ctx, True), day_after(ctx, False)
    return card(
        'after-the-best-days',
        {'en': 'The day after his best days', 'ko': '최고의 날 다음 날'},
        {'value': f'{b["exposure_move"]:+.2f}x vs {w["exposure_move"]:+.2f}x', 'unit': '',
         'label': {'en': 'median change his trades made to Bitcoin exposure the next day, after best vs worst days',
                   'ko': '다음 날 그의 매매가 바꾼 BTC 노출도(중앙값), 최고의 날 뒤 vs 최악의 날 뒤'}},
        {'en': f'The mirror of the worst-days check: his 20 best days by mark-to-market return, 2019-2021, from {b["low"]:+.1%} '
               f'to {b["high"]:+.1%}. After both kinds of day he was busier than usual, {b["activity"]:.1f}x his usual number '
               f'of XBTUSD decisions after the best and {w["activity"]:.1f}x after the worst. After neither did his trades '
               f'get much bigger: {b["size"]:.2f}x and {w["size"]:.2f}x his typical contract size that year. The difference '
               f'was direction. After his worst days, the contracts he traded moved his Bitcoin exposure by a median '
               f'{w["exposure_move"]:+.2f}x of equity; after his best days, by {b["exposure_move"]:+.2f}x. '
               f'{b["quiet"]:.0%} of the days after a best day had no XBTUSD decision at all.',
         'ko': f'최악의 날 검사를 뒤집었다: 2019~2021년 일간 평가손익 기준 최고의 20일({b["low"]:+.1%}~{b["high"]:+.1%}). '
               f'두 경우 모두 다음 날 평소보다 바빴다. XBTUSD 결정 수가 최고의 날 뒤에는 평소의 {b["activity"]:.1f}배, '
               f'최악의 날 뒤에는 {w["activity"]:.1f}배였다. 어느 쪽에서도 거래가 크게 커지지 않았다: 그해 평소 계약 크기의 '
               f'{b["size"]:.2f}배와 {w["size"]:.2f}배. 달랐던 것은 방향이다. 최악의 날 다음 날 그가 거래한 계약은 BTC 노출도를 '
               f'자산 대비 중앙값 {w["exposure_move"]:+.2f}배만큼 움직였고, 최고의 날 다음 날에는 {b["exposure_move"]:+.2f}배였다. '
               f'최고의 날 다음 날의 {b["quiet"]:.0%}는 XBTUSD 결정이 아예 없었다.'},
        None, best_low=round(b['low'], 4), best_high=round(b['high'], 4), activity_best=round(b['activity'], 3),
        activity_worst=round(w['activity'], 3), size_best=round(b['size'], 3), size_worst=round(w['size'], 3),
        exposure_move_best=round(b['exposure_move'], 3), exposure_move_worst=round(w['exposure_move'], 3),
        quiet_best=round(b['quiet'], 3), quiet_worst=round(w['quiet'], 3),
        best_days=[str(x.date()) for x in b['days']], worst_days=[str(x.date()) for x in w['days']])
