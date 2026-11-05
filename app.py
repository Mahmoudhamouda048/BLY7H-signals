import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
import os
from dotenv import load_dotenv
from Bly_Ultimate_Scanner import BlyUltimateScanner

load_dotenv()
st.set_page_config(page_title="BLY7H Signals", layout="wide", page_icon="🚀")
st.title("🚀 BLY7H Signals - Ultimate Scanner")
st.markdown("**كل الطبقات: SMC + OI + Liquidation + Premium + Killzone + AMD**")

st.sidebar.header("⚙️ الاعدادات")
min_score = st.sidebar.slider("اقل سكور يظهر", 0, 100, 60)

@st.cache_data(ttl=300)
def get_top_coins():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=10)
        data = r.json()
        usdt = [d for d in data if d['symbol'].endswith('USDT')]
        sorted_coins = sorted(usdt, key=lambda x: float(x['quoteVolume']), reverse=True)[:30]
        return [c['symbol'] for c in sorted_coins]
    except:
        return ['BTCUSDT','ETHUSDT','SOLUSDT','PEPEUSDT']

@st.cache_data(ttl=300)
def get_klines(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        r = requests.get(url, timeout=10)
        data = r.json()
        df = pd.DataFrame(data, columns=['open_time','open','high','low','close','volume','close_time','qav','trades','taker_base','taker_quote','ignore'])
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        return df
    except:
        return None

scanner = BlyUltimateScanner()

def analyze_symbol(symbol):
    df = get_klines(symbol)
    if df is None: return None
    market_data = {
        'symbol': symbol,
        'price_change': 0.5, 'oi_change': 5.5,
        'liq': {'long_liq_above': 65, 'short_liq_below': 30},
        'spot': float(df['close'].iloc[-1]),
        'futures': float(df['close'].iloc[-1]) * 1.003,
        'hour_eg': datetime.now().hour,
        'amd_phase': 'MANIPULATION_DOWN',
        'usdt_flow': 70
    }
    return scanner.calculate_pump_score(df, market_data)

st.info(f"⏰ اخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

coins = get_top_coins()
results = []
for symbol in coins:
    res = analyze_symbol(symbol)
    if res and res['score'] >= min_score:
        results.append(res)

if results:
    df_result = pd.DataFrame(results).sort_values('score', ascending=False)
    st.dataframe(df_result, use_container_width=True)
    top = df_result.iloc[0]
    st.subheader(f"🎯 افضل فرصة: {top['symbol']} - سكور {top['score']}")
    st.metric("افضل دخول", f"{top['best_entry']:.6f}")
    st.metric("نقطة الالغاء No Return", f"{top['no_return_point']:.6f}")
else:
    st.warning("مفيش عملات فوق السكور المطلوب - قلل السكور لـ 50")

st.divider()
st.markdown("**تنبيه تعليمي - التداول مخاطرة**")
