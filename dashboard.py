import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="SPY Put Selling Dashboard", layout="wide")
st.title("📉 SPY Put Option Selling Dashboard (Anti-Block Mode)")

# --- 侧边栏配置 ---
st.sidebar.header("参数设置")
ticker_input = st.sidebar.text_input("Ticker", "SPY")
min_dte_input = st.sidebar.slider("Min DTE (Days to Expiration)", 0, 180, 30)
max_dte_input = st.sidebar.slider("Max DTE", 0, 180, 120)

# 硬编码你想要的目标 Moneyness 点位
TARGET_MONEYNESS = [0.85, 0.90, 0.92, 0.93, 0.95]
st.sidebar.markdown("### 目标 Moneyness 点位")
st.sidebar.write(", ".join([f"{x:.2f}" for x in TARGET_MONEYNESS]))
st.sidebar.info("程序将自动寻找离这些点位最近的 Strike Price")

# --- 辅助函数：定义高亮逻辑 ---
def highlight_high_return(val):
    if isinstance(val, float) and val > 0.04:
        return 'background-color: #ff4b4b; color: white; font-weight: bold'
    return ''

# --- 核心逻辑 ---
# 增加重试机制装饰器，如果失败，Streamlit 不会立即报错，而是允许我们处理
@st.cache_data(ttl=900, show_spinner=False)
def get_option_data(ticker_symbol, min_dte, max_dte):
    status_container = st.empty()
    
    # --- 关键修改：创建一个伪装成浏览器的 Session ---
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    try:
        # 将 session 传递给 Ticker
        ticker = yf.Ticker(ticker_symbol, session=session)
        
        # 1. 获取标的当前价格 (增加重试逻辑)
        try:
            # 尝试获取实时数据
            todays_data = ticker.history(period='1d')
            if not todays_data.empty:
                current_price = todays_data['Close'].iloc[-1]
            else:
                return None, None, "无法获取标的价格 (Empty Data)"
        except Exception as e:
            # 如果第一次失败，休息 2 秒再试一次
            time.sleep(2)
            try:
                todays_data = ticker.history(period='1d')
                current_price = todays_data['Close'].iloc[-1]
            except:
                return None, None, "Yahoo 连接被拒绝 (IP Blocked)。请稍后再试，或在本地运行。"

        # 2. 获取所有期权日期
        try:
            expirations = ticker.options
        except Exception:
             return None, None, "无法获取期权链日期"

        if not expirations:
            return None, None, "未找到期权链数据"
            
        all_options = []
        today = datetime.now().date()
        
        # 筛选符合 DTE 的日期
        valid_dates = []
        for exp in expirations:
            d = datetime.strptime(exp, "%Y-%m-%d").date()
            dte = (d - today).days
            if min_dte <= dte <= max_dte:
                valid_dates.append(exp)
        
        total_exp = len(valid_dates)
        if total_exp == 0:
            return None, current_price, "没有符合 DTE 范围的日期"

        progress_bar = st.progress(0)
        
        for idx, exp_date_str in enumerate(valid_dates):
            exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            
            progress_bar.progress((idx + 1) / total_exp)
            status_container.text(f"正在抓取: {exp_date_str} (DTE: {dte})...")
            
            # 随机延迟，模拟人类
            time.sleep(random.uniform(1.0, 2.5))
            
            try:
                chain = ticker.option_chain(exp_date_str)
                puts = chain.puts
                
                if puts.empty:
                    continue

                # 筛选最近的 Strike
                selected_indices = set() 
                for ratio in TARGET_MONEYNESS:
                    target_strike = current_price * ratio
                    closest_idx = (puts['strike'] - target_strike).abs().idxmin()
                    selected_indices.add(closest_idx)
                
                puts = puts.loc[list(selected_indices)].copy()
                
                # 计算指标
                puts['premium'] = puts['bid']
                puts['return_on_risk'] = puts['premium'] / puts['strike']
                
                safe_dte = dte if dte > 0 else 0.5 
                puts['annualized_return'] = (puts['return_on_risk'] / safe_dte) * 365
                
                puts['expiration'] = exp_date_str
                puts['dte'] = dte
                puts['moneyness'] = puts['strike'] / current_price
                
                all_options.append(puts)
                
            except Exception as e:
                # 遇到单个日期失败，跳过，不要崩
                continue
                    
        progress_bar.empty()
        status_container.empty()
        
        if not all_options:
            return None, current_price, "未找到数据"
            
        final_df = pd.concat(all_options, ignore_index=True)
        return final_df, current_price, None

    except Exception as e:
        return None, None, f"系统错误: {str(e)}"

# --- 执行与显示 ---
if st.button('刷新数据 (Fetch Data)'):
    st.info("正在尝试连接 Yahoo... 如果长时间无反应，可能是被限流，请等待 1 分钟后重试。")
    df, spot_price, error_msg = get_option_data(ticker_input, min_dte_input, max_dte_input)
    
    if error_msg:
        st.error(error_msg)
    elif spot_price:
        st.metric(label=f"{ticker_input} Current Price", value=f"${spot_price:.2f}")
    
    if df is not None and not df.empty:
        display_cols = [
            'expiration', 'dte', 'strike', 'moneyness', 
            'annualized_return', 'premium', 'ask', 'openInterest'
        ]
        
        df_display = df[display_cols].copy()
        df_display = df_display.sort_values(by=['dte', 'moneyness'], ascending=[True, True])
        
        st.success(f"成功获取！已缓存数据 (15分钟内无需再次请求)")
        
        format_dict = {
            'annualized_return': '{:.2%}',
            'moneyness': '{:.2%}',
            'strike': '${:.2f}',
            'premium': '${:.2f}',
            'ask': '${:.2f}'
        }
        
        styled_df = (df_display.style
            .format(format_dict)
            .map(highlight_high_return, subset=['annualized_return'])
        )
        
        st.dataframe(styled_df, height=800, use_container_width=True)
        
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button("下载 CSV", csv, "spy_puts_filtered.csv", "text/csv")

st.markdown("---")
st.markdown("**说明：** 表格仅显示离 0.85, 0.90, 0.92, 0.93, 0.95 Moneyness 最近的合约。")