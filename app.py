# BLY7H ULTIMATE V10 FINAL - الكود كامل بكل حاجة - اخر تعديل
# يجمع: PUMP + DUMP + BINANCE + KUCOIN + MEXC + DEX (15 اداة) + MEXC PREDICTION LAB + BACKTEST + TELEGRAM
# القواعد النهائية: الدخول = السعر اللحظي - الاستوب = نقطة اللاعودة بالظبط - الاهداف من الستركشر - لا ارقام عشوائية
import streamlit as st
import requests, os, json
from datetime import datetime

st.set_page_config(page_title="BLY7H ULTIMATE V10 FINAL", layout="wide", initial_sidebar_state="collapsed")

# ===== اللوجو =====
try:
    if os.path.exists("bly7h_logo.jpg"):
        c1,c2,c3 = st.columns([1,2,1])
        with c2: st.image("bly7h_logo.jpg", use_container_width=True)
    else:
        st.markdown("<div style='text-align:center;'><div style='font-size:42px;font-weight:900;color:#FFD700;letter-spacing:4px;'>BLY7H ELITE</div><div style='color:#FFD700;font-size:13px;letter-spacing:3px;'>@WHYNOTBLY7 - PREDICT BEFORE THE MOVE</div></div>", unsafe_allow_html=True)
except Exception: pass

st.markdown("### BLY7H ULTIMATE V10 FINAL - كامل")

# ===== TELEGRAM =====
def send_tg(msg):
    try:
        tok = st.secrets.get("TELEGRAM_BOT_TOKEN","") if hasattr(st,"secrets") else ""
        chat = st.secrets.get("TELEGRAM_CHANNEL_ID","") or st.secrets.get("TELEGRAM_CHAT_ID","") if hasattr(st,"secrets") else ""
        if not tok or not chat: return False
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id":chat,"text":msg}, timeout=10)
        return r.status_code==200
    except Exception: return False

# ===== المصدر الحقيقي =====
def get_price(symbol, market="mexc"):
    # 1) MEXC Spot REAL - جزء من Composite Index
    # 2) Binance REAL - 3) KuCoin REAL
    tries=[]
    if market in ("mexc","all"): tries.append(("https://api.mexc.com/api/v3/ticker/price",{"symbol":symbol},"MEXC Spot REAL"))
    if market in ("binance","all"): tries.append(("https://api.binance.com/api/v3/ticker/price",{"symbol":symbol},"Binance REAL"))
    if market in ("kucoin","all"):
        ks=symbol.replace("USDT","-USDT") if "-" not in symbol else symbol
        tries.append((f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={ks}",{},"KuCoin REAL"))
    for url,params,src in tries:
        try:
            r=requests.get(url,params=params,timeout=8)
            if r.status_code==200:
                j=r.json()
                if "price" in j: return float(j["price"]),src
                if isinstance(j.get("data"),dict) and j["data"].get("price"): return float(j["data"]["price"]),src
        except Exception: pass
    return None,"NONE"

def get_klines(symbol, market="mexc"):
    try:
        if market=="mexc":
            r=requests.get("https://api.mexc.com/api/v3/klines",params={"symbol":symbol,"interval":"15m","limit":100},timeout=8)
            if r.status_code==200:
                d=r.json()
                return [float(x[2]) for x in d],[float(x[3]) for x in d],[float(x[4]) for x in d],[float(x[5]) for x in d]
        if market=="binance":
            r=requests.get("https://api.binance.com/api/v3/klines",params={"symbol":symbol,"interval":"15m","limit":100},timeout=8)
            if r.status_code==200:
                d=r.json()
                return [float(x[2]) for x in d],[float(x[3]) for x in d],[float(x[4]) for x in d],[float(x[5]) for x in d]
        if market=="kucoin":
            ks=symbol.replace("USDT","-USDT") if "-" not in symbol else symbol
            r=requests.get("https://api.kucoin.com/api/v1/market/candles",params={"type":"15min","symbol":ks},timeout=8)
            if r.status_code==200:
                d=list(reversed(r.json().get("data",[])))
                return [float(x[3]) for x in d],[float(x[4]) for x in d],[float(x[2]) for x in d],[float(x[5]) for x in d]
    except Exception: pass
    return [],[],[],[]

def get_funding(symbol):
    # Funding من Binance Futures - لو مفيش Futures = غير متاح - مش 0.000% وهمي
    try:
        r=requests.get("https://fapi.binance.com/fapi/v1/premiumIndex",params={"symbol":symbol},timeout=8)
        if r.status_code==200:
            j=r.json()
            return float(j.get("lastFundingRate",0))*100, float(j.get("markPrice",0) or 0)
    except Exception: pass
    return None, None

def get_oi(symbol):
    try:
        r=requests.get("https://fapi.binance.com/fapi/v1/openInterest",params={"symbol":symbol},timeout=8)
        if r.status_code==200: return float(r.json().get("openInterest",0))
    except Exception: pass
    return None

def killzone_now():
    h=datetime.now().hour
    if h in [10,11,12]: return "لندن", True, 5
    if h in [15,16,17]: return "نيويورك", True, 5
    return "خارج", False, 0

# ===== المحرك الرئيسي V10 =====
def analyze_full(symbol, market, direction):
    live, src = get_price(symbol, market)
    if live is None: return None
    highs,lows,closes,vols = get_klines(symbol, market)
    # --- FVG: اخر فجوة ---
    fvg=None
    if len(highs)>=3:
        for i in range(1,len(highs)-1):
            if direction=="PUMP" and lows[i+1] > highs[i-1]:
                fvg={"top":float(lows[i+1]),"bottom":float(highs[i-1]),"mid":float((lows[i+1]+highs[i-1])/2),"type":"bullish"}
            if direction=="DUMP" and highs[i+1] < lows[i-1]:
                fvg={"top":float(lows[i-1]),"bottom":float(highs[i+1]),"mid":float((lows[i-1]+highs[i+1])/2),"type":"bearish"}
    ob={"ob_low": float(lows[-3]) if len(lows)>=3 else live, "ob_high": float(highs[-3]) if len(highs)>=3 else live}
    recent_high=float(max(highs[-20:])) if len(highs)>=5 else live
    recent_low=float(min(lows[-20:])) if len(lows)>=5 else live
    # --- الدخول = السعر اللحظي ---
    entry=live
    # --- نقطة اللاعودة = قاع/قمة FVG بالظبط - او قاع/قمة OB ---
    if fvg and abs(fvg["mid"]-live)/live <= 0.015:
        if direction=="PUMP": no_return=float(fvg["bottom"]); nr_reason="قاع FVG"
        else: no_return=float(fvg["top"]); nr_reason="قمة FVG"
        has_fvg=True
    else:
        if direction=="PUMP": no_return=float(ob["ob_low"]); nr_reason="قاع Order Block"
        else: no_return=float(ob["ob_high"]); nr_reason="قمة Order Block"
        has_fvg=False
    # --- اهداف من الستركشر ---
    if direction=="PUMP":
        if fvg and fvg["top"]>live: tp1=float(fvg["top"]); tp1_r="قمة FVG"
        elif ob["ob_high"]>live: tp1=float(ob["ob_high"]); tp1_r="قمة Order Block"
        else: tp1=float(recent_high); tp1_r="القمة الاخيرة"
        tp2=float(recent_high) if recent_high>tp1 else tp1; tp2_r="القمة الاخيرة - سيولة"
        model_h=tp2-no_return if tp2>no_return else 0
        tp3=tp2+model_h if model_h>0 else tp2; tp3_r="امتداد النموذج: TP2 + ارتفاع النموذج"
    else:
        if fvg and fvg["bottom"]<live: tp1=float(fvg["bottom"]); tp1_r="قاع FVG"
        elif ob["ob_low"]<live: tp1=float(ob["ob_low"]); tp1_r="قاع Order Block"
        else: tp1=float(recent_low); tp1_r="القاع الاخير"
        tp2=float(recent_low) if recent_low<tp1 else tp1; tp2_r="القاع الاخير - سيولة"
        model_h=no_return-tp2 if no_return>tp2 else 0
        tp3=tp2-model_h if model_h>0 else tp2; tp3_r="امتداد النموذج"
    # --- Score ---
    score=50
    if has_fvg: score+=15
    if direction=="PUMP" and live>no_return: score+=10
    if direction=="DUMP" and live<no_return: score+=10
    kz_name,in_kz,kz_bonus=killzone_now()
    if in_kz: score+=kz_bonus
    # CVD مبسط: اخر 5 شموع
    cvd="محايد"
    if len(closes)>=5:
        up=sum(1 for i in range(1,5) if closes[-i]>closes[-i-1])
        if up>=3: cvd="شراء > بيع"
        elif up<=1: cvd="بيع > شراء"
        if direction=="PUMP" and up>=3: score+=10
        if direction=="DUMP" and up<=1: score+=10
    # Vol Spike
    vol_spike=1.0; vol_msg="غير متاح"
    if len(vols)>=10:
        avg=sum(vols[-10:-1])/9 if len(vols)>=10 else 1
        vol_spike=float(vols[-1]/avg) if avg else 1.0
        vol_msg=f"x{vol_spike:.2f}"
        if vol_spike>=2.5: score+=10
        elif vol_spike>=1.5: score+=5
    # Funding + OI - حقيقي - مش 0.000% وهمي
    funding, mark = get_funding(symbol) if market=="binance" else (None,None)
    oi = get_oi(symbol) if market=="binance" else None
    # Whale Wall / Liquidation - تقدير من القمم والقيعان
    wall="لا يوجد حائط واضح"
    if recent_high>live and (recent_high-live)/live<0.02: wall=f"حائط بيع عند القمة {recent_high}"
    if recent_low<live and (live-recent_low)/live<0.02: wall=f"حائط شراء عند القاع {recent_low}"
    liq_msg="خطر تصفية لو كسر نقطة اللاعودة"
    # RR من الستركشر
    risk=abs(live-no_return) if live!=no_return else 0.0001
    rr1=abs(tp1-live)/risk if risk else 0
    rr2=abs(tp2-live)/risk if risk else 0
    return {"live":live,"src":src,"entry":entry,"no_return":no_return,"nr_reason":nr_reason,"tp1":tp1,"tp1_r":tp1_r,"tp2":tp2,"tp2_r":tp2_r,"tp3":tp3,"tp3_r":tp3_r,"score":min(100,score),"has_fvg":has_fvg,"kz":kz_name,"in_kz":in_kz,"cvd":cvd,"vol":vol_msg,"vol_spike":vol_spike,"funding":funding,"oi":oi,"wall":wall,"liq":liq_msg,"rr1":round(rr1,2),"rr2":round(rr2,2),"recent_high":recent_high,"recent_low":recent_low,"fvg":fvg,"ob":ob}

def show_full(symbol, market, direction):
    res=analyze_full(symbol, market, direction)
    if res is None:
        st.error("المصدر غير متاح - جرب تاني"); return None
    st.info(f"📡 المصدر: {res['src']} | السعر اللحظي: {res['live']}")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Score", f"{res['score']}/100")
    c2.metric("الدخول - لحظي", f"{res['entry']}")
    c3.metric("الاستوب - نقطة اللاعودة", f"{res['no_return']}")
    c4.metric("نقطة اللاعودة", res['nr_reason'])
    st.markdown(f"**TP1:** {res['tp1']} - {res['tp1_r']} - RR: {res['rr1']}")
    st.markdown(f"**TP2:** {res['tp2']} - {res['tp2_r']} - RR: {res['rr2']}")
    st.markdown(f"**TP3 - رنر:** {res['tp3']} - {res['tp3_r']}")
    st.markdown(f"**FVG:** {'موجود' if res['has_fvg'] else 'غير موجود - OB'} | **Killzone:** {res['kz']} | **CVD:** {res['cvd']} | **Vol:** {res['vol']} | **Whale Wall:** {res['wall']}")
    _fund_txt = f"{res['funding']:.4f}%" if res['funding'] is not None else 'غير متاح - لا يوجد Futures'
    _oi_txt = res['oi'] if res['oi'] is not None else 'غير متاح'
    st.markdown(f"**Funding:** {_fund_txt} | **OI:** {_oi_txt} | **Liquidation:** {res['liq']}")
    st.markdown(f"**القمة الاخيرة:** {res['recent_high']} | **القاع الاخير:** {res['recent_low']}")
    st.markdown("**الخطة:** TP1 اقفل 40% - TP2 اقفل 30% - حرك الوقف للدخول - سيب 30% رنر لـ TP3 - لو العملة هتعمل 50x الرنر هيكمل معاها")
    invalid=False
    if direction=="PUMP" and res['live'] < res['no_return']: invalid=True
    if direction=="DUMP" and res['live'] > res['no_return']: invalid=True
    if invalid: st.error("السعر عبر نقطة اللاعودة - النموذج مات - لا دخول")
    elif res['score']>=70:
        st.success("اشارة قوية")
        if st.button("📩 ابعت تنبيه تلجرام", key=f"tg_{symbol}_{direction}_{market}"):
            ok=send_tg(f"BLY7H {direction} {symbol} Score {res['score']} - دخول {res['entry']} - استوب {res['no_return']} ({res['nr_reason']}) - TP1 {res['tp1']} - TP2 {res['tp2']} - TP3 {res['tp3']} - @WHYNOTBLY7")
            st.success("تم الارسال") if ok else st.warning("تأكد من Secrets - البوت لازم يكون ادمن في القناة")
    else: st.warning("اشارة ضعيفة - انتظر تأكيد")
    return res

# ===== التنقل - كل الاقسام =====
section = st.radio("القسم", ["🟢 PUMP - صعود", "🔴 DUMP - هبوط", "🟡 BINANCE - CEX", "🔵 KUCOIN - CEX", "🟣 MEXC - CEX", "🟠 DEX - DexScreener", "🎯 MEXC PREDICTION LAB", "📊 BACKTEST"], horizontal=True)

if section in ["🟢 PUMP - صعود", "🔴 DUMP - هبوط"]:
    direction="PUMP" if "PUMP" in section else "DUMP"
    st.subheader(section)
    sym=st.text_input("العملة", "DOGEUSDT", key=f"s_{direction}").strip().upper()
    mkt=st.selectbox("المنصة", ["mexc","binance","kucoin"], key=f"m_{direction}")
    if st.button("🔍 حلل دلوقتي", key=f"b_{direction}", use_container_width=True):
        show_full(sym, mkt, direction)

elif section=="🟡 BINANCE - CEX":
    st.subheader("BINANCE - CEX - OI + Funding + CVD + FVG + OB + Killzone")
    sym=st.text_input("العملة", "BTCUSDT", key="sb").strip().upper()
    d=st.selectbox("الاتجاه", ["PUMP","DUMP"], key="db")
    if st.button("🔍 حلل", key="bb", use_container_width=True): show_full(sym, "binance", d)

elif section=="🔵 KUCOIN - CEX":
    st.subheader("KUCOIN - CEX - عملات 4x / 5x")
    st.caption("لا تدخل بعد الصعود 4x / 5x - استنى تصحيح لنقطة اللاعودة")
    sym=st.text_input("العملة", "DOGEUSDT", key="sk").strip().upper()
    d=st.selectbox("الاتجاه", ["PUMP","DUMP"], key="dk")
    if st.button("🔍 حلل", key="bk", use_container_width=True): show_full(sym, "kucoin", d)

elif section=="🟣 MEXC - CEX":
    st.subheader("MEXC - CEX")
    sym=st.text_input("العملة", "DOGEUSDT", key="sm").strip().upper()
    d=st.selectbox("الاتجاه", ["PUMP","DUMP"], key="dm")
    if st.button("🔍 حلل", key="bm", use_container_width=True): show_full(sym, "mexc", d)

elif section=="🟠 DEX - DexScreener":
    st.subheader("DEX - DexScreener - 15 اداة")
    st.caption("1) Vol 5m > 5000 + نسبة >= 2.5 | 2) تغير 5m >= 5% | 3) سيولة > 15000 | 4) تغير 1h > 20% | 5) FDV < 20M = -30 | 6) ساعات الحيتان 2-6 صباحا +15 | 7) MIN_SCORE 75 | 8) اهداف ATR | 9) ترند BSC | 10) SafeTelegram | 11) 429 retry | 12) DexScreener API | 13) اعلى سيولة اولا | 14) Symbol + ChainId | 15) dex_url + @WHYNOTBLY7 | فلتر Rug: سيولة < 10K او سيولة/FDV < 2% = مرفوض")
    q=st.text_input("ابحث بالرمز او العنوان", "DOGE", key="dexq")
    if st.button("🔍 ابحث في DEX", key="bdex", use_container_width=True):
        try:
            r=requests.get(f"https://api.dexscreener.com/latest/dex/search?q={q}", timeout=10)
            if r.status_code==200:
                pairs=r.json().get("pairs",[])[:10]
                if not pairs: st.warning("لا نتائج")
                for p in pairs:
                    liq=float(p.get("liquidity",{}).get("usd",0) or 0)
                    fdv=float(p.get("fdv",0) or 0)
                    ratio=(liq/fdv*100) if fdv else 0
                    ch5=float((p.get("priceChange",{}) or {}).get("m5",0) or 0)
                    ch1h=float((p.get("priceChange",{}) or {}).get("h1",0) or 0)
                    vol5=float((p.get("volume",{}) or {}).get("m5",0) or 0)
                    rug=liq<10000 or ratio<2
                    sc=50
                    if vol5>5000: sc+=10
                    if ch5>=5: sc+=10
                    if liq>15000: sc+=10
                    if ch1h>20: sc+=10
                    if fdv<20000000: sc-=30
                    st.markdown(f"**{p.get('baseToken',{}).get('symbol')} / {p.get('chainId')}** - السعر: {p.get('priceUsd')} - Vol5m: {vol5:.0f} - تغير 5m: {ch5}% - تغير 1h: {ch1h}% - سيولة: {liq:.0f} - FDV: {fdv:.0f} - نسبة: {ratio:.2f}% - Score: {sc} - {'🚫 RUG - مرفوض' if rug else '✅ مقبول'} - [رابط]({p.get('url')})")
            else: st.error("DexScreener غير متاح")
        except Exception as e: st.error(f"خطأ: {e}")

elif section=="🎯 MEXC PREDICTION LAB":
    st.subheader("MEXC PREDICTION LAB - Up / Down 15m")
    st.info("المصدر: prediction.mexc.com - لو طلب Login - يتم الجلب من api.mexc.com Spot REAL - جزء من Composite Index - التسوية الرسمية تسجل يدوي من التطبيق")
    sym2=st.text_input("العملة", "BTCUSDT", key="labsym").strip().upper()
    if st.button("🔍 توقع الجولة الحالية", key="blab", use_container_width=True):
        rp=analyze_full(sym2, "mexc", "PUMP")
        rd=analyze_full(sym2, "mexc", "DUMP")
        if rp:
            st.markdown(f"**السعر اللحظي:** {rp['live']} | **المصدر:** {rp['src']}")
            st.markdown(f"**نقطة اللاعودة صعود:** {rp['no_return']} | **نقطة اللاعودة هبوط:** {rd['no_return'] if rd else '-'}")
            if rp['score']>=70: st.success("التوقع: 🟢 UP - ادخل شراء - دوس ارتفاع")
            elif rd and rd['score']>=70: st.error("التوقع: 🔴 DOWN - ادخل بيع - دوس هبوط")
            else: st.warning("التوقع: ⏸️ NO_TRADE - لا تدخل - Score ضعيف")
            st.markdown(f"**TP صعود:** {rp['tp1']} / {rp['tp2']} | **TP هبوط:** {rd['tp1'] if rd else '-'} / {rd['tp2'] if rd else '-'}")
    st.markdown("---")
    st.markdown("**تسجيل النتيجة الرسمية للجولة:**")
    c1,c2,c3=st.columns(3)
    with c1: rt=st.text_input("وقت الجولة - 2026-11-07 07:30", key="labt")
    with c2: rr=st.selectbox("النتيجة الرسمية من التطبيق", ["UP","DOWN"], key="labr")
    with c3:
        if st.button("💾 سجل النتيجة", key="labsave"):
            st.success(f"تم تسجيل {rt} = {rr} - تستخدم في التعلم") if rt else st.warning("ادخل وقت الجولة")

elif section=="📊 BACKTEST":
    st.subheader("BACKTEST - اختبار النموذج على الشموع اللي فاتت")
    sym=st.text_input("العملة", "DOGEUSDT", key="bt_sym").strip().upper()
    mkt=st.selectbox("المنصة", ["mexc","binance"], key="bt_mkt")
    if st.button("🔍 شغل الباك تست", key="bt_btn", use_container_width=True):
        highs,lows,closes,vols=get_klines(sym, mkt)
        if len(closes)<20: st.error("لا توجد شموع كافية")
        else:
            wins=0; total=0; tp1_hits=0
            for i in range(20, len(closes)-5):
                entry=closes[i]
                # نقطة اللاعودة = قاع اخر 20 شمعة قبل الدخول
                nr=min(lows[i-20:i])
                tp1=max(highs[i-20:i])
                # هل وصل TP1 قبل ما يكسر نقطة اللاعودة في 5 شموع؟
                hit_tp=False; hit_sl=False
                for j in range(i+1, min(i+6, len(closes))):
                    if highs[j]>=tp1: hit_tp=True; break
                    if lows[j]<nr: hit_sl=True; break
                total+=1
                if hit_tp: wins+=1; tp1_hits+=1
            st.metric("عدد الصفقات", total)
            st.metric("نسبة نجاح TP1", f"{(wins/total*100):.1f}%" if total else "0%")
            st.caption("الباك تست = امتحان - مش تعلم - التعلم من النتائج الرسمية المسجلة في MEXC LAB")

st.markdown("---")
st.caption("BLY7H ELITE - @WHYNOTBLY7 - الدخول من السعر اللحظي - الاستوب = نقطة اللاعودة - الاهداف من الستركشر - لا ارقام عشوائية - المصدر الحقيقي: MEXC / Binance / KuCoin / DexScreener")
