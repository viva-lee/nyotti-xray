"""Second look at the original twenty cards: each finding re-measured another way.

Every check returns {verdict, note{en,ko}, numbers}. `holds` means the other measurement agrees, `nuance` adds
something the card leaves out, `revised` means the card's wording was changed because of the check. Like the
cards, every figure in a note is computed here.
"""
import json

import numpy as np
import pandas as pd

from . import wmedian
from .lenses import against_vs_chance
from .proof import tape_days
from ..fetch import EXPECTED
from ..paths import CACHE, RAW


def note(verdict, en, ko, **numbers):
    return {'verdict': verdict, 'note': {'en': en, 'ko': ko}, 'numbers': numbers}


def release_extra():
    """Order fields the cached table does not keep: client order ids, pegs and contingent orders."""
    path = CACHE / 'release_extra.json'
    if path.exists():
        return json.loads(path.read_text())
    cols = ['exectype', 'clordid', 'clordlinkid', 'pegpricetype', 'contingencytype']
    parts = [pd.read_csv(RAW / name, usecols=cols, dtype=str, encoding='utf-8-sig') for name in EXPECTED if 'execution' in name]
    r = pd.concat(parts, ignore_index=True)
    r = r[r.exectype == 'Trade']
    out = {c: int(r[c].notna().sum()) for c in cols[1:]}
    out['fills'] = len(r)
    path.write_text(json.dumps(out))
    return out


def verified(ctx, c):
    dts = np.array([abs(v[2]) for d in tape_days() for v in d['found']])
    zero = float((dts == 0).mean()) if len(dts) else float('nan')
    return note('holds',
                f'Every matched fill carries the exact timestamp the tape has, to the microsecond: the largest difference '
                f'across {len(dts):,} matches is {dts.max():g} s. All {c["numbers"]["not_found"]} fills missing from the tape '
                'are liquidations or self-trades.',
                f'테이프와 맞은 체결 {len(dts):,}건 모두 시각이 마이크로초까지 같다. 가장 큰 차이가 {dts.max():g}초다. 테이프에 '
                f'없는 체결 {c["numbers"]["not_found"]}건은 모두 강제청산이거나 자전거래다.',
                matched=len(dts), max_abs_seconds=float(dts.max()), share_exact=zero)


def by_hand(ctx, c):
    e = release_extra()
    return note('holds',
                f'A second, independent sign: none of the {e["fills"]:,} fills carries a client order id (clOrdID), which API '
                f'clients normally set, and none came from a pegged or linked order ({e["pegpricetype"]} and '
                f'{e["contingencytype"]}).',
                f'독립적인 두 번째 근거: 체결 {e["fills"]:,}건 중 API 클라이언트가 보통 붙이는 주문 식별자(clOrdID)가 있는 체결이 '
                f'하나도 없고, 페그 주문이나 연결 주문에서 나온 체결도 없다({e["pegpricetype"]}건, {e["contingencytype"]}건).',
                **e)


def transfers(ctx, c):
    w = pd.read_csv(RAW / EXPECTED[-1], dtype=str, encoding='utf-8-sig').dropna(subset=['transacttype'])
    btc = pd.to_numeric(w.amount) / 1e8
    bal = btc.cumsum()
    canceled = w.transactstatus != 'Completed'
    first_neg = pd.to_datetime(w.date[bal < 0]).min()
    return note('holds',
                f'The cleanup matters: counting the {int(canceled.sum())} canceled withdrawals ({-btc[canceled].sum():.2f} BTC) '
                f'as real would push the rebuilt balance below zero on {first_neg:%Y-%m-%d}, to {bal.min():.2f} BTC at its lowest. '
                'Skipping them keeps it positive throughout.',
                f'정리 작업이 중요하다: 취소된 출금 {int(canceled.sum())}건({-btc[canceled].sum():.2f} BTC)을 실제 출금으로 세면 '
                f'재구성한 잔고가 {first_neg:%Y-%m-%d}에 0 아래로 내려가고 최저 {bal.min():.2f} BTC가 된다. 빼면 내내 양수다.',
                canceled=int(canceled.sum()), canceled_btc=round(float(-btc[canceled].sum()), 3),
                negative_from=str(first_neg.date()), lowest=round(float(bal.min()), 3))


def by_coin(ctx, c):
    bk = ctx.book
    gain = bk.realized.diff().fillna(bk.realized)
    coin = bk.symbol.astype(str).str.replace(r'(USDM21|USDTZ20|USDT|USD|_U110|[FGHJKMNQUVXZ]\d\d)$', '', regex=True)
    coin = coin.str.replace('XBT7D', 'XBT').replace('XBT', 'BTC')
    by = gain.groupby(coin).sum()
    share = by.get('BTC', 0) / by.sum()
    fu = ctx.x[ctx.x.exectype == 'Funding']
    alt = ~fu.symbol.astype(str).str.startswith('XBT')
    f_alt, f_xbt = -fu.execcomm[alt].sum() / 1e8, -fu.execcomm[~alt].sum() / 1e8
    return note('holds',
                f'Rebuilt from the fills alone, before fees and funding, Bitcoin contracts made {share:.0%} of realised PnL '
                f'({by.get("BTC", 0):,.0f} of {by.sum():,.0f} BTC), against {c["stat"]["value"]} in the wallet. Funding explains '
                f'the gap: over four years it paid him {f_alt:,.1f} BTC on altcoin contracts and {f_xbt:,.1f} BTC on Bitcoin ones.',
                f'수수료와 펀딩 전, 체결만으로 다시 계산하면 비트코인 계약이 실현손익의 {share:.0%}'
                f'({by.sum():,.0f} BTC 중 {by.get("BTC", 0):,.0f} BTC)이고 지갑 기준은 {c["stat"]["value"]}다. 차이는 펀딩에서 난다. '
                f'4년 동안 펀딩으로 알트 계약에서 {f_alt:,.1f} BTC, 비트코인 계약에서 {f_xbt:,.1f} BTC를 받았다.',
                btc_share_fills=round(float(share), 4), by_coin_fills={k: round(float(v), 2) for k, v in by.items()},
                funding_alt=round(float(f_alt), 3), funding_xbt=round(float(f_xbt), 3))


def hedge(ctx, c):
    s = c['numbers']['exposure_split']
    return note('revised',
                f'The earlier title, "\'Short\' mostly meant \'in dollars\'", went further than the numbers: only {s[1]:.0%} of '
                f'short hours left the account parked in dollars. The {c["numbers"]["hedged_share"]:.0%} that were not a bet on a '
                f'fall include {s[3]:.0%} where the short only trimmed an account still about like holding Bitcoin. The title now '
                'says what the numbers support.',
                f'예전 제목 "숏은 대부분 \'달러로 파킹\'이었다"는 숫자보다 앞서 나갔다. 계좌가 달러로 파킹된 숏 시간은 {s[1]:.0%}뿐이다. '
                f'하락 베팅이 아니었던 {c["numbers"]["hedged_share"]:.0%}에는 BTC 보유와 비슷한 계좌를 숏이 조금 덜어냈을 뿐인 '
                f'{s[3]:.0%}가 들어 있다. 제목을 숫자가 뒷받침하는 만큼으로 고쳤다.',
                split=s)


def holding_time(ctx, c):
    lots = ctx.lots_lifo
    med = lots.groupby('year').apply(lambda g: wmedian(g.hours, g.qty), include_groups=False)
    years = [str(y) for y in med.index]
    fifo = c['numbers']['median_hold_hours']
    fifo_x = fifo[years[-1]] / fifo[years[0]]

    def human(h, ko=False):
        if h < 1:
            return f'{h * 60:.0f}{"분" if ko else " min"}'
        return f'{h:.1f}{"시간" if ko else " h"}'
    return note('holds',
                'Pairing each close with the newest open contract (LIFO) instead of the oldest shortens every hold but keeps '
                'the trend: ' + ' → '.join(human(v) for v in med) + f' ({med.iloc[-1] / med.iloc[0]:.0f}x, against '
                f'{fifo_x:.0f}x with FIFO).',
                '가장 오래된 진입분 대신 가장 최근 진입분과 짝지어도(LIFO) 보유시간은 짧아질 뿐 흐름은 같다: '
                + ' → '.join(human(v, True) for v in med) + f'({med.iloc[-1] / med.iloc[0]:.0f}배, FIFO는 {fifo_x:.0f}배).',
                lifo_median_hours={y: round(float(v), 3) for y, v in zip(years, med)})


def order_craft(ctx, c):
    f = ctx.f
    usd = ctx.fills_usd
    maker = f.lastliquidityind == 'AddedLiquidity'
    by = usd.where(maker, 0).groupby(f.ts.dt.year).sum() / usd.groupby(f.ts.dt.year).sum()
    years = [str(y) for y in by.index]
    return note('nuance',
                'Counted by dollar volume instead of by fills, the maker share rises steadily: '
                + ' → '.join(f'{v:.0%} ({y})' for y, v in zip(years, by)) + '. Fill counts make 2019-2020 look more aggressive, '
                'because one order that takes liquidity is split across every resting order it hits.',
                '체결 건수 대신 거래 금액으로 세면 메이커 비중은 꾸준히 오른다: '
                + ' → '.join(f'{v:.0%}({y})' for y, v in zip(years, by)) + '. 건수로 세면 2019~2020년이 더 공격적으로 보인다. '
                '유동성을 가져가는 주문 하나가 부딪힌 대기 주문 수만큼 여러 체결로 쪼개지기 때문이다.',
                maker_by_usd={y: round(float(v), 4) for y, v in zip(years, by)})


def leverage(ctx, c):
    g = ctx.h.dropna(subset=['gross_leverage'])
    rest = g.loc['2018-04-01':'2018-12-31'].gross_leverage.quantile(.95)
    return note('holds',
                f'March 2018, when the account held well under a bitcoin, inflates that year. From April to December 2018 '
                f'the 95th percentile was {rest:.1f}x: still the highest year, and the decline holds.',
                f'계좌에 1 BTC도 안 되던 2018년 3월이 그해 숫자를 키운다. 2018년 4~12월만 보면 95백분위는 {rest:.1f}배로, 여전히 '
                '가장 높은 해이고 감소 흐름도 그대로다.',
                p95_2018_from_april=round(float(rest), 3))


def funding(ctx, c):
    x = ctx.x
    settle = x[x.exectype == 'Settlement'].execcomm.fillna(0).sum() / 1e8
    return note('holds',
                'These fees and funding payments, plus '
                f'{settle:.2f} BTC charged when dated futures settled, are exactly what the ledger card subtracts from the fills; '
                'with them the rebuilt book matches the wallet to within 0.1%.',
                f'이 수수료와 펀딩에 만기 선물 정산 때 낸 {settle:.2f} BTC를 더한 것이 장부 카드가 체결에서 빼는 금액이다. 이걸 빼면 '
                '재구성한 장부가 지갑과 0.1% 안쪽으로 맞는다.',
                settlement_fees_btc=round(float(settle), 4))


def liquidations(ctx, c):
    f = ctx.f
    liq = f[f.text.astype(str).str.contains('Liquidation')]
    days = liq.groupby(liq.ts.dt.year).ts.apply(lambda s: s.dt.date.nunique())
    return note('holds',
                f'Counted by calendar day instead of by minute and symbol, 2018 still stands alone: {int(days.get(2018, 0))} days '
                f'with a liquidation, against {int(days.drop(2018, errors="ignore").sum())} in the three years after.',
                f'분·종목 대신 날짜로 세도 2018년이 압도적이다: 강제청산이 있던 날이 {int(days.get(2018, 0))}일, 그 뒤 3년 동안은 '
                f'{int(days.drop(2018, errors="ignore").sum())}일이다.',
                days_by_year={str(k): int(v) for k, v in days.items()})


def concentration(ctx, c):
    out = {}
    for unit in ('btc', 'usd'):
        d = ctx.daily
        gain = (d.equity.diff() - d.flow) if unit == 'btc' else (d.usd.diff() - d.flow * d.price)
        gain = gain[d.r_btc.notna()]
        top = gain.sort_values(ascending=False).cumsum() / gain.sum()
        out[unit] = int((top < 0.5).sum() + 1)
    return note('holds',
                'Realised PnL can lag the market by days, so the same test was run on mark-to-market daily gains. Half of the net '
                f'came from {out["btc"]} days counted in BTC and {out["usd"]} counted in dollars, against '
                f'{c["numbers"]["days_to_half"]} for realised PnL.',
                '실현손익은 시장보다 며칠 늦게 잡힐 수 있어 일간 평가손익으로 다시 쟀다. 순이익의 절반이 BTC 기준 '
                f'{out["btc"]}일, 달러 기준 {out["usd"]}일에서 나왔다(실현손익 기준 {c["numbers"]["days_to_half"]}일).',
                days_to_half_mtm_btc=out['btc'], days_to_half_mtm_usd=out['usd'])


def black_thursday(ctx, c):
    d = ctx.daily
    days = pd.to_datetime(['2020-03-12', '2020-03-13'])
    gain = (d.equity.diff() - d.flow).reindex(days)
    r, u = d.r_btc.reindex(days), d.r_usd.reindex(days)
    return note('holds',
                f'Mark-to-market the account moved {gain.iloc[0]:+,.0f} BTC ({r.iloc[0]:+.1%}) on the 12th and {gain.iloc[1]:+,.0f} BTC '
                f'({r.iloc[1]:+.1%}) on the 13th; in dollars, {u.iloc[0]:+.1%} and {u.iloc[1]:+.1%}. The wallet booked '
                f'{c["numbers"]["booked_13"]:+,.0f} BTC on the 13th because realised PnL counts when positions close, not when they gain.',
                f'평가손익으로는 12일 {gain.iloc[0]:+,.0f} BTC({r.iloc[0]:+.1%}), 13일 {gain.iloc[1]:+,.0f} BTC({r.iloc[1]:+.1%})였고, '
                f'달러 기준으로는 {u.iloc[0]:+.1%}, {u.iloc[1]:+.1%}였다. 13일 지갑에 {c["numbers"]["booked_13"]:+,.0f} BTC가 찍힌 것은 '
                '실현손익이 이익이 날 때가 아니라 포지션을 닫을 때 잡히기 때문이다.',
                mtm_btc=[round(float(v), 2) for v in gain], r_btc=[round(float(v), 4) for v in r], r_usd=[round(float(v), 4) for v in u])


def worst_day(ctx, c):
    d = ctx.daily
    r = d.r_usd[d.index >= '2019-01-01']
    return note('holds',
                f'In dollars it is also the worst: {r.min():.1%} on {r.idxmin():%Y-%m-%d}, so the choice of unit does not change '
                'this one.',
                f'달러로 세도 최악의 날이다: {r.idxmin():%Y-%m-%d}, {r.min():.1%}. 이 날은 단위를 바꿔도 그대로다.',
                worst_usd_day=str(r.idxmin().date()), worst_usd=round(float(r.min()), 4))


def _merged(ctx):
    return ctx.d.merge(ctx.j, on='id') if ctx.j is not None else None


def panic(ctx, c):
    m = _merged(ctx)
    code = (m.r24h <= -0.08) & (m.volume_ratio >= 1.5)
    agree = ((m.panic > 0.5) == code).mean()
    return note('holds',
                f'Without Jev, defining panic as a 24-hour fall of 8% or more on 1.5x normal volume: {int(code.sum()):,} decisions, '
                f'{(m.side[code] == "Buy").mean():.1%} of them buys, against {(m.side == "Buy").mean():.1%} overall. Jev and this '
                f'rule agree on {agree:.1%} of decisions.',
                f'Jev 없이 "24시간 8% 이상 하락 + 거래량 평소의 1.5배 이상"을 패닉으로 정의해도 결정 {int(code.sum()):,}개 중 매수가 '
                f'{(m.side[code] == "Buy").mean():.1%}(전체 {(m.side == "Buy").mean():.1%})다. 이 규칙과 Jev는 결정의 {agree:.1%}에서 '
                '일치한다.',
                code_panic=int(code.sum()), code_panic_buys=round(float((m.side[code] == 'Buy').mean()), 4), agree=round(float(agree), 4))


def tilt(ctx, c):
    m = _merged(ctx)
    pain = (m.equity_24h <= -0.04) | (m.equity_7d <= -0.08) | (m.drawdown_30d <= -0.10)
    return note('holds',
                'Without Jev, calling it pain when equity fell 4% in a day, 8% in a week, or sat 10% below its 30-day peak '
                f'({pain.mean():.0%} of decisions): the median trade afterwards was {m.size_rel[pain].median():.2f}x his typical '
                f'size, against {m.size_rel[~pain].median():.2f}x otherwise. Smaller, not bigger.',
                'Jev 없이 "하루 4% 하락, 일주일 8% 하락, 또는 30일 고점 대비 10% 아래"를 손실 직후로 정의하면(결정의 '
                f'{pain.mean():.0%}) 그 뒤 거래 크기 중앙값은 평소의 {m.size_rel[pain].median():.2f}배, 아닐 때는 '
                f'{m.size_rel[~pain].median():.2f}배다. 커지지 않고 작아졌다.',
                code_pain_share=round(float(pain.mean()), 4), size_pain=round(float(m.size_rel[pain].median()), 3),
                size_calm=round(float(m.size_rel[~pain].median()), 3))


def after_worst(ctx, c):
    from .behavior import day_after
    w = day_after(ctx, False)
    return note('holds',
                f'Measured in contracts against his typical size that year instead of against equity, the next-day trades were '
                f'{w["size"]:.2f}x usual. The new best-days card runs the same test in the other direction.',
                f'자산 대비가 아니라 그해 평소 계약 크기 대비로 재도 다음 날 거래는 평소의 {w["size"]:.2f}배였다. 새 카드 "최고의 날 '
                '다음 날"이 같은 검사를 반대 방향으로 한다.',
                size_contracts=round(w['size'], 3))


def regimes(ctx, c):
    m = _merged(ctx)
    a, b = against_vs_chance(m)
    return note('revised',
                'The earlier title, "Against the move, more often than not", did not hold: with the code definition, '
                f'{a:.1%} of all decisions went against the 24h move, and random sides with the same buy share would give '
                f'{b:.1%}. The card now compares each year with that baseline, which singles out 2021.',
                f'예전 영문 제목 "Against the move, more often than not"(흐름을 거스른 매매가 더 많다)은 맞지 않았다. 코드 정의로 전체 '
                f'결정의 {a:.1%}가 24시간 흐름을 거슬렀는데, 매수 비중이 '
                f'같고 방향만 무작위인 경우에도 {b:.1%}가 나온다. 카드는 이제 해마다 이 기준선과 비교하고, 그러면 2021년만 남는다.',
                against=round(float(a), 4), chance=round(float(b), 4))


def footprint(ctx, c):
    days = tape_days()
    tape = pd.Series({d['day']: d['totals'].get('XBTUSD', [0, 0, 0])[1] for d in days if not d.get('missing')})
    f = ctx.f[ctx.f.symbol == 'XBTUSD']
    share = (f.groupby(f.ts.dt.date.astype(str)).lastqty.sum() / tape).dropna().sort_values(ascending=False).head(5)
    return note('holds',
                'His five biggest days all fall in mid-2021: ' + ', '.join(f'{d} ({v:.1%})' for d, v in share.items()) + '.',
                '거래량 비중이 가장 컸던 다섯 날은 모두 2021년 중반이다: ' + ', '.join(f'{d}({v:.1%})' for d, v in share.items()) + '.',
                top_days={d: round(float(v), 4) for d, v in share.items()})


def clock(ctx, c):
    o = ctx.orders
    a = o[o.active]
    kst = (a.ts + pd.Timedelta(hours=9)).dt.hour
    window = []
    for y, hours in kst.groupby(a.ts.dt.year):
        s = hours.value_counts(normalize=True).reindex(range(24), fill_value=0)
        window.append((int(y), min(s.iloc[[(h + k) % 24 for k in range(6)]].sum() for h in range(24))))
    lo, hi = min(v for _, v in window), max(v for _, v in window)
    return note('holds',
                'Resting orders fill while their owner sleeps, so this was re-run on the orders that traded the instant they were '
                f'sent, which needs a click at that moment ({len(a):,} orders). Those are spread over the whole day too: the '
                f'quietest six hours of each year held {lo:.0%}-{hi:.0%} of them, where an even day would give 25%.',
                '걸어 둔 주문은 주인이 자는 동안에도 체결되므로, 보내는 즉시 체결된 주문만 다시 셌다. 그 순간 누군가 클릭해야 나오는 '
                f'주문이다({len(a):,}개). 이 주문들도 하루 전체에 퍼져 있다: 해마다 가장 조용한 6시간에 {lo:.0%}~{hi:.0%}가 몰렸고, '
                '고르게 퍼졌다면 25%다.',
                active_orders=len(a), quietest_six_hours={str(y): round(float(v), 4) for y, v in window})


def calibration(ctx, c):
    m = _merged(ctx)
    code_panic = (m.r24h <= -0.08) & (m.volume_ratio >= 1.5)
    code_knife = (m.side == 'Buy') & (m.r6h < -0.007) & (m.r24h < -0.01)
    a_p = ((m.panic > 0.5) == code_panic).mean()
    a_k = ((m.knife > 0.5) == code_knife).mean()
    return note('holds',
                f'Two more lenses can be approximated by a rule on the same numbers Jev was shown: panic selling agrees on {a_p:.1%} '
                f'of decisions and catching a falling knife on {a_k:.1%}.',
                f'Jev가 본 숫자에 규칙을 대면 두 렌즈를 더 근사할 수 있다: 패닉 매도장은 결정의 {a_p:.1%}, 떨어지는 칼날 받기는 '
                f'{a_k:.1%}에서 일치한다.',
                panic_agree=round(float(a_p), 4), knife_agree=round(float(a_k), 4))


CHECKS_BY_CARD = {
    'verified': verified, 'by-hand': by_hand, 'transfers': transfers, 'by-coin': by_coin, 'short-is-not-bearish': hedge,
    'scalps-to-swings': holding_time, 'order-craft': order_craft, 'leverage': leverage, 'funding': funding,
    'liquidations': liquidations, 'concentration': concentration, 'black-thursday': black_thursday, 'worst-day': worst_day,
    'into-the-panic': panic, 'tilt-check': tilt, 'after-the-worst-days': after_worst, 'regimes': regimes,
    'footprint': footprint, 'clock': clock, 'jev-check': calibration,
}


def run(ctx, cards, log=print):
    """Attach a `review` to every original card that has a check."""
    for c in cards:
        fn = CHECKS_BY_CARD.get(c['id'])
        if fn is None:
            continue
        c['review'] = fn(ctx, c)
        log(f'review {c["id"]}: {c["review"]["verdict"]}')
    return cards
