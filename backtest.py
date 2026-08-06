import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 页面配置
st.set_page_config(page_title="A股回测系统", layout="centered")
st.title("📈 A股回测系统 (海外稳定版)")

# 2. 数据获取函数 (带缓存，避免重复请求被限制)
@st.cache_data(ttl=3600)
def get_stock_data(symbol, start_date):
    # 自动识别沪深股市后缀：6开头的为沪市(.SS)，0或3开头为深市(.SZ)
    ticker = f"{symbol}.SS" if symbol.startswith("6") else f"{symbol}.SZ"
    
    # 将 "20240624" 格式转为 yfinance 识别的 "2024-06-24"
    if len(start_date) == 8 and "-" not in start_date:
        formatted_start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    else:
        formatted_start = start_date
        
    # 获取行情数据
    df = yf.download(ticker, start=formatted_start)
    
    # 扁平化列名（解决 yfinance 较新版本返回多层索引的问题）
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # 清理空数据
    df = df.dropna()
    return df

# 3. 侧边栏/输入区
st.sidebar.header("参数设置")
symbol = st.sidebar.text_input("股票代码 (如: 603399)", value="603399")
start_date = st.sidebar.text_input("开始日期 (如: 20240101)", value="20240101")

# 4. 主逻辑区
if st.sidebar.button("获取数据并执行回测"):
    with st.spinner('正在拉取数据，请稍候...'):
        try:
            df = get_stock_data(symbol, start_date)
            
            if df.empty:
                st.warning("⚠️ 未能获取到数据，请检查股票代码或日期。")
            else:
                st.success(f"成功获取 {symbol} 的数据！共 {len(df)} 个交易日。")
                
                # 展示最新几行数据
                st.subheader("📊 数据预览 (最新5天)")
                st.dataframe(df.tail())
                
                # 绘制收盘价走势图
                st.subheader("📈 收盘价走势")
                if "Close" in df.columns:
                    st.line_chart(df["Close"])
                
                # ==========================================
                # 你的回测计算逻辑（如计算均线、收益率等）可以写在这里
                # 例如：
                # df['MA5'] = df['Close'].rolling(window=5).mean()
                # ==========================================
                
        except Exception as e:
            st.error(f"❌ 数据拉取发生错误: {e}")
