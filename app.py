import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time, json, os, math

st.set_page_config(page_title="BLY7H Ultimate Radar", layout="wide", page_icon="🎯")
st.title("BLY7H Ultimate Radar - Predict BEFORE")
st.caption("PUMP دخول تحت السعر | DUMP دخول فوق السعر")

st.sidebar.header("Settings")
min_score = st.sidebar.slider("اقل سكور", 0, 100, 30)
mode = st.sidebar.selectbox("نوع الفحص", ["الكل", "بمب بس", "دمب بس"])
limit_coins = st.sidebar.slider("عدد العملات", 20, 300, 80)
use_ai = st.sidebar.checkbox("AI", value=True)
send_tg = st.sidebar.checkbox("تليجرام", value=True)
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
        lines = []
        lines.append(f"{emoji} BLY7H {sig['type']} {emoji}")
        lines.append(f"💰 {sig['symbol']} - قبل الحركة!")
        lines.append(f"📊 سكور: {sig['score']} (T:{sig['tech']} L:{sig['liq']} G:{sig['gann']})")
        lines.append(f"💵 الان: {sig['price']} تغير: {sig['change_1h']}%")
        lines.append(f"🎯 دخول: {sig['best_entry']}")
        lines.append(f"❌ الغاء: {sig['no_return_point']}")
        lines.append(f"⛔ ستوب: {sig['stop_loss']}")
        lines.append(f"✅ هدف1: {sig['TP1']} هدف2: {sig['TP2']}")
        lines.append(f"📚 {sig['tech_reason']}")
        lines.append(f"💧 {sig['liq_reason']}")
        lines.append(f"📐 {sig['gann_reason']}")
        lines.append(f"🧠 {sig['ai_reason']}")
        txt = "\n".join(lines)
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": txt}, timeout=10)
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
        res = []
        for i in range(-3,4):
            res.append((s + i*0.25)**2)
        return res
    except:
        return [price]

def calc_gann(price):
    try:
        levels = gann_levels(price)
        best = 999
        for l in levels:
            d = abs(price - l) / price * 100
            if d < best:
                best = d
        score = 12 if best < 0.5 else 7 if best < 1.5 else 2
        reason = f"جان {best:.2f}%"
        days = (datetime.now() - datetime(2023,1,1)).days
        if days % 90 < 3:
            score += 5
            reason += " دورة"
        if score > 20:
            score = 20
        return score, reason
    except:
        return 5, "جان"

def calc_astro():
    try:
        new_moon = datetime(2024,1,11)
        days = (datetime.now() - new_moon).days % 29.5
        score = 6 if days < 2 or abs(days - 14.75) < 1.5 else 3 if days < 5 else 1
        reason = f"قمر {days:.0f}"
        if datetime.now().weekday() in [0,4]:
            score += 3
            reason += " قوي"
        if score > 10:
            score = 10
        return score, reason
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
            reasons.append("AMD")
        col = 'vol' if 'vol' in df.columns else 'volume'
        mean_vol = df[col].astype(float).mean()
        last_vol = float(df[col].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol>0 else 1
        if vol_spike > 2:
            score += 6
            reasons.append(f"Vol x{vol_spike:.1f}")
        high_20 = float(df['high'].iloc[-20:].max())
        if price < high_20 and (high_20 - price) / price < 0.03:
            score += 5
            reasons.append("سيولة فوق")
        if score > 30:
            score = 30
        txt = " | ".join(reasons) if reasons else "طبيعية"
        return score, txt
    except:
        return 8, "سيولة"

def calc_smc(df, price):
    try:
        bull_b = None
        bull_m = None
        bear_b = None
        bear_m = None
        bear_t = None
        bull_dist = 999
        bear_dist = 999
        for i in range(1, len(df)-1):
            try:
                low_next = float(df['low'].iloc[i+1])
                high_prev = float(df['high'].iloc[i-1])
                high_next = float(df['high'].iloc[i+1])
                low_prev = float(df['low'].iloc[i-1])
                if low_next > high_prev and bull_b is None:
                    bull_b = high_prev
                    bull_m = (high_prev + low_next) / 2
                    bull_dist = abs(price - bull_m) / price * 100
                if high_next < low_prev and bear_b is None:
                    bear_b = high_next
                    bear_t = low_prev
                    bear_m = (high_next + low_prev) / 2
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
            reasons.append(f"Bull FVG {bull_dist:.1f}%")
        elif bear_b is not None and bear_dist < 4:
            score += 20
            reasons.append(f"Bear FVG {bear_dist:.1f}%")
        elif has_fvg:
            score += 8
            reasons.append("FVG")
        if price <= recent_low * 1.02:
            score += 10
            reasons.append("OB")
        fvg_data = {'bull_b': bull_b, 'bull_m': bull_m, 'bear_b': bear_b, 'bear_m': bear_m, 'bear_t': bear_t}
        txt = " | ".join(reasons) if reasons else "SMC"
        return score, has_fvg, True, fvg_data, recent_low, recent_high, txt
    except:
        return 15, False, False, {}, price*0.99, price*1.01, "SMC"

def get_symbols_binance():
    bases = ["https://data-api.binance.vision", "https://api1.binance.com"]
    for base in bases:
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

def get_symbols_okx():
    try:
        r = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SPOT", timeout=15)
        data = r.json()
        if data.get('code') != '0':
            return []
        tickers = data.get('data',[])
        usdt = []
        for t in tickers:
            if t.get('instId','').endswith('-USDT'):
                usdt.append(t)
        usdt_sorted = sorted(usdt, key=lambda x: float(x.get('vol24h') or 0), reverse=True)
        res = []
        for t in usdt_sorted[:400]:
            res.append(t['instId'].replace('-',''))
        return res
    except:
        return []

@st.cache_data(ttl=300)
def get_all_symbols():
    s = get_symbols_binance()
    src = " binance"
    if len(s) < 20:
        s = get_symbols_okx()
        src = " okx"
    clean = []
    for x in s:
        if 'BULL' not in x:
            clean.append(x)
    return clean[:400], src

def get_klines_binance(sym):
    bases = ["https://data-api.binance.vision", "https://api1.binance.com"]
    for base in bases:
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

def get_klines_okx(sym):
    try:
        inst = sym.replace('USDT','-USDT')
        r = requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=1H&limit=100", timeout=10)
        data = r.json()
        if data.get('code') != '0':
            return None
        klines = data.get('data',[])
        if len(klines) < 20:
            return None
        klines = list(reversed(klines))
        df = pd.DataFrame(klines, columns=['ts','open','high','low','close','vol','volCcy','volCcyQuote','confirm'])
        for c in ['high','low','close','open']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except:
        return None

@st.cache_data(ttl=90)
def get_klines(sym):
    df = get_klines_binance(sym)
    if df is not None and len(df) >= 20:
        return df
    df = get_klines_okx(sym)
    if df is not None and len(df) >= 20:
        return df
    return None

def ultimate_score(df, sym, memory):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change = (last - prev) / prev * 100 if prev != 0 else 0
        tech, has_fvg, has_ob, fvg_data, rec_low, rec_high, tech_r = calc_smc(df, last)
        liq, liq_r = calc_institutional(df, last)
        gann, gann_r = calc_gann(last)
        astro, astro_r = calc_astro()
        ai_bonus = 0
        ai_r = "جديد"
        if use_ai:
            col = 'vol' if 'vol' in df.columns else 'volume'
            mean_vol = df[col].astype(float).mean()
            last_vol = float(df[col].iloc[-1])
            vs = last_vol / mean_vol if mean_vol>0 else 1
            for pat in memory.get('patterns',[]):
                if abs(vs - pat.get('vol',2)) < 1.5:
                    ai_bonus = 5
                    ai_r = pat['name']
                    break
        total = tech + liq + gann + astro + ai_bonus
        if total > 99:
            total = 99
        total = int(total)
        bull_b = fvg_data.get('bull_b')
        bull_m = fvg_data.get('bull_m')
        bear_b = fvg_data.get('bear_b')
        bear_m = fvg_data.get('bear_m')
        bear_t = fvg_data.get('bear_t')
        if bull_b is not None and bull_m is not None and abs(last - bull_m) / last * 100 < 5:
            ptype = "PUMP"
            best = bull_m
            no_ret = bull_b * 0.985
        elif bear_b is not None and bear_m is not None and abs(last - bear_m) / last * 100 < 5:
            ptype = "DUMP"
            best = bear_m
            no_ret = bear_t * 1.015 if bear_t else last * 1.02
        else:
            ptype = "PUMP" if change >= -0.3 else "DUMP"
            if ptype == "PUMP":
                best = last * 0.994
                no_ret = rec_low * 0.985
            else:
                best = last * 1.006
                no_ret = rec_high * 1.015
        if ptype == "PUMP":
            if best > last * 0.998:
                best = last * 0.998
            stop = no_ret * 0.994
            tp1 = best * 1.028
            tp2 = best * 1.065
            if tp1 <= last:
                tp1 = last * 1.02
            if tp2 <= tp1:
                tp2 = tp1 * 1.03
        else:
            if best < last * 1.002:
                best = last * 1.002
            stop = no_ret * 1.006
            tp1 = best * 0.972
            tp2 = best * 0.935
            if tp1 >= last:
                tp1 = last * 0.98
            if tp2 >= tp1:
                tp2 = tp1 * 0.97
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

if st.sidebar.button("اختبار تليجرام"):
    test_sig = {}
    test_sig['symbol'] = 'TESTUSDT'
    test_sig['score'] = 80
    test_sig['type'] = 'PUMP'
    test_sig['price'] = 1
    test_sig['best_entry'] = 0.99
    test_sig['no_return_point'] = 0.98
    test_sig['stop_loss'] = 0.97
    test_sig['TP1'] = 1.02
    test_sig['TP2'] = 1.05
    if send_tg_alert(test_sig):
        st.sidebar.success("تليجرام شغال!")
    else:
        st.sidebar.error("فشل")

if st.button("افحص قبل الحركة", type="primary"):
    st.cache_data.clear()
    st.rerun()

symbols, src = get_all_symbols()
st.write(f"تم جلب {len(symbols)} عملة من {src} - هيفحص اول {limit_coins}")

to_scan = symbols[:limit_coins]
results = []
prog = st.progress(0)
stat = st.empty()
for i, sym in enumerate(to_scan):
    prog.progress((i+1)/len(to_scan))
    stat.text(f"يفحص: {sym} {i+1}/{len(to_scan)}")
    df = get_klines(sym)
    if df is not None:
        res = ultimate_score(df, sym, memory)
        if res and res['score'] >= min_score:
            if mode == "بمب بس" and res['type'] != "PUMP":
                pass
            elif mode == "دمب بس" and res['type'] != "DUMP":
                pass
            else:
                results.append(res)
    time.sleep(0.02)
prog.empty()
stat.empty()

if results:
    memory['total'] = memory.get('total',0)+1
    save_memory(memory)
    st.session_state['mem'] = memory

if results:
    df_res = pd.DataFrame(results).sort_values('score', ascending=False)
    st.success(f"تنبؤ {len(df_res)} عملة")
    c1,c2 = st.columns(2)
    c1.metric("بمب", len([r for r in results if r['type']=='PUMP']))
    c2.metric("دمب", len([r for r in results if r['type']=='DUMP']))
    st.dataframe(df_res, use_container_width=True)
    if send_tg:
        sent = 0
        for sig in df_res.head(5).to_dict('records'):
            if send_tg_alert(sig):
                sent += 1
                time.sleep(0.5)
        if sent > 0:
            st.success(f"اتبعت {sent} للتليجرام!")
    top = df_res.iloc[0]
    st.divider()
    st.subheader(f"افضل: {top['symbol']} {top['type']} سكور {top['score']}")
    c1,c2,c3 = st.columns(3)
    c1.metric("السعر", f"{top['price']}")
    c1.metric("دخول", f"{top['best_entry']}")
    c2.metric("الغاء", f"{top['no_return_point']}")
    c2.metric("ستوب", f"{top['stop_loss']}")
    c3.metric("هدف1", f"{top['TP1']}")
    c3.metric("هدف2", f"{top['TP2']}")
else:
    st.error(f"مفيش فوق {min_score} - نزله لـ 20")
