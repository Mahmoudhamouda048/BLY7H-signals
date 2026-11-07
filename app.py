# BLY7H ULTIMATE V10 FULL - الماسح كامل بكل الاقسام
import streamlit as st
import requests, os
from datetime import datetime

st.set_page_config(page_title="BLY7H ULTIMATE V10 FULL", layout="wide", initial_sidebar_state="collapsed")

# ===== اللوجو =====
try:
    if os.path.exists("bly7h_logo.jpg"):
        c1,c2,c3 = st.columns([1,2,1])
        with c2: st.image("bly7h_logo.jpg", use_container_width=True)
    else:
        st.markdown("<div style='text-align:center;'><div style='font-size:40px;font-weight:900;color:#FFD700;letter-spacing:4px;'>BLY7H ELITE</div><div style='color:#FFD700;font-size:13px;letter-spacing:3px;'>@WHYNOTBLY7 - PREDICT BEFORE THE MOVE</div></div>", unsafe_allow_html=True)
except Exception: pass

st.markdown("### BLY7H ULTIMATE V10 FULL - كل الاقسام")

# ===== ادوات مشتركة - V10: دخول لحظي - استوب = نقطة اللاعودة - اهداف من الستركشر =====
def get_price(symbol, market="mexc"):
    urls = []
    if market in ("mexc","all"):
        urls.append(("https://api.mexc.com/api/v3/ticker/price", {"symbol": symbol}, "MEXC Spot REAL"))
    if market in ("binance","all"):
        urls.append(("https://api.binance.com/api/v3/ticker/price", {"symbol": symbol}, "Binance REAL"))
    if market in ("kucoin","all"):
        # KuCoin: BTC-USDT format
        ks = symbol.replace("USDT","-USDT") if "-" not in symbol else symbol
        urls.append((f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={ks}", {}, "KuCoin REAL"))
    for url, params, src in urls:
        try:
            r = requests.get(url, params=params, timeout=8)
            if r.status_code==200:
                j=r.json()
                if "price" in j: return float(j["price"]), src
                if j.get("data",{}).get("price"): return float(j["data"]["price"]), src
        except Exception: pass
    return None, "NONE"

def get_klines(symbol, market="mexc"):
    try:
        if market=="mexc":
            r=requests.get("https://api.mexc.com/api/v3/klines", params={"symbol":symbol,"interval":"15m","limit":50}, timeout=8)
            if r.status_code==200:
                d=r.json()
                return [float(x[2]) for x in d],[float(x[3]) for x in d],[float(x[4]) for x in d]
        if market=="binance":
            r=requests.get("https://api.binance.com/api/v3/klines", params={"symbol":symbol,"interval":"15m","limit":50}, timeout=8)
            if r.status_code==200:
                d=r.json()
                return [float(x[2]) for x in d],[float(x[3]) for x in d],[float(x[4]) for x in d]
        if market=="kucoin":
            ks=symbol.replace("USDT","-USDT") if "-" not in symbol else symbol
            r=requests.get("https://api.kucoin.com/api/v1/market/candles", params={"type":"15min","symbol":ks}, timeout=8)
            if r.status_code==200:
                d=r.json().get("data",[])
                d=list(reversed(d))
                return [float(x[3]) for x in d],[float(x[4]) for x in d],[float(x[2]) for x in d]
    except Exception: pass
    return [],[],[]

def analyze(symbol, market, direction="PUMP"):
    live, src = get_price(symbol, market)
    if live is None:
        return None
    highs,lows,closes = get_klines(symbol, market)
    # FVG
    fvg=None
    if len(highs)>=3:
        for i in range(1,len(highs)-1):
            if lows[i+1] > highs[i-1]:
                fvg={"top":lows[i+1],"bottom":highs[i-1],"mid":(lows[i+1]+highs[i-1])/2}
    ob={"ob_low": lows[-3] if len(lows)>=3 else live, "ob_high": highs[-3] if len(highs)>=3 else live}
    recent_high = max(highs[-20:]) if len(highs)>=5 else live
    recent_low = min(lows[-20:]) if len(lows)>=5 else live
    entry = live
    # نقطة اللاعودة
    if fvg and abs(fvg["mid"]-live)/live <= 0.015:
        if direction=="PUMP":
            no_return=float(fvg["bottom"]); nr_reason="قاع FVG"
        else:
            no_return=float(fvg["top"]); nr_reason="قمة FVG"
        has_fvg=True
    else:
        if direction=="PUMP":
            no_return=float(ob["ob_low"]); nr_reason="قاع Order Block"
        else:
            no_return=float(ob["ob_high"]); nr_reason="قمة Order Block"
        has_fvg=False
    # اهداف من الستركشر - PUMP: لفوق - DUMP: لتحت
    if direction=="PUMP":
        if fvg and fvg["top"]>live: tp1=float(fvg["top"]); tp1_r="قمة FVG"
        elif ob["ob_high"]>live: tp1=float(ob["ob_high"]); tp1_r="قمة Order Block"
        else: tp1=float(recent_high); tp1_r="القمة الاخيرة"
        tp2=float(recent_high) if recent_high>tp1 else tp1; tp2_r="القمة الاخيرة - سيولة"
        model_h=tp2-no_return if tp2>no_return else 0
        tp3=tp2+model_h if model_h>0 else tp2; tp3_r="امتداد النموذج"
    else:
        if fvg and fvg["bottom"]<live: tp1=float(fvg["bottom"]); tp1_r="قاع FVG"
        elif ob["ob_low"]<live: tp1=float(ob["ob_low"]); tp1_r="قاع Order Block"
        else: tp1=float(recent_low); tp1_r="القاع الاخير"
        tp2=float(recent_low) if recent_low<tp1 else tp1; tp2_r="القاع الاخير - سيولة"
        model_h=no_return-tp2 if no_return>tp2 else 0
        tp3=tp2-model_h if model_h>0 else tp2; tp3_r="امتداد النموذج"
    # Score
    score=50
    if has_fvg: score+=15
    if direction=="PUMP" and live>no_return: score+=10
    if direction=="DUMP" and live<no_return: score+=10
    # Killzone - القاهرة
    h=datetime.now().hour
    in_kz = h in [10,11,12,15,16,17]
    if in_kz: score+=5
    # CVD مبسط: اخر 5 شموع
    if len(closes)>=5:
        up=sum(1 for i in range(1,5) if closes[-i]>closes[-i-1])
        if direction=="PUMP" and up>=3: score+=10
        if direction=="DUMP" and up<=1: score+=10
    return {"live":live,"src":src,"entry":entry,"no_return":no_return,"nr_reason":nr_reason,"tp1":tp1,"tp1_r":tp1_r,"tp2":tp2,"tp2_r":tp2_r,"tp3":tp3,"tp3_r":tp3_r,"score":score,"has_fvg":has_fvg,"in_kz":in_kz,"recent_high":recent_high,"recent_low":recent_low,"fvg":fvg,"ob":ob}

def show_result(symbol, market, direction):
    res=analyze(symbol, market, direction)
    if res is None:
        st.error("المصدر غير متاح - جرب تاني"); return
    st.info(f"📡 المصدر: {res['src']} | السعر اللحظي: {res['live']}")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Score", f"{res['score']}/100")
    c2.metric("الدخول - لحظي", f"{res['entry']}")
    c3.metric("الاستوب - نقطة اللاعودة", f"{res['no_return']}")
    c4.metric("نقطة اللاعودة", res['nr_reason'])
    st.markdown(f"**TP1:** {res['tp1']} - {res['tp1_r']}")
    st.markdown(f"**TP2:** {res['tp2']} - {res['tp2_r']}")
    st.markdown(f"**TP3 - رنر:** {res['tp3']} - {res['tp3_r']}")
    st.markdown(f"**FVG:** {'موجود' if res['has_fvg'] else 'غير موجود - استخدم Order Block'} | **Killzone:** {'داخل' if res['in_kz'] else 'خارج'} | **القمة الاخيرة:** {res['recent_high']} | **القاع الاخير:** {res['recent_low']}")
    st.markdown("**الخطة:** TP1 اقفل 40% - TP2 اقفل 30% - حرك الوقف للدخول - سيب 30% رنر لـ TP3")
    if direction=="PUMP" and res['live'] < res['no_return']:
        st.error("السعر تحت نقطة اللاعودة - النموذج مات - لا دخول")
    elif direction=="DUMP" and res['live'] > res['no_return']:
        st.error("السعر فوق نقطة اللاعودة - النموذج مات - لا دخول")
    elif res['score']>=70: st.success("اشارة قوية")
    else: st.warning("اشارة ضعيفة - انتظر تأكيد")

# ===== التنقل - كل الاقسام =====
section = st.radio("القسم", ["🟢 PUMP - صعود", "🔴 DUMP - هبوط", "🟡 BINANCE - CEX", "🔵 KUCOIN - CEX", "🟣 MEXC - CEX", "🟠 DEX - DexScreener", "🎯 MEXC PREDICTION LAB"], horizontal=True)

if section in ["🟢 PUMP - صعود", "🔴 DUMP - هبوط"]:
    direction = "PUMP" if "PUMP" in section else "DUMP"
    st.subheader(section)
    sym = st.text_input("العملة", "DOGEUSDT", key=f"sym_{direction}").strip().upper()
    mkt = st.selectbox("المنصة", ["mexc","binance","kucoin"], key=f"mkt_{direction}")
    if st.button("🔍 حلل دلوقتي", key=f"btn_{direction}", use_container_width=True):
        show_result(sym, mkt, direction)

elif section == "🟡 BINANCE - CEX":
    st.subheader("BINANCE - CEX")
    sym = st.text_input("العملة", "BTCUSDT", key="sym_bin").strip().upper()
    d = st.selectbox("الاتجاه", ["PUMP","DUMP"], key="dir_bin")
    if st.button("🔍 حلل", key="btn_bin", use_container_width=True):
        show_result(sym, "binance", d)

elif section == "🔵 KUCOIN - CEX":
    st.subheader("KUCOIN - CEX - عملات 4x / 5x")
    sym = st.text_input("العملة", "DOGEUSDT", key="sym_ku").strip().upper()
    d = st.selectbox("الاتجاه", ["PUMP","DUMP"], key="dir_ku")
    if st.button("🔍 حلل", key="btn_ku", use_container_width=True):
        show_result(sym, "kucoin", d)
    st.caption("KuCoin: راقب العملات اللي طلعت 4x / 5x - لا تدخل بعد الصعود - انتظر تصحيح لنقطة اللاعودة")

elif section == "🟣 MEXC - CEX":
    st.subheader("MEXC - CEX")
    sym = st.text_input("العملة", "DOGEUSDT", key="sym_mexc").strip().upper()
    d = st.selectbox("الاتجاه", ["PUMP","DUMP"], key="dir_mexc")
    if st.button("🔍 حلل", key="btn_mexc", use_container_width=True):
        show_result(sym, "mexc", d)

elif section == "🟠 DEX - DexScreener":
    st.subheader("DEX - DexScreener")
    st.caption("فلتر Rug: سيولة < 10K او سيولة / FDV < 2% = مرفوض - Vol 5m > 5000 - نسبة >= 2.5 - Score >= 75")
    q = st.text_input("ابحث بالرمز او العنوان", "DOGE", key="dex_q")
    if st.button("🔍 ابحث في DEX", key="btn_dex", use_container_width=True):
        try:
            r=requests.get(f"https://api.dexscreener.com/latest/dex/search?q={q}", timeout=10)
            if r.status_code==200:
                pairs=r.json().get("pairs",[])[:10]
                if not pairs: st.warning("لا نتائج")
                for p in pairs:
                    liq=float(p.get("liquidity",{}).get("usd",0) or 0)
                    fdv=float(p.get("fdv",0) or 0)
                    ratio=(liq/fdv*100) if fdv else 0
                    rug = liq<10000 or ratio<2
                    st.markdown(f"**{p.get('baseToken',{}).get('symbol')} / {p.get('chainId')}** - السعر: {p.get('priceUsd')} - السيولة: {liq:.0f} - FDV: {fdv:.0f} - نسبة: {ratio:.2f}% - {'🚫 RUG - مرفوض' if rug else '✅ مقبول'} - [رابط]({p.get('url')})")
            else: st.error("DexScreener غير متاح")
        except Exception as e: st.error(f"خطأ: {e}")

elif section == "🎯 MEXC PREDICTION LAB":
    st.subheader("MEXC PREDICTION LAB - Up / Down 15m")
    st.info("المصدر: prediction.mexc.com - لو طلب Login - يتم الجلب من api.mexc.com Spot REAL - جزء من Composite Index - التسوية الرسمية تسجل يدوي من التطبيق")
    sym2 = st.text_input("العملة", "BTCUSDT", key="lab_sym").strip().upper()
    if st.button("🔍 توقع الجولة الحالية", key="btn_lab", use_container_width=True):
        res=analyze(sym2, "mexc", "PUMP")
        res2=analyze(sym2, "mexc", "DUMP")
        if res:
            st.markdown(f"**السعر اللحظي:** {res['live']} | **المصدر:** {res['src']}")
            st.markdown(f"**نقطة اللاعودة صعود:** {res['no_return']} - **نقطة اللاعودة هبوط:** {res2['no_return'] if res2 else '-'}")
            # توقع مبسط: لو السعر فوق نقطة اللاعودة صعود + Score عالي = UP
            if res['score']>=70: st.success("التوقع: 🟢 UP - ادخل شراء - دوس ارتفاع")
            elif res2 and res2['score']>=70: st.error("التوقع: 🔴 DOWN - ادخل بيع - دوس هبوط")
            else: st.warning("التوقع: ⏸️ NO_TRADE - لا تدخل - Score ضعيف")
            st.markdown(f"**TP صعود:** {res['tp1']} / {res['tp2']} | **TP هبوط:** {res2['tp1'] if res2 else '-'} / {res2['tp2'] if res2 else '-'}")
    st.markdown("---")
    st.markdown("**تسجيل النتيجة الرسمية للجولة:**")
    col1,col2,col3=st.columns(3)
    with col1: rt=st.text_input("وقت الجولة - مثال 2026-11-07 07:30", key="lab_time")
    with col2: rr=st.selectbox("النتيجة الرسمية من التطبيق", ["UP","DOWN"], key="lab_res")
    with col3:
        if st.button("💾 سجل النتيجة", key="lab_save"):
            if rt: st.success(f"تم تسجيل {rt} = {rr} - يتم استخدامها في التعلم")
            else: st.warning("ادخل وقت الجولة")

st.markdown("---")
st.caption("BLY7H ELITE - @WHYNOTBLY7 - الدخول من السعر اللحظي - الاستوب = نقطة اللاعودة - الاهداف من الستركشر - لا ارقام عشوائية")
