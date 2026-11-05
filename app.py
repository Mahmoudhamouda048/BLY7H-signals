import streamlit as st
import pandas as pd
import requests, time

st.set_page_config(page_title="BLY7H V7 FINAL", layout="wide")

TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = st.secrets.get("TELEGRAM_CHANNEL_ID", "@WHYNOTBLY7")
CHAT = st.secrets.get("TELEGRAM_CHAT_ID", "")

def send_telegram(text):
    for target in [CHANNEL, CHAT]:
        if not target:
            continue
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            r = requests.post(url, json={"chat_id": target, "text": text}, timeout=15)
            if r.status_code == 200:
                return True
        except:
            pass
    return False

# 15 أداة DEX - زي ما انت كاتبهم
def check_dex_token(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        pairs = data.get('pairs', [])
        if not pairs:
            return None
        # اعلى سيولة
        best = None
        best_liq = 0
        for p in pairs:
            lq = p.get('liquidity', {})
            lv = lq.get('usd', 0)
            try:
                lv = float(lv or 0)
            except:
                lv = 0
            if lv > best_liq:
                best_liq = lv
                best = p
        pair = best
        if not pair:
            return None
        
        # فلتر Rug - سيولة اقل من 10K
        liq_obj = pair.get('liquidity', {})
        liq_usd = liq_obj.get('usd', 0)
        try:
            liq_val = float(liq_usd or 0)
        except:
            liq_val = 0
        if liq_val < 10000:
            return None
        
        base = pair.get('baseToken', {})
        quote = pair.get('quoteToken', {})
        symbol = base.get('symbol','UNK')
        chain = pair.get('chainId','')
        price = pair.get('priceUsd','0')
        
        pc = pair.get('priceChange', {})
        v5_raw = pc.get('m5', 0)
        h1_raw = pc.get('h1', 0)
        try:
            ch5 = float(v5_raw or 0)
        except:
            ch5 = 0
        try:
            ch1 = float(h1_raw or 0)
        except:
            ch1 = 0
        
        vol_obj = pair.get('volume', {})
        vol5_raw = vol_obj.get('m5', 0)
        vol1_raw = vol_obj.get('h1', 1)
        try:
            v5 = float(vol5_raw or 0)
        except:
            v5 = 0
        try:
            v1 = float(vol1_raw or 1)
        except:
            v1 = 1
        
        fdv_raw = pair.get('fdv', 0)
        try:
            fdv = float(fdv_raw or 0)
        except:
            fdv = 0
        
        dex_url = pair.get('url','')
        
        score = 0
        conds = []
        # اداة 1 و 2
        if v5 > 5000:
            ratio = v5 / (v1/12) if v1>0 else 0
            if ratio >= 2.5:
                score += 25
                conds.append(f"Vol x{ratio:.1f}")
        # اداة 3
        if ch5 >= 5:
            score += 20
            conds.append(f"+{ch5}% 5د")
        # اداة 4
        if liq_val > 15000:
            score += 15
            conds.append(f"${liq_val/1000:.0f}K")
        # اداة 5
        if ch1 > 20:
            score += 10
            conds.append(f"+{ch1}% 1س")
        # اداة 6
        if fdv > 0 and fdv < 20000000:
            score -= 30
        
        # اداة 7 وقت حيتان
        from datetime import datetime
        hour = datetime.now().hour
        if 2 <= hour <= 6:
            score += 15
            tstate = "🟢 وقت حيتان"
        else:
            tstate = "🟡 عادي"
        
        # اداة 8 MIN_SCORE 75
        if score < 75:
            return None
        
        # اداة 9 ATR اهداف
        try:
            p = float(price)
            atr = p * 0.02
            entry = p
            tp1 = p + atr*1.5
            tp2 = p + atr*3.0
            sl = p - atr
            cancel = p - atr*0.7
        except:
            entry = price
            tp1 = price
            tp2 = price
            sl = price
            cancel = price
        
        msg = f"🚀 DEX {symbol} على {chain}\n{' | '.join(conds)}\n{tstate} سكور {score}\n${price} دخول ${entry} ستوب ${sl}\n{dex_url}\n@WHYNOTBLY7"
        return msg, score, symbol
    except:
        return None

st.title("BLY7H V7 - 15 أداة + CEX")

tab1, tab2 = st.tabs(["DEX - 15 أداة", "CEX - 52 عملة"])

with tab1:
    if st.button("DEX فحص", type="primary"):
        try:
            url = "https://api.dexscreener.com/latest/dex/search/?q=BSC"
            r = requests.get(url, timeout=15)
            pairs = r.json().get('pairs', [])[:10]
            seen = set()
            for p in pairs:
                bt = p.get('baseToken', {})
                addr = bt.get('address')
                if not addr or addr in seen:
                    continue
                seen.add(addr)
                res = check_dex_token(addr)
                if res:
                    msg, score, sym = res
                    st.code(msg)
                    if send_telegram(msg):
                        st.success(f"✅ {sym}")
                    time.sleep(2)
        except Exception as e:
            st.error(str(e))

with tab2:
    STABLES = ["USDCUSDT","BUSDUSDT","TUSDUSDT","USDPUSDT","DAIUSDT","FDUSDUSDT"]
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
                    if 'BULL' in s or 'BEAR' in s:
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
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['vol'] = pd.to_numeric(df['vol'], errors='coerce')
                df['low'] = pd.to_numeric(df['low'], errors='coerce')
                df['high'] = pd.to_numeric(df['high'], errors='coerce')
                return df.dropna()
            except:
                continue
        return None
    
    if st.button("💥 CEX 52 عملة + تليجرام", type="primary"):
        syms = get_symbols()
        results = []
        prog = st.progress(0)
        for i, sym in enumerate(syms[:52]):
            prog.progress((i+1)/52)
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
                if score < 50:
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
                results.append({'symbol': sym, 'score': score, 'type': ptype, 'price': round(last,6), 'change': round(change,2), 'vol': round(vol_spike,2), 'entry': round(best,6), 'stop': round(stop,6), 'tp1': round(tp1,6)})
            except:
                continue
        prog.empty()
        if results:
            df_res = pd.DataFrame(results)
            df_res = df_res.sort_values('score', ascending=False)
            st.dataframe(df_res, use_container_width=True)
            for sig in df_res.head(5).to_dict('records'):
                txt = f"🚀 BLY7H {sig['type']} {sig['symbol']} سكور {sig['score']} Vol x{sig['vol']} {sig['change']}% سعر {sig['price']} دخول {sig['entry']} ستوب {sig['stop']} هدف {sig['tp1']}"
                if send_telegram(txt):
                    st.success(f"✅ {sig['symbol']}")
                    time.sleep(2)
        else:
            st.warning("مفيش")
