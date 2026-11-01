"""How he traded: by hand, with limit orders, slowing from scalps to swings, around the clock."""
import pandas as pd

from . import card, fmt, wmedian


def by_hand(ctx):
    f = ctx.f
    text = f.text.astype(str)
    web = text.str.contains('www.bitmex.com')
    liq = text.str.contains('Liquidation')
    amended = text.str.contains('Amend')
    close_btn = text.str.contains('Position Close')
    api = ~(web | liq)
    orders = f.orderid.nunique()
    maker = (f.lastliquidityind == 'AddedLiquidity').mean()
    limit = (f.ordtype == 'Limit').mean()
    n = len(f)
    return card(
        'by-hand',
        {'en': 'Every order came from the website', 'ko': '모든 주문이 웹사이트에서 나왔다'},
        {'value': f'{web.mean():.2%}', 'unit': '', 'label': {'en': 'of fills placed via www.bitmex.com', 'ko': '체결이 www.bitmex.com 주문'}},
        {'en': f'Each fill carries a text field saying where its order came from. {fmt(web.sum())} of {fmt(n)} say '
               f'"from www.bitmex.com"; the other {fmt(liq.sum())} are liquidations. Not one came through the API. '
               f'{fmt(amended.sum())} fills came from orders he dragged to a new price, and {fmt(close_btn.sum())} '
               f'from the Close button. {limit:.1%} of fills were limit orders and {maker:.1%} rested on the book '
               f'(maker). Four years, {fmt(orders)} orders, no bot.',
         'ko': f'체결마다 주문 경로가 적혀 있다. {fmt(n)}건 중 {fmt(web.sum())}건이 "www.bitmex.com"이고 나머지 '
               f'{fmt(liq.sum())}건은 강제청산이다. API 주문은 한 건도 없다. 가격을 끌어서 정정한 주문의 체결이 '
               f'{fmt(amended.sum())}건, 포지션 종료 버튼이 {fmt(close_btn.sum())}건이다. 체결의 {limit:.1%}가 '
               f'지정가, {maker:.1%}가 메이커였다. 4년, 주문 {fmt(orders)}개, 봇 없음.'},
        {'type': 'bars', 'labels': {'en': ['Website', 'Website, amended', 'Close button', 'Liquidation', 'API'],
                                    'ko': ['웹사이트', '웹사이트(정정)', '종료 버튼', '강제청산', 'API']},
         'values': [int((web & ~amended & ~close_btn).sum()), int(amended.sum()), int(close_btn.sum()),
                    int(liq.sum()), int(api.sum())], 'log': True},
        fills=n, web=int(web.sum()), liquidations=int(liq.sum()), api=int(api.sum()), orders=int(orders),
        maker=round(maker, 4), limit=round(limit, 4))


def holding_time(ctx):
    """FIFO: match each closing XBTUSD contract to the oldest open one, weight by contracts."""
    H = ctx.lots_fifo
    med = H.groupby('year').apply(lambda g: wmedian(g.hours, g.qty), include_groups=False)
    under1h = H.groupby('year').apply(lambda g: g.qty[g.hours < 1].sum() / g.qty.sum(), include_groups=False)
    years = [int(y) for y in med.index]

    def human(h):
        return f'{h * 60:.0f} min' if h < 1 else f'{h:.1f} h'

    def human_ko(h):
        return f'{h * 60:.0f}분' if h < 1 else f'{h:.1f}시간'

    a, b = med.iloc[0], med.iloc[-1]
    return card(
        'scalps-to-swings',
        {'en': 'From scalps to swings', 'ko': '스캘핑에서 스윙으로'},
        {'value': f'{b / a:.0f}x', 'unit': '', 'label': {'en': f'longer median hold, {years[0]} to {years[-1]}',
                                                          'ko': f'보유시간 증가, {years[0]}→{years[-1]}'}},
        {'en': 'Matching every closing XBTUSD contract to the oldest open one (FIFO), the contract-weighted median '
               'hold went ' + ' → '.join(f'{human(v)} ({y})' for y, v in zip(years, med)) + '. Contracts closed within '
               f'an hour fell from {under1h.iloc[0]:.0%} to {under1h.iloc[-1]:.0%}. As the account grew, he traded less '
               'often and held longer.',
         'ko': '청산된 XBTUSD 계약을 가장 오래된 진입분과 짝지으면(FIFO) 계약 가중 보유시간 중앙값이 '
               + ' → '.join(f'{human_ko(v)}({y})' for y, v in zip(years, med)) + f'로 늘었다. 1시간 안에 청산된 계약은 '
               f'{under1h.iloc[0]:.0%}에서 {under1h.iloc[-1]:.0%}로 줄었다. 계좌가 커질수록 덜 자주, 더 길게 들고 갔다.'},
        {'type': 'bars', 'labels': {'en': [str(y) for y in years], 'ko': [str(y) for y in years]},
         'values': [round(v, 2) for v in med], 'unit': 'h', 'log': True},
        median_hold_hours={str(y): round(v, 3) for y, v in zip(years, med)},
        closed_within_1h={str(y): round(v, 3) for y, v in zip(years, under1h)})


def clock(ctx):
    kst = ctx.d.start + pd.Timedelta(hours=9)
    grid = pd.crosstab(kst.dt.weekday, kst.dt.hour).reindex(index=range(7), columns=range(24), fill_value=0)
    share = kst.dt.hour.value_counts(normalize=True).sort_index()
    weekend = kst.dt.weekday.isin([5, 6]).mean()
    lo, hi = share.idxmin(), share.idxmax()
    return card(
        'clock',
        {'en': 'No quiet hours', 'ko': '쉬는 시간대가 없다'},
        {'value': f'{share.min():.1%}', 'unit': '', 'label': {'en': 'of decisions in his quietest hour (KST)',
                                                               'ko': '가장 조용한 시간대의 결정 비중 (KST)'}},
        {'en': f'Spread over Korean time, his {len(kst):,} XBTUSD decisions never stop: the quietest hour '
               f'({lo:02d}:00 KST) still holds {share.min():.1%} of them and the busiest ({hi:02d}:00) {share.max():.1%}, '
               f'against 4.2% for a flat clock. Weekends are calmer: {weekend:.1%} of decisions, against 28.6% '
               'for an even week.',
         'ko': f'XBTUSD 결정 {len(kst):,}개를 한국 시간으로 펼치면 멈추는 시간이 없다. 가장 조용한 {lo:02d}시에도 '
               f'{share.min():.1%}, 가장 바쁜 {hi:02d}시에 {share.max():.1%}다(균등하면 4.2%). 주말은 조용하다: '
               f'결정의 {weekend:.1%}(균등하면 28.6%).'},
        {'type': 'heat', 'rows': {'en': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                                  'ko': ['월', '화', '수', '목', '금', '토', '일']},
         'cols': [f'{h:02d}' for h in range(24)], 'values': grid.to_numpy().tolist()},
        quietest_hour_kst=int(lo), busiest_hour_kst=int(hi), weekend_share=round(weekend, 4))


def order_craft(ctx):
    f = ctx.f
    y = f.ts.dt.year
    maker = (f.lastliquidityind == 'AddedLiquidity').groupby(y).mean()
    post = f.execinst.astype(str).str.contains('ParticipateDoNotInitiate').groupby(y).mean()
    o = f.groupby('orderid').agg(n=('lastqty', 'size'), y=('ts', 'first'), usd=('foreignnotional', lambda s: s.abs().sum()))
    o['y'] = o.y.dt.year
    per = o.groupby('y').n.median()
    usd = o.groupby('y').usd.median()
    years = [str(v) for v in maker.index]
    return card(
        'order-craft',
        {'en': 'Bigger orders, resting longer', 'ko': '주문은 커지고, 호가에 더 오래 걸렸다'},
        {'value': f'{maker.iloc[-1]:.0%}', 'unit': '', 'label': {'en': f'of fills were maker fills in {years[-1]}',
                                                                  'ko': f'{years[-1]}년 체결 중 메이커 비중'}},
        {'en': 'Maker fills (orders resting on the book) by year: ' + ', '.join(f'{v:.0%} ({k})' for k, v in zip(years, maker))
               + '. The median order grew from ' + ' → '.join(f'${v / 1e6:,.2f}M' for v in usd) + ' and was filled in '
               + ' → '.join(f'{v:.0f}' for v in per) + ' pieces. In 2021 he rarely needed the post-only flag '
               f'({post.iloc[-1]:.1%} of fills, down from {post.iloc[0]:.0%}), yet most of his volume still waited on the book.',
         'ko': '연도별 메이커 체결(호가에 걸어둔 주문) 비중: ' + ', '.join(f'{v:.0%}({k})' for k, v in zip(years, maker))
               + '. 주문 크기 중앙값은 ' + ' → '.join(f'${v / 1e6:,.2f}M' for v in usd) + '로 커졌고, 한 주문이 '
               + ' → '.join(f'{v:.0f}' for v in per) + f'조각으로 나뉘어 체결됐다. 2021년에는 포스트온리 옵션을 거의 쓰지 않았지만'
               f'(체결의 {post.iloc[-1]:.1%}, 2018년 {post.iloc[0]:.0%}) 물량 대부분은 여전히 호가에서 기다렸다.'},
        {'type': 'bars', 'labels': {'en': years, 'ko': years}, 'values': [round(v * 100, 1) for v in maker], 'unit': '%'},
        maker_by_year={k: round(v, 4) for k, v in zip(years, maker)}, postonly_by_year={k: round(v, 4) for k, v in zip(years, post)},
        fills_per_order={k: float(v) for k, v in zip(years, per)}, order_usd={k: round(v) for k, v in zip(years, usd)})
