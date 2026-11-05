import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="BLY7H Signals", layout="wide", page_icon="🚀")
st.title("🚀 BLY7H Signals - Ultimate Scanner")

st.sidebar.header("⚙️ الاعدادات")
min_score = st.sidebar.slider("اقل سكور يظهر", 0, 100, 10)

BINANCE_URLS = [
    "https://data-api.binance.vision",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api.binance.com"
]

@st.cache_data(ttl=60)
def get_top_coins():
    for base in BINANCE_URLS:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            if not isinstance(data, list):
                continue
            usdt = [d for d in data if d.get('symbol','').endswith('USDT')]
            sorted_coins = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0) or 0), reverse=True)[:20]
            coins = [c['symbol'] for c in sorted_coins if c.get('symbol')]
            if coins:
                return coins
        except:
            continue
    return ['BTCUSDT','ETHUSDT','BNBUDT','SOLUSDT','XRPUSDT','PEPEUSDT','WIFUSDT','BONKUSDT','SHIBUSDT','DOGEUSDT']

@st.cache_data(ttl=60)
def get_klines(symbol):
    for base in BINANCE_URLS:
        try:
            url = f"{base}/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            if not data or len(data) < 5:
                continue
            df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            for col in ['high','low','close']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.dropna()
            if len(df) >= 5:
                return df
        except:
            continue
    return None

def calc_score(df, symbol):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change = ((last-prev)/prev*100) if prev else 0
        score = 35
        best_entry = last * 0.995
        no_return = float(df['low'].min()) * 0.98
        return {
            'symbol': symbol,
            'score': score,
            'price': last,
            'change_1h': round(change,2),
            'best_entry': best_entry,
            'no_return_point': no_return,
            'stop_loss': no_return*0.998,
            'take_profit_1': best_entry*1.02,
            'take_profit_2': best_entry*1.05,
        }
    except:
        return None

st.info(f"⏰ اخر تحديث: {datetime.now().strftime('%H:%M:%S %d-%m-%Y')}")
if st.button("🔍 افحص الان", type="primary"):
    st.cache_data.clear()
    st.rerun()

coins = get_top_coins()
st.write(f"تم جلب {len(coins)} عملة - اول 3: {coins[:3]}")

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
    st.subheader(f"🎯 افضل فرصة: {top['symbol']} - سكور {top['score']}")
    c1,c2 = st.columns(2)
    c1.metric("افضل دخول", f"{top['best_entry']:.6f}")
    c2.metric("نقطة الالغاء", f"{top['no_return_point']:.6f}")
else:
    st.error("Binance API محظور مؤقتا - جرب دوس افحص الان تاني")
    st.write("العملات:", coins)
