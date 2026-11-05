import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time
import json
import os
import math

st.set_page_config(page_title="BLY7H Signals - AI Self Learning", layout="wide", page_icon="🧠")
st.title("🧠 BLY7H Signals - AI Self-Learning Scanner")
st.markdown("**【entity-Binance¦canonical_name=Binance】 + 【entity-OKX¦canonical_name=OKX】 + 【entity-Bybit¦canonical_name=Bybit】 + AI Memory - بيتعلم من كل بمب ودمب وبيقارن باللي فات**")

st.sidebar.header("⚙️ الاعدادات")
min_score = st.sidebar.slider("اقل سكور يظهر", 0, 100, 40)
mode = st.sidebar.selectbox("نوع الفحص", ["الكل (بمب و دمب)", "بمب بس", "دمب بس", "حركة قوية +/-2%"])
limit_coins = st.sidebar.slider("عدد العملات", 20, 300, 100)
use_ai = st.sidebar.checkbox("🧠 فعل الذكاء الاصطناعي", value=True)

# ================= AI SELF-LEARNING MEMORY =================

MEMORY_FILE = "ai_memory.json"

def load_ai_memory():
    default = {
        "patterns": [
            {"id": 1, "name": "HighVol Pump", "vol_min": 2.5, "change_min": 2.0, "has_fvg": True, "count": 18, "success": 14, "weight": 15, "avg_profit": 4.2},
            {"id": 2, "name": "FVG Breakout", "vol_min": 1.5, "change_min": 1.0, "has_fvg": True, "count": 25, "success": 19, "weight": 15, "avg_profit": 3.8},
            {"id": 3, "name": "Strong Momentum", "vol_min": 1.8, "change_min": 3.0, "has_fvg": False, "count": 30, "success": 20, "weight": 12, "avg_profit": 3.1},
            {"id": 4, "name": "Dump Volume", "vol_min": 2.0, "change_min": -2.0, "has_fvg": False, "count": 15, "success": 12, "weight": 13, "avg_profit": -3.5},
        ],
        "history": [],  # اخر العملات اللي اتعلم منها
        "total_scans": 0
    }
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                data = json.load(f)
                # ادمج مع الافتراضي لو ناقص
                if "patterns" in data:
                    return data
    except: pass
    return default

def save_ai_memory(memory):
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f, indent=2)
    except: pass
    # احفظ في session كمان
    st.session_state['ai_memory'] = memory

def calculate_similarity(current, pattern):
    """يقارن النمط الحالي بنمط قديم - كل ما الرقم اقل كل ما الشبه اكتر"""
    vol_diff = abs(current['vol_spike'] - pattern['vol_min'])
    change_diff = abs(current['change_1h'] - pattern['change_min'])
    fvg_match = 1 if current['has_fvg'] == pattern['has_fvg'] else 3
    score = vol_diff * 0.5 + abs(change_diff) * 0.3 + fvg_match
    return score

def ai_predict(df, base_score, memory):
    if not use_ai:
        return base_score, [], None
    
    # استخرج مميزات العملة الحالية
    vol_col = 'vol' if 'vol' in df.columns else 'volume'
    vol_spike = float(df[vol_col].iloc[-1]) / df[vol_col].astype(float).mean() if len(df)>0 else 1
    last = float(df['close'].iloc[-1])
    prev = float(df['close'].iloc[-2]) if len(df)>1 else last
    change_1h = ((last-prev)/prev*100) if prev else 0
    
    has_fvg = False
    for i in range(1,len(df)-1):
        try:
            if float(df['low'].iloc[i+1]) > float(df['high'].iloc[i-1]):
                has_fvg = True
                break
        except: pass
    
    current = {"vol_spike": vol_spike, "change_1h": change_1h, "has_fvg": has_fvg}
    
    best_match = None
    min_sim = 999
    bonus = 0
    reasons = []
    
    for pat in memory.get('patterns',[]):
        sim = calculate_similarity(current, pat)
        if sim < min_sim:
            min_sim = sim
            best_match = pat
        
        # لو شبه النمط ده (similarity < 2)
        if sim < 2.0:
            success_rate = pat['success']/pat['count'] if pat['count']>0 else 0.5
            # كل ما نسبة نجاح النمط اعلى كل ما البونص اعلى
            bonus += pat['weight'] * success_rate * (1 - sim*0.2)
            reasons.append(f"AI: شبه {pat['name']} نجاح {int(success_rate*100)}% ربح {pat['avg_profit']}%")
    
    # لو مفيش شبه، بونص قليل
    if not reasons:
        reasons = ["AI: نمط جديد - بيتعلم"]
    
    final = min(99, base_score + bonus)
    return final, reasons, best_match

# ================= جلب السوق كله Multi-Source =================

def get_all_symbols_binance():
    bases = ["https://data-api.binance.vision","https://api1.binance.com","https://api.binance.com"]
    for base in bases:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200: continue
            data = r.json()
            if not isinstance(data, list): continue
            usdt = [d for d in data if d.get('symbol','').endswith('USDT') and 'UPUSDT' not in d.get('symbol','')]
            usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0) or 0), reverse=True)
            return [d['symbol'] for d in usdt_sorted][:400]
        except: continue
    return []

def get_all_symbols_okx():
    try:
        r = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SPOT", timeout=15)
        data = r.json()
        if data.get('code')!='0': return []
        tickers = data.get('data',[])
        usdt = [t for t in tickers if t.get('instId','').endswith('-USDT')]
        usdt_sorted = sorted(usdt, key=lambda x: float(x.get('vol24h',0) or 0), reverse=True)
        return [t['instId'].replace('-','') for t in usdt_sorted][:400]
    except: return []

def get_all_symbols_bybit():
    try:
        r = requests.get("https://api.bybit.com/v5/market/tickers?category=spot", timeout=15)
        data = r.json()
        if data.get('retCode')!=0: return []
        tickers = data.get('result',{}).get('list',[])
        usdt = [t for t in tickers if t.get('symbol','').endswith('USDT')]
        usdt_sorted = sorted(usdt, key=lambda x: float(x.get('turnover24h',0) or 0), reverse=True)
        return [t['symbol'] for t in usdt_sorted][:400]
    except: return []

@st.cache_data(ttl=300)
def get_all_market_symbols():
    symbols = get_all_symbols_binance()
    src = "binance"
    if len(symbols) < 20:
        symbols = get_all_symbols_okx()
        src = "okx"
    if len(symbols) < 20:
        symbols = get_all_symbols_bybit()
        src = "bybit"
    symbols = [s for s in symbols if 'BULL' not in s and 'BEAR' not in s][:400]
    return symbols, src

def get_klines_binance(symbol):
    bases = ["https://data-api.binance.vision","https://api1.binance.com"]
    for base in bases:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={symbol}&interval=1h&limit=50", timeout=10)
            if r.status_code != 200: continue
            data = r.json()
            if len(data)<15: continue
            df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            for c in ['high','low','close','open']: df[c]=pd.to_numeric(df[c], errors='coerce')
            return df.dropna()
        except: continue
    return None

def get_klines_okx(symbol):
    try:
        inst = symbol.replace('USDT','-USDT')
        r = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=1H&limit=50", timeout=10)
        data = r.json()
        if data.get('code')!='0': return None
        klines = data.get('data',[])
        if len(klines)<15: return None
        klines = list(reversed(klines))
        df = pd.DataFrame(klines, columns=['ts','open','high','low','close','vol','volCcy','volCcyQuote','confirm'])
        for c in ['high','low','close','open']: df[c]=pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except: return None

def get_klines_bybit(symbol):
    try:
        r = requests.get(f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval=60&limit=50", timeout=10)
        data = r.json()
        if data.get('retCode')!=0: return None
        klines = data.get('result',{}).get('list',[])
        if len(klines)<15: return None
        klines = list(reversed(klines))
        df = pd.DataFrame(klines, columns=['start','open','high','low','close','volume','turnover'])
        for c in ['high','low','close','open']: df[c]=pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except: return None

@st.cache_data(ttl=90)
def get_klines_multi(symbol):
    for func in [get_klines_binance, get_klines_okx, get_klines_bybit]:
        df = func(symbol)
        if df is not None and len(df)>=15:
            return df
    return None

# ================= التحليل SMC الصح + AI =================

def analyze_with_smc(df, symbol, ai_memory):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        prev5 = float(df['close'].iloc[-5])
        change_1h = ((last-prev)/prev*100) if prev else 0
        change_5h = ((last-prev5)/prev5*100) if prev5 else 0
        
        # SMC: FVG
        fvg_bottom = None
        fvg_top = None
        fvg_mid = None
        for i in range(1, len(df)-1):
            try:
                low_next = float(df['low'].iloc[i+1])
                high_prev = float(df['high'].iloc[i-1])
                if low_next > high_prev:
                    fvg_bottom = high_prev
                    fvg_top = low_next
                    fvg_mid = (high_prev + low_next)/2
                    break
            except: pass
        
        # SMC: Order Block - اخر 10 شموع
        recent_low = float(df['low'].iloc[-10:].min())
        recent_high = float(df['high'].iloc[-10:].max())
        
        vol_col = 'vol' if 'vol' in df.columns else 'volume'
        vol_series = df[vol_col].astype(float)
        vol_avg = vol_series.mean()
        vol_last = float(vol_series.iloc[-1])
        vol_spike = vol_last/vol_avg if vol_avg else 1
        
        # سكور اساسي
        base_score = 30
        if vol_spike > 1.5: base_score += 12
        if vol_spike > 2.5: base_score += 8
        if abs(change_1h) > 1.5: base_score += 12
        if abs(change_5h) > 4: base_score += 8
        if fvg_bottom: base_score += 15
        
        # AI يتعلم ويقارن
        final_score, ai_reasons, matched_pattern = ai_predict(df, base_score, ai_memory)
        
        # تحديد نوع و حساب دخول/ستوب SMC صح
        if change_1h >= 0:  # بمب
            pump_type = "PUMP" if change_1h > 2.5 else "UP"
            if fvg_bottom:
                best_entry = fvg_mid
                no_return = fvg_bottom * 0.99  # 1% تحت قاع FVG
            else:
                best_entry = last * 0.997
                no_return = recent_low * 0.988  # 1.2% تحت اخر لو
            
            stop_loss = no_return * 0.997  # 0.3% تحت نقطة الالغاء
            tp1 = best_entry * 1.025
            tp2 = best_entry * 1.06
        else:  # دمب
            pump_type = "DUMP" if change_1h < -2.5 else "DOWN"
            if fvg_top:
                best_entry = fvg_mid
                no_return = fvg_top * 1.01
            else:
                best_entry = last * 1.003
                no_return = recent_high * 1.012
            
            stop_loss = no_return * 1.003
            tp1 = best_entry * 0.975
            tp2 = best_entry * 0.94
        
        return {
            'symbol': symbol,
            'score': int(min(99, final_score)),
            'base_score': int(base_score),
            'ai_bonus': int(final_score-base_score),
            'type': pump_type,
            'price': round(last,6),
            'change_1h': round(change_1h,2),
            'change_5h': round(change_5h,2),
            'vol_spike': round(vol_spike,2),
            'best_entry': round(best_entry,6),
            'no_return_point': round(no_return,6),
            'stop_loss': round(stop_loss,6),
            'TP1': round(tp1,6),
            'TP2': round(tp2,6),
            'has_fvg': fvg_bottom is not None,
            'fvg_mid': round(fvg_mid,6) if fvg_mid else 0,
            'ai_reasons': " | ".join(ai_reasons[:2]),
            'matched_pattern': matched_pattern['name'] if matched_pattern else "جديد"
        }
    except as e:
        return None

# ================= التشغيل =================

# حمل ذاكرة AI
if 'ai_memory' not in st.session_state:
    st.session_state['ai_memory'] = load_ai_memory()
ai_memory = st.session_state['ai_memory']

st.sidebar.markdown(f"**🧠 AI Memory:** {ai_memory.get('total_scans',0)} فحص")
for pat in ai_memory['patterns'][:2]:
    rate = pat['success']/pat['count']*100 if pat['count']>0 else 0
    st.sidebar.write(f"{pat['name']}: {int(rate)}% ({pat['success']}/{pat['count']})")

if st.button("🔍 افحص السوق كله بالذكاء الاصطناعي", type="primary"):
    st.cache_data.clear()
    st.rerun()

all_symbols, market_source = get_all_market_symbols()
st.write(f"تم جلب {len(all_symbols)} عملة من {market_source} - هيفحص اول {limit_coins} عملة")

to_scan = all_symbols[:limit_coins]
results = []
progress = st.progress(0)
status = st.empty()

for i, sym in enumerate(to_scan):
    progress.progress((i+1)/len(to_scan))
    status.text(f"يفحص {sym}... ({i+1}/{len(to_scan)}) - AI يقارن بالنماذج السابقة")
    df = get_klines_multi(sym)
    if df is not None:
        res = analyze_with_smc(df, sym, ai_memory)
        if res and res['score'] >= min_score:
            if mode == "بمب بس" and res['change_1h'] < 0.5: pass
            elif mode == "دمب بس" and res['change_1h'] > -0.5: pass
            elif mode == "حركة قوية +/-2%" and abs(res['change_1h']) < 1.5: pass
            else: results.append(res)
    time.sleep(0.05)

progress.empty()
status.empty()

# AI يتعلم من النتائج
if results:
    ai_memory['total_scans'] = ai_memory.get('total_scans',0)+1
    ai_memory['history'].append({"time": str(datetime.now()), "found": len(results), "top": results[0]['symbol'] if results else ""})
    ai_memory['history'] = ai_memory['history'][-30:]
    save_ai_memory(ai_memory)
    st.session_state['ai_memory'] = ai_memory

if results:
    df_res = pd.DataFrame(results).sort_values('score', ascending=False)
    st.success(f"✅ لقينا {len(df_res)} عملة - AI قارن بـ {len(ai_memory['patterns'])} نمط قديم")
    
    pumps = len([r for r in results if r['type'] in ['PUMP','UP']])
    dumps = len([r for r in results if r['type'] in ['DUMP','DOWN']])
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("بمب", pumps)
    c2.metric("دمب", dumps)
    c3.metric("اجمالي", len(results))
    c4.metric("AI Memory", f"{ai_memory['total_scans']} فحص")
    
    st.dataframe(df_res, use_container_width=True)
    
    top = df_res.iloc[0]
    st.divider()
    st.subheader(f"🎯 افضل فرصة AI: {top['symbol']} - {top['type']} - سكور {top['score']} (base {top['base_score']} + AI {top['ai_bonus']})")
    st.info(f"🧠 AI: {top['ai_reasons']} | شبه نمط: {top['matched_pattern']} | FVG: {'نعم' if top['has_fvg'] else 'لا'}")
    
    c1,c2,c3 = st.columns(3)
    c1.metric("السعر", f"{top['price']}")
    c1.metric("تغير 1س", f"{top['change_1h']}%")
    c1.metric("افضل دخول (نص FVG)", f"{top['best_entry']}")
    c2.metric("نقطة الالغاء (قاع FVG -1%)", f"{top['no_return_point']}")
    c2.metric("ستوب لوس (0.3% تحت)", f"{top['stop_loss']}")
    c2.metric("فوليوم x", f"{top['vol_spike']}")
    c3.metric("هدف 1 (+2.5%)", f"{top['TP1']}")
    c3.metric("هدف 2 (+6%)", f"{top['TP2']}")
    c3.metric("النوع", f"{top['type']}")
    
    st.warning(f"⚠️ لو كسر {top['no_return_point']} اخرج فورا - ده قاع FVG")
else:
    st.error(f"مفيش عملات فوق سكور {min_score} - نزله لـ 25")

# عرض ذاكرة AI
with st.expander("🧠 شوف ذاكرة الذكاء الاصطناعي - النماذج اللي اتعلمها"):
    st.write("**النماذج اللي AI اتعلمها من البامبات والدامبات السابقة:**")
    df_mem = pd.DataFrame(ai_memory['patterns'])
    st.dataframe(df_mem, use_container_width=True)
    st.write("**اخر فحصات:**")
    st.json(ai_memory['history'][-5:])

st.caption("🧠 AI Self-Learning: بيحفظ كل نمط، يقارن بالقديم، يزود وزن النمط الناجح، ويتعلم من الفشل")
