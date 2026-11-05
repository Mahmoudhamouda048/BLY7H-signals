import streamlit as st
import pandas as pd
import requests, time, random
from datetime import datetime

st.set_page_config(page_title="BLY7H V7 FINAL", layout="wide", page_icon="🚀")
st.title("🚀 BLY7H V7 FINAL - شغال 100% تليجرام")

# ========== SECRETS ==========
TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = st.secrets.get("TELEGRAM_CHANNEL_ID", "@WHYNOTBLY7")
CHAT = st.secrets.get("TELEGRAM_CHAT_ID", "")

if not TOKEN:
    st.error("❌ مفيش TELEGRAM_BOT_TOKEN في Secrets")
    st.stop()

# ========== TELEGRAM شغال 100% ==========
def send_telegram(text, chat_id=None):
    target = chat_id if chat_id else CHANNEL
    if not target:
        st.error("مفيش CHANNEL او CHAT ID")
        return False
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": target, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            return True
        else:
            st.error(f"تليجرام خطأ: {r.text}")
            # جرب بدون Markdown لو فشل
            payload2 = {"chat_id": target, "text": text}
            r2 = requests.post(url, json=payload2, timeout=15)
            return r2.status_code == 200
    except Exception as e:
        st.error(f"خطأ اتصال تليجرام: {e}")
        return False

# ========== TEST TELEGRAM ==========
st.sidebar.header("📱 اختبار تليجرام")
st.sidebar.write(f"TOKEN: {'موجود ✅' if TOKEN else 'مش موجود ❌'}")
st.sidebar.write(f"CHANNEL: {CHANNEL}")
st.sidebar.write(f"CHAT: {CHAT if CHAT else 'فاضي'}")

if st.sidebar.button("🧪 جرب ابعت للقناة"):
    if send_telegram("✅ BLY7H V7 شغال - اختبار قناة @WHYNOTBLY7"):
        st.sidebar.success("✅ اتبعت للقناة!")
    else:
        st.sidebar.error("❌ فشل - اتأكد البوت Admin في القناة")

if st.sidebar.button("🧪 جرب ابعت للخاص"):
    target = CHAT if CHAT else CHANNEL
    if send_telegram("✅ BLY7H V7 شغال - اختبار خاص", chat_id=target):
        st.sidebar.success(f"✅ اتبعت لـ {target}!")
    else:
        st.sidebar.error("❌ فشل")

# ========== CONFIG ==========
STABLES = ["USDCUSDT","BUSDUSDT","TUSDUSDT","USDPUSDT","DAIUSDT","FDUSDUSDT","USDeUSDT","USD1USDT","RLUSDUSDT","XUSDUSDT","EURUSDT","PYUSDUSDT","GUSDUSDT","USDXUSDT"]
MIN_SCORE = 75

def is_safe_token(pair):
    try:
        liq = float(pair.get('liquidity',{}).get('usd',0))
        if liq < 10000: return False
        fdv = float(pair.get('fdv',0
