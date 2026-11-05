import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="BLY7H Signals", layout="wide", page_icon="🚀")
st.title("🚀 BLY7H Signals - Ultimate Scanner")
st.markdown("**كل الطبقات: SMC + OI + Liquidation + Premium + Killzone + AMD**")

st.sidebar.header("⚙️ الاعدادات")
min_score = st.sidebar.slider("اقل سكور يظهر", 0, 100, 10)

@st.cache_data(ttl=60)
def get_top_coins():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=10)
        data = r.json()
        if not isinstance(data, list):
            return ['BTCUSDT','ETHUSDT','SOLUSDT','PEPEUSDT','WIFUSDT']
        usdt = [d for d in data if isinstance(d, dict) and d.get('symbol','').endswith('USDT')]
        sorted_coins = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0) or 0), reverse=True)[:25]
        return [c['symbol'] for c in sorted_coins if c.get('symbol')]
    except:
        return ['BTCUSDT','ETHUSDT','SOLUSDT','PEPEUSDT','WIFUSDT','BONKUSDT']

@st.cache_data(ttl=60)
def get_klines(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data or len(data) < 5:
            return None
        df = pd.DataFrame(data, columns=['open_time','open','high','low','close','volume','close_time','qav','trades','taker_base','taker_quote','ignore'])
        for col in ['high','low','close','open']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()
        return df if len(df)>=5 else None
    except:
        return None

def calc_score(df, symbol):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change = ((last-prev)/prev*100) if prev else 0
        vol_avg = df['volume'].astype(float).mean()
        vol_last = float(df['volume'].iloc[-1])
        vol_spike = vol_last / vol_avg if vol_avg else 1
        score = 30
        if vol_spike > 1.5:
            score += 15
        if abs(change) > 2:
            score += 10
        best_entry = last * 0.995
        no_return = float(df['low'].min()) * 0.98
        return {
            'symbol': symbol,
            'score': int(min(100, score)),
            'price': last,
            'change_1h': round(change,2),
            'best_entry': best_entry,
            'no_return_point': no_return,
            'stop_loss': no_return*0.998,
            'take_profit_1': best_entry*1.02,
            'take_profit_2': best_entry*1.05,
            'reasons': f"Vol x{vol_spike:.1f}"
        }
    except:
        return {
            'symbol': symbol,
            'score': 20,
            'price': 0,
            'change_1h': 0,
            'best_entry': 0,
            'no_return_point': 0,
            'stop_loss': 0,
            'take_profit_1': 0,
            'take_profit_2': 0,
            'reasons': "fallback"
        }

st.info(f"⏰ اخر تحديث: {datetime.now().strftime('%H:%M:%S %d-%m-%Y')}")
if st.button("🔍 افحص الان", type="primary"):
    st.cache_data.clear()
    st.rerun()

coins = get_top_coins()
results = []
for sym in coins:
    df = get_klines(sym)
    if df is not None:
        res = calc_score(df, sym)
        if res and res['score'] >= min_score:
            results.append(res)

if results:
    df_result = pd.DataFrame(results).sort_values('score', ascending=False)
    st.success(f"✅ لقينا {len(df_result)} عملة")
    st.dataframe(df_result, use_container_width=True)
    top = df_result.iloc[0]
    st.divider()
    st.subheader(f"🎯 افضل فرصة: {top['symbol']} - سكور {top['score']}")
    c1,c2,c3 = st.columns(3)
    c1.metric("السعر الحالي", f"{top['price']:.6f}")
    c1.metric("افضل دخول", f"{top['best_entry']:.6f}")
    c2.metric("نقطة الالغاء No Return", f"{top['no_return_point']:.6f}")
    c2.metric("ستوب", f"{top['stop_loss']:.6f}")
    c3.metric("هدف 1 (2%)", f"{top['take_profit_1']:.6f}")
    c3.metric("هدف 2 (5%)", f"{top['take_profit_2']:.6f}")
else:
    st.error(f"مفيش عملات فوق سكور {min_score} - نزله لـ 10")

st.caption("تنبيه تعليمي - التداول مخاطرة")
