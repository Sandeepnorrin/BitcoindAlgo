import ccxt
import pandas as pd
import time
from datetime import datetime

def fetch_ohlcv(symbol, timeframe, since, limit=1000):
    exchange = ccxt.bitstamp()
    all_ohlcv = []
    # Fetch from 2021-05-20 to 2024-05-20
    end_time = int(datetime(2024, 5, 20).timestamp() * 1000)
    while since < end_time:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            new_since = ohlcv[-1][0] + 1
            if new_since <= since:
                break
            since = new_since
            if since >= end_time:
                break
            time.sleep(exchange.rateLimit / 1000)
            print(f"Fetched until {datetime.fromtimestamp(since/1000)}")
        except Exception as e:
            print(f"Error: {e}")
            break
    return all_ohlcv

symbol = 'BTC/USD'
timeframe = '4h'
start_date = int(datetime(2021, 5, 20).timestamp() * 1000)

ohlcv = fetch_ohlcv(symbol, timeframe, start_date)
if ohlcv:
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.to_csv('btc_4h_3y_real.csv', index=False)
    print(f"Saved {len(df)} rows to btc_4h_3y_real.csv")
