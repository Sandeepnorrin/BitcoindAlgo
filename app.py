import streamlit as st
import pandas as pd
import numpy as np
import backtrader as bt
from strategy import BitcoinStrategy
import plotly.graph_objects as go

st.set_page_config(page_title="BTC Pro Backtester", layout="wide")

st.title("₿ BTC Strategy Pro: High-Frequency 1H Backtester")
st.markdown("Dynamic Bitcoin strategy for all market phases. Backtested on 3 years of 1-hour data.")

# Sidebar
st.sidebar.header("Execution Settings")
risk_pct = st.sidebar.slider("Risk Per Trade (%)", 0.5, 5.0, 2.0) / 100.0
leverage = st.sidebar.slider("Leverage (Max)", 1.0, 10.0, 3.0)
trend_rr = st.sidebar.slider("Trend Risk:Reward", 1.0, 8.0, 5.0)
cons_rr = st.sidebar.slider("Consolidation Risk:Reward", 1.0, 5.0, 3.0)

# Load Data
@st.cache_data
def load_data():
    df = pd.read_csv('btc_1h_recent.csv', index_col='timestamp', parse_dates=True)
    # Filter to "current" date
    df = df[df.index <= '2024-05-19']
    return df

df = load_data()

if st.button("🚀 Run Analysis"):
    with st.spinner("Processing trades..."):
        cerebro = bt.Cerebro()
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data)

        cerebro.addstrategy(
            BitcoinStrategy,
            risk_per_trade=risk_pct,
            leverage=leverage,
            trend_rr=trend_rr,
            cons_rr=cons_rr
        )

        initial_cash = 10000.0
        cerebro.broker.setcash(initial_cash)
        cerebro.broker.setcommission(commission=0.0006)

        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')

        results = cerebro.run()
        strat = results[0]

        # Display Metrics
        final_val = cerebro.broker.getvalue()
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
        dd = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
        trades_res = strat.analyzers.trades.get_analysis()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Final Balance", f"$\{final_val:,.2f\}", f"\{(final_val/initial_cash-1):.2%\}")
        m2.metric("Total Trades", trades_res.total.total if 'total' in trades_res else 0)
        m3.metric("Sharpe Ratio", f"\{sharpe if sharpe else 0:.2f\}")
        m4.metric("Max Drawdown", f"\{dd:.2f\}%")

        # Chart with Signals
        st.subheader("Price Action & Entry Signals")
        # Show last 1000 candles
        plot_df = df.tail(1000)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['open'], high=plot_df['high'], low=plot_df['low'], close=plot_df['close'], name='Price'))

        logs = strat.trade_logs
        for log in logs:
            log_date = pd.to_datetime(log['date'])
            if log_date >= plot_df.index[0]:
                color = 'green' if 'Long' in log['type'] else 'red'
                marker = 'triangle-up' if 'Long' in log['type'] else 'triangle-down'
                fig.add_trace(go.Scatter(x=[log_date], y=[log['price']], mode='markers', marker=dict(symbol=marker, size=12, color=color), name=log['type'], showlegend=False))

                # Visual SL/TP
                fig.add_trace(go.Scatter(x=[log_date, log_date + pd.Timedelta(hours=48)], y=[log['tp'], log['tp']], mode='lines', line=dict(color='blue', dash='dot', width=1), showlegend=False))
                fig.add_trace(go.Scatter(x=[log_date, log_date + pd.Timedelta(hours=48)], y=[log['sl'], log['sl']], mode='lines', line=dict(color='orange', dash='dot', width=1), showlegend=False))

        fig.update_layout(xaxis_rangeslider_visible=False, height=600)
        st.plotly_chart(fig, use_container_width=True)

        # Equity Curve
        st.subheader("Performance Curve")
        ret_df = pd.Series(strat.analyzers.timereturn.get_analysis()).cumsum()
        st.line_chart(ret_df)

st.sidebar.markdown("---")
st.sidebar.info("Using 1-hour candles for higher trade frequency. Strategy utilizes EMA, RSI, MACD, and ADX for phase detection and entry confirmation.")
