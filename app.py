import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
from dotenv import load_dotenv
from Bly_Ultimate_Scanner import BlyUltimateScanner

load_dotenv()
st.set_page_config(page_title="BLY7H Signals", layout="wide", page_icon="🚀")
st.title("🚀 BLY7H Signals - Ultimate Scanner")
st.markdown("**كل الطبقات: SMC + OI + Liquidation + Premium + Killzone + AMD**")
st.sidebar.header("⚙️ الاعدادات")
min_score = st.sidebar.slider("اقل سكور يظهر", 0, 100, 50)

@st.cache_data(ttl=300)
def get_top_coins():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=10)
        data = r.json()
        usdt = [d for d in data if isinstance(d, dict) and d.get('symbol','').endswith('USDT')]
        sorted_coins = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0)), reverse=True)[:20]
        return [c['symbol'] for c in sorted_coins]
    except:
        return ['BTCUSDT','ETHUSDT','SOLUSDT','PEPEUSDT']

@st.cache_data(ttl=300)
def get_klines(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return None
        data = r.json()
        if not data or len(data) < 10: return None
        df = pd.DataFrame(data, columns=['open_time','open','high','low','close','volume','close_time','qav','trades','taker_base','taker_quote','ignore'])
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna()
        if len(df) < 5: return None
        return df
    except:
        return None

scanner = BlyUltimateScanner()

def analyze_symbol(symbol):
    try:
        df = get_klines(symbol)
        if df is None or len(df) < 5: return None
        last_close = float(df['close'].iloc[-1])
        prev_close = float(df['close'].iloc[-2])
        price_change = ((last_close - prev_close) / prev_close * 100) if prev_close != 0 else 0
        market_data = {
            'symbol': symbol, 'price_change': price_change, 'oi_change': 5.5,
            'liq': {'long_liq_above': 65, 'short_liq_below': 30},
            'spot': last_close, 'futures': last_close * 1.003,
            'hour_eg': datetime.now().hour,
            'amd_phase': 'MANIPULATION_DOWN' if df['low'].iloc[-1] < df['low'].iloc[-2] else 'ACCUMULATION',
            'usdt_flow': 70
        }
        return scanner.calculate_pump_score(df, market_data)
    except:
        return None

st.info(f"⏰ اخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
if st.button("🔍 افحص الان"):
    st.cache_data.clear()
    st.rerun()

coins = get_top_coins()
results = []
for symbol in coins:
    res = analyze_symbol(symbol)
    if res and res.get('score',0) >= min_score:
        results.append(res)

if results:
    df_result = pd.DataFrame(results).sort_values('score', ascending=False)
    st.success(f"✅ لقينا {len(df_result)} عملة فوق سكور {min_score}")
    st.dataframe(df_result, use_container_width=True)
    top = df_result.iloc[0]
    st.subheader(f"🎯 افضل فرصة: {top['symbol']} - سكور {top['score']}")
    st.metric("افضل دخول", f"{top['best_entry']:.6f}")
    st.metric("نقطة الالغاء No Return", f"{top['no_return_point']:.6f}")
else:
    st.warning(f"مفيش عملات فوق السكور {min_score} - قلل السكور لـ 30")
