import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 页面配置
st.set_page_config(page_title="A股回测系统", layout="centered")
st.title("📈 A股回测系统 (海外稳定版)")

# 2. 数据获取函数 (带缓存)
@st.cache_data(ttl=3600)
def get_stock_data(symbol, start_date):
    # 容错处理：清理多余的空格、字符，并自动转大写
    symbol = str(symbol).strip().upper().replace(".SS", "").replace(".SZ", "")
    
    # 自动识别并拼接正确的后缀
    ticker = f"{symbol}.SS" if symbol.startswith("6") else f"{symbol}.SZ"
    
    # 格式化日期
    if len(start_date) == 8 and "-" not in start_date:
        formatted_start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    else:
        formatted_start = start_date
        
    # 获取行情数据 (progress=False 阻止终端报错)
    df = yf.download(ticker, start=formatted_start, progress=False)
    
    # 如果直接就是空的，直接返回
    if df.empty:
        return df, ticker
        
    # 扁平化多层索引列名（兼容 yfinance 新版）
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # 【关键修复】千万不要用默认的 dropna()！改为只删除“整行全是空值”的数据
    df = df.dropna(how='all')
    
    # 剩下的个别空值，用前一天的有效数据填补
    df = df.ffill()
    
    return df, ticker

# 3. 侧边栏/输入区
st.sidebar.header("参数设置")
symbol = st.sidebar.text_input("股票代码 (如: 603399)", value="603399")
start_date = st.sidebar.text_input("开始日期 (如: 20240101)", value="20240101")

# 4. 主逻辑区
if st.sidebar.button("获取数据并执行回测"):
    with st.spinner('正在拉取数据，请稍候...'):
        try:
            # 接收数据和处理后的 ticker
            result = get_stock_data(symbol, start_date)
            
            # 兼容处理返回结果
            if isinstance(result, tuple):
                df, actual_ticker = result
            else:
                df = result
                actual_ticker = symbol

            if df.empty:
                st.error(f"⚠️ 依然未能获取到数据。系统实际请求的代码为：【{actual_ticker}】，起始日期：【{start_date}】。")
                st.warning("💡 可能原因：该股票在此期间停牌，或者雅虎财经临时限制了 Streamlit 云服务器的 IP。")
            else:
                st.success(f"成功获取 {symbol} 的数据！共 {len(df)} 个交易日。")
                
                # 展示最新几行数据
                st.subheader("📊 数据预览 (最新5天)")
                st.dataframe(df.tail())
                
                # 绘制收盘价走势图
                st.subheader("📈 收盘价走势")
                if "Close" in df.columns:
                    st.line_chart(df["Close"])
                
        except Exception as e:
            st.error(f"❌ 运行发生错误: {e}")
