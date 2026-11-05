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
        msg = f"{emoji} BLY7H {sig['type']} {emoji}\n💰 {sig['symbol']} قبل الحركة!\n📊 سكور: {sig['score']}\n💵 الان: {sig['price']}\n🎯 دخول: {sig['best_entry']}\n❌ الغاء: {sig['no_return_point']}\n⛔ ستوب: {sig['stop_loss']}\n✅ هدف1: {sig['TP1']} | هدف2: {sig['TP2']}\n"
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
        reason = f"قريب جان {dist:.2f}%"
        days = (datetime.now() - datetime(2023, 1, 1)).days
        if days % 90 < 3:
            score += 5
            reason += " + دورة"
        return min(20, score), reason
    except:
        return 5, "جان"

def calc_astro():
    try:
        new_moon = datetime(2024, 1, 11)
        days = (datetime.now() - new_moon).days % 29.5
        score = 6 if days < 2 or abs(days - 14.75) < 1.5 else 3 if days < 5 else 1
        reason = f"قمر {days:.0f}"
        if datetime.now().weekday() in [0,4]:
            score += 3
            reason += " يوم قوي"
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
            reasons.append("AMD")
        vol_col = 'vol' if 'vol' in df.columns else 'volume'
        vol_spike = float(df[vol_col].iloc[-1]) / df[vol_col].astype(float).mean()
        if vol_spike > 2:
            score += 6
            reasons.append(f"Vol x{vol_spike:.1f}")
        high_20 = float(df['high'].iloc[-20:].max())
        if price < high_20 and (high_20 - price) / price < 0.03:
            score += 5
            reasons.append("سيولة فوق")
        return min(30, score), " | ".join(reasons) if reasons else "طبيعية"
    except:
        return 8, "سيولة"

def calc_smc(df, price):
    try:
        bull_b = bull_m = None
        bear_b = bear_m = bear_t = None
        bull_dist = bear_dist = 999
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
        return score, has_fvg, True, fvg_data, recent_low, recent_high, " | ".join(reasons) if reasons else "SMC"
    except:
        return 15, False, False, {}, price*0.99, price*1.01, "SMC"

def get_symbols_binance():
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            usdt = [d for d in data if d.get('symbol','').endswith('USDT')]
            usdt = sorted(usdt, key
