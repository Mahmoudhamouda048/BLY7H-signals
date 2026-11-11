import os, json, time, math, sqlite3, hashlib, concurrent.futures, threading
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import requests
import streamlit as st

st.set_page_config(page_title="BLY7TRADER SIGNALS", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")
CAIRO = ZoneInfo("Africa/Cairo")
DB_PATH = "bly7h_signals.db"
TIMEOUT = 12
STABLES = {"USDCUSDT","BUSDUSDT","DAIUSDT","FDUSDUSDT","USDEUSDT"}

# ===== FIX 1: Thread-local Session - اهم اصلاح ل KuCoin =====
_thread_local = threading.local()
def get_session():
    if not hasattr(_thread_local, "s"):
        s = requests.Session()
        s.headers.update({"User-Agent": "BLY7TRADER-SIGNALS/V21-ALL-FIXED-BINANCE"})
        _thread_local.s = s
    return _thread_local.s
SESSION = get_session()

st.markdown("<div style='border:2px solid #FFD700;background:#0B0E14;padding:14px;box-shadow:0 24px 80px rgba(0,0,0,.55)'>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center'><div style='font-size:10px;font-weight:900;letter-spacing:0.28em;color:#FFD700'>BLY7TRADER SIGNALS - POSTER STYLE</div><div style='font-size:42px;font-weight:900;letter-spacing:4px;line-height:1.05;background:linear-gradient(90deg,#FFD700,#FF8C00,#FFD700);-webkit-background-clip:text;-webkit-text-fill-color:transparent'>BLY7TRADER<br>SIGNALS</div><div style='color:#FFD700;font-size:12px;letter-spacing:3px'>BLY7H ULTIMATE V21 ALL FIXED + BINANCE - @WHYNOTBLY7 - PREDICT BEFORE THE MOVE</div></div>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;margin-top:12px'><span style='display:inline-block;background:#FFD700;color:#000;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:900'>SELF-LEARNING BOT - Learns from 1000 rounds</span> <span style='display:inline-block;background:#12161F;border:1px solid #1E2530;color:#E6E9EF;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700'>Monthly Rent $149 (Foreign $290) - Full Ownership $2499 (Foreign $4000)</span></div>", unsafe_allow_html=True)
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

def save_signals(signals, exchange):
    if not signals:
        return
    rows = []
    stamp = datetime.now(timezone.utc).isoformat()
    for s in signals:
        rows.append((stamp, exchange, s["symbol"], s["type"], s["score"], s["price"], s["entry"], s["stop"], s["tp1"], s["tp2"], s.get("tp3", s["tp2"]), s["ch"], s["vol"], s["buy"], "OPEN"))
    with sqlite3.connect(DB_PATH) as c:
        c.executemany("INSERT INTO signals (created_at,exchange,symbol,side,score,price,entry,stop,tp1,tp2,tp3,change_pct,volume_ratio,cvd,outcome) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        c.commit()

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
    return f"""BLY7TRADER\n\n{side} — {s['symbol']}\n⭐ Score: {s['score']}/100\n\n💵 Price: {s['price']:.8g}\n🎯 Entry: {s['entry']:.8g}\n⛔ Stop Loss: {s['stop']:.8g}\n✅ TP1: {s['tp1']:.8g}\n🏆 TP2: {s['tp2']:.8g}\n🏆 TP3: {s.get('tp3', s['tp2']):.8g}\n📊 R:R TP1 1:{rr1:.2f} | TP2 1:{rr2:.2f}\n\n📈 1H Change: {s['ch']}%\n📦 Volume: x{s['vol']}\n📊 CVD: {s['buy']}%\n{s.get('extra','')}\n\n📩 Telegram: @WHYNOTBLY7\n#BLY7TRADER"""

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
    # MEXC FIX: ميكسك مش بيقبل 15m / 1h - بيقبل Min15 / Min60 بس
    mexc_map = {"1m": "Min1", "3m": "Min5", "5m": "Min5", "15m": "Min15", "1h": "Min60", "Min1": "Min1", "Min5": "Min5", "Min15": "Min15", "Min60": "Min60"}
    mexc_interval = mexc_map.get(interval, "Min15")
    p = api_json("https://contract.mexc.com/api/v1/contract/kline", {"symbol": symbol, "interval": mexc_interval, "limit": limit})
    if not p:
        return None
    d = p.get("data", {})
    # MEXC بيرجع الداتا كـ dict فيه اعمدة: {"time":[...], "open":[...], "high":[...], "low":[...], "close":[...], "vol":[...]}
    # مش list زي كوكوين - ده كان سبب ان ميكسك يرجع None على طول
    try:
        if isinstance(d, dict) and "time" in d and "close" in d:
            df = pd.DataFrame({"time": d.get("time", []), "open": d.get("open", []), "high": d.get("high", []), "low": d.get("low", []), "close": d.get("close", []), "vol": d.get("vol", [])})
        elif isinstance(d, dict):
            inner = d.get("data", []) or d.get("kline", []) or []
            if not inner or len(inner) < 30:
                return None
            if isinstance(inner[0], dict):
                df = pd.DataFrame(inner)
                df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "vol", "t": "time"})
            else:
                df = pd.DataFrame(inner, columns=["time", "open", "high", "low", "close", "vol"][:len(inner[0])])
        elif isinstance(d, list):
            if len(d) < 30:
                return None
            if isinstance(d[0], dict):
                df = pd.DataFrame(d)
                df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "vol", "t": "time"})
            else:
                df = pd.DataFrame(d, columns=["time", "open", "high", "low", "close", "vol"][:len(d[0])])
        else:
            return None
        for c in ["open", "high", "low", "close", "vol"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna().reset_index(drop=True)
        if len(df) < 30:
            return None
        return df
    except Exception:
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
       
