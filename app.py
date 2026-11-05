import streamlit as st
import pandas as pd
import requests, time
from datetime import datetime

st.set_page_config(page_title="BLY7H V7 FINAL", layout="wide", page_icon="🚀")

TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = st.secrets.get("TELEGRAM_CHANNEL_ID", "@WHYNOTBLY7")
CHAT = st.secrets.get("TELEGRAM_CHAT_ID", "")

def send_telegram(text):
    # يجرب القناة والخاص - واحد فيهم هيشتغل
    for target in [CHANNEL, CHAT]:
        if not target:
            continue
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            r = requests.post(url, json={"chat_id": target, "text": text}, timeout=15)
            if r.status_code == 200:
                return True
        except:
            continue
    return False

st.title("🚀 BLY7H V7 FINAL")

tab1, tab2 = st.tabs(["🚀 DEX", "💥 CEX"])

with tab1:
    if st.button("🔍 DEX"):
        try:
            url = "https://api.dexscreener.com/latest/dex/search/?q=BSC"
            r = requests.get(url, timeout=15)
            pairs = r.json().get('pairs', [])[:10]
            for p in pairs:
                sym = p.get('baseToken',{}).get('symbol','UNK')
                price = p.get('priceUsd','0')
                ch5 = float(p.get('priceChange',{}).get('m5',0) or 0)
                v5 = float(p.get('volume',{}).get('m5',0) or 0)
                liq = float(p.get('liquidity',{}).get('usd',0) or 0)
                if v5 > 5000 and ch5 >= 5 and liq > 15000:
                    msg = f"🚀 DEX {sym} ${price} +{ch5}% Vol ${v5} @WHYNOTBLY7\n{p.get('url','')}"
                    st.code(msg)
                    if send_telegram(msg):
                        st.success(f"✅ اتبعت {sym}")
                    time.sleep(2)
        except Exception as e:
            st.error(str(e))

with tab2:
    STABLES = ["USDCUSDT","BUSDUSDT","TUSDUSDT","USDPUSDT","DAIUSDT","FDUSDUSDT","USDeUSDT","USD1USDT","RLUSDUSDT","XUSDUSDT","EURUSDT","PYUSDUSDT","GUSDUSDT","USDXUSDT"]
    
    def get_symbols():
        for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
            try:
                r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
                if r.status_code != 200: continue
                data = r.json()
                usdt = [d for d in data if d.get('symbol','').endswith('USDT')]
                usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume') or 0), reverse=True)
                syms = [d['symbol'] for d in usdt_sorted[:60]]
                return [s for s in syms if s not in STABLES and 'BULL' not in s and 'BEAR' not in s]
            except: continue
        return []

    @st.cache_data(ttl=60)
    def get_klines(sym):
        for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
            try:
                r = requests.get(f"{base}/api/v3/klines?symbol={sym}&interval=1h&limit=50", timeout=10)
                if r.status_code != 200: continue
                data = r.json()
                if len(data) < 20: continue
                df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
                for c in ['high','low','close','open','vol']:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
                return df.dropna()
            except: continue
        return None

    min_score = st.slider("اقل سكور", 0, 100, 50)
    limit = st.slider("عدد العملات", 20, 100, 52)
    
    if st.button("💥 افحص CEX + ابعت تليجرام", type="primary"):
        symbols = get_symbols()
        results = []
        prog = st.progress(0)
        for i, sym in enumerate(symbols[:limit]):
            prog.progress((i+1)/limit)
            df = get_klines(sym)
            if df is None: continue
            try:
                last = float(df['close'].iloc[-1])
                prev = float(df['close'].iloc[-2])
                change = (last - prev)/prev*100 if prev!=0 else 0
                mean_vol = float(df['vol'].iloc[-20:-1].mean())
                last_vol = float(df['vol'].iloc[-1])
                vol_spike = last_vol / mean_vol if mean_vol>0 else 1
                if vol_spike < 1.8 and abs(change) < 1.5: continue
                score = 40 + min(vol_spike*5, 20) if change > -1 else 35 + abs(change)*2 + vol_spike*2
                score = min(int(score), 99)
                if score < min_score: continue
                ptype = "PUMP" if change > -1 else "DUMP"
                rec_low = float(df['low'].iloc[-10:].min())
                rec_high = float(df['high'].iloc[-10:].max())
                if ptype == "PUMP":
                    best = last * 0.995
                    stop = rec_low * 0.98
                    tp1 = last * 1.04
                    tp2 = last * 1.08
                else:
                    best = last * 1.005
                    stop = rec_high * 1.02
                    tp1 = last * 0.96
                    tp2 = last * 0.92
                results.append({'symbol': sym, 'score': score, 'type': ptype, 'price': round(last,6), 'change_1h': round(change,2), 'vol_spike': round(vol_spike,2), 'best_entry': round(best,6), 'stop_loss': round(stop,6), 'TP1': round(tp1,6), 'TP2': round(tp2,6)})
            except: continue
        prog.empty()
        if results:
            df_res = pd.DataFrame(results).sort_values('score', ascending=False)
            st.dataframe(df_res, use_container_width=True)
            sent = 0
            for sig in df_res.head(8).to_dict('records'):
                txt = f"🚀 BLY7H {sig['type']} {sig['symbol']}\nسكور {sig['score']} Vol x{sig['vol_spike']} {sig['change_1h']}%\nسعر {sig['price']} دخول {sig['best_entry']} ستوب {sig['stop_loss']} هدف {sig['TP1']}"
                if send_telegram(txt):
                    st.success(f"✅ اتبعت {sig['symbol']}")
                    sent += 1
                    time.sleep(2)
            st.success(f"اتبعت {sent}!")
        else:
            st.warning("مفيش")
