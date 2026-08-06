import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# 1. 页面配置
st.set_page_config(page_title="A股定投回测系统", layout="wide")
st.title("📈 A股定投回测系统")

# 初始化 session_state 历史记录列表
if "history" not in st.session_state:
    st.session_state.history = []

# 2. 数据获取函数 (带缓存)
@st.cache_data(ttl=3600)
def get_stock_data(symbol, start_date, end_date):
    symbol = str(symbol).strip().upper().replace(".SS", "").replace(".SZ", "")
    ticker = f"{symbol}.SS" if symbol.startswith("6") else f"{symbol}.SZ"
    
    fetch_end = end_date + datetime.timedelta(days=1)
    
    df = yf.download(ticker, start=start_date, end=fetch_end, progress=False)
    if df.empty:
        return df, ticker
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df = df.dropna(how='all')
    df = df.ffill()
    return df, ticker

# 3. 侧边栏/输入区 (左侧)
st.sidebar.header("⚙️ 参数设置")
symbol = st.sidebar.text_input("股票代码 (如: 603399)", value="603399")

# 默认开始日期修改为 2026年05月01日
start_date = st.sidebar.date_input("开始日期", value=datetime.date(2026, 5, 1))
end_date = st.sidebar.date_input("结束日期", value=datetime.date.today())

# 默认定投金额修改为 10000 元
daily_amount = st.sidebar.number_input("每日定投金额 (元)", value=10000.0, step=1000.0)

run_button = st.sidebar.button("获取数据并执行回测", type="primary")

# 4. 主逻辑区
if run_button:
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
                    # 2. 提取统计指标
                    # ==========================================
                    last_row = display_df.iloc[-1]
                    total_invested = last_row['累计投入本金']
                    final_market_value = last_row['持仓市值']
                    total_profit = last_row['累计盈亏']
                    total_return_pct = last_row['收益率(%)']

                    # 天数计算
                    total_calendar_days = (end_date - start_date).days + 1  # 日历天数
                    actual_trading_days = len(df)                          # 实际定投交易天数

                    # ==========================================
                    # 3. 顶部核心数据看板 (Metrics 6项)
                    # ==========================================
                    st.subheader("📌 核心数据汇总")
                    
                    row1_col1, row1_col2, row1_col3 = st.columns(3)
                    row1_col1.metric("累计投入本金", f"¥{total_invested:,.2f}")
                    row1_col2.metric("期末持仓市值", f"¥{final_market_value:,.2f}")
                    row1_col3.metric("累计盈亏", f"¥{total_profit:,.2f}", delta=f"{total_profit:,.2f} 元")

                    row2_col1, row2_col2, row2_col3 = st.columns(3)
                    row2_col1.metric("截止结束日收益率", f"{total_return_pct:.2f}%", delta=f"{total_return_pct:.2f}%")
                    row2_col2.metric("日历总天数 (开始至今)", f"{total_calendar_days} 天")
                    row2_col3.metric("实际定投天数 (交易日)", f"{actual_trading_days} 天")

                    st.divider()

                    # ==========================================
                    # 4. 写入左下角历史记录 (Session State)
                    # ==========================================
                    new_record = {
                        "时间": datetime.datetime.now().strftime("%H:%M:%S"),
                        "代码": symbol,
                        "投入": f"¥{total_invested:,.0f}",
                        "盈亏": f"¥{total_profit:,.0f}",
                        "收益率": f"{total_return_pct:.2f}%"
                    }
                    st.session_state.history.insert(0, new_record)  # 保持最新纪录在最前

                    # ==========================================
                    # 5. 详细明细表与走势图
                    # ==========================================
                    st.subheader(f"📊 定投明细表 ({start_date} 至 {end_date})")
                    st.dataframe(display_df, use_container_width=True)
                    
                    st.subheader("📈 累计投入 vs 持仓市值")
                    st.line_chart(display_df[['累计投入本金', '持仓市值']])
                    
                    st.subheader("💰 累计盈亏走势 (元)")
                    st.line_chart(display_df['累计盈亏'])
                    
            except Exception as e:
                st.error(f"❌ 运行发生错误: {e}")

# ==========================================
# 5. 左下角：历史回测记录区 (Sidebar 底部)
# ==========================================
st.sidebar.divider()
st.sidebar.subheader("📜 历史回测记录")

if st.session_state.history:
    hist_df = pd.DataFrame(st.session_state.history)
    st.sidebar.dataframe(hist_df, use_container_width=True, hide_index=True)
    if st.sidebar.button("清空历史记录", key="clear_hist_btn"):
        st.session_state.history = []
        st.rerun()
else:
    st.sidebar.caption("暂无历史记录，执行回测后将在此处自动留存对比。")
