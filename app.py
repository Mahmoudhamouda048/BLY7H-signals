import streamlit as st
import pandas as pd
import requests, time

st.set_page_config(page_title="BLY7H V7", layout="wide")

TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = st.secrets.get("TELEGRAM_CHANNEL_ID", "@WHYNOTBLY7")
CHAT = st.secrets.get("TELEGRAM_CHAT_ID", "")

def send_telegram(text):
    ok = False
    for target in [CHANNEL, CHAT]:
        if not target:
            continue
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            r = requests.post(url, json={"chat_id": target, "text": text}, timeout=15)
            if r.status_code == 200:
                ok = True
        except:
            pass
    return ok

st.title("BLY7H V7 FINAL")

STABLES = ["USDCUSDT","BUSDUSDT","TUSDUSDT","USDPUSDT","DAIUSDT","FDUSDUSDT","USDeUSDT","USD1USDT","RLUSDUSDT","XUSDUSDT"]

def get_symbols():
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            usdt = []
            for d in data:
                if d.get('symbol','').endswith('USDT'):
                    usdt.append(d)
            usdt = sorted(usdt, key=lambda x: float(x.get('quoteVolume') or 0), reverse=True)
            syms = []
            for d in usdt[:60]:
                syms.append(d['symbol'])
            clean = []
            for s in syms:
                if s in STABLES:
                    continue
                if 'BULL' in s:
                    continue
                if 'BEAR' in s:
                    continue
                clean.append(s)
            return clean
        except:
            continue
    return []

def get_klines(sym):
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={sym}&interval=1h&limit=50", timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            if len(data) < 20:
                continue
            df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['vol'] = pd.to_numeric(df['vol'], errors='coerce')
            return df.dropna()
        except:
            continue
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
        if df is None:
            continue
        try:
            last = float(df['close'].iloc[-1])
            prev = float(df['close'].iloc[-2])
            if prev == 0:
                continue
            change = (last - prev) / prev * 100
            mean_vol = float(df['vol'].iloc[-20:-1].mean())
            last_vol = float(df['vol'].iloc[-1])
            if mean_vol == 0:
                continue
            vol_spike = last_vol / mean_vol
            if vol_spike < 1.8 and abs(change) < 1.5:
                continue
            if change > -1:
                score = 40 + min(vol_spike*5, 20)
                ptype = "PUMP"
            else:
                score = 35 + abs(change)*2 + vol_spike*2
                ptype = "DUMP"
            score = min(int(score), 99)
            if score < min_score:
                continue
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
            results.append({
                'symbol': sym,
                'score': score,
                'type': ptype,
                'price': round(last,6),
                'change_1h': round(change,2),
                'vol_spike': round(vol_spike,2),
                'best_entry': round(best,6),
                'stop_loss': round(stop,6),
                'TP1': round(tp1,6),
                'TP2': round(tp2,6)
            })
        except:
            continue
    prog.empty()
    if results:
        df_res = pd.DataFrame(results)
        df_res = df_res.sort_values('score', ascending=False)
        st.dataframe(df_res, use_container_width=True)
        sent = 0
        for sig in df_res.head(8).to_dict('records'):
            txt = f"🚀 BLY7H {sig['type']} {sig['symbol']} سكور {sig['score']} Vol x{sig['vol_spike']} {sig['change_1h']}% سعر {sig['price']} دخول {sig['best_entry']} ستوب {sig['stop_loss']} هدف {sig['TP1']}"
            if send_telegram(txt):
                st.success(f"✅ اتبعت {sig['symbol']}")
                sent += 1
                time.sleep(2)
        st.success(f"اتبعت {sent} اشارات!")
    else:
        st.warning("مفيش نتائج")
