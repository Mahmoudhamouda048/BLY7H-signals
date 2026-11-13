import os
import json
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

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
        <div style="font-size:34px;font-weight:900;letter-spacing:3px;line-height:1.1;
            background:linear-gradient(90deg,#FFD700,#FF8C00,#FFD700);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent">
            BLY7TRADER ELITE
        </div>
        <div style="color:#FFD700;font-size:12px;letter-spacing:2px;margin-top:4px">
            STRUCTURE • ORDER BLOCK • FVG • LIQUIDITY • SELF-LEARNING
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

import sqlite3
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

# ====================== STRUCTURE ENGINE ======================
def detect_swings(df, left=2, right=2):
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
    highs, lows = detect_swings(df)
    if len(highs) < 2 or len(lows) < 2:
        return {"bias": "NEUTRAL", "bos": False, "last_high": None, "last_low": None}

    last_high = highs[-1][1]
    prev_high = highs[-2][1]
    last_low = lows[-1][1]
    prev_low = lows[-2][1]

    bias = "NEUTRAL"
    if last_high > prev_high and last_low > prev_low:
        bias = "BULLISH"
    elif last_high < prev_high and last_low < prev_low:
        bias = "BEARISH"

    bos = False
    close = float(df["close"].iloc[-1])
    if bias == "BULLISH" and close > last_high:
        bos = True
    if bias == "BEARISH" and close < last_low:
        bos = True

    return {
        "bias": bias,
        "bos": bos,
        "last_high": last_high,
        "last_low": last_low
    }

def detect_order_blocks(df, lookback=25):
    bullish_obs = []
    bearish_obs = []
    for i in range(5, min(len(df)-2, lookback)):
        atr_val = float(atr(df.iloc[:i+1]).iloc[-1]) if i > 14 else 0
        if atr_val <= 0:
            continue
        # Bullish OB
        if df["close"].iloc[i] < df["open"].iloc[i]:
            move = float(df["close"].iloc[i+1:i+4].max() - df["low"].iloc[i])
            if move > 1.1 * atr_val:
                bullish_obs.append({
                    "top": float(df["high"].iloc[i]),
                    "bottom": float(df["low"].iloc[i]),
                    "mid": (float(df["high"].iloc[i]) + float(df["low"].iloc[i])) / 2
                })
        # Bearish OB
        if df["close"].iloc[i] > df["open"].iloc[i]:
            move = float(df["high"].iloc[i] - df["close"].iloc[i+1:i+4].min())
            if move > 1.1 * atr_val:
                bearish_obs.append({
                    "top": float(df["high"].iloc[i]),
                    "bottom": float(df["low"].iloc[i]),
                    "mid": (float(df["high"].iloc[i]) + float(df["low"].iloc[i])) / 2
                })
    return {
        "bullish": bullish_obs[-2:] if bullish_obs else [],
        "bearish": bearish_obs[-2:] if bearish_obs else []
    }

def detect_fvg(df, lookback=35):
    fvgs = []
    start = max(1, len(df) - lookback)
    for i in range(start, len(df) - 1):
        if df["low"].iloc[i+1] > df["high"].iloc[i-1]:
            top = float(df["low"].iloc[i+1])
            bottom = float(df["high"].iloc[i-1])
            fvgs.append({"type": "BULLISH_FVG", "top": top, "bottom": bottom, "mid": (top + bottom) / 2})
        if df["high"].iloc[i+1] < df["low"].iloc[i-1]:
            top = float(df["low"].iloc[i-1])
            bottom = float(df["high"].iloc[i+1])
            fvgs.append({"type": "BEARISH_FVG", "top": top, "bottom": bottom, "mid": (top + bottom) / 2})
    return fvgs[-4:] if fvgs else []

def detect_liquidity_sweep(df, lookback=22):
    if len(df) < lookback + 3:
        return {"sweep": False, "direction": "NONE", "level": None}
    recent = df.iloc[-lookback-2:-2]
    bsl = float(recent["high"].max())
    ssl = float(recent["low"].min())
    last = df.iloc[-1]
    if float(last["high"]) > bsl and float(last["close"]) < bsl:
        return {"sweep": True, "direction": "BEARISH_SWEEP", "level": bsl}
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
def kucoin_futures_symbols(limit=200):
    p = api_json("https://api-futures.kucoin.com/api/v1/contracts/active")
    data = (p or {}).get("data", [])
    out = [c.get("symbol") for c in data if c.get("symbol", "").endswith("USDTM")]
    return out[:limit]

def mexc_futures_symbols(limit=200):
    p = api_json("https://contract.mexc.com/api/v1/contract/detail")
    data = (p or {}).get("data", []) if isinstance(p, dict) else []
    out = [c.get("symbol") for c in data if c.get("symbol", "").endswith("_USDT")]
    return out[:limit]

def bybit_futures_symbols(limit=200):
    p = api_json("https://api.bybit.com/v5/market/instruments-info", {"category": "linear", "limit": 1000})
    data = (p or {}).get("result", {}).get("list", [])
    out = [c.get("symbol") for c in data if c.get("symbol", "").endswith("USDT")]
    return out[:limit]

def klines_kucoin(symbol, gran=15, limit=150):
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

def klines_mexc(symbol, interval="15m", limit=150):
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

def klines_bybit(symbol, interval="15", limit=150):
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

def get_klines(exchange, symbol, timeframe="15m", limit=150):
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
def analyze_symbol(exchange, symbol, display_name, btc_bias="NEUTRAL", weights=None):
    if weights is None:
        weights = get_active_weights()

    df_1h = get_klines(exchange, symbol, "1h", 120)
    df_15 = get_klines(exchange, symbol, "15m", 100)

    if df_1h is None or len(df_1h) < 50:
        return None

    price = float(df_1h["close"].iloc[-1])
    atr_series = atr(df_1h)
    atr_val = float(atr_series.iloc[-1]) if pd.notna(atr_series.iloc[-1]) else price * 0.01

    structure = detect_market_structure(df_1h)
    obs = detect_order_blocks(df_1h)
    fvgs = detect_fvg(df_1h)
    sweep = detect_liquidity_sweep(df_1h)
    cvd = calc_cvd_proxy(df_1h)
    vol_ratio = float(df_1h["vol"].iloc[-1] / (df_1h["vol"].iloc[-20:-1].mean() + 1e-9))

    e9 = ema(df_1h["close"], 9)
    e21 = ema(df_1h["close"], 21)
    rsi_val = float(rsi(df_1h["close"]).iloc[-1]) if pd.notna(rsi(df_1h["close"]).iloc[-1]) else 50

    mtf_align = False
    if df_15 is not None and len(df_15) > 30:
        e9_15 = ema(df_15["close"], 9)
        e21_15 = ema(df_15["close"], 21)
        if structure["bias"] == "BULLISH" and float(e9_15.iloc[-1]) > float(e21_15.iloc[-1]):
            mtf_align = True
        if structure["bias"] == "BEARISH" and float(e9_15.iloc[-1]) < float(e21_15.iloc[-1]):
            mtf_align = True

    score = 0
    reasons = []
    tools_used = []
    features = {
        "structure_bias": structure["bias"],
        "bos": structure["bos"],
        "sweep": sweep["direction"],
        "cvd": round(cvd, 2),
        "vol_ratio": round(vol_ratio, 2),
        "rsi": round(rsi_val, 1),
        "mtf_align": mtf_align
    }

    if structure["bias"] == "BULLISH":
        score += weights.get("structure", 18)
        reasons.append("Market Structure صاعد (HH + HL)")
        tools_used.append("Market Structure")
        side = "LONG"
    elif structure["bias"] == "BEARISH":
        score += weights.get("structure", 18)
        reasons.append("Market Structure هابط (LH + LL)")
        tools_used.append("Market Structure")
        side = "SHORT"
    else:
        return None

    if structure["bos"]:
        score += 6
        reasons.append("Break of Structure مؤكد")

    valid_ob = None
    if side == "LONG" and obs["bullish"]:
        valid_ob = obs["bullish"][-1]
        score += weights.get("order_block", 16)
        reasons.append(f"Bullish Order Block @ {valid_ob['bottom']:.6g}-{valid_ob['top']:.6g}")
        tools_used.append("Order Block")
    elif side == "SHORT" and obs["bearish"]:
        valid_ob = obs["bearish"][-1]
        score += weights.get("order_block", 16)
        reasons.append(f"Bearish Order Block @ {valid_ob['bottom']:.6g}-{valid_ob['top']:.6g}")
        tools_used.append("Order Block")

    valid_fvg = None
    if side == "LONG":
        bull_fvgs = [f for f in fvgs if f["type"] == "BULLISH_FVG"]
        if bull_fvgs:
            valid_fvg = bull_fvgs[-1]
            score += weights.get("fvg", 14)
            reasons.append(f"Bullish FVG @ {valid_fvg['bottom']:.6g}-{valid_fvg['top']:.6g}")
            tools_used.append("Fair Value Gap")
    else:
        bear_fvgs = [f for f in fvgs if f["type"] == "BEARISH_FVG"]
        if bear_fvgs:
            valid_fvg = bear_fvgs[-1]
            score += weights.get("fvg", 14)
            reasons.append(f"Bearish FVG @ {valid_fvg['bottom']:.6g}-{valid_fvg['top']:.6g}")
            tools_used.append("Fair Value Gap")

    if sweep["sweep"]:
        if (side == "LONG" and sweep["direction"] == "BULLISH_SWEEP") or (side == "SHORT" and sweep["direction"] == "BEARISH_SWEEP"):
            score += weights.get("sweep", 12)
            reasons.append(f"Liquidity Sweep ({sweep['direction']})")
            tools_used.append("Liquidity Sweep")

    if mtf_align:
        score += weights.get("mtf", 10)
        reasons.append("15m يؤكد اتجاه الـ 1H")
        tools_used.append("Multi-Timeframe")

    if vol_ratio >= 1.4:
        score += weights.get("volume", 8)
        reasons.append(f"حجم مرتفع x{vol_ratio:.2f}")
        tools_used.append("Volume Spike")

    if (side == "LONG" and cvd > 15) or (side == "SHORT" and cvd < -15):
        score += weights.get("cvd", 8)
        reasons.append(f"CVD داعم ({cvd:.1f}%)")
        tools_used.append("CVD")

    kz, kz_name = killzone_status()
    if kz:
        score += weights.get("killzone", 6)
        reasons.append(kz_name)
        tools_used.append("Killzone")

    if (side == "LONG" and float(e9.iloc[-1]) > float(e21.iloc[-1])) or (side == "SHORT" and float(e9.iloc[-1]) < float(e21.iloc[-1])):
        score += weights.get("ema_align", 5)
        tools_used.append("EMA 9/21")

    if 40 <= rsi_val <= 65:
        score += weights.get("rsi_filter", 3)

    if btc_bias == "UP" and side == "SHORT":
        score -= 10
        reasons.append("BTC صاعد → SHORT أضعف")
    if btc_bias == "DOWN" and side == "LONG":
        score -= 10
        reasons.append("BTC هابط → LONG أضعف")

    score = int(max(0, min(100, score)))

    if score < 62:
        return None
    if "Market Structure" not in tools_used:
        return None
    if len(tools_used) < 3:
        return None

    # ===== STOP & TARGETS (Structure Based) =====
    buffer = atr_val * 0.15

    if side == "LONG":
        if valid_ob:
            stop = valid_ob["bottom"] - buffer
        elif structure["last_low"]:
            stop = structure["last_low"] - buffer
        else:
            stop = price - 1.4 * atr_val

        risk = price - stop
        if risk <= 0:
            return None

        tp1 = price + risk * 1.2
        tp2 = structure["last_high"] if structure["last_high"] else price + risk * 2.1
        tp3 = price + risk * 3.2

        if valid_fvg and valid_fvg["top"] > price:
            tp1 = min(tp1, valid_fvg["mid"])
    else:
        if valid_ob:
            stop = valid_ob["top"] + buffer
        elif structure["last_high"]:
            stop = structure["last_high"] + buffer
        else:
            stop = price + 1.4 * atr_val

        risk = stop - price
        if risk <= 0:
            return None

        tp1 = price - risk * 1.2
        tp2 = structure["last_low"] if structure["last_low"] else price - risk * 2.1
        tp3 = price - risk * 3.2

        if valid_fvg and valid_fvg["bottom"] < price:
            tp1 = max(tp1, valid_fvg["mid"])

    max_risk_pct = 0.035
    if side == "LONG" and (price - stop) / price > max_risk_pct:
        stop = price * (1 - max_risk_pct)
    if side == "SHORT" and (stop - price) / price > max_risk_pct:
        stop = price * (1 + max_risk_pct)

    rr1 = abs(tp1 - price) / abs(price - stop) if abs(price - stop) > 0 else 0
    rr2 = abs(tp2 - price) / abs(price - stop) if abs(price - stop) > 0 else 0

    return {
        "symbol": display_name,
        "exchange": exchange,
        "type": side,
        "score": score,
        "price": price,
        "entry": price,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rr1": round(rr1, 2),
        "rr2": round(rr2, 2),
        "reasons": reasons,
        "tools_used": list(set(tools_used)),
        "features": features,
        "structure": structure,
        "atr": atr_val,
        "cvd": round(cvd, 1),
        "vol_ratio": round(vol_ratio, 2),
        "rsi": round(rsi_val, 1)
    }

# ====================== TELEGRAM ======================
def send_telegram(message):
    try:
        token = st.secrets.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    except Exception:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    try:
        chat = st.secrets.get("TELEGRAM_CHANNEL_ID", st.secrets.get("TELEGRAM_CHAT_ID", ""))
    except Exception:
        chat = os.getenv("TELEGRAM_CHANNEL_ID", os.getenv("TELEGRAM_CHAT_ID", ""))

    if not token or not chat:
        return False, "حط TELEGRAM_BOT_TOKEN و TELEGRAM_CHANNEL_ID في Secrets"

    try:
        r = SESSION.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": message, "disable_web_page_preview": True},
            timeout=15
        )
        d = r.json()
        if r.ok and d.get("ok"):
            return True, "تم الإرسال"
        return False, d.get("description", "Telegram error")
    except Exception as e:
        return False, str(e)

def format_signal_message(s):
    side_emoji = "🟢 LONG" if s["type"] == "LONG" else "🔴 SHORT"
    tools = " + ".join(s.get("tools_used", []))
    reasons_txt = "\n".join([f"• {r}" for r in s.get("reasons", [])])

    msg = f"""💎 BLY7TRADER ELITE

{side_emoji}  {s['symbol']}
⭐ Score: {s['score']}/100

📥 Entry: {s['entry']:.6g}
🛑 Stop: {s['stop']:.6g}
🎯 TP1: {s['tp1']:.6g}  (R:R 1:{s['rr1']})
🎯 TP2: {s['tp2']:.6g}  (R:R 1:{s['rr2']})
🎯 TP3: {s['tp3']:.6g}

📊 الأدوات المستخدمة:
{tools}

📌 ليه الصفقة دي؟
{reasons_txt}

🛑 ليه الاستوب هنا؟
الاستوب مبني على Order Block أو آخر Swing حقيقي + Buffer بسيط من الـ ATR.

🎯 ليه الأهداف هنا؟
TP1 قريب من أقرب منطقة سيولة/هيكل.
TP2 على مستوى السيولة السابقة.
TP3 Runner حسب امتداد الهيكل.

#BLY7TRADER #ELITE
@WHYNOTBLY7"""
    return msg

# ====================== LEARNING ======================
def auto_update_weights():
    with sqlite3.connect(DB_PATH) as c:
        rows = c.execute("""
            SELECT features, outcome, pnl FROM learning_log
            WHERE outcome IN ('WIN', 'LOSS')
            ORDER BY id DESC LIMIT 300
        """).fetchall()

    if len(rows) < 15:
        return False, "محتاج على الأقل 15 صفقة مقفولة عشان يتعلم"

    wins = sum(1 for r in rows if r[1] == "WIN")
    total = len(rows)
    win_rate = wins / total * 100
    weights = get_active_weights()

    with sqlite3.connect(DB_PATH) as c:
        c.execute("UPDATE model_weights SET is_active=0")
        c.execute("""
            INSERT INTO model_weights (updated_at, weights, win_rate, total_trades, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (
            datetime.now(timezone.utc).isoformat(),
            json.dumps(weights),
            round(win_rate, 2),
            total
        ))
        c.commit()

    return True, f"تم التحديث | Win Rate: {win_rate:.1f}% من {total} صفقة"

# ====================== UI ======================
kz_active, kz_msg = killzone_status()
st.markdown(f"**Killzone:** {'✅ ' + kz_msg if kz_active else '⏸️ ' + kz_msg} | **الوقت:** {now_cairo().strftime('%Y-%m-%d %H:%M')} Cairo")

section = st.radio(
    "الأقسام",
    ["📡 Futures Scanner", "📊 تحليل عملة", "🧠 Self-Learning", "💾 Paper Trading", "📩 Telegram Test"],
    horizontal=True,
    label_visibility="collapsed"
)

if section.startswith("📡"):
    st.subheader("📡 Futures Scanner - High Confluence Only")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        exch = st.selectbox("المنصة", ["KuCoin", "MEXC", "Bybit"])
    with c2:
        n_sym = st.slider("عدد العملات", 30, 200, 100, step=10)
    with c3:
        min_score = st.slider("أقل Score", 60, 85, 68)
    with c4:
        side_filter = st.selectbox("الاتجاه", ["الكل", "LONG فقط", "SHORT فقط"])

    btc_bias = "NEUTRAL"
    btc_df = get_klines("KuCoin", "XBTUSDTM", "1h", 80)
    if btc_df is not None:
        st_struct = detect_market_structure(btc_df)
        btc_bias = "UP" if st_struct["bias"] == "BULLISH" else ("DOWN" if st_struct["bias"] == "BEARISH" else "NEUTRAL")
    st.caption(f"BTC Bias: **{btc_bias}**")

    if st.button("🔍 امسح دلوقتي", type="primary", use_container_width=True):
        with st.spinner(f"جاري المسح على {exch}..."):
            if exch == "KuCoin":
                symbols = kucoin_futures_symbols(n_sym)
            elif exch == "MEXC":
                symbols = mexc_futures_symbols(n_sym)
            else:
                symbols = bybit_futures_symbols(n_sym)

            results = []
            progress = st.progress(0)
            weights = get_active_weights()

            for i, sym in enumerate(symbols):
                progress.progress((i + 1) / max(len(symbols), 1))
                if any(x in sym for x in ["USDC", "DAI", "USDE"]):
                    continue

                display = sym.replace("USDTM", "/USDT").replace("_USDT", "/USDT")
                if exch == "Bybit":
                    display = sym.replace("USDT", "/USDT")

                try:
                    res = analyze_symbol(exch, sym, display, btc_bias, weights)
                    if res and res["score"] >= min_score:
                        if side_filter == "LONG فقط" and res["type"] != "LONG":
                            continue
                        if side_filter == "SHORT فقط" and res["type"] != "SHORT":
                            continue
                        results.append(res)
                        save_signal_to_db(res, exch)
                        log_for_learning(res)
                except Exception:
                    continue

            results = sorted(results, key=lambda x: x["score"], reverse=True)
            st.session_state["elite_results"] = results

            if not results:
                st.warning("مفيش إشارات عالية الجودة دلوقتي.")
            else:
                st.success(f"تم العثور على {len(results)} إشارة عالية الجودة")

    results = st.session_state.get("elite_results", [])
    if results:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("إجمالي الفرص", len(results))
        m2.metric("LONG", sum(1 for x in results if x["type"] == "LONG"))
        m3.metric("SHORT", sum(1 for x in results if x["type"] == "SHORT"))
        m4.metric("أعلى Score", max(x["score"] for x in results))

        df_show = pd.DataFrame([{
            "العملة": r["symbol"],
            "الاتجاه": r["type"],
            "Score": r["score"],
            "الدخول": r["entry"],
            "الاستوب": r["stop"],
            "TP1": r["tp1"],
            "TP2": r["tp2"],
            "R:R": r["rr2"],
            "أدوات": " | ".join(r["tools_used"][:3])
        } for r in results])
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        for r in results[:8]:
            with st.expander(f"{r['symbol']} | {r['type']} | Score {r['score']}"):
                st.markdown(f"""
                **الدخول:** `{r['entry']:.6g}`  
                **الاستوب:** `{r['stop']:.6g}`  
                **TP1:** `{r['tp1']:.6g}` | **TP2:** `{r['tp2']:.6g}` | **TP3:** `{r['tp3']:.6g}`  
                **R:R:** 1:{r['rr1']} / 1:{r['rr2']}
                """)
                st.markdown("**الأدوات:** " + " • ".join(r["tools_used"]))
                st.markdown("**الأسباب:**")
                for reason in r["reasons"]:
                    st.markdown(f"- {reason}")
                st.code(format_signal_message(r), language="text")
                if st.button(f"📩 إرسال {r['symbol']}", key=f"tg_{r['symbol']}_{r['type']}"):
                    ok, msg = send_telegram(format_signal_message(r))
                    st.success(msg) if ok else st.error(msg)

        if st.button("📩 إرسال أقوى 3 إشارات"):
            for r in results[:3]:
                send_telegram(format_signal_message(r))
                time.sleep(0.5)
            st.success("تم إرسال أقوى 3 إشارات")

elif section.startswith("📊"):
    st.subheader("📊 تحليل عملة واحدة")
    exch2 = st.selectbox("المنصة", ["KuCoin", "MEXC", "Bybit"], key="ex2")
    default_sym = "XBTUSDTM" if exch2 == "KuCoin" else ("BTC_USDT" if exch2 == "MEXC" else "BTCUSDT")
    sym_in = st.text_input("الرمز", default_sym).strip().upper()

    if st.button("تحليل"):
        res = analyze_symbol(exch2, sym_in, sym_in)
        if res is None:
            st.warning("مفيش إعداد عالي الجودة حاليًا على العملة دي")
        else:
            st.success(f"Score: {res['score']} | {res['type']}")
            st.json({
                "Entry": res["entry"],
                "Stop": res["stop"],
                "TP1": res["tp1"],
                "TP2": res["tp2"],
                "TP3": res["tp3"],
                "Tools": res["tools_used"],
                "Reasons": res["reasons"]
            })
            st.code(format_signal_message(res), language="text")

elif section.startswith("🧠"):
    st.subheader("🧠 Self-Learning System")
    st.markdown("النظام بيسجل كل إشارة أوتوماتيك. لما تحدد نتيجة الصفقة البوت بيتعلم.")

    with sqlite3.connect(DB_PATH) as c:
        total_logs = c.execute("SELECT COUNT(*) FROM learning_log").fetchone()[0]
        open_signals = c.execute("SELECT COUNT(*) FROM signals WHERE outcome='OPEN'").fetchone()[0]
        closed = c.execute("SELECT COUNT(*) FROM learning_log WHERE outcome IN ('WIN','LOSS')").fetchone()[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("إجمالي السجلات", total_logs)
    c2.metric("إشارات مفتوحة", open_signals)
    c3.metric("صفقات مقفولة", closed)

    st.markdown("### تسجيل نتيجة صفقة")
    with sqlite3.connect(DB_PATH) as c:
        open_rows = c.execute("""
            SELECT id, symbol, side, entry, stop, tp1, created_at
            FROM signals WHERE outcome='OPEN' ORDER BY id DESC LIMIT 30
        """).fetchall()

    if open_rows:
        options = {f"#{r[0]} {r[1]} {r[2]} @ {r[3]}": r[0] for r in open_rows}
        selected = st.selectbox("اختر الإشارة", list(options.keys()))
        outcome = st.selectbox("النتيجة", ["WIN", "LOSS", "BE"])
        pnl = st.number_input("PnL ($)", value=0.0)

        if st.button("تسجيل النتيجة"):
            sig_id = options[selected]
            with sqlite3.connect(DB_PATH) as c:
                c.execute("UPDATE signals SET outcome=?, pnl=? WHERE id=?", (outcome, pnl, sig_id))
                row = c.execute("SELECT symbol, side, score FROM signals WHERE id=?", (sig_id,)).fetchone()
                if row:
                    log_for_learning(
                        {"symbol": row[0], "type": row[1], "score": row[2], "features": {}},
                        outcome=outcome,
                        pnl=pnl
                    )
                c.commit()
            st.success("تم تسجيل النتيجة")
    else:
        st.info("مفيش إشارات مفتوحة حاليًا")

    st.markdown("---")
    if st.button("🔄 تحديث أوزان النموذج", type="primary"):
        ok, msg = auto_update_weights()
        st.success(msg) if ok else st.warning(msg)

    st.markdown("### الأوزان الحالية")
    st.json(get_active_weights())

elif section.startswith("💾"):
    st.subheader("💾 Paper Trading")
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        pt_sym = st.text_input("العملة", "BTC/USDT")
    with pc2:
        pt_side = st.selectbox("الاتجاه", ["LONG", "SHORT"])
    with pc3:
        pt_size = st.number_input("الحجم $", value=100.0)

    pe1, pe2, pe3 = st.columns(3)
    with pe1:
        pt_entry = st.number_input("الدخول", value=0.0, format="%.8f")
    with pe2:
        pt_stop = st.number_input("الاستوب", value=0.0, format="%.8f")
    with pe3:
        pt_tp1 = st.number_input("TP1", value=0.0, format="%.8f")

    if st.button("تسجيل Paper Trade"):
        if pt_entry > 0:
            with sqlite3.connect(DB_PATH) as c:
                c.execute("""
                    INSERT INTO paper_trades
                    (created_at, symbol, side, entry, stop, tp1, tp2, tp3, size_usd)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    pt_sym, pt_side, pt_entry, pt_stop, pt_tp1, pt_tp1, pt_tp1, pt_size
                ))
                c.commit()
            st.success("تم التسجيل")

    with sqlite3.connect(DB_PATH) as c:
        df_pt = pd.read_sql_query("SELECT * FROM paper_trades ORDER BY id DESC LIMIT 20", c)
    if not df_pt.empty:
        st.dataframe(df_pt, use_container_width=True, hide_index=True)

elif section.startswith("📩"):
    st.subheader("📩 اختبار تليجرام")
    if st.button("إرسال رسالة تجريبية"):
        ok, msg = send_telegram("💎 BLY7TRADER ELITE - Test Message ✅\nالبوت شغال.")
        st.success(msg) if ok else st.error(msg)

    st.markdown("""
    **Secrets المطلوبة:**
    ```
    TELEGRAM_BOT_TOKEN = "..."
    TELEGRAM_CHANNEL_ID = "-100..."
    ```
    """)

st.markdown("---")
st.caption("BLY7TRADER ELITE • Structure Based • High Confluence • Self-Learning")
