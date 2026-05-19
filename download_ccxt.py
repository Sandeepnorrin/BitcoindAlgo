import ccxt
import pandas as pd
import time
from datetime import datetime

def fetch_ohlcv(symbol, timeframe, since, limit=1000):
    exchange = ccxt.binance()
    all_ohlcv = []
    while since < exchange.milliseconds():
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 1
        time.sleep(exchange.rateLimit / 1000)
        print(f"Fetched until {datetime.fromtimestamp(since/1000)}")
    return all_ohlcv

symbol = 'BTC/USDT'
timeframe = '4h'
three_years_ago = int((datetime.now() - pd.Timedelta(days=3*365)).timestamp() * 1000)

ohlcv = fetch_ohlcv(symbol, timeframe, three_years_ago)
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.to_csv('btc_4h_3y.csv', index=False)
print(f"Saved {len(df)} rows to btc_4h_3y.csv")
