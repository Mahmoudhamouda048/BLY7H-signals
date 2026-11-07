# BLY7H ULTIMATE V10 - app.py كامل - يشتغل على طول
import streamlit as st
import requests
import os

st.set_page_config(page_title="BLY7H ULTIMATE V10", layout="wide", initial_sidebar_state="collapsed")

# ===== اللوجو =====
try:
    if os.path.exists("bly7h_logo.jpg"):
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.image("bly7h_logo.jpg", use_container_width=True)
    else:
        st.markdown("<div style='text-align:center;'><div style='font-size:40px;font-weight:900;letter-spacing:4px;color:#FFD700;'>BLY7H ELITE</div><div style='color:#FFD700;font-size:13px;letter-spacing:3px;'>@WHYNOTBLY7 - PREDICT BEFORE THE MOVE</div></div>", unsafe_allow_html=True)
except Exception:
    pass

st.markdown("### BLY7H ULTIMATE V10 - الدخول من السعر اللحظي - الاستوب = نقطة اللاعودة")

# ===== جلب السعر اللحظي + الشموع من MEXC الحقيقي =====
def get_live(symbol):
    try:
        r = requests.get("https://api.mexc.com/api/v3/ticker/price", params={"symbol": symbol}, timeout=8)
        if r.status_code == 200:
            return float(r.json()["price"]), "api.mexc.com Spot REAL"
    except Exception:
        pass
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": symbol}, timeout=8)
        if r.status_code == 200:
            return float(r.json()["price"]), "Binance Public REAL"
    except Exception:
        pass
    return None, "NONE"

def get_klines(symbol):
    try:
        r = requests.get("https://api.mexc.com/api/v3/klines", params={"symbol": symbol, "interval": "15m", "limit": 50}, timeout=8)
        if r.status_code == 200:
            data = r.json()
            highs = [float(x[2]) for x in data]
            lows = [float(x[3]) for x in data]
            closes = [float(x[4]) for x in data]
            return highs, lows, closes
    except Exception:
        pass
    return [], [], []

def calc_fvg(highs, lows):
    # FVG = اخر فجوة: low[i+1] > high[i-1]
    for i in range(1, len(highs)-1):
        if lows[i+1] > highs[i-1]:
            return {"top": lows[i+1], "bottom": highs[i-1], "mid": (lows[i+1]+highs[i-1])/2}
    return None

def calc_ob(highs, lows):
    if len(highs) >= 3:
        return {"ob_low": lows[-3], "ob_high": highs[-3]}
    if len(highs) > 0:
        return {"ob_low": lows[-1], "ob_high": highs[-1]}
    return {"ob_low": 0, "ob_high": 0}

# ===== الواجهة =====
symbol = st.text_input("العملة", "DOGEUSDT").strip().upper()
if st.button("🔍 حلل دلوقتي", use_container_width=True):
    live, src = get_live(symbol)
    if live is None:
        st.error("المصدر غير متاح - جرب تاني")
    else:
        st.info(f"📡 المصدر: {src} | السعر اللحظي: {live}")
        highs, lows, closes = get_klines(symbol)
        fvg = calc_fvg(highs, lows) if highs else None
        ob = calc_ob(highs, lows) if highs else {"ob_low": live, "ob_high": live}
        recent_high = max(highs[-20:]) if len(highs) >= 5 else live
        recent_low = min(lows[-20:]) if len(lows) >= 5 else live

        # الدخول = السعر اللحظي
        entry = live
        # نقطة اللاعودة = قاع FVG بالظبط - مش رقم عشوائي
        if fvg and abs(fvg["mid"] - live) / live <= 0.015:
            no_return = float(fvg["bottom"])
            no_return_reason = "قاع FVG"
            has_fvg = True
        else:
            no_return = float(ob["ob_low"])
            no_return_reason = "قاع Order Block"
            has_fvg = False

        # الاهداف من الستركشر
        if fvg and fvg["top"] > live:
            tp1 = float(fvg["top"])
            tp1_reason = "قمة FVG"
        elif ob["ob_high"] > live:
            tp1 = float(ob["ob_high"])
            tp1_reason = "قمة Order Block"
        else:
            tp1 = float(recent_high)
            tp1_reason = "القمة الاخيرة"

        if recent_high > tp1:
            tp2 = float(recent_high)
            tp2_reason = "القمة الاخيرة - منطقة السيولة"
        else:
            tp2 = tp1
            tp2_reason = "قمة FVG"

        model_h = tp2 - no_return if tp2 > no_return else 0
        tp3 = tp2 + model_h if model_h > 0 else tp2
        tp3_reason = "امتداد النموذج: TP2 + ارتفاع النموذج"

        # Score بسيط
        score = 50
        if has_fvg:
            score += 15
        if live > no_return:
            score += 10
        if tp2 > live:
            score += 10

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Score", f"{score}/100")
        c2.metric("الدخول - السعر اللحظي", f"{entry}")
        c3.metric("الاستوب - نقطة اللاعودة", f"{no_return}")
        c4.metric("نقطة اللاعودة", no_return_reason)

        st.markdown(f"**TP1:** {tp1} - {tp1_reason}")
        st.markdown(f"**TP2:** {tp2} - {tp2_reason}")
        st.markdown(f"**TP3 - رنر:** {tp3} - {tp3_reason}")
        st.markdown(f"**الخطة:** TP1 اقفل 40% - TP2 اقفل 30% - حرك الوقف للدخول - سيب 30% رنر لـ TP3")
        if live < no_return:
            st.error("السعر تحت نقطة اللاعودة - النموذج مات - لا دخول")
        elif score >= 70:
            st.success("اشارة قوية")
        else:
            st.warning("اشارة ضعيفة - انتظر تأكيد")

st.markdown("---")
st.caption("BLY7H ELITE - @WHYNOTBLY7 - الاستوب = نقطة اللاعودة - الاهداف من الستركشر - لا ارقام عشوائية")
