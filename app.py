import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time, json, os, math

st.set_page_config(page_title="BLY7H Ultimate Radar", layout="wide", page_icon="🎯")
st.title("🎯 BLY7H Ultimate Radar - Predict BEFORE")
st.caption("PUMP دخول تحت السعر | DUMP دخول فوق السعر | تنبؤ قبل الحركة")

st.sidebar.header("⚙️ الاعدادات")
min_score = st.sidebar.slider("اقل سكور للجدول", 0, 100, 30)
mode = st.sidebar.selectbox("نوع الفحص", ["الكل", "بمب بس", "دمب بس"])
limit_coins = st.sidebar.slider("عدد العملات", 20, 300, 80)
use_ai = st.sidebar.checkbox("🧠 AI", value=True)
send_tg = st.sidebar.checkbox("📱 تليجرام", value=True)
tg_min = st.sidebar.slider("سكور التليجرام", 20, 95, 50)

def send_tg_alert(sig):
    try:
        bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN")
        chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            return False
        if sig['score'] < tg_min:
            return False
        emoji = "🚀" if "PUMP" in sig['type'] else "💥"
        msg = f"""{emoji} BLY7H {sig['type']} {emoji}
💰 {sig['symbol']} - قبل الحركة!
📊 سكور: {sig['score']} (T:{sig['tech']}|L:{sig['liq']}|G:{sig['gann']}|A:{sig['astro']})
💵 الان: {sig['price']} | تغير: {sig['change_1h']}%
🎯 دخول: {sig['best_entry']} {'(تحت السعر)' if sig['type']=='PUMP' else '(فوق السعر)'}
❌ الغاء: {sig['no_return_point']}
⛔ ستوب: {sig['stop_loss']}
✅ هدف1: {sig['TP1']} | هدف2: {sig['TP2']}
📚 {sig['tech_reason']}
💧 {sig['liq_reason']}
📐 {sig['gann_reason']}
🌙 {sig['astro_reason']}
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return r.status_code == 200
    except:
        return False

MEMORY_FILE = "ai_memory.json"
def load_memory():
    default = {"patterns": [{"name": "HighVol", "vol": 2.5, "count": 20, "success": 15, "weight": 10}], "total": 0}
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return default

def save_memory(m):
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(m, f, indent=2)
    except:
        pass
    st.session_state['mem'] = m

def gann_levels(price):
    try:
        s = math.sqrt(price)
        return [(s + i * 0.25) ** 2 for i in range(-3, 4)]
    except:
        return [price]

def calc_gann(price):
    try:
        levels = gann_levels(price)
        dist = min([abs(price - l) / price * 100 for l in levels])
        score = 12 if dist < 0.5 else 7 if dist < 1.5 else 2
        reason = f"قريب جان {dist:.2f}% - انعكاس قبل" if dist < 0.5 else f"يقترب جان {dist:.1f}%" if dist < 1.5 else "بعيد جان"
        days = (datetime.now() - datetime(2023, 1, 1)).days
        if days % 90 < 3:
            score += 5
            reason += " + دورة زمنية"
        return min(20, score), reason
    except:
        return 5, "جان"

def calc_astro():
    try:
        new_moon = datetime(2024, 1, 11)
        days = (datetime.now() - new_moon).days % 29.5
        score = 6 if days < 2 or abs(days - 14.75) < 1.5 else 3 if days < 5 else 1
        reason = f"قمر {days:.0f} يوم" + (" + يوم قوي" if datetime.now().weekday() in [0,4] else "")
        if datetime.now().weekday() in [0,4]:
            score += 3
        return min(10, score), reason
    except:
        return 2, "فلكي"

def calc_institutional(df, price):
    try:
        score = 5
        reasons = []
        hour_eg = (datetime.utcnow().hour + 2) % 24
        if hour_eg in [10,11,12,13,16,17,18,19]:
            score += 7
            reasons.append("Killzone")
        low_10 = float(df['low'].iloc[-10:].min())
        if price <= low_10 * 1.015:
            score += 10
            reasons.append("AMD صعود متوقع")
        vol_col = 'vol' if 'vol' in df.columns else 'volume'
        vol_spike = float(df[vol_col].iloc[-1]) / df[vol_col].astype(float).mean()
        if vol_spike > 2:
            score += 6
            reasons.append(f"Vol x{vol_spike:.1f}")
        high_20 = float(df['high'].iloc[-20:].max())
        if price < high_20 and (high_20 - price) / price < 0.03:
            score += 5
            reasons.append("سيولة فوق")
        return min(30, score), " | ".join(reasons) if reasons else "سيولة طبيعية"
    except:
        return 8, "سيولة"

def calc_smc(df, price):
    try:
        bull_b = bull_t = bull_m = None
        bear_b = bear_t = bear_m = None
        bull_dist = bear_dist = 999
        for i in range(1, len(df)-1):
            try:
                low_next = float(df['low'].iloc[i+1])
                high_prev = float(df['high'].iloc[i-1])
                high_next = float(df['high'].iloc[i+1])
                low_prev = float(df['low'].iloc[i-1])
                if low_next > high_prev and bull_b is None:
                    bull_b = high_prev; bull_t = low_next; bull_m = (high_prev+low_next)/2
                    bull_dist = abs(price - bull_m) / price * 100
                if high_next < low_prev and bear_b is None:
                    bear_b = high_next; bear_t = low_prev; bear_m = (high_next+low_prev)/2
                    bear_dist = abs(price - bear_m) / price * 100
            except:
                pass
        recent_low = float(df['low'].iloc[-10:].min())
        recent_high = float(df['high'].iloc[-10:].max())
        score = 15
        has_fvg = bull_b is not None or bear_b is not None
        reasons = []
        if bull_b is not None and bull_dist < 4:
            score += 20
            reasons.append(f"Bull FVG {bull_dist:.1f}% دعم قبل اللمس")
        elif bear_b is not None and bear_dist < 4:
            score += 20
            reasons.append(f"Bear FVG {bear_dist:.1f}% مقاومة قبل اللمس")
        elif has_fvg:
            score += 8
            reasons.append("يوجد FVG")
        if price <= recent_low * 1.02:
            score += 10
            reasons.append("OB شرائي")
        fvg_data = {'bull_b': bull_b, 'bull_t': bull_t, 'bull_m': bull_m, 'bear_b': bear_b, 'bear_t': bear_t, 'bear_m': bear_m}
        return score, has_fvg, True, fvg_data, recent_low, recent_high, " | ".join(reasons) if reasons else "SMC عادي"
    except:
        return 15, False, False, {}, price*0.99, price*1.01, "SMC"

def get_symbols_binance():
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200: continue
            data = r.json()
            usdt = [d for d in data if d.get('symbol','').endswith('USDT')]
            usdt = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0) or 0), reverse=True)
            return [d['symbol'] for d in usdt][:400]
        except:
            continue
    return []

def get_symbols_okx():
    try:
        r = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SPOT", timeout=15)
        data = r.json()
        if data.get('code') != '0': return []
        tickers = data.get('data',[])
        usdt = [t for t in tickers if t.get('instId','').endswith('-USDT')]
        usdt = sorted(usdt, key=lambda x: float(x.get('vol24h',0) or 0), reverse=True)
        return [t['instId'].replace('-','') for t in usdt][:400]
    except:
        return []

@st.cache_data(ttl=300)
def get_all_symbols():
    s = get_symbols_binance()
    src = " 【entity-binance¦canonical_name=Binance】"
    if len(s) < 20:
        s = get_symbols_okx()
        src = " 【entity-okx¦canonical_name=OKX】"
    return [x for x in s if 'BULL' not in x][:400], src

def get_klines_binance(sym):
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={sym}&interval=1h&limit=100", timeout=10)
            if r.status_code != 200: continue
            data = r.json()
            if len(data) < 20: continue
            df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            for c in ['high','low','close','open']: df[c] = pd.to_numeric(df[c], errors='coerce')
            return df.dropna()
        except:
            continue
    return None

def get_klines_okx(sym):
    try:
        inst = sym.replace('USDT','-USDT')
        r = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=1H&limit=100", timeout=10)
        data = r.json()
        if data.get('code') != '0': return None
        klines = data.get('data',[])
        if len(klines) < 20: return None
        klines = list(reversed(klines))
        df = pd.DataFrame(klines, columns=['ts','open','high','low','close','vol','volCcy','volCcyQuote','confirm'])
        for c in ['high','low','close','open']: df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except:
        return None

@st.cache_data(ttl=90)
def get_klines(sym):
    for f in [get_klines_binance, get_klines_okx]:
        df = f(sym)
        if df is not None and len(df) >= 20:
            return df
    return None

def ultimate_score(df, sym, memory):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change = ((last - prev) / prev * 100) if prev else 0
        tech, has_fvg, has_ob, fvg_data, rec_low, rec_high, tech_r = calc_smc(df, last)
        liq, liq_r = calc_institutional(df, last)
        gann, gann_r = calc_gann(last)
        astro, astro_r = calc_astro()
        ai_bonus = 0
        ai_r = "جديد"
        if use_ai:
            vol_col = 'vol' if 'vol' in df.columns else 'volume'
            vs = float(df[vol_col].iloc[-1]) / df[vol_col].astype(float).mean()
            for pat in memory.get('patterns',[]):
                if abs(vs - pat.get('vol',2)) < 1.5:
                    ai_bonus = 5
                    ai_r = f"شبه {pat['name']}"
                    break
        total = min(99, int(tech + liq + gann + astro + ai_bonus))

        bull_b = fvg_data.get('bull_b')
        bull_m = fvg_data.get('bull_m')
        bear_b = fvg_data.get('bear_b')
        bear_m = fvg_data.get('bear_m')
        bear_t = fvg_data.get('bear_t')

        if bull_b is not None and abs(last - bull_m) / last * 100 < 5:
            ptype = "PUMP"
            best = bull_m
            no_ret = bull_b * 0.985
        elif bear_b is not None and abs(last - bear_m) / last * 100 < 5:
            ptype = "DUMP"
            best = bear_m
            no_ret = bear_t * 1.015 if bear_t else last * 1.02
        else:
            ptype = "PUMP" if change >= -0.3 else "DUMP"
            best = last * 0.994 if ptype == "PUMP" else last * 1.006
            no_ret = rec_low * 0.985 if ptype == "PUMP" else rec_high * 1.015

        if ptype == "PUMP":
            best = min(best, last * 0.998)
            stop = no_ret * 0.994
            tp1 = best * 1.028
            tp2 = best * 1.065
            if tp1 <= last: tp1 = last * 1.02
            if tp2 <= tp1: tp2 = tp1 * 1.03
        else:
            best = max(best, last * 1.002)
            stop = no_ret * 1.006
            tp1 = best * 0.972
            tp2 = best * 0.935
            if tp1 >= last: tp1 = last * 0.98
            if tp2 >= tp1: tp2 = tp1 * 0.97

        return {
            'symbol': sym, 'score': total, 'tech': tech, 'liq': liq, 'gann': gann, 'astro': astro,
            'ai_bonus': int(ai_bonus), 'type': ptype, 'price': round(last,6),
            'change_1h': round(change,2), 'best_entry': round(best,6),
            'no_return_point': round(no_ret,6), 'stop_loss': round(stop,6),
            'TP1': round(tp1,6), 'TP2': round(tp2,6), 'has_fvg': has_fvg, 'has_ob': has_ob,
            'liq_reason': liq_r, 'gann_reason': gann_r, 'astro_reason': astro_r,
            'ai_reason': ai_r, 'tech_reason': tech_r
        }
    except:
        return None

if 'mem' not in st.session_state:
    st.session_state['mem'] = load_memory()
memory = st.session_state['mem']

if st.sidebar.button("🧪 اختبار تليجرام"):
    test_sig = {'symbol':'TESTUSDT','score':80,'tech':20,'liq':20,'gann':15,'astro':5,'type':'PUMP','price':1,'change_1h':2,'best_entry':0.99,'no_return_point':0.98,'stop_loss':0.97,'TP1':1.02,'TP2':1.
