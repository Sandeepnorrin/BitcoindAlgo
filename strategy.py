import backtrader as bt
import pandas as pd
import numpy as np

class BitcoinStrategy(bt.Strategy):
    params = (
        ('ema_period', 300),
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
        self.ema = bt.indicators.EMA(period=self.p.ema_period)
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(period_me1=self.p.macd_p1,
                                       period_me2=self.p.macd_p2,
                                       period_signal=self.p.macd_psig)
        self.adx = bt.indicators.ADX(period=self.p.adx_period)
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
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
        if len(self) < self.p.ema_period:
            return
        if self.order or self.position:
            return

        cross_count = sum([1 for i in range(-self.p.lookback_cross + 1, 1) if self.crosses[i] != 0])
        if cross_count >= self.p.min_crosses:
            phase = 'consolidation'; rr = 3
        elif self.data.close[0] > self.ema[0]:
            phase = 'bull'; rr = 8
        else:
            phase = 'bear'; rr = 8

        score = 0
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
        else:
            if 40 < self.rsi[0] < 60: score += 1
            if abs(self.macd.macd[0] - self.macd.signal[0]) < (self.data.close[0] * 0.001): score += 1
            if self.adx[0] < 25: score += 1
            if self.data.volume[0] < self.vol_ema[0] * 1.2: score += 1

        conviction = score / 4.0
        leverage = self.p.leverage_high if conviction >= 0.95 else self.p.leverage_low

        equity = self.broker.get_value()
        risk_amount = equity * self.p.risk_per_trade
        sl_dist = 2.5 * self.atr[0]
        if sl_dist == 0: return

        size = risk_amount / sl_dist
        max_size = (equity * leverage * 0.95) / self.data.close[0]
        size = min(size, max_size)

        if size <= 0.0001: return

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

    print("\n--- BTC TRADING STRATEGY BACKTEST (REAL DATA) ---")
    print(f"Final Balance:   {cerebro.broker.getvalue():.2f} USD")
