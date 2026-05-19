import backtrader as bt
import pandas as pd
import numpy as np

class BitcoinStrategy(bt.Strategy):
    params = (
        ('ema_period', 1200),
        ('rsi_period', 14),
        ('risk_per_trade', 0.02),
        ('trend_rr', 5.0),
        ('cons_rr', 3.0),
        ('leverage', 1.0),
    )

    def __init__(self):
        self.ema_long = bt.indicators.EMA(period=self.p.ema_period)
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.macd = bt.indicators.MACD()
        self.atr = bt.indicators.ATR(period=14)
        self.adx = bt.indicators.ADX(period=14)

        self.order = None
        self.stop_order = None
        self.limit_order = None
        self.trade_logs = []

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

        # Phase
        if self.adx[0] < 25:
            phase = 'consolidation'; rr = self.p.cons_rr
        elif self.data.close[0] > self.ema_long[0]:
            phase = 'bull'; rr = self.p.trend_rr
        else:
            phase = 'bear'; rr = self.p.trend_rr

        entry = False
        sl_dist = 2.0 * self.atr[0]
        if sl_dist == 0: return

        # Relaxed entry logic for higher frequency
        if phase == 'bull':
            if self.macd.macd[0] > self.macd.signal[0]: # Simple MACD cross in trend
                sl_p = self.data.close[0] - sl_dist
                tp_p = self.data.close[0] + (sl_dist * rr)
                entry = True; trade_type = 'Long'
        elif phase == 'bear':
            if self.macd.macd[0] < self.macd.signal[0]:
                sl_p = self.data.close[0] + sl_dist
                tp_p = self.data.close[0] - (sl_dist * rr)
                entry = True; trade_type = 'Short'
        else: # Consolidation
            if self.rsi[0] < 35:
                sl_p = self.data.close[0] - sl_dist
                tp_p = self.data.close[0] + (sl_dist * rr)
                entry = True; trade_type = 'Cons Long'
            elif self.rsi[0] > 65:
                sl_p = self.data.close[0] + sl_dist
                tp_p = self.data.close[0] - (sl_dist * rr)
                entry = True; trade_type = 'Cons Short'

        if entry:
            equity = self.broker.get_value()
            risk_amount = equity * self.p.risk_per_trade
            size = risk_amount / sl_dist
            max_size = (equity * self.p.leverage * 0.95) / self.data.close[0]
            size = min(size, max_size)

            if size > 0.00001:
                if 'Long' in trade_type:
                    self.order = self.buy(size=size)
                    self.stop_order = self.sell(exectype=bt.Order.Stop, price=sl_p, size=size)
                    self.limit_order = self.sell(exectype=bt.Order.Limit, price=tp_p, size=size)
                else:
                    self.order = self.sell(size=size)
                    self.stop_order = self.buy(exectype=bt.Order.Stop, price=sl_p, size=size)
                    self.limit_order = self.buy(exectype=bt.Order.Limit, price=tp_p, size=size)

                self.trade_logs.append({
                    'date': self.data.datetime.datetime(0).isoformat(),
                    'type': trade_type,
                    'price': float(self.data.close[0]),
                    'sl': float(sl_p),
                    'tp': float(tp_p),
                    'phase': phase
                })

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    df = pd.read_csv('btc_1h_recent.csv', index_col='timestamp', parse_dates=True)
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(BitcoinStrategy)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0006)
    results = cerebro.run()
    print(f"Final Value: {cerebro.broker.getvalue():.2f}")
