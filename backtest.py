import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# 1. 页面配置
st.set_page_config(page_title="A股定投回测系统", layout="wide")
st.title("📈 A股定投回测系统")

# 2. 数据获取函数 (带缓存)
@st.cache_data(ttl=3600)
def get_stock_data(symbol, start_date, end_date):
    symbol = str(symbol).strip().upper().replace(".SS", "").replace(".SZ", "")
    ticker = f"{symbol}.SS" if symbol.startswith("6") else f"{symbol}.SZ"
    
    # end 参数是不包含当天的开区间，加 1 天以包含选定的结束日期当天
    fetch_end = end_date + datetime.timedelta(days=1)
    
    df = yf.download(ticker, start=start_date, end=fetch_end, progress=False)
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

start_date = st.sidebar.date_input("开始日期", value=datetime.date(2024, 1, 1))
end_date = st.sidebar.date_input("结束日期", value=datetime.date.today())

daily_amount = st.sidebar.number_input("每日定投金额 (元)", value=100.0, step=50.0)

# 4. 主逻辑区
if st.sidebar.button("获取数据并执行回测"):
    if start_date >= end_date:
        st.error("❌ 开始日期必须早于结束日期！")
    else:
        with st.spinner('正在拉取数据并计算...'):
            try:
                result = get_stock_data(symbol, start_date, end_date)
                
                if isinstance(result, tuple):
                    df, actual_ticker = result
                else:
                    df = result
                    actual_ticker = symbol

                if df.empty:
                    st.error(f"⚠️ 未能获取到数据。系统实际请求的代码为：【{actual_ticker}】")
                else:
                    # ==========================================
                    # 1. 核心逻辑计算
                    # ==========================================
                    df['当天涨幅(%)'] = df['Close'].pct_change() * 100
                    df['当天涨幅(%)'] = df['当天涨幅(%)'].fillna(0.0)
                    
                    df['当日买入股数'] = daily_amount / df['Close']
                    df['累计持有股数'] = df['当日买入股数'].cumsum()
                    df['累计投入本金'] = daily_amount * pd.Series(range(1, len(df) + 1), index=df.index)
                    df['持仓市值'] = df['累计持有股数'] * df['Close']
                    df['累计盈亏'] = df['持仓市值'] - df['累计投入本金']
                    df['收益率(%)'] = (df['累计盈亏'] / df['累计投入本金']) * 100

                    display_cols = ['Close', '当天涨幅(%)', '累计投入本金', '持仓市值', '累计盈亏', '收益率(%)']
                    display_df = df[display_cols].copy().round(2)
                    display_df = display_df.rename(columns={'Close': '收盘价'})

                    # ==========================================
                    # 2. 【新增】顶部核心数据看板 (Metrics)
                    # ==========================================
                    st.subheader("📌 核心数据汇总")
                    
                    # 提取最后一天（即结束当天）的数据
                    last_row = display_df.iloc[-1]
                    total_invested = last_row['累计投入本金']
                    final_market_value = last_row['持仓市值']
                    total_profit = last_row['累计盈亏']
                    total_return_pct = last_row['收益率(%)']

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("累计投入本金", f"¥{total_invested:,.2f}")
                    col2.metric("期末持仓市值", f"¥{final_market_value:,.2f}")
                    col3.metric("累计盈亏", f"¥{total_profit:,.2f}", delta=f"{total_profit:,.2f} 元")
                    col4.metric("截止结束日收益率", f"{total_return_pct:.2f}%", delta=f"{total_return_pct:.2f}%")

                    st.divider()  # 分割线

                    # ==========================================
                    # 3. 详细明细表与走势图
                    # ==========================================
                    st.subheader(f"📊 定投明细表 ({start_date} 至 {end_date})")
                    st.dataframe(display_df, use_container_width=True)
                    
                    st.subheader("📈 累计投入 vs 持仓市值")
                    st.line_chart(display_df[['累计投入本金', '持仓市值']])
                    
                    st.subheader("💰 累计盈亏走势 (元)")
                    st.line_chart(display_df['累计盈亏'])
                    
            except Exception as e:
                st.error(f"❌ 运行发生错误: {e}")
