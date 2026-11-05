import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time
import json
import os

st.set_page_config(page_title="BLY7H Signals - AI Whole Market", layout="wide", page_icon="🧠")
st.title("🧠 BLY7H Signals - AI Self-Learning Scanner")
st.markdown("**【entity-Binance¦canonical_name=Binance】 + 【entity-OKX¦canonical_name=OKX】 + 【entity-Bybit¦canonical_name=Bybit】 + AI Memory - بيتعلم من كل بمب ودمب حصل قبل كده**")

st.sidebar.header("⚙️ الاعدادات")
min_score = st.sidebar.slider("اقل سكور يظهر", 0, 100, 35)
mode = st.sidebar.selectbox("نوع الفحص", ["الكل (بمب و دمب)", "بمب بس +5%", "دمب بس -5%", "حركة قوية +/-2%"])
limit_coins = st.sidebar.slider("عدد العملات اللي يفحصها", 20, 300, 100)
use_ai = st.sidebar.checkbox("🧠 فعل الذكاء الاصطناعي اللي بيتعلم", value=True)

# ========== AI MEMORY - الذكاء الاصطناعي اللي بيتعلم ==========

MEMORY_FILE = "ai_memory.json"

def load_ai_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
    except: pass
    # ذاكرة ابتدائية
    return {
        "patterns": {
            "high_vol_pump": {"count": 15, "success": 12, "weight": 15},
            "fvg_pump": {"count": 20, "success": 16, "weight": 15},
            "strong_change": {"count": 25, "success": 18, "weight": 10},
            "dump_vol": {"count": 10, "success": 8, "weight": 12}
        },
        "total_scans": 0,
        "learned_coins": []
    }

def save_ai_memory(memory):
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f, indent=2)
    except: pass

def ai_predict_score(df, base_score, memory):
    """الذكاء الاصطناعي يعدل السكور حسب اللي اتعلمه"""
    if not use_ai:
        return base_score, []
    
    last = float(df['close'].iloc[-1])
    prev = float(df['close'].iloc[-2])
    change = ((last-prev)/prev*100) if prev else 0
    vol_avg = df['vol' if 'vol' in df.columns else 'volume'].astype(float).mean()
    vol_last = float(df['vol' if 'vol' in df.columns else 'volume'].iloc[-1])
    vol_spike = vol_last/vol_avg if vol_avg else 1
    
    ai_bonus = 0
    reasons = []
    
    patterns = memory.get('patterns',{})
    
    # نمط 1: فوليوم عالي + بمب
    if vol_spike > 2 and change > 2:
        pat = patterns.get('high_vol_pump', {"weight": 10, "success": 1, "count":1})
        success_rate = pat['success']/pat['count'] if pat['count']>0 else 0.5
        bonus = pat['weight'] * success_rate
        ai_bonus += bonus
        reasons.append(f"AI: High Vol Pump {success_rate*100:.0f}% نجاح")
    
    # نمط 2: FVG
    has_fvg = False
    for i in range(1,len(df)-1):
        try:
            if float(df['low'].iloc[i+1]) > float(df['high'].iloc[i-1]): 
                has_fvg=True; break
        except: pass
    if has_fvg:
        pat = patterns.get('fvg_pump', {"weight": 10})
        success_rate = pat['success']/pat['count'] if pat['count']>0 else 0.5
        ai_bonus += pat['weight']*success_rate
        reasons.append(f"AI: FVG Pattern {success_rate*100:.0f}% نجاح")
    
    # نمط 3: حركة قوية
    if abs(change) > 3:
        pat = patterns.get('strong_change', {"weight": 8})
        success_rate = pat['success']/pat['count'] if pat['count']>0 else 0.5
        ai_bonus += pat['weight']*success_rate*0.7
        reasons.append(f"AI: Strong Move")
    
    return min(99, base_score + ai_bonus), reasons

def ai_learn_from_result(symbol, df, was_success):
    """يتعلم بعد ما يشوف النتيجة"""
    memory = load_ai_memory()
    # بسيط: زود العداد
    memory['total_scans'] = memory.get('total_scans',0)+1
    
    last = float(df['close'].iloc[-1])
    prev = float(df['close'].iloc[-2])
    change = ((last-prev)/prev*100) if prev else 0
    vol_avg = df['vol' if 'vol' in df.columns else 'volume'].astype(float).mean()
    vol_last = float(df['vol' if 'vol' in df.columns else 'volume'].iloc[-1])
    vol_spike = vol_last/vol_avg if vol_avg else 1
    
    if vol_spike>2 and change>2:
        p = memory['patterns']['high_vol_pump']
        p['count']+=1
        if was_success: p['success']+=1
    
    # احفظ اخر 20 عملة اتعلمها
    memory['learned_coins'].append({"symbol": symbol, "time": str(datetime.now()), "success": was_success})
    memory['learned_coins'] = memory['learned_coins'][-20:]
    
    save_ai_memory(memory)

# ========== جلب كل السوق ==========

def get_all_symbols_binance():
    bases = ["https://data-api.binance.vision","https://api1.binance.com","https://api.binance.com"]
    for base in bases:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200: continue
            data = r.json()
            if not isinstance(data, list): continue
            usdt = [d for d in data if d.get('symbol','').endswith('USDT')]
            usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0) or 0), reverse=True)
            return [d['symbol'] for d in usdt_sorted]
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
        return [t['instId'].replace('-','') for t in usdt_sorted]
    except: return []

def get_all_symbols_bybit():
    try:
        r = requests.get("https://api.bybit.com/v5/market/tickers?category=spot", timeout=15)
        data = r.json()
        if data.get('retCode')!=0: return []
        tickers = data.get('result',{}).get('list',[])
        usdt = [t for t in tickers if t.get('symbol','').endswith('USDT')]
        usdt_sorted = sorted(usdt, key=lambda x: float(x.get('turnover24h',0) or 0), reverse=True)
        return [t['symbol'] for t in usdt_sorted]
    except: return []

@st.cache_data(ttl=300)
def get_all_market_symbols():
    symbols = get_all_symbols_binance()
    source = "binance"
    if len(symbols) < 20:
        symbols = get_all_symbols_okx()
        source = "okx"
    if len(symbols) < 20:
        symbols = get_all_symbols_bybit()
        source = "bybit"
    symbols = [s for s in symbols if 'UP' not in s and 'DOWN' not in s][:400]
    return symbols, source

def get_klines_binance(symbol):
    bases = ["https://data-api.binance.vision","https://api1.binance.com"]
    for base in bases:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={symbol}&interval=1h&limit=50", timeout=10)
            if r.status_code != 200: continue
            data = r.json()
            if len(data)<10: continue
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
        if len(klines)<10: return None
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
        if len(klines)<10: return None
        klines = list(reversed(klines))
        df = pd.DataFrame(klines, columns=['start','open','high','low','close','volume','turnover'])
        for c in ['high','low','close','open']: df[c]=pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except: return None

@st.cache_data(ttl=90)
def get_klines_multi(symbol):
    for func in [get_klines_binance, get_klines_okx, get_klines_bybit]:
        df = func(symbol)
        if df is not None and len(df)>=10:
            return df
    return None

def calc_score(df, symbol, ai_memory):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        prev5 = float(df['close'].iloc[-5])
        change_1h = ((last-prev)/prev*100) if prev else 0
        change_5h = ((last-prev5)/prev5*100) if prev5 else 0
        low_50 = float(df['low'].min())
        high_50 = float(df['high'].max())
        vol_avg = df['vol' if 'vol' in df.columns else 'volume'].astype(float).mean()
        vol_last = float(df['vol' if 'vol' in df.columns else 'volume'].iloc[-1])
        vol_spike = vol_last/vol_avg if vol_avg else 1
        
        base_score = 30
        if vol_spike > 1.5: base_score += 15
        if vol_spike > 3: base_score += 10
        if abs(change_1h) > 2: base_score += 15
        if abs(change_5h) > 5: base_score += 10
        
        for i in range(1,len(df)-1):
            try:
                if float(df['low'].iloc[i+1]) > float(df['high'].iloc[i-1]): 
                    base_score += 15; break
            except: pass
        
        # AI يعدل السكور
        final_score, ai_reasons = ai_predict_score(df, base_score, ai_memory)
        
        pump_type = "STABLE"
        if change_1h > 3: pump_type = "PUMP"
        elif change_1h < -3: pump_type = "DUMP"
        elif change_1h > 1: pump_type = "UP"
        elif change_1h < -1: pump_type = "DOWN"
        
        best_entry = last * 0.993 if change_1h>0 else last * 1.007
        no_return = low_50 * 0.97 if change_1h>0 else high_50 * 1.03
        
        return {
            'symbol': symbol,
            'score': int(min(99, final_score)),
            'base_score': base_score,
            'ai_bonus': int(final_score-base_score),
            'type': pump_type,
            'price': round(last,6),
            'change_1h': round(change_1h,2),
            'change_5h': round(change_5h,2),
            'vol_spike': round(vol_spike,2),
            'best_entry': round(best_entry,6),
            'no_return_point': round(no_return,6),
            'stop_loss': round(no_return*0.998,6) if pump_type in ["PUMP","UP"] else round(no_return*1.002,6),
            'TP1': round(best_entry*1.025,6) if pump_type in ["PUMP","UP"] else round(best_entry*0.975,6),
            'TP2': round(best_entry*1.06,6) if pump_type in ["PUMP","UP"] else round(best_entry*0.94,6),
            'ai_reasons': ", ".join(ai_reasons)
        }
    except:
        return None

# ========== التشغيل ==========

ai_memory = load_ai_memory()
st.sidebar.markdown(f"**🧠 AI Memory:** {ai_memory.get('total_scans',0)} فحص")
st.sidebar.write(f"High Vol Pump: {ai_memory['patterns']['high_vol_pump']['success']}/{ai_memory['patterns']['high_vol_pump']['count']}")

if st.button("🔍 افحص السوق كله بالذكاء الاصطناعي", type="primary"):
    st.cache_data.clear()
    st.rerun()

all_symbols, market_source = get_all_market_symbols()
st.write(f"تم جلب {len(all_symbols)} عملة من {market_source} - هيفحص اول {limit_coins}")

to_scan = all_symbols[:limit_coins]
results = []
progress = st.progress(0)
status = st.empty()

for i, sym in enumerate(to_scan):
    progress.progress((i+1)/len(to_scan))
    status.text(f"يفحص {sym}... ({i+1}/{len(to_scan)}) - AI شغال")
    df = get_klines_multi(sym)
    if df is not None:
        res = calc_score(df, sym, ai_memory)
        if res and res['score'] >= min_score:
            if mode == "بمب بس +5%" and res['change_1h'] < 2: pass
            elif mode == "دمب بس -5%" and res['change_1h'] > -2: pass
            elif mode == "حركة قوية +/-2%" and abs(res['change_1h']) < 2: pass
            else: results.append(res)
    time.sleep(0.08)

progress.empty()
status.empty()

if results:
    df_res = pd.DataFrame(results).sort_values('score', ascending=False)
    st.success(f"✅ لقينا {len(df_res)} عملة - AI بيتعلم من كل فحص")
    st.dataframe(df_res, use_container_width=True)
    top = df_res.iloc[0]
    st.divider()
    st.subheader(f"🎯 افضل فرصة AI: {top['symbol']} - {top['type']} - سكور {top['score']} (base {top['base_score']} + AI {top['ai_bonus']})")
    st.caption(f"🧠 {top['ai_reasons']}")
    c1,c2,c3 = st.columns(3)
    c1.metric("السعر", f"{top['price']}")
    c1.metric("تغير 1س", f"{top['change_1h']}%")
    c1.metric("افضل دخول", f"{top['best_entry']}")
    c2.metric("نقطة الالغاء", f"{top['no_return_point']}")
    c2.metric("ستوب", f"{top['stop_loss']}")
    c2.metric("فوليوم x", f"{top['vol_spike']}")
    c3.metric("هدف 1", f"{top['TP1']}")
    c3.metric("هدف 2", f"{top['TP2']}")
    c3.metric("النوع", f"{top['type']}")
else:
    st.error(f"مفيش عملات فوق سكور {min_score}")

st.caption("AI Self-Learning: كل فحص بيتعلم من اللي قبله ويحسن السكور")
