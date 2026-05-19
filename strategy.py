import backtrader as bt
import pandas as pd
import numpy as np

class BitcoinStrategy(bt.Strategy):
    params = (
        ('ema_period', 300), # ~50 days for 4h candles
        ('rsi_period', 14),
        ('macd_p1', 12),
        ('macd_p2', 26),
        ('macd_psig', 9),
        ('adx_period', 14),
        ('atr_period', 14),
        ('lookback_cross', 60),
        ('min_crosses', 3),
        ('leverage_high', 10.0),
        ('leverage_low', 2.0),
        ('risk_per_trade', 0.02),
    )

    def __init__(self):
        # Indicators
        self.ema = bt.indicators.EMA(period=self.params.ema_period)
        self.rsi = bt.indicators.RSI(period=self.params.rsi_period)
        self.macd = bt.indicators.MACD(period_me1=self.params.macd_p1,
                                       period_me2=self.params.macd_p2,
                                       period_signal=self.params.macd_psig)
        self.adx = bt.indicators.ADX(period=self.params.adx_period)
        self.atr = bt.indicators.ATR(period=self.params.atr_period)
        self.vol_ema = bt.indicators.EMA(self.data.volume, period=20)
        self.crosses = bt.indicators.CrossOver(self.data.close, self.ema)

        self.order = None
        self.stop_order = None
        self.limit_order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if not order.alive():
            if order == self.order:
                self.order = None
            elif order == self.stop_order:
                self.stop_order = None
                if self.limit_order: self.cancel(self.limit_order)
            elif order == self.limit_order:
                self.limit_order = None
                if self.stop_order: self.cancel(self.stop_order)

    def next(self):
        if len(self) < self.params.ema_period:
            return
        if self.order or self.position:
            return

        # 1. Market Phase Detection
        cross_count = sum([1 for i in range(-self.params.lookback_cross + 1, 1) if self.crosses[i] != 0])
        if cross_count >= self.params.min_crosses:
            phase = 'consolidation'; rr = 3
        elif self.data.close[0] > self.ema[0]:
            phase = 'bull'; rr = 8
        else:
            phase = 'bear'; rr = 8

        # 2. Conviction Scoring
        score = 0
        total_weight = 4
        if phase == 'bull':
            if self.rsi[0] > 50: score += 1
            if self.macd.macd[0] > self.macd.signal[0]: score += 1
            if self.adx[0] > 20: score += 1
            if self.data.volume[0] > self.vol_ema[0]: score += 1
        elif phase == 'bear':
            if self.rsi[0] < 50: score += 1
            if self.macd.macd[0] < self.macd.signal[0]: score += 1
            if self.adx[0] > 20: score += 1
            if self.data.volume[0] > self.vol_ema[0]: score += 1
        else: # consolidation
            if 40 < self.rsi[0] < 60: score += 1
            if abs(self.macd.macd[0] - self.macd.signal[0]) < (self.data.close[0] * 0.001): score += 1
            if self.adx[0] < 25: score += 1
            if self.data.volume[0] < self.vol_ema[0] * 1.2: score += 1

        conviction = score / total_weight
        leverage = self.params.leverage_high if conviction >= 0.95 else self.params.leverage_low

        # 3. Position Sizing
        equity = self.broker.get_value()
        risk_amount = equity * self.params.risk_per_trade
        sl_dist = 2.5 * self.atr[0]
        if sl_dist == 0: return

        size = risk_amount / sl_dist
        max_size = (equity * leverage * 0.95) / self.data.close[0]
        size = min(size, max_size)

        if size <= 0.0001: return

        # 4. Signal Execution
        if (phase == 'bull' and conviction >= 0.75):
             if self.rsi[0] < 70:
                sl_p = self.data.close[0] - sl_dist
                tp_p = self.data.close[0] + (sl_dist * rr)
                self.order = self.buy(size=size)
                self.stop_order = self.sell(exectype=bt.Order.Stop, price=sl_p, size=size)
                self.limit_order = self.sell(exectype=bt.Order.Limit, price=tp_p, size=size)
        elif (phase == 'bear' and conviction >= 0.75):
             if self.rsi[0] > 30:
                sl_p = self.data.close[0] + sl_dist
                tp_p = self.data.close[0] - (sl_dist * rr)
                self.order = self.sell(size=size)
                self.stop_order = self.buy(exectype=bt.Order.Stop, price=sl_p, size=size)
                self.limit_order = self.buy(exectype=bt.Order.Limit, price=tp_p, size=size)
        elif phase == 'consolidation' and conviction >= 0.5:
            if self.rsi[0] < 30:
                sl_p = self.data.close[0] - sl_dist
                tp_p = self.data.close[0] + (sl_dist * rr)
                self.order = self.buy(size=size)
                self.stop_order = self.sell(exectype=bt.Order.Stop, price=sl_p, size=size)
                self.limit_order = self.sell(exectype=bt.Order.Limit, price=tp_p, size=size)
            elif self.rsi[0] > 70:
                sl_p = self.data.close[0] + sl_dist
                tp_p = self.data.close[0] - (sl_dist * rr)
                self.order = self.sell(size=size)
                self.stop_order = self.buy(exectype=bt.Order.Stop, price=sl_p, size=size)
                self.limit_order = self.buy(exectype=bt.Order.Limit, price=tp_p, size=size)

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    df = pd.read_csv('btc_4h_3y_real.csv', index_col='timestamp', parse_dates=True)
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(BitcoinStrategy)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0006)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

    results = cerebro.run()
    strat = results[0]

    print("\n--- BTC TRADING STRATEGY BACKTEST (REAL DATA: 2021-05 to 2024-07) ---")
    print(f"Initial Balance: 10,000.00 USD")
    print(f"Final Balance:   {cerebro.broker.getvalue():.2f} USD")

    res_sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    res_dd = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
    res_trades = strat.analyzers.trades.get_analysis()
    res_ret = strat.analyzers.returns.get_analysis().get('rtot', 0)

    print(f"Total Return:    {(np.exp(res_ret)-1)*100:.2f}%")
    print(f"Sharpe Ratio:    {res_sharpe if res_sharpe else 0:.2f}")
    print(f"Max Drawdown:    {res_dd:.2f}%")

    if 'total' in res_trades:
        print(f"Total Trades:    {res_trades.total.total}")
        if 'won' in res_trades:
            print(f"Win Rate:        {res_trades.won.total / res_trades.total.total:.2%}")
            if res_trades.lost.total > 0:
                print(f"Profit Factor:   {res_trades.won.pnl.total / abs(res_trades.lost.pnl.total):.2f}")
