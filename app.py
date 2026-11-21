# BLY7TRADER —  (Pro UI + Lead Indicators + Pump/Dump Radar)
## ملاحظة: الإشارات تنبيهات بحثية وليست نصيحة مالية.

import os
import json
import time
import sqlite3
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st

try:
    from zoneinfo import ZoneInfo
    CAIRO = ZoneInfo("Africa/Cairo")
except Exception:  # tzdata غير متوفر
    CAIRO = timezone(timedelta(hours=2))

st.set_page_config(
    page_title="BLY7TRADER V24",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_TITLE = "BLY7TRADER"
APP_VERSION = "V24"
DB_PATH = os.getenv("BLY7TRADER_DB", "bly7trader_memory.db")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BLY7TRADER/24.0"})
TIMEOUT = 8
STABLES = {"USDCUSDT", "BUSDUSDT", "DAIUSDT", "FDUSDUSDT", "USDEUSDT", "TUSDUSDT"}

# ============================ Theme / UI helpers ============================

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
.stMarkdown, .stButton button, .stTabs button, label, .stCaption { font-family: 'Cairo', sans-serif; }
.block-container { padding-top: 1.2rem; max-width: 1280px; }
.b7-hero { padding: 18px 22px; border-radius: 16px; margin-bottom: 14px; color: #fff;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #6d28d9 100%); }
.b7-hero h1 { margin: 0; font-size: 1.7rem; font-weight: 800; letter-spacing: .5px; }
.b7-hero p { margin: 4px 0 0 0; opacity: .85; font-size: .95rem; }
.b7-badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .78rem;
  font-weight: 700; margin: 0 3px 3px 0; }
.b7-dec { border: 1.5px solid; border-radius: 16px; padding: 16px 20px; margin: 6px 0 12px 0; }
.b7-dec-top { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; }
.b7-dec-label { font-size: 2rem; font-weight: 800; }
.b7-dec-sub { font-size: .85rem; opacity: .8; }
.b7-dec-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 12px; }
.b7-stat { background: rgba(128,128,128,.10); border-radius: 12px; padding: 8px 12px; }
.b7-stat .k { font-size: .75rem; opacity: .7; }
.b7-stat .v { font-size: 1.25rem; font-weight: 800; }
.b7-gauge { margin: 8px 0 14px 0; }
.b7-g-top { display: flex; justify-content: space-between; font-size: .88rem; font-weight: 600; margin-bottom: 4px; }
.b7-g-track { position: relative; height: 12px; border-radius: 999px; background: rgba(128,128,128,.18); overflow: hidden; }
.b7-g-mid { position: absolute; left: 50%; top: 0; bottom: 0; width: 2px; background: rgba(128,128,128,.55); z-index: 2; }
.b7-g-fill { position: absolute; top: 0; bottom: 0; border-radius: 999px; }
.b7-note { font-size: .78rem; opacity: .65; margin-top: 2px; }
.b7-score { height: 8px; border-radius: 999px; background: rgba(128,128,128,.18); overflow: hidden; margin: 2px 0 8px 0; }
.b7-score > div { height: 100%; border-radius: 999px; }
@media (max-width: 700px) { .b7-dec-grid { grid-template-columns: repeat(2, 1fr); } .b7-dec-label { font-size: 1.5rem; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

TONES = {"up": "#16a34a", "down": "#dc2626", "neutral": "#64748b", "warn": "#d97706", "info": "#2563eb"}


def badge(text, tone="neutral"):
    c = TONES.get(tone, TONES["neutral"])
    return f'<span class="b7-badge" style="background:{c}22;color:{c};border:1px solid {c}55">{text}</span>'


def gauge(label, value, text="", note=""):
    """شريط مؤشر من -1 (أحمر/يسار) إلى +1 (أخضر/يمين)."""
    v = float(max(-1.0, min(1.0, value if value is not None else 0.0)))
    pct = abs(v) * 50
    color = TONES["up"] if v > 0.05 else TONES["down"] if v < -0.05 else TONES["neutral"]
    left = 50 if v >= 0 else 50 - pct
    st.markdown(
        f'<div class="b7-gauge"><div class="b7-g-top"><span>{label}</span>'
        f'<span style="color:{color}">{text}</span></div>'
        f'<div class="b7-g-track"><div class="b7-g-mid"></div>'
        f'<div class="b7-g-fill" style="left:{left}%;width:{pct}%;background:{color}"></div></div>'
        f'<div class="b7-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def score_bar(value, tone="info"):
    c = TONES.get(tone, TONES["info"])
    v = max(0, min(100, float(value)))
    st.markdown(f'<div class="b7-score"><div style="width:{v}%;background:{c}"></div></div>', unsafe_allow_html=True)


def decision_card(label, tone, sub, stats):
    c = TONES.get(tone, TONES["neutral"])
    cells = "".join(f'<div class="b7-stat"><div class="k">{k}</div><div class="v">{v}</div></div>' for k, v in stats)
    st.markdown(
        f'<div class="b7-dec" style="border-color:{c}88;background:{c}14">'
        f'<div class="b7-dec-top"><span class="b7-dec-label" style="color:{c}">{label}</span>'
        f'<span class="b7-dec-sub">{sub}</span></div><div class="b7-dec-grid">{cells}</div></div>',
        unsafe_allow_html=True,
    )


st.markdown(
    f"""
    <div class="b7-hero">
      <h1>💎 {APP_TITLE} <span style="opacity:.7;font-weight:600">{APP_VERSION}</span></h1>
      <p>ماسح عقود Futures + رادار Pump/Dump مبكر + MEXC Up/Down بمؤشرات قائدة + ذاكرة وتعلّم وباكتست</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================ Utilities ============================

def api_json(url, params=None, retries=1, timeout=None):
    """GET JSON مع فحص أكواد الخطأ الشائعة؛ يرجع None عند أي فشل."""
    for attempt in range(retries + 1):
        try:
            response = SESSION.get(url, params=params, timeout=timeout or TIMEOUT)
            if response.status_code == 429:
                time.sleep(1.0)
                continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                if payload.get("code") not in (None, "200000", 200, 0, "0", "00000"):
                    return None
                if payload.get("retCode") not in (None, 0):
                    return None
            return payload
        except (requests.RequestException, ValueError, TypeError):
            if attempt < retries:
                time.sleep(0.4)
    return None


def safe_float(value, default=0.0):
    try:
        result = float(value)
        return result if pd.notna(result) else default
    except (TypeError, ValueError):
        return default


def base_asset(symbol):
    s = str(symbol).upper()
    for suffix in ("USDTM", "_USDT", "-USDT", "USDT"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    return "BTC" if s == "XBT" else s


def clamp_entry(entry, price, is_long):
    if price <= 0:
        return entry
    if abs(entry - price) / price * 100 > 1.5:
        return price * (0.997 if is_long else 1.003)
    return entry


def now_cairo():
    return datetime.now(CAIRO)


def killzone_status():
    current = now_cairo()
    minutes = current.hour * 60 + current.minute
    if 10 * 60 <= minutes <= 12 * 60:
        return True, "نافذة لندن التقريبية"
    if 15 * 60 + 30 <= minutes <= 17 * 60 + 30:
        return True, "نافذة نيويورك التقريبية"
    return False, "خارج النوافذ المحددة"


def show_df(df, **kwargs):
    """يتفادى مشاكل use_container_width في نسخ Streamlit المختلفة."""
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)


def _secret(name, default=""):
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def _parse_dt(text):
    dt = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ============================ Database ============================

SIGNAL_COLUMNS = [
    "id", "created_at", "exchange", "symbol", "side", "score", "price", "entry", "stop",
    "tp1", "tp2", "change_pct", "volume_ratio", "cvd_proxy", "outcome", "tp3", "closed_at",
    "pnl_pct", "result_source", "funding_pct", "oi_change_pct", "market_type", "auto_checked_at",
]
REQUIRED_IMPORT = {"created_at", "exchange", "symbol", "side", "score", "price", "entry", "stop", "tp1", "tp2"}


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
            exchange TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
            score INTEGER NOT NULL, price REAL NOT NULL, entry REAL NOT NULL,
            stop REAL NOT NULL, tp1 REAL NOT NULL, tp2 REAL NOT NULL,
            change_pct REAL NOT NULL, volume_ratio REAL NOT NULL,
            cvd_proxy REAL NOT NULL, outcome TEXT DEFAULT 'OPEN')""")
        existing = {row[1] for row in conn.execute("PRAGMA table_info(signals)")}
        additions = {
            "tp3": "REAL", "closed_at": "TEXT", "pnl_pct": "REAL", "result_source": "TEXT",
            "funding_pct": "REAL", "oi_change_pct": "REAL",
            "market_type": "TEXT DEFAULT 'FUTURES'", "auto_checked_at": "TEXT",
        }
        for name, declaration in additions.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE signals ADD COLUMN {name} {declaration}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_outcome ON signals(outcome)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at)")


def update_trade_outcome(signal_id, outcome):
    if outcome not in ("WIN", "LOSS", "BREAKEVEN", "OPEN"):
        return
    with db() as conn:
        row = conn.execute("SELECT side, entry, stop, tp1 FROM signals WHERE id=?", (signal_id,)).fetchone()
        if not row:
            return
        side, entry, stop, tp1 = row
        if outcome == "WIN":
            pnl = (tp1 - entry) / entry * 100 if side == "LONG" else (entry - tp1) / entry * 100
        elif outcome == "LOSS":
            pnl = (stop - entry) / entry * 100 if side == "LONG" else (entry - stop) / entry * 100
        else:
            pnl = 0.0
        closed = None if outcome == "OPEN" else datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE signals SET outcome=?, closed_at=?, pnl_pct=?, result_source='MANUAL' WHERE id=?",
                     (outcome, closed, pnl, signal_id))


def save_signals(signals, exchange):
    signals = [s for s in signals if not s.get("_weak")]
    if not signals:
        return 0
    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    cutoff = (now - timedelta(minutes=20)).isoformat()
    saved = 0
    with db() as conn:
        for s in signals:
            exists = conn.execute(
                "SELECT 1 FROM signals WHERE exchange=? AND symbol=? AND side=? AND created_at>=? LIMIT 1",
                (exchange, s["symbol"], s["type"], cutoff)).fetchone()
            if exists:
                continue
            conn.execute(
                """INSERT INTO signals (created_at, exchange, symbol, side, score, price, entry, stop, tp1, tp2,
                   change_pct, volume_ratio, cvd_proxy, outcome, tp3, funding_pct, oi_change_pct, market_type)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'OPEN',?,?,?,'FUTURES')""",
                (stamp, exchange, s["symbol"], s["type"], int(s["score"]), s["price"], s["entry"],
                 s["stop"], s["tp1"], s["tp2"], s["ch"], s["vol"], s["buy"], s.get("tp3"),
                 s.get("funding"), s.get("oi_change")))
            saved += 1
    return saved


def load_signal_history(limit=200):
    with db() as conn:
        return pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT ?", conn, params=(limit,))


def import_history(df):
    cols = [c for c in df.columns if c in SIGNAL_COLUMNS and c != "id"]
    if not REQUIRED_IMPORT.issubset(set(cols)):
        return 0, "الملف ناقص أعمدة أساسية: " + ", ".join(sorted(REQUIRED_IMPORT - set(cols)))
    added = 0
    with db() as conn:
        for _, row in df.iterrows():
            dup = conn.execute(
                "SELECT 1 FROM signals WHERE created_at=? AND exchange=? AND symbol=? AND side=? LIMIT 1",
                (row["created_at"], row["exchange"], row["symbol"], row["side"])).fetchone()
            if dup:
                continue
            values = []
            for c in cols:
                v = row[c]
                values.append(None if pd.isna(v) else (v.item() if hasattr(v, "item") else v))
            conn.execute(f"INSERT INTO signals ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", values)
            added += 1
    return added, "OK"


def learning_profile():
    with db() as conn:
        df = pd.read_sql_query(
            "SELECT exchange, side, score, outcome FROM signals WHERE outcome IN ('WIN','LOSS','BREAKEVEN')", conn)
    if df.empty:
        return {"trades": 0, "win_rate": 0.0, "adjustment": 0, "by_side": {}}
    decided = df[df.outcome.isin(["WIN", "LOSS"])]
    win_rate = (decided.outcome == "WIN").mean() * 100 if not decided.empty else 0.0
    by_side = {}
    for side, group in df.groupby("side"):
        d = group[group.outcome.isin(["WIN", "LOSS"])]
        by_side[side] = {"trades": len(group),
                         "win_rate": round((d.outcome == "WIN").mean() * 100, 1) if len(d) else 0.0}
    adjustment = 0
    if len(decided) >= 10:
        adjustment = int(max(-8, min(8, round((win_rate - 50) * min(len(decided) / 30, 1) * 0.16))))
    return {"trades": len(df), "win_rate": round(win_rate, 1), "adjustment": adjustment, "by_side": by_side}


# ============================ Telegram ============================

def send_telegram(message):
    token = _secret("TELEGRAM_BOT_TOKEN")
    chat_id = _secret("TELEGRAM_CHANNEL_ID") or _secret("TELEGRAM_CHAT_ID")
    if not token:
        return False, "أضف TELEGRAM_BOT_TOKEN داخل Streamlit Secrets"
    if not chat_id:
        return False, "أضف TELEGRAM_CHANNEL_ID أو TELEGRAM_CHAT_ID داخل Secrets"
    try:
        response = SESSION.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message[:4000], "disable_web_page_preview": True},
            timeout=15,
        )
        data = response.json()
        if response.ok and data.get("ok"):
            return True, "تم الإرسال"
        return False, data.get("description", f"Telegram HTTP {response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        return False, str(exc)


def format_telegram(signal, exchange=""):
    side = "🚀 LONG" if signal["type"] == "LONG" else "📉 SHORT"
    extra_lines = str(signal.get("extra", "")).split("\n")[:8]
    return (
        f"{side} — {signal['symbol']} ({exchange})\n"
        f"⭐ Score: {signal['score']}/100\n"
        f"💵 السعر: {signal['price']}\n"
        f"🎯 الدخول (Limit): {signal['entry']}\n"
        f"⛔ وقف الخسارة: {signal['stop']}\n"
        f"✅ TP1: {signal['tp1']}\n"
        f"🏆 TP2: {signal['tp2']}\n"
        f"🎯 TP3: {signal.get('tp3', '—')}\n"
        f"📦 حجم التداول: x{signal['vol']}\n"
        f"📊 ضغط الشموع: {signal['buy']}%\n"
        + "\n".join(extra_lines)
        + "\n@WHYNOTBLY7"
    )


def send_signal_batch(signals, exchange, min_score):
    eligible = [s for s in signals if not s.get("_weak") and s["score"] >= min_score]
    eligible = sorted(eligible, key=lambda s: s["score"], reverse=True)[:5]
    sent, errors = 0, []
    for s in eligible:
        ok, message = send_telegram(format_telegram(s, exchange))
        if ok:
            sent += 1
        else:
            errors.append(message)
        time.sleep(0.4)
    return sent, errors, len(eligible)


# ============================ Market data ============================

def aggregate_3m(frame):
    if frame is None or frame.empty:
        return frame
    f = frame.copy()
    t = pd.to_numeric(f["time"], errors="coerce")
    step = 180_000 if t.max() > 1e12 else 180
    f["bucket"] = t // step
    out = f.groupby("bucket", sort=True).agg(
        time=("time", "first"), open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"), vol=("vol", "sum")).reset_index(drop=True)
    return out


def _finish(frame, timeframe):
    for c in ("time", "open", "high", "low", "close", "vol"):
        frame[c] = pd.to_numeric(frame[c], errors="coerce")
    frame = frame.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time")
    frame["vol"] = frame["vol"].fillna(0)
    frame = frame.reset_index(drop=True)
    if timeframe == "3m":
        frame = aggregate_3m(frame)
    return frame if len(frame) >= 30 else None


# ---- KuCoin ----
def get_kucoin_futures_symbols(limit=100):
    payload = api_json("https://api-futures.kucoin.com/api/v1/contracts/active")
    rows = (payload or {}).get("data", []) or []
    rows = [x for x in rows if str(x.get("symbol", "")).endswith("USDTM")
            and x.get("status", "Open") == "Open"]
    rows.sort(key=lambda x: safe_float(x.get("turnoverOf24h")), reverse=True)
    return [x["symbol"] for x in rows[:limit]]


def get_kucoin_futures_klines(symbol, timeframe="1h", limit=500):
    gran = {"1m": 1, "3m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240}.get(timeframe, 60)
    mult = 3 if timeframe == "3m" else 1
    n = min(int(limit) * mult, 500)
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - n * gran * 60_000
    payload = api_json("https://api-futures.kucoin.com/api/v1/kline/query",
                       {"symbol": symbol, "granularity": gran, "from": start_ms, "to": end_ms})
    rows = [r[:6] for r in ((payload or {}).get("data") or []) if isinstance(r, (list, tuple)) and len(r) >= 6]
    if len(rows) < 30:
        return None
    return _finish(pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "vol"]), timeframe)


# ---- Binance ----
def get_binance_futures_symbols(limit=100):
    payload = api_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
    if not isinstance(payload, list):
        return []
    rows = [x for x in payload if x.get("symbol", "").endswith("USDT") and x.get("symbol") not in STABLES]
    rows.sort(key=lambda x: safe_float(x.get("quoteVolume")), reverse=True)
    return [x["symbol"] for x in rows[:limit]]


def get_binance_futures_klines(symbol, timeframe="1h", limit=500):
    payload = api_json("https://fapi.binance.com/fapi/v1/klines",
                       {"symbol": symbol, "interval": timeframe, "limit": min(int(limit), 1000)})
    if not isinstance(payload, list) or len(payload) < 30:
        return None
    frame = pd.DataFrame(payload, columns=["time", "open", "high", "low", "close", "vol",
                                           "ct", "qav", "trades", "tb", "tq", "ignore"])
    return _finish(frame[["time", "open", "high", "low", "close", "vol"]].copy(), "native")


# ---- Bybit ----
def get_bybit_futures_symbols(limit=100):
    payload = api_json("https://api.bybit.com/v5/market/tickers", {"category": "linear"})
    rows = (payload or {}).get("result", {}).get("list", []) or []
    rows = [x for x in rows if x.get("symbol", "").endswith("USDT") and x.get("symbol") not in STABLES]
    rows.sort(key=lambda x: safe_float(x.get("turnover24h")), reverse=True)
    return [x["symbol"] for x in rows[:limit]]


def get_bybit_futures_klines(symbol, timeframe="1h", limit=500):
    interval = {"1m": "1", "3m": "3", "5m": "5", "15m": "15", "1h": "60", "4h": "240"}.get(timeframe, "60")
    payload = api_json("https://api.bybit.com/v5/market/kline",
                       {"category": "linear", "symbol": symbol, "interval": interval,
                        "limit": min(int(limit), 1000)})
    rows = (payload or {}).get("result", {}).get("list", []) or []
    if len(rows) < 30:
        return None
    frame = pd.DataFrame([r[:6] for r in rows], columns=["time", "open", "high", "low", "close", "vol"])
    return _finish(frame, "native")


# ---- MEXC ----
def get_mexc_futures_symbols(limit=100):
    payload = api_json("https://contract.mexc.com/api/v1/contract/ticker")
    rows = (payload or {}).get("data", []) or []
    rows = [x for x in rows if x.get("symbol", "").endswith("_USDT")]
    rows.sort(key=lambda x: safe_float(x.get("amount24")), reverse=True)
    return [x["symbol"] for x in rows[:limit]]


def get_mexc_futures_klines(symbol, timeframe="1h", limit=500):
    gran = {"1m": "Min1", "3m": "Min1", "5m": "Min5", "15m": "Min15", "1h": "Min60", "4h": "Hour4"}.get(timeframe, "Min60")
    seconds = {"1m": 60, "3m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400}.get(timeframe, 3600)
    mult = 3 if timeframe == "3m" else 1
    n = min(int(limit) * mult, 1500)
    end = int(time.time())
    payload = api_json("https://contract.mexc.com/api/v1/contract/kline/" + symbol,
                       {"interval": gran, "start": end - n * seconds, "end": end})
    data = (payload or {}).get("data", {})
    if not isinstance(data, dict) or len(data.get("time", [])) < 30:
        return None
    frame = pd.DataFrame({"time": data["time"], "open": data["open"], "high": data["high"],
                          "low": data["low"], "close": data["close"],
                          "vol": data.get("vol", [0] * len(data["time"]))})
    return _finish(frame, timeframe)


KLINE_SOURCES = {"KUCOIN": get_kucoin_futures_klines, "BINANCE": get_binance_futures_klines,
                 "BYBIT": get_bybit_futures_klines, "MEXC": get_mexc_futures_klines}
SYMBOL_SOURCES = {"KUCOIN": get_kucoin_futures_symbols, "BINANCE": get_binance_futures_symbols,
                  "BYBIT": get_bybit_futures_symbols, "MEXC": get_mexc_futures_symbols}
DEFAULT_TEST_SYMBOL = {"KUCOIN": "XBTUSDTM", "BINANCE": "BTCUSDT", "BYBIT": "BTCUSDT", "MEXC": "BTC_USDT"}


def get_futures_funding_oi(exchange, symbol):
    """يرجع (funding%, oi_change%)؛ None لو غير متاح."""
    try:
        if exchange == "BINANCE":
            fund = api_json("https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol": symbol})
            oi = api_json("https://fapi.binance.com/futures/data/openInterestHist",
                          {"symbol": symbol, "period": "5m", "limit": 12})
            funding = safe_float(fund.get("lastFundingRate")) * 100 if isinstance(fund, dict) and "lastFundingRate" in fund else None
            change = None
            if isinstance(oi, list) and len(oi) > 1:
                first = safe_float(oi[0].get("sumOpenInterestValue"))
                last = safe_float(oi[-1].get("sumOpenInterestValue"))
                change = (last - first) / first * 100 if first > 0 else None
            return funding, change
        if exchange == "BYBIT":
            f = api_json("https://api.bybit.com/v5/market/funding/history", {"category": "linear", "symbol": symbol, "limit": 2})
            o = api_json("https://api.bybit.com/v5/market/open-interest",
                         {"category": "linear", "symbol": symbol, "intervalTime": "5min", "limit": 12})
            fl = (f or {}).get("result", {}).get("list", []) or []
            ol = (o or {}).get("result", {}).get("list", []) or []
            funding = safe_float(fl[0].get("fundingRate")) * 100 if fl else None
            first = safe_float(ol[-1].get("openInterest")) if ol else 0
            last = safe_float(ol[0].get("openInterest")) if ol else 0
            return funding, ((last - first) / first * 100 if first > 0 else None)
        if exchange == "KUCOIN":
            payload = api_json("https://api-futures.kucoin.com/api/v1/funding-rate/" + symbol + "/current")
            data = (payload or {}).get("data") or {}
            return (safe_float(data.get("value")) * 100 if data else None), None
        if exchange == "MEXC":
            payload = api_json("https://contract.mexc.com/api/v1/contract/funding_rate/" + symbol)
            data = (payload or {}).get("data") or {}
            return (safe_float(data.get("fundingRate")) * 100 if data else None), None
    except Exception:
        pass
    return None, None


def get_btc_change():
    """تغير شمعة الساعة لـ BTC؛ Binance ثم Bybit كبديل (Binance بيتحجب أحيانًا من السيرفرات الأمريكية)."""
    payload = api_json("https://fapi.binance.com/fapi/v1/klines", {"symbol": "BTCUSDT", "interval": "1h", "limit": 2})
    if isinstance(payload, list) and len(payload) >= 2:
        prev, cur = safe_float(payload[-2][4]), safe_float(payload[-1][4])
        if prev:
            return (cur - prev) / prev * 100
    payload = api_json("https://api.bybit.com/v5/market/kline",
                       {"category": "linear", "symbol": "BTCUSDT", "interval": "60", "limit": 2})
    rows = (payload or {}).get("result", {}).get("list", []) or []
    if len(rows) >= 2:
        cur, prev = safe_float(rows[0][4]), safe_float(rows[1][4])
        if prev:
            return (cur - prev) / prev * 100
    return None


def get_trades(exchange, symbol, limit=1000):
    """آخر صفقات فعلية: قائمة (ts_ms, qty, is_buy_aggressor) من كل المنصات الأربع."""
    try:
        if exchange == "BINANCE":
            p = api_json("https://fapi.binance.com/fapi/v1/aggTrades",
                         {"symbol": symbol, "limit": min(limit, 1000)}, retries=0)
            if isinstance(p, list):
                return [(safe_float(t.get("T")), safe_float(t.get("q")), not t.get("m")) for t in p]
        elif exchange == "BYBIT":
            p = api_json("https://api.bybit.com/v5/market/recent-trade",
                         {"category": "linear", "symbol": symbol, "limit": min(limit, 1000)}, retries=0)
            rows = ((p or {}).get("result") or {}).get("list") or []
            return [(safe_float(t.get("time")), safe_float(t.get("size")), t.get("side") == "Buy") for t in rows]
        elif exchange == "MEXC":
            p = api_json("https://contract.mexc.com/api/v1/contract/deals/" + symbol, {"limit": 100}, retries=0)
            rows = (p or {}).get("data") or []
            return [(safe_float(t.get("t")), safe_float(t.get("v")), t.get("T") == 1) for t in rows]
        elif exchange == "KUCOIN":
            p = api_json("https://api-futures.kucoin.com/api/v1/trade/history", {"symbol": symbol}, retries=0)
            rows = (p or {}).get("data") or []
            return [(safe_float(t.get("ts")) / 1e6, safe_float(t.get("size")), t.get("side") == "buy") for t in rows]
    except Exception:
        pass
    return []


def get_real_cvd(exchange, symbol, limit=1000):
    """CVD حقيقي % من صفقات المنصة (Taker buy - sell)؛ None لو غير متاح."""
    trades = get_trades(exchange, symbol, limit)
    if len(trades) < 20:
        return None
    buy = sum(q for _, q, b in trades if b)
    sell = sum(q for _, q, b in trades if not b)
    total = buy + sell
    return (buy - sell) / total * 100 if total else None


def get_futures_orderbook(exchange, symbol, limit=20):
    """يرجع (imbalance%, note)."""
    try:
        if exchange == "BINANCE":
            payload = api_json("https://fapi.binance.com/fapi/v1/depth", {"symbol": symbol, "limit": limit})
            if not isinstance(payload, dict):
                return None, ""
            bids, asks = payload.get("bids", []), payload.get("asks", [])
        elif exchange == "BYBIT":
            payload = api_json("https://api.bybit.com/v5/market/orderbook", {"category": "linear", "symbol": symbol, "limit": limit})
            res = (payload or {}).get("result", {}) or {}
            bids, asks = res.get("b", []), res.get("a", [])
        elif exchange == "KUCOIN":
            payload = api_json("https://api-futures.kucoin.com/api/v1/level2/snapshot", {"symbol": symbol})
            d = (payload or {}).get("data", {}) or {}
            bids, asks = d.get("bids", [])[:limit], d.get("asks", [])[:limit]
        elif exchange == "MEXC":
            payload = api_json("https://contract.mexc.com/api/v1/contract/depth/" + symbol, {"limit": limit})
            d = (payload or {}).get("data", {}) or {}
            bids, asks = d.get("bids", [])[:limit], d.get("asks", [])[:limit]
        else:
            return None, ""
        bid_vol = sum(safe_float(x[1]) for x in bids if len(x) >= 2)
        ask_vol = sum(safe_float(x[1]) for x in asks if len(x) >= 2)
        total = bid_vol + ask_vol
        if total <= 0:
            return None, ""
        imb = (bid_vol - ask_vol) / total * 100
        return imb, f"دفتر أوامر Futures: اختلال {imb:+.1f}% (شراء {bid_vol:.1f} / بيع {ask_vol:.1f})"
    except Exception:
        return None, ""


def check_spot_listings(symbol):
    base = base_asset(symbol)
    checks = [
        ("KUCOIN", f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={base}-USDT"),
        ("GATE", f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={base}_USDT"),
        ("BITGET", f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={base}USDT"),
        ("BYBIT", f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={base}USDT"),
        ("BINANCE", f"https://data-api.binance.vision/api/v3/ticker/price?symbol={base}USDT"),
    ]
    available = []
    for name, url in checks:
        try:
            response = SESSION.get(url, timeout=4)
            if not response.ok:
                continue
            data = response.json()
            if name == "KUCOIN":
                valid = data.get("code") == "200000" and bool(data.get("data"))
            elif name == "GATE":
                valid = isinstance(data, list) and len(data) > 0
            elif name == "BITGET":
                valid = data.get("code") == "00000" and bool(data.get("data"))
            elif name == "BYBIT":
                valid = data.get("retCode") == 0 and bool(data.get("result", {}).get("list"))
            else:
                valid = isinstance(data, dict) and "price" in data
            if valid:
                available.append(name)
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            continue
    return len(available), available


# ============================ Indicators ============================

def add_indicators(frame):
    f = frame.copy()
    close = pd.to_numeric(f["close"], errors="coerce")
    high = pd.to_numeric(f["high"], errors="coerce")
    low = pd.to_numeric(f["low"], errors="coerce")
    f["ema9"] = close.ewm(span=9, adjust=False).mean()
    f["ema21"] = close.ewm(span=21, adjust=False).mean()
    delta = close.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    f["rsi"] = (100 - 100 / (1 + rs)).fillna(50)
    ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
    f["macd"] = ema12 - ema26
    f["macd_signal"] = f["macd"].ewm(span=9, adjust=False).mean()
    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    f["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    f["momentum"] = close.pct_change(5) * 100
    return f


def candle_volume_delta_proxy(frame, lookback=20):
    """تقريب CVD من حجم الشموع الخضراء/الحمراء (ليس CVD حقيقي)."""
    recent = frame.tail(lookback)
    green = recent.loc[recent["close"] > recent["open"], "vol"].sum()
    red = recent.loc[recent["close"] < recent["open"], "vol"].sum()
    total = green + red
    return float((green - red) / total * 100) if total else 0.0


def find_recent_fvg(frame, lookback=30):
    bull = bear = None
    start = max(1, len(frame) - lookback)
    for i in range(start, len(frame) - 1):
        prev_high, prev_low = safe_float(frame["high"].iloc[i - 1]), safe_float(frame["low"].iloc[i - 1])
        next_low, next_high = safe_float(frame["low"].iloc[i + 1]), safe_float(frame["high"].iloc[i + 1])
        if next_low > prev_high:
            bull = (prev_high, next_low, (prev_high + next_low) / 2)
        if next_high < prev_low:
            bear = (next_high, prev_low, (next_high + prev_low) / 2)
    return bull, bear


def market_structure(frame, lookback=20):
    """BSL/SSL من نطاق سابق + اكتشاف Sweep (اختراق ثم إغلاق داخل النطاق) + OB تقريبي."""
    ref = frame.iloc[-(lookback + 3):-3] if len(frame) > lookback + 3 else frame.iloc[:-3]
    bsl, ssl = safe_float(ref["high"].max()), safe_float(ref["low"].min())
    last2 = frame.tail(2)
    last_close = safe_float(frame["close"].iloc[-1])
    bsl_sweep = safe_float(last2["high"].max()) > bsl > last_close
    ssl_sweep = safe_float(last2["low"].min()) < ssl < last_close
    bull_ob = bear_ob = None
    if len(frame) >= 4:
        c = frame.iloc[-3]
        if safe_float(c["close"]) > safe_float(c["open"]):
            bull_ob = (safe_float(c["low"]), safe_float(c["high"]))
        elif safe_float(c["close"]) < safe_float(c["open"]):
            bear_ob = (safe_float(c["low"]), safe_float(c["high"]))
    return {"bsl": bsl, "ssl": ssl, "bsl_sweep": bool(bsl_sweep), "ssl_sweep": bool(ssl_sweep),
            "bull_ob": bull_ob, "bear_ob": bear_ob}


def candle_trap_note(frame, side, cvd_proxy):
    c = frame.iloc[-1]
    high, low, o, cl = (safe_float(c[k]) for k in ("high", "low", "open", "close"))
    body = abs(cl - o)
    upper, lower = high - max(o, cl), min(o, cl) - low
    if side == "SHORT" and body > 0 and upper > body * 1.5:
        return "ذيل علوي طويل؛ احتمال رفض سعري"
    if side == "LONG" and body > 0 and lower > body * 1.5:
        return "ذيل سفلي طويل؛ احتمال رفض سعري"
    return f"ضغط الشموع التقريبي: {cvd_proxy:+.1f}%"


def build_levels(side, last, atr, fvg):
    """الدخول Limit قرب السعر (FVG لو متاح). الوقف والأهداف تُحسب من الدخول دائمًا."""
    if side == "LONG":
        raw = fvg[2] if fvg else last * 0.997
        entry = min(clamp_entry(raw, last, True), last)
        sign = 1
    else:
        raw = fvg[2] if fvg else last * 1.003
        entry = max(clamp_entry(raw, last, False), last)
        sign = -1
    risk = max(atr * 1.5, entry * 0.006)
    stop = entry - sign * risk
    tps = [entry + sign * risk * m for m in (1.5, 2.5, 3.5)]
    return entry, stop, tps, risk


def position_sizing(entry, stop, settings):
    dist = abs(entry - stop)
    risk_cash = settings.get("capital_usdt", 100.0) * settings.get("risk_pct", 1.0) / 100
    cost_pct = settings.get("fee_pct", 0.10) + settings.get("slippage_pct", 0.05)
    eff = dist + entry * cost_pct / 100
    qty = risk_cash / eff if eff > 0 else 0
    return qty, qty * entry, risk_cash, cost_pct


# ============================ Analysis ============================

def analyze(frame, symbol, settings, exchange="BINANCE", learning_obj=None, btc_cached=None, offline=False):
    """مرحلة 1: تحليل الشموع فقط. مرحلة 2 (لو مش offline): بيانات المنصة للمرشحين فقط."""
    try:
        if frame is None or len(frame) < 30:
            return None, "بيانات شموع غير كافية"
        frame = add_indicators(frame)
        last = safe_float(frame["close"].iloc[-1])
        previous = safe_float(frame["close"].iloc[-2])
        if last <= 0 or previous <= 0:
            return None, "سعر غير صالح"
        change = (last - previous) / previous * 100

        avg_vol = safe_float(frame["vol"].iloc[-22:-2].mean())
        vol_closed = safe_float(frame["vol"].iloc[-2])
        volume_ratio = vol_closed / avg_vol if avg_vol > 0 else 0.0

        cvd_proxy = candle_volume_delta_proxy(frame)
        ema_bull = safe_float(frame["ema9"].iloc[-1]) > safe_float(frame["ema21"].iloc[-1])
        macd_bull = safe_float(frame["macd"].iloc[-1]) > safe_float(frame["macd_signal"].iloc[-1])
        rsi = safe_float(frame["rsi"].iloc[-1], 50)
        atr = safe_float(frame["atr"].iloc[-1])
        momentum = safe_float(frame["momentum"].iloc[-1])
        if atr <= 0:
            atr = last * 0.004

        # اتجاه بالتصويت بدل CVD لوحده
        vote = (2 if cvd_proxy > 0 else -2 if cvd_proxy < 0 else 0)
        vote += 1 if ema_bull else -1
        vote += 1 if macd_bull else -1
        vote += 1 if momentum > 0 else -1 if momentum < 0 else 0
        side = "LONG" if vote > 0 else "SHORT" if vote < 0 else ("LONG" if cvd_proxy >= 0 else "SHORT")
        if side == "LONG" and not settings.get("want_long", True):
            return None, "LONG غير مفعّل"
        if side == "SHORT" and not settings.get("want_short", True):
            return None, "SHORT غير مفعّل"

        bull_fvg, bear_fvg = find_recent_fvg(frame)
        fvg = bull_fvg if side == "LONG" else bear_fvg
        structure = market_structure(frame)
        in_kz, kz_label = killzone_status()
        use_kz = bool(settings.get("killzone")) and not offline and in_kz

        penalty = 0
        if abs(change) > 8:
            penalty -= 20
        if settings.get("use_fvg") and not fvg:
            penalty -= 8
        if side == "LONG" and rsi > 75:
            penalty -= 6
        if side == "SHORT" and rsi < 25:
            penalty -= 6

        score = 35.0
        score += min(max(volume_ratio, 0) * 3, 15)
        agree = (cvd_proxy > 0) == (side == "LONG")
        score += min(abs(cvd_proxy) * 0.15, 12) if agree else 0
        score += min(abs(vote) * 2, 10)
        score += 4 if ((side == "LONG" and 45 <= rsi <= 68) or (side == "SHORT" and 32 <= rsi <= 55)) else 0
        score += 8 if fvg else 0
        score += 5 if use_kz else 0
        score += 5 if ((side == "LONG" and structure["ssl_sweep"]) or (side == "SHORT" and structure["bsl_sweep"])) else 0

        notes = []
        mtf_note = "MTF غير مفعل"
        real_cvd = funding = oi_change = book_imb = None
        book_note = ""

        # ---------- مرحلة 2: بيانات المنصة للمرشحين فقط ----------
        if not offline:
            if settings.get("mtf_filter"):
                higher_tf = "1h" if settings.get("timeframe") != "1h" else "4h"
                higher = KLINE_SOURCES[exchange](symbol, higher_tf, 120)
                if higher is None or len(higher) < 30:
                    mtf_note = "MTF غير متاح"
                else:
                    higher = add_indicators(higher)
                    h_bull = safe_float(higher["ema9"].iloc[-1]) > safe_float(higher["ema21"].iloc[-1])
                    aligned = h_bull if side == "LONG" else not h_bull
                    mtf_note = f"MTF مؤكد على {higher_tf}" if aligned else f"MTF عكس {side} (-10)"
                    if not aligned:
                        penalty -= 10
            btc_change = btc_cached if settings.get("btc_filter") else None
            if btc_change is not None:
                if side == "LONG" and btc_change < -2:
                    penalty -= 10
                if side == "SHORT" and btc_change > 2:
                    penalty -= 10

            pre = score + penalty
            if pre >= max(settings.get("min_score", 0) - 12, 35):
                real_cvd = get_real_cvd(exchange, symbol)
                if real_cvd is not None and abs(real_cvd) >= 3:
                    score += 5 if (real_cvd > 0) == (side == "LONG") else -5
                funding, oi_change = get_futures_funding_oi(exchange, symbol)
                if settings.get("funding_filter") and funding is not None:
                    if (side == "LONG" and funding > 0.05) or (side == "SHORT" and funding < -0.05):
                        penalty -= 8
                if oi_change is not None and oi_change > 1:
                    score += 3
                if settings.get("wall_filter"):
                    book_imb, book_note = get_futures_orderbook(exchange, symbol)
                    if book_imb is not None and ((side == "LONG" and book_imb > 8) or (side == "SHORT" and book_imb < -8)):
                        score += 5

        learning = learning_obj if learning_obj is not None else learning_profile()
        score = max(5, min(int(score) + learning.get("adjustment", 0) + penalty, 98))

        entry, stop, (tp1, tp2, tp3), _risk = build_levels(side, last, atr, fvg)
        qty, notional, risk_cash, cost_pct = position_sizing(entry, stop, settings)
        stop_dist = abs(entry - stop)
        rr1 = abs(tp1 - entry) / max(stop_dist, 1e-12)

        notes.append(f"📊 CVD: {(real_cvd if real_cvd is not None else cvd_proxy):+.1f}% "
                     f"({'تدفق صفقات حقيقي' if real_cvd is not None else 'Proxy من اتجاه الشموع'})")
        notes.append(f"🗳️ تصويت الاتجاه: {vote:+d} (CVD/EMA/MACD/Momentum)")
        notes.append(f"📦 حجم آخر شمعة مغلقة: x{volume_ratio:.2f} من متوسط 20 شمعة")
        notes.append(f"⏰ {kz_label}" if settings.get("killzone") else "⏰ فلتر الوقت متوقف")
        notes.append(f"🐋 {candle_trap_note(frame, side, cvd_proxy)}")
        notes.append(f"🧭 {mtf_note}")
        notes.append(f"📐 EMA9/21: {'صاعد' if ema_bull else 'هابط'} | RSI14: {rsi:.1f} | MACD: {'إيجابي' if macd_bull else 'سلبي'}")
        notes.append(f"⚡ ATR14: {atr:.8g} | Momentum(5): {momentum:+.2f}%")
        sweep = "BSL" if structure["bsl_sweep"] else ("SSL" if structure["ssl_sweep"] else "لا يوجد")
        notes.append(f"💧 BSL: {structure['bsl']:.8g} | SSL: {structure['ssl']:.8g} | Sweep: {sweep}")
        ob = structure["bull_ob"] if side == "LONG" else structure["bear_ob"]
        notes.append(f"🧱 OB تقريبي: {ob[0]:.8g}–{ob[1]:.8g}" if ob else "🧱 لا يوجد OB واضح")
        if fvg:
            notes.append(f"FVG: {fvg[0]:.8g} إلى {fvg[1]:.8g}؛ المنتصف {fvg[2]:.8g}")
        if book_imb is not None:
            notes.append(f"📚 {book_note}")
        if not offline:
            notes.append(f"💸 Funding: {funding:+.4f}%" if funding is not None else "💸 Funding: غير متاح")
            notes.append(f"📈 OI: {oi_change:+.2f}%" if oi_change is not None else "📈 OI: غير متاح من الواجهة العامة")
            if settings.get("confirm_exchanges") and score >= settings.get("min_score", 0):
                count, names = check_spot_listings(symbol)
                notes.append(f"🌐 متاح Spot على {count}/5: {', '.join(names)}")
                if count >= 3:
                    score = min(score + 3, 98)
        notes.append("🧨 Liquidations: لا توجد بيانات موحدة موثوقة؛ لم يتم اختلاق خريطة تصفيات.")
        notes.append(f"🎯 مسافة الوقف: {stop_dist / entry * 100:.2f}% | R:R لـ TP1 = {rr1:.2f}")
        notes.append(f"📏 حجم المركز النظري: {qty:.6g} وحدة | {notional:.2f} USDT | مخاطرة {risk_cash:.2f} USDT | تكلفة {cost_pct:.2f}%")
        notes.append("⚠️ الدخول أمر Limit؛ لو السعر ما رجعش للدخول تتجاهل الصفقة. أعد الحساب عند التنفيذ.")

        weak = score < settings.get("min_score", 0)
        result = {
            "symbol": symbol, "type": side, "score": score, "price": round(last, 8),
            "ch": round(change, 2), "vol": round(volume_ratio, 2), "buy": round(cvd_proxy, 1),
            "entry": round(entry, 8), "stop": round(stop, 8), "tp1": round(tp1, 8),
            "tp2": round(tp2, 8), "tp3": round(tp3, 8), "funding": funding, "oi_change": oi_change,
            "real_cvd": real_cvd, "rr_tp1": round(rr1, 2), "position_qty": round(qty, 8),
            "position_notional": round(notional, 2), "extra": "\n".join(notes),
        }
        if weak:
            result["_weak"] = True
            result["extra"] = f"إشارة ضعيفة - السكور {score} أقل من المطلوب {settings.get('min_score')}\n" + result["extra"]
            return result, f"السكور {score} أقل من المطلوب {settings.get('min_score')}"
        return result, "OK"
    except Exception as exc:
        return None, f"خطأ تحليل: {exc}"


# ============================ Scanner ============================

def run_scan(platform, settings, limit_coins, timeframe, bars_limit):
    local = dict(settings)
    symbols = SYMBOL_SOURCES[platform](limit_coins)
    if not symbols:
        return {"error": f"تعذر جلب قائمة الرموز من {platform} (قد تكون المنصة محجوبة من سيرفرك).",
                "signals": [], "weak": [], "debug": [], "symbols": 0}
    learning_obj = learning_profile()
    btc_cached = get_btc_change() if local.get("btc_filter") else None
    source = KLINE_SOURCES[platform]

    def scan_one(sym):
        try:
            fr = source(sym, timeframe, bars_limit)
            if fr is None:
                return None, {"العملة": sym, "السبب": "تعذر جلب الشموع"}
            sig, reason = analyze(fr, sym, local, platform, learning_obj=learning_obj, btc_cached=btc_cached)
            if sig:
                return sig, None
            return None, {"العملة": sym, "السبب": reason}
        except Exception as exc:
            return None, {"العملة": sym, "السبب": f"خطأ: {exc}"}

    signals, weak, debug = [], [], []
    progress, status = st.progress(0), st.empty()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(scan_one, s): s for s in symbols}
        for done, fut in enumerate(as_completed(futures), start=1):
            progress.progress(done / len(symbols))
            status.caption(f"يفحص {futures[fut]} ({done}/{len(symbols)})")
            sig, dbg = fut.result()
            if sig and sig.get("_weak"):
                weak.append(sig)
            elif sig:
                signals.append(sig)
            elif dbg:
                debug.append(dbg)
    progress.empty()
    status.empty()
    signals.sort(key=lambda s: s["score"], reverse=True)
    weak.sort(key=lambda s: s["score"], reverse=True)
    return {"signals": signals, "weak": weak, "debug": debug, "symbols": len(symbols), "error": None,
            "platform": platform, "ts": now_cairo().strftime("%H:%M:%S"), "tf": timeframe}


def render_signal_card(signal, key, platform):
    is_long = signal["type"] == "LONG"
    tone = "up" if is_long else "down"
    with st.container(border=True):
        left, right = st.columns([4, 1])
        with left:
            st.markdown(f"### {'🚀' if is_long else '📉'} {signal['symbol']} "
                        + badge(signal["type"], tone)
                        + badge("CVD حقيقي" if signal.get("real_cvd") is not None else "CVD Proxy",
                                "info" if signal.get("real_cvd") is not None else "neutral"),
                        unsafe_allow_html=True)
            st.write(f"السعر: **{signal['price']}** | تغير آخر شمعة: **{signal['ch']}%** | "
                     f"Volume: **x{signal['vol']}** | ضغط الشموع: **{signal['buy']}%**")
        with right:
            st.metric("Score", f"{signal['score']}/100")
        score_bar(signal["score"], tone)
        a, b, c, d, e = st.columns(5)
        a.metric("الدخول (Limit)", signal["entry"])
        b.metric("وقف الخسارة", signal["stop"])
        c.metric("TP1", signal["tp1"])
        d.metric("TP2", signal["tp2"])
        e.metric("TP3", signal["tp3"])
        st.caption(f"R:R إلى TP1 = {signal['rr_tp1']} | حجم المركز النظري = {signal['position_qty']}")
        with st.expander("تفاصيل التحليل"):
            st.text(signal["extra"])
        if st.button("📡 أرسل هذه الإشارة إلى Telegram", key=f"tg_{key}"):
            ok, msg = send_telegram(format_telegram(signal, platform))
            st.success(msg) if ok else st.error(msg)


def render_scan_results(state_key, min_score, show_closest):
    res = st.session_state.get(state_key)
    if not res:
        return
    if res.get("error"):
        st.error(res["error"])
        return
    st.caption(f"آخر فحص: {res['ts']} | {res['platform']} | TF {res['tf']} | رموز مفحوصة: {res['symbols']}")
    signals, weak = res["signals"], res["weak"]
    shown, is_weak = signals, False
    if not signals and weak and show_closest:
        shown, is_weak = weak[:10], True
        st.warning(f"⚠️ مفيش إشارة عدّت فلتر السكور ({min_score})، فعرضتلك أقرب {len(shown)} إشارة. دي مش إشارات دخول قوية.")
    if shown:
        if not is_weak:
            st.success(f"تم العثور على {len(shown)} إشارة مطابقة.")
        for i, s in enumerate(shown):
            render_signal_card(s, f"{state_key}_{i}_{s['symbol']}", res["platform"])
    else:
        st.warning("لم تظهر إشارات مطابقة للفلاتر الحالية.")
    if res["debug"]:
        with st.expander(f"أسباب استبعاد بعض العملات ({len(res['debug'])})"):
            show_df(pd.DataFrame(res["debug"][:50]))


# ============================ Auto monitor ============================

def auto_monitor_open_trades(limit=150):
    """
    يحسم الصفقات المفتوحة من الشموع اللاحقة.
    1) لازم الدخول (Limit) يتلمس الأول، ولو ما اتلمسش خلال 12 ساعة -> EXPIRED.
    2) في شمعة التفعيل نفسها بنفحص الوقف فقط (تحفظًا).
    3) لو الوقف والهدف في نفس الشمعة، الوقف يكسب.
    4) الربح عند TP1 (والتسمية بأعلى هدف اتلمس) — لو معدّى 72 ساعة بدون حسم -> EXPIRED.
    """
    with db() as conn:
        rows = conn.execute(
            "SELECT id,created_at,exchange,symbol,side,entry,stop,tp1,tp2,tp3 "
            "FROM signals WHERE outcome='OPEN' ORDER BY id ASC LIMIT ?", (limit,)).fetchall()
    if not rows:
        return {"checked": 0, "resolved": []}
    now = datetime.now(timezone.utc)
    prepared, jobs = [], set()
    for row in rows:
        try:
            created = _parse_dt(row[1])
        except Exception:
            continue
        age_h = (now - created).total_seconds() / 3600
        tf = "1m" if age_h <= 7.5 else "1h"
        if row[2] in KLINE_SOURCES:
            prepared.append((row, created.timestamp(), age_h, tf))
            jobs.add((row[2], row[3], tf))

    def fetch(key):
        try:
            return key, KLINE_SOURCES[key[0]](key[1], key[2], 500)
        except Exception:
            return key, None

    frames = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for key, fr in ex.map(fetch, list(jobs)):
            frames[key] = fr

    resolved, updates, touched = [], [], []
    for row, created_ts, age_h, tf in prepared:
        sid, _, exchange, symbol, side, entry, stop, tp1, tp2, tp3 = row
        frame = frames.get((exchange, symbol, tf))
        if frame is None or frame.empty:
            continue
        touched.append(sid)
        t = pd.to_numeric(frame["time"], errors="coerce").to_numpy(dtype=float)
        t = np.where(t > 1e12, t / 1000, t)
        hi = frame["high"].to_numpy(dtype=float)
        lo = frame["low"].to_numpy(dtype=float)
        is_long = side == "LONG"
        filled, result = False, None
        for k in range(len(t)):
            if t[k] <= created_ts:
                continue
            if not filled:
                if (is_long and lo[k] <= entry) or ((not is_long) and hi[k] >= entry):
                    filled = True
                    if (is_long and lo[k] <= stop) or ((not is_long) and hi[k] >= stop):
                        result = ("LOSS", "AUTO_SL", stop, t[k])
                        break
                continue
            hit_stop = lo[k] <= stop if is_long else hi[k] >= stop
            hit = [(n, p) for n, p in (("TP3", tp3), ("TP2", tp2), ("TP1", tp1))
                   if p and (hi[k] >= p if is_long else lo[k] <= p)]
            if hit_stop:
                result = ("LOSS", "AUTO_SL", stop, t[k])
                break
            if hit:
                result = ("WIN", "AUTO_" + hit[0][0], tp1, t[k])
                break
        if result:
            outcome, label, exit_price, ts = result
            pnl = (exit_price - entry) / entry * 100 if is_long else (entry - exit_price) / entry * 100
            closed = datetime.fromtimestamp(ts, timezone.utc).isoformat()
            updates.append((outcome, closed, pnl, label, sid))
            resolved.append({"id": sid, "symbol": symbol, "result": label, "pnl_%": round(pnl, 3)})
        elif (not filled and age_h > 12) or (filled and age_h > 72):
            label = "AUTO_NOFILL" if not filled else "AUTO_TIMEOUT"
            updates.append(("EXPIRED", now.isoformat(), 0.0, label, sid))
            resolved.append({"id": sid, "symbol": symbol, "result": label, "pnl_%": 0.0})
    with db() as conn:
        stamp = now.isoformat()
        for outcome, closed, pnl, label, sid in updates:
            conn.execute("UPDATE signals SET outcome=?,closed_at=?,pnl_pct=?,result_source=?,auto_checked_at=? "
                         "WHERE id=? AND outcome='OPEN'", (outcome, closed, pnl, label, stamp, sid))
        for sid in touched:
            conn.execute("UPDATE signals SET auto_checked_at=? WHERE id=? AND outcome='OPEN'", (stamp, sid))
    return {"checked": len(touched), "resolved": resolved}


def get_monitor_status(force=False):
    last = st.session_state.get("_mon_ts", 0)
    if not force and "_mon_res" in st.session_state and time.time() - last < 55:
        return st.session_state["_mon_res"]
    try:
        res = auto_monitor_open_trades()
    except Exception as exc:
        res = {"checked": 0, "resolved": [], "error": str(exc)}
    st.session_state["_mon_ts"], st.session_state["_mon_res"] = time.time(), res
    return res


# ============================ DEX scanner ============================

def scan_dex(min_vol5=5000.0, min_chg5=5.0, min_liq=15000.0):
    """أزواج BSC من DexScreener: بحث + Boosts + Profiles. يرجع (مطابق, أقرب)."""
    pairs, addresses = [], []
    for q in ("WBNB", "BNB", "USDT", "CAKE", "BSC"):
        payload = api_json("https://api.dexscreener.com/latest/dex/search", {"q": q})
        pairs += (payload or {}).get("pairs", []) or []
    for url in ("https://api.dexscreener.com/token-boosts/top/v1",
                "https://api.dexscreener.com/token-boosts/latest/v1",
                "https://api.dexscreener.com/token-profiles/latest/v1"):
        data = api_json(url)
        if isinstance(data, list):
            addresses += [x.get("tokenAddress") for x in data if x.get("chainId") == "bsc" and x.get("tokenAddress")]
    addresses = list(dict.fromkeys(addresses))
    for i in range(0, len(addresses), 30):
        chunk = ",".join(addresses[i:i + 30])
        data = api_json(f"https://api.dexscreener.com/tokens/v1/bsc/{chunk}")
        if isinstance(data, list):
            pairs += data
    best = {}
    for pair in pairs:
        if pair.get("chainId") != "bsc":
            continue
        token = pair.get("baseToken") or {}
        addr = (token.get("address") or "").lower()
        if not addr:
            continue
        liq = safe_float((pair.get("liquidity") or {}).get("usd"))
        if addr not in best or liq > best[addr][1]:
            best[addr] = (pair, liq)
    rows = []
    for pair, liq in best.values():
        token = pair.get("baseToken") or {}
        price = safe_float(pair.get("priceUsd"))
        vol5 = safe_float((pair.get("volume") or {}).get("m5"))
        chg5 = safe_float((pair.get("priceChange") or {}).get("m5"))
        chg1h = safe_float((pair.get("priceChange") or {}).get("h1"))
        tx5 = (pair.get("txns") or {}).get("m5") or {}
        buys, sells = safe_float(tx5.get("buys")), safe_float(tx5.get("sells"))
        created = safe_float(pair.get("pairCreatedAt"))
        age_h = (time.time() * 1000 - created) / 3_600_000 if created else None
        if price <= 0:
            continue
        rows.append({"symbol": token.get("symbol", "UNKNOWN"), "address": token.get("address", ""),
                     "price": price, "change_5m": chg5, "change_1h": chg1h, "volume_5m": vol5,
                     "liquidity": liq, "buys": buys, "sells": sells, "age_h": age_h,
                     "fdv": safe_float(pair.get("fdv")), "url": pair.get("url", "")})
    passed = [r for r in rows if r["volume_5m"] >= min_vol5 and r["change_5m"] >= min_chg5 and r["liquidity"] >= min_liq]
    passed.sort(key=lambda r: r["volume_5m"], reverse=True)
    near = [r for r in rows if r["liquidity"] >= min_liq and r not in passed]
    near.sort(key=lambda r: r["change_5m"] * min(r["volume_5m"], 50000), reverse=True)
    return passed, near[:10]


def render_dex_item(item, key):
    with st.container(border=True):
        st.markdown(f"### 🚀 {item['symbol']}")
        age = f"{item['age_h']:.1f} ساعة" if item["age_h"] is not None else "—"
        st.write(f"السعر: ${item['price']:.10g} | 5 دقائق: {item['change_5m']:.2f}% | ساعة: {item['change_1h']:.2f}% | "
                 f"حجم 5د: ${item['volume_5m']:,.0f} | السيولة: ${item['liquidity']:,.0f}")
        st.caption(f"شراء/بيع (5د): {item['buys']:.0f}/{item['sells']:.0f} | عمر الزوج: {age} | FDV: ${item['fdv']:,.0f}")
        if item["liquidity"] < 30000 or (item["age_h"] is not None and item["age_h"] < 24):
            st.caption("⚠️ سيولة ضعيفة أو زوج جديد: مخاطر Rug Pull/Honeypot عالية — افحص العقد قبل أي شيء.")
        if item["url"]:
            st.markdown(f"[فتح الزوج على DexScreener]({item['url']})")
        if st.button("📡 أرسل إلى Telegram", key=f"dex_tg_{key}"):
            ok, msg = send_telegram(
                f"🚀 DEX {item['symbol']} على BSC\nالسعر: ${item['price']:.10g}\n5m: {item['change_5m']:.2f}%\n"
                f"حجم 5m: ${item['volume_5m']:,.0f}\nالسيولة: ${item['liquidity']:,.0f}\n{item['url']}\n@WHYNOTBLY7")
            st.success(msg) if ok else st.error(msg)


# ============================ Backtest ============================

def simulate_trade(frame, start, sig, target_idx, max_hold, fill_wait, cost_pct):
    side, entry, stop = sig["type"], sig["entry"], sig["stop"]
    target = [sig["tp1"], sig["tp2"], sig["tp3"]][target_idx]
    risk = abs(entry - stop)
    if risk <= 0:
        return {"outcome": "SKIP", "r": 0.0, "end": start}
    cost_r = cost_pct / 100 * entry / risk
    is_long = side == "LONG"
    hi, lo, cl = frame["high"].to_numpy(float), frame["low"].to_numpy(float), frame["close"].to_numpy(float)
    n = len(frame)
    filled = False
    end = min(n, start + fill_wait + max_hold)
    for j in range(start, end):
        if not filled:
            if j >= start + fill_wait:
                return {"outcome": "NOFILL", "r": 0.0, "end": j}
            if (is_long and lo[j] <= entry) or ((not is_long) and hi[j] >= entry):
                filled = True
                if (is_long and lo[j] <= stop) or ((not is_long) and hi[j] >= stop):
                    return {"outcome": "LOSS", "r": -1 - cost_r, "end": j}
            continue
        if (is_long and lo[j] <= stop) or ((not is_long) and hi[j] >= stop):
            return {"outcome": "LOSS", "r": -1 - cost_r, "end": j}
        if (is_long and hi[j] >= target) or ((not is_long) and lo[j] <= target):
            return {"outcome": "WIN", "r": abs(target - entry) / risk - cost_r, "end": j}
    if filled:
        j = end - 1
        r = ((cl[j] - entry) if is_long else (entry - cl[j])) / risk - cost_r
        return {"outcome": "TIMEOUT", "r": r, "end": j}
    return {"outcome": "NOFILL", "r": 0.0, "end": end - 1}


def run_backtest(frame, settings, target_idx=0, max_hold=48, fill_wait=6, warmup=60):
    bt_settings = dict(settings)
    bt_settings.update({"mtf_filter": False, "btc_filter": False, "funding_filter": False,
                        "wall_filter": False, "killzone": False, "confirm_exchanges": False})
    cost_pct = settings.get("fee_pct", 0.10) + settings.get("slippage_pct", 0.05)
    trades, i, n = [], warmup, len(frame)
    while i < n - 2:
        window = frame.iloc[max(0, i - 299): i + 1]
        sig, _ = analyze(window, "BT", bt_settings, offline=True, learning_obj={"adjustment": 0})
        if not sig or sig.get("_weak"):
            i += 1
            continue
        res = simulate_trade(frame, i + 1, sig, target_idx, max_hold, fill_wait, cost_pct)
        trades.append({"bar": i, "side": sig["type"], "score": sig["score"], "entry": sig["entry"],
                       "stop": sig["stop"], "outcome": res["outcome"], "R": round(res["r"], 3)})
        i = max(res["end"], i) + 1
    return pd.DataFrame(trades)


# ============================ Pump / Dump Radar ============================
# الفكرة: نلتقط "البصمة" اللي بتسبق الحركة (حجم يتصاعد + تدفق أموال في اتجاه واحد + انضغاط تذبذب + قرب مستوى)
# ونفرّق بين: مبكر (قبل الحركة) / بدأت / متأخر (الحركة خلصت تقريبًا). مفيش حد يتنبأ بالمستقبل 100%؛
# الرادار بيرفع احتمال، والسجل بيقيس نسبة النجاح الفعلية عشان تعرف تثق فيه قد إيه.

def radar_init():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS radar_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, exchange TEXT, symbol TEXT,
            direction TEXT, score INTEGER, stage TEXT, price REAL, atr_pct REAL,
            outcome TEXT DEFAULT 'OPEN', mfe REAL, mae REAL, closed_at TEXT)""")


def radar_features(frame):
    """ميزات الإنذار المبكر من الشموع. آخر شمعة = الجارية (سعر لحظي)، والحجم يُقاس على الشموع المغلقة."""
    try:
        f = add_indicators(frame)
        n = len(f)
        if n < 60:
            return None
        o, h, l, c, v = (f[k].to_numpy(float) for k in ("open", "high", "low", "close", "vol"))
        last = c[-1]
        if last <= 0:
            return None
        atr = safe_float(f["atr"].iloc[-2])
        if atr <= 0:
            atr = last * 0.004
        atr_pct = max(atr / last * 100, 0.05)
        med_v = float(np.median(v[-50:-4]))
        if med_v <= 0:
            return None
        vr1 = v[-2] / med_v
        vr3 = float(v[-4:-1].mean()) / med_v
        move3 = (last - c[-4]) / c[-4] * 100
        move_atr = move3 / atr_pct
        rng = np.maximum(h - l, last * 1e-9)
        clv = ((c - l) - (h - c)) / rng
        vv = v[-7:-1]
        mf = float((clv[-7:-1] * vv).sum() / max(vv.sum(), 1e-12))
        sma = pd.Series(c).rolling(20).mean()
        sd = pd.Series(c).rolling(20).std()
        bw = (4 * sd / sma).to_numpy()
        hist_bw = bw[-102:-2]
        hist_bw = hist_bw[~np.isnan(hist_bw)]
        bw_now = bw[-2]
        bw_pct = float((hist_bw < bw_now).mean()) if len(hist_bw) >= 20 and not np.isnan(bw_now) else 0.5
        hi_n, lo_n = float(h[-50:-2].max()), float(l[-50:-2].min())
        near_hi = (hi_n - last) / max(atr, 1e-12)
        near_lo = (last - lo_n) / max(atr, 1e-12)
        roc_now = (c[-2] - c[-5]) / c[-5] * 100
        roc_prev = (c[-5] - c[-8]) / c[-8] * 100
        accel = (roc_now - roc_prev) / atr_pct
        hl = float(np.mean(np.diff(l[-8:-1]) > 0))
        lh = float(np.mean(np.diff(h[-8:-1]) < 0))
        return {
            "last": last, "atr": atr, "atr_pct": atr_pct, "vr1": vr1, "vr3": vr3, "move3": move3,
            "move_atr": move_atr, "mf": mf, "bw_pct": bw_pct, "squeeze": bw_pct <= 0.25,
            "hi_n": hi_n, "lo_n": lo_n, "near_hi": near_hi, "near_lo": near_lo,
            "broke_hi": last > hi_n, "broke_lo": last < lo_n, "accel": accel, "hl": hl, "lh": lh,
            "rsi": safe_float(f["rsi"].iloc[-2], 50),
            "ema_bull": safe_float(f["ema9"].iloc[-1]) > safe_float(f["ema21"].iloc[-1]),
            "low6": float(l[-7:-1].min()), "high6": float(h[-7:-1].max()),
        }
    except Exception:
        return None


def radar_score(ft, ctx):
    """يحسب احتمال Pump و Dump (0-99) مع الأسباب. ctx = بيانات المرحلة التانية (دفتر/CVD/OI/Funding/BTC)."""
    pump = dump = 0.0
    rp, rd = [], []
    vr3, mf, ma = ft["vr3"], ft["mf"], ft["move_atr"]

    energy = min(max(vr3 - 1.0, 0) * 6, 22)
    if energy > 0:
        if mf > 0.1:
            pump += energy
            rp.append(f"حجم متصاعد x{vr3:.1f} مع شراء")
        elif mf < -0.1:
            dump += energy
            rd.append(f"حجم متصاعد x{vr3:.1f} مع بيع")
        else:
            pump += energy * 0.3
            dump += energy * 0.3
    if mf > 0:
        pump += mf * 20
        if mf > 0.25:
            rp.append(f"تدفق أموال شرائي {mf:+.2f}")
    else:
        dump += -mf * 20
        if mf < -0.25:
            rd.append(f"تدفق أموال بيعي {mf:+.2f}")
    pump += ft["hl"] * 8
    dump += ft["lh"] * 8
    if ft["hl"] >= 0.8:
        rp.append("قيعان صاعدة متتالية")
    if ft["lh"] >= 0.8:
        rd.append("قمم هابطة متتالية")
    if ft["squeeze"]:
        if ft["near_hi"] < 1.0:
            pump += 12
            rp.append("انضغاط تذبذب + السعر قرب أعلى 50 شمعة")
        if ft["near_lo"] < 1.0:
            dump += 12
            rd.append("انضغاط تذبذب + السعر قرب أدنى 50 شمعة")
    if ft["broke_hi"] and ma < 3:
        pump += 10
        rp.append("اختراق قمة 50 شمعة")
    if ft["broke_lo"] and ma > -3:
        dump += 10
        rd.append("كسر قاع 50 شمعة")
    acc = ft["accel"]
    if acc > 0:
        pump += min(acc, 1.0) * 8
        if acc > 0.4:
            rp.append("تسارع صعودي")
    elif acc < 0:
        dump += min(-acc, 1.0) * 8
        if acc < -0.4:
            rd.append("تسارع هبوطي")
    if ft["ema_bull"]:
        pump += 4
    else:
        dump += 4
    if vr3 > 2.5 and abs(ma) < 1.0:
        if mf > 0.15:
            pump += 10
            rp.append("امتصاص/تجميع: حجم كبير بدون حركة سعرية")
        elif mf < -0.15:
            dump += 10
            rd.append("تصريف: حجم كبير بدون حركة سعرية")

    # الحركة المتأخرة
    if ma > 3.5:
        pump -= min((ma - 3.5) * 6, 24)
        rp.append("⚠️ الحركة الصاعدة متقدمة بالفعل")
        if ft["rsi"] > 80:
            dump += 6
            rd.append("إرهاق شرائي RSI>80؛ احتمال انعكاس")
    if ma < -3.5:
        dump -= min((-ma - 3.5) * 6, 24)
        rd.append("⚠️ الحركة الهابطة متقدمة بالفعل")
        if ft["rsi"] < 20:
            pump += 6
            rp.append("إرهاق بيعي RSI<20؛ احتمال ارتداد")

    # المرحلة التانية
    book, cvd, oi = ctx.get("book"), ctx.get("cvd"), ctx.get("oi")
    fund, btc = ctx.get("funding"), ctx.get("btc")
    if book is not None:
        if book > 12:
            pump += 7
            rp.append(f"دفتر الأوامر مائل للشراء {book:+.0f}%")
        elif book < -12:
            dump += 7
            rd.append(f"دفتر الأوامر مائل للبيع {book:+.0f}%")
    if cvd is not None:
        if cvd > 8:
            pump += 8
            rp.append(f"CVD حقيقي إيجابي {cvd:+.0f}%")
        elif cvd < -8:
            dump += 8
            rd.append(f"CVD حقيقي سلبي {cvd:+.0f}%")
    if oi is not None and oi >= 1.0:
        if mf >= 0 and ft["move3"] > -0.3:
            pump += 6
            rp.append(f"OI يرتفع {oi:+.1f}%: مراكز جديدة تتراكم")
        elif mf < 0 and ft["move3"] < 0.3:
            dump += 6
            rd.append(f"OI يرتفع {oi:+.1f}%: مراكز بيع جديدة")
    if fund is not None:
        if fund < -0.05:
            pump += 6
            rp.append(f"Funding سالب {fund:+.3f}%: وقود Short Squeeze")
        elif fund > 0.06:
            dump += 6
            rd.append(f"Funding مرتفع {fund:+.3f}%: Longs مزدحمة")
    if btc is not None:
        if btc < -1.5:
            pump -= 6
        if btc > 1.5:
            dump -= 6

    pump, dump = float(np.clip(pump, 0, 99)), float(np.clip(dump, 0, 99))
    if abs(ma) < 1.2:
        stage_key, stage = "early", "مبكر ⏳ (قبل الحركة)"
    elif abs(ma) < 3.0:
        stage_key, stage = "started", "بدأت 🔥"
    else:
        stage_key, stage = "late", "متأخر ⚠️"
    score = max(pump, dump)
    if abs(pump - dump) < 8:
        direction = "VOLATILE"
    else:
        direction = "PUMP" if pump > dump else "DUMP"
    reasons = rp if direction == "PUMP" else rd if direction == "DUMP" else rp[:3] + rd[:3]
    return {"pump": round(pump), "dump": round(dump), "score": round(score), "direction": direction,
            "stage": stage, "stage_key": stage_key, "reasons": reasons}


def radar_levels(ft, direction):
    atr, last = ft["atr"], ft["last"]
    if direction == "PUMP":
        return {"trigger": max(ft["hi_n"], last), "stop": ft["low6"] - 0.2 * atr,
                "tp1": last + 2 * atr, "tp2": last + 3.5 * atr}
    if direction == "DUMP":
        return {"trigger": min(ft["lo_n"], last), "stop": ft["high6"] + 0.2 * atr,
                "tp1": last - 2 * atr, "tp2": last - 3.5 * atr}
    return {"trigger": None, "stop": None, "tp1": None, "tp2": None}


def radar_deep(platform, symbol):
    book, _ = get_futures_orderbook(platform, symbol, 20)
    cvd = get_real_cvd(platform, symbol)
    funding, oi = get_futures_funding_oi(platform, symbol)
    return {"book": book, "cvd": cvd, "funding": funding, "oi": oi}


def run_radar(platform, limit_coins, timeframe, deep_n):
    symbols = SYMBOL_SOURCES[platform](limit_coins)
    if not symbols:
        return {"error": f"تعذر جلب قائمة الرموز من {platform} (جرّب منصة تانية).", "rows": []}
    source = KLINE_SOURCES[platform]
    btc = get_btc_change()
    prev = st.session_state.get("radar_prev", {})

    def stage1(sym):
        try:
            fr = source(sym, timeframe, 150)
            ft = radar_features(fr) if fr is not None else None
            if ft is None:
                return None
            return {"symbol": sym, "ft": ft}
        except Exception:
            return None

    rows = []
    progress, status = st.progress(0), st.empty()
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(stage1, s): s for s in symbols}
        for done, fut in enumerate(as_completed(futs), start=1):
            progress.progress(done / len(symbols))
            status.caption(f"مرحلة 1: {futs[fut]} ({done}/{len(symbols)})")
            r = fut.result()
            if r:
                r["s1"] = radar_score(r["ft"], {"btc": btc})
                rows.append(r)
    rows.sort(key=lambda r: r["s1"]["score"], reverse=True)
    top = rows[:deep_n]
    status.caption(f"مرحلة 2: دفتر أوامر + CVD + OI + Funding لأفضل {len(top)} مرشح...")
    with ThreadPoolExecutor(max_workers=6) as ex:
        deeps = list(ex.map(lambda r: radar_deep(platform, r["symbol"]), top))
    progress.empty()
    status.empty()
    out = []
    now = time.time()
    for r, d in zip(top, deeps):
        ctx = dict(d)
        ctx["btc"] = btc
        sc = radar_score(r["ft"], ctx)
        p = prev.get(r["symbol"])
        delta = sc["score"] - p[1] if p and now - p[0] < 900 else None
        out.append({"symbol": r["symbol"], "ft": r["ft"], "ctx": ctx, "levels": radar_levels(r["ft"], sc["direction"]),
                    "price": r["ft"]["last"], "atr_pct": r["ft"]["atr_pct"], "delta": delta, **sc})
    st.session_state["radar_prev"] = {**prev, **{o["symbol"]: (now, o["score"]) for o in out}}
    out.sort(key=lambda o: (o["stage_key"] == "late", -o["score"]))
    return {"error": None, "rows": out, "platform": platform, "tf": timeframe, "scanned": len(rows),
            "ts": now_cairo().strftime("%H:%M:%S"), "btc": btc}


def radar_log_alerts(rows, exchange, min_score):
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=30)).isoformat()
    n = 0
    with db() as conn:
        for r in rows:
            if r["direction"] == "VOLATILE" or r["stage_key"] == "late" or r["score"] < min_score:
                continue
            dup = conn.execute("SELECT 1 FROM radar_log WHERE exchange=? AND symbol=? AND created_at>=? LIMIT 1",
                               (exchange, r["symbol"], cutoff)).fetchone()
            if dup:
                continue
            conn.execute("INSERT INTO radar_log (created_at,exchange,symbol,direction,score,stage,price,atr_pct) "
                         "VALUES (?,?,?,?,?,?,?,?)",
                         (now.isoformat(), exchange, r["symbol"], r["direction"], int(r["score"]),
                          r["stage_key"], float(r["price"]), float(r["atr_pct"])))
            n += 1
    return n


def radar_evaluate(limit=40):
    """يقيس نجاح التنبيهات: Hit لو الحركة المتوقعة (2×ATR، حد أدنى 1%) حصلت قبل حركة عكسية (1.2×ATR، حد أدنى 0.6%) خلال 60 دقيقة."""
    with db() as conn:
        rows = conn.execute("SELECT id,created_at,exchange,symbol,direction,price,atr_pct FROM radar_log "
                            "WHERE outcome='OPEN' ORDER BY id ASC LIMIT ?", (limit,)).fetchall()
    now = datetime.now(timezone.utc)
    due = []
    for r in rows:
        try:
            ts = _parse_dt(r[1])
        except Exception:
            continue
        if (now - ts).total_seconds() >= 180 and r[2] in KLINE_SOURCES:
            due.append((r, ts))
    if not due:
        return 0
    jobs = {(r[2], r[3]) for r, _ in due}

    def fetch(k):
        try:
            return k, KLINE_SOURCES[k[0]](k[1], "1m", 500)
        except Exception:
            return k, None

    with ThreadPoolExecutor(max_workers=6) as ex:
        frames = dict(ex.map(fetch, list(jobs)))
    updates = 0
    for r, ts in due:
        sid, _, ex_name, sym, direction, price, atr_pct = r
        fr = frames.get((ex_name, sym))
        if fr is None or fr.empty:
            continue
        t = pd.to_numeric(fr["time"], errors="coerce").to_numpy(float)
        t = np.where(t > 1e12, t / 1000, t)
        hi, lo = fr["high"].to_numpy(float), fr["low"].to_numpy(float)
        tgt = max(1.0, 2 * atr_pct) / 100
        adv = max(0.6, 1.2 * atr_pct) / 100
        t0 = ts.timestamp()
        mfe = mae = 0.0
        outcome = None
        for k in range(len(t)):
            if t[k] <= t0 or t[k] > t0 + 3600:
                continue
            if direction == "PUMP":
                fav, bad = hi[k] / price - 1, 1 - lo[k] / price
            else:
                fav, bad = 1 - lo[k] / price, hi[k] / price - 1
            mfe, mae = max(mfe, fav), max(mae, bad)
            if bad >= adv:
                outcome = "MISS"
                break
            if fav >= tgt:
                outcome = "HIT"
                break
        if outcome is None and (now - ts).total_seconds() >= 3600:
            outcome = "NEUTRAL"
        if outcome:
            with db() as conn:
                conn.execute("UPDATE radar_log SET outcome=?,mfe=?,mae=?,closed_at=? WHERE id=? AND outcome='OPEN'",
                             (outcome, mfe * 100, mae * 100, now.isoformat(), sid))
            updates += 1
    return updates


def render_radar_card(item, key, platform, tg_min):
    d = item["direction"]
    tone = {"PUMP": "up", "DUMP": "down", "VOLATILE": "warn"}[d]
    label = {"PUMP": "🚀 PUMP محتمل", "DUMP": "🔻 DUMP محتمل", "VOLATILE": "⚡ تحرك عنيف (الاتجاه غير محسوم)"}[d]
    stage_tone = {"early": "up", "started": "warn", "late": "down"}[item["stage_key"]]
    with st.container(border=True):
        top_l, top_r = st.columns([4, 1])
        with top_l:
            delta_txt = ""
            if item.get("delta") is not None and abs(item["delta"]) >= 3:
                delta_txt = badge(f"{'↑' if item['delta'] > 0 else '↓'} {item['delta']:+.0f} عن الفحص السابق", "info")
            st.markdown(f"### {item['symbol']} " + badge(label, tone) + badge(item["stage"], stage_tone) + delta_txt,
                        unsafe_allow_html=True)
        with top_r:
            st.metric("Score", f"{item['score']}/100")
        score_bar(item["score"], tone)
        ft, ctx = item["ft"], item["ctx"]
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Pump", f"{item['pump']}")
        m2.metric("Dump", f"{item['dump']}")
        m3.metric("حجم x", f"{ft['vr3']:.1f}")
        m4.metric("تدفق أموال", f"{ft['mf']:+.2f}")
        m5.metric("حركة (ATR)", f"{ft['move_atr']:+.1f}")
        chips = ""
        chips += badge(f"دفتر {ctx['book']:+.0f}%", "up" if ctx["book"] > 0 else "down") if ctx.get("book") is not None else ""
        chips += badge(f"CVD {ctx['cvd']:+.0f}%", "up" if ctx["cvd"] > 0 else "down") if ctx.get("cvd") is not None else ""
        chips += badge(f"OI {ctx['oi']:+.1f}%", "info") if ctx.get("oi") is not None else ""
        chips += badge(f"Funding {ctx['funding']:+.3f}%", "warn") if ctx.get("funding") is not None else ""
        chips += badge("انضغاط تذبذب", "info") if ft["squeeze"] else ""
        if chips:
            st.markdown(chips, unsafe_allow_html=True)
        if item["reasons"]:
            st.caption("الأسباب: " + " • ".join(item["reasons"][:6]))
        lv = item["levels"]
        if lv["trigger"] is not None:
            st.caption(f"🎯 تأكيد الدخول: {'إغلاق فوق' if d == 'PUMP' else 'إغلاق تحت'} {lv['trigger']:.8g} | "
                       f"إبطال: {lv['stop']:.8g} | أهداف ATR: {lv['tp1']:.8g} / {lv['tp2']:.8g}")
        if st.button("📡 أرسل إلى Telegram", key=f"rd_tg_{key}"):
            ok, msg = send_telegram(format_radar_telegram(item, platform))
            st.success(msg) if ok else st.error(msg)


def format_radar_telegram(item, platform):
    d = {"PUMP": "🚀 PUMP محتمل", "DUMP": "🔻 DUMP محتمل", "VOLATILE": "⚡ تحرك عنيف"}[item["direction"]]
    lv = item["levels"]
    lines = [f"{d} — {item['symbol']} ({platform})", f"⭐ Score: {item['score']}/100 | {item['stage']}",
             f"💵 السعر: {item['price']:.8g}"]
    if lv["trigger"] is not None:
        lines.append(f"🎯 تأكيد: {lv['trigger']:.8g} | ⛔ إبطال: {lv['stop']:.8g}")
        lines.append(f"✅ {lv['tp1']:.8g} / {lv['tp2']:.8g}")
    lines.append("الأسباب: " + " • ".join(item["reasons"][:5]))
    lines.append("⚠️ تنبيه بحثي وليس نصيحة مالية\n@WHYNOTBLY7")
    return "\n".join(lines)


# ============================ MEXC Up/Down (5m / 15m) — لحظي ============================
# قواعد MEXC: Up يكسب لو سعر التسوية > Baseline، ولو يساوي أو أقل يكسب Down.
# التسوية = متوسط أسعار Index في آخر دقيقة قبل الانتهاء.
# V24: مؤشرات قائدة (دفتر أوامر + CVD حقيقي + فرق سعر البورصات الكبيرة عن Index + زخم) بتتحرك قبل Index بثواني.
PM_PRIOR = np.array([1.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
PM_NAMES = ["z", "z_late", "mom3", "rsi", "ema", "cvd", "volr", "bias"]

LEAD_NAMES = ["ob", "cvd", "spread", "mom"]
LEAD_LABELS = ["ضغط دفتر الأوامر", "تدفق الصفقات (CVD حقيقي)", "فرق سعر البورصات عن Index", "زخم البورصات الكبيرة"]
LEAD_PRIOR = np.array([0.35, 0.50, 0.60, 0.30])
LEAD_W = {
    "ob": {"BINANCE": 1.0, "BYBIT": 0.8, "OKX": 0.5},
    "cvd": {"BINANCE": 1.0, "BYBIT": 0.8, "OKX": 0.5},
    "sp": {"BINANCE": 1.0, "BYBIT": 0.8, "OKX": 0.6, "COINBASE": 0.6},
}


def pm_init():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS pm_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, horizon INTEGER, window_start REAL,
            decision_min REAL, start_price REAL, price_now REAL, p_up REAL, side TEXT,
            payout_up REAL, payout_down REAL, ev REAL, features TEXT, outcome TEXT DEFAULT 'OPEN',
            end_price REAL, correct INTEGER, model_correct INTEGER, pnl REAL, lead TEXT)""")
        cols = {row[1] for row in conn.execute("PRAGMA table_info(pm_predictions)")}
        if "lead" not in cols:
            conn.execute("ALTER TABLE pm_predictions ADD COLUMN lead TEXT")
        conn.execute("CREATE TABLE IF NOT EXISTS pm_model (id INTEGER PRIMARY KEY, weights TEXT, n_updates INTEGER, updated_at TEXT)")


def _sig(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def pm_load_vec(key, prior):
    with db() as conn:
        row = conn.execute("SELECT weights, n_updates FROM pm_model WHERE id=?", (key,)).fetchone()
    if row:
        try:
            w = np.array(json.loads(row[0]), dtype=float)
            if len(w) == len(prior):
                return w, int(row[1])
        except Exception:
            pass
    return prior.copy(), 0


def pm_save_vec(key, w, n_updates):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO pm_model (id, weights, n_updates, updated_at) VALUES (?,?,?,?)",
                     (key, json.dumps([float(v) for v in w]), int(n_updates), datetime.now(timezone.utc).isoformat()))


def pm_load(horizon):
    return pm_load_vec(horizon, PM_PRIOR)


def pm_save(horizon, w, n_updates):
    pm_save_vec(horizon, w, n_updates)


def _pm_norm(frame):
    f = frame.copy()
    t = pd.to_numeric(f["time"], errors="coerce").to_numpy(dtype=float)
    f["time"] = np.where(t > 1e12, t / 1000, t)
    return f.reset_index(drop=True)


def get_pm_frame(n=1500):
    """شموع 1 دقيقة لـ BTC: Index من MEXC أولًا، ثم عقود MEXC، ثم Bybit كبديل. آخر صف = الشمعة الجارية."""
    end = int(time.time())
    for path, label in (("kline/index_price/", "MEXC Index"), ("kline/", "MEXC Futures")):
        payload = api_json("https://contract.mexc.com/api/v1/contract/" + path + "BTC_USDT",
                           {"interval": "Min1", "start": end - n * 60, "end": end})
        data = (payload or {}).get("data")
        if isinstance(data, dict) and len(data.get("time", [])) >= 100:
            size = len(data["time"])
            vol = data.get("vol") or data.get("amount") or [0] * size
            if len(vol) != size:
                vol = [0] * size
            frame = pd.DataFrame({"time": data["time"], "open": data["open"], "high": data["high"],
                                  "low": data["low"], "close": data["close"], "vol": vol})
            frame = _finish(frame, "native")
            if frame is not None:
                return _pm_norm(frame), label
    frame = get_bybit_futures_klines("BTCUSDT", "1m", 1000)
    if frame is not None:
        return _pm_norm(frame), "Bybit (بديل)"
    return None, "تعذر جلب البيانات"


def get_live_index(symbol="BTC_USDT"):
    """سعر لحظي: Index من ticker العقود في MEXC، ثم Bybit كبديل. يرجع (price, source, latency_sec)."""
    t_start = time.time()
    payload = api_json("https://contract.mexc.com/api/v1/contract/ticker", {"symbol": symbol}, retries=0)
    data = (payload or {}).get("data")
    if isinstance(data, list):
        data = data[0] if data else None
    if isinstance(data, dict):
        idx = safe_float(data.get("indexPrice"))
        px = idx or safe_float(data.get("fairPrice")) or safe_float(data.get("lastPrice"))
        if px > 0:
            return px, ("MEXC Index" if idx else "MEXC Last"), time.time() - t_start
    payload = api_json("https://api.bybit.com/v5/market/tickers", {"category": "linear", "symbol": "BTCUSDT"}, retries=0)
    rows = ((payload or {}).get("result") or {}).get("list") or []
    if rows:
        px = safe_float(rows[0].get("indexPrice")) or safe_float(rows[0].get("lastPrice"))
        if px > 0:
            return px, "Bybit Index (بديل)", time.time() - t_start
    return None, "تعذر جلب السعر اللحظي", time.time() - t_start


# ---------------------- المؤشرات القائدة ----------------------

def lead_fetch():
    """يجلب كل البيانات بالتوازي (7 طلبات) — بيرجع (raw, latency)."""
    jobs = {
        "bn_book": ("https://fapi.binance.com/fapi/v1/depth", {"symbol": "BTCUSDT", "limit": 50}),
        "bn_tr": ("https://fapi.binance.com/fapi/v1/aggTrades", {"symbol": "BTCUSDT", "limit": 1000}),
        "by_book": ("https://api.bybit.com/v5/market/orderbook", {"category": "linear", "symbol": "BTCUSDT", "limit": 50}),
        "by_tr": ("https://api.bybit.com/v5/market/recent-trade", {"category": "linear", "symbol": "BTCUSDT", "limit": 1000}),
        "okx_book": ("https://www.okx.com/api/v5/market/books", {"instId": "BTC-USDT-SWAP", "sz": 50}),
        "okx_tr": ("https://www.okx.com/api/v5/market/trades", {"instId": "BTC-USDT-SWAP", "limit": 500}),
        "cb": ("https://api.exchange.coinbase.com/products/BTC-USD/ticker", None),
    }
    t0 = time.time()

    def one(k):
        u, p = jobs[k]
        return k, api_json(u, p, retries=0, timeout=2.5)

    with ThreadPoolExecutor(max_workers=7) as ex:
        raw = dict(ex.map(one, list(jobs)))
    return raw, time.time() - t0


def _lvls(rows, n=50):
    out = []
    for x in (rows or [])[:n]:
        try:
            out.append((float(x[0]), float(x[1])))
        except (TypeError, ValueError, IndexError):
            continue
    return out


def _imb(bids, asks):
    """اختلال دفتر الأوامر % بوزن أقرب مستويات أكتر (وزن = 1/(1+rank/10))."""
    wb = sum(q / (1 + i / 10) for i, (_, q) in enumerate(bids))
    wa = sum(q / (1 + i / 10) for i, (_, q) in enumerate(asks))
    tot = wb + wa
    return (wb - wa) / tot * 100 if tot > 0 else None


def _cvd_windows(trades):
    trades = [t for t in trades if t[0] > 0]
    if not trades:
        return {"fast": None, "slow": None, "cover": 0.0}
    ref = max(t[0] for t in trades)
    out = {"cover": (ref - min(t[0] for t in trades)) / 1000}
    for name, win in (("fast", 20), ("slow", 90)):
        cut = ref - win * 1000
        sel = [t for t in trades if t[0] >= cut]
        buy = sum(q for _, q, b in sel if b)
        sell = sum(q for _, q, b in sel if not b)
        tot = buy + sell
        out[name] = (buy - sell) / tot * 100 if tot > 0 and len(sel) >= 5 else None
    return out


def parse_lead(raw):
    venues = {}

    def add(name, bids, asks, trades):
        mid = None
        if bids and asks:
            mid = (max(p for p, _ in bids) + min(p for p, _ in asks)) / 2
        cv = _cvd_windows(trades) if trades else {"fast": None, "slow": None, "cover": 0.0}
        venues[name] = {"mid": mid, "imb": _imb(bids, asks) if bids and asks else None,
                        "fast": cv["fast"], "slow": cv["slow"], "cover": cv["cover"]}

    b = raw.get("bn_book")
    t = raw.get("bn_tr")
    if isinstance(b, dict) and b.get("bids"):
        trades = [(safe_float(x.get("T")), safe_float(x.get("q")), not x.get("m")) for x in t] if isinstance(t, list) else []
        add("BINANCE", _lvls(b.get("bids")), _lvls(b.get("asks")), trades)
    b = ((raw.get("by_book") or {}).get("result") or {})
    t = ((raw.get("by_tr") or {}).get("result") or {}).get("list") or []
    if b.get("b"):
        trades = [(safe_float(x.get("time")), safe_float(x.get("size")), x.get("side") == "Buy") for x in t]
        add("BYBIT", _lvls(b.get("b")), _lvls(b.get("a")), trades)
    b = ((raw.get("okx_book") or {}).get("data") or [{}])
    b = b[0] if b else {}
    t = (raw.get("okx_tr") or {}).get("data") or []
    if b.get("bids"):
        trades = [(safe_float(x.get("ts")), safe_float(x.get("sz")), x.get("side") == "buy") for x in t]
        add("OKX", _lvls(b.get("bids")), _lvls(b.get("asks")), trades)
    cb = raw.get("cb")
    if isinstance(cb, dict):
        bid, ask, price = safe_float(cb.get("bid")), safe_float(cb.get("ask")), safe_float(cb.get("price"))
        mid = (bid + ask) / 2 if bid > 0 and ask > 0 else price
        if mid > 0:
            venues["COINBASE"] = {"mid": mid, "imb": None, "fast": None, "slow": None, "cover": 0.0}
    return venues


def lead_compute(venues, px, ss, now):
    """يحوّل بيانات البورصات لـ 4 مؤشرات في [-1, +1]. فرق السعر بيتعدّل بخط أساس (Basis) آخر 15 دقيقة."""
    hist = ss.setdefault("pm_lead_hist", {})
    acc = {k: [0.0, 0.0] for k in ("ob", "cvd", "sp", "mom")}
    rows, calibrating, cal_have = [], False, 0
    for name, d in venues.items():
        mid = d.get("mid")
        sp = sp_adj = mom_bps = None
        if mid and px:
            sp = (mid - px) / px * 1e4
            h = hist.setdefault(name, [])
            base_pts = [s for ts, s, _ in h if ts <= now - 15]
            if len(base_pts) >= 20:
                sp_adj = sp - float(np.median(base_pts))
            else:
                calibrating = True
                cal_have = max(cal_have, len(base_pts))
            past = [(ts, m) for ts, _, m in h if ts <= now - 10]
            if past and now - past[-1][0] <= 25:
                mom_bps = (mid - past[-1][1]) / mid * 1e4
            h.append((now, sp, mid))
            while h and h[0][0] < now - 900:
                h.pop(0)
        w = LEAD_W["ob"].get(name)
        if w and d.get("imb") is not None:
            acc["ob"][0] += w * float(np.tanh(d["imb"] / 30))
            acc["ob"][1] += w
        w = LEAD_W["cvd"].get(name)
        if w and (d.get("fast") is not None or d.get("slow") is not None):
            val = (0.6 * np.tanh(d["fast"] / 40) if d.get("fast") is not None else 0.0) + \
                  (0.4 * np.tanh(d["slow"] / 40) if d.get("slow") is not None else 0.0)
            acc["cvd"][0] += w * float(val)
            acc["cvd"][1] += w
        w = LEAD_W["sp"].get(name)
        if w and sp_adj is not None:
            acc["sp"][0] += w * float(np.tanh(sp_adj / 2.0))
            acc["sp"][1] += w
        if w and mom_bps is not None:
            acc["mom"][0] += w * float(np.tanh(mom_bps / 2.0))
            acc["mom"][1] += w
        rows.append({
            "المنصة": name, "السعر": round(mid, 2) if mid else None,
            "فرق عن Index (bps)": round(sp, 2) if sp is not None else None,
            "الفرق المعدّل (bps)": round(sp_adj, 2) if sp_adj is not None else None,
            "دفتر الأوامر %": round(d["imb"], 1) if d.get("imb") is not None else None,
            "CVD 20ث %": round(d["fast"], 1) if d.get("fast") is not None else None,
            "CVD 90ث %": round(d["slow"], 1) if d.get("slow") is not None else None,
        })
    L = [acc[k][0] / acc[k][1] if acc[k][1] > 0 else 0.0 for k in ("ob", "cvd", "sp", "mom")]
    return {"L": L, "rows": rows, "n": len(venues), "calibrating": calibrating, "cal_have": cal_have}


# ---------------------- نموذج الاحتمال ----------------------

def pm_eff_remaining(r):
    """التباين الفعّال بالدقائق: السعر النهائي = متوسط آخر دقيقة، مش آخر Tick."""
    r = max(float(r), 0.0)
    return (r - 1.0) + 1.0 / 3.0 if r > 1.0 else max(r ** 3 / 3.0, 1e-4)


def pm_features(frame, i, t0, H, e=None, live_price=None, start=None):
    close = frame["close"].to_numpy(float).copy()
    vol = frame["vol"].to_numpy(float)
    if live_price:
        close[i] = float(live_price)
    e_val = float(e) if e is not None else float(i - t0 + 1)
    r = max(H - e_val, 0.02)
    start_p = float(start) if start else float(frame["open"].iloc[t0])
    lo = max(0, i - 30)
    rets = np.diff(np.log(close[lo:i + 1]))
    sigma = max(float(rets.std()), 1e-5) if len(rets) >= 5 else 1e-4
    z = float(np.clip(np.log(close[i] / start_p) / (sigma * np.sqrt(pm_eff_remaining(r))), -6, 6))
    mom3 = float(np.clip(np.log(close[i] / close[max(i - 3, 0)]) / (sigma * np.sqrt(3)), -4, 4))
    d = np.diff(close[max(0, i - 14):i + 1])
    gain, loss = d[d > 0].sum(), -d[d < 0].sum()
    rsi = 50.0 if (gain + loss) == 0 else 100 * gain / (gain + loss)
    s60 = pd.Series(close[max(0, i - 59):i + 1])
    ema = float(np.clip((s60.ewm(span=9, adjust=False).mean().iloc[-1] - s60.ewm(span=21, adjust=False).mean().iloc[-1])
                        / (close[i] * sigma), -3, 3))
    cvd = volr = 0.0
    if vol[max(0, i - 20):i + 1].sum() > 0:
        o15 = frame["open"].to_numpy(float)[max(0, i - 14):i + 1]
        c15, v15 = close[max(0, i - 14):i + 1], vol[max(0, i - 14):i + 1]
        g, rr = v15[c15 > o15].sum(), v15[c15 < o15].sum()
        cvd = float((g - rr) / (g + rr) if (g + rr) > 0 else 0.0)
        prev = max(i - 1, 0)
        volr = float(np.clip(np.log((vol[prev] + 1) / (vol[max(0, prev - 20):prev].mean() + 1)), -2, 2)) if prev > 0 else 0.0
    return np.array([z, z * e_val / H, mom3, (rsi - 50) / 50, ema, cvd, volr, 1.0]), e_val, start_p


def pm_build_dataset(frame, H, offset=0):
    t = frame["time"].to_numpy(float)
    opens, highs = frame["open"].to_numpy(float), frame["high"].to_numpy(float)
    lows, closes = frame["low"].to_numpy(float), frame["close"].to_numpy(float)
    X, y, E, W = [], [], [], []
    wid = 0
    for t0 in range(len(t) - H):
        if int(round(t[t0] - offset * 60)) % (H * 60) != 0:
            continue
        last = t0 + H - 1
        if abs(t[last] - t[t0] - (H - 1) * 60) > 1:
            continue
        start = opens[t0]
        settle = (opens[last] + highs[last] + lows[last] + closes[last]) / 4  # تقدير متوسط آخر دقيقة
        label = 1.0 if settle > start else 0.0  # المساواة = Down حسب القواعد
        wid += 1
        for e in range(1, H):
            i = t0 + e - 1
            if i < 35:
                continue
            x, _, _ = pm_features(frame, i, t0, H)
            X.append(x); y.append(label); E.append(e); W.append(wid)
    return np.array(X), np.array(y), np.array(E), np.array(W)


def pm_fit(X, y, w0=None, steps=400, lr=0.4, l2=0.05):
    w = (PM_PRIOR if w0 is None else w0).copy()
    n = max(len(y), 1)
    for _ in range(steps):
        p = _sig(X @ w)
        w -= lr * (X.T @ (p - y) / n + l2 * (w - PM_PRIOR))
    return w


def pm_online_step(w, x, y, lr=0.03, l2=0.01):
    p = _sig(float(x @ w))
    return w - lr * ((p - y) * x + l2 * (w - PM_PRIOR))


def pm_decide(p_up, payout_up, payout_down, min_edge, min_conf):
    ev_up = p_up * payout_up - (1 - p_up)
    ev_dn = (1 - p_up) * payout_down - p_up
    side, ev = ("UP", ev_up) if ev_up >= ev_dn else ("DOWN", ev_dn)
    conf = p_up if side == "UP" else 1 - p_up
    if ev < min_edge or conf < min_conf:
        return "SKIP", ev, conf
    return side, ev, conf


def pm_evaluate(X, y, E, W, payout, min_edge, min_conf):
    cut = np.quantile(W, 0.7)
    tr, te = W <= cut, W > cut
    if tr.sum() < 50 or te.sum() < 30:
        return None
    w = pm_fit(X[tr], y[tr])
    out = {}
    for name, ww in (("Baseline (Brownian)", PM_PRIOR), ("النموذج المتعلّم", w)):
        p = _sig(X[te] @ ww)
        bets = []
        for pi, yi in zip(p, y[te]):
            side, ev, _ = pm_decide(pi, payout, payout, min_edge, min_conf)
            if side == "SKIP":
                continue
            bets.append(payout if (side == "UP") == (yi == 1.0) else -1.0)
        out[name] = {"accuracy": float(((p > 0.5) == (y[te] == 1.0)).mean()), "brier": float(((p - y[te]) ** 2).mean()),
                     "bets": len(bets), "bet_win_rate": float(np.mean([b > 0 for b in bets])) if bets else 0.0,
                     "pnl_per_bet": float(np.mean(bets)) if bets else 0.0, "pnl_total": float(np.sum(bets))}
    p = _sig(X[te] @ w)
    conf = np.maximum(p, 1 - p)
    correct = ((p > 0.5) == (y[te] == 1.0))
    rows = []
    for lo_, hi_ in ((0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)):
        m = (conf >= lo_) & (conf < hi_)
        if m.sum():
            rows.append({"الثقة": f"{lo_:.0%}-{min(hi_, 1):.0%}", "عدد": int(m.sum()), "الدقة الفعلية": f"{correct[m].mean():.1%}"})
    by_e = []
    for e in sorted(set(E[te])):
        m = E[te] == e
        by_e.append({"الدقيقة داخل الدورة": int(e), "عدد": int(m.sum()), "الدقة": f"{correct[m].mean():.1%}"})
    return {"metrics": out, "calibration": rows, "by_elapsed": by_e, "weights": w,
            "n_train": int(tr.sum()), "n_test": int(te.sum()), "base_up": float(y[te].mean())}


def pm_window_start(H, offset, now=None):
    now = time.time() if now is None else now
    W_sec = H * 60
    return ((now - offset * 60) // W_sec) * W_sec + offset * 60


def pm_live_state(H, offset, payout_up, payout_down, min_edge, min_conf, cutoff_sec, auto_log, opts):
    """حالة لحظية: Index الحالي + Baseline + مؤشرات قائدة + احتمال + قرار. بيتحدث كل ثانيتين."""
    ss = st.session_state
    px, src, latency = get_live_index()
    if px is None:
        return {"error": "تعذر جلب السعر اللحظي من MEXC/Bybit."}
    now = time.time()
    ticks = ss.setdefault("pm_ticks", [])
    ticks.append((now, px))
    del ticks[:-4000]
    if ss.get("pm_frame") is None or now - ss.get("pm_frame_ts", 0) > 20:
        frame, fsrc = get_pm_frame()
        if frame is not None:
            ss["pm_frame"], ss["pm_frame_ts"], ss["pm_frame_src"] = frame, now, fsrc
    frame = ss.get("pm_frame")
    if frame is None:
        return {"error": "تعذر جلب شموع الدقيقة."}
    W_sec = H * 60
    t0_time = pm_window_start(H, offset, now)
    t = frame["time"].to_numpy(float)
    idx0 = np.where(np.abs(t - t0_time) < 1)[0]
    if len(idx0) == 0:
        return {"error": "شمعة بداية الدورة مش في البيانات لسه؛ استنى ثواني."}
    t0, i = int(idx0[0]), len(frame) - 1
    manual = ss.get("pm_base_manual")
    if manual and abs(manual[0] - t0_time) < 1 and manual[1] > 0:
        base, base_src = float(manual[1]), "يدوي من شاشة MEXC ✅"
    else:
        near = [p for (ts, p) in ticks if t0_time <= ts <= t0_time + 4]
        if near:
            base, base_src = near[0], "لحظي من التطبيق (أول Tick في الدورة)"
        else:
            base, base_src = float(frame["open"].iloc[t0]), "تقدير من افتتاح شمعة الدقيقة ⚠️ (ثبّت Baseline الحقيقي)"
    e = (now - t0_time) / 60
    remaining = H * 60 - (now - t0_time)
    if e < 0.1:
        return {"error": "الدورة لسه بادئة؛ استنى ثواني."}

    # --- السعر الفعّال: في آخر دقيقة جزء من متوسط التسوية اتحدد فعلًا ---
    running_avg, eff_px = None, px
    if remaining <= 60:
        pts = [p for ts, p in ticks if ts >= t0_time + W_sec - 60]
        if len(pts) >= 3:
            running_avg = float(np.mean(pts))
            a = 1 - remaining / 60.0
            eff_px = a * running_avg + (1 - a) * px

    # --- المؤشرات القائدة ---
    lead, adj = None, 0.0
    if opts.get("use_lead", True):
        cached = ss.get("pm_lead_cache")
        if cached and now - cached[0] < 1.0:
            venues, lat_l = cached[1], cached[2]
        else:
            raw, lat_l = lead_fetch()
            venues = parse_lead(raw)
            ss["pm_lead_cache"] = (now, venues, lat_l)
        lead = lead_compute(venues, px, ss, now)
        lead["lat"] = lat_l
        wl, nl = pm_load_vec(100 + H, LEAD_PRIOR)
        Lv = np.array(lead["L"], dtype=float)
        mult = float(opts.get("lead_mult", 1.0))
        adj = float((Lv * wl).sum() * mult)
        lead.update({"adj": adj, "n_updates": nl, "w": wl, "mult": mult})

    x, e, _ = pm_features(frame, i, t0, H, e=e, live_price=eff_px, start=base)
    w, n_upd = pm_load(H)
    p_base = float(_sig(x @ w))
    p_up = float(_sig(float(x @ w) + adj))
    side, ev, conf = pm_decide(p_up, payout_up, payout_down, min_edge, min_conf)
    gate = None
    if side != "SKIP" and lead and lead["n"] > 0 and opts.get("require_agree", True):
        d = 1 if side == "UP" else -1
        if abs(adj) >= 0.25 and np.sign(adj) != d:
            side, gate = "SKIP", "تعارض مع المؤشرات القائدة"
    if side != "SKIP" and latency > opts.get("max_latency", 2.5):
        side, gate = "SKIP", "تأخر بيانات السعر"
    closed = remaining < cutoff_sec
    stake = 0.0
    if side != "SKIP":
        b = payout_up if side == "UP" else payout_down
        kelly = (conf * b - (1 - conf)) / b
        stake = float(np.clip(kelly * 0.25, 0, 0.05))
    logged = False
    if auto_log and side != "SKIP" and not closed:
        with db() as conn:
            dup = conn.execute("SELECT 1 FROM pm_predictions WHERE horizon=? AND window_start=?", (H, t0_time)).fetchone()
            if not dup:
                lead_js = json.dumps({"L": [float(v) for v in lead["L"]], "mult": lead["mult"]}) if lead else None
                conn.execute("""INSERT INTO pm_predictions (created_at,horizon,window_start,decision_min,start_price,price_now,
                    p_up,side,payout_up,payout_down,ev,features,lead) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                             (datetime.now(timezone.utc).isoformat(), H, t0_time, e, base, px, p_up, side,
                              payout_up, payout_down, ev, json.dumps([float(v) for v in x]), lead_js))
                logged = True
    chart = [(datetime.fromtimestamp(ts, CAIRO).strftime("%H:%M:%S"), p) for ts, p in ticks if ts >= t0_time]
    return {"p_up": p_up, "p_base": p_base, "side": side, "ev": ev, "conf": conf, "e": e, "remaining": remaining,
            "base": base, "base_src": base_src, "px": px, "src": src, "latency": latency, "z": float(x[0]),
            "closed": closed, "n_updates": n_upd, "n_ticks": len(ticks), "running_avg": running_avg,
            "eff_px": eff_px, "logged": logged, "lead": lead, "gate": gate, "stake": stake,
            "ends_at": datetime.fromtimestamp(t0_time + W_sec, CAIRO).strftime("%H:%M:%S"),
            "now": now_cairo().strftime("%H:%M:%S"), "chart": chart, "window_start": t0_time, "H": H}


def pm_resolve_open():
    with db() as conn:
        rows = conn.execute("SELECT id,horizon,window_start,start_price,side,payout_up,payout_down,p_up,features,lead "
                            "FROM pm_predictions WHERE outcome='OPEN'").fetchall()
    now = time.time()
    due = [r for r in rows if r[2] + r[1] * 60 + 20 <= now]
    if not due:
        return 0
    frame, _ = get_pm_frame()
    if frame is None:
        return 0
    t = frame["time"].to_numpy(float)
    ticks = st.session_state.get("pm_ticks", [])
    done = 0
    for sid, H, ws, start, side, pu, pd_, p_up, feats, lead_js in due:
        end_t = ws + H * 60
        pts = [p for ts, p in ticks if end_t - 60 <= ts <= end_t]
        if len(pts) >= 8:
            settle = float(np.mean(pts))  # متوسط Ticks حقيقية جمعها التطبيق في آخر دقيقة
        else:
            idx = np.where(np.abs(t - (ws + (H - 1) * 60)) < 1)[0]
            if len(idx) == 0:
                if now - ws > 7200:
                    with db() as conn:
                        conn.execute("UPDATE pm_predictions SET outcome='EXPIRED' WHERE id=?", (sid,))
                continue
            k = idx[0]
            settle = float((frame["open"].iloc[k] + frame["high"].iloc[k] + frame["low"].iloc[k] + frame["close"].iloc[k]) / 4)
        up = settle > start  # المساواة = Down
        model_correct = int((p_up > 0.5) == up)
        correct = int((side == "UP") == up) if side != "SKIP" else None
        pnl = ((pu if side == "UP" else pd_) if correct else -1.0) if side != "SKIP" else 0.0
        y = 1.0 if up else 0.0
        xv = np.array(json.loads(feats), dtype=float)
        w, n_upd = pm_load(H)
        if lead_js:  # تعلّم أوزان المؤشرات القائدة
            try:
                ld = json.loads(lead_js)
                Lv, mult = np.array(ld["L"], dtype=float), float(ld.get("mult", 1.0))
                wl, nl = pm_load_vec(100 + H, LEAD_PRIOR)
                p_l = float(_sig(float(xv @ w) + float((Lv * wl).sum() * mult)))
                wl = wl - 0.05 * ((p_l - y) * Lv * mult + 0.01 * (wl - LEAD_PRIOR))
                pm_save_vec(100 + H, np.clip(wl, -0.3, 2.0), nl + 1)
            except Exception:
                pass
        w = pm_online_step(w, xv, y)
        pm_save(H, w, n_upd + 1)
        with db() as conn:
            conn.execute("UPDATE pm_predictions SET outcome=?,end_price=?,correct=?,model_correct=?,pnl=? WHERE id=?",
                         ("UP" if up else "DOWN", settle, correct, model_correct, pnl, sid))
        done += 1
    return done


def render_pm_section(tg_enabled):
    st.subheader("🎯 MEXC Up/Down — BTC")
    st.caption("Up يكسب لو سعر التسوية > Baseline، والتساوي = Down. التسوية = متوسط Index آخر دقيقة. "
               "مفيش توقع 100% — النظام بيدخل بس لما فيه ميزة (EV) فوق التعادل وبيقيس دقته الحقيقية.")
    with st.expander("⚙️ الإعدادات", expanded=False):
        c1, c2, c3 = st.columns(3)
        pm_h = 5 if c1.selectbox("الدورة", ["5 دقائق", "15 دقيقة"]) == "5 دقائق" else 15
        pm_pu = c2.number_input("Payout لـ Up (من الشاشة)", min_value=0.1, max_value=5.0, value=0.85, step=0.01)
        pm_pd = c3.number_input("Payout لـ Down (من الشاشة)", min_value=0.1, max_value=5.0, value=0.85, step=0.01)
        c4, c5, c6 = st.columns(3)
        pm_edge = c4.slider("أقل ميزة EV للدخول", 0.0, 0.5, 0.08, 0.01)
        pm_conf = c5.slider("أقل ثقة", 0.50, 0.95, 0.62, 0.01)
        pm_off = c6.number_input("إزاحة بداية الدورة (دقائق)", min_value=0, max_value=14, value=0, step=1)
        c7, c8, c9 = st.columns(3)
        pm_cut = c7.number_input("قفل الدخول قبل النهاية (ثواني)", min_value=0, max_value=120, value=15, step=5)
        pm_live_on = c8.checkbox("⚡ تحديث لحظي كل ثانيتين", value=True, key="pm_live_on")
        pm_auto = c9.checkbox("تسجيل تلقائي لأول إشارة في كل دورة", value=True)
        c10, c11, c12 = st.columns(3)
        use_lead = c10.checkbox("🧭 استخدم المؤشرات القائدة", value=True)
        lead_mult = c11.slider("قوة المؤشرات القائدة", 0.0, 2.0, 1.0, 0.1)
        require_agree = c12.checkbox("امنع الدخول عند التعارض معاها", value=True)
        pm_tg = st.checkbox("📡 أرسل إشارة الدخول إلى Telegram", value=False)
    st.caption(f"نقطة التعادل: Up ≥ {1 / (1 + pm_pu):.1%} | Down ≥ {1 / (1 + pm_pd):.1%} احتمال صح.")

    b1, b2 = st.columns([3, 1])
    base_in = b1.number_input("Baseline (To Beat) من شاشة MEXC للدورة الحالية", min_value=0.0, value=0.0, step=0.01, format="%.2f")
    b2.write("")
    if b2.button("📌 ثبّت للدورة الحالية"):
        st.session_state["pm_base_manual"] = (pm_window_start(pm_h, pm_off), base_in)
        st.toast("تم تثبيت Baseline للدورة الحالية فقط")

    _now_pm = time.time()
    if _now_pm - st.session_state.get("pm_resolve_ts", 0) > 15:
        st.session_state["pm_resolve_ts"] = _now_pm
        try:
            if pm_resolve_open():
                st.toast("اتحسمت توقعات وتم تحديث النموذج")
        except Exception as exc:
            st.caption(f"تعذر حسم التوقعات: {exc}")

    manual_click = (not pm_live_on) and st.button("🎯 توقّع الآن", type="primary")
    live = None
    if pm_live_on or manual_click:
        opts = {"use_lead": use_lead, "lead_mult": lead_mult, "require_agree": require_agree, "max_latency": 2.5}
        live = pm_live_state(pm_h, pm_off, pm_pu, pm_pd, pm_edge, pm_conf, pm_cut, pm_auto, opts)

    tab_live, tab_lead, tab_train, tab_log = st.tabs(["⚡ لحظي", "🧭 المؤشرات القائدة", "🧠 التدريب والتقييم", "📒 السجل والأداء"])

    with tab_live:
        if live is None:
            st.info("فعّل التحديث اللحظي من الإعدادات أو اضغط «توقّع الآن».")
        elif live.get("error"):
            st.error(live["error"])
        else:
            if live["closed"]:
                label, tone = "🔒 الدخول مقفول", "neutral"
            else:
                label, tone = {"UP": ("🟢 UP", "up"), "DOWN": ("🔴 DOWN", "down"), "SKIP": ("⏸️ تجاهل", "neutral")}[live["side"]]
            sub = f"{live['now']} | باقي {live['remaining']:.0f}ث (تنتهي {live['ends_at']})"
            if live["gate"]:
                sub += f" | سبب التجاهل: {live['gate']}"
            decision_card(label, tone, sub, [
                ("احتمال Up", f"{live['p_up']:.1%}"),
                ("الثقة", f"{live['conf']:.1%}"),
                ("EV لكل 1$", f"{live['ev']:+.3f}"),
                ("نسبة دخول مقترحة", f"{live['stake'] * 100:.1f}%" if live["side"] != "SKIP" else "—"),
            ])
            st.progress(float(max(0.0, min(1.0, live["remaining"] / (live["H"] * 60)))))
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Index الآن", f"{live['px']:,.2f}", f"{live['px'] - live['base']:+,.2f} عن Baseline")
            m2.metric("Baseline", f"{live['base']:,.2f}")
            m3.metric("z (البعد عن Baseline)", f"{live['z']:+.2f}")
            m4.metric("احتمال بدون القائدة", f"{live['p_base']:.1%}")
            st.caption(f"Baseline: {live['base_src']} | المصدر: {live['src']} ({live['latency'] * 1000:.0f}ms) | "
                       f"تحديثات تعلّم: {live['n_updates']} | Ticks: {live['n_ticks']}")
            if live["running_avg"] is not None:
                st.caption(f"آخر دقيقة: متوسط Index حتى الآن {live['running_avg']:,.2f} → السعر الفعّال في الحساب {live['eff_px']:,.2f} "
                           "(جزء من التسوية اتحدد فعلًا).")
            if live["logged"]:
                st.success("📝 اتسجلت إشارة للدورة دي.")
                if pm_tg:
                    sent_w = st.session_state.setdefault("pm_tg_sent", set())
                    if live["window_start"] not in sent_w:
                        ok, msg = send_telegram(
                            f"🎯 MEXC {live['H']}m — {'UP 🟢' if live['side'] == 'UP' else 'DOWN 🔴'}\n"
                            f"احتمال Up: {live['p_up']:.1%} | ثقة {live['conf']:.1%} | EV {live['ev']:+.3f}\n"
                            f"Index: {live['px']:,.2f} | Baseline: {live['base']:,.2f}\n⚠️ تنبيه بحثي\n@WHYNOTBLY7")
                        if ok:
                            sent_w.add(live["window_start"])
            if live["side"] == "SKIP" and not live["closed"] and not live["gate"]:
                st.info("مفيش ميزة كفاية دلوقتي. التجاهل قرار صح كتير.")
            if len(live["chart"]) >= 2:
                chart_df = pd.DataFrame(live["chart"], columns=["t", "السعر"]).set_index("t")
                chart_df["Baseline"] = live["base"]
                st.line_chart(chart_df)
            st.caption("⚠️ تأكد إن الـ Payout وBaseline اللي على شاشتك هما اللي كاتبهم هنا، وإن المنصة لسه بتقبل الدخول.")

    with tab_lead:
        if live is None or live.get("error"):
            st.info("شغّل التحديث اللحظي أولًا.")
        elif not live.get("lead"):
            st.info("المؤشرات القائدة متوقفة من الإعدادات.")
        else:
            ld = live["lead"]
            if ld["n"] == 0:
                st.error("مفيش ولا بورصة رجّعت بيانات (غالبًا Binance/Bybit/OKX محجوبين من السيرفر). جرّب تشغيل التطبيق من سيرفر مختلف.")
            else:
                bias = float(np.tanh(ld["adj"]))
                vtone = "up" if bias > 0.12 else "down" if bias < -0.12 else "neutral"
                vtxt = "🟢 القائدة تميل Up" if bias > 0.12 else "🔴 القائدة تميل Down" if bias < -0.12 else "⚪ القائدة محايدة"
                st.markdown(badge(vtxt, vtone) + badge(f"{ld['n']} بورصات متصلة", "info")
                            + badge(f"سرعة الجلب {ld['lat'] * 1000:.0f}ms", "neutral")
                            + badge(f"تحديثات تعلّم الأوزان: {ld['n_updates']}", "neutral"), unsafe_allow_html=True)
                if ld["calibrating"]:
                    st.warning(f"⏳ جاري معايرة خط أساس فرق السعر ({ld['cal_have']}/20 عينة). مؤشر الفرق والزخم هيشتغلوا بعد حوالي دقيقة من فتح الصفحة.")
                notes = [
                    "اختلال الأوامر (Binance/Bybit/OKX) بوزن أقرب المستويات",
                    "Taker buy/sell آخر 20ث و90ث",
                    "الفرق عن خط الأساس (آخر 15 دقيقة) بالـ bps",
                    "تغير متوسط أسعار البورصات خلال 10ث",
                ]
                for k, (lab, v) in enumerate(zip(LEAD_LABELS, ld["L"])):
                    gauge(lab, v, f"{v:+.2f} × وزن {ld['w'][k]:.2f}", notes[k])
                st.markdown("**تفاصيل كل بورصة**")
                show_df(pd.DataFrame(ld["rows"]))
                st.caption("الأوزان بتتعلم تلقائيًا من نتايج الإشارات المسجلة. فرق السعر محسوب بعد إزالة الـ Basis الثابت "
                           "(USDT/USD وعلاوة العقود)، فبيقيس الانحراف غير الطبيعي بس. Coinbase بيدخل في الفرق والزخم فقط.")

    with tab_train:
        if st.button("🧠 درّب وقيّم النموذج"):
            with st.spinner("بيجلب البيانات ويشغّل اختبار Walk-forward..."):
                frame, src = get_pm_frame()
                if frame is None:
                    st.session_state["pm_eval"] = {"error": src}
                else:
                    X, y, E, W = pm_build_dataset(frame, pm_h, pm_off)
                    if len(y) < 200:
                        st.session_state["pm_eval"] = {"error": "بيانات قليلة للتدريب."}
                    else:
                        ev_res = pm_evaluate(X, y, E, W, (pm_pu + pm_pd) / 2, pm_edge, pm_conf)
                        w_all = pm_fit(X, y)
                        _, n_old = pm_load(pm_h)
                        pm_save(pm_h, w_all, n_old)
                        st.session_state["pm_eval"] = {"eval": ev_res, "src": src, "n": len(y), "w": w_all}
        pe = st.session_state.get("pm_eval")
        if pe:
            if pe.get("error"):
                st.error(pe["error"])
            elif pe.get("eval") is None:
                st.info("عينات الاختبار قليلة؛ زوّد البيانات.")
            else:
                r = pe["eval"]
                st.caption(f"المصدر: {pe['src']} | عينات: {pe['n']} (تدريب {r['n_train']} / اختبار {r['n_test']}) | نسبة Up في الاختبار {r['base_up']:.1%}")
                show_df(pd.DataFrame([{"النموذج": k, "الدقة": f"{v['accuracy']:.1%}", "Brier (أقل أحسن)": round(v["brier"], 4),
                                       "صفقات": v["bets"], "فوز الصفقات": f"{v['bet_win_rate']:.1%}",
                                       "ربح/صفقة": round(v["pnl_per_bet"], 3), "إجمالي": round(v["pnl_total"], 2)}
                                      for k, v in r["metrics"].items()]))
                st.write("**الدقة حسب الثقة (اختبار خارج العينة)**")
                show_df(pd.DataFrame(r["calibration"]))
                st.write("**الدقة حسب الدقيقة داخل الدورة**")
                show_df(pd.DataFrame(r["by_elapsed"]))
                st.write("أوزان النموذج: " + " | ".join(f"{n}={v:+.2f}" for n, v in zip(PM_NAMES, pe["w"])))
                st.caption("التدريب التاريخي بيغطي الميزات السعرية بس (المؤشرات القائدة مفيش لها تاريخ مجاني) — هي بتتعلم من السجل الحي. "
                           "الباكتست بيفترض Payout ثابت؛ القياس الحقيقي هو السجل الحي.")
        else:
            st.info("اضغط الزر لتدريب وتقييم النموذج على بيانات الدقيقة التاريخية.")

    with tab_log:
        with db() as conn:
            log = pd.read_sql_query("SELECT id,created_at,horizon,decision_min,start_price,p_up,side,ev,outcome,end_price,correct,model_correct,pnl "
                                    "FROM pm_predictions ORDER BY id DESC LIMIT 300", conn)
        if log.empty:
            st.info("لسه مفيش توقعات مسجلة. فعّل التحديث اللحظي وسيب التطبيق مفتوح.")
        else:
            done_log = log[log.outcome.isin(["UP", "DOWN"])]
            bets_log = done_log[done_log.side != "SKIP"]
            a1, a2, a3, a4 = st.columns(4)
            a1.metric("توقعات محسومة", len(done_log))
            a2.metric("دقة النموذج", f"{done_log['model_correct'].mean():.1%}" if len(done_log) else "—")
            a3.metric("فوز الصفقات", f"{bets_log['correct'].mean():.1%}" if len(bets_log) else "—")
            a4.metric("ربح Paper (وحدات)", f"{done_log['pnl'].sum():+.2f}")
            if len(done_log) >= 2:
                st.line_chart(done_log.sort_values("id")["pnl"].cumsum().reset_index(drop=True))
            st.caption("النتيجة بتتحسب من Ticks حقيقية جمعها التطبيق في آخر دقيقة (لو كان مفتوح)، وإلا من شمعة آخر دقيقة كتقدير. قارنها بسجل MEXC عندك.")
            show_df(log)


# ============================ Init ============================

try:
    init_db()
    pm_init()
    radar_init()
except Exception as _db_exc:
    st.warning(f"تحذير قاعدة البيانات: {_db_exc}")

monitor_status = get_monitor_status()

# ============================ Sidebar ============================

with st.sidebar:
    st.markdown("## 🎛️ إعدادات الماسح")
    platform = st.selectbox("منصة العقود الآجلة", ["KUCOIN", "BINANCE", "BYBIT", "MEXC"])
    st.caption("لو Binance/Bybit مش بيجيبوا بيانات: سيرفرك غالبًا محجوب جغرافيًا، جرّب KUCOIN أو MEXC.")
    st.markdown("### اتجاه الصفقة")
    want_long = st.checkbox("🚀 LONG", value=True)
    want_short = st.checkbox("📉 SHORT", value=True)
    st.markdown("### الفلاتر")
    use_fvg = st.checkbox("FVG (خصم 8 لو مفيش)", value=False)
    mtf_filter = st.checkbox("تأكيد الاتجاه متعدد الأطر (MTF)", value=False)
    btc_filter = st.checkbox("فلتر اتجاه BTC", value=True)
    funding_filter = st.checkbox("فلتر Funding Futures", value=False)
    wall_filter = st.checkbox("دفتر أوامر Futures (حسب المنصة)", value=False)
    killzone = st.checkbox("نوافذ السيولة التقريبية (+5)", value=True)
    confirm_exchanges = st.checkbox("فحص توافر الرمز على 5 منصات Spot", value=False)
    st.markdown("### التصفية")
    min_score = st.slider("أقل Score", 0, 95, 60)
    show_closest = st.checkbox("📌 لو مفيش إشارات، اعرض أقرب 10", value=True)
    limit_coins = st.slider("عدد العملات للفحص", 10, 100, 40, step=5)
    timeframe = st.selectbox("الإطار الزمني", ["1m", "3m", "5m", "15m", "1h"], index=2)
    bars_limit = st.select_slider("عدد الشموع", options=[100, 250, 500, 1000], value=500)
    st.markdown("### إدارة المخاطر")
    capital_usdt = st.number_input("رأس المال USDT", min_value=10.0, value=100.0, step=10.0)
    risk_pct = st.number_input("المخاطرة لكل صفقة %", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
    fee_pct = st.number_input("رسوم تقديرية دخول+خروج %", min_value=0.0, max_value=2.0, value=0.10, step=0.01)
    slippage_pct = st.number_input("انزلاق تقديري %", min_value=0.0, max_value=2.0, value=0.05, step=0.01)
    st.markdown("### Telegram")
    telegram_enabled = st.checkbox("إرسال تلقائي بعد كل فحص", value=False)
    tg_min_score = st.slider("أقل Score للإرسال", 50, 95, 70)
    _tok = _secret("TELEGRAM_BOT_TOKEN")
    _chat = _secret("TELEGRAM_CHANNEL_ID") or _secret("TELEGRAM_CHAT_ID")
    if _tok and _chat:
        st.success("✅ Telegram متوصل")
    else:
        st.error("❌ Telegram ناقص: " + ("التوكن " if not _tok else "") + ("الشات " if not _chat else ""))
        st.caption('Settings > Secrets:\nTELEGRAM_BOT_TOKEN = "..."\nTELEGRAM_CHANNEL_ID = "@channel"')
    if st.button("📡 اختبار Telegram"):
        ok, message = send_telegram("🧪 اختبار BLY7TRADER — الاتصال يعمل.")
        st.success(message) if ok else st.error(message)
    try:
        _prof = learning_profile()
        st.caption(f"🧠 {_prof['trades']} صفقة محسومة | Win Rate {_prof['win_rate']:.1f}% | تعديل {_prof['adjustment']:+d}")
        if _prof["trades"] < 10:
            st.caption(f"التعلم يبدأ بعد {10 - _prof['trades']} صفقات محسومة كمان.")
    except Exception as _e:
        st.caption(f"تعذر قراءة التعلم: {_e}")

settings = {
    "want_long": want_long, "want_short": want_short, "use_fvg": use_fvg, "mtf_filter": mtf_filter,
    "btc_filter": btc_filter, "funding_filter": funding_filter, "wall_filter": wall_filter,
    "killzone": killzone, "confirm_exchanges": confirm_exchanges, "min_score": min_score,
    "capital_usdt": capital_usdt, "risk_pct": risk_pct, "fee_pct": fee_pct,
    "slippage_pct": slippage_pct, "timeframe": timeframe,
}

# ============================ Main navigation ============================

SECTIONS = ["🔎 الماسح", "💥 رادار PUMP/DUMP", "🚀 DEX", "📊 سجل الإشارات", "🧠 الذاكرة والتعلّم", "🧪 اختبار تاريخي", "🎯 MEXC Up/Down"]
section = st.radio("القسم", SECTIONS, horizontal=True, label_visibility="collapsed")

if section == "🔎 الماسح":
    state_key = "scan_main"
    st.subheader("🔎 ماسح السوق")
    st.caption(f"المصدر: {platform} USDT-M Futures | TF: {timeframe} | الشموع: {bars_limit} | العملات: {limit_coins} | "
               f"أقل Score: {min_score} | توقيت القاهرة: {now_cairo().strftime('%H:%M')}")
    if st.button("🔍 افحص السوق الآن", type="primary"):
        result = run_scan(platform, settings, limit_coins, timeframe, bars_limit)
        st.session_state[state_key] = result
        if not result.get("error"):
            saved = save_signals(result["signals"], platform)
            if saved:
                st.toast(f"تم حفظ {saved} إشارة في السجل")
            if telegram_enabled and result["signals"]:
                sent, errors, total = send_signal_batch(result["signals"], platform, tg_min_score)
                if sent:
                    st.success(f"📡 تم إرسال {sent} إشارة إلى تليجرام")
                if errors:
                    st.error(f"تعذر إرسال بعض الإشارات: {errors[-1]}")
                if total == 0:
                    st.info(f"مفيش إشارات بسكور ≥ {tg_min_score} للإرسال.")
    render_scan_results(state_key, min_score, show_closest)

elif section == "💥 رادار PUMP/DUMP":
    ss = st.session_state
    st.subheader("💥 رادار Pump / Dump — إنذار مبكر")
    st.caption("بيدوّر على البصمة اللي بتسبق الحركة: حجم يتصاعد + تدفق أموال في اتجاه واحد + انضغاط تذبذب + قرب مستوى مهم، "
               "وبعدين يأكدها بدفتر الأوامر وCVD الحقيقي وOI وFunding. الحالة «مبكر» = السعر لسه ما اتحركش.")
    with st.expander("⚙️ إعدادات الرادار", expanded=False):
        r1, r2, r3 = st.columns(3)
        r_tf = r1.selectbox("الإطار", ["1m", "3m", "5m", "15m"], index=2, key="r_tf")
        r_n = r2.slider("عدد العملات", 20, 150, 60, 10, key="r_n")
        r_deep = r3.slider("فحص عميق لأفضل", 5, 30, 12, key="r_deep")
        r4, r5, r6 = st.columns(3)
        r_min = r4.slider("أقل Score للعرض", 30, 95, 55, key="r_min")
        r_auto = r5.checkbox("🔄 مراقبة تلقائية", value=False, key="r_auto")
        r_every = r6.select_slider("كل (ثانية)", options=[30, 60, 120, 300], value=60, key="r_every")
        r7, r8, r9 = st.columns(3)
        r_hide_late = r7.checkbox("اخفِ المتأخر ⚠️", value=True, key="r_hide_late")
        r_tg = r8.checkbox("📡 تنبيه Telegram تلقائي", value=False, key="r_tg")
        r_tg_min = r9.slider("أقل Score للتنبيه", 50, 95, 70, key="r_tg_min")
    st.caption(f"المصدر: {platform} | الإطار {r_tf} | توقيت القاهرة {now_cairo().strftime('%H:%M:%S')}")

    if time.time() - ss.get("radar_eval_ts", 0) > 120:
        ss["radar_eval_ts"] = time.time()
        try:
            radar_evaluate()
        except Exception as exc:
            st.caption(f"تعذر تقييم تنبيهات الرادار: {exc}")

    auto_due = r_auto and (time.time() - ss.get("radar_last_ts", 0) >= r_every)
    if st.button("💥 افحص الرادار الآن", type="primary") or auto_due:
        res = run_radar(platform, r_n, r_tf, r_deep)
        ss["radar_res"] = res
        ss["radar_last_ts"] = time.time()
        if not res.get("error"):
            radar_log_alerts(res["rows"], platform, r_min)
            if r_tg:
                alerted = ss.setdefault("radar_alerted", {})
                for item in res["rows"]:
                    if (item["direction"] == "VOLATILE" or item["stage_key"] == "late" or item["score"] < r_tg_min
                            or time.time() - alerted.get(item["symbol"], 0) < 3600):
                        continue
                    ok, _msg = send_telegram(format_radar_telegram(item, platform))
                    if ok:
                        alerted[item["symbol"]] = time.time()

    tab_radar, tab_rlog = st.tabs(["🎯 الرادار", "📒 سجل وتقييم التنبيهات"])
    with tab_radar:
        res = ss.get("radar_res")
        if not res:
            st.info("اضغط «افحص الرادار الآن» أو فعّل المراقبة التلقائية.")
        elif res.get("error"):
            st.error(res["error"])
        else:
            btc_txt = f" | BTC ساعة: {res['btc']:+.2f}%" if res.get("btc") is not None else ""
            st.caption(f"آخر فحص: {res['ts']} | {res['platform']} | TF {res['tf']} | مفحوص: {res['scanned']}{btc_txt}")
            shown = [r for r in res["rows"] if r["score"] >= r_min and not (r_hide_late and r["stage_key"] == "late")]
            if not shown:
                st.warning("مفيش مرشحين بالسكور المطلوب حاليًا. ده طبيعي — السوق الهادي مفيهوش بصمات قوية. "
                           "تقدر تقلل «أقل Score للعرض» أو تفعّل المراقبة التلقائية.")
                near = res["rows"][:5]
                if near:
                    with st.expander("أقرب 5 مرشحين (ضعاف)"):
                        show_df(pd.DataFrame([{"العملة": r["symbol"], "الاتجاه": r["direction"], "Score": r["score"],
                                               "المرحلة": r["stage"]} for r in near]))
            else:
                early = sum(1 for r in shown if r["stage_key"] == "early")
                st.success(f"{len(shown)} مرشح — منهم {early} في مرحلة مبكرة (قبل الحركة).")
                for k, item in enumerate(shown):
                    render_radar_card(item, f"{k}_{item['symbol']}", res["platform"], r_tg_min)
            st.caption("⚠️ الرادار بيرفع احتمال مش بيضمن. استخدم وقف خسارة، وتجاهل أي عملة سيولتها ضعيفة. "
                       "نسبة النجاح الحقيقية تظهر في تبويب السجل بعد ما التنبيهات تتحسم.")
    with tab_rlog:
        with db() as conn:
            rlog = pd.read_sql_query("SELECT id,created_at,exchange,symbol,direction,score,stage,price,outcome,mfe,mae "
                                     "FROM radar_log ORDER BY id DESC LIMIT 300", conn)
        if rlog.empty:
            st.info("لسه مفيش تنبيهات مسجلة. التنبيهات اللي score ≥ حد العرض وغير متأخرة بتتسجل تلقائيًا وبتتقيّم بعد 60 دقيقة.")
        else:
            decided = rlog[rlog.outcome.isin(["HIT", "MISS"])]
            q1, q2, q3, q4 = st.columns(4)
            q1.metric("تنبيهات", len(rlog))
            q2.metric("محسومة (Hit/Miss)", len(decided))
            q3.metric("Hit Rate", f"{(decided.outcome == 'HIT').mean():.1%}" if len(decided) else "—")
            q4.metric("مفتوحة", int((rlog.outcome == "OPEN").sum()))
            if len(decided) >= 5:
                buckets = []
                for lo_, hi_ in ((0, 65), (65, 75), (75, 101)):
                    sub = decided[(decided.score >= lo_) & (decided.score < hi_)]
                    if len(sub):
                        buckets.append({"Score": f"{lo_}-{min(hi_, 100)}", "عدد": len(sub),
                                        "Hit Rate": f"{(sub.outcome == 'HIT').mean():.1%}"})
                if buckets:
                    st.write("**Hit Rate حسب الـ Score**")
                    show_df(pd.DataFrame(buckets))
            st.caption("Hit = الحركة المتوقعة (2×ATR، حد أدنى 1%) حصلت قبل حركة عكسية (1.2×ATR، حد أدنى 0.6%) خلال 60 دقيقة. "
                       "لو الحركتين في نفس الدقيقة تُحسب Miss.")
            show_df(rlog)

elif section == "🚀 DEX":
    st.subheader("🚀 ماسح DEX — BNB Smart Chain")
    c1, c2, c3 = st.columns(3)
    dex_vol = c1.number_input("أقل حجم 5 دقائق $", min_value=0.0, value=5000.0, step=1000.0)
    dex_chg = c2.number_input("أقل تغير 5 دقائق %", min_value=0.0, value=5.0, step=1.0)
    dex_liq = c3.number_input("أقل سيولة $", min_value=0.0, value=15000.0, step=5000.0)
    if st.button("🚀 افحص DEX الآن", type="primary"):
        with st.spinner("بيجمع أزواج BSC..."):
            passed, near = scan_dex(dex_vol, dex_chg, dex_liq)
        st.session_state["dex_res"] = {"passed": passed, "near": near, "ts": now_cairo().strftime("%H:%M:%S")}
        if telegram_enabled:
            sent_addr = st.session_state.setdefault("dex_sent", set())
            for item in passed[:5]:
                if item["address"] in sent_addr:
                    continue
                ok, err = send_telegram(f"🚀 DEX {item['symbol']} على BSC\nالسعر: ${item['price']:.10g}\n"
                                        f"5m: {item['change_5m']:.2f}%\nحجم 5m: ${item['volume_5m']:,.0f}\n"
                                        f"السيولة: ${item['liquidity']:,.0f}\n{item['url']}\n@WHYNOTBLY7")
                if ok:
                    sent_addr.add(item["address"])
                else:
                    st.warning(f"تعذر إرسال {item['symbol']}: {err}")
    dex_res = st.session_state.get("dex_res")
    if dex_res:
        st.caption(f"آخر فحص: {dex_res['ts']}")
        if dex_res["passed"]:
            st.success(f"{len(dex_res['passed'])} زوج مطابق")
            for i, item in enumerate(dex_res["passed"]):
                render_dex_item(item, f"p{i}")
        else:
            st.info("لا توجد أزواج مطابقة للشروط حاليًا. أقرب النتائج:")
            for i, item in enumerate(dex_res["near"]):
                render_dex_item(item, f"n{i}")

elif section == "📊 سجل الإشارات":
    st.subheader("📊 سجل الإشارات المحفوظ")
    history = load_signal_history(300)
    if history.empty:
        st.info("لا توجد إشارات محفوظة بعد. شغّل الماسح أولاً.")
    else:
        outcome_filter = st.selectbox("تصفية النتيجة", ["الكل", "OPEN", "WIN", "LOSS", "BREAKEVEN", "EXPIRED"])
        view = history if outcome_filter == "الكل" else history[history["outcome"] == outcome_filter]
        show_df(view)
        st.caption("المتابعة التلقائية كل دقيقة والتطبيق مفتوح. الصفقة لازم يتلمس دخولها الأول، وعند تعارض الوقف والهدف في نفس الشمعة يُحتسب الوقف.")

elif section == "🧠 الذاكرة والتعلّم":
    st.subheader("🧠 الذاكرة الدائمة — نتائج الصفقات")
    if st.button("🔄 حدّث المراقبة الآن"):
        monitor_status = get_monitor_status(force=True)
    st.caption(f"المراقبة: فُحصت {monitor_status['checked']} صفقة مفتوحة؛ حُسمت {len(monitor_status['resolved'])}."
               + (f" ⚠️ {monitor_status['error']}" if monitor_status.get("error") else ""))
    if monitor_status["resolved"]:
        show_df(pd.DataFrame(monitor_status["resolved"]))
    profile = learning_profile()
    a, b, c = st.columns(3)
    a.metric("صفقات محسومة", profile["trades"])
    b.metric("Win Rate", f"{profile['win_rate']:.1f}%")
    c.metric("تعديل السكور المتعلّم", f"{profile['adjustment']:+d}")
    if profile["by_side"]:
        st.write("**الأداء حسب الاتجاه**")
        show_df(pd.DataFrame([{"الاتجاه": k, **v} for k, v in profile["by_side"].items()]))
    with db() as conn:
        open_trades = pd.read_sql_query(
            "SELECT id,created_at,exchange,symbol,side,score FROM signals WHERE outcome='OPEN' ORDER BY id DESC LIMIT 300", conn)
        all_trades = pd.read_sql_query(
            "SELECT id,created_at,exchange,symbol,side,score,entry,stop,tp1,tp2,tp3,outcome,pnl_pct,result_source "
            "FROM signals ORDER BY id DESC LIMIT 500", conn)
    st.markdown("#### تحديث نتيجة صفقة يدويًا")
    if not open_trades.empty:
        options = {f"#{int(r.id)} {r.exchange} {r.symbol} {r.side} | {str(r.created_at)[:16]}": int(r.id)
                   for r in open_trades.itertuples()}
        selected = st.selectbox("اختر الإشارة", list(options))
        choice = st.selectbox("النتيجة", ["WIN", "LOSS", "BREAKEVEN", "OPEN"])
        if st.button("💾 حفظ النتيجة"):
            update_trade_outcome(options[selected], choice)
            st.success("تم الحفظ.")
            st.rerun()
    else:
        st.info("لا توجد صفقات مفتوحة.")
    st.markdown("#### سجل النتائج")
    if not all_trades.empty:
        show_df(all_trades)
    else:
        st.info("سيظهر السجل بعد أول فحص.")
    st.markdown("#### نسخ احتياطي (مهم على Streamlit Cloud)")
    st.caption("الملفات بتتمسح عند إعادة تشغيل التطبيق، فصدّر السجل دوريًا وارفعه تاني عند الحاجة.")
    full = load_signal_history(100000)
    st.download_button("⬇️ تصدير السجل CSV", full.to_csv(index=False).encode("utf-8"),
                       file_name="bly7trader_signals.csv", mime="text/csv")
    up = st.file_uploader("استيراد سجل CSV", type=["csv"])
    if up is not None and st.button("📥 استيراد"):
        try:
            added, msg = import_history(pd.read_csv(up))
            st.success(f"تمت إضافة {added} صفقة.") if msg == "OK" else st.error(msg)
        except Exception as exc:
            st.error(f"فشل الاستيراد: {exc}")

elif section == "🧪 اختبار تاريخي":
    st.subheader("🧪 باكتست بنفس منطق الماسح (بدون فلاتر الشبكة)")
    st.caption("بيستخدم نفس حساب Score والاتجاه والدخول/الوقف/الأهداف على شموع تاريخية، ويحاكي التنفيذ بنفس قواعد المراقبة.")
    c1, c2, c3 = st.columns(3)
    bt_platform = c1.selectbox("المنصة", list(KLINE_SOURCES), index=list(KLINE_SOURCES).index(platform), key="bt_platform")
    bt_symbol = c2.text_input("الرمز", value=DEFAULT_TEST_SYMBOL[bt_platform], key=f"bt_sym_{bt_platform}")
    bt_tf = c3.selectbox("الإطار", ["1m", "3m", "5m", "15m", "1h"], index=2, key="bt_tf")
    c4, c5, c6 = st.columns(3)
    bt_target = c4.selectbox("الهدف", ["TP1 (1.5R)", "TP2 (2.5R)", "TP3 (3.5R)"], key="bt_target")
    bt_hold = c5.slider("أقصى مدة احتفاظ (شموع)", 10, 200, 48, key="bt_hold")
    bt_score = c6.slider("أقل Score للباكتست", 0, 95, int(min_score), key="bt_score")
    if st.button("▶️ شغّل الباكتست", type="primary"):
        with st.spinner("بيجلب الشموع ويشغّل الاختبار..."):
            frame = KLINE_SOURCES[bt_platform](bt_symbol.strip(), bt_tf, 1000)
            if frame is None or len(frame) < 120:
                st.session_state["bt_res"] = {"error": "تعذر جلب شموع كافية (راجع صيغة الرمز أو جرّب منصة تانية)."}
            else:
                bt_set = dict(settings)
                bt_set["min_score"] = bt_score
                bt_set["want_long"], bt_set["want_short"] = True, True
                trades = run_backtest(frame, bt_set, ["TP1 (1.5R)", "TP2 (2.5R)", "TP3 (3.5R)"].index(bt_target), bt_hold)
                st.session_state["bt_res"] = {"trades": trades, "bars": len(frame), "label": f"{bt_platform} {bt_symbol} {bt_tf}"}
    bt = st.session_state.get("bt_res")
    if bt:
        if bt.get("error"):
            st.error(bt["error"])
        else:
            trades = bt["trades"]
            st.caption(f"{bt['label']} | شموع: {bt['bars']}")
            if trades.empty:
                st.info("مفيش صفقات عدّت الفلتر. قلّل أقل Score أو جرّب رمز/إطار تاني.")
            else:
                done = trades[trades.outcome.isin(["WIN", "LOSS", "TIMEOUT"])]
                wins, losses = int((done.outcome == "WIN").sum()), int((done.outcome == "LOSS").sum())
                gross_win = done.loc[done.R > 0, "R"].sum()
                gross_loss = -done.loc[done.R < 0, "R"].sum()
                pf = gross_win / gross_loss if gross_loss > 0 else float("inf") if gross_win > 0 else 0
                equity = done["R"].cumsum()
                dd = float((equity - equity.cummax()).min()) if len(equity) else 0.0
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("صفقات منفّذة", len(done))
                m2.metric("رابحة / خاسرة", f"{wins} / {losses}")
                m3.metric("Win Rate", f"{wins / max(wins + losses, 1) * 100:.1f}%")
                m4.metric("لم يُفعّل دخولها", int((trades.outcome == "NOFILL").sum()))
                m5, m6, m7 = st.columns(3)
                m5.metric("إجمالي R", f"{done['R'].sum():+.2f}")
                m6.metric("متوسط R (Expectancy)", f"{done['R'].mean():+.3f}" if len(done) else "—")
                m7.metric("Profit Factor", "∞" if pf == float("inf") else f"{pf:.2f}")
                st.caption(f"أقصى تراجع: {dd:.2f}R")
                if len(equity):
                    st.line_chart(equity.reset_index(drop=True))
                show_df(trades)
            st.caption("تنبيه: باكتست على بيانات ماضية لا يضمن الأداء المستقبلي، ولا يشمل Funding ولا فروق السبريد الفعلية.")

elif section == "🎯 MEXC Up/Down":
    render_pm_section(telegram_enabled)

# المؤقّت في آخر السكريبت عشان ما يقاطعش فحص شغّال
try:
    from streamlit_autorefresh import st_autorefresh
    _pm_fast = section == "🎯 MEXC Up/Down" and st.session_state.get("pm_live_on", True)
    _radar_auto = section == "💥 رادار PUMP/DUMP" and st.session_state.get("r_auto", False)
    if _pm_fast:
        st_autorefresh(interval=2_000, key="bly7_pm_live_refresh")
    elif _radar_auto:
        st_autorefresh(interval=10_000, key="bly7_radar_refresh")
    else:
        st_autorefresh(interval=60_000, key="bly7_auto_monitor")
except Exception:
    pass

st.markdown("---")
st.caption("BLY7TRADER | بيانات من واجهات المنصات العامة؛ قد تحدث انقطاعات/حدود معدل. "
           "لا تنفّذ صفقة اعتمادًا على الإشارة وحدها؛ راجع السيولة والسبريد والمخاطرة.")
