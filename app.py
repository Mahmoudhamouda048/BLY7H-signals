import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

st.set_page_config(page_title="BLY7H Signals - Multi Source", layout="wide", page_icon="🚀")
st.title("🚀 BLY7H Signals - Multi Source Scanner")
st.markdown("**【entity-Binance¦canonical_name=Binance】 + 【entity-OKX¦canonical_name=OKX】 + 【entity-Bybit¦canonical_name=Bybit】 + 【entity-KuCoin¦canonical_name=KuCoin】 - لو واحد اتحظر يجيب من التاني اوتوماتيك**")

st.sidebar.header("⚙️ الاعدادات")
min_score = st.sidebar.slider("اقل سكور يظهر", 0, 100, 35)
source_choice = st.sidebar.selectbox("المصدر المفضل", ["Auto (يجرب كله)", "【entity-Binance¦canonical_name=Binance】", "【entity-OKX¦canonical_name=OKX】", "【entity-Bybit¦canonical_name=Bybit】"])

TOP_COINS = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','DOGEUSDT','PEPEUSDT','WIFUSDT','BONKUSDT','AVAXUSDT','ADAUSDT','DOTUSDT','LINKUSDT','MATICUSDT','LTCUSDT','TRXUSDT','NEARUSDT','APTUSDT','ARBUSDT','SUIUSDT']

def symbol_for_okx(sym):
    # BTCUSDT -> BTC-USDT
    return sym.replace('USDT','-USDT')

def get_klines_binance(symbol):
    bases = ["https://data-api.binance.vision","https://api1.binance.com","https://api2.binance.com"]
    for base in bases:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={symbol}&interval=1h&limit=50", timeout=10)
            if r.status_code != 200: continue
            data = r.json()
            if len(data) < 10: continue
            df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            for c in ['high','low','close','open']: df[c]=pd.to_numeric(df[c], errors='coerce')
            return df.dropna()
        except: continue
    return None

def get_klines_okx(symbol):
    try:
        inst = symbol_for_okx(symbol)
        url = f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=1H&limit=50"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('code')!='0': return None
        klines = data.get('data',[])
        if len(klines)<10: return None
        # OKX ترتيبها معكوس
        klines = list(reversed(klines))
        df = pd.DataFrame(klines, columns=['ts','open','high','low','close','vol','volCcy','volCcyQuote','confirm'])
        for c in ['high','low','close','open']: df[c]=pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except: return None

def get_klines_bybit(symbol):
    try:
        url = f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval=60&limit=50"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get('retCode')!=0: return None
        klines = data.get('result',{}).get('list',[])
        if len(klines)<10: return None
        klines = list(reversed(klines))
        df = pd.DataFrame(klines, columns=['start','open','high','low','close','volume','turnover'])
        for c in ['high','low','close','open']: df[c]=pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except: return None

@st.cache_data(ttl=90)
def get_klines_multi(symbol, pref="Auto"):
    sources = []
    if pref=="Binance": sources=["binance","okx","bybit"]
    elif pref=="OKX": sources=["okx","bybit","binance"]
    elif pref=="Bybit": sources=["bybit","binance","okx"]
    else: sources=["binance","okx","bybit"] # Auto
    
    for src in sources:
        df=None
        if src=="binance": df=get_klines_binance(symbol)
        elif src=="okx": df=get_klines_okx(symbol)
        elif src=="bybit": df=get_klines_bybit(symbol)
        if df is not None and len(df)>=10:
            return df, src
    return None, "none"

def calc_score(df, symbol, source):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change = ((last-prev)/prev*100) if prev else 0
        low_50 = float(df['low'].min())
        score = 35
        if abs(change)>1.2: score+=15
        if last>float(df['close'].iloc[-5:].mean()): score+=10
        # FVG
        for i in range(1,len(df)-1):
            try:
                if float(df['low'].iloc[i+1])>float(df['high'].iloc[i-1]): 
                    score+=15; break
            except: pass
        
        best = last*0.992
        no_ret = low_50*0.98
        return {
            'symbol': symbol,
            'score': min(95,score),
            'source': source,
            'price': round(last,6),
            'change_1h': round(change,2),
            'best_entry': round(best,6),
            'no_return_point': round(no_ret,6),
            'stop_loss': round(no_ret*0.998,6),
            'TP1': round(best*1.025,6),
            'TP2': round(best*1.06,6),
        }
    except: return None

st.info(f"⏰ {datetime.now().strftime('%H:%M:%S')} - بيفحص {len(TOP_COINS)} عملة من {source_choice}")

if st.button("🔍 افحص الان", type="primary"):
    st.cache_data.clear()
    st.rerun()

results=[]
progress=st.progress(0)
status=st.empty()

for i,sym in enumerate(TOP_COINS):
    progress.progress((i+1)/len(TOP_COINS))
    status.text(f"يفحص {sym}...")
    df, src = get_klines_multi(sym, source_choice if source_choice!="Auto (يجرب كله)" else "Auto")
    if df is not None:
        res=calc_score(df,sym,src)
        if res and res['score']>=min_score:
            results.append(res)
    time.sleep(0.15)

progress.empty()
status.empty()

if results:
    df_res=pd.DataFrame(results).sort_values('score',ascending=False)
    st.success(f"✅ لقينا {len(df_res)} عملة - مصادر متعددة شغالة")
    st.dataframe(df_res, use_container_width=True)
    top=df_res.iloc[0]
    st.divider()
    st.subheader(f"🎯 افضل فرصة: {top['symbol']} من {top['source']} - سكور {top['score']}")
    c1,c2,c3=st.columns(3)
    c1.metric("السعر", f"{top['price']}")
    c1.metric("افضل دخول", f"{top['best_entry']}")
    c2.metric("نقطة الالغاء", f"{top['no_return_point']}")
    c2.metric("ستوب", f"{top['stop_loss']}")
    c3.metric("هدف 1", f"{top['TP1']}")
    c3.metric("هدف 2", f"{top['TP2']}")
else:
    st.error(f"مفيش عملات فوق سكور {min_score} - نزله لـ 20")
    st.caption("جرب تغير المصدر من السايدبار لـ OKX او Bybit")

st.caption("Multi-Source: لو Binance محظور هيجيب من OKX/Bybit اوتوماتيك")
