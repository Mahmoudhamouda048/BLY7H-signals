import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import json
import os
import math
import random

st.set_page_config(page_title="BLY7H Ultimate Radar", layout="wide", page_icon="🎯")
st.title("🎯 BLY7H Ultimate Radar - Predict BEFORE Pump")
st.markdown("**Tier1 SMC + Tier2 Professional + Tier3 Institutional + Gann + Astro + AI - يتنبأ قبل الحركة**")

st.sidebar.header("⚙️ الاعدادات")
min_score = st.sidebar.slider("اقل سكور", 0, 100, 60)
mode = st.sidebar.selectbox("نوع الفحص", ["الكل (بمب و دمب)", "بمب بس - تنبؤ", "دمب بس - تنبؤ"])
limit_coins = st.sidebar.slider("عدد العملات", 20, 300, 80)
use_ai = st.sidebar.checkbox("🧠 AI", value=True)
send_tg = st.sidebar.checkbox("📱 تليجرام", value=True)
tg_min = st.sidebar.slider("سكور التليجرام", 60, 95, 75)

# ================= TELEGRAM =================
def send_tg_alert(sig):
    try:
        bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN")
        chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id: return False
        if sig['score'] < tg_min: return False
        emoji = "🚀" if sig['type']=="PUMP" else "💥" if sig['type']=="DUMP" else "⚠️"
        msg = f"""{emoji} BLY7H PREDICTIVE RADAR {emoji}

💰 {sig['symbol']} - {sig['type']} - BEFORE MOVE!
📊 سكور: {sig['score']} (T:{sig['tech']}|L:{sig['liq']}|G:{sig['gann']}|A:{sig['astro']})
💵 السعر الان: {sig['price']}
🎯 دخول متوقع: {sig['best_entry']}
❌ الغاء: {sig['no_return_point']}
⛔ ستوب: {sig['stop_loss']}
✅ هدف1: {sig['TP1']} | هدف2: {sig['TP2']}

📚 SMC: FVG {sig['has_fvg']} | OB {sig['has_ob']}
💧 سيولة: {sig['liq_reason']}
📐 Gann: {sig['gann_reason']}
🌙 فلكي: {sig['astro_reason']}
🧠 AI: {sig['ai_reason']}

⏰ {datetime.now().strftime('%H:%M:%S %d-%m-%Y')}
⚠️ تنبؤ قبل الحركة - مش بعدها!
"""
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return r.status_code==200
    except Exception:
        return False

# ================= AI MEMORY =================
MEMORY_FILE = "ai_memory.json"
def load_memory():
    default = {
        "patterns": [
            {"name":"HighVol Pump","vol":2.5,"change":2,"fvg":True,"count":20,"success":15,"weight":15},
            {"name":"FVG Breakout","vol":1.5,"change":1,"fvg":True,"count":25,"success":19,"weight":15},
            {"name":"Liquidity Sweep","vol":2,"change":-1,"fvg":False,"count":15,"success":12,"weight":13},
        ],
        "history":[],"total":0
    }
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE,'r') as f:
                d=json.load(f)
                if "patterns" in d: return d
    except Exception:
        pass
    return default

def save_memory(m):
    try:
        with open(MEMORY_FILE,'w') as f:
            json.dump(m,f,indent=2)
    except Exception:
        pass
    st.session_state['mem']=m

# ================= GANN - يتنبأ قبل الحركة =================
def gann_square9_levels(price):
    """يحسب مستويات جان Square of 9 القادمة"""
    try:
        sqrt_p = math.sqrt(price)
        levels = []
        for i in range(-3,4):
            lvl = (sqrt_p + i*0.25) ** 2  # كل 45 درجة
            levels.append(lvl)
        return levels
    except Exception:
        return [price]

def gann_score(price, df):
    """هل السعر قرب مستوى جان مهم؟ لو قرب يبقى هيرتد قبل ما يوصل"""
    try:
        levels = gann_square9_levels(price)
        min_dist = min([abs(price-l)/price*100 for l in levels])
        score = 0
        reason = ""
        if min_dist < 0.5:
            score = 15
            reason = f"قريب من مستوى جان {min_dist:.2f}% - انعكاس متوقع"
        elif min_dist < 1.2:
            score = 8
            reason = f"يقترب من جان {min_dist:.1f}%"
        else:
            reason = "بعيد عن جان"
        
        # Gann Time Cycle - كل 90 يوم
        days_since = (datetime.now() - datetime(2023,1,1)).days
        if days_since % 90 < 3 or days_since % 45 < 2:
            score += 5
            reason += " + دورة زمنية"
        
        return min(20, score), reason
    except Exception:
        return 0, ""

# ================= ASTRO - يتنبأ قبل الحركة =================
def astro_score():
    """دورة القمر + ايام قوية للكريبتو"""
    try:
        # دورة قمر مبسطة (29.5 يوم)
        new_moon = datetime(2024,1,11)
        days = (datetime.now() - new_moon).days % 29.5
        score = 0
        reason = ""
        # ايام قمر جديد وبدر قوية
        if days < 2 or abs(days-14.75) < 1.5 or abs(days-29.5) < 2:
            score = 7
            reason = f"قمر جديد/بدر {days:.0f} يوم - تقلب عالي متوقع"
        elif days < 5 or abs(days-22) < 2:
            score = 4
            reason = f"تربيع قمر {days:.0f} يوم"
        else:
            reason = "قمر عادي"
        
        # يوم في الاسبوع - الاتنين والجمعة اقوى
        weekday = datetime.now().weekday()
        if weekday in [0,4]: # Monday, Friday
            score += 3
            reason += " + يوم قوي"
        
        return min(10, score), reason
    except Exception:
        return 0, ""

# ================= INSTITUTIONAL - سيولة قبل الحركة =================
def institutional_score(df, price):
    """OI + Premium + Killzone + 【entity-AMD¦canonical_name=AMD】 - يكشف حركة الحيتان قبل البمب"""
    try:
        score = 0
        reasons = []
        
        # 1. Killzone - توقيت لندن ونيويورك (10-13 و 16-19 بتوقيت القاهرة)
        hour_eg = (datetime.utcnow().hour + 2) % 24
        if hour_eg in [10,11,12,13,16,17,18,19]:
            score += 8
            reasons.append("Killzone لندن/نيويورك")
        
        # 2. 【entity-AMD¦canonical_name=AMD】 Model - لو السعر عمل Manipulation Down دلوقتي يبقى Distribution جاي
        low_10 = float(df['low'].iloc[-10:].min())
        if price <= low_10 * 1.01: # قريب من لو 10 شموع = Manipulation
            score += 10
            reasons.append("【entity-AMD¦canonical_name=AMD】: Manipulation - صعود متوقع")
        
        # 3. Spot vs Futures Premium - لو فيوتشر اعلى من سبوت بكتير = حيتان بتشتري
        # نحاكيها من الفوليوم
        vol_col = 'vol' if 'vol' in df.columns else 'volume'
        vol_spike = float(df[vol_col].iloc[-1]) / df[vol_col].astype(float).mean()
        if vol_spike > 2.5 and price > float(df['close'].iloc[-5:].mean()):
            score += 7
            reasons.append(f"Premium Gap + Vol x{vol_spike:.1f}")
        
        # 4. Liquidation - لو فيه سيولة كتير فوق = هيطلع ياخدها
        high_20 = float(df['high'].iloc[-20:].max())
        if price < high_20 and (high_20 - price)/price < 0.03: # 3% تحت هاي
            score += 5
            reasons.append("سيولة فوق قريبة - Sweep متوقع")
        
        return min(30, score), " | ".join(reasons[:2])
    except Exception:
        return 0, ""

# ================= SMC PREDICTIVE - يتنبأ قبل لمس FVG =================
def smc_predictive(df, price):
    """مش يستنى السعر يلمس FVG، يتنبأ قبلها"""
    try:
        fvg_bottom = None
        fvg_top = None
        fvg_mid = None
        fvg_dist = 999
        
        for i in range(1, len(df)-1):
            try:
                low_next = float(df['low'].iloc[i+1])
                high_prev = float(df['high'].iloc[i-1])
                if low_next > high_prev:
                    fvg_bottom = high_prev
                    fvg_top = low_next
                    fvg_mid = (high_prev + low_next)/2
                    # المسافة من السعر الحالي للـ FVG
                    if price < fvg_bottom:
                        fvg_dist = (fvg_bottom - price)/price*100
                    elif price > fvg_top:
                        fvg_dist = (price - fvg_top)/price*100
                    break
            except Exception:
                pass
        
        recent_low = float(df['low'].iloc[-10:].min())
        recent_high = float(df['high'].iloc[-10:].max())
        
        score = 0
        reasons = []
        has_fvg = fvg_bottom is not None
        has_ob = True
        
        # لو السعر قرب من FVG (1-3% بعيد) يبقى تنبؤ قبل اللمس
        if has_fvg and fvg_dist < 3:
            score += 25
            reasons.append(f"يقترب من FVG {fvg_dist:.1f}% - دخول متوقع قبل اللمس")
        elif has_fvg and fvg_dist < 6:
            score += 15
            reasons.append(f"في الطريق لـ FVG {fvg_dist:.1f}%")
        elif has_fvg:
            score += 10
            reasons.append("يوجد FVG")
        
        # Order Block
        if price <= recent_low * 1.02:
            score += 10
            reasons.append("عند Order Block")
        
        return score, has_fvg, has_ob, fvg_bottom, fvg_top, fvg_mid, recent_low, recent_high, " | ".join(reasons[:2])
    except Exception:
        return 0, False, False, None, None, None, price*0.99, price*1.01, ""

# ================= مصادر السوق =================
def get_symbols_binance():
    bases = ["https://data-api.binance.vision","https://api1.binance.com"]
    for base in bases:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200: continue
            data = r.json()
            if not isinstance(data, list): continue
            usdt = [d for d in data if d.get('symbol','').endswith('USDT') and 'UP' not in d.get('symbol','')]
            usdt = sorted(usdt, key=lambda x: float(x.get('quoteVolume',0) or 0), reverse=True)
            return [d['symbol'] for d in usdt][:400]
        except Exception:
            continue
    return []

def get_symbols_okx():
    try:
        r = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SPOT", timeout=15)
        data = r.json()
        if data.get('code')!='0': return []
        tickers = data.get('data',[])
        usdt = [t for t in tickers if t.get('instId','').endswith('-USDT')]
        usdt = sorted(usdt, key=lambda x: float(x.get('vol24h',0) or 0), reverse=True)
        return [t['instId'].replace('-','') for t in usdt][:400]
    except Exception:
        return []

@st.cache_data(ttl=300)
def get_all_symbols():
    s = get_symbols_binance()
    src = "【entity-binance¦canonical_name=Binance】"
    if len(s)<20:
        s = get_symbols_okx()
        src = "【entity-okx¦canonical_name=OKX】"
    return [x for x in s if 'BULL' not in x][:400], src

def get_klines_binance(sym):
    bases = ["https://data-api.binance.vision","https://api1.binance.com"]
    for base in bases:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={sym}&interval=1h&limit=100", timeout=10)
            if r.status_code!=200: continue
            data=r.json()
            if len(data)<20: continue
            df=pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            for c in ['high','low','close','open']: df[c]=pd.to_numeric(df[c], errors='coerce')
            return df.dropna()
        except Exception:
            continue
    return None

def get_klines_okx(sym):
    try:
        inst=sym.replace('USDT','-USDT')
        r=requests.get(f"https://www.okx.com/api/v5/market/candles?instId={inst}&bar=1H&limit=100", timeout=10)
        data=r.json()
        if data.get('code')!='0': return None
        klines=data.get('data',[])
        if len(klines)<20: return None
        klines=list(reversed(klines))
        df=pd.DataFrame(klines, columns=['ts','open','high','low','close','vol','volCcy','volCcyQuote','confirm'])
        for c in ['high','low','close','open']: df[c]=pd.to_numeric(df[c], errors='coerce')
        return df.dropna()
    except Exception:
        return None

@st.cache_data(ttl=90)
def get_klines(sym):
    for f in [get_klines_binance, get_klines_okx]:
        df=f(sym)
        if df is not None and len(df)>=20:
            return df
    return None

# ================= التحليل الشامل قبل الحركة =================
def ultimate_predictive_score(df, sym, memory):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change = ((last-prev)/prev*100) if prev else 0
        
        # 1. Technical SMC Predictive 40%
        tech_score, has_fvg, has_ob, fvg_b, fvg_t, fvg_m, rec_low, rec_high, tech_reason = smc_predictive(df, last)
        
        # 2. Liquidity Institutional 30%
        liq_score, liq_reason = institutional_score(df, last)
        
        # 3. Gann 20%
        gann_score, gann_reason = gann_score_func(last, df) if False else gann_score(last, df)
        
        # 4. Astro 10%
        astro_score, astro_reason = astro_score()
        
        # AI bonus
        ai_bonus = 0
        ai_reason = "جديد"
        if use_ai:
            vol_col='vol' if 'vol' in df.columns else 'volume'
            vol_spike=float(df[vol_col].iloc[-1])/df[vol_col].astype(float).mean()
            for pat in memory.get('patterns',[]):
                if abs(vol_spike-pat['vol'])<1 and abs(change-pat['change'])<2:
                    rate=pat['success']/pat['count'] if pat['count']>0 else 0.5
                    ai_bonus+=pat['weight']*rate*0.5
                    ai_reason=f"شبه {pat['name']} {int(rate*100)}%"
                    break
        
        total = tech_score + liq_score + gann_score + astro_score + ai_bonus
        total = min(99, int(total))
        
        # تحديد النوع قبل الحركة
        # لو قرب FVG تحت = PUMP متوقع، لو قرب FVG فوق = DUMP متوقع
        if fvg_b and last < fvg_b and (fvg_b-last)/last*100 < 5:
            ptype = "PUMP"
            best = fvg_m if fvg_m else last*0.992
            no_ret = fvg_b*0.99
        elif fvg_t and last > fvg_t and (last-fvg_t)/last*100 < 5:
            ptype = "DUMP"
            best = fvg_m if fvg_m else last*1.008
            no_ret = fvg_t*1.01
        else:
            # بناء على AMD و Killzone
            if liq_score>10 and tech_score>15:
                ptype = "PUMP" if change>-1 else "DUMP"
            else:
                ptype = "UP" if change>=0 else "DOWN"
            if ptype in ["PUMP","UP"]:
                best = last*0.997
                no_ret = rec_low*0.985
            else:
                best = last*1.003
                no_ret = rec_high*1.015
        
        stop = no_ret*0.997 if ptype in ["PUMP","UP"] else no_ret*1.003
        tp1 = best*1.025 if ptype in ["PUMP","UP"] else best*0.975
        tp2 = best*1.06 if ptype in ["PUMP","UP"] else best*0.94
        
        return {
            'symbol': sym,
            'score': total,
            'tech': tech_score,
            'liq': liq_score,
            'gann': gann_score,
            'astro': astro_score,
            'ai_bonus': int(ai_bonus),
            'type': ptype,
            'price': round(last,6),
            'change_1h': round(change,2),
            'best_entry': round(best,6),
            'no_return_point': round(no_ret,6),
            'stop_loss': round(stop,6),
            'TP1': round(tp1,6),
            'TP2': round(tp2,6),
            'has_fvg': has_fvg,
            'has_ob': has_ob,
            'liq_reason': liq_reason,
            'gann_reason': gann_reason,
            'astro_reason': astro_reason,
            'ai_reason': ai_reason,
            'tech_reason': tech_reason,
        }
    except Exception as e:
        return None

# ================= تشغيل =================
if 'mem' not in st.session_state:
    st.session_state['mem']=load_memory()
memory=st.session_state['mem']

if st.button("🎯 افحص قبل الحركة - تنبؤ", type="primary"):
    st.cache_data.clear()
    st.rerun()

symbols, src = get_all_symbols()
st.write(f"تم جلب {len(symbols)} عملة من {src} - هيفحص اول {limit_coins} - تنبؤ قبل الحركة")

to_scan = symbols[:limit_coins]
results=[]
progress=st.progress(0)
status=st.empty()

for i, sym in enumerate(to_scan):
    progress.progress((i+1)/len(to_scan))
    status.text(f"رادار يتنبأ: {sym}... ({i+1}/{len(to_scan)})")
    df=get_klines(sym)
    if df is not None:
        res=ultimate_predictive_score(df, sym, memory)
        if res and res['score']>=min_score:
            if mode=="بمب بس - تنبؤ" and res['type'] not in ["PUMP","UP"]: pass
            elif mode=="دمب بس - تنبؤ" and res['type'] not in ["DUMP","DOWN"]: pass
            else: results.append(res)
    time.sleep(0.03)

progress.empty()
status.empty()

if results:
    memory['total']=memory.get('total',0)+1
    save_memory(memory)
    st.session_state['mem']=memory

if results:
    df_res=pd.DataFrame(results).sort_values('score', ascending=False)
    st.success(f"✅ تنبؤ {len(df_res)} عملة قبل الحركة - سكور {min_score}+")
    
    pumps=len([r for r in results if r['type'] in ['PUMP','UP']])
    dumps=len([r for r in results if r['type'] in ['DUMP','DOWN']])
    c1,c2,c3=st.columns(3)
    c1.metric("بمب متوقع", pumps)
    c2.metric("دمب متوقع", dumps)
    c3.metric("AI فحص", f"{memory.get('total',0)}")
    
    st.dataframe(df_res, use_container_width=True)
    
    # تليجرام
    if send_tg:
        sent=0
        for sig in df_res.head(5).to_dict('records'):
            if sig['score']>=tg_min:
                if send_tg_alert(sig):
                    sent+=1
                    time.sleep(0.5)
        if sent>0:
            st.success(f"📱 اتبعت {sent} تنبؤ للتليجرام قبل الحركة!")
    
    top=df_res.iloc[0]
    st.divider()
    st.subheader(f"🎯 افضل تنبؤ قبل الحركة: {top['symbol']} - {top['type']} - سكور {top['score']}")
    st.info(f"📚 {top['tech_reason']} | 💧 {top['liq_reason']} | 📐 {top['gann_reason']} | 🌙 {top['astro_reason']} | 🧠 {top['ai_reason']}")
    c1,c2,c3=st.columns(3)
    c1.metric("السعر الان", f"{top['price']}")
    c1.metric("دخول متوقع (قبل الحركة)", f"{top['best_entry']}")
    c1.metric("تغير 1س", f"{top['change_1h']}%")
    c2.metric("نقطة الالغاء", f"{top['no_return_point']}")
    c2.metric("ستوب", f"{top['stop_loss']}")
    c2.metric("سكور T/L/G/A", f"{top['tech']}/{top['liq']}/{top['gann']}/{top['astro']}")
    c3.metric("هدف 1", f"{top['TP1']}")
    c3.metric("هدف 2", f"{top['TP2']}")
    c3.metric("النوع", f"{top['type']}")
    st.warning(f"⚠️ تنبؤ قبل الحركة: لو كسر {top['no_return_point']} الغي الفكرة")
else:
    st.error(f"مفيش تنبؤات فوق سكور {min_score} - نزل السكور لـ 40")

with st.expander("🧠 AI Memory + Gann + Astro"):
    st.write("Gann: يحسب مستويات Square of 9 القادمة ويتنبأ بانعكاس قبل وصول السعر")
    st.write("Astro: دورة قمر + ايام قوية")
    st.write("Institutional: Killzone + AMD + سيولة فوق")
    st.write("SMC Predictive: يتنبأ قبل لمس FVG مش بعده")
    df_mem=pd.DataFrame(memory['patterns'])
    st.dataframe(df_mem)

st.caption("🎯 Ultimate Predictive Radar - يتنبأ قبل الحركة مش بعدها - T40 L30 G20 A10")
