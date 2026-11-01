"""Read the released CSVs once and keep typed parquet copies for every later step."""
import pandas as pd

from .fetch import EXPECTED
from .paths import CACHE, RAW

FILL_COLS = {
    'timestamp': str, 'symbol': 'category', 'side': 'category', 'lastqty': 'float64', 'lastpx': 'float64',
    'lastliquidityind': 'category', 'exectype': 'category', 'ordtype': 'category', 'execinst': 'category',
    'timeinforce': 'category', 'text': 'category', 'trdmatchid': str, 'orderid': str, 'orderqty': 'float64',
    'price': 'float64', 'displayqty': 'float64', 'stoppx': 'float64', 'ordstatus': 'category',
    'execcomm': 'float64', 'execcost': 'float64', 'homenotional': 'float64', 'foreignnotional': 'float64',
}


def executions():
    """Every execution row (trades, funding, settlement), sorted by time."""
    path = CACHE / 'executions.parquet'
    if path.exists():
        return pd.read_parquet(path)
    parts = [pd.read_csv(RAW / name, usecols=list(FILL_COLS), dtype=FILL_COLS, encoding='utf-8-sig')
             for name in EXPECTED if 'execution' in name]
    x = pd.concat(parts, ignore_index=True)
    for c in ('symbol', 'side', 'lastliquidityind', 'exectype', 'ordtype', 'execinst', 'timeinforce', 'text',
              'ordstatus'):
        x[c] = x[c].astype(str).replace('nan', '').astype('category')
    x['ts'] = pd.to_datetime(x.pop('timestamp'))
    x = x.sort_values('ts', kind='stable').reset_index(drop=True)
    x.to_parquet(path)
    return x


def fills():
    """Trade executions only."""
    x = executions()
    return x[x.exectype == 'Trade'].reset_index(drop=True)


def wallet():
    """Deposits, withdrawals and daily realised PnL. Amounts converted from satoshi to BTC.

    The released wallet file was saved through Excel: its time columns lost their date part and
    `walletbalance` went to scientific notation, so the running balance is rebuilt from `amount`.
    Canceled withdrawals are listed too and must be skipped, or the balance drifts 17.99 BTC low.
    """
    w = pd.read_csv(RAW / EXPECTED[-1], dtype=str, encoding='utf-8-sig')
    w = w.dropna(subset=['transacttype'])  # 2,135 blank rows left by Excel
    w = w[w.transactstatus == 'Completed'].reset_index(drop=True)  # 7 withdrawals (17.99 BTC) were canceled
    w['btc'] = pd.to_numeric(w.amount) / 1e8
    w['day'] = pd.to_datetime(w.date)
    w['balance'] = w.btc.cumsum()
    return w[['day', 'transacttype', 'address', 'btc', 'balance']].rename(columns={'address': 'symbol'})
