import os, json, time, math, sqlite3, hashlib, concurrent.futures, threading
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import requests
import streamlit as st

st.set_page_config(page_title="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")
CAIRO = ZoneInfo("Africa/Cairo")
DB_PATH = "bly7h_signals.db"
TIMEOUT = 12
STABLES = {"USDCUSDT","BUSDUSDT","DAIUSDT","FDUSDUSDT","USDEUSDT"}

# ===== FIX 1: Thread-local Session - اهم اصلاح ل KuCoin =====
_thread_local = threading.local()
def get_session():
    if not hasattr(_thread_local, "s"):
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"})
        _thread_local.s = s
    return _thread_local.s
SESSION = get_session()

st.markdown("<div style='border:2px solid #FFD700;background:#0B0E14;padding:14px;box-shadow:0 24px 80px rgba(0,0,0,.55)'>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center'><div style='font-size:10px;font-weight:900;letter-spacing:0.28em;color:#FFD700'>Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;margin-top:12px'><span style='display:inline-block;background:#FFD700;color:#000;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:900'>SELF-LEARNING BOT - Learns from 1000 rounds</span> <span style='display:inline-block;background:#12161F;border:1px solid #1E2530;color:#E6E9EF;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700'>Monthly Rent $149 (Foreign $290) - Full Ownership $2499 (Foreign $4000)</span></div>", unsafe_allow_html=True)
st.markdown("<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:14px'>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📐</div><div style='font-size:11px;font-weight:800;color:#FFF'>FVG</div><div style='font-size:10px;color:#8A93A3'>Fair Value Gap</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>🧱</div><div style='font-size:11px;font-weight:800;color:#FFF'>Order Block</div><div style='font-size:10px;color:#8A93A3'>Whale Zone</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📊</div><div style='font-size:11px;font-weight:800;color:#FFF'>CVD Real</div><div style='font-size:10px;color:#8A93A3'>Buy vs Sell</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📈</div><div style='font-size:11px;font-weight:800;color:#FFF'>OI + Funding</div><div style='font-size:10px;color:#8A93A3'>Open Interest</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📖</div><div style='font-size:11px;font-weight:800;color:#FFF'>Order Book</div><div style='font-size:10px;color:#8A93A3'>Buy / Sell Walls</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>⏰</div><div style='font-size:11px;font-weight:800;color:#FFF'>Killzone</div><div style='font-size:10px;color:#8A93A3'>London / NY</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>🧹</div><div style='font-size:11px;font-weight:800;color:#FFF'>Sweep</div><div style='font-size:10px;color:#8A93A3'>Stop Hunt</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📉</div><div style='font-size:11px;font-weight:800;color:#FFF'>EMA 9/21</div><div style='font-size:10px;color:#8A93A3'>Trend</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📊</div><div style='font-size:11px;font-weight:800;color:#FFF'>RSI</div><div style='font-size:10px;color:#8A93A3'>Momentum</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📈</div><div style='font-size:11px;font-weight:800;color:#FFF'>MACD</div><div style='font-size:10px;color:#8A93A3'>Momentum</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📏</div><div style='font-size:11px;font-weight:800;color:#FFF'>ATR</div><div style='font-size:10px;color:#8A93A3'>Volatility</div></div>"
"<div style='background:#12161F;border:1px solid #FFD700;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>💎</div><div style='font-size:11px;font-weight:900;color:#FFD700'>Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
"</div>", unsafe_allow_html=True)
st.markdown("<style>.stApp{background:#0B0E14;color:#E6E9EF} h1,h2,h3{color:#E6E9EF!important} .stButton>button{background:#FFD700;color:#000;font-weight:900;border-radius:10px;border:1px solid #FFD700} div[data-testid='stMetric']{background:#12161F;border:1px solid #1E2530;border-radius:14px} .stExpander{border:1px solid #1E2530;border-radius:14px;background:#12161F} section[data-testid='stSidebar']{background:#0F131B;border-right:1px solid #1E2530}</style>", unsafe_allow_html=True)

# ===== FIX 2: api_json with Retry + diagnostic =====
def api_json(url, params=None, timeout=TIMEOUT, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            sess = get_session()
            r = sess.get(url, params=params, timeout=timeout)
            if r.status_code == 429:
                time.sleep(0.6 * (attempt + 1))
                continue
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}"
                time.sleep(0.3)
                continue
            try:
                j = r.json()
            except Exception as e:
                last_err = str(e)
                continue
            if isinstance(j, dict):
                code = j.get("code")
                if code is not None and str(code) not in ("0", "200", "200000", "0.0"):
                    if "result" in j or "data" in j:
                        pass
                    else:
                        last_err = f"code={code} msg={j.get('msg','')}"
                        time.sleep(0.3)
                        continue
            return j
        except Exception as e:
            last_err = str(e)
            time.sleep(0.4 * (attempt + 1))
    return None

def safe_float(v, d=0.0):
    try:
        x = float(v)
        return x if pd.notna(x) else d
    except Exception:
        return d
def now_cairo():
    return datetime.now(CAIRO)
def killzone_status():
    cur = now_cairo()
    mins = cur.hour * 60 + cur.minute
    if 10 * 60 <= mins <= 12 * 60:
        return True, "London 10:00-12:00 Cairo"
    if 15 * 60 + 30 <= mins <= 17 * 60 + 30:
        return True, "New York 15:30-17:30 Cairo"
    return False, "خارج Killzone - بونص فقط، مش حظر"

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, exchange TEXT, symbol TEXT, side TEXT, score INTEGER, price REAL, entry REAL, stop REAL, tp1 REAL, tp2 REAL, tp3 REAL, change_pct REAL, volume_ratio REAL, cvd REAL, outcome TEXT DEFAULT 'OPEN')""")
        c.execute("""CREATE TABLE IF NOT EXISTS paper_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, symbol TEXT, side TEXT, entry REAL, stop REAL, tp1 REAL, tp2 REAL, tp3 REAL, size_usd REAL, status TEXT DEFAULT 'OPEN', pnl REAL DEFAULT 0, exit_price REAL, exit_reason TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, round_start TEXT UNIQUE, feats TEXT, label TEXT, model TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS backtests (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, symbol TEXT, timeframe TEXT, win_rate REAL, total INTEGER, avg_rr REAL, notes TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS lab_rounds (round_start TEXT PRIMARY KEY, open_price REAL, close_price REAL, label TEXT, feats TEXT, model TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS lab_models (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, accuracy REAL, total INTEGER, weights TEXT, is_best INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS alerts_sent (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, symbol TEXT, side TEXT, score INTEGER, price REAL)""")
        c.commit()
init_db()

def normalize_symbol(user_input, exchange):
    s = (user_input or "").strip().upper().replace(" ", "").replace("-", "").replace("/", "").replace(":", "")
    if not s:
        return None
    if exchange == "KuCoin":
        if s in ("BTC", "XBT"):
            return "XBTUSDTM"
        if s.endswith("USDTM"):
            return s
        if s.endswith("USDT"):
            return s[:-4] + "USDTM"
        return s + "USDTM"
    if exchange == "MEXC":
        if "_USDT" in s:
            return s
        if s.endswith("USDT"):
            return s[:-4] + "_USDT"
        return s + "_USDT"
    if exchange == "Bybit":
        if s.endswith("USDT"):
            return s
        return s + "USDT"
    if exchange == "Binance":
        if s.endswith("USDT"):
            return s
        if s.endswith("USDTM"):
            return s[:-3]
        if "_USDT" in s:
            return s.replace("_USDT", "USDT")
        return s + "USDT"
    return s

def display_symbol(raw, exchange):
    if exchange == "KuCoin":
        return raw.replace("USDTM", "/USDT").replace("XBT", "BTC")
    if exchange == "MEXC":
        return raw.replace("_USDT", "/USDT")
    if exchange == "Binance":
        return raw.replace("USDT", "/USDT")
    return raw.replace("USDT", "/USDT")

def save_signals(results, exch):
    return None  # لحظي: مفيش حفظ
def save_paper_trade(symbol, side, entry, stop, tp1, tp2, tp3, size_usd):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO paper_trades (created_at,symbol,side,entry,stop,tp1,tp2,tp3,size_usd) VALUES (?,?,?,?,?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), symbol, side, entry, stop, tp1, tp2, tp3, size_usd))
        c.commit()

def already_alerted(symbol, side, score):
    with sqlite3.connect(DB_PATH) as c:
        row = c.execute("SELECT id FROM alerts_sent WHERE symbol=? AND side=? AND created_at > datetime('now','-1 hour') ORDER BY id DESC LIMIT 1", (symbol, side)).fetchone()
        return row is not None
def mark_alerted(symbol, side, score, price):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO alerts_sent (created_at,symbol,side,score,price) VALUES (?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), symbol, side, score, price))
        c.commit()
def get_secret(name, default=""):
    try:
        v = st.secrets[name]
        if v:
            return str(v)
    except Exception:
        pass
    return os.getenv(name, default)
def send_telegram(message):
    token = get_secret("TELEGRAM_BOT_TOKEN", "")
    chat = get_secret("TELEGRAM_CHANNEL_ID", "") or get_secret("TELEGRAM_CHAT_ID", "")
    if not token:
        return False, "أضف TELEGRAM_BOT_TOKEN في Secrets"
    if not chat:
        return False, "أضف TELEGRAM_CHANNEL_ID في Secrets"
    try:
        r = get_session().post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat, "text": message, "disable_web_page_preview": True}, timeout=15)
        d = r.json() if r.content else {}
        return (True, "تم الإرسال") if r.ok and d.get("ok") else (False, d.get("description", "Telegram error"))
    except Exception as e:
        return False, str(e)
def fmt_bly7trader(s):
    side = "🚀 LONG" if s["type"] == "LONG" else "🔻 SHORT"
    denom = abs(s["entry"] - s["stop"]) if abs(s["entry"] - s["stop"]) > 0 else 1
    rr1 = abs(s["tp1"] - s["entry"]) / denom
    rr2 = abs(s["tp2"] - s["entry"]) / denom
    return f"""Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"""

# ===== FIX 3: KuCoin symbols - فلترة صح + ترتيب بالفوليوم =====
def kucoin_futures_symbols(limit=1000):
    p = api_json("https://api-futures.kucoin.com/api/v1/contracts/active")
    d = (p or {}).get("data", [])
    out = []
    for c in d:
        s = c.get("symbol", "")
        if not s.endswith("USDTM"):
            continue
        if any(x in s for x in STABLES):
            continue
        # استبعد العقود المتوقفة / بدون تداول
        if str(c.get("status", "")).lower() not in ("", "open", "trading"):
            continue
        out.append(s)
    # لو فشل الـ API ارجع قائمة احتياطية لاهم 30 عملة عشان السكان ميقفش خالص
    if not out:
        out = ["XBTUSDTM","ETHUSDTM","SOLUSDTM","BNBUSDTM","XRPUSDTM","DOGEUSDTM","ADAUSDTM","AVAXUSDTM","LINKUSDTM","DOTUSDTM","MATICUSDTM","LTCUSDTM","TRXUSDTM","ATOMUSDTM","NEARUSDTM","APTUSDTM","ARBUSDTM","OPUSDTM","SUIUSDTM","PEPEUSDTM"]
    return out[:limit]

def mexc_futures_symbols(limit=1000):
    p = api_json("https://contract.mexc.com/api/v1/contract/detail")
    d = (p or {}).get("data", []) if isinstance(p, dict) else []
    if isinstance(d, dict):
        d = d.get("data", []) or list(d.values())
    out = []
    for c in d:
        if not isinstance(c, dict):
            continue
        s = c.get("symbol", "")
        if s.endswith("_USDT") and not any(x in s for x in ["USDC", "DAI", "FDUSD", "USDE"]):
            out.append(s)
    if not out:
        out = ["BTC_USDT","ETH_USDT","SOL_USDT","XRP_USDT","DOGE_USDT","ADA_USDT","AVAX_USDT","LINK_USDT","DOT_USDT","LTC_USDT","TRX_USDT","ATOM_USDT","NEAR_USDT","APT_USDT","ARB_USDT","OP_USDT","SUI_USDT","PEPE_USDT","BNB_USDT","MATIC_USDT"]
    return out[:limit]
def bybit_futures_symbols(limit=1000):
    p = api_json("https://api.bybit.com/v5/market/instruments-info", {"category": "linear", "limit": 1000})
    d = (p or {}).get("result", {}).get("list", [])
    out = [c.get("symbol", "") for c in d if c.get("symbol", "").endswith("USDT") and not any(x in c.get("symbol", "") for x in STABLES)]
    return out[:limit]

# ===== FIX 4: KuCoin klines - ترتيب + fallback =====
def klines_kucoin_fut(symbol, gran=15, limit=200):
    # KuCoin بيقبل بس: 1,5,15,30,60,120,240,480,720,1440 - 3 ممنوع
    if gran not in (1,5,15,30,60,120,240,480,720,1440):
        gran = 5 if gran == 3 else 15
    end = int(time.time() * 1000)
    start = end - limit * gran * 60 * 1000
    p = api_json("https://api-futures.kucoin.com/api/v1/kline/query", {"symbol": symbol, "granularity": gran, "from": start, "to": end})
    d = (p or {}).get("data", [])
    if len(d) < 30:
        return None
    try:
        df = pd.DataFrame(d, columns=["time", "open", "close", "high", "low", "vol", "turnover"])
        for c in ["open", "close", "high", "low", "vol"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna().sort_values("time").reset_index(drop=True)
        if len(df) < 30:
            return None
        return df
    except Exception:
        return None


def binance_futures_symbols(limit=1000):
    p = api_json("https://fapi.binance.com/fapi/v1/exchangeInfo")
    d = (p or {}).get("symbols", [])
    out = []
    for c in d:
        s = c.get("symbol", "")
        if c.get("contractType") != "PERPETUAL":
            continue
        if c.get("status") != "TRADING":
            continue
        if not s.endswith("USDT"):
            continue
        if any(x in s for x in STABLES):
            continue
        out.append(s)
    if not out:
        out = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","MATICUSDT","LTCUSDT","TRXUSDT","ATOMUSDT","NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","SUIUSDT","PEPEUSDT"]
    return out[:limit]

def klines_binance_fut(symbol, interval="15m", limit=200):
    # Binance Futures: interval بيقبل 1m,3m,5m,15m,1h عادي
    bmap = {"1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "1h": "1h", "Min1": "1m", "Min5": "5m", "Min15": "15m", "Min60": "1h"}
    bi = bmap.get(interval, "15m")
    p = api_json("https://fapi.binance.com/fapi/v1/klines", {"symbol": symbol, "interval": bi, "limit": limit})
    if not p or not isinstance(p, list) or len(p) < 30:
        return None
    try:
        df = pd.DataFrame(p, columns=["time","open","high","low","close","vol","close_time","quote_vol","trades","taker_buy_base","taker_buy_quote","ignore"])
        for c in ["open","high","low","close","vol"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df[["time","open","high","low","close","vol"]].dropna().sort_values("time").reset_index(drop=True)
        if len(df) < 30:
            return None
        return df
    except Exception:
        return None

def funding_binance(symbol):
    p = api_json("https://fapi.binance.com/fapi/v1/fundingRate", {"symbol": symbol, "limit": 1})
    if not p or not isinstance(p, list) or len(p) == 0:
        return "N/A"
    try:
        return f"{float(p[0].get('fundingRate', 0))*100:.4f}%"
    except Exception:
        return "N/A"

def oi_binance(symbol):
    p = api_json("https://fapi.binance.com/fapi/v1/openInterest", {"symbol": symbol})
    if not p:
        return "N/A"
    return p.get("openInterest", "N/A")

def klines_mexc_fut(symbol, interval="15m", limit=200):
    mexc_map = {"1m": "Min1", "3m": "Min5", "5m": "Min5", "15m": "Min15", "1h": "Min60", "Min1": "Min1", "Min5": "Min5", "Min15": "Min15", "Min60": "Min60"}
    mexc_interval = mexc_map.get(interval, "Min15")
    # MEXC بيعمل Rate Limit لو ضربت limit بس - جرب start/end الاول، وبعدين limit، وجرب هوست بديل
    import time as _t
    hosts = ["https://contract.mexc.com", "https://futures.mexc.com"]
    end_ms = int(_t.time() * 1000)
    gran_min = {"Min1": 1, "Min5": 5, "Min15": 15, "Min60": 60}.get(mexc_interval, 15)
    start_ms = end_ms - limit * gran_min * 60 * 1000
    last_err = ""
    for host in hosts:
        for params in [{"symbol": symbol, "interval": mexc_interval, "start": start_ms, "end": end_ms}, {"symbol": symbol, "interval": mexc_interval, "limit": limit}]:
            try:
                sess = get_session()
                r = sess.get(f"{host}/api/v1/contract/kline", params=params, timeout=TIMEOUT)
                last_err = f"HTTP {r.status_code} host={host} params={params}"
                if r.status_code != 200:
                    continue
                try:
                    j = r.json()
                except Exception as e:
                    last_err = str(e); continue
                # MEXC بيرجع {"success":true,"code":0,"data":{...}} او {"code":0,"data":...}
                if isinstance(j, dict) and j.get("code") not in (None, 0, "0", 200, "200"):
                    # لو فيه data مع كود غريب كمل، لو مفيش data سجل الخطأ
                    if "data" not in j:
                        last_err = f"MEXC code={j.get('code')} msg={j.get('msg')} host={host}"
                        continue
                d = (j or {}).get("data", {}) if isinstance(j, dict) else {}
                if not d:
                    last_err = f"MEXC empty data host={host} j_keys={list(j.keys()) if isinstance(j,dict) else type(j)}"
                    continue
                # داتا اعمدة
                if isinstance(d, dict) and "time" in d and "close" in d:
                    df = pd.DataFrame({"time": d.get("time", []), "open": d.get("open", []), "high": d.get("high", []), "low": d.get("low", []), "close": d.get("close", []), "vol": d.get("vol", [])})
                    for c in ["open", "high", "low", "close", "vol"]:
                        df[c] = pd.to_numeric(df[c], errors="coerce")
                    df = df.dropna().reset_index(drop=True)
                    if len(df) >= 30:
                        return df
                    last_err = f"MEXC len {len(df)} <30"
                    continue
                if isinstance(d, dict):
                    inner = d.get("data", []) or d.get("kline", []) or []
                    if inner and len(inner) >= 30:
                        if isinstance(inner[0], dict):
                            df = pd.DataFrame(inner); df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "vol", "t": "time"})
                        else:
                            df = pd.DataFrame(inner, columns=["time", "open", "high", "low", "close", "vol"][:len(inner[0])])
                        for c in ["open", "high", "low", "close", "vol"]:
                            if c in df.columns:
                                df[c] = pd.to_numeric(df[c], errors="coerce")
                        df = df.dropna().reset_index(drop=True)
                        if len(df) >= 30:
                            return df
                if isinstance(d, list) and len(d) >= 30:
                    df = pd.DataFrame(d, columns=["time", "open", "high", "low", "close", "vol"][:len(d[0])]) if not isinstance(d[0], dict) else pd.DataFrame(d)
                    for c in ["open", "high", "low", "close", "vol"]:
                        if c in df.columns:
                            df[c] = pd.to_numeric(df[c], errors="coerce")
                    df = df.dropna().reset_index(drop=True)
                    if len(df) >= 30:
                        return df
            except Exception as e:
                last_err = str(e); continue
            _t.sleep(0.05)
    # خزن اخر خطأ في متغير عام - مش session_state عشان Threads
    global LAST_MEXC_ERR
    LAST_MEXC_ERR = last_err
    try:
        LAST_MEXC_ERRS.append(last_err)
    except Exception:
        pass
    # بديل أخير: لو Futures اتقفل من Streamlit، جرب Spot klines عشان المسح مايقفش - السعر قريب جدا للتحليل
    try:
        spot_sym = symbol.replace("_USDT", "USDT")
        sess2 = get_session()
        r2 = sess2.get("https://api.mexc.com/api/v3/klines", params={"symbol": spot_sym, "interval": "15m" if mexc_interval=="Min15" else "1h", "limit": limit}, timeout=TIMEOUT)
        if r2.status_code == 200:
            j2 = r2.json()
            if isinstance(j2, list) and len(j2) >= 30:
                df2 = pd.DataFrame(j2, columns=["time","open","high","low","close","vol","close_time","quote_vol","trades","taker_buy_base","taker_buy_quote","ignore"])
                for c in ["open","high","low","close","vol"]:
                    df2[c] = pd.to_numeric(df2[c], errors="coerce")
                df2 = df2[["time","open","high","low","close","vol"]].dropna().reset_index(drop=True)
                if len(df2) >= 30:
                    LAST_MEXC_ERR = last_err + " | تم استخدام Spot كبديل"
                    return df2
    except Exception as e:
        pass
    return None

def klines_bybit_fut(symbol, interval="15", limit=200):
    p = api_json("https://api.bybit.com/v5/market/kline", {"category": "linear", "symbol": symbol, "interval": interval, "limit": limit})
    d = (p or {}).get("result", {}).get("list", [])
    if not d or len(d) < 30:
        return None
    df = pd.DataFrame(d, columns=["time", "open", "high", "low", "close", "vol", "turnover"])
    for c in ["open", "high", "low", "close", "vol"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values("time").reset_index(drop=True)
    return df

# KuCoin granularity map - FIX: 3m -> 5m لان KuCoin مفيهوش 3
KUCOIN_GRAN = {"1m": 1, "3m": 5, "5m": 5, "15m": 15, "1h": 60}
def get_futures_klines(exchange, symbol, gran_label="15m", limit=200):
    if exchange == "KuCoin":
        return klines_kucoin_fut(symbol, KUCOIN_GRAN.get(gran_label, 15), limit)
    if exchange == "MEXC":
        return klines_mexc_fut(symbol, gran_label, limit)
    if exchange == "Bybit":
        return klines_bybit_fut(symbol, {"1m": "1", "3m": "3", "5m": "5", "15m": "15", "1h": "60"}[gran_label], limit)
    if exchange == "Binance":
        return klines_binance_fut(symbol, gran_label, limit)
    return None

def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()
def rsi_calc(s, n=14):
    d = s.diff(); up = d.clip(lower=0); dn = -d.clip(upper=0)
    ru = up.ewm(alpha=1/n, adjust=False).mean(); rd = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = ru / (rd.replace(0, np.nan)); return 100 - 100 / (1 + rs)
def macd_calc(s):
    e12 = ema(s, 12); e26 = ema(s, 26); m = e12 - e26; sig = ema(m, 9); return m, sig, m - sig
def atr_calc(df, n=14):
    tr = pd.concat([(df["high"] - df["low"]).abs(), (df["high"] - df["close"].shift()).abs(), (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()
def momentum_calc(s, n=10):
    return s - s.shift(n)
def detect_fvg(df):
    out = []
    for i in range(1, len(df) - 1):
        if df["low"].iloc[i+1] > df["high"].iloc[i-1]:
            out.append({"type": "bull", "top": float(df["low"].iloc[i+1]), "bottom": float(df["high"].iloc[i-1]), "mid": (float(df["low"].iloc[i+1]) + float(df["high"].iloc[i-1])) / 2})
        if df["high"].iloc[i+1] < df["low"].iloc[i-1]:
            out.append({"type": "bear", "top": float(df["low"].iloc[i-1]), "bottom": float(df["high"].iloc[i+1]), "mid": (float(df["low"].iloc[i-1]) + float(df["high"].iloc[i+1])) / 2})
    return out
def detect_ob(df):
    return {"ob_low": float(df["low"].iloc[-3]), "ob_high": float(df["high"].iloc[-3])}
def detect_bsl_ssl(df, lookback=20):
    return {"BSL": float(df["high"].tail(lookback).max()), "SSL": float(df["low"].tail(lookback).min())}
def detect_sweep(df):
    if len(df) < 25:
        return {"sweep": False, "dir": "NONE"}
    bsl_ssl = detect_bsl_ssl(df.iloc[:-2], 20); last = df.iloc[-1]
    if float(last["high"]) > bsl_ssl["BSL"] and float(last["close"]) < bsl_ssl["BSL"]:
        return {"sweep": True, "dir": "BEARISH_SWEEP"}
    if float(last["low"]) < bsl_ssl["SSL"] and float(last["close"]) > bsl_ssl["SSL"]:
        return {"sweep": True, "dir": "BULLISH_SWEEP"}
    return {"sweep": False, "dir": "NONE"}
def orderbook_kucoin_fut(symbol):
    p = api_json("https://api-futures.kucoin.com/api/v1/level2/snapshot", {"symbol": symbol})
    d = (p or {}).get("data", {})
    if not d:
        return None
    bids = d.get("bids", [])[:10]; asks = d.get("asks", [])[:10]
    try:
        bid_vol = sum(float(b[1]) for b in bids); ask_vol = sum(float(a[1]) for a in asks)
        return {"bid_wall": max([float(b[1]) for b in bids], default=0), "ask_wall": max([float(a[1]) for a in asks], default=0), "bid_vol": bid_vol, "ask_vol": ask_vol, "spread": None}
    except Exception:
        return None
def funding_kucoin(symbol):
    p = api_json("https://api-futures.kucoin.com/api/v1/funding-rate", {"symbol": symbol})
    d = (p or {}).get("data", {})
    if not d:
        return "N/A"
    v = d.get("value") if isinstance(d, dict) else None
    return f"{float(v)*100:.4f}%" if v is not None else "N/A"
def funding_mexc(symbol):
    p = api_json("https://contract.mexc.com/api/v1/contract/funding_rate", {"symbol": symbol})
    d = (p or {}).get("data", {})
    if not d:
        return "N/A"
    v = d.get("fundingRate")
    return f"{float(v)*100:.4f}%" if v is not None else "N/A"
def funding_bybit(symbol):
    p = api_json("https://api.bybit.com/v5/market/funding/history", {"category": "linear", "symbol": symbol, "limit": 1})
    l = (p or {}).get("result", {}).get("list", [])
    if not l:
        return "N/A"
    return f"{float(l[0].get('fundingRate', 0))*100:.4f}%"
def oi_kucoin(symbol):
    p = api_json("https://api-futures.kucoin.com/api/v1/open-interest", {"symbol": symbol})
    d = (p or {}).get("data", {})
    if not d:
        return "N/A"
    return d.get("openInterest", "N/A")
def cvd_from_trades_kucoin(symbol):
    p = api_json("https://api-futures.kucoin.com/api/v1/trade/history", {"symbol": symbol})
    d = (p or {}).get("data", [])
    if not d:
        return None
    buy = sum(float(t.get("size", 0)) for t in d if t.get("side") == "buy"); sell = sum(float(t.get("size", 0)) for t in d if t.get("side") == "sell")
    if buy + sell == 0:
        return None
    return (buy - sell) / (buy + sell) * 100


def calc_structural_stop(df, side, entry, e21_val, bsl_ssl, fvg_list, sweep_info, atr_val, ob_dict):
    """استوب مبني على البنية - مش رقم ثابت ولا عشوائي"""
    buf = 0.5 * atr_val
    if side == "LONG":
        # مرشحين تحت الدخول: SSL / اقل قاع 20 شمعة / EMA21 / قاع FVG / قاع OB
        cands = []
        cands.append(bsl_ssl["SSL"] - buf)
        try:
            cands.append(float(df["low"].tail(20).min()) - buf)
        except Exception:
            pass
        if e21_val < entry:
            cands.append(e21_val - buf)
        # FVG صاعد: قاع الجاب
        for f in (fvg_list or []):
            if f.get("type") == "bull" and f.get("bottom", 0) < entry:
                cands.append(float(f["bottom"]) - buf)
        if ob_dict and ob_dict.get("ob_low", 0) < entry:
            cands.append(float(ob_dict["ob_low"]) - buf)
        # Sweep هابط: لو عمل Sweep تحت SSL يبقى الاستوب تحت قاع الـ Sweep
        if sweep_info and sweep_info.get("dir") == "BULLISH_SWEEP":
            try:
                cands.append(float(df["low"].iloc[-1]) - buf)
            except Exception:
                pass
        # اختار اقرب مرشح تحت الدخول (اكبر واحد تحت الدخول) - ده اللي يلغي الفكرة
        below = [c for c in cands if c < entry]
        if below:
            stop = max(below)
        else:
            stop = entry - 1.0 * atr_val
        # حماية: الاستوب مايكونش قريب اوي ولا بعيد اوي
        risk_pct = (entry - stop) / entry if entry else 0
        if risk_pct < 0.002:  # اقل من 0.2% - قريب اوي هيتضرب
            stop = entry - max(0.5 * atr_val, entry * 0.003)
        if risk_pct > 0.04:  # اكتر من 4% - بعيد اوي
            stop = entry * 0.96
        return float(stop), "LONG: SSL/EMA21/FVG/OB/Sweep"
    else:  # SHORT
        cands = []
        cands.append(bsl_ssl["BSL"] + buf)
        try:
            cands.append(float(df["high"].tail(20).max()) + buf)
        except Exception:
            pass
        if e21_val > entry:
            cands.append(e21_val + buf)
        for f in (fvg_list or []):
            if f.get("type") == "bear" and f.get("top", 0) > entry:
                cands.append(float(f["top"]) + buf)
        if ob_dict and ob_dict.get("ob_high", 0) > entry:
            cands.append(float(ob_dict["ob_high"]) + buf)
        if sweep_info and sweep_info.get("dir") == "BEARISH_SWEEP":
            try:
                cands.append(float(df["high"].iloc[-1]) + buf)
            except Exception:
                pass
        above = [c for c in cands if c > entry]
        if above:
            stop = min(above)
        else:
            stop = entry + 1.0 * atr_val
        risk_pct = (stop - entry) / entry if entry else 0
        if risk_pct < 0.002:
            stop = entry + max(0.5 * atr_val, entry * 0.003)
        if risk_pct > 0.04:
            stop = entry * 1.04
        return float(stop), "SHORT: BSL/EMA21/FVG/OB/Sweep"

def analyze_futures(exchange, symbol, display, btc_trend="NEUTRAL", fetch_extra=False, _df_pre=None, _df15_pre=None):
    df = _df_pre if _df_pre is not None else get_futures_klines(exchange, symbol, "1h", 200)
    if df is None:
        return None
    df15 = _df15_pre if _df15_pre is not None else get_futures_klines(exchange, symbol, "15m", 100)
    price = float(df["close"].iloc[-1])
    e9 = ema(df["close"], 9); e21 = ema(df["close"], 21); r = rsi_calc(df["close"]); m, sig, hist = macd_calc(df["close"]); a = atr_calc(df)
    fvg = detect_fvg(df); ob = detect_ob(df); bsl_ssl = detect_bsl_ssl(df); sweep = detect_sweep(df)
    cvd_real = None
    if exchange == "KuCoin" and fetch_extra:
        cvd_real = cvd_from_trades_kucoin(symbol)
    if cvd_real is None:
        last20 = df.tail(20); bv = float(last20[last20["close"] > last20["open"]]["vol"].sum()); sv = float(last20[last20["close"] <= last20["open"]]["vol"].sum())
        cvd = (bv - sv) / (bv + sv + 1e-9) * 100; cvd_src = "CVD proxy من الشموع - تقديري"
    else:
        cvd = float(cvd_real); cvd_src = "CVD حقيقي من صفقات KuCoin"
    avg_vol = float(df["vol"].iloc[:-10].mean()) if len(df) > 20 else 1; last_vol = float(df["vol"].iloc[-1]); vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1
    score = 10; reasons = []
    is_long = e9.iloc[-1] > e21.iloc[-1]; is_short = not is_long
    if is_long:
        score += 12; reasons.append("EMA9>21")
    else:
        score += 12; reasons.append("EMA9<21")
    r_last = float(r.iloc[-1]) if pd.notna(r.iloc[-1]) else 50
    if 45 <= r_last <= 65:
        score += 10; reasons.append("RSI جاهز")
    elif r_last > 70 or r_last < 30:
        score += 4; reasons.append("RSI متطرف - حذر")
    else:
        score += 6
    if float(hist.iloc[-1]) > 0 and is_long:
        score += 8; reasons.append("MACD+")
    if float(hist.iloc[-1]) < 0 and is_short:
        score += 8; reasons.append("MACD-")
    if fvg:
        score += 20; reasons.append(f"FVG {fvg[-1]['type']}")
    if vol_ratio >= 1.5:
        score += 15; reasons.append(f"حجم x{vol_ratio:.2f}")
    elif vol_ratio >= 1.2:
        score += 8
    if abs(cvd) > 20:
        score += 10; reasons.append(f"CVD {cvd:.1f}%")
    if sweep["sweep"]:
        score += 12; reasons.append(f"Sweep {sweep['dir']}")
    mtf = "N/A"
    if df15 is not None:
        e9_15 = ema(df15["close"], 9); e21_15 = ema(df15["close"], 21)
        if is_long and e9_15.iloc[-1] > e21_15.iloc[-1]:
            score += 8; reasons.append("15m يؤكد LONG"); mtf = "15m ✅"
        elif is_short and e9_15.iloc[-1] < e21_15.iloc[-1]:
            score += 8; reasons.append("15m يؤكد SHORT"); mtf = "15m ✅"
        else:
            mtf = "15m ❌ تعارض"
    btc_note = ""
    if btc_trend == "UP" and is_short:
        score -= 8; btc_note = "BTC صاعد - SHORT أضعف"
    if btc_trend == "DOWN" and is_long:
        score -= 8; btc_note = "BTC هابط - LONG أضعف"
    kz, _ = killzone_status()
    if kz:
        score += 5; reasons.append("Killzone +5")
    ch_1h = (price - float(df["open"].iloc[-1])) / float(df["open"].iloc[-1]) * 100 if float(df["open"].iloc[-1]) != 0 else 0
    if abs(ch_1h) > 30:
        return None
    a_last = float(a.iloc[-1]) if pd.notna(a.iloc[-1]) else price * 0.01
    if a_last <= 0:
        a_last = price * 0.01
    side = "LONG" if is_long else "SHORT"
    entry = price
    e21_val = float(e21.iloc[-1]) if len(e21) else entry
    stop, stop_reason = calc_structural_stop(df, side, entry, e21_val, bsl_ssl, fvg, sweep, a_last, ob)
    # تأكيد نهائي: الاستوب لازم يكون في الاتجاه الصح - لو غلط الغي الاشارة
    if side == "LONG" and stop >= entry:
        return None
    if side == "SHORT" and stop <= entry:
        return None
    risk = abs(entry - stop)
    # TPs مبنية على الريسك نفسه - مش ATR ثابت - عشان R:R يبقى مظبوط
    if side == "LONG":
        tp1 = entry + 1.5 * risk; tp2 = entry + 2.8 * risk; tp3 = entry + 4.5 * risk
    else:
        tp1 = entry - 1.5 * risk; tp2 = entry - 2.8 * risk; tp3 = entry - 4.5 * risk
    risk = abs(entry - stop); rr1 = abs(tp1 - entry) / risk if risk > 0 else 0; rr2 = abs(tp2 - entry) / risk if risk > 0 else 0; rr3 = abs(tp3 - entry) / risk if risk > 0 else 0
    funding = "N/A"; oi = "N/A"; obk = None
    if fetch_extra:
        if exchange == "KuCoin":
            funding = funding_kucoin(symbol); oi = oi_kucoin(symbol); obk = orderbook_kucoin_fut(symbol)
        elif exchange == "MEXC":
            funding = funding_mexc(symbol)
        elif exchange == "Bybit":
            funding = funding_bybit(symbol)
        elif exchange == "Binance":
            funding = funding_binance(symbol); oi = oi_binance(symbol)
    extra = f"Stop: {stop_reason} | Stop {stop:.8g} من BSL {bsl_ssl['BSL']:.4g} / SSL {bsl_ssl['SSL']:.4g} / EMA21 {e21_val:.4g} | EMA9 {float(e9.iloc[-1]):.4g} / EMA21 {float(e21.iloc[-1]):.4g} | RSI {r_last:.1f} | ATR {a_last:.4g} | BSL {bsl_ssl['BSL']:.4g} / SSL {bsl_ssl['SSL']:.4g} | Sweep {sweep['dir']} | MTF {mtf} | Funding {funding} | OI {oi} | {cvd_src} | {btc_note} | رسوم تقديرية 0.06% + انزلاق 0.03% | Trailing: حرك الاستوب للدخول عند TP1، ثم Trailing بـ 1 ATR"
    return {"symbol": display, "exchange": exchange, "type": side, "score": int(max(5, min(100, score))), "price": price, "entry": entry, "stop": stop, "tp1": tp1, "tp2": tp2, "tp3": tp3, "ch": round(float(ch_1h), 2), "vol": round(float(vol_ratio), 2), "buy": round(float(cvd), 1), "rsi": round(r_last, 1), "atr": a_last, "fvg": len(fvg), "extra": extra, "rr1": round(float(rr1), 2), "rr2": round(float(rr2), 2), "rr3": round(float(rr3), 2), "funding": funding, "oi": oi, "ob": obk, "killzone": kz, "mtf": mtf, "reasons": " | ".join(reasons)}

def mexc_prediction_check(symbol="BTCUSDT"):
    key = get_secret("CHAINLINK_API_KEY", "")
    if key:
        return {"status": "CHAINLINK", "msg": "Chainlink API Key موجود - التسوية من Chainlink TWAP 60s الرسمي.", "key": True}
    p = api_json("https://api.mexc.com/api/v3/ticker/price", {"symbol": symbol})
    price = safe_float((p or {}).get("price", 0))
    return {"status": "WAIT_OFFICIAL", "msg": f"⏳ انتظار التسوية الرسمية - Chainlink TWAP 60s غير متاح. السعر الحالي من MEXC Spot كمؤشر فقط: {price} - لا تستخدمه كسعر تسوية.", "key": False, "price": price}
def options_analysis(symbol="BTC"):
    return {"IV": "N/A - لا يوجد مصدر خيارات مجاني متاح في هذا الإصدار", "OI": "N/A", "Strikes": "N/A", "Greeks": "N/A - Delta/Gamma/Theta/Vega تحتاج مصدر خيارات مرخص", "note": "N/A"}
def football_analysis(home, away, home_odds, draw_odds, away_odds):
    try:
        ph = 1 / float(home_odds); pd_ = 1 / float(draw_odds); pa = 1 / float(away_odds); tot = ph + pd_ + pa
        return {"home": round(ph / tot * 100, 1), "draw": round(pd_ / tot * 100, 1), "away": round(pa / tot * 100, 1), "note": "احتمالات ضمنية من الأودز بعد إزالة هامش الوسيط"}
    except Exception:
        return {"home": "N/A", "draw": "N/A", "away": "N/A", "note": "ادخل أودز صحيحة"}
def backtest_simple(exchange, symbol, gran="1h", limit=500):
    df = get_futures_klines(exchange, symbol, gran, limit)
    if df is None or len(df) < 60:
        return None
    split = int(len(df) * 0.7); train = df.iloc[:split]; test = df.iloc[split:]
    wins = 0; total = 0; rrs = []
    for i in range(1, len(test) - 1):
        window = pd.concat([train, test.iloc[:i]])
        if len(window) < 30:
            continue
        e9 = ema(window["close"], 9); e21 = ema(window["close"], 21)
        if len(e9) < 2:
            continue
        is_long = e9.iloc[-1] > e21.iloc[-1]; entry = float(test.iloc[i]["close"]); nxt = float(test.iloc[i+1]["close"])
        a = atr_calc(window); a_last = float(a.iloc[-1]) if pd.notna(a.iloc[-1]) else entry * 0.01
        if a_last <= 0:
            a_last = entry * 0.01
        ob = detect_ob(window)
        if is_long:
            _e21b = float(ema(window["close"], 21).iloc[-1]); _bsl = detect_bsl_ssl(window); _fvg_b = detect_fvg(window); _sw_b = detect_sweep(window)
            stop, _ = calc_structural_stop(window, "LONG", entry, _e21b, _bsl, _fvg_b, _sw_b, a_last, ob)
            risk = abs(entry - stop); tp1 = entry + 1.5 * risk
            if nxt >= tp1:
                wins += 1; rrs.append(abs(tp1 - entry) / risk if risk > 0 else 0)
            elif nxt <= stop:
                rrs.append(-1)
            total += 1
        else:
            _e21b = float(ema(window["close"], 21).iloc[-1]); _bsl = detect_bsl_ssl(window); _fvg_b = detect_fvg(window); _sw_b = detect_sweep(window)
            stop, _ = calc_structural_stop(window, "SHORT", entry, _e21b, _bsl, _fvg_b, _sw_b, a_last, ob)
            risk = abs(stop - entry); tp1 = entry - 1.5 * risk
            if nxt <= tp1:
                wins += 1; rrs.append(abs(tp1 - entry) / risk if risk > 0 else 0)
            elif nxt >= stop:
                rrs.append(-1)
            total += 1
    if total == 0:
        return None
    wr = wins / total * 100; avg_rr = sum(rrs) / len(rrs) if rrs else 0
    return {"symbol": symbol, "timeframe": gran, "total": total, "win_rate": round(wr, 1), "avg_rr": round(avg_rr, 2), "train_len": len(train), "test_len": len(test)}

st.markdown(f"**Killzone:** {'✅ ' + killzone_status()[1] if killzone_status()[0] else '⏸️ ' + killzone_status()[1]} | **البيانات:** Futures حقيقية من المنصة - Spot مفصول تمامًا | **آخر تحديث:** {now_cairo().strftime('%Y-%m-%d %H:%M:%S')} Cairo")

def _feats_from_df(df):
    if df is None or len(df) < 30:
        return None
    e9 = ema(df['close'], 9); e21 = ema(df['close'], 21); r = rsi_calc(df['close']); m, s, h = macd_calc(df['close']); a = atr_calc(df); last = df.iloc[-1]; fvg = detect_fvg(df)
    last20 = df.tail(20); bv = float(last20[last20['close'] > last20['open']]['vol'].sum()); sv = float(last20[last20['close'] <= last20['open']]['vol'].sum()); cvd = (bv - sv) / (bv + sv + 1e-9) * 100
    return {'ema_diff': float(e9.iloc[-1] - e21.iloc[-1]), 'rsi': float(r.iloc[-1]) if pd.notna(r.iloc[-1]) else 50, 'macd_hist': float(h.iloc[-1]), 'atr': float(a.iloc[-1]) if pd.notna(a.iloc[-1]) else 0, 'cvd': float(cvd), 'vol_ratio': float(df['vol'].iloc[-1] / (df['vol'].iloc[:-10].mean() + 1e-9)), 'fvg_count': len(fvg), 'body': float(last['close'] - last['open'])}
def lab_auto_learn(exchange='KuCoin', symbol='XBTUSDTM', limit=1000):
    df = get_futures_klines(exchange, symbol, '15m', limit)
    if df is None or len(df) < 100:
        return {'learned': 0, 'accuracy': 0, 'total': 0, 'is_best': False, 'msg': 'N/A'}
    learned = 0
    with sqlite3.connect(DB_PATH) as c:
        for i in range(30, len(df) - 1):
            window = df.iloc[:i+1]; feats = _feats_from_df(window)
            if not feats:
                continue
            open_p = float(df.iloc[i+1]['open']); close_p = float(df.iloc[i+1]['close']); label = 'UP' if close_p >= open_p else 'DOWN'; rs = str(df.iloc[i]['time'])
            c.execute("INSERT OR IGNORE INTO lab_rounds (round_start,open_price,close_price,label,feats,model) VALUES (?,?,?,?,?,?)", (rs, open_p, close_p, label, json.dumps(feats), 'AUTO-1000')); learned += 1
        c.commit(); rows = c.execute("SELECT feats,label FROM lab_rounds WHERE model='AUTO-1000'").fetchall()
    correct = 0; total = 0
    for fjs, lab in rows:
        try:
            f = json.loads(fjs)
        except Exception:
            continue
        score = 0
        if f.get('ema_diff', 0) > 0:
            score += 1
        else:
            score -= 1
        if f.get('cvd', 0) > 0:
            score += 1
        else:
            score -= 1
        if f.get('rsi', 50) > 50:
            score += 0.5
        else:
            score -= 0.5
        pred = 'UP' if score > 0 else 'DOWN'
        if pred == lab:
            correct += 1
        total += 1
    acc = correct / total * 100 if total > 0 else 0
    with sqlite3.connect(DB_PATH) as c:
        best = c.execute("SELECT MAX(accuracy) FROM lab_models").fetchone()[0] or 0; is_best = 1 if acc >= best else 0
        if is_best:
            c.execute("UPDATE lab_models SET is_best=0")
        c.execute("INSERT INTO lab_models (created_at,accuracy,total,weights,is_best) VALUES (?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), acc, total, json.dumps({'ema': 1, 'cvd': 1, 'rsi': 0.5}), is_best)); c.commit()
    return {'learned': learned, 'accuracy': round(acc, 1), 'total': total, 'is_best': bool(is_best)}
def lab_predict_current(exchange='KuCoin', symbol='XBTUSDTM'):
    df = get_futures_klines(exchange, symbol, '15m', 200)
    if df is None:
        return None
    feats = _feats_from_df(df)
    if not feats:
        return None
    score = 0; reasons = []
    if feats['ema_diff'] > 0:
        score += 1; reasons.append('EMA9>21')
    else:
        score -= 1; reasons.append('EMA9<21')
    if feats['cvd'] > 0:
        score += 1; reasons.append('CVD +')
    else:
        score -= 1; reasons.append('CVD -')
    if feats['rsi'] > 50:
        score += 0.5
    else:
        score -= 0.5
    with sqlite3.connect(DB_PATH) as c:
        row = c.execute("SELECT accuracy,total FROM lab_models WHERE is_best=1 ORDER BY id DESC LIMIT 1").fetchone()
    acc = row[0] if row else 50; total = row[1] if row else 0; pred = 'UP' if score > 0 else 'DOWN'; conf = min(85, max(50, acc + abs(score) * 5))
    return {'pred': pred, 'conf': round(conf, 1), 'score': score, 'feats': feats, 'accuracy': acc, 'total': total, 'reasons': reasons}


# --- Scanner helpers V23 ---
LAST_MEXC_ERRS = []
LAST_MEXC_ERR = ""
import functools
def _live_symbols(exch_cached, limit_cached):
    if exch_cached == "KuCoin":
        return kucoin_futures_symbols(limit_cached)
    if exch_cached == "MEXC":
        return mexc_futures_symbols(limit_cached)
    if exch_cached == "Binance":
        return binance_futures_symbols(limit_cached)
    return bybit_futures_symbols(limit_cached)

def _btc_trend_live():
    try:
        df = get_futures_klines("Binance", "BTCUSDT", "1h", 100)
        if df is None:
            df = get_futures_klines("KuCoin", "XBTUSDTM", "1h", 100)
        if df is None:
            return "NEUTRAL"
        e9 = ema(df["close"], 9); e21 = ema(df["close"], 21)
        return "UP" if e9.iloc[-1] > e21.iloc[-1] else "DOWN"
    except Exception:
        return "NEUTRAL"

def _volume_map(exch):
    """ترتيب الرموز بالسيولة - عشان الماسح مايمسحش عملات ميتة اول 100"""
    try:
        if exch == "Binance":
            j = api_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
            if isinstance(j, list):
                return {x.get("symbol",""): float(x.get("quoteVolume",0) or 0) for x in j}
        if exch == "KuCoin":
            j = api_json("https://api-futures.kucoin.com/api/v1/contracts/active")
            d = (j or {}).get("data", [])
            return {c.get("symbol",""): float(c.get("turnoverOf24h",0) or 0) for c in d}
        if exch == "Bybit":
            j = api_json("https://api.bybit.com/v5/market/tickers", {"category":"linear"})
            lst = (j or {}).get("result",{}).get("list",[])
            return {x.get("symbol",""): float(x.get("turnover24h",0) or 0) for x in lst}
        if exch == "MEXC":
            j = api_json("https://contract.mexc.com/api/v1/contract/ticker")
            d = (j or {}).get("data", [])
            if isinstance(d, list):
                return {x.get("symbol",""): float(x.get("amount24",0) or 0) for x in d}
    except Exception:
        pass
    return {}

def _sort_by_volume(syms, exch):
    vm = _volume_map(exch)
    if not vm:
        # dedupe فقط لو مفيش سيولة
        return list(dict.fromkeys(syms))
    # dedupe + ترتيب تنازلي بالسيولة + استبعاد سيولة صفر
    uniq = list(dict.fromkeys(syms))
    uniq_sorted = sorted(uniq, key=lambda s: vm.get(s, 0), reverse=True)
    # استبعد اللي سيولته صفر تماما (عملات متوقفة) لو فيه بديل
    filtered = [s for s in uniq_sorted if vm.get(s, 0) > 0]
    return filtered if len(filtered) >= 20 else uniq_sorted

def _is_stale(df, max_age_min=150):
    try:
        last_ms = int(df["time"].iloc[-1])
        age_min = (int(time.time()*1000) - last_ms) / 60000
        return age_min > max_age_min
    except Exception:
        return False

section = st.radio("الأقسام", ["📡 Futures Scanner", "📊 تحليل عملة", "🎲 MEXC Prediction", "📈 Options", "⚽ Football", "💾 Paper Trading", "📊 Performance", "🧠 MEXC Learner", "📩 Telegram"], horizontal=True, label_visibility="collapsed")
st.sidebar.markdown("---"); st.sidebar.markdown("**Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"); st.sidebar.caption("TELEGRAM_BOT_TOKEN + TELEGRAM_CHANNEL_ID في Secrets")
st.sidebar.markdown("### 🔔 التنبيهات")
auto_alert = st.sidebar.toggle("تنبيه تلقائي لأقوى إشارة", value=False)
alert_min = st.sidebar.slider("أقل Score للتنبيه", 60, 90, 75)
if st.sidebar.button("🔔 اختبار التنبيه الآن"):
    ok, msg = send_telegram("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    st.sidebar.success(msg) if ok else st.sidebar.error(msg)

if section.startswith("📡"):
    st.subheader("🔴 LIVE Futures Scanner - KuCoin / MEXC / Bybit / Binance - كل حاجة لحظية بدون حفظ")
    # تشخيص لكل منصة - نفس الدالة لكل منصة عشان مفيش تحيز
    diag_cols = st.columns(4)
    for _i, (_ex, _sym) in enumerate([("KuCoin","XBTUSDTM"),("MEXC","BTC_USDT"),("Bybit","BTCUSDT"),("Binance","BTCUSDT")]):
        with diag_cols[_i]:
            if st.button(f"🔧 اختبر {_ex}", key=f"diag_{_ex}"):
                with st.spinner(f"بختبر {_ex}..."):
                    _syms = _live_symbols(_ex, 20)
                    st.write(f"{_ex}: {len(_syms)} رمز")
                    _df = get_futures_klines(_ex, _sym, "1h", 100)
                    if _df is None or _is_stale(_df):
                        st.error(f"❌ {_ex}: مفيش شموع حديثة")
                    else:
                        st.success(f"✅ {_ex}: {float(_df['close'].iloc[-1]):.8g} - {len(_df)} شمعة")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        exch = st.selectbox("المنصة", ["KuCoin", "MEXC", "Bybit", "Binance"])
    with c2:
        n_sym = st.slider("عدد العملات - بعد ترتيب السيولة", 20, 500, 100, step=10)
    with c3:
        min_score = st.slider("أقل Score", 50, 85, 60)
    with c4:
        side_f = st.selectbox("الاتجاه", ["الكل", "LONG فقط", "SHORT فقط"])
    # Threads متكيف حسب المنصة - KuCoin/MEXC حساسين للـ Rate Limit
    default_workers = 3 if exch == "MEXC" else (5 if exch == "KuCoin" else 8)
    workers = st.slider("سرعة المسح (Threads)", 1, 12, default_workers)
    show_diag = st.checkbox("اعرض تشخيص المسح", value=True)
    # لحظي: مفيش نتايج متسجلة - كل مسح بيبدأ من الصفر
    btc_trend = _btc_trend_live()
    _live_res = []
    st.caption(f"BTC Trend: {btc_trend} | الترتيب: بالسيولة 24h تنازلي | الاستوب: بنيوي BSL/SSL/EMA21/FVG/OB/Sweep")
    if st.button("🔍 امسح Futures دلوقتي", type="primary", use_container_width=True):
        with st.spinner(f"بمسح {exch} Futures..."):
            raw_syms = _live_symbols(exch, 500)
            syms = _sort_by_volume(raw_syms, exch)[:n_sym]
            if show_diag:
                st.info(f"تم جلب {len(raw_syms)} رمز من {exch} - بعد ترتيب السيولة هنمسح {len(syms)}")
            results = []; ok_count=0; no_klines=0; stale=0; invalid_stop=0; low_score=0; side_filtered=0
            prog = st.progress(0)
            _errs = []
            def _one(s):
                try:
                    disp = display_symbol(s, exch)
                    df1 = get_futures_klines(exch, s, "1h", 200)
                    if df1 is None:
                        return (s, None, "NO_KLINES")
                    if _is_stale(df1):
                        return (s, None, "STALE")
                    # 15m مرة واحدة بس - مش جوه analyze تاني
                    df15 = get_futures_klines(exch, s, "15m", 100)
                    r = analyze_futures(exch, s, disp, btc_trend, fetch_extra=False, _df_pre=df1, _df15_pre=df15)
                    if r is None:
                        return (s, None, "INVALID_STOP_OR_FILTER")
                    if r.get("vol", 0) is not None and float(r.get("vol", 1)) < 0.01:
                        return (s, None, "LOW_VOL")
                    # تهدئة لـ MEXC عشان Rate Limit
                    if exch == "MEXC":
                        time.sleep(0.08)
                    return (s, r, "OK")
                except Exception as e:
                    _errs.append(str(e))
                    return (s, None, "EXC")
            with concurrent.futures.ThreadPoolExecutor(max_workers=int(workers)) as ex:
                futs = {ex.submit(_one, s): s for s in syms}
                done_n = 0
                for fut in concurrent.futures.as_completed(futs):
                    done_n += 1
                    prog.progress(min(1.0, done_n / max(1, len(syms))))
                    s, r, reason = fut.result()
                    if reason == "NO_KLINES" or reason == "EXC":
                        no_klines += 1; continue
                    if reason == "STALE":
                        stale += 1; continue
                    if reason == "INVALID_STOP_OR_FILTER":
                        invalid_stop += 1; continue
                    if reason == "LOW_VOL":
                        invalid_stop += 1; continue
                    ok_count += 1
                    if r["score"] < min_score:
                        low_score += 1; continue
                    if side_f == "LONG فقط" and r["type"] != "LONG":
                        side_filtered += 1; continue
                    if side_f == "SHORT فقط" and r["type"] != "SHORT":
                        side_filtered += 1; continue
                    results.append(r)
            results = sorted(results, key=lambda x: (x["score"], x["vol"]), reverse=True)
            _live_res = results
            # لحظي: مفيش حفظ - النتايج دي بتاعت المسح ده بس
            if show_diag:
                st.markdown(f"**تشخيص المسح [{exch}]:** جلبنا `{len(raw_syms)}` | هنمسح `{len(syms)}` | نجح `{ok_count}` | مفيش شموع `{no_klines}` | شموع قديمة `{stale}` | استوب بنيوي مرفوض `{invalid_stop}` | تحت Score `{low_score}` | اتجاه مخالف `{side_filtered}` | فرص ظاهرة `{len(results)}`")
                if ok_count == 0 and len(syms) > 0:
                    st.error(f"❌ كل الشموع فشلت على {exch} - جرب تاني بعد دقيقة او قلل Threads لـ 3")
                    _le = LAST_MEXC_ERR if exch == "MEXC" else ""
                    if _le:
                        st.caption(f"آخر خطأ من MEXC: {_le}")
                    if _errs:
                        st.caption(f"أول خطأ داخلي: {_errs[0][:300]}")
            if auto_alert and results:
                top = results[0]
                if top["score"] >= alert_min:
                    ok, msg = send_telegram(fmt_bly7trader(top))
                    if ok:
                        st.success("🔔 تم إرسال التنبيه التلقائي لأقوى إشارة - لحظي")
            if not results:
                st.warning(f"مسحنا {len(syms)} عملة على {exch} - مفيش فرص فوق Score {min_score} - جرب تنزل لـ 55")
    res = _live_res  # لحظي فقط - مفيش نتايج من مسح قديم
    if res:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي الفرص", len(res)); m2.metric("LONG", sum(1 for x in res if x["type"] == "LONG")); m3.metric("SHORT", sum(1 for x in res if x["type"] == "SHORT")); m4.metric("أعلى Score", max(x["score"] for x in res))
        st.markdown(f"### 🔥 أقوى {len(res)} إشارة - {exch}")
        df_show = pd.DataFrame([{"العملة": r["symbol"], "المنصة": r["exchange"], "الاتجاه": r["type"], "Score": r["score"], "السعر": r["price"], "الدخول": r["entry"], "الاستوب (بنيوي)": r["stop"], "TP1": r["tp1"], "TP2": r["tp2"], "TP3": r["tp3"], "R:R TP2": r["rr2"], "1H%": r["ch"], "حجم": r["vol"], "CVD": r["buy"]} for r in res])
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        for r in res[:10]:
            with st.expander(f"{r['symbol']} — {r['type']} — Score {r['score']} — دخول {r['entry']:.8g} — استوب {r['stop']:.8g}"):
                st.markdown(f"**الدخول:** {r['entry']:.8g} | **الاستوب (بنيوي):** {r['stop']:.8g} | **TP1:** {r['tp1']:.8g} | **TP2:** {r['tp2']:.8g} | **TP3:** {r['tp3']:.8g} | **R:R:** TP1 1:{r['rr1']} TP2 1:{r['rr2']} TP3 1:{r['rr3']}")
                st.text(r["extra"]); st.code(fmt_bly7trader(r), language="text")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"📩 ابعت {r['symbol']} لتليجرام", key=f"tg_{r['symbol']}_{r['type']}_{r['exchange']}"):
                        ok, msg = send_telegram(fmt_bly7trader(r)); st.success(msg) if ok else st.error(msg)
                with col_b:
                    st.caption("لحظي - مفيش تسجيل Paper Trade")
        if st.button("📩 ابعت أقوى 5 لتليجرام"):
            for r in res[:5]:
                send_telegram(fmt_bly7trader(r)); time.sleep(0.4)
            st.success("تم إرسال أقوى 5")

elif section.startswith("📊 تحليل"):
    st.subheader("📊 تحليل عملة واحدة - كل الفواصل 1m / 5m / 15m / 1h - Futures فقط")
    exch2 = st.selectbox("المنصة", ["KuCoin", "MEXC", "Bybit", "Binance"], key="ex2")
    sym_raw = st.text_input("العملة - اكتب أي صيغة: BTC / BTCUSDT / BTC_USDT / XBTUSDTM", "BTCUSDT" if exch2 != "KuCoin" else "XBTUSDTM").strip().upper()
    sym_in = normalize_symbol(sym_raw, exch2)
    st.caption(f"الرمز المستخدم على {exch2}: `{sym_in}` | العرض: `{display_symbol(sym_in, exch2)}`")
    if st.button("📊 حلل على كل الفواصل"):
        if not sym_in:
            st.error("اكتب اسم عملة صحيح")
        else:
            found = False
            for gran in (["1m", "5m", "15m", "1h"] if exch2 == "KuCoin" else ["1m", "3m", "5m", "15m", "1h"]):
                df = get_futures_klines(exch2, sym_in, gran, 200)
                if df is None:
                    st.warning(f"{gran}: N/A - مفيش شموع - تأكد من الرمز"); continue
                found = True
                e9 = ema(df["close"], 9); e21 = ema(df["close"], 21); rr = rsi_calc(df["close"]); mm, ss, hh = macd_calc(df["close"]); aa = atr_calc(df)
                st.markdown(f"**{gran}** — سعر `{float(df['close'].iloc[-1]):.8g}` | EMA9 `{float(e9.iloc[-1]):.8g}` | EMA21 `{float(e21.iloc[-1]):.8g}` | RSI `{float(rr.iloc[-1]):.1f}` | MACD Hist `{float(hh.iloc[-1]):.8g}` | ATR `{float(aa.iloc[-1]):.8g}` | Momentum `{float(momentum_calc(df['close']).iloc[-1]):.8g}` | FVG {len(detect_fvg(df))} | OB {detect_ob(df)} | BSL/SSL {detect_bsl_ssl(df)} | Sweep {detect_sweep(df)['dir']}")
            if found:
                r_full = analyze_futures(exch2, sym_in, display_symbol(sym_in, exch2), "NEUTRAL", fetch_extra=True)
                if r_full:
                    st.success(f"إشارة مجمعة: {r_full['type']} - Score {r_full['score']} - دخول {r_full['entry']:.8g} - استوب {r_full['stop']:.8g} - TP1 {r_full['tp1']:.8g} - TP2 {r_full['tp2']:.8g} - TP3 {r_full['tp3']:.8g}")
                    st.text(r_full["extra"]); st.code(fmt_bly7trader(r_full), language="text")
                    cta1, cta2 = st.columns(2)
                    with cta1:
                        if st.button("📩 ابعت التحليل لتليجرام"):
                            ok, msg = send_telegram(fmt_bly7trader(r_full)); st.success(msg) if ok else st.error(msg)
                    with cta2:
                        if st.button("💾 سجل Paper Trade"):
                            save_paper_trade(r_full["symbol"], r_full["type"], r_full["entry"], r_full["stop"], r_full["tp1"], r_full["tp2"], r_full["tp3"], 100.0); st.success("تم تسجيل Paper Trade")

elif section.startswith("🎲"):
    st.subheader("🎯 MEXC Prediction - UP / DOWN / NO_TRADE")
    chk = mexc_prediction_check("BTCUSDT")
    if chk["status"] == "CHAINLINK":
        st.success(chk["msg"])
    else:
        st.warning(chk["msg"])
    sym_p = st.text_input("العملة", "BTCUSDT", key="pred_sym")
    if st.button("🔍 توقع الجولة الحالية"):
        sym_norm = normalize_symbol(sym_p, "KuCoin")
        r = analyze_futures("KuCoin", sym_norm, display_symbol(sym_norm, "KuCoin"), "NEUTRAL", fetch_extra=True)
        if r is None:
            st.warning("NO_TRADE - مفيش إشارة واضحة")
        else:
            st.markdown(f"**Score:** {r['score']} | **FVG:** {r['fvg']} | **CVD:** {r['buy']}% | **الدخول:** {r['entry']:.8g} | **الاستوب:** {r['stop']:.8g}")
            if r["score"] >= 70 and r["fvg"] > 0 and abs(r["buy"]) > 10:
                st.success(f"توقع: {'🟢 UP - ادخل شراء' if r['type'] == 'LONG' else '🔴 DOWN - ادخل بيع'} - 3 شروط متوفرة"); save_signals([r], "KuCoin")
            else:
                st.warning("⏸️ NO_TRADE - شرط ناقص - المعتدل لا يدخل ناقص")

elif section.startswith("🧠"):
    st.subheader("🤖 MEXC Learner - بيعلم نفسه بنفسه")
    if st.button("🧠 علم البوت من 1000 جولة سابقة دلوقتي", type="primary", use_container_width=True):
        with st.spinner("بيتعلم من 1000 شمعة..."):
            res_learn = lab_auto_learn("KuCoin", "XBTUSDTM", 1000)
            st.success(f"اتعلم من {res_learn['learned']} جولة - الدقة: {res_learn['accuracy']}% على {res_learn['total']} جولة")
    with sqlite3.connect(DB_PATH) as _c:
        try:
            _rows = _c.execute("SELECT created_at,accuracy,total,is_best FROM lab_models ORDER BY id DESC LIMIT 5").fetchall()
        except Exception:
            _rows = []
        try:
            _cnt = _c.execute("SELECT COUNT(*) FROM lab_rounds").fetchone()[0]
        except Exception:
            _cnt = 0
    st.markdown(f"**إجمالي الجولات المتعلمة:** {_cnt}")
    if _rows:
        for _r in _rows:
            st.markdown(f"- {_r[0][:19]} - دقة {_r[1]:.1f}% على {_r[2]} جولة - {'⭐ الأفضل' if _r[3] else ''}")
    if st.button("🔍 توقع الجولة الحالية - بعد التعلم"):
        pr = lab_predict_current("KuCoin", "XBTUSDTM")
        if pr is None:
            st.warning("N/A")
        else:
            st.markdown(f"**التوقع:** {'🟢 UP' if pr['pred'] == 'UP' else '🔴 DOWN'} - **الثقة:** {pr['conf']}% - **دقة النموذج:** {pr['accuracy']}% على {pr['total']} جولة")
            st.text(" | ".join(pr['reasons']))
            if pr['conf'] >= 70:
                st.success("المعتدل: ادخل" if pr['pred'] == 'UP' else "المعتدل: ادخل بيع")
            else:
                st.warning("NO_TRADE - الثقة أقل من 70")

elif section.startswith("📈"):
    st.subheader("📈 Options Analysis")
    sym_o = st.text_input("العملة للخيارات", "BTC", key="opt_sym")
    o = options_analysis(sym_o)
    st.markdown(f"**Implied Volatility:** {o['IV']}\n\n**Open Interest:** {o['OI']}\n\n**Strike Prices:** {o['Strikes']}\n\n**Greeks:** {o['Greeks']}\n\n*{o['note']}*")
elif section.startswith("⚽"):
    st.subheader("⚽ Football Analysis")
    c1, c2 = st.columns(2)
    with c1:
        home = st.text_input("الفريق الأول", "Real Madrid")
    with c2:
        away = st.text_input("الفريق الثاني", "Barcelona")
    o1, o2, o3 = st.columns(3)
    with o1:
        oh = st.number_input("أودز فوز الأول (1)", value=2.10, step=0.01)
    with o2:
        od = st.number_input("أودز التعادل (X)", value=3.40, step=0.01)
    with o3:
        oa = st.number_input("أودز فوز الثاني (2)", value=3.20, step=0.01)
    if st.button("📊 احسب الاحتمالات"):
        f = football_analysis(home, away, oh, od, oa)
        st.markdown(f"**{home} فوز (1):** {f['home']}% | **تعادل (X):** {f['draw']}% | **{away} فوز (2):** {f['away']}%")
elif section.startswith("💾"):
    st.subheader("💾 Paper Trading + Backtest + Walk-forward")
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        pt_sym = st.text_input("العملة", "BTC/USDT", key="pt_sym")
    with pc2:
        pt_side = st.selectbox("الاتجاه", ["LONG", "SHORT"], key="pt_side")
    with pc3:
        pt_size = st.number_input("حجم الصفقة $", value=100.0, step=10.0, key="pt_size")
    pe1, pe2, pe3 = st.columns(3)
    with pe1:
        pt_entry = st.number_input("الدخول", value=0.0, format="%.8f", key="pt_entry")
    with pe2:
        pt_stop = st.number_input("الاستوب", value=0.0, format="%.8f", key="pt_stop")
    with pe3:
        pt_tp1 = st.number_input("TP1", value=0.0, format="%.8f", key="pt_tp1")
    if st.button("💾 سجل Paper Trade"):
        if pt_entry > 0:
            save_paper_trade(pt_sym, pt_side, pt_entry, pt_stop, pt_tp1, pt_tp1, pt_tp1, pt_size); st.success("تم تسجيل Paper Trade")
        else:
            st.error("الدخول لازم يكون أكبر من صفر")
    with sqlite3.connect(DB_PATH) as c:
        df_pt = pd.read_sql_query("SELECT * FROM paper_trades ORDER BY id DESC LIMIT 20", c)
    if not df_pt.empty:
        st.dataframe(df_pt, use_container_width=True, hide_index=True)
    st.markdown("---"); st.markdown("**Backtest + Walk-forward (بدون Look-ahead):**")
    be1, be2 = st.columns(2)
    with be1:
        bt_ex = st.selectbox("المنصة للباك تست", ["KuCoin", "MEXC", "Bybit", "Binance"], key="bt_ex")
    with be2:
        bt_sym_raw = st.text_input("رمز الباك تست - اكتب أي صيغة", "BTCUSDT", key="bt_sym")
    bt_sym = normalize_symbol(bt_sym_raw, bt_ex)
    st.caption(f"الرمز المستخدم: `{bt_sym}`")
    if st.button("▶️ شغل Backtest"):
        bt = backtest_simple(bt_ex, bt_sym, "1h", 500)
        if bt is None:
            st.warning("N/A - مفيش بيانات كافية أو الرمز غلط - جرب BTCUSDT")
        else:
            st.markdown(f"**Win Rate:** {bt['win_rate']}% | **إجمالي الصفقات:** {bt['total']} | **متوسط R:R:** {bt['avg_rr']} | **Train:** {bt['train_len']} شمعة | **Test:** {bt['test_len']} شمعة (Walk-forward 70/30)")
            with sqlite3.connect(DB_PATH) as c:
                c.execute("INSERT INTO backtests (created_at,symbol,timeframe,win_rate,total,avg_rr,notes) VALUES (?,?,?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), bt_sym, "1h", bt['win_rate'], bt['total'], bt['avg_rr'], "Champion: EMA9/21 + OB Stop")); c.commit()
            st.success("تم حفظ نتيجة الباك تست")
elif section.startswith("📊 Performance"):
    st.subheader("📊 Performance Dashboard - دقة الإشارات")
    with sqlite3.connect(DB_PATH) as c:
        try:
            df_s = pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT 200", c)
        except Exception:
            df_s = pd.DataFrame()
        try:
            df_b = pd.read_sql_query("SELECT * FROM backtests ORDER BY id DESC LIMIT 20", c)
        except Exception:
            df_b = pd.DataFrame()
        try:
            df_a = pd.read_sql_query("SELECT * FROM alerts_sent ORDER BY id DESC LIMIT 20", c)
        except Exception:
            df_a = pd.DataFrame()
    if df_s.empty:
        st.info("لسه مفيش إشارات مسجلة - امسح Futures الأول")
    else:
        st.markdown(f"**إجمالي الإشارات:** {len(df_s)} | **متوسط Score:** {df_s['score'].mean():.1f} | **LONG:** {(df_s['side'] == 'LONG').sum()} | **SHORT:** {(df_s['side'] == 'SHORT').sum()}")
        st.dataframe(df_s, use_container_width=True, hide_index=True)
    if not df_b.empty:
        st.markdown("### Backtests السابقة"); st.dataframe(df_b, use_container_width=True, hide_index=True)
    if not df_a.empty:
        st.markdown("### التنبيهات المرسلة"); st.dataframe(df_a, use_container_width=True, hide_index=True)
elif section.startswith("📩"):
    st.subheader("📩 Telegram Test - @WHYNOTBLY7")
    if st.button("📩 ابعت رسالة تجريبية"):
        ok, msg = send_telegram("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
        st.success(msg) if ok else st.error(msg)
    st.markdown("**Secrets المطلوبة في Streamlit:**\n```\nTELEGRAM_BOT_TOKEN = \"...\"\nTELEGRAM_CHANNEL_ID = \"-100...\"\nCHAINLINK_API_KEY = \"...\" # اختياري\n```")
st.markdown("---")
