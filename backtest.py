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
    
    # yfinance 的 end 参数是不包含当天的开区间，因此加 1 天以包含选定的结束日期当天
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

# 原生日历选择控件
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
                    st.success(f"成功获取 {symbol} 从 {start_date} 到 {end_date} 的数据！共 {len(df)} 个交易日。")
                    
                    # ==========================================
                    # 核心逻辑计算
                    # ==========================================
                    # 1. 计算当天涨幅 (%)
                    df['当天涨幅(%)'] = df['Close'].pct_change() * 100
                    df['当天涨幅(%)'] = df['当天涨幅(%)'].fillna(0.0)  # 起始第一天没有前一天数据，设为 0
                    
                    # 2. 每天买入股数 (允许碎股)
                    df['当日买入股数'] = daily_amount / df['Close']
                    
                    # 3. 累计持有股数
                    df['累计持有股数'] = df['当日买入股数'].cumsum()
                    
                    # 4. 累计投入本金
                    df['累计投入本金'] = daily_amount * pd.Series(range(1, len(df) + 1), index=df.index)
                    
                    # 5. 持仓市值
                    df['持仓市值'] = df['累计持有股数'] * df['Close']
                    
                    # 6. 累计盈亏
                    df['累计盈亏'] = df['持仓市值'] - df['累计投入本金']
                    
                    # 7. 收益率(%)
                    df['收益率(%)'] = (df['累计盈亏'] / df['累计投入本金']) * 100

                    # 整理展示的列并做重命名
                    display_cols = ['Close', '当天涨幅(%)', '累计投入本金', '持仓市值', '累计盈亏', '收益率(%)']
                    display_df = df[display_cols].copy().round(2)
                    display_df = display_df.rename(columns={'Close': '收盘价'})
                    
                    st.subheader(f"📊 定投明细表 ({start_date} 至 {end_date})")
                    # 显示全量数据表格，不限制显示行数
                    st.dataframe(display_df, use_container_width=True)
                    
                    # 绘制走势图
                    st.subheader("📈 累计投入 vs 持仓市值")
                    st.line_chart(display_df[['累计投入本金', '持仓市值']])
                    
                    st.subheader("💰 累计盈亏走势 (元)")
                    st.line_chart(display_df['累计盈亏'])
                    
            except Exception as e:
                st.error(f"❌ 运行发生错误: {e}")
