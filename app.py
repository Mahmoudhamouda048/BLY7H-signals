import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time, json, os, math

st.set_page_config(page_title="BLY7H Ultimate Radar", layout="wide", page_icon="🎯")
st.title("🎯 BLY7H Ultimate Radar - Predict BEFORE Pump")

st.sidebar.header("⚙️ الاعدادات")
min_score = st.sidebar.slider("اقل سكور للجدول", 0, 100, 40)
mode = st.sidebar.selectbox("نوع الفحص", ["الكل", "بمب بس", "دمب بس"])
limit_coins = st.sidebar.slider("عدد العملات", 20, 300, 80)
use_ai = st.sidebar.checkbox("🧠 AI", value=True)
send_tg = st.sidebar.checkbox("📱 تليجرام", value=True)
tg_min = st.sidebar.slider("سكور التليجرام", 20, 95, 50)

# ========== TELEGRAM ==========
def send_tg_alert(sig):
    try:
        bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN")
        chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            st.error("Secrets ناقص")
            return False
        if sig['score'] < tg_min:
            return False
        emoji = "🚀" if "PUMP" in sig['type'] else "💥"
        msg = f"""{emoji} BLY7H PREDICTIVE {emoji}
💰 {sig['symbol']} - {sig['type']} - قبل الحركة!
📊 سكور: {sig['score']} (T:{sig['tech']}|L:{sig['liq']}|G:{sig['gann']}|A:{sig['astro']})
💵 الان: {sig['price']} | تغير: {sig['change_1h']}%
🎯 دخول متوقع: {sig['best_entry']}
❌ الغاء: {sig['no_return_point']}
⛔ ستوب: {sig['stop_loss']}
✅ هدف1: {sig['TP1']} | هدف2: {sig['TP2']}
📚 {sig['tech_reason']}
💧 {sig['liq_reason']}
📐 {sig['gann_reason']}
🌙 {sig['astro_reason']}
🧠 {sig['ai_reason']}
⏰ {datetime.now().strftime('%H:%M:%S %d-%m-%Y')}
"""
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return r.status_code==200
    except Exception as e:
        st.error(f"Telegram error: {e}")
        return False

# ========== MEMORY ==========
MEMORY_FILE="ai_memory.json"
def load_memory():
    default={"patterns":[{"name":"HighVol","vol":2.5,"change":2,"count":20,"success":15,"weight":10}],"total":0}
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE,'r') as f: return json.load(f)
    except: pass
    return default
def save_memory(m):
    try:
        with open(MEMORY_FILE,'w') as f: json.dump(m,f,indent=2)
    except: pass
    st.session_state['mem']=m

# ========== GANN ==========
def gann_levels(price):
    try:
        s=math.sqrt(price)
        return [(s+i*0.25)**2 for i in range(-3,4)]
    except: return [price]

def calc_gann(price):
    try:
        levels=gann_levels(price)
        dist=min([abs(price-l)/price*100 for l in levels])
        score=0
        reason=""
        if dist<0.5: score=12; reason=f"قريب جان {dist:.2f}% - انعكاس متوقع قبل"
        elif dist<1.5: score=7; reason=f"يقترب جان {dist:.1f}%"
        else: reason="بعيد عن جان"
        days=(datetime.now()-datetime(2023,1,1)).days
        if days%90<3 or days%45<2: score+=5; reason+=" + دورة زمنية"
        return min(20,score), reason
    except: return 5, ""

# ========== ASTRO ==========
def calc_astro():
    try:
        new_moon=datetime(2024,1,11)
        days=(datetime.now()-new_moon).days % 29.5
        score=0
        reason=""
        if days<2 or abs(days-14.75)<1.5: score=6; reason=f"قمر جديد/بدر {days:.0f} يوم - تقلب"
        elif days<5: score=3; reason=f"تربيع {days:.0f}"
        else: reason="قمر عادي"
        if datetime.now().weekday() in [0,4]: score+=3; reason+=" + يوم قوي"
        return min(10,score), reason
    except: return 2, ""

# ========== INSTITUTIONAL ==========
def calc_institutional(df, price):
    try:
        score=0; reasons=[]
        hour_eg=(datetime.utcnow().hour+2)%24
        if hour_eg in [10,11,12,13,16,17,18,19]: score+=7; reasons.append("Killzone")
        low_10=float(df['low'].iloc[-10:].min())
        if price <= low_10*1.015: score+=10; reasons.append("AMD Manipulation-صعود متوقع")
        vol_col='vol' if 'vol' in df.columns else 'volume'
        vol_spike=float(df[vol_col].iloc[-1])/df[vol_col].astype(float).mean()
        if vol_spike>2: score+=6; reasons.append(f"Vol x{vol_spike:.1f}")
        high_20=float(df['high'].iloc[-20:].max())
        if price < high_20 and (high_20-price)/price<0.03: score+=5; reasons.append("سيولة فوق - Sweep متوقع")
        # Base liquidity score
        score+=5
        return min(30,score), " | ".join(reasons) if reasons else "سيولة طبيعية"
    except: return 8, ""

# ========== SMC PREDICTIVE ==========
def calc_smc(df, price):
    try:
        fvg_b=fvg_t=fvg_m=None; fvg_dist=999
        for i in range(1,len(df)-1):
            try:
                low_next=float(df['low'].iloc[i+1]); high_prev=float(df['high'].iloc[i-1])
                if low_next>high_prev:
                    fvg_b=high_prev; fvg_t=low_next; fvg_m=(high_prev+low_next)/2
                    if price < fvg_b: fvg_dist=(fvg_b-price)/price*100
                    elif price > fvg_t: fvg_dist=(price-fvg_t)/price*100
                    else: fvg_dist=0
                    break
            except: pass
        recent_low=float(df['low'].iloc[-10:].min())
        recent_high=float(df['high'].iloc[-10:].max())
        score=15  # base
        reasons=[]
        has_fvg=fvg_b is not None
        if has_fvg and fvg_dist<3: score+=20; reasons.append(f"يقترب FVG {fvg_dist:.1f}% - قبل اللمس")
        elif has_fvg and fvg_dist<6: score+=10; reasons.append(f"في الطريق FVG {fvg_dist:.1f}%")
        elif has_fvg: score+=5; reasons.append("يوجد FVG")
        if price <= recent_low*1.02: score+=10; reasons.append("عند OB")
        return score, has_fvg, True, fvg_b, fvg_t, fvg_m, recent_low, recent_high, " | ".join(reasons) if reasons else "SMC عادي"
    except: return 15, False, False, None, None, None, price*0.99, price*1.01, ""

# ========== SYMBOLS ==========
def get_symbols_binance():
    bases=["https://data-api.binance.vision","https://api1.binance.com"]
    for base in bases:
        try:
            r=requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code!=200: continue
            data=r.json()
            usdt=[d for d in data if d.get('symbol','').endswith('USDT')]
            usdt=sorted(usdt, key=lambda x: float(x.get('quoteVolume',0) or 0), reverse=True)
            return [d['symbol'] for d in usdt][:400]
        except: continue
    return []
def get_symbols_okx():
    try:
        r=requests.get("https://www.okx.com/api/v5/market/tickers?instType=SPOT", timeout=15)
        data=r.json()
        if data.get('code')!='0': return []
        tickers=data.get('data',[])
        usdt=[t for t in tickers if t.get('instId','').endswith('-USDT')]
        usdt=sorted(usdt, key=lambda x: float(x.get('vol24h',0) or 0), reverse=True)
        return [t['instId'].replace('-','') for t in usdt][:400]
    except: return []
@st.cache_data(ttl=300)
def get_all_symbols():
    s=get_symbols_binance(); src=" 【entity-binance¦canonical_name=binance】"
    if len(s)<20: s=get_symbols_okx(); src=" 【entity-okx¦canonical_name=okx】"
    return [x for x in s if 'BULL' not in x][:400], src

def get_klines_binance(sym):
    bases=["https://data-api.binance.vision","https://api1.binance.com"]
    for base in bases:
        try:
            r=requests.get(f"{base}/api/v3/klines?symbol={sym}&interval=1h&limit=100", timeout=10)
            if r.status_code!=200: continue
            data=r.json()
            if len(data)<20: continue
            df=pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            for c in ['high','low','close','open']: df[c]=pd.to_numeric(df[c], errors='coerce')
            return df.dropna()
        except: continue
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
    except: return None
@st.cache_data(ttl=90)
def get_klines(sym):
    for f in [get_klines_binance, get_klines_okx]:
        df=f(sym)
        if df is not None and len(df)>=20: return df
    return None

def ultimate_score(df, sym, memory):
    try:
        last=float(df['close'].iloc[-1]); prev=float(df['close'].iloc[-2])
        change=((last-prev)/prev*100) if prev else 0
        tech, has_fvg, has_ob, fvg_b, fvg_t, fvg_m, rec_low, rec_high, tech_r = calc_smc(df, last)
        liq, liq_r = calc_institutional(df, last)
        gann, gann_r = calc_gann(last)
        astro, astro_r = calc_astro()
        ai_bonus=0; ai_r="جديد"
        if use_ai:
            vol_col='vol' if 'vol' in df.columns else 'volume'
            vs=float(df[vol_col].iloc[-1])/df[vol_col].astype(float).mean()
            for pat in memory.get('patterns',[]):
                if abs(vs-pat.get('vol',2))<1.5:
                    ai_bonus=5; ai_r=f"شبه {pat['name']}"
                    break
        total=tech+liq+gann+astro+ai_bonus
        total=min(99,int(total))
        # predictive entry
        if fvg_b and last < fvg_b and (fvg_b-last)/last*100<5:
            ptype="PUMP"; best=fvg_m if fvg_m else last*0.992; no_ret=fvg_b*0.99
        elif fvg_t and last > fvg_t and (last-fvg_t)/last*100<5:
            ptype="DUMP"; best=fvg_m if fvg_m else last*1.008; no_ret=fvg_t*1.01
        else:
            ptype="PUMP" if change>-0.5 else "DUMP"
            if ptype=="PUMP": best=last*0.997; no_ret=rec_low*0.985
            else: best=last*1.003; no_ret=rec_high*1.015
        stop=no_ret*0.997 if ptype=="PUMP" else no_ret*1.003
        tp1=best*1.025 if ptype=="PUMP" else best*0.975
        tp2=best*1.06 if ptype=="PUMP" else best*0.94
        return {'symbol':sym,'score':total,'tech':tech,'liq':liq,'gann':gann,'astro':astro,'ai_bonus':int(ai_bonus),'type':ptype,'price':round(last,6),'change_1h':round(change,2),'best_entry':round(best,6),'no_return_point':round(no_ret,6),'stop_loss':round(stop,6),'TP1':round(tp1,6),'TP2':round(tp2,6),'has_fvg':has_fvg,'has_ob':has_ob,'liq_reason':liq_r,'gann_reason':gann_r,'astro_reason':astro_r,'ai_reason':ai_r,'tech_reason':tech_r}
    except Exception as e:
        return None

# ========== RUN ==========
if 'mem' not in st.session_state: st.session_state['mem']=load_memory()
memory=st.session_state['mem']

if st.sidebar.button("🧪 اختبار تليجرام"):
    test_sig={'symbol':'TESTUSDT','score':80,'tech':20,'liq':20,'gann':15,'astro':5,'type':'PUMP','price':1,'change_1h':2,'best_entry':0.99,'no_return_point':0.98,'stop_loss':0.97,'TP1':1.02,'TP2':1.05,'has_fvg':True,'has_ob':True,'liq_reason':'Killzone','gann_reason':'قريب جان','astro_reason':'قمر','ai_reason':'جديد','tech_reason':'FVG'}
    if send_tg_alert(test_sig): st.sidebar.success("✅ تليجرام شغال!")
    else: st.sidebar.error("❌ فشل - شوف Secrets")

if st.button("🎯 افحص قبل الحركة", type="primary"):
    st.cache_data.clear()
    st.rerun()

symbols, src = get_all_symbols()
st.write(f"تم جلب {len(symbols)} عملة من {src} - هيفحص اول {limit_coins}")

to_scan=symbols[:limit_coins]
results=[]; prog=st.progress(0); stat=st.empty()
for i,sym in enumerate(to_scan):
    prog.progress((i+1)/len(to_scan)); stat.text(f"رادار قبل الحركة: {sym} {i+1}/{len(to_scan)}")
    df=get_klines(sym)
    if df is not None:
        res=ultimate_score(df,sym,memory)
        if res and res['score']>=min_score:
            if mode=="بمب بس" and res['type']!="PUMP": pass
            elif mode=="دمب بس" and res['type']!="DUMP": pass
            else: results.append(res)
    time.sleep(0.02)
prog.empty(); stat.empty()

if results:
    memory['total']=memory.get('total',0)+1; save_memory(memory); st.session_state['mem']=memory

if results:
    df_res=pd.DataFrame(results).sort_values('score', ascending=False)
    st.success(f"✅ تنبؤ {len(df_res)} عملة قبل الحركة")
    c1,c2=st.columns(2); c1.metric("بمب متوقع", len([r for r in results if r['type']=='PUMP'])); c2.metric("دمب متوقع", len([r for r in results if r['type']=='DUMP']))
    st.dataframe(df_res, use_container_width=True)
    if send_tg:
        sent=0
        for sig in df_res.head(5).to_dict('records'):
            if send_tg_alert(sig): sent+=1; time.sleep(0.5)
        if sent>0: st.success(f"📱 اتبعت {sent} للتليجرام!")
        else: st.warning("تليجرام متفعل بس مفيش سكور عالي او Secrets ناقص")
    top=df_res.iloc[0]
    st.divider(); st.subheader(f"🎯 افضل تنبؤ: {top['symbol']} {top['type']} سكور {top['score']}")
    st.info(f"📚 {top['tech_reason']} | 💧 {top['liq_reason']} | 📐 {top['gann_reason']} | 🌙 {top['astro_reason']}")
    c1,c2,c3=st.columns(3)
    c1.metric("السعر", f"{top['price']}"); c1.metric("دخول متوقع", f"{top['best_entry']}"); c2.metric("الغاء", f"{top['no_return_point']}"); c2.metric("ستوب", f"{top['stop_loss']}"); c3.metric("هدف1", f"{top['TP1']}"); c3.metric("هدف2", f"{top['TP2']}")
else:
    st.error(f"مفيش فوق {min_score} - انزل لـ 20 وجرب تاني")
    st.write("نزل شريط اقل سكور للجدول لحد 20 وهيظهر")

st.caption("Predictive T40 L30 G20 A10 - قبل الحركة")
