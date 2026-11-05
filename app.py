import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time, json, os, math

st.set_page_config(page_title="BLY7H ULTIMATE", layout="wide", page_icon="🚀")
st.title("🚀 BLY7H ULTIMATE - CEX + DEX قبل الحركة")

st.sidebar.header("Settings")
min_score = st.sidebar.slider("اقل سكور", 0, 100, 55)
limit_coins = st.sidebar.slider("عدد العملات", 20, 200, 80)
filter_stable = st.sidebar.checkbox("فلتر المستقرة", value=True)
send_tg = st.sidebar.checkbox("تليجرام", value=True)
tg_min = st.sidebar.slider("سكور التليجرام", 20, 95, 70)

STABLES = ["USDCUSDT","BUSDUSDT","TUSDUSDT","USDPUSDT","DAIUSDT","FDUSDUSDT","USDeUSDT","USD1USDT","RLUSDUSDT","XUSDUSDT","EURUSDT","PYUSDUSDT","GUSDUSDT"]

def send_tg_alert(text):
    try:
        bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN")
        chat_id = st.secrets.get("TELEGRAM_CHANNEL_ID", st.secrets.get("TELEGRAM_CHAT_ID"))
        if not bot_token or not chat_id:
            return False
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 429:
            retry = r.json().get('parameters',{}).get('retry_after',30)
            time.sleep(retry+2)
            return send_tg_alert(text)
        return r.status_code == 200
    except:
        return False

# ========== CEX FUNCTIONS ==========
def get_oi_change(sym):
    try:
        r = requests.get(f"https://fapi.binance.com/futures/data/openInterestHist?symbol={sym}&period=5m&limit=12", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if len(data) >= 2:
                first = float(data[0]['sumOpenInterest'])
                last = float(data[-1]['sumOpenInterest'])
                change = (last - first) / first * 100 if first>0 else 0
                return change
    except:
        pass
    return 0

def calc_cvd(df):
    try:
        green = 0
        red = 0
        for i in range(-10, 0):
            c = float(df['close'].iloc[i])
            o = float(df['open'].iloc[i])
            v = float(df['vol'].iloc[i])
            if c > o:
                green += v
            else:
                red += v
        total = green + red
        if total == 0:
            return 0, "متوازن"
        pct = (green - red) / total * 100
        if pct > 30:
            return 15, f"CVD +{pct:.0f}% شراء قوي"
        elif pct < -30:
            return 15, f"CVD {pct:.0f}% بيع قوي"
        elif pct > 15:
            return 8, f"CVD +{pct:.0f}% شراء"
        elif pct < -15:
            return 8, f"CVD {pct:.0f}% بيع"
        else:
            return 0, f"CVD {pct:.0f}%"
    except:
        return 0, "CVD"

def calc_smc(df, price):
    try:
        bull_b = bull_m = bear_b = bear_m = bear_t = None
        for i in range(1, len(df)-1):
            try:
                low_next = float(df['low'].iloc[i+1])
                high_prev = float(df['high'].iloc[i-1])
                high_next = float(df['high'].iloc[i+1])
                low_prev = float(df['low'].iloc[i-1])
                if low_next > high_prev and bull_b is None:
                    bull_b = high_prev
                    bull_m = (high_prev + low_next)/2
                if high_next < low_prev and bear_b is None:
                    bear_b = high_next
                    bear_t = low_prev
                    bear_m = (high_next + low_prev)/2
            except:
                pass
        recent_low = float(df['low'].iloc[-10:].min())
        recent_high = float(df['high'].iloc[-10:].max())
        fvg_data = {'bull_b': bull_b, 'bull_m': bull_m, 'bear_b': bear_b, 'bear_m': bear_m, 'bear_t': bear_t}
        has_fvg = bull_b is not None or bear_b is not None
        return has_fvg, fvg_data, recent_low, recent_high
    except:
        return False, {}, price*0.99, price*1.01

def get_symbols_binance():
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            usdt = []
            for d in data:
                sym = d.get('symbol','')
                if sym.endswith('USDT'):
                    usdt.append(d)
            usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume') or 0), reverse=True)
            res = []
            for d in usdt_sorted[:400]:
                res.append(d['symbol'])
            return res
        except:
            continue
    return []

@st.cache_data(ttl=300)
def get_all_symbols():
    s = get_symbols_binance()
    clean = []
    for x in s:
        if 'BULL' not in x and 'BEAR' not in x:
            if filter_stable and x in STABLES:
                continue
            clean.append(x)
    return clean[:400], " binance"

def get_klines_binance(sym):
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={sym}&interval=1h&limit=100", timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            if len(data) < 20:
                continue
            df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            for c in ['high','low','close','open']:
                df[c] = pd.to_numeric(df[c], errors='coerce')
            return df.dropna()
        except:
            continue
    return None

@st.cache_data(ttl=90)
def get_klines(sym):
    df = get_klines_binance(sym)
    if df is not None and len(df) >= 20:
        return df
    return None

def pump_dump_predictive(df, sym):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change_1h = (last - prev)/prev*100 if prev!=0 else 0
        col = 'vol' if 'vol' in df.columns else 'volume'
        mean_vol = df[col].astype(float).iloc[-20:-1].mean()
        last_vol = float(df[col].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol>0 else 1
        oi_change = get_oi_change(sym)
        cvd_score, cvd_reason = calc_cvd(df)
        has_fvg, fvg_data, rec_low, rec_high = calc_smc(df, last)
        
        if vol_spike < 1.5 and abs(oi_change) < 2 and cvd_score < 5:
            return None
        
        score = 0
        if vol_spike > 2.0 or oi_change > 3 or cvd_score > 8:
            if change_1h > -1:
                score = 40 + (15 if oi_change>3 else 0) + cvd_score + min(vol_spike*3, 15)
                ptype = "PUMP"
                vol_reason = f"PUMP قبل OI {oi_change:.1f}% Vol x{vol_spike:.1f}"
            else:
                score = 30 + vol_spike*3 + abs(change_1h)
                ptype = "DUMP"
                vol_reason = f"DUMP Vol x{vol_spike:.1f}"
        elif change_1h < -1.5 and vol_spike > 1.8:
            score = 35 + abs(change_1h)*2 + vol_spike*2
            ptype = "DUMP"
            vol_reason = f"DUMP حقيقي Vol x{vol_spike:.1f}"
        else:
            return None
        
        if has_fvg:
            score += 10
        score = min(int(score), 99)
        if score < min_score:
            return None
        
        bull_b = fvg_data.get('bull_b')
        bull_m = fvg_data.get('bull_m')
        bear_b = fvg_data.get('bear_b')
        bear_m = fvg_data.get('bear_m')
        bear_t = fvg_data.get('bear_t')
        
        if ptype == "PUMP":
            best = bull_m if bull_m is not None else last * 0.993
            no_ret = bull_b * 0.985 if bull_b else rec_low * 0.98
            best = min(best, last * 0.998)
            stop = no_ret * 0.99
            tp1 = last * 1.04
            tp2 = last * 1.08
            if stop >= best:
                stop = best * 0.97
        else:
            best = bear_m if bear_m is not None else last * 1.007
            no_ret = bear_t * 1.015 if bear_t else rec_high * 1.02
            best = max(best, last * 1.002)
            stop = no_ret * 1.01
            tp1 = last * 0.96
            tp2 = last * 0.92
            if stop <= best:
                stop = best * 1.03
        
        return {
            'symbol': sym, 'score': score, 'type': ptype, 'price': round(last,6),
            'change_1h': round(change_1h,2), 'vol_spike': round(vol_spike,2),
            'oi_change': round(oi_change,2), 'best_entry': round(best,6),
            'no_return_point': round(no_ret,6), 'stop_loss': round(stop,6),
            'TP1': round(tp1,6), 'TP2': round(tp2,6), 'vol_reason': vol_reason,
            'oi_reason': f"OI {oi_change:.1f}%", 'cvd_reason': cvd_reason
        }
    except:
        return None

# ========== DEX FUNCTIONS ==========
def check_dex_pump(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        r = requests.get(url, timeout=10)
        pairs = r.json().get('pairs', [])
        if not pairs:
            return None
        pair = sorted(pairs, key=lambda x: float(x.get('liquidity',{}).get('usd',0)), reverse=True)[0]
        symbol = pair.get('baseToken',{}).get('symbol','UNK')
        chain = pair.get('chainId','').upper()
        price = pair.get('priceUsd','0')
        change_5m = float(pair.get('priceChange',{}).get('m5',0))
        vol_5m = float(pair.get('volume',{}).get('m5',0))
        vol_1h = float(pair.get('volume',{}).get('h1',1))
        liquidity = float(pair.get('liquidity',{}).get('usd',0))
        dex_url = pair.get('url','')
        score = 0
        conds = []
        if vol_5m > 5000:
            ratio = vol_5m / (vol_1h/12) if vol_1h>0 else 0
            if ratio >= 2.5:
                score += 25
                conds.append(f"Vol x{ratio:.1f}")
        if change_5m >= 5:
            score += 20
            conds.append(f"+{change_5m}% 5د")
        if liquidity > 15000:
            score += 15
            conds.append(f"${liquidity/1000:.0f}K")
        if score < min_score:
            return None
        p = float(price)
        msg = f"🚀 DEX EARLY PUMP - {symbol} على {chain}\n📊 {' | '.join(conds)} سكور {score}\n💵 {price} دخول {p} الغاء {p*0.97:.8f} ستوب {p*0.95:.8f} هدف {p*1.3:.8f}\n🔗 {dex_url}\n@WHYNOTBLY7"
        return msg, score, symbol
    except:
        return None

# ========== UI TABS ==========
tab1, tab2 = st.tabs(["💥 CEX PUMP DUMP (OI + CVD)", "🚀 DEX EARLY (قبل المنصات)"])

with tab1:
    st.subheader("CEX - تنبؤ قبل الحركة OI + CVD + Vol")
    if st.button("💥 افحص CEX", type="primary", key="cex"):
        st.cache_data.clear()
        st.rerun()
    
    symbols, src = get_all_symbols()
    st.write(f"تم جلب {len(symbols)} عملة - هيفحص اول {limit_coins}")
    to_scan = symbols[:limit_coins]
    results = []
    prog = st.progress(0)
    stat = st.empty()
    for i, sym in enumerate(to_scan):
        prog.progress((i+1)/len(to_scan))
        stat.text(f"CEX: {sym} {i+1}/{len(to_scan)}")
        df = get_klines(sym)
        if df is not None:
            res = pump_dump_predictive(df, sym)
            if res:
                results.append(res)
        time.sleep(0.05)
    prog.empty()
    stat.empty()
    
    if results:
        df_res = pd.DataFrame(results).sort_values('score', ascending=False)
        st.success(f"💥 {len(df_res)} تنبؤ CEX")
        st.dataframe(df_res, use_container_width=True)
        if send_tg:
            sent = 0
            for sig in df_res.head(5).to_dict('records'):
                txt = f"🚀 BLY7H {sig['type']} {sig['symbol']} قبل الحركة!\nسكور {sig['score']} Vol x{sig['vol_spike']} OI {sig['oi_change']}%\nسعر {sig['price']} دخول {sig['best_entry']} ستوب {sig['stop_loss']} هدف {sig['TP1']}"
                if send_tg_alert(txt):
                    sent += 1
                    time.sleep(1)
            if sent > 0:
                st.success(f"اتبعت {sent} للتليجرام!")

with tab2:
    st.subheader("DEX - قبل ما توصل المنصات المركزية")
    st.write("يفحص BSC التريند - Vol x2.5 + 5د + سيولة")
    if st.button("🚀 افحص DEX", type="primary", key="dex"):
        with st.spinner("يفحص DEX..."):
            try:
                url = "https://api.dexscreener.com/latest/dex/search/?q=BSC"
                r = requests.get(url, timeout=15)
                pairs = r.json().get('pairs', [])[:20]
                seen = set()
                found = 0
                for p in pairs:
                    addr = p.get('baseToken',{}).get('address')
                    if not addr or addr in seen:
                        continue
                    seen.add(addr)
                    result = check_dex_pump(addr)
                    if result:
                        msg, score, sym = result
                        st.code(msg)
                        if send_tg and send_tg_alert(msg):
                            st.success(f"اتبعت {sym} سكور {score}")
                            found += 1
                        time.sleep(1)
                if found == 0:
                    st.warning("مفيش بمب DEX قوي")
            except Exception as e:
                st.error(f"خطأ: {e}")
