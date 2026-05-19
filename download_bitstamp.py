import ccxt
import pandas as pd
import time
from datetime import datetime

def fetch_ohlcv(symbol, timeframe, since, limit=1000):
    exchange = ccxt.bitstamp()
    all_ohlcv = []
    end_time = exchange.milliseconds()
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
            time.sleep(exchange.rateLimit / 1000)
            print(f"Fetched until {datetime.fromtimestamp(since/1000)}")
        except Exception as e:
            print(f"Error: {e}")
            break
    return all_ohlcv

symbol = 'BTC/USD'
timeframe = '4h'
three_years_ago = int((datetime.now() - pd.Timedelta(days=3*365)).timestamp() * 1000)

ohlcv = fetch_ohlcv(symbol, timeframe, three_years_ago)
if ohlcv:
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.to_csv('btc_4h_3y.csv', index=False)
    print(f"Saved {len(df)} rows to btc_4h_3y.csv")
else:
    print("No data fetched from Bitstamp")
