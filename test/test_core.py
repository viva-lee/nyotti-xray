"""Run with: python -I -m unittest discover -s test   (from the repo root)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from nyotti import build, describe  # noqa: E402
from nyotti.analyses import btc_value, bucket, match_lots, wmedian  # noqa: E402
from nyotti.analyses.lenses import against_vs_chance  # noqa: E402
from nyotti.analyses.risk import distance  # noqa: E402
from nyotti.judge import CHECKS  # noqa: E402


def fills(rows):
    """rows: (minute, symbol, side, qty, price, execcost_sat)"""
    x = pd.DataFrame(rows, columns=['m', 'symbol', 'side', 'lastqty', 'lastpx', 'execcost'])
    x['ts'] = pd.Timestamp('2020-01-01') + pd.to_timedelta(x.m, unit='min')
    x['exectype'] = 'Trade'
    return x


class Book(unittest.TestCase):
    def test_inverse_round_trip(self):
        # Long 10,000 XBTUSD at 10,000, close at 12,500: 10000 * (1/10000 - 1/12500) = 0.2 BTC.
        bk, _ = build.book(fills([(0, 'XBTUSD', 'Buy', 10000, 10000.0, 1e8), (5, 'XBTUSD', 'Sell', 10000, 12500.0, 8e7)]))
        self.assertAlmostEqual(bk.realized.iloc[-1], 0.2, places=9)
        self.assertEqual(bk.xbt_net.iloc[-1], 0)

    def test_inverse_short_loses_when_price_rises(self):
        bk, _ = build.book(fills([(0, 'XBTUSD', 'Sell', 10000, 10000.0, 1e8), (5, 'XBTUSD', 'Buy', 10000, 12500.0, 8e7)]))
        self.assertAlmostEqual(bk.realized.iloc[-1], -0.2, places=9)

    def test_flip_realises_only_the_closed_part(self):
        bk, _ = build.book(fills([(0, 'XBTUSD', 'Buy', 100, 10000.0, 1e6), (1, 'XBTUSD', 'Sell', 300, 20000.0, 1.5e6)]))
        self.assertAlmostEqual(bk.realized.iloc[-1], 100 * (1 / 10000 - 1 / 20000), places=12)
        self.assertEqual(bk.xbt_net.iloc[-1], -200)

    def test_quanto_uses_the_multiplier(self):
        # ETHUSD: 100 satoshi per $1 per contract. Long 1,000 at 200, out at 250: 1000 * 50 * 1e-6 = 0.05 BTC.
        rows = [(0, 'ETHUSD', 'Buy', 1000, 200.0, 1000 * 200 * 100), (9, 'ETHUSD', 'Sell', 1000, 250.0, 1000 * 250 * 100)]
        bk, mult = build.book(fills(rows))
        self.assertAlmostEqual(mult['ETHUSD'], 1e-6)
        self.assertAlmostEqual(bk.realized.iloc[-1], 0.05, places=9)
        self.assertEqual(bk.xbt_net.iloc[-1], 0)  # altcoins never count as Bitcoin contracts


class State(unittest.TestCase):
    def decision(self, **kw):
        d = dict(start=pd.Timestamp('2020-03-12 13:01'), side='Buy', kind='add', pos_before=-100, pos_after=-50,
                 size_rel=1.0, maker=0.8, minutes=3, r6h=-0.06, r24h=-0.25, r7d=-0.3, r30d=-0.4, range_pos=0.02,
                 volume_ratio=2.6, volatility_ratio=3.1, equity_24h=-0.05, equity_7d=0.01, drawdown_30d=-0.07,
                 exposure_before=0.4, exposure_after=0.6, next_24h=0.5, pnl_24h_btc=9.9)
        d.update(kw)
        return pd.Series(d)

    def test_numbers_become_named_buckets(self):
        s = describe.state(self.decision())
        self.assertEqual(s['market_before']['last_24_hours'], 'Bitcoin fell sharply (-25.0%)')
        self.assertIn('very heavy', s['market_before']['volume_last_24_hours'])

    def test_no_hindsight_reaches_jev(self):
        text = str(describe.state(self.decision(next_24h=0.123456, pnl_24h_btc=98765.4321)))
        self.assertNotIn('12.3', text)
        self.assertNotIn('98765', text)
        self.assertNotIn('next', text)

    def test_trader_is_never_named(self):
        text = str(describe.state(self.decision())).lower()
        for name in ('wonyotti', 'nyotti', 'aoa', '워뇨띠'):
            self.assertNotIn(name, text)

    def test_flip_says_bigger_or_smaller(self):
        s = describe.state(self.decision(kind='flip', pos_before=100, pos_after=-300, side='Sell'))
        self.assertIn('a larger net short', s['action']['effect_on_contracts'])


class Checks(unittest.TestCase):
    def test_against_move(self):
        d = pd.DataFrame({'side': ['Buy', 'Buy', 'Sell', 'Sell'], 'r24h': [-0.05, 0.005, 0.05, -0.05]})
        self.assertEqual(CHECKS['against_move'](d).tolist(), [True, False, True, False])

    def test_chance_baseline_matches_random_sides(self):
        # Half buys; a quarter of decisions after a fall, a quarter after a rise: random sides give 0.5*0.25 + 0.5*0.25.
        d = pd.DataFrame({'side': ['Buy', 'Sell'] * 4, 'r24h': [-0.05, 0.0, 0.05, 0.0, 0.0, -0.05, 0.0, 0.05]})
        against, chance = against_vs_chance(d)
        self.assertAlmostEqual(chance, 0.25)
        self.assertAlmostEqual(against, 0.25)  # the buy after -5% and the sell after +5%


class Lots(unittest.TestCase):
    def fills(self, rows):
        return pd.DataFrame(rows, columns=['m', 'side', 'lastqty', 'lastpx']).assign(
            ts=lambda x: pd.Timestamp('2020-01-01') + pd.to_timedelta(x.m, unit='min'))

    def test_fifo_and_lifo_pair_different_lots(self):
        # Buy 1 at 100 (t0), buy 1 at 200 (t10), sell 1 at 150 (t20).
        t = self.fills([(0, 'Buy', 1, 100.0), (10, 'Buy', 1, 200.0), (20, 'Sell', 1, 150.0)])
        fifo, lifo = match_lots(t, lifo=False), match_lots(t, lifo=True)
        self.assertEqual(fifo.entry_px.tolist(), [100.0])
        self.assertEqual(lifo.entry_px.tolist(), [200.0])
        self.assertAlmostEqual(fifo.hours.iloc[0], 20 / 60)
        self.assertAlmostEqual(lifo.hours.iloc[0], 10 / 60)
        self.assertGreater(fifo.pnl.iloc[0], 0)  # long from 100, out at 150
        self.assertLess(lifo.pnl.iloc[0], 0)  # long from 200, out at 150

    def test_a_flip_closes_then_opens(self):
        t = self.fills([(0, 'Buy', 2, 100.0), (5, 'Sell', 5, 110.0), (9, 'Buy', 3, 90.0)])
        m = match_lots(t)
        self.assertEqual(m.qty.tolist(), [2.0, 3.0])
        self.assertEqual(m.dir.tolist(), [1.0, -1.0])
        self.assertAlmostEqual(m.pnl.iloc[1], 3 * (1 / 90 - 1 / 110))  # short 3 from 110, covered at 90

    def test_weighted_median(self):
        self.assertEqual(wmedian([1, 2, 3], [1, 1, 10]), 3)
        self.assertEqual(wmedian([5, 1], [1, 1]), 1)


class Account(unittest.TestCase):
    def test_distance_to_zero(self):
        frac, side = distance([2.0, 4.0, 0.5, 0.0, 1.0, -0.5, -2.0])
        self.assertAlmostEqual(frac[0], 0.5)  # 2x long: a 50% fall
        self.assertAlmostEqual(frac[1], 0.25)
        self.assertTrue(all(f == float('inf') for f in frac[2:5]))  # 0x to 1x: no move does it
        self.assertAlmostEqual(frac[5], 2.0)  # -0.5x: Bitcoin has to triple
        self.assertAlmostEqual(frac[6], 0.5)
        self.assertEqual(list(side), [1, 1, 0, 0, 0, -1, -1])

    def test_distance_matches_the_inverse_contract(self):
        # 1 BTC of equity at $10,000, net long 20,000 contracts: exposure 3x, so a fall of 1/3 should empty it.
        E, P, N = 1.0, 10000.0, 20000.0
        e = 1 + N / (P * E)
        P2 = P * (1 - distance([e])[0][0])
        self.assertAlmostEqual(E + N * (1 / P - 1 / P2), 0.0, places=9)

    def test_buckets_use_the_jev_cut_points(self):
        self.assertEqual(list(bucket([-0.25, -0.2, 0.25, 0.85, 1.15, 1.2])), [0, 1, 2, 3, 3, 4])
        self.assertEqual(describe.exposure(-0.25).split(' ')[0:3], ['a', 'net', 'short'])
        self.assertTrue(describe.exposure(1.15).startswith('about the same'))

    def test_btc_value_is_exec_cost_for_every_contract(self):
        # The two largest liquidation minutes: homeNotional is BTC for XBTUSD but XRP for XRPU18.
        f = pd.DataFrame({'symbol': ['XBTUSD', 'XRPU18'], 'execcost': [-8309386200.0, 4280760000.0],
                          'homenotional': [83.093862, -330000.0], 'foreignnotional': [-599999.0, 42.8076]})
        self.assertEqual([round(v, 6) for v in btc_value(f)], [83.093862, 42.8076])


if __name__ == '__main__':
    unittest.main()
