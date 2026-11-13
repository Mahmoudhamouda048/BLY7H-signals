import os
import json
import time
import math
import sqlite3
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np
import requests
import streamlit as st

# ====================== CONFIG ======================
st.set_page_config(
    page_title="BLY7TRADER ELITE",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

CAIRO = ZoneInfo("Africa/Cairo")
DB_PATH = "bly7h_elite.db"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BLY7TRADER-ELITE/V1"})
TIMEOUT = 12

# ====================== STYLE ======================
st.markdown("""
<style>
.stApp { background: #0B0E14; color: #E6E9EF; }
h1, h2, h3 { color: #E6E9EF !important; }
.stButton > button {
    background: #FFD700; color: #000; font-weight: 900;
    border-radius: 10px; border: 1px solid #FFD700;
}
div[data-testid="stMetric"] {
    background: #12161F; border: 1px solid #1E2530; border-radius: 14px;
}
.stExpander {
    border: 1px solid #1E2530; border-radius: 14px; background: #12161F;
}
section[data-testid="stSidebar"] {
    background: #0F131B; border-right: 1px solid #1E2530;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="border:2px solid #FFD700;background:#0B0E14;padding:16px;border-radius:12px;margin-bottom:12px">
    <div style="text-align:center">
        <div style="font-size:11px;font-weight:900;letter-spacing:0.25em;color:#FFD700">BLY7TRADER ELITE</div>
        <div style="font-size:36px;font-weight:900;letter-spacing:3px;line-height:1.1;
            background:linear-gradient(90deg,#FFD700,#FF8C00,#FFD700);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent">
            BLY7TRADER ELITE
        </div>
        <div style="color:#FFD700;font-size:12px;letter-spacing:2px;margin-top:4px">
            STRUCTURE • ORDER BLOCK • FVG • LIQUIDITY • SELF-LEARNING
        </div>
        <div style="margin-top:10px">
            <span style="background:#FFD700;color:#000;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:900">
                HIGH CONFLUENCE ONLY
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ====================== UTILS ======================
def now_cairo():
    return datetime.now(CAIRO)

def api_json(url, params=None, timeout=TIMEOUT):
    try:
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code != 200:
            return None
        j = r.json()
        if isinstance(j, dict) and j.get("code") not in (None, "200000", 200, 0):
            return None
        return j
    except Exception:
        return None

def safe_float(v, default=0.0):
    try:
        x = float(v)
        return x if pd.notna(x) else default
    except Exception:
        return default

def killzone_status():
    cur = now_cairo()
    mins = cur.hour * 60 + cur.minute
    if 10 * 60 <= mins <= 12 * 60:
        return True, "London Killzone 10:00-12:00 Cairo"
    if 15 * 60 + 30 <= mins <= 17 * 60 + 30:
        return True, "New York Killzone 15:30-17:30 Cairo"
    return False, "خارج Killzone"

# ====================== DATABASE ======================
def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                exchange TEXT,
                symbol TEXT,
                side TEXT,
                score INTEGER,
                price REAL,
                entry REAL,
                stop REAL,
                tp1 REAL,
                tp2 REAL,
                tp3 REAL,
                reasons TEXT,
                tools_used TEXT,
                outcome TEXT DEFAULT 'OPEN',
                pnl REAL DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                symbol TEXT,
                side TEXT,
                entry REAL,
                stop REAL,
                tp1 REAL,
                tp2 REAL,
                tp3 REAL,
                size_usd REAL,
                status TEXT DEFAULT 'OPEN',
                pnl REAL DEFAULT 0,
                exit_price REAL,
                exit_reason TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS learning_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                symbol TEXT,
                side TEXT,
                features TEXT,
                score INTEGER,
                outcome TEXT,
                pnl REAL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS model_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                updated_at TEXT,
                weights TEXT,
                win_rate REAL,
                total_trades INTEGER,
                is_active INTEGER DEFAULT 1
            )
        """)
        c.commit()

init_db()

def get_active_weights():
    default = {
        "structure": 18,
        "order_block": 16,
        "fvg": 14,
        "sweep": 12,
        "mtf": 10,
        "volume": 8,
        "cvd": 8,
        "killzone": 6,
        "ema_align": 5,
        "rsi_filter": 3
    }
    try:
        with sqlite3.connect(DB_PATH) as c:
            row = c.execute(
                "SELECT weights FROM model_weights WHERE is_active=1 ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                return json.loads(row[0])
    except Exception:
        pass
    return default

def save_signal_to_db(signal, exchange):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            INSERT INTO signals
            (created_at, exchange, symbol, side, score, price, entry, stop, tp1, tp2, tp3, reasons, tools_used, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
        """, (
            datetime.now(timezone.utc).isoformat(),
            exchange,
            signal["symbol"],
            signal["type"],
            signal["score"],
            signal["price"],
            signal["entry"],
            signal["stop"],
            signal["tp1"],
            signal["tp2"],
            signal["tp3"],
            json.dumps(signal.get("reasons", []), ensure_ascii=False),
            json.dumps(signal.get("tools_used", []), ensure_ascii=False)
        ))
        c.commit()

def log_for_learning(signal, outcome="OPEN", pnl=0.0):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            INSERT INTO learning_log
            (created_at, symbol, side, features, score, outcome, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            signal["symbol"],
            signal["type"],
            json.dumps(signal.get("features", {}), ensure_ascii=False),
            signal["score"],
            outcome,
            pnl
        ))
        c.commit()

# ====================== INDICATORS ======================
def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()

def rsi(series, n=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(alpha=1/n, adjust=False).mean()
    ma_down = down.ewm(alpha=1/n, adjust=False).mean()
    rs = ma_up / (ma_down.replace(0, np.nan))
    return 100 - (100 / (1 + rs))

def atr(df, n=14):
    tr = pd.concat([
        (df["high"] - df["low"]).abs(),
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def macd(series):
    e12 = ema(series, 12)
    e26 = ema(series, 26)
    line = e12 - e26
    signal = ema(line, 9)
    hist = line - signal
    return line, signal, hist

# ====================== STRUCTURE ENGINE ======================
def detect_swings(df, left=3, right=3):
    highs = []
    lows = []
    for i in range(left, len(df) - right):
        window_high = df["high"].iloc[i-left:i+right+1]
        window_low = df["low"].iloc[i-left:i+right+1]
        if df["high"].iloc[i] >= window_high.max():
            highs.append((i, float(df["high"].iloc[i])))
        if df["low"].iloc[i] <= window_low.min():
            lows.append((i, float(df["low"].iloc[i])))
    return highs, lows

def detect_market_structure(df):
    highs, lows = detect_swings(df, left=2, right=2)
    if len(highs) < 2 or len(lows) < 2:
        return {"bias": "NEUTRAL", "bos": False, "choch": False, "last_high": None, "last_low": None}

    last_high = highs[-1][1]
    prev_high = highs[-2][1]
    last_low = lows[-1][1]
    prev_low = lows[-2][1]

    bias = "NEUTRAL"
    bos = False
    choch = False

    # Simple structure bias
    if last_high > prev_high and last_low > prev_low:
        bias = "BULLISH"
    elif last_high < prev_high and last_low < prev_low:
        bias = "BEARISH"

    # Break of structure
    close = float(df["close"].iloc[-1])
    if bias == "BULLISH" and close > last_high:
        bos = True
    if bias == "BEARISH" and close < last_low:
        bos = True

    return {
        "bias": bias,
        "bos": bos,
        "choch": choch,
        "last_high": last_high,
        "last_low": last_low,
        "prev_high": prev_high,
        "prev_low": prev_low
    }

def detect_order_blocks(df, lookback=30):
    """Proper-ish Order Block: last opposing candle before impulsive move"""
    bullish_obs = []
    bearish_obs = []

    for i in range(5, min(len(df)-1, lookback)):
        # Bullish OB: down candle followed by strong up move
        if df["close"].iloc[i] < df["open"].iloc[i]:
            move = float(df["close"].iloc[i+1:i+4].max() - df["low"].iloc[i])
            atr_val = float(atr(df.iloc[:i+1]).iloc[-1]) if i > 14 else 0
            if atr_val > 0 and move > 1.2 * atr_val:
                bullish_obs.append({
                    "type": "BULLISH_OB",
                    "top": float(df["high"].iloc[i]),
                    "bottom": float(df["low"].iloc[i]),
                    "mid": (float(df["high"].iloc[i]) + float(df["low"].iloc[i])) / 2,
                    "index": i
                })

        # Bearish OB: up candle followed by strong down move
        if df["close"].iloc[i] > df["open"].iloc[i]:
            move = float(df["high"].iloc[i] - df["close"].iloc[i+1:i+4].min())
            atr_val = float(atr(df.iloc[:i+1]).iloc[-1]) if i > 14 else 0
            if atr_val > 0 and move > 1.2 * atr_val:
                bearish_obs.append({
                    "type": "BEARISH_OB",
                    "top": float(df["high"].iloc[i]),
                    "bottom": float(df["low"].iloc[i]),
                    "mid": (float(df["high"].iloc[i]) + float(df["low"].iloc[i])) / 2,
                    "index": i
                })

    return {
        "bullish": bullish_obs[-2:] if bullish_obs else [],
        "bearish": bearish_obs[-2:] if bearish_obs else []
    }

def detect_fvg(df, lookback=40):
    fvgs = []
    start = max(1, len(df) - lookback)
    for i in range(start, len(df) - 1):
        # Bullish FVG
        if df["low"].iloc[i+1] > df["high"].iloc[i-1]:
            top = float(df["low"].iloc[i+1])
            bottom = float(df["high"].iloc[i-1])
            fvgs.append({
                "type": "BULLISH_FVG",
                "top": top,
                "bottom": bottom,
                "mid": (top + bottom) / 2,
                "size": top - bottom,
                "index": i
            })
        # Bearish FVG
        if df["high"].iloc[i+1] < df["low"].iloc[i-1]:
            top = float(df["low"].iloc[i-1])
            bottom = float(df["high"].iloc[i+1])
            fvgs.append({
                "type": "BEARISH_FVG",
                "top": top,
                "bottom": bottom,
                "mid": (top + bottom) / 2,
                "size": top - bottom,
                "index": i
            })
    return fvgs[-5:] if fvgs else []

def detect_liquidity_sweep(df, lookback=25):
    if len(df) < lookback + 5:
        return {"sweep": False, "direction": "NONE", "level": None}

    recent = df.iloc[-lookback-2:-2]
    bsl = float(recent["high"].max())
    ssl = float(recent["low"].min())

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Bearish sweep (took highs then closed back)
    if float(last["high"]) > bsl and float(last["close"]) < bsl:
        return {"sweep": True, "direction": "BEARISH_SWEEP", "level": bsl}

    # Bullish sweep (took lows then closed back)
    if float(last["low"]) < ssl and float(last["close"]) > ssl:
        return {"sweep": True, "direction": "BULLISH_SWEEP", "level": ssl}

    return {"sweep": False, "direction": "NONE", "level": None}

def calc_cvd_proxy(df, period=20):
    last = df.tail(period)
    buy_vol = float(last[last["close"] > last["open"]]["vol"].sum())
    sell_vol = float(last[last["close"] <= last["open"]]["vol"].sum())
    total = buy_vol + sell_vol
    if total == 0:
        return 0.0
    return (buy_vol - sell_vol) / total * 100

# ====================== EXCHANGE DATA ======================
def kucoin_futures_symbols(limit=300):
    p = api_json("https://api-futures.kucoin.com/api/v1/contracts/active")
    data = (p or {}).get("data", [])
    out = [c.get("symbol") for c in data if c.get("symbol", "").endswith("USDTM")]
    return out[:limit]

def mexc_futures_symbols(limit=300):
    p = api_json("https://contract.mexc.com/api/v1/contract/detail")
    data = (p or {}).get("data", []) if isinstance(p, dict) else []
    out = [c.get("symbol") for c in data if c.get("symbol", "").endswith("_USDT")]
    return out[:limit]

def bybit_futures_symbols(limit=300):
    p = api_json("https://api.bybit.com/v5/market/instruments-info", {"category": "linear", "limit": 1000})
    data = (p or {}).get("result", {}).get("list", [])
    out = [c.get("symbol") for c in data if c.get("symbol", "").endswith("USDT")]
    return out[:limit]

def klines_kucoin(symbol, gran=15, limit=200):
    end = int(time.time() * 1000)
    start = end - limit * gran * 60 * 1000
    p = api_json("https://api-futures.kucoin.com/api/v1/kline/query", {
        "symbol": symbol, "granularity": gran, "from": start, "to": end
    })
    d = (p or {}).get("data", [])
    if len(d) < 40:
        return None
    df = pd.DataFrame(d, columns=["time", "open", "close", "high", "low", "vol", "turnover"])
    for col in ["open", "close", "high", "low", "vol"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna().reset_index(drop=True)

def klines_mexc(symbol, interval="15m", limit=200):
    p = api_json("https://contract.mexc.com/api/v1/contract/kline", {
        "symbol": symbol, "interval": interval, "limit": limit
    })
    d = (p or {}).get("data", [])
    if not d or len(d) < 40:
        return None
    try:
        df = pd.DataFrame(d, columns=["time", "open", "high", "low", "close", "vol"])
        for col in ["open", "high", "low", "close", "vol"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.dropna().reset_index(drop=True)
    except Exception:
        return None

def klines_bybit(symbol, interval="15", limit=200):
    p = api_json("https://api.bybit.com/v5/market/kline", {
        "category": "linear", "symbol": symbol, "interval": interval, "limit": limit
    })
    d = (p or {}).get("result", {}).get("list", [])
    if not d or len(d) < 40:
        return None
    df = pd.DataFrame(d, columns=["time", "open", "high", "low", "close", "vol", "turnover"])
    for col in ["open", "high", "low", "close", "vol"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("time").reset_index(drop=True)

def get_klines(exchange, symbol, timeframe="15m", limit=200):
    if exchange == "KuCoin":
        gran = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}.get(timeframe, 15)
        return klines_kucoin(symbol, gran, limit)
    if exchange == "MEXC":
        return klines_mexc(symbol, timeframe, limit)
    if exchange == "Bybit":
        iv = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}.get(timeframe, "15")
        return klines_bybit(symbol, iv, limit)
    return None

# ====================== CORE ANALYSIS ======================
def analyze_symbol(exchange, symbol, display_name, btc_bias
