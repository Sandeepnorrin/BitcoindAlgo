import streamlit as st
import pandas as pd
import numpy as np
import backtrader as bt
from strategy import BitcoinStrategy
import matplotlib.pyplot as plt

# --- Page Config ---
st.set_page_config(page_title="BTC Strategy Backtester", layout="wide")

st.title("₿ Bitcoin Trading Strategy Backtester")
st.markdown("""
This tool allows you to backtest a swing trading strategy for Bitcoin.
The strategy adapts to **Bull**, **Bear**, and **Consolidation** phases using the 50-day EMA and other technical indicators.
""")

# --- Sidebar Parameters ---
st.sidebar.header("Strategy Parameters")

ema_period = st.sidebar.number_input("EMA Period (for phase detection)", value=300, help="~50 days for 4h candles")
rsi_period = st.sidebar.number_input("RSI Period", value=14)
risk_per_trade = st.sidebar.slider("Risk Per Trade (%)", 0.1, 5.0, 2.0) / 100.0
leverage_high = st.sidebar.slider("High Conviction Leverage", 1.0, 20.0, 10.0)
leverage_low = st.sidebar.slider("Low Conviction Leverage", 1.0, 5.0, 2.0)

st.sidebar.header("Market Phase Settings")
lookback_cross = st.sidebar.number_input("Lookback for crosses (candles)", value=60)
min_crosses = st.sidebar.number_input("Min crosses for Consolidation", value=3)

# --- Load Data ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('btc_4h_3y_real.csv', index_col='timestamp', parse_dates=True)
        return df
    except FileNotFoundError:
        st.error("Historical data file 'btc_4h_3y_real.csv' not found. Please run the download script first.")
        return None

data_df = load_data()

if data_df is not None:
    st.subheader("Historical Data Preview")
    st.line_chart(data_df['close'])

    # --- Run Backtest ---
    if st.button("Run Backtest"):
        with st.spinner("Running strategy..."):
            class EquityObserver(bt.observer.Observer):
                lines = ('equity',)
                plotinfo = dict(plot=True, subplot=True)
                def next(self):
                    self.lines.equity[0] = self._owner.broker.getvalue()

            cerebro = bt.Cerebro()
            data = bt.feeds.PandasData(dataname=data_df)
            cerebro.adddata(data)

            cerebro.addstrategy(
                BitcoinStrategy,
                ema_period=int(ema_period),
                rsi_period=int(rsi_period),
                risk_per_trade=risk_per_trade,
                leverage_high=leverage_high,
                leverage_low=leverage_low,
                lookback_cross=int(lookback_cross),
                min_crosses=int(min_crosses)
            )

            initial_cash = 10000.0
            cerebro.broker.setcash(initial_cash)
            cerebro.broker.setcommission(commission=0.0006)

            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')

            results = cerebro.run()
            strat = results[0]

            # --- Display Results ---
            final_value = cerebro.broker.getvalue()
            res_sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
            res_dd = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
            res_trades = strat.analyzers.trades.get_analysis()
            res_ret = strat.analyzers.returns.get_analysis().get('rtot', 0)

            st.success("Backtest Completed!")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Final Balance", f"${final_value:,.2f}", f"{(final_value/initial_cash - 1):.2%}")
            col2.metric("Sharpe Ratio", f"{res_sharpe if res_sharpe else 0:.2f}")
            col3.metric("Max Drawdown", f"{res_dd:.2f}%")

            if 'total' in res_trades:
                col4.metric("Total Trades", res_trades.total.total)

                st.subheader("Trade Statistics")
                t_col1, t_col2, t_col3, t_col4 = st.columns(4)
                if 'won' in res_trades:
                    win_rate = res_trades.won.total / res_trades.total.total if res_trades.total.total > 0 else 0
                    t_col1.write(f"**Win Rate:** {win_rate:.2%}")
                    t_col2.write(f"**Wins:** {res_trades.won.total}")
                    t_col3.write(f"**Losses:** {res_trades.lost.total}")

                    if res_trades.lost.total > 0:
                        pf = res_trades.won.pnl.total / abs(res_trades.lost.pnl.total)
                        t_col4.write(f"**Profit Factor:** {pf:.2f}")

            # Plot Equity Curve
            returns_dict = strat.analyzers.timereturn.get_analysis()
            returns_df = pd.Series(returns_dict).cumsum()
            st.subheader("Equity Curve (Cumulative Returns)")
            st.line_chart(returns_df)

    st.info("The backtest runs on 4-hour candles from May 2021 to July 2024.")
else:
    st.warning("Please download the data first to proceed.")
