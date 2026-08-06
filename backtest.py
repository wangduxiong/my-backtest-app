import os
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['all_proxy'] = ''
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['ALL_PROXY'] = ''

import math
import requests
import akshare as ak
import backtrader as bt
import pandas as pd

# 强制将 requests 库的代理彻底置空
session = requests.Session()
session.trust_env = False
requests.get = lambda *args, **kwargs: session.get(*args, **kwargs)

class DailyFixedAmountStrategy(bt.Strategy):
    params = (('daily_budget', 10000),)

    def __init__(self):
        self.order = None

    def next(self):
        if self.order:
            return
        
        open_price = self.data.open[0]
        shares = math.floor(self.p.daily_budget / open_price / 100) * 100
        
        if shares >= 100:
            self.order = self.buy(size=shares)

    def stop(self):
        data_len = len(self.data)

        print("\n" + "=" * 95)
        print("【603399 每日及累计盈亏明细】")
        print(f"{'日期':<10}\t{'开盘价':<6}\t{'收盘价':<6}\t{'当日涨跌':<8}\t{'累计投入(元)':<10}\t{'当天持仓市值(元)':<12}\t{'截至当天总盈亏':<12}\t{'截至当天总收益率'}")
        print("-" * 95)

        accumulated_invested = 0
        accumulated_shares = 0

        for i in range(-data_len + 1, 1):
            dt_str = self.data.datetime.date(i).strftime('%Y-%m-%d')
            op = self.data.open[i]
            cp = self.data.close[i]
            
            s = math.floor(self.p.daily_budget / op / 100) * 100
            if s >= 100:
                accumulated_invested += s * op
                accumulated_shares += s
            
            daily_ret = ((cp - op) / op) * 100
            current_market_value = accumulated_shares * cp
            cum_pnl = current_market_value - accumulated_invested
            cum_ret = (cum_pnl / accumulated_invested * 100) if accumulated_invested > 0 else 0

            print(f"{dt_str}\t{op:<6.2f}\t{cp:<6.2f}\t{daily_ret:+6.2f}%\t{accumulated_invested:<12.2f}\t{current_market_value:<14.2f}\t{cum_pnl:+12.2f}\t{cum_ret:+8.2f}%")

        print("=" * 95)
        
@st.cache_data(ttl=3600)  # 缓存数据 1 小时，避免重复请求接口
def get_stock_data(symbol, start_date):
    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, adjust="qfq")
    return df
    
def get_stock_data(symbol="603399", start_date="20240624"):
    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, adjust="qfq")
    df = df[['日期', '开盘', '最高', '最低', '收盘', '成交量']]
    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    return df

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    df = get_stock_data("603399", "20240624")
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.broker.setcash(10000000.0)
    cerebro.addstrategy(DailyFixedAmountStrategy, daily_budget=10000)
    print("正在拉取 603399 数据并运行回测，请稍候...")
    cerebro.run()
