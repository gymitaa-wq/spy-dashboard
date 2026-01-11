import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="SPY Put Selling Dashboard", layout="wide")
st.title("📈 putoption Option Selling Dashboard")

# --- 侧边栏配置 ---
st.sidebar.header("参数设置")

min_dte_input = st.sidebar.slider("Min DTE (Days to Expiration)", 0, 180, 30)
max_dte_input = st.sidebar.slider("Max DTE", 0, 800, 120)

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

# --- 核心逻辑 ---
@st.cache_data(ttl=900, show_spinner=False)
def get_option_data(ticker_symbol, min_dte, max_dte):
    status_container = st.empty()
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # 1. 获取标的当前价格
        try:
            todays_data = ticker.history(period='1d')
            if not todays_data.empty:
                current_price = todays_data['Close'].iloc[-1]
            else:
                return None, None, "无法获取标的价格"
        except Exception:
            return None, None, "Yahoo Finance 连接失败，请稍后重试。"

        # 2. 获取所有期权日期
        expirations = ticker.options
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
            
            # 防封锁延迟
            time.sleep(random.uniform(0.5, 1.5))
            
            try:
                chain = ticker.option_chain(exp_date_str)
                puts = chain.puts
                
                if puts.empty:
                    continue

                # --- 关键修改：只保留离目标 Moneyness 最近的 Strike ---
                selected_indices = set() # 用集合去重
                
                for ratio in TARGET_MONEYNESS:
                    target_strike = current_price * ratio
                    # 找到绝对差值最小的那个索引
                    # (abs(puts['strike'] - target_strike)).idxmin() 返回最小值的索引
                    closest_idx = (puts['strike'] - target_strike).abs().idxmin()
                    selected_indices.add(closest_idx)
                
                # 根据筛选出的索引提取数据
                puts = puts.loc[list(selected_indices)].copy()
                
                # --- 计算指标 ---
                puts['premium'] = puts['bid']
                puts['return_on_risk'] = puts['premium'] / puts['strike']
                
                safe_dte = dte if dte > 0 else 0.5 
                puts['annualized_return'] = (puts['return_on_risk'] / safe_dte) * 365
                
                puts['expiration'] = exp_date_str
                puts['dte'] = dte
                puts['moneyness'] = puts['strike'] / current_price
                
                all_options.append(puts)
                
            except Exception as e:
                continue
                    
        progress_bar.empty()
        status_container.empty()
        
        if not all_options:
            return None, current_price, "未找到数据"
            
        final_df = pd.concat(all_options, ignore_index=True)
        return final_df, current_price, None

    except Exception as e:
        return None, None, f"发生错误: {str(e)}"

def display_ticker_dashboard(ticker_symbol, min_dte, max_dte):
    if st.button(f'刷新数据 (Fetch Data) - {ticker_symbol}', key=f"btn_{ticker_symbol}"):
        with st.spinner(f'正在从 Yahoo Finance 获取 {ticker_symbol} 数据...'):
            df, spot_price, error_msg = get_option_data(ticker_symbol, min_dte, max_dte)
            
            if error_msg:
                st.error(error_msg)
            elif spot_price:
                st.metric(label=f"{ticker_symbol} Current Price", value=f"${spot_price:.2f}")
            
            if df is not None and not df.empty:
                display_cols = [
                    'expiration', 'dte', 'strike', 'moneyness', 
                    'annualized_return', 'premium', 'ask', 'openInterest'
                ]
                
                df_display = df[display_cols].copy()
                # 排序：先按日期，再按 Moneyness 从小到大 (0.85 -> 0.95)
                df_display = df_display.sort_values(by=['dte', 'moneyness'], ascending=[True, True])
                
                st.success(f"已精简显示：共找到 {len(df)} 个关键合约")
                
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
                
                st.dataframe(styled_df, height=600, use_container_width=True)
                
                csv = df_display.to_csv(index=False).encode('utf-8')
                st.download_button(f"下载 {ticker_symbol} CSV", csv, f"{ticker_symbol}_puts_filtered.csv", "text/csv", key=f"dl_{ticker_symbol}")

# --- Tab 布局 ---
tab_spy, tab_qqq, tab_tsla, tab_ibit = st.tabs(["SPY", "QQQ", "TSLA", "IBIT"])

with tab_spy:
    st.header("SPY Options")
    display_ticker_dashboard("SPY", min_dte_input, max_dte_input)

with tab_qqq:
    st.header("QQQ Options")
    display_ticker_dashboard("QQQ", min_dte_input, max_dte_input)

with tab_tsla:
    st.header("TSLA Options")
    display_ticker_dashboard("TSLA", min_dte_input, max_dte_input)

with tab_ibit:
    st.header("IBIT Options")
    display_ticker_dashboard("IBIT", min_dte_input, max_dte_input)

st.markdown("---")
st.markdown("**说明：** 表格仅显示离 0.85, 0.90, 0.92, 0.93, 0.95 Moneyness 最近的合约。")
