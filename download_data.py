import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def download_btc_data():
    symbol = "BTC-USD"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3*365)

    print(f"Downloading {symbol} data from {start_date.date()} to {end_date.date()}...")

    # Try 4h first
    data = yf.download(symbol, start=start_date, end=end_date, interval="1d")
    if data.empty:
        print("Failed to download 1d data")
        return

    data.to_csv("btc_1d_3y.csv")
    print("Downloaded 1d data")

    # Let's also try to get 1h data. yfinance usually limits 1h to 730 days.
    # We might need to download in chunks or use another source if 3 years 1h is needed.
    # But 1d is safe for 3 years.

    # Let's try 1h for the last 730 days (max for yf 1h)
    start_date_1h = end_date - timedelta(days=729)
    data_1h = yf.download(symbol, start=start_date_1h, end=end_date, interval="1h")
    if not data_1h.empty:
        data_1h.to_csv("btc_1h_2y.csv")
        print("Downloaded 1h data (2 years)")

if __name__ == "__main__":
    download_btc_data()
