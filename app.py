import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time, json, os, math

st.set_page_config(page_title="BLY7H PUMP DUMP RADAR", layout="wide", page_icon="💥")
st.title("💥 BLY7H PUMP DUMP - Predictive OI CVD")
st.caption("تنبؤ قبل الحركة: OI Divergence + CVD + Vol + FVG + Gann")

st.sidebar.header("Settings")
min_score = st.sidebar.slider("اقل سكور", 0, 100, 55)
mode = st.sidebar.selectbox("نوع الفحص", ["الكل", "بمب بس", "دمب بس"])
limit_coins = st.sidebar.slider("عدد العملات", 20, 300, 100)
filter_stable = st.sidebar.checkbox("فلتر المستقرة", value=True)
send_tg = st.sidebar.checkbox("تليجرام", value=True)
tg_min = st.sidebar.slider("سكور التليجرام", 20, 95, 70)

STABLES = ["USDCUSDT","USDTUSDT","BUSDUSDT","TUSDUSDT","USDPUSDT","DAIUSDT","FDUSDUSDT","USDeUSDT","USD1USDT","RLUSDUSDT","XUSDUSDT","EURUSDT","PYUSDUSDT","GUSDUSDT","USDXUSDT","USDGUSDT"]

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
        lines.append(f"{emoji} BLY7H {sig['type']} PREDICTIVE {emoji}")
        lines.append(f"💰 {sig['symbol']} - {sig['vol_reason']}")
        lines.append(f"📊 سكور: {sig['score']} Vol x{sig['vol_spike']} تغير {sig['change_1h']}%")
        lines.append(f"📈 OI: {sig['oi_reason']}")
        lines.append(f"💧 CVD: {sig['cvd_reason']}")
        lines.append(f"💵 الان: {sig['price']}")
        lines.append(f"🎯 دخول: {sig['best_entry']}")
        lines.append(f"❌ الغاء: {sig['no_return_point']}")
        lines.append(f"⛔ ستوب: {sig['stop_loss']}")
        lines.append(f"✅ هدف1: {sig['TP1']} هدف2: {sig['TP2']}")
        lines.append(f"📚 {sig['tech_reason']}")
        txt = "\n".join(lines)
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": txt}, timeout=10)
        return r.status_code == 200
    except:
        return False

def load_memory():
    default = {"total": 0}
    try:
        if os.path.exists("ai_memory.json"):
            with open("ai_memory.json", 'r') as f:
                return json.load(f)
    except:
        pass
    return default

def save_memory(m):
    try:
        with open("ai_memory.json", 'w') as f:
            json.dump(m, f, indent=2)
    except:
        pass
    st.session_state['mem'] = m

def get_oi(symbol):
    try:
        # 【entity-Binance¦canonical_name=Binance】 Futures OI
        r = requests.get(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return float(data.get('openInterest', 0))
    except:
        pass
    return 0

def get_oi_history(symbol):
    try:
        # OI history اخر ساعة
        r = requests.get(f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period=5m&limit=12", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if len(data) >= 2:
                first = float(data[0]['sumOpenInterest'])
                last = float(data[-1]['sumOpenInterest'])
                change = (last - first) / first * 100 if first>0 else 0
                return change, last
    except:
        pass
    return 0, 0

def calc_oi_divergence(price_change, oi_change):
    # OI بيزيد والسعر ثابت او نازل خفيف = تجميع حيتان = بمب جاي
    # OI بيزيد والسعر طالع = تأكيد بمب
    # OI بينزل والسعر طالع = ضعف = دمب جاي
    score = 0
    reason = "OI طبيعي"
    if oi_change > 5 and price_change < 1 and price_change > -1:
        score = 20
        reason = f"OI +{oi_change:.1f}% والسعر ثابت - تجميع حيتان - بمب قادم"
    elif oi_change > 3 and price_change > 1:
        score = 15
        reason = f"OI +{oi_change:.1f}% + سعر +{price_change:.1f}% - تأكيد بمب"
    elif oi_change < -3 and price_change > 1:
        score = -10
        reason = f"OI {oi_change:.1f}% والسعر طالع - ضعف - دمب محتمل"
    elif oi_change > 5 and price_change < -1:
        score = 15
        reason = f"OI +{oi_change:.1f}% والسعر نازل - تجميع شورت - دمب قادم"
    return score, reason

def calc_cvd(df):
    # CVD مبسط: لو الشموع الخضرا فوليومها اعلى من الحمرا = شراء
    try:
        green_vol = 0
        red_vol = 0
        for i in range(-10, 0):
            c = float(df['close'].iloc[i])
            o = float(df['open'].iloc[i])
            v = float(df['vol'].iloc[i])
            if c > o:
                green_vol += v
            else:
                red_vol += v
        total = green_vol + red_vol
        if total == 0:
            return 0, "CVD متوازن"
        cvd_pct = (green_vol - red_vol) / total * 100
        if cvd_pct > 30:
            return 15, f"CVD +{cvd_pct:.0f}% شراء قوي - بمب"
        elif cvd_pct < -30:
            return 15, f"CVD {cvd_pct:.0f}% بيع قوي - دمب"
        elif cvd_pct > 15:
            return 8, f"CVD +{cvd_pct:.0f}% شراء"
        elif cvd_pct < -15:
            return 8, f"CVD {cvd_pct:.0f}% بيع"
        else:
            return 0, f"CVD {cvd_pct:.0f}% متوازن"
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
        
        # OI الحقيقي
        oi_change, oi_now = get_oi_history(sym)
        oi_score, oi_reason = calc_oi_divergence(change_1h, oi_change)
        
        # CVD الحقيقي
        cvd_score, cvd_reason = calc_cvd(df)
        
        has_fvg, fvg_data, rec_low, rec_high = calc_smc(df, last)
        
        # فلتر بمب ودمب حقيقي فقط
        if vol_spike < 1.5 and abs(oi_change) < 2 and cvd_score < 5:
            return None
        
        score = 0
        vol_reason = ""
        
        # اساس البمب: OI + CVD + Vol
        if vol_spike > 2.0 or oi_change > 3 or cvd_score > 8:
            if change_1h > -1:  # مش نازل جامد
                if oi_score >= 15 or cvd_score >= 10:
                    score = 40 + oi_score + cvd_score + min(vol_spike*3, 15)
                    ptype = "PUMP"
                    vol_reason = f"PUMP قبل الحركة OI {oi_change:.1f}% CVD {cvd_reason} Vol x{vol_spike:.1f}"
                elif vol_spike > 2.5 and change_1h > 0.5:
                    score = 35 + vol_spike*3 + change_1h*2
                    ptype = "PUMP"
                    vol_reason = f"PUMP Vol x{vol_spike:.1f} +{change_1h:.1f}%"
                else:
                    score = 25 + vol_spike*2
                    ptype = "PUMP"
                    vol_reason = f"تجميع Vol x{vol_spike:.1f} قبل بمب"
            else:
                score = 30 + vol_spike*3 + abs(change_1h)
                ptype = "DUMP"
                vol_reason = f"DUMP Vol x{vol_spike:.1f} {change_1h:.1f}%"
        elif change_1h < -1.5 and vol_spike > 1.8:
            score = 35 + abs(change_1h)*2 + vol_spike*2
            ptype = "DUMP"
            vol_reason = f"DUMP حقيقي Vol x{vol_spike:.1f} {change_1h:.1f}%"
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
            if bull_b is not None and bull_m is not None:
                best = bull_m
                no_ret = bull_b * 0.985
            else:
                best = last * 0.993
                no_ret = rec_low * 0.98
            best = min(best, last * 0.998)
            stop = no_ret * 0.99
            tp1 = last * 1.04
            tp2 = last * 1.08
            if stop >= best:
                stop = best * 0.97
            if no_ret >= best:
                no_ret = best * 0.985
        else:
            if bear_b is not None and bear_m is not None:
                best = bear_m
                no_ret = bear_t * 1.015 if bear_t else last * 1.02
            else:
                best = last * 1.007
                no_ret = rec_high * 1.02
            best = max(best, last * 1.002)
            stop = no_ret * 1.01
            tp1 = last * 0.96
            tp2 = last * 0.92
            if stop <= best:
                stop = best * 1.03
            if no_ret <= best:
                no_ret = best * 1.015
        
        return {
            'symbol': sym, 'score': score, 'type': ptype, 'price': round(last,6),
            'change_1h': round(change_1h,2), 'vol_spike': round(vol_spike,2),
            'oi_change': round(oi_change,2), 'best_entry': round(best,6),
            'no_return_point': round(no_ret,6), 'stop_loss': round(stop,6),
            'TP1': round(tp1,6), 'TP2': round(tp2,6), 'has_fvg': has_fvg,
            'tech_reason': "FVG" if has_fvg else "No FVG",
            'vol_reason': vol_reason, 'oi_reason': oi_reason, 'cvd_reason': cvd_reason
        }
    except Exception as e:
        return None

if 'mem' not in st.session_state:
    st.session_state['mem'] = load_memory()
memory = st.session_state['mem']

if st.sidebar.button("اختبار تليجرام"):
    test_sig = {'symbol':'TESTUSDT','score':80,'type':'PUMP','price':1,'change_1h':2,'vol_spike':3,'best_entry':0.99,'no_return_point':0.98,'stop_loss':0.97,'TP1':1.04,'TP2':1.08,'tech_reason':'FVG','vol_reason':'PUMP','oi_reason':'OI +5% تجميع','cvd_reason':'CVD شراء'}
    if send_tg_alert(test_sig):
        st.sidebar.success("شغال!")
    else:
        st.sidebar.error("فشل")

if st.button("💥 افحص تنبؤ OI + CVD", type="primary"):
    st.cache_data.clear()
    st.rerun()

symbols, src = get_all_symbols()
st.write(f"تم جلب {len(symbols)} عملة - هيفحص اول {limit_coins} - تنبؤ قبل الحركة OI + CVD + Vol")

to_scan = symbols[:limit_coins]
results = []
prog = st.progress(0)
stat = st.empty()
for i, sym in enumerate(to_scan):
    prog.progress((i+1)/len(to_scan))
    stat.text(f"يفحص OI CVD: {sym} {i+1}/{len(to_scan)}")
    df = get_klines(sym)
    if df is not None:
        res = pump_dump_predictive(df, sym)
        if res:
            if mode == "بمب بس" and res['type'] != "PUMP":
                pass
            elif mode == "دمب بس" and res['type'] != "DUMP":
                pass
            else:
                results.append(res)
    time.sleep(0.05)
prog.empty()
stat.empty()

if results:
    memory['total'] = memory.get('total',0)+1
    save_memory(memory)
    st.session_state['mem'] = memory

if results:
    df_res = pd.DataFrame(results).sort_values('score', ascending=False)
    st.success(f"💥 {len(df_res)} تنبؤ قبل الحركة OI + CVD")
    c1,c2 = st.columns(2)
    c1.metric("🚀 بمب قبل", len([r for r in results if r['type']=='PUMP']))
    c2.metric("💥 دمب قبل", len([r for r in results if r['type']=='DUMP']))
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
    st.subheader(f"🎯 افضل تنبؤ: {top['symbol']} {top['type']} سكور {top['score']}")
    st.info(f"{top['oi_reason']} | {top['cvd_reason']}")
    c1,c2,c3 = st.columns(3)
    c1.metric("السعر", f"{top['price']}")
    c1.metric("دخول", f"{top['best_entry']}")
    c2.metric("الغاء", f"{top['no_return_point']}")
    c2.metric("ستوب", f"{top['stop_loss']}")
    c3.metric("هدف1", f"{top['TP1']}")
    c3.metric("هدف2", f"{top['TP2']}")
    if top['type'] == "PUMP":
        st.success(f"PUMP قبل الحركة: دخول تحت {top['price']} - OI {top['oi_change']}% - {top['vol_reason']}")
    else:
        st.error(f"DUMP قبل الحركة: دخول فوق {top['price']} - OI {top['oi_change']}% - {top['vol_reason']}")
else:
    st.warning(f"مفيش تنبؤ قوي فوق {min_score} - نزله لـ 50 او استنى تجميع حيتان")
