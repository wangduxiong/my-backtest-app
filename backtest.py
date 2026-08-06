import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 页面配置
st.set_page_config(page_title="A股定投回测系统", layout="centered")
st.title("📈 A股定投回测系统 (海外稳定版)")

# 2. 数据获取函数 (带缓存)
@st.cache_data(ttl=3600)
def get_stock_data(symbol, start_date):
    symbol = str(symbol).strip().upper().replace(".SS", "").replace(".SZ", "")
    ticker = f"{symbol}.SS" if symbol.startswith("6") else f"{symbol}.SZ"
    
    if len(start_date) == 8 and "-" not in start_date:
        formatted_start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    else:
        formatted_start = start_date
        
    df = yf.download(ticker, start=formatted_start, progress=False)
    if df.empty:
        return df, ticker
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df = df.dropna(how='all')
    df = df.ffill()
    return df, ticker

# 3. 侧边栏/输入区
st.sidebar.header("参数设置")
symbol = st.sidebar.text_input("股票代码 (如: 603399)", value="603399")
start_date = st.sidebar.text_input("开始日期 (如: 20240101)", value="20240101")
daily_amount = st.sidebar.number_input("每日定投金额 (元)", value=100.0, step=50.0)

# 4. 主逻辑区
if st.sidebar.button("获取数据并执行回测"):
    with st.spinner('正在拉取数据并计算...'):
        try:
            result = get_stock_data(symbol, start_date)
            
            if isinstance(result, tuple):
                df, actual_ticker = result
            else:
                df = result
                actual_ticker = symbol

            if df.empty:
                st.error(f"⚠️ 未能获取到数据。系统实际请求的代码为：【{actual_ticker}】")
            else:
                st.success(f"成功获取 {symbol} 的数据！共 {len(df)} 个交易日。")
                
                # ==========================================
                # 核心逻辑：计算每日定投盈亏
                # ==========================================
                # 1. 每天买入的股数 = 每天定投金额 / 当天收盘价 (理论计算，允许碎股)
                df['当日买入股数'] = daily_amount / df['Close']
                
                # 2. 累计持有股数
                df['累计持有股数'] = df['当日买入股数'].cumsum()
                
                # 3. 累计投入本金 = 每天定投金额 * 累计天数
                df['累计投入本金'] = daily_amount * pd.Series(range(1, len(df) + 1), index=df.index)
                
                # 4. 当日持仓市值 = 累计持有股数 * 当天收盘价
                df['持仓市值'] = df['累计持有股数'] * df['Close']
                
                # 5. 累计盈亏 = 持仓市值 - 累计投入本金
                df['累计盈亏'] = df['持仓市值'] - df['累计投入本金']
                
                # 6. 收益率(%) = (累计盈亏 / 累计投入本金) * 100
                df['收益率(%)'] = (df['累计盈亏'] / df['累计投入本金']) * 100

                # 整理要展示的列并保留两位小数
                display_cols = ['Close', '累计投入本金', '持仓市值', '累计盈亏', '收益率(%)']
                display_df = df[display_cols].copy().round(2)
                
                st.subheader(f"📊 定投数据明细 (每日 {daily_amount} 元)")
                st.dataframe(display_df.tail(10))  # 显示最近10天
                
                # 绘制走势图
                st.subheader("📈 累计投入 vs 持仓市值")
                st.line_chart(display_df[['累计投入本金', '持仓市值']])
                
                st.subheader("💰 累计盈亏走势 (元)")
                st.line_chart(display_df['累计盈亏'])
                
        except Exception as e:
            st.error(f"❌ 运行发生错误: {e}")
