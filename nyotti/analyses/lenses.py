"""Read Jev's answers back as findings. Probabilities above 0.5 count as yes; 0.3-0.7 is shown as unsure."""
import pandas as pd

from . import card
from ..judge import CHECKS, load_lenses


def merged(ctx):
    if ctx.j is None:
        return None
    return ctx.d.merge(ctx.j, on='id')


def calibration(ctx):
    m = merged(ctx)
    if m is None:
        return None
    rows = []
    for lens in load_lenses():
        if lens.get('check') and lens['key'] in m:
            truth = CHECKS[lens['check']](m)
            p = m[lens['key']]
            rows.append((lens, ((p > 0.5) == truth).mean(), ((p > 0.3) & (p < 0.7)).mean(), len(m)))
    if not rows:
        return None
    worst = min(r[1] for r in rows)
    return card(
        'jev-check',
        {'en': 'Can Jev read a trade?', 'ko': 'Jev는 매매를 제대로 읽나?'},
        {'value': f'{worst:.1%}', 'unit': '', 'label': {'en': 'lowest agreement with code on checkable questions',
                                                        'ko': '정답을 아는 질문에서 코드와의 최저 일치율'}},
        {'en': 'Two of the eight questions have answers code can compute, so they test whether Jev reads the description '
               'correctly before we trust it on the others. ' + ' '.join(
                   f'"{l["label"]}": {a:.1%} agreement over {n:,} decisions, {u:.1%} answered between 0.3 and 0.7.'
                   for l, a, u, n in rows) + ' The unsure answers cluster where the market was nearly flat, which is where '
               'the question itself is borderline.',
         'ko': '8개 질문 중 2개는 코드로 정답을 계산할 수 있다. 나머지 판단을 믿기 전에 Jev가 묘사를 제대로 읽는지 확인하는 '
               '장치다. ' + ' '.join(f'"{l["label_ko"]}": 결정 {n:,}개 중 {a:.1%} 일치, 0.3~0.7 사이 답 {u:.1%}.'
                                   for l, a, u, n in rows) + ' 애매한 답은 시장이 거의 보합이던 경계 사례에 몰려 있다.'},
        None, checks={r[0]['key']: {'agree': round(r[1], 4), 'unsure': round(r[2], 4), 'n': r[3]} for r in rows})


def panic(ctx):
    m = merged(ctx)
    if m is None or 'panic' not in m:
        return None
    p = m[m.panic > 0.5]
    e = m[m.euphoria > 0.5] if 'euphoria' in m else m.iloc[0:0]
    buy_p, buy_all, buy_e = (p.side == 'Buy').mean(), (m.side == 'Buy').mean(), (e.side == 'Buy').mean()
    grow_p = p.kind.isin(['open', 'add', 'flip']).mean()
    knife = (m.knife > 0.5).mean() if 'knife' in m else float('nan')
    days = p.start.dt.date.nunique()
    return card(
        'into-the-panic',
        {'en': 'What he did in a panic', 'ko': '패닉장에서 한 일'},
        {'value': f'{buy_p:.0%}', 'unit': '', 'label': {'en': 'of his panic-selling decisions were buys',
                                                        'ko': '패닉 매도장에서 내린 결정 중 매수'}},
        {'en': f'Jev marked {len(p):,} of his decisions, on {days} different days, as made during panic selling (a sharp '
               f'fall on unusually heavy volume). {buy_p:.0%} of them were buys, against {buy_all:.0%} of all his decisions, '
               f'and {grow_p:.0%} opened or grew a position. In a buying frenzy ({len(e):,} decisions) he bought '
               f'{buy_e:.0%} of the time. Jev marked {knife:.1%} of all his decisions as buying into a fall still under way.',
         'ko': f'Jev는 그의 결정 {len(p):,}개({days}일)를 패닉 매도장(거래량이 크게 실린 급락) 속 결정으로 봤다. 그중 '
               f'{buy_p:.0%}가 매수였다(전체 결정의 매수 비중은 {buy_all:.0%}). {grow_p:.0%}는 포지션을 열거나 키웠다. '
               f'급등 과열장의 결정 {len(e):,}개에서는 {buy_e:.0%}가 매수였다. 진행 중인 하락에 매수한 '
               f'"떨어지는 칼날 받기"로 본 결정은 전체의 {knife:.1%}다.'},
        {'type': 'bars', 'labels': {'en': ['Panic selling', 'All decisions', 'Buying frenzy'],
                                    'ko': ['패닉 매도장', '전체 결정', '급등 과열장']},
         'values': [round(buy_p * 100, 1), round(buy_all * 100, 1), round(buy_e * 100, 1)], 'unit': '%'},
        panic_decisions=len(p), panic_days=days, buy_share_panic=round(buy_p, 4), buy_share_all=round(buy_all, 4),
        euphoria_decisions=len(e), buy_share_euphoria=round(buy_e, 4), knife_share=round(knife, 4))


def tilt(ctx):
    """The revenge-trading check: after a painful stretch, did his trades get bolder?"""
    m = merged(ctx)
    if m is None or 'after_pain' not in m:
        return None
    pain = m.after_pain > 0.5
    b_pain, b_calm = m.boldness[pain].mean(), m.boldness[~pain].mean()
    g_pain = m.kind[pain].isin(['open', 'add', 'flip']).mean()
    g_calm = m.kind[~pain].isin(['open', 'add', 'flip']).mean()
    s_pain, s_calm = m.size_rel[pain].median(), m.size_rel[~pain].median()
    return card(
        'tilt-check',
        {'en': 'The tilt check', 'ko': '복수 매매 검사'},
        {'value': f'{b_pain:.2f} vs {b_calm:.2f}', 'unit': '', 'label': {'en': 'boldness after pain vs otherwise (0-4)',
                                                                          'ko': '손실 직후 vs 평소 과감함 (0~4)'}},
        {'en': f'Jev marked {pain.mean():.0%} of his decisions as made right after his equity took a hit. Revenge trading '
               'would show up as bigger, bolder trades there. Jev\'s boldness score averaged '
               f'{b_pain:.2f} after pain and {b_calm:.2f} otherwise. The median trade was {s_pain:.2f}x his yearly typical '
               f'size after pain and {s_calm:.2f}x otherwise; {g_pain:.0%} vs {g_calm:.0%} of decisions opened or grew '
               'a position.',
         'ko': f'Jev는 그의 결정 중 {pain.mean():.0%}를 자산이 타격을 입은 직후의 결정으로 봤다. 복수 매매라면 여기서 거래가 '
               f'커지고 과감해져야 한다. Jev의 과감함 점수 평균은 손실 직후 {b_pain:.2f}, 평소 {b_calm:.2f}였다. 거래 크기 '
               f'중앙값은 그해 평소의 {s_pain:.2f}배와 {s_calm:.2f}배, 포지션을 열거나 키운 비중은 {g_pain:.0%}와 '
               f'{g_calm:.0%}다.'},
        {'type': 'bars', 'labels': {'en': ['After pain', 'Otherwise'], 'ko': ['손실 직후', '평소']},
         'values': [round(b_pain, 3), round(b_calm, 3)], 'unit': ''},
        pain_share=round(pain.mean(), 4), boldness_pain=round(b_pain, 3), boldness_calm=round(b_calm, 3),
        size_pain=round(s_pain, 3), size_calm=round(s_calm, 3), grow_pain=round(g_pain, 4), grow_calm=round(g_calm, 4))


def against_vs_chance(d):
    """Share of decisions against the 24h move (code definition), and what the same buy share would give
    if each decision's side had been picked at random: P(buy)·P(fall) + P(sell)·P(rise)."""
    against = CHECKS['against_move'](d).mean()
    buy = (d.side == 'Buy').mean()
    chance = buy * (d.r24h < -0.01).mean() + (1 - buy) * (d.r24h > 0.01).mean()
    return against, chance


def regimes(ctx):
    m = merged(ctx)
    if m is None or 'regime' not in m:
        return None
    order = ['uptrend', 'range', 'downtrend', 'selloff', 'squeeze']
    ko = {'uptrend': '상승 추세', 'range': '횡보', 'downtrend': '하락 추세', 'selloff': '급락', 'squeeze': '급등'}
    share = m.regime.value_counts(normalize=True).reindex(order).fillna(0)
    buys = m.groupby('regime').side.apply(lambda s: (s == 'Buy').mean()).reindex(order)
    by = {int(y): against_vs_chance(g) for y, g in m.groupby(m.start.dt.year)}
    years = [str(y) for y in by]
    act, base = [by[int(y)][0] for y in years], [by[int(y)][1] for y in years]
    lean = [y for y, a, b in zip(years, act, base) if a - b > 0.02]
    last = years[-1]
    title_en = f'Against the 24h move? Only in {", ".join(lean)}' if lean else 'Against the 24h move? No more than chance'
    title_ko = f'24시간 흐름 역행은 {", ".join(lean)}년에만' if lean else '24시간 흐름 역행은 우연 수준'
    return card(
        'regimes',
        {'en': title_en, 'ko': title_ko},
        {'value': f'{act[-1]:.0%} vs {base[-1]:.0%}', 'unit': '',
         'label': {'en': f'of {last} decisions went against the 24h move, vs random sides',
                   'ko': f'{last}년 결정 중 24시간 흐름 역행 비중 vs 방향을 무작위로 골랐을 때'}},
        {'en': 'Jev sorted the market at each decision into five regimes: ' + ', '.join(
            f'{r} {share[r]:.0%} (buys {buys[r]:.0%})' for r in order) + '. He bought about as often as he sold in every regime. '
               'Going against the last 24 hours (buying after a fall of more than 1%, selling after a rise of more than 1%) '
               'happened in ' + ', '.join(f'{a:.0%} ({y})' for y, a in zip(years, act)) + ' of decisions. Had he picked buy or '
               'sell at random, keeping the same buy share, the expected rates would be '
               + ', '.join(f'{b:.0%}' for b in base) + '.' + (f' Only in {", ".join(lean)} did he lean against the move.'
                                                             if lean else ' He never leaned against the move.'),
         'ko': 'Jev가 결정 시점의 시장을 다섯 국면으로 나눴다: ' + ', '.join(
             f'{ko[r]} {share[r]:.0%}(매수 {buys[r]:.0%})' for r in order) + '. 어느 국면에서나 사고파는 비율이 비슷했다. '
               '24시간 흐름을 거스른 결정(1% 넘게 내린 뒤 매수, 1% 넘게 오른 뒤 매도)의 비중은 '
               + ', '.join(f'{a:.0%}({y})' for y, a in zip(years, act)) + '였다. 매수 비중은 그대로 두고 방향만 무작위로 골랐다면 '
               + ', '.join(f'{b:.0%}' for b in base) + '가 나온다.' + (f' 흐름을 거스르는 쪽으로 기운 해는 {", ".join(lean)}년뿐이다.'
                                                                  if lean else ' 흐름을 거스르는 쪽으로 기운 해는 없다.')},
        {'type': 'pair', 'labels': {'en': ['Against the 24h move', 'If sides were random'], 'ko': ['24시간 흐름 역행', '방향이 무작위였다면']},
         'years': years, 'values': [[round(v, 3) for v in act], [round(v, 3) for v in base]], 'unit': '%'},
        regime_share={r: round(share[r], 4) for r in order}, buy_share={r: round(buys[r], 4) for r in order},
        against_by_year={y: round(v, 4) for y, v in zip(years, act)}, chance_by_year={y: round(v, 4) for y, v in zip(years, base)},
        against_jev=round(float((m.against_move > 0.5).mean()), 4))
