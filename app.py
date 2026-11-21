# BLY7TRADER — V24 (Pro UI + Lead Indicators + Pump/Dump Radar)
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
except Exception:
    CAIRO = timezone(timedelta(hours=2))

st.set_page_config(page_title="BLY7TRADER V24", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")
APP_TITLE = "BLY7TRADER"
APP_VERSION = "V24"
DB_PATH = os.getenv("BLY7TRADER_DB", "bly7trader_memory.db")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BLY7TRADER/24.0"})
TIMEOUT = 8
STABLES = {"USDCUSDT", "BUSDUSDT", "DAIUSDT", "FDUSDUSDT", "USDEUSDT", "TUSDUSDT"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
.stMarkdown, .stButton button, .stTabs button, label, .stCaption { font-family: 'Cairo', sans-serif; }
.block-container { padding-top: 1.2rem; max-width: 1280px; }
.b7-hero { padding: 18px 22px; border-radius: 16px; margin-bottom: 14px; color: #fff;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #6d28d9 100%); }
.b7-hero h1 { margin: 0; font-size: 1.7rem; font-weight: 800; letter-spacing: .5px; }
.b7-hero p { margin: 4px 0 0 0; opacity: .85; font-size: .95rem; }
.b7-badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .78rem; font-weight: 700; margin: 0 3px 3px 0; }
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
    v = float(max(-1.0, min(1.0, value if value is not None else 0.0)))
    pct = abs(v) * 50
    color = TONES["up"] if v > 0.05 else TONES["down"] if v < -0.05 else TONES["neutral"]
    left = 50 if v >= 0 else 50 - pct
    st.markdown(f'<div class="b7-gauge"><div class="b7-g-top"><span>{label}</span><span style="color:{color}">{text}</span></div><div class="b7-g-track"><div class="b7-g-mid"></div><div class="b7-g-fill" style="left:{left}%;width:{pct}%;background:{color}"></div></div><div class="b7-note">{note}</div></div>', unsafe_allow_html=True)
def score_bar(value, tone="info"):
    c = TONES.get(tone, TONES["info"])
    v = max(0, min(100, float(value)))
    st.markdown(f'<div class="b7-score"><div style="width:{v}%;background:{c}"></div></div>', unsafe_allow_html=True)
def decision_card(label, tone, sub, stats):
    c = TONES.get(tone, TONES["neutral"])
    cells = "".join(f'<div class="b7-stat"><div class="k">{k}</div><div class="v">{v}</div></div>' for k, v in stats)
    st.markdown(f'<div class="b7-dec" style="border-color:{c}88;background:{c}14"><div class="b7-dec-top"><span class="b7-dec-label" style="color:{c}">{label}</span><span class="b7-dec-sub">{sub}</span></div><div class="b7-dec-grid">{cells}</div></div>', unsafe_allow_html=True)
st.markdown(f"""<div class="b7-hero"><h1>💎 {APP_TITLE} <span style="opacity:.7;font-weight:600">{APP_VERSION}</span></h1><p>ماسح عقود Futures + رادار Pump/Dump مبكر + MEXC Up/Down بمؤشرات قائدة + ذاكرة وتعلّم وباكتست</p></div>""", unsafe_allow_html=True)

def api_json(url, params=None, retries=1, timeout=None):
    for attempt in range(retries + 1):
        try:
            response = SESSION.get(url, params=params, timeout=timeout or TIMEOUT)
            if response.status_code == 429:
                time.sleep(1.0); continue
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                if payload.get("code") not in (None, "200000", 200, 0, "0", "00000"): return None
                if payload.get("retCode") not in (None, 0): return None
            return payload
        except (requests.RequestException, ValueError, TypeError):
            if attempt < retries: time.sleep(0.4)
    return None
def safe_float(value, default=0.0):
    try:
        result = float(value)
        return result if pd.notna(result) else default
    except (TypeError, ValueError): return default
def base_asset(symbol):
    s = str(symbol).upper()
    for suffix in ("USDTM", "_USDT", "-USDT", "USDT"):
        if s.endswith(suffix): s = s[: -len(suffix)]; break
    return "BTC" if s == "XBT" else s
def clamp_entry(entry, price, is_long):
    if price <= 0: return entry
    if abs(entry - price) / price * 100 > 1.5: return price * (0.997 if is_long else 1.003)
    return entry
def now_cairo(): return datetime.now(CAIRO)
def killzone_status():
    current = now_cairo(); minutes = current.hour * 60 + current.minute
    if 10 * 60 <= minutes <= 12 * 60: return True, "نافذة لندن التقريبية"
    if 15 * 60 + 30 <= minutes <= 17 * 60 + 30: return True, "نافذة نيويورك التقريبية"
    return False, "خارج النوافذ المحددة"
def show_df(df, **kwargs):
    try: st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    except TypeError: st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)
def _secret(name, default=""):
    try:
        value = st.secrets.get(name, "")
        if value: return str(value)
    except Exception: pass
    return os.getenv(name, default)
def _parse_dt(text):
    dt = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

SIGNAL_COLUMNS = ["id", "created_at", "exchange", "symbol", "side", "score", "price", "entry", "stop", "tp1", "tp2", "change_pct", "volume_ratio", "cvd_proxy", "outcome", "tp3", "closed_at", "pnl_pct", "result_source", "funding_pct", "oi_change_pct", "market_type", "auto_checked_at"]
REQUIRED_IMPORT = {"created_at", "exchange", "symbol", "side", "score", "price", "entry", "stop", "tp1", "tp2"}
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try: yield conn; conn.commit()
    finally: conn.close()
def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, exchange TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL, score INTEGER NOT NULL, price REAL NOT NULL, entry REAL NOT NULL, stop REAL NOT NULL, tp1 REAL NOT NULL, tp2 REAL NOT NULL, change_pct REAL NOT NULL, volume_ratio REAL NOT NULL, cvd_proxy REAL NOT NULL, outcome TEXT DEFAULT 'OPEN')""")
        existing = {row[1] for row in conn.execute("PRAGMA table_info(signals)")}
        additions = {"tp3": "REAL", "closed_at": "TEXT", "pnl_pct": "REAL", "result_source": "TEXT", "funding_pct": "REAL", "oi_change_pct": "REAL", "market_type": "TEXT DEFAULT 'FUTURES'", "auto_checked_at": "TEXT"}
        for name, declaration in additions.items():
            if name not in existing: conn.execute(f"ALTER TABLE signals ADD COLUMN {name} {declaration}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_outcome ON signals(outcome)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at)")
def update_trade_outcome(signal_id, outcome):
    if outcome not in ("WIN", "LOSS", "BREAKEVEN", "OPEN"): return
    with db() as conn:
        row = conn.execute("SELECT side, entry, stop, tp1 FROM signals WHERE id=?", (signal_id,)).fetchone()
        if not row: return
        side, entry, stop, tp1 = row
        if outcome == "WIN": pnl = (tp1 - entry) / entry * 100 if side == "LONG" else (entry - tp1) / entry * 100
        elif outcome == "LOSS": pnl = (stop - entry) / entry * 100 if side == "LONG" else (entry - stop) / entry * 100
        else: pnl = 0.0
        closed = None if outcome == "OPEN" else datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE signals SET outcome=?, closed_at=?, pnl_pct=?, result_source='MANUAL' WHERE id=?", (outcome, closed, pnl, signal_id))
def save_signals(signals, exchange):
    signals = [s for s in signals if not s.get("_weak")]
    if not signals: return 0
    now = datetime.now(timezone.utc); stamp = now.isoformat(); cutoff = (now - timedelta(minutes=20)).isoformat(); saved = 0
    with db() as conn:
        for s in signals:
            exists = conn.execute("SELECT 1 FROM signals WHERE exchange=? AND symbol=? AND side=? AND created_at>=? LIMIT 1", (exchange, s["symbol"], s["type"], cutoff)).fetchone()
            if exists: continue
            conn.execute("""INSERT INTO signals (created_at, exchange, symbol, side, score, price, entry, stop, tp1, tp2, change_pct, volume_ratio, cvd_proxy, outcome, tp3, funding_pct, oi_change_pct, market_type) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'OPEN',?,?,?,'FUTURES')""", (stamp, exchange, s["symbol"], s["type"], int(s["score"]), s["price"], s["entry"], s["stop"], s["tp1"], s["tp2"], s["ch"], s["vol"], s["buy"], s.get("tp3"), s.get("funding"), s.get("oi_change")))
            saved += 1
    return saved
def load_signal_history(limit=200):
    with db() as conn: return pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT ?", conn, params=(limit,))
def import_history(df):
    cols = [c for c in df.columns if c in SIGNAL_COLUMNS and c != "id"]
    if not REQUIRED_IMPORT.issubset(set(cols)): return 0, "الملف ناقص أعمدة أساسية: " + ", ".join(sorted(REQUIRED_IMPORT - set(cols)))
    added = 0
    with db() as conn:
        for _, row in df.iterrows():
            dup = conn.execute("SELECT 1 FROM signals WHERE created_at=? AND exchange=? AND symbol=? AND side=? LIMIT 1", (row["created_at"], row["exchange"], row["symbol"], row["side"])).fetchone()
            if dup: continue
            values = []
            for c in cols:
                v = row[c]; values.append(None if pd.isna(v) else (v.item() if hasattr(v, "item") else v))
            conn.execute(f"INSERT INTO signals ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", values); added += 1
    return added, "OK"
def learning_profile():
    with db() as conn: df = pd.read_sql_query("SELECT exchange, side, score, outcome FROM signals WHERE outcome IN ('WIN','LOSS','BREAKEVEN')", conn)
    if df.empty: return {"trades": 0, "win_rate": 0.0, "adjustment": 0, "by_side": {}}
    decided = df[df.outcome.isin(["WIN", "LOSS"])]
    win_rate = (decided.outcome == "WIN").mean() * 100 if not decided.empty else 0.0
    by_side = {}
    for side, group in df.groupby("side"):
        d = group[group.outcome.isin(["WIN", "LOSS"])]
        by_side[side] = {"trades": len(group), "win_rate": round((d.outcome == "WIN").mean() * 100, 1) if len(d) else 0.0}
    adjustment = 0
    if len(decided) >= 10: adjustment = int(max(-8, min(8, round((win_rate - 50) * min(len(decided) / 30, 1) * 0.16))))
    return {"trades": len(df), "win_rate": round(win_rate, 1), "adjustment": adjustment, "by_side": by_side}
def send_telegram(message):
    token = _secret("TELEGRAM_BOT_TOKEN"); chat_id = _secret("TELEGRAM_CHANNEL_ID") or _secret("TELEGRAM_CHAT_ID")
    if not token: return False, "أضف TELEGRAM_BOT_TOKEN داخل Streamlit Secrets"
    if not chat_id: return False, "أضف TELEGRAM_CHANNEL_ID أو TELEGRAM_CHAT_ID داخل Secrets"
    try:
        response = SESSION.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": message[:4000], "disable_web_page_preview": True}, timeout=15)
        data = response.json()
        if response.ok and data.get("ok"): return True, "تم الإرسال"
        return False, data.get("description", f"Telegram HTTP {response.status_code}")
    except (requests.RequestException, ValueError) as exc: return False, str(exc)
def format_telegram(signal, exchange=""):
    side = "🚀 LONG" if signal["type"] == "LONG" else "📉 SHORT"
    extra_lines = str(signal.get("extra", "")).split("\n")[:8]
    return (f"{side} — {signal['symbol']} ({exchange})\n⭐ Score: {signal['score']}/100\n💵 السعر: {signal['price']}\n🎯 الدخول (Limit): {signal['entry']}\n⛔ وقف الخسارة: {signal['stop']}\n✅ TP1: {signal['tp1']}\n🏆 TP2: {signal['tp2']}\n🎯 TP3: {signal.get('tp3', '—')}\n📦 حجم التداول: x{signal['vol']}\n📊 ضغط الشموع: {signal['buy']}%\n" + "\n".join(extra_lines) + "\n@WHYNOTBLY7")
def send_signal_batch(signals, exchange, min_score):
    eligible = [s for s in signals if not s.get("_weak") and s["score"] >= min_score]
    eligible = sorted(eligible, key=lambda s: s["score"], reverse=True)[:5]
    sent, errors = 0, []
    for s in eligible:
        ok, message = send_telegram(format_telegram(s, exchange))
        if ok: sent += 1
        else: errors.append(message)
        time.sleep(0.4)
    return sent, errors, len(eligible)
def aggregate_3m(frame):
    if frame is None or frame.empty: return frame
    f = frame.copy(); t = pd.to_numeric(f["time"], errors="coerce"); step = 180_000 if t.max() > 1e12 else 180; f["bucket"] = t // step
    out = f.groupby("bucket", sort=True).agg(time=("time", "first"), open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), vol=("vol", "sum")).reset_index(drop=True)
    return out
def _finish(frame, timeframe):
    for c in ("time", "open", "high", "low", "close", "vol"): frame[c] = pd.to_numeric(frame[c], errors="coerce")
    frame = frame.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time"); frame["vol"] = frame["vol"].fillna(0); frame = frame.reset_index(drop=True)
    if timeframe == "3m": frame = aggregate_3m(frame)
    return frame if len(frame) >= 30 else None
def get_kucoin_futures_symbols(limit=100):
    payload = api_json("https://api-futures.kucoin.com/api/v1/contracts/active"); rows = (payload or {}).get("data", []) or []
    rows = [x for x in rows if str(x.get("symbol", "")).endswith("USDTM") and x.get("status", "Open") == "Open"]
    rows.sort(key=lambda x: safe_float(x.get("turnoverOf24h")), reverse=True); return [x["symbol"] for x in rows[:limit]]
def get_kucoin_futures_klines(symbol, timeframe="1h", limit=500):
    gran = {"1m": 1, "3m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240}.get(timeframe, 60); mult = 3 if timeframe == "3m" else 1; n = min(int(limit) * mult, 500); end_ms = int(time.time() * 1000); start_ms = end_ms - n * gran * 60_000
    payload = api_json("https://api-futures.kucoin.com/api/v1/kline/query", {"symbol": symbol, "granularity": gran, "from": start_ms, "to": end_ms})
    rows = [r[:6] for r in ((payload or {}).get("data") or []) if isinstance(r, (list, tuple)) and len(r) >= 6]
    if len(rows) < 30: return None
    return _finish(pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "vol"]), timeframe)
def get_binance_futures_symbols(limit=100):
    payload = api_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
    if not isinstance(payload, list): return []
    rows = [x for x in payload if x.get("symbol", "").endswith("USDT") and x.get("symbol") not in STABLES]
    rows.sort(key=lambda x: safe_float(x.get("quoteVolume")), reverse=True); return [x["symbol"] for x in rows[:limit]]
def get_binance_futures_klines(symbol, timeframe="1h", limit=500):
    payload = api_json("https://fapi.binance.com/fapi/v1/klines", {"symbol": symbol, "interval": timeframe, "limit": min(int(limit), 1000)})
    if not isinstance(payload, list) or len(payload) < 30: return None
    frame = pd.DataFrame(payload, columns=["time", "open", "high", "low", "close", "vol", "ct", "qav", "trades", "tb", "tq", "ignore"])
    return _finish(frame[["time", "open", "high", "low", "close", "vol"]].copy(), "native")
def get_bybit_futures_symbols(limit=100):
    payload = api_json("https://api.bybit.com/v5/market/tickers", {"category": "linear"}); rows = (payload or {}).get("result", {}).get("list", []) or []
    rows = [x for x in rows if x.get("symbol", "").endswith("USDT") and x.get("symbol") not in STABLES]
    rows.sort(key=lambda x: safe_float(x.get("turnover24h")), reverse=True); return [x["symbol"] for x in rows[:limit]]
def get_bybit_futures_klines(symbol, timeframe="1h", limit=500):
    interval = {"1m": "1", "3m": "3", "5m": "5", "15m": "15", "1h": "60", "4h": "240"}.get(timeframe, "60")
    payload = api_json("https://api.bybit.com/v5/market/kline", {"category": "linear", "symbol": symbol, "interval": interval, "limit": min(int(limit), 1000)})
    rows = (payload or {}).get("result", {}).get("list", []) or []
    if len(rows) < 30: return None
    frame = pd.DataFrame([r[:6] for r in rows], columns=["time", "open", "high", "low", "close", "vol"]); return _finish(frame, "native")
def get_mexc_futures_symbols(limit=100):
    payload = api_json("https://contract.mexc.com/api/v1/contract/ticker"); rows = (payload or {}).get("data", []) or []
    rows = [x for x in rows if x.get("symbol", "").endswith("_USDT")]; rows.sort(key=lambda x: safe_float(x.get("amount24")), reverse=True); return [x["symbol"] for x in rows[:limit]]
def get_mexc_futures_klines(symbol, timeframe="1h", limit=500):
    gran = {"1m": "Min1", "3m": "Min1", "5m": "Min5", "15m": "Min15", "1h": "Min60", "4h": "Hour4"}.get(timeframe, "Min60")
    seconds = {"1m": 60, "3m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400}.get(timeframe, 3600); mult = 3 if timeframe == "3m" else 1; n = min(int(limit) * mult, 1500); end = int(time.time())
    payload = api_json("https://contract.mexc.com/api/v1/contract/kline/" + symbol, {"interval": gran, "start": end - n * seconds, "end": end})
    data = (payload or {}).get("data", {})
    if not isinstance(data, dict) or len(data.get("time", [])) < 30: return None
    frame = pd.DataFrame({"time": data["time"], "open": data["open"], "high": data["high"], "low": data["low"], "close": data["close"], "vol": data.get("vol", [0] * len(data["time"]))})
    return _finish(frame, timeframe)
KLINE_SOURCES = {"【entity-KUCOIN¦canonical_name=KUCOIN】": get_kucoin_futures_klines, "【entity-BINANCE¦canonical_name=BINANCE】": get_binance_futures_klines, "【entity-BYBIT¦canonical_name=BYBIT】": get_bybit_futures_klines, "MEXC": get_mexc_futures_klines}
SYMBOL_SOURCES = {"【entity-KUCOIN¦canonical_name=KUCOIN】": get_kucoin_futures_symbols, "【entity-BINANCE¦canonical_name=BINANCE】": get_binance_futures_symbols, "【entity-BYBIT¦canonical_name=BYBIT】": get_bybit_futures_symbols, "MEXC": get_mexc_futures_symbols}
DEFAULT_TEST_SYMBOL = {"【entity-KUCOIN¦canonical_name=KUCOIN】": "XBTUSDTM", "【entity-BINANCE¦canonical_name=BINANCE】": "BTCUSDT", "【entity-BYBIT¦canonical_name=BYBIT】": "BTCUSDT", "MEXC": "BTC_USDT"}
def get_futures_funding_oi(exchange, symbol):
    try:
        if exchange == "【entity-BINANCE¦canonical_name=BINANCE】":
            fund = api_json("https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol": symbol}); oi = api_json("https://fapi.binance.com/futures/data/openInterestHist", {"symbol": symbol, "period": "5m", "limit": 12})
            funding = safe_float(fund.get("lastFundingRate")) * 100 if isinstance(fund, dict) and "lastFundingRate" in fund else None; change = None
            if isinstance(oi, list) and len(oi) > 1:
                first = safe_float(oi[0].get("sumOpenInterestValue")); last = safe_float(oi[-1].get("sumOpenInterestValue")); change = (last - first) / first * 100 if first > 0 else None
            return funding, change
        if exchange == "【entity-BYBIT¦canonical_name=BYBIT】":
            f = api_json("https://api.bybit.com/v5/market/funding/history", {"category": "linear", "symbol": symbol, "limit": 2}); o = api_json("https://api.bybit.com/v5/market/open-interest", {"category": "linear", "symbol": symbol, "intervalTime": "5min", "limit": 12})
            fl = (f or {}).get("result", {}).get("list", []) or []; ol = (o or {}).get("result", {}).get("list", []) or []
            funding = safe_float(fl[0].get("fundingRate")) * 100 if fl else None; first = safe_float(ol[-1].get("openInterest")) if ol else 0; last = safe_float(ol[0].get("openInterest")) if ol else 0
            return funding, ((last - first) / first * 100 if first > 0 else None)
        if exchange == "【entity-KUCOIN¦canonical_name=KUCOIN】":
            payload = api_json("https://api-futures.kucoin.com/api/v1/funding-rate/" + symbol + "/current"); data = (payload or {}).get("data") or {}; return (safe_float(data.get("value")) * 100 if data else None), None
        if exchange == "MEXC":
            payload = api_json("https://contract.mexc.com/api/v1/contract/funding_rate/" + symbol); data = (payload or {}).get("data") or {}; return (safe_float(data.get("fundingRate")) * 100 if data else None), None
    except Exception: pass
    return None, None
def get_btc_change():
    payload = api_json("https://fapi.binance.com/fapi/v1/klines", {"symbol": "BTCUSDT", "interval": "1h", "limit": 2})
    if isinstance(payload, list) and len(payload) >= 2:
        prev, cur = safe_float(payload[-2][4]), safe_float(payload[-1][4])
        if prev: return (cur - prev) / prev * 100
    payload = api_json("https://api.bybit.com/v5/market/kline", {"category": "linear", "symbol": "BTCUSDT", "interval": "60", "limit": 2}); rows = (payload or {}).get("result", {}).get("list", []) or []
    if len(rows) >= 2:
        cur, prev = safe_float(rows[0][4]), safe_float(rows[1][4])
        if prev: return (cur - prev) / prev * 100
    return None
def get_trades(exchange, symbol, limit=1000):
    try:
        if exchange == "【entity-BINANCE¦canonical_name=BINANCE】":
            p = api_json("https://fapi.binance.com/fapi/v1/aggTrades", {"symbol": symbol, "limit": min(limit, 1000)}, retries=0)
            if isinstance(p, list): return [(safe_float(t.get("T")), safe_float(t.get("q")), not t.get("m")) for t in p]
        elif exchange == "BYBIT":
            p = api_json("https://api.bybit.com/v5/market/recent-trade", {"category": "linear", "symbol": symbol, "limit": min(limit, 1000)}, retries=0); rows = ((p or {}).get("result") or {}).get("list") or []; return [(safe_float(t.get("time")), safe_float(t.get("size")), t.get("side") == "Buy") for t in rows]
        elif exchange == "MEXC":
            p = api_json("https://contract.mexc.com/api/v1/contract/deals/" + symbol, {"limit": 100}, retries=0); rows = (p or {}).get("data") or []; return [(safe_float(t.get("t")), safe_float(t.get("v")), t.get("T") == 1) for t in rows]
        elif exchange == "KUCOIN":
            p = api_json("https://api-futures.kucoin.com/api/v1/trade/history", {"symbol": symbol}, retries=0); rows = (p or {}).get("data") or []; return [(safe_float(t.get("ts")) / 1e6, safe_float(t.get("size")), t.get("side") == "buy") for t in rows]
    except Exception: pass
    return []
def get_real_cvd(exchange, symbol, limit=1000):
    trades = get_trades(exchange, symbol, limit)
    if len(trades) < 20: return None
    buy = sum(q for _, q, b in trades if b); sell = sum(q for _, q, b in trades if not b); total = buy + sell
    return (buy - sell) / total * 100 if total else None
def get_futures_orderbook(exchange, symbol, limit=20):
    try:
        if exchange == "BINANCE":
            payload = api_json("https://fapi.binance.com/fapi/v1/depth", {"symbol": symbol, "limit": limit})
            if not isinstance(payload, dict): return None, ""
            bids, asks = payload.get("bids", []), payload.get("asks", [])
        elif exchange == "BYBIT":
            payload = api_json("https://api.bybit.com/v5/market/orderbook", {"category": "linear", "symbol": symbol, "limit": limit}); res = (payload or {}).get("result", {}) or {}; bids, asks = res.get("b", []), res.get("a", [])
        elif exchange == "KUCOIN":
            payload = api_json("https://api-futures.kucoin.com/api/v1/level2/snapshot", {"symbol": symbol}); d = (payload or {}).get("data", {}) or {}; bids, asks = d.get("bids", [])[:limit], d.get("asks", [])[:limit]
        elif exchange == "MEXC":
            payload = api_json("https://contract.mexc.com/api/v1/contract/depth/" + symbol, {"limit": limit}); d = (payload or {}).get("data", {}) or {}; bids, asks = d.get("bids", [])[:limit], d.get("asks", [])[:limit]
        else: return None, ""
        bid_vol = sum(safe_float(x[1]) for x in bids if len(x) >= 2); ask_vol = sum(safe_float(x[1]) for x in asks if len(x) >= 2); total = bid_vol + ask_vol
        if total <= 0: return None, ""
        imb = (bid_vol - ask_vol) / total * 100; return imb, f"دفتر أوامر Futures: اختلال {imb:+.1f}% (شراء {bid_vol:.1f} / بيع {ask_vol:.1f})"
    except Exception: return None, ""
def check_spot_listings(symbol):
    base = base_asset(symbol); checks = [("KUCOIN", f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={base}-USDT"), ("GATE", f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={base}_USDT"), ("BITGET", f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={base}USDT"), ("BYBIT", f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={base}USDT"), ("BINANCE", f"https://data-api.binance.vision/api/v3/ticker/price?symbol={base}USDT")]
    available = []
    for name, url in checks:
        try:
            response = SESSION.get(url, timeout=4)
            if not response.ok: continue
            data = response.json()
            if name == "KUCOIN": valid = data.get("code") == "200000" and bool(data.get("data"))
            elif name == "GATE": valid = isinstance(data, list) and len(data) > 0
            elif name == "BITGET": valid = data.get("code") == "00000" and bool(data.get("data"))
            elif name == "BYBIT": valid = data.get("retCode") == 0 and bool(data.get("result", {}).get("list"))
            else: valid = isinstance(data, dict) and "price" in data
            if valid: available.append(name)
        except (requests.RequestException, ValueError, TypeError, AttributeError): continue
    return len(available), available
def add_indicators(frame):
    f = frame.copy(); close = pd.to_numeric(f["close"], errors="coerce"); high = pd.to_numeric(f["high"], errors="coerce"); low = pd.to_numeric(f["low"], errors="coerce")
    f["ema9"] = close.ewm(span=9, adjust=False).mean(); f["ema21"] = close.ewm(span=21, adjust=False).mean()
    delta = close.diff(); gain, loss = delta.clip(lower=0), -delta.clip(upper=0); avg_gain = gain.ewm(alpha=1/14, adjust=False).mean(); avg_loss = loss.ewm(alpha=1/14, adjust=False).mean(); rs = avg_gain / avg_loss.replace(0, np.nan); f["rsi"] = (100 - 100 / (1 + rs)).fillna(50)
    ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean(); f["macd"] = ema12 - ema26; f["macd_signal"] = f["macd"].ewm(span=9, adjust=False).mean()
    prev_close = close.shift(1); tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1); f["atr"] = tr.ewm(alpha=1/14, adjust=False).mean(); f["momentum"] = close.pct_change(5) * 100; return f
def candle_volume_delta_proxy(frame, lookback=20):
    recent = frame.tail(lookback); green = recent.loc[recent["close"] > recent["open"], "vol"].sum(); red = recent.loc[recent["close"] < recent["open"], "vol"].sum(); total = green + red; return float((green - red) / total * 100) if total else 0.0
def find_recent_fvg(frame, lookback=30):
    bull = bear = None; start = max(1, len(frame) - lookback)
    for i in range(start, len(frame) - 1):
        prev_high, prev_low = safe_float(frame["high"].iloc[i-1]), safe_float(frame["low"].iloc[i-1]); next_low, next_high = safe_float(frame["low"].iloc[i+1]), safe_float(frame["high"].iloc[i+1])
        if next_low > prev_high: bull = (prev_high, next_low, (prev_high + next_low) / 2)
        if next_high < prev_low: bear = (next_high, prev_low, (next_high + prev_low) / 2)
    return bull, bear
def market_structure(frame, lookback=20):
    ref = frame.iloc[-(lookback+3):-3] if len(frame) > lookback + 3 else frame.iloc[:-3]; bsl, ssl = safe_float(ref["high"].max()), safe_float(ref["low"].min()); last2 = frame.tail(2); last_close = safe_float(frame["close"].iloc[-1]); bsl_sweep = safe_float(last2["high"].max()) > bsl > last_close; ssl_sweep = safe_float(last2["low"].min()) < ssl < last_close
    bull_ob = bear_ob = None
    if len(frame) >= 4:
        c = frame.iloc[-3]
        if safe_float(c["close"]) > safe_float(c["open"]): bull_ob = (safe_float(c["low"]), safe_float(c["high"]))
        elif safe_float(c["close"]) < safe_float(c["open"]): bear_ob = (safe_float(c["low"]), safe_float(c["high"]))
    return {"bsl": bsl, "ssl": ssl, "bsl_sweep": bool(bsl_sweep), "ssl_sweep": bool(ssl_sweep), "bull_ob": bull_ob, "bear_ob": bear_ob}
def candle_trap_note(frame, side, cvd_proxy):
    c = frame.iloc[-1]; high, low, o, cl = (safe_float(c[k]) for k in ("high", "low", "open", "close")); body = abs(cl - o); upper, lower = high - max(o, cl), min(o, cl) - low
    if side == "SHORT" and body > 0 and upper > body * 1.5: return "ذيل علوي طويل؛ احتمال رفض سعري"
    if side == "LONG" and body > 0 and lower > body * 1.5: return "ذيل سفلي طويل؛ احتمال رفض سعري"
    return f"ضغط الشموع التقريبي: {cvd_proxy:+.1f}%"
def build_levels(side, last, atr, fvg):
    if side == "LONG": raw = fvg[2] if fvg else last * 0.997; entry = min(clamp_entry(raw, last, True), last); sign = 1
    else: raw = fvg[2] if fvg else last * 1.003; entry = max(clamp_entry(raw, last, False), last); sign = -1
    risk = max(atr * 1.5, entry * 0.006); stop = entry - sign * risk; tps = [entry + sign * risk * m for m in (1.5, 2.5, 3.5)]; return entry, stop, tps, risk
def position_sizing(entry, stop, settings):
    dist = abs(entry - stop); risk_cash = settings.get("capital_usdt", 100.0) * settings.get("risk_pct", 1.0) / 100; cost_pct = settings.get("fee_pct", 0.10) + settings.get("slippage_pct", 0.05); eff = dist + entry * cost_pct / 100; qty = risk_cash / eff if eff > 0 else 0; return qty, qty * entry, risk_cash, cost_pct

# ============================ Analysis - زي ما هو بدون تعديل ============================
def analyze(frame, symbol, settings, exchange="BINANCE", learning_obj=None, btc_cached=None, offline=False):
    try:
        if frame is None or len(frame) < 30: return None, "بيانات شموع غير كافية"
        frame = add_indicators(frame); last = safe_float(frame["close"].iloc[-1]); previous = safe_float(frame["close"].iloc[-2])
        if last <= 0 or previous <= 0: return None, "سعر غير صالح"
        change = (last - previous) / previous * 100; avg_vol = safe_float(frame["vol"].iloc[-22:-2].mean()); vol_closed = safe_float(frame["vol"].iloc[-2]); volume_ratio = vol_closed / avg_vol if avg_vol > 0 else 0.0
        cvd_proxy = candle_volume_delta_proxy(frame); ema_bull = safe_float(frame["ema9"].iloc[-1]) > safe_float(frame["ema21"].iloc[-1]); macd_bull = safe_float(frame["macd"].iloc[-1]) > safe_float(frame["macd_signal"].iloc[-1]); rsi = safe_float(frame["rsi"].iloc[-1], 50); atr = safe_float(frame["atr"].iloc[-1]); momentum = safe_float(frame["momentum"].iloc[-1])
        if atr <= 0: atr = last * 0.004
        vote = (2 if cvd_proxy > 0 else -2 if cvd_proxy < 0 else 0); vote += 1 if ema_bull else -1; vote += 1 if macd_bull else -1; vote += 1 if momentum > 0 else -1 if momentum < 0 else 0
        side = "LONG" if vote > 0 else "SHORT" if vote < 0 else ("LONG" if cvd_proxy >= 0 else "SHORT")
        if side == "LONG" and not settings.get("want_long", True): return None, "LONG غير مفعّل"
        if side == "SHORT" and not settings.get("want_short", True): return None, "SHORT غير مفعّل"
        bull_fvg, bear_fvg = find_recent_fvg(frame); fvg = bull_fvg if side == "LONG" else bear_fvg; structure = market_structure(frame); in_kz, kz_label = killzone_status(); use_kz = bool(settings.get("killzone")) and not offline and in_kz
        penalty = 0
        if abs(change) > 8: penalty -= 20
        if settings.get("use_fvg") and not fvg: penalty -= 8
        if side == "LONG" and rsi > 75: penalty -= 6
        if side == "SHORT" and rsi < 25: penalty -= 6
        score = 35.0; score += min(max(volume_ratio, 0) * 3, 15); agree = (cvd_proxy > 0) == (side == "LONG"); score += min(abs(cvd_proxy) * 0.15, 12) if agree else 0; score += min(abs(vote) * 2, 10); score += 4 if ((side == "LONG" and 45 <= rsi <= 68) or (side == "SHORT" and 32 <= rsi <= 55)) else 0; score += 8 if fvg else 0; score += 5 if use_kz else 0; score += 5 if ((side == "LONG" and structure["ssl_sweep"]) or (side == "SHORT" and structure["bsl_sweep"])) else 0
        notes = []; mtf_note = "MTF غير مفعل"; real_cvd = funding = oi_change = book_imb = None; book_note = ""
        if not offline:
            if settings.get("mtf_filter"):
                higher_tf = "1h" if settings.get("timeframe") != "1h" else "4h"; higher = KLINE_SOURCES[exchange](symbol, higher_tf, 120)
                if higher is None or len(higher) < 30: mtf_note = "MTF غير متاح"
                else:
                    higher = add_indicators(higher); h_bull = safe_float(higher["ema9"].iloc[-1]) > safe_float(higher["ema21"].iloc[-1]); aligned = h_bull if side == "LONG" else not h_bull; mtf_note = f"MTF مؤكد على {higher_tf}" if aligned else f"MTF عكس {side} (-10)"
                    if not aligned: penalty -= 10
            btc_change = btc_cached if settings.get("btc_filter") else None
            if btc_change is not None:
                if side == "LONG" and btc_change < -2: penalty -= 10
                if side == "SHORT" and btc_change > 2: penalty -= 10
            pre = score + penalty
            if pre >= max(settings.get("min_score", 0) - 12, 35):
                real_cvd = get_real_cvd(exchange, symbol)
                if real_cvd is not None and abs(real_cvd) >= 3: score += 5 if (real_cvd > 0) == (side == "LONG") else -5
                funding, oi_change = get_futures_funding_oi(exchange, symbol)
                if settings.get("funding_filter") and funding is not None:
                    if (side == "LONG" and funding > 0.05) or (side == "SHORT" and funding < -0.05): penalty -= 8
                if oi_change is not None and oi_change > 1: score += 3
                if settings.get("wall_filter"):
                    book_imb, book_note = get_futures_orderbook(exchange, symbol)
                    if book_imb is not None and ((side == "LONG" and book_imb > 8) or (side == "SHORT" and book_imb < -8)): score += 5
        learning = learning_obj if learning_obj is not None else learning_profile(); score = max(5, min(int(score) + learning.get("adjustment", 0) + penalty, 98))
        entry, stop, (tp1, tp2, tp3), _risk = build_levels(side, last, atr, fvg); qty, notional, risk_cash, cost_pct = position_sizing(entry, stop, settings); stop_dist = abs(entry - stop); rr1 = abs(tp1 - entry) / max(stop_dist, 1e-12)
        notes.append(f"📊 CVD: {(real_cvd if real_cvd is not None else cvd_proxy):+.1f}%"); notes.append(f"🗳️ تصويت الاتجاه: {vote:+d}"); notes.append(f"📦 حجم آخر شمعة مغلقة: x{volume_ratio:.2f}"); notes.append(f"⏰ {kz_label}" if settings.get("killzone") else "⏰ فلتر الوقت متوقف"); notes.append(f"🐋 {candle_trap_note(frame, side, cvd_proxy)}"); notes.append(f"🧭 {mtf_note}"); notes.append(f"📐 EMA9/21: {'صاعد' if ema_bull else 'هابط'} | RSI14: {rsi:.1f} | MACD: {'إيجابي' if macd_bull else 'سلبي'}"); notes.append(f"⚡ ATR14: {atr:.8g} | Momentum(5): {momentum:+.2f}%")
        notes.append(f"🎯 مسافة الوقف: {stop_dist / entry * 100:.2f}% | R:R لـ TP1 = {rr1:.2f}"); notes.append(f"📏 حجم المركز النظري: {qty:.6g} وحدة | {notional:.2f} USDT | مخاطرة {risk_cash:.2f} USDT | تكلفة {cost_pct:.2f}%")
        weak = score < settings.get("min_score", 0)
        result = {"symbol": symbol, "type": side, "score": score, "price": round(last, 8), "ch": round(change, 2), "vol": round(volume_ratio, 2), "buy": round(cvd_proxy, 1), "entry": round(entry, 8), "stop": round(stop, 8), "tp1": round(tp1, 8), "tp2": round(tp2, 8), "tp3": round(tp3, 8), "funding": funding, "oi_change": oi_change, "real_cvd": real_cvd, "rr_tp1": round(rr1, 2), "position_qty": round(qty, 8), "position_notional": round(notional, 2), "extra": "\n".join(notes)}
        if weak: result["_weak"] = True; result["extra"] = f"إشارة ضعيفة - السكور {score} أقل من المطلوب {settings.get('min_score')}\n" + result["extra"]; return result, f"السكور {score} أقل من المطلوب {settings.get('min_score')}"
        return result, "OK"
    except Exception as exc: return None, f"خطأ تحليل: {exc}"
def run_scan(platform, settings, limit_coins, timeframe, bars_limit):
    local = dict(settings); symbols = SYMBOL_SOURCES[platform](limit_coins)
    if not symbols: return {"error": f"تعذر جلب قائمة الرموز من {platform}.", "signals": [], "weak": [], "debug": [], "symbols": 0}
    learning_obj = learning_profile(); btc_cached = get_btc_change() if local.get("btc_filter") else None; source = KLINE_SOURCES[platform]
    def scan_one(sym):
        try:
            fr = source(sym, timeframe, bars_limit)
            if fr is None: return None, {"العملة": sym, "السبب": "تعذر جلب الشموع"}
            sig, reason = analyze(fr, sym, local, platform, learning_obj=learning_obj, btc_cached=btc_cached)
            if sig: return sig, None
            return None, {"العملة": sym, "السبب": reason}
        except Exception as exc: return None, {"العملة": sym, "السبب": f"خطأ: {exc}"}
    signals, weak, debug = [], [], []; progress, status = st.progress(0), st.empty()
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(scan_one, s): s for s in symbols}
        for done, fut in enumerate(as_completed(futures), start=1):
            progress.progress(done / len(symbols)); status.caption(f"يفحص {futures[fut]} ({done}/{len(symbols)})"); sig, dbg = fut.result()
            if sig and sig.get("_weak"): weak.append(sig)
            elif sig: signals.append(sig)
            elif dbg: debug.append(dbg)
    progress.empty(); status.empty(); signals.sort(key=lambda s: s["score"], reverse=True); weak.sort(key=lambda s: s["score"], reverse=True)
    return {"signals": signals, "weak": weak, "debug": debug, "symbols": len(symbols), "error": None, "platform": platform, "ts": now_cairo().strftime("%H:%M:%S"), "tf": timeframe}
def render_signal_card(signal, key, platform):
    is_long = signal["type"] == "LONG"; tone = "up" if is_long else "down"
    with st.container(border=True):
        left, right = st.columns([4, 1])
        with left: st.markdown(f"### {'🚀' if is_long else '📉'} {signal['symbol']} " + badge(signal["type"], tone), unsafe_allow_html=True); st.write(f"السعر: **{signal['price']}** | تغير: **{signal['ch']}%** | Volume: **x{signal['vol']}**")
        with right: st.metric("Score", f"{signal['score']}/100")
        score_bar(signal["score"], tone); a, b, c, d, e = st.columns(5); a.metric("الدخول", signal["entry"]); b.metric("وقف", signal["stop"]); c.metric("TP1", signal["tp1"]); d.metric("TP2", signal["tp2"]); e.metric("TP3", signal["tp3"])
        with st.expander("تفاصيل التحليل"): st.text(signal["extra"])
        if st.button("📡 أرسل إلى Telegram", key=f"tg_{key}"):
            ok, msg = send_telegram(format_telegram(signal, platform)); st.success(msg) if ok else st.error(msg)
def render_scan_results(state_key, min_score, show_closest):
    res = st.session_state.get(state_key)
    if not res: return
    if res.get("error"): st.error(res["error"]); return
    st.caption(f"آخر فحص: {res['ts']} | {res['platform']} | TF {res['tf']} | رموز: {res['symbols']}")
    signals, weak = res["signals"], res["weak"]; shown, is_weak = signals, False
    if not signals and weak and show_closest: shown, is_weak = weak[:10], True; st.warning("مفيش إشارة عدت الفلتر")
    if shown:
        for i, s in enumerate(shown): render_signal_card(s, f"{state_key}_{i}_{s['symbol']}", res["platform"])
    else: st.warning("لم تظهر إشارات مطابقة.")
    if res["debug"]:
        with st.expander(f"أسباب استبعاد ({len(res['debug'])})"): show_df(pd.DataFrame(res["debug"][:50]))
def auto_monitor_open_trades(limit=150):
    with db() as conn: rows = conn.execute("SELECT id,created_at,exchange,symbol,side,entry,stop,tp1,tp2,tp3 FROM signals WHERE outcome='OPEN' ORDER BY id ASC LIMIT ?", (limit,)).fetchall()
    if not rows: return {"checked": 0, "resolved": []}
    now = datetime.now(timezone.utc); prepared, jobs = [], set()
    for row in rows:
        try: created = _parse_dt(row[1])
        except Exception: continue
        age_h = (now - created).total_seconds() / 3600; tf = "1m" if age_h <= 7.5 else "1h"
        if row[2] in KLINE_SOURCES: prepared.append((row, created.timestamp(), age_h, tf)); jobs.add((row[2], row[3], tf))
    def fetch(key):
        try: return key, KLINE_SOURCES[key[0]](key[1], key[2], 500)
        except Exception: return key, None
    frames = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for key, fr in ex.map(fetch, list(jobs)): frames[key] = fr
    resolved, updates, touched = [], [], []
    for row, created_ts, age_h, tf in prepared:
        sid, _, exchange, symbol, side, entry, stop, tp1, tp2, tp3 = row; frame = frames.get((exchange, symbol, tf))
        if frame is None or frame.empty: continue
        touched.append(sid); t = pd.to_numeric(frame["time"], errors="coerce").to_numpy(dtype=float); t = np.where(t > 1e12, t / 1000, t); hi = frame["high"].to_numpy(dtype=float); lo = frame["low"].to_numpy(dtype=float); is_long = side == "LONG"; filled, result = False, None
        for k in range(len(t)):
            if t[k] <= created_ts: continue
            if not filled:
                if (is_long and lo[k] <= entry) or ((not is_long) and hi[k] >= entry):
                    filled = True
                    if (is_long and lo[k] <= stop) or ((not is_long) and hi[k] >= stop): result = ("LOSS", "AUTO_SL", stop, t[k]); break
                continue
            hit_stop = lo[k] <= stop if is_long else hi[k] >= stop; hit = [(n, p) for n, p in (("TP3", tp3), ("TP2", tp2), ("TP1", tp1)) if p and (hi[k] >= p if is_long else lo[k] <= p)]
            if hit_stop: result = ("LOSS", "AUTO_SL", stop, t[k]); break
            if hit: result = ("WIN", "AUTO_" + hit[0][0], tp1, t[k]); break
        if result:
            outcome, label, exit_price, ts = result; pnl = (exit_price - entry) / entry * 100 if is_long else (entry - exit_price) / entry * 100; closed = datetime.fromtimestamp(ts, timezone.utc).isoformat(); updates.append((outcome, closed, pnl, label, sid)); resolved.append({"id": sid, "symbol": symbol, "result": label, "pnl_%": round(pnl, 3)})
        elif (not filled and age_h > 12) or (filled and age_h > 72):
            label = "AUTO_NOFILL" if not filled else "AUTO_TIMEOUT"; updates.append(("EXPIRED", now.isoformat(), 0.0, label, sid)); resolved.append({"id": sid, "symbol": symbol, "result": label, "pnl_%": 0.0})
    with db() as conn:
        stamp = now.isoformat()
        for outcome, closed, pnl, label, sid in updates: conn.execute("UPDATE signals SET outcome=?,closed_at=?,pnl_pct=?,result_source=?,auto_checked_at=? WHERE id=? AND outcome='OPEN'", (outcome, closed, pnl, label, stamp, sid))
        for sid in touched: conn.execute("UPDATE signals SET auto_checked_at=? WHERE id=? AND outcome='OPEN'", (stamp, sid))
    return {"checked": len(touched), "resolved": resolved}
def get_monitor_status(force=False):
    last = st.session_state.get("_mon_ts", 0)
    if not force and "_mon_res" in st.session_state and time.time() - last < 55: return st.session_state["_mon_res"]
    try: res = auto_monitor_open_trades()
    except Exception as exc: res = {"checked": 0, "resolved": [], "error": str(exc)}
    st.session_state["_mon_ts"], st.session_state["_mon_res"] = time.time(), res; return res
def scan_dex(min_vol5=5000.0, min_chg5=5.0, min_liq=15000.0):
    pairs, addresses = [], []
    for q in ("WBNB", "BNB", "USDT", "CAKE", "BSC"):
        payload = api_json("https://api.dexscreener.com/latest/dex/search", {"q": q}); pairs += (payload or {}).get("pairs", []) or []
    for url in ("https://api.dexscreener.com/token-boosts/top/v1", "https://api.dexscreener.com/token-boosts/latest/v1", "https://api.dexscreener.com/token-profiles/latest/v1"):
        data = api_json(url)
        if isinstance(data, list): addresses += [x.get("tokenAddress") for x in data if x.get("chainId") == "bsc" and x.get("tokenAddress")]
    addresses = list(dict.fromkeys(addresses))
    for i in range(0, len(addresses), 30):
        chunk = ",".join(addresses[i:i+30]); data = api_json(f"https://api.dexscreener.com/tokens/v1/bsc/{chunk}")
        if isinstance(data, list): pairs += data
    best = {}
    for pair in pairs:
        if pair.get("chainId") != "bsc": continue
        token = pair.get("baseToken") or {}; addr = (token.get("address") or "").lower()
        if not addr: continue
        liq = safe_float((pair.get("liquidity") or {}).get("usd"))
        if addr not in best or liq > best[addr][1]: best[addr] = (pair, liq)
    rows = []
    for pair, liq in best.values():
        token = pair.get("baseToken") or {}; price = safe_float(pair.get("priceUsd")); vol5 = safe_float((pair.get("volume") or {}).get("m5")); chg5 = safe_float((pair.get("priceChange") or {}).get("m5")); chg1h = safe_float((pair.get("priceChange") or {}).get("h1")); tx5 = (pair.get("txns") or {}).get("m5") or {}; buys, sells = safe_float(tx5.get("buys")), safe_float(tx5.get("sells")); created = safe_float(pair.get("pairCreatedAt")); age_h = (time.time()*1000 - created)/3_600_000 if created else None
        if price <= 0: continue
        rows.append({"symbol": token.get("symbol", "UNKNOWN"), "address": token.get("address", ""), "price": price, "change_5m": chg5, "change_1h": chg1h, "volume_5m": vol5, "liquidity": liq, "buys": buys, "sells": sells, "age_h": age_h, "fdv": safe_float(pair.get("fdv")), "url": pair.get("url", "")})
    passed = [r for r in rows if r["volume_5m"] >= min_vol5 and r["change_5m"] >= min_chg5 and r["liquidity"] >= min_liq]; passed.sort(key=lambda r: r["volume_5m"], reverse=True); near = [r for r in rows if r["liquidity"] >= min_liq and r not in passed]; near.sort(key=lambda r: r["change_5m"]*min(r["volume_5m"], 50000), reverse=True); return passed, near[:10]
def render_dex_item(item, key):
    with st.container(border=True):
        st.markdown(f"### 🚀 {item['symbol']}"); st.write(f"السعر: ${item['price']:.10g} | 5د: {item['change_5m']:.2f}% | حجم 5د: ${item['volume_5m']:,.0f} | السيولة: ${item['liquidity']:,.0f}")
        if item["url"]: st.markdown(f"[فتح الزوج على DexScreener]({item['url']})")
        if st.button("📡 أرسل إلى Telegram", key=f"dex_tg_{key}"):
            ok, msg = send_telegram(f"🚀 DEX {item['symbol']}\nالسعر: ${item['price']:.10g}\n5m: {item['change_5m']:.2f}%\n{item['url']}\n@WHYNOTBLY7"); st.success(msg) if ok else st.error(msg)
def simulate_trade(frame, start, sig, target_idx, max_hold, fill_wait, cost_pct):
    side, entry, stop = sig["type"], sig["entry"], sig["stop"]; target = [sig["tp1"], sig["tp2"], sig["tp3"]][target_idx]; risk = abs(entry - stop)
    if risk <= 0: return {"outcome": "SKIP", "r": 0.0, "end": start}
    cost_r = cost_pct / 100 * entry / risk; is_long = side == "LONG"; hi, lo, cl = frame["high"].to_numpy(float), frame["low"].to_numpy(float), frame["close"].to_numpy(float); n = len(frame); filled = False; end = min(n, start + fill_wait + max_hold)
    for j in range(start, end):
        if not filled:
            if j >= start + fill_wait: return {"outcome": "NOFILL", "r": 0.0, "end": j}
            if (is_long and lo[j] <= entry) or ((not is_long) and hi[j] >= entry):
                filled = True
                if (is_long and lo[j] <= stop) or ((not is_long) and hi[j] >= stop): return {"outcome": "LOSS", "r": -1 - cost_r, "end": j}
            continue
        if (is_long and lo[j] <= stop) or ((not is_long) and hi[j] >= stop): return {"outcome": "LOSS", "r": -1 - cost_r, "end": j}
        if (is_long and hi[j] >= target) or ((not is_long) and lo[j] <= target): return {"outcome": "WIN", "r": abs(target - entry) / risk - cost_r, "end": j}
    if filled:
        j = end - 1; r = ((cl[j] - entry) if is_long else (entry - cl[j])) / risk - cost_r; return {"outcome": "TIMEOUT", "r": r, "end": j}
    return {"outcome": "NOFILL", "r": 0.0, "end": end - 1}
def run_backtest(frame, settings, target_idx=0, max_hold=48, fill_wait=6, warmup=60):
    bt_settings = dict(settings); bt_settings.update({"mtf_filter": False, "btc_filter": False, "funding_filter": False, "wall_filter": False, "killzone": False, "confirm_exchanges": False}); cost_pct = settings.get("fee_pct", 0.10) + settings.get("slippage_pct", 0.05); trades, i, n = [], warmup, len(frame)
    while i < n - 2:
        window = frame.iloc[max(0, i - 299): i + 1]; sig, _ = analyze(window, "BT", bt_settings, offline=True, learning_obj={"adjustment": 0})
        if not sig or sig.get("_weak"): i += 1; continue
        res = simulate_trade(frame, i + 1, sig, target_idx, max_hold, fill_wait, cost_pct); trades.append({"bar": i, "side": sig["type"], "score": sig["score"], "entry": sig["entry"], "stop": sig["stop"], "outcome": res["outcome"], "R": round(res["r"], 3)}); i = max(res["end"], i) + 1
    return pd.DataFrame(trades)
def radar_init():
    with db() as conn: conn.execute("""CREATE TABLE IF NOT EXISTS radar_log (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, exchange TEXT, symbol TEXT, direction TEXT, score INTEGER, stage TEXT, price REAL, atr_pct REAL, outcome TEXT DEFAULT 'OPEN', mfe REAL, mae REAL, closed_at TEXT)""")
def radar_features(frame):
    try:
        f = add_indicators(frame); n = len(f)
        if n < 60: return None
        o, h, l, c, v = (f[k].to_numpy(float) for k in ("open", "high", "low", "close", "vol")); last = c[-1]
        if last <= 0: return None
        atr = safe_float(f["atr"].iloc[-2]);
        if atr <= 0: atr = last * 0.004
        atr_pct = max(atr / last * 100, 0.05); med_v = float(np.median(v[-50:-4]))
        if med_v <= 0: return None
        vr1 = v[-2] / med_v; vr3 = float(v[-4:-1].mean()) / med_v; move3 = (last - c[-4]) / c[-4] * 100; move_atr = move3 / atr_pct; rng = np.maximum(h - l, last * 1e-9); clv = ((c - l) - (h - c)) / rng; vv = v[-7:-1]; mf = float((clv[-7:-1] * vv).sum() / max(vv.sum(), 1e-12)); sma = pd.Series(c).rolling(20).mean(); sd = pd.Series(c).rolling(20).std(); bw = (4 * sd / sma).to_numpy(); hist_bw = bw[-102:-2]; hist_bw = hist_bw[~np.isnan(hist_bw)]; bw_now = bw[-2]; bw_pct = float((hist_bw < bw_now).mean()) if len(hist_bw) >= 20 and not np.isnan(bw_now) else 0.5; hi_n, lo_n = float(h[-50:-2].max()), float(l[-50:-2].min()); near_hi = (hi_n - last) / max(atr, 1e-12); near_lo = (last - lo_n) / max(atr, 1e-12); roc_now = (c[-2] - c[-5]) / c[-5] * 100; roc_prev = (c[-5] - c[-8]) / c[-8] * 100; accel = (roc_now - roc_prev) / atr_pct; hl = float(np.mean(np.diff(l[-8:-1]) > 0)); lh = float(np.mean(np.diff(h[-8:-1]) < 0))
        return {"last": last, "atr": atr, "atr_pct": atr_pct, "vr1": vr1, "vr3": vr3, "move3": move3, "move_atr": move_atr, "mf": mf, "bw_pct": bw_pct, "squeeze": bw_pct <= 0.25, "hi_n": hi_n, "lo_n": lo_n, "near_hi": near_hi, "near_lo": near_lo, "broke_hi": last > hi_n, "broke_lo": last < lo_n, "accel": accel, "hl": hl, "lh": lh, "rsi": safe_float(f["rsi"].iloc[-2], 50), "ema_bull": safe_float(f["ema9"].iloc[-1]) > safe_float(f["ema21"].iloc[-1]), "low6": float(l[-7:-1].min()), "high6": float(h[-7:-1].max())}
    except Exception: return None
def radar_score(ft, ctx):
    pump = dump = 0.0; rp, rd = [], []; vr3, mf, ma = ft["vr3"], ft["mf"], ft["move_atr"]
    energy = min(max(vr3 - 1.0, 0) * 6, 22)
    if energy > 0:
        if mf > 0.1: pump += energy; rp.append(f"حجم متصاعد x{vr3:.1f} مع شراء")
        elif mf < -0.1: dump += energy; rd.append(f"حجم متصاعد x{vr3:.1f} مع بيع")
        else: pump += energy * 0.3; dump += energy * 0.3
    if mf > 0: pump += mf * 20
    else: dump += -mf * 20
    pump += ft["hl"] * 8; dump += ft["lh"] * 8
    if ft["squeeze"]:
        if ft["near_hi"] < 1.0: pump += 12; rp.append("انضغاط + قرب قمة")
        if ft["near_lo"] < 1.0: dump += 12; rd.append("انضغاط + قرب قاع")
    if ft["broke_hi"] and ma < 3: pump += 10; rp.append("اختراق قمة")
    if ft["broke_lo"] and ma > -3: dump += 10; rd.append("كسر قاع")
    acc = ft["accel"]
    if acc > 0: pump += min(acc, 1.0) * 8
    elif acc < 0: dump += min(-acc, 1.0) * 8
    if ft["ema_bull"]: pump += 4
    else: dump += 4
    if ma > 3.5: pump -= min((ma - 3.5) * 6, 24)
    if ma < -3.5: dump -= min((-ma - 3.5) * 6, 24)
    book, cvd, oi = ctx.get("book"), ctx.get("cvd"), ctx.get("oi"); fund, btc = ctx.get("funding"), ctx.get("btc")
    if book is not None:
        if book > 12: pump += 7; rp.append(f"دفتر شراء {book:+.0f}%")
        elif book < -12: dump += 7; rd.append(f"دفتر بيع {book:+.0f}%")
    if cvd is not None:
        if cvd > 8: pump += 8
        elif cvd < -8: dump += 8
    if oi is not None and oi >= 1.0: pump += 6 if mf >= 0 else 0; dump += 6 if mf < 0 else 0
    if fund is not None:
        if fund < -0.05: pump += 6
        elif fund > 0.06: dump += 6
    if btc is not None:
        if btc < -1.5: pump -= 6
        if btc > 1.5: dump -= 6
    pump, dump = float(np.clip(pump, 0, 99)), float(np.clip(dump, 0, 99))
    if abs(ma) < 1.2: stage_key, stage = "early", "مبكر ⏳"
    elif abs(ma) < 3.0: stage_key, stage = "started", "بدأت 🔥"
    else: stage_key, stage = "late", "متأخر ⚠️"
    score = max(pump, dump); direction = "VOLATILE" if abs(pump - dump) < 8 else ("PUMP" if pump > dump else "DUMP"); reasons = rp if direction == "PUMP" else rd if direction == "DUMP" else rp[:3] + rd[:3]
    return {"pump": round(pump), "dump": round(dump), "score": round(score), "direction": direction, "stage": stage, "stage_key": stage_key, "reasons": reasons}
def radar_levels(ft, direction):
    atr, last = ft["atr"], ft["last"]
    if direction == "PUMP": return {"trigger": max(ft["hi_n"], last), "stop": ft["low6"] - 0.2 * atr, "tp1": last + 2 * atr, "tp2": last + 3.5 * atr}
    if direction == "DUMP": return {"trigger": min(ft["lo_n"], last), "stop": ft["high6"] + 0.2 * atr, "tp1": last - 2 * atr, "tp2": last - 3.5 * atr}
    return {"trigger": None, "stop": None, "tp1": None, "tp2": None}
def radar_deep(platform, symbol):
    book, _ = get_futures_orderbook(platform, symbol, 20); cvd = get_real_cvd(platform, symbol); funding, oi = get_futures_funding_oi(platform, symbol); return {"book": book, "cvd": cvd, "funding": funding, "oi": oi}
def run_radar(platform, limit_coins, timeframe, deep_n):
    symbols = SYMBOL_SOURCES[platform](limit_coins)
    if not symbols: return {"error": "تعذر جلب الرموز", "rows": []}
    source = KLINE_SOURCES[platform]; btc = get_btc_change(); prev = st.session_state.get("radar_prev", {})
    def stage1(sym):
        try:
            fr = source(sym, timeframe, 150); ft = radar_features(fr) if fr is not None else None
            if ft is None: return None
            return {"symbol": sym, "ft": ft}
        except Exception: return None
    rows = []; progress, status = st.progress(0), st.empty()
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(stage1, s): s for s in symbols}
        for done, fut in enumerate(as_completed(futs), start=1):
            progress.progress(done / len(symbols)); status.caption(f"مرحلة 1: {futs[fut]} ({done}/{len(symbols)})"); r = fut.result()
            if r: r["s1"] = radar_score(r["ft"], {"btc": btc}); rows.append(r)
    rows.sort(key=lambda r: r["s1"]["score"], reverse=True); top = rows[:deep_n]
    with ThreadPoolExecutor(max_workers=6) as ex: deeps = list(ex.map(lambda r: radar_deep(platform, r["symbol"]), top))
    progress.empty(); status.empty(); out = []; now = time.time()
    for r, d in zip(top, deeps):
        ctx = dict(d); ctx["btc"] = btc; sc = radar_score(r["ft"], ctx); p = prev.get(r["symbol"]); delta = sc["score"] - p[1] if p and now - p[0] < 900 else None
        out.append({"symbol": r["symbol"], "ft": r["ft"], "ctx": ctx, "levels": radar_levels(r["ft"], sc["direction"]), "price": r["ft"]["last"], "atr_pct": r["ft"]["atr_pct"], "delta": delta, **sc})
    st.session_state["radar_prev"] = {**prev, **{o["symbol"]: (now, o["score"]) for o in out}}; out.sort(key=lambda o: (o["stage_key"] == "late", -o["score"]))
    return {"error": None, "rows": out, "platform": platform, "tf": timeframe, "scanned": len(rows), "ts": now_cairo().strftime("%H:%M:%S"), "btc": btc}
def radar_log_alerts(rows, exchange, min_score):
    now = datetime.now(timezone.utc); cutoff = (now - timedelta(minutes=30)).isoformat(); n = 0
    with db() as conn:
        for r in rows:
            if r["direction"] == "VOLATILE" or r["stage_key"] == "late" or r["score"] < min_score: continue
            dup = conn.execute("SELECT 1 FROM radar_log WHERE exchange=? AND symbol=? AND created_at>=? LIMIT 1", (exchange, r["symbol"], cutoff)).fetchone()
            if dup: continue
            conn.execute("INSERT INTO radar_log (created_at,exchange,symbol,direction,score,stage,price,atr_pct) VALUES (?,?,?,?,?,?,?,?)", (now.isoformat(), exchange, r["symbol"], r["direction"], int(r["score"]), r["stage_key"], float(r["price"]), float(r["atr_pct"]))); n += 1
    return n
def radar_evaluate(limit=40):
    with db() as conn: rows = conn.execute("SELECT id,created_at,exchange,symbol,direction,price,atr_pct FROM radar_log WHERE outcome='OPEN' ORDER BY id ASC LIMIT ?", (limit,)).fetchall()
    now = datetime.now(timezone.utc); due = []
    for r in rows:
        try: ts = _parse_dt(r[1])
        except Exception: continue
        if (now - ts).total_seconds() >= 180 and r[2] in KLINE_SOURCES: due.append((r, ts))
    if not due: return 0
    jobs = {(r[2], r[3]) for r, _ in due}
    def fetch(k):
        try: return k, KLINE_SOURCES[k[0]](k[1], "1m", 500)
        except Exception: return k, None
    with ThreadPoolExecutor(max_workers=6) as ex: frames = dict(ex.map(fetch, list(jobs)))
    updates = 0
    for r, ts in due:
        sid, _, ex_name, sym, direction, price, atr_pct = r; fr = frames.get((ex_name, sym))
        if fr is None or fr.empty: continue
        t = pd.to_numeric(fr["time"], errors="coerce").to_numpy(float); t = np.where(t > 1e12, t / 1000, t); hi, lo = fr["high"].to_numpy(float), fr["low"].to_numpy(float); tgt = max(1.0, 2 * atr_pct) / 100; adv = max(0.6, 1.2 * atr_pct) / 100; t0 = ts.timestamp(); mfe = mae = 0.0; outcome = None
        for k in range(len(t)):
            if t[k] <= t0 or t[k] > t0 + 3600: continue
            if direction == "PUMP": fav, bad = hi[k] / price - 1, 1 - lo[k] / price
            else: fav, bad = 1 - lo[k] / price, hi[k] / price - 1
            mfe, mae = max(mfe, fav), max(mae, bad)
            if bad >= adv: outcome = "MISS"; break
            if fav >= tgt: outcome = "HIT"; break
        if outcome is None and (now - ts).total_seconds() >= 3600: outcome = "NEUTRAL"
        if outcome:
            with db() as conn: conn.execute("UPDATE radar_log SET outcome=?,mfe=?,mae=?,closed_at=? WHERE id=? AND outcome='OPEN'", (outcome, mfe * 100, mae * 100, now.isoformat(), sid))
            updates += 1
    return updates
def render_radar_card(item, key, platform, tg_min):
    d = item["direction"]; tone = {"PUMP": "up", "DUMP": "down", "VOLATILE": "warn"}[d]; label = {"PUMP": "🚀 PUMP محتمل", "DUMP": "🔻 DUMP محتمل", "VOLATILE": "⚡ تحرك عنيف"}[d]; stage_tone = {"early": "up", "started": "warn", "late": "down"}[item["stage_key"]]
    with st.container(border=True):
        top_l, top_r = st.columns([4, 1])
        with top_l: st.markdown(f"### {item['symbol']} " + badge(label, tone) + badge(item["stage"], stage_tone), unsafe_allow_html=True)
        with top_r: st.metric("Score", f"{item['score']}/100")
        score_bar(item["score"], tone); ft, ctx = item["ft"], item["ctx"]; m1, m2, m3, m4, m5 = st.columns(5); m1.metric("Pump", f"{item['pump']}"); m2.metric("Dump", f"{item['dump']}"); m3.metric("حجم x", f"{ft['vr3']:.1f}"); m4.metric("تدفق", f"{ft['mf']:+.2f}"); m5.metric("حركة ATR", f"{ft['move_atr']:+.1f}")
        if item["reasons"]: st.caption("الأسباب: " + " • ".join(item["reasons"][:6]))
        lv = item["levels"]
        if lv["trigger"] is not None: st.caption(f"🎯 تأكيد: {lv['trigger']:.8g} | إبطال: {lv['stop']:.8g} | أهداف: {lv['tp1']:.8g} / {lv['tp2']:.8g}")
        if st.button("📡 أرسل إلى Telegram", key=f"rd_tg_{key}"):
            ok, msg = send_telegram(format_radar_telegram(item, platform)); st.success(msg) if ok else st.error(msg)
def format_radar_telegram(item, platform):
    d = {"PUMP": "🚀 PUMP محتمل", "DUMP": "🔻 DUMP محتمل", "VOLATILE": "⚡ تحرك عنيف"}[item["direction"]]; lv = item["levels"]; lines = [f"{d} — {item['symbol']} ({platform})", f"⭐ Score: {item['score']}/100 | {item['stage']}", f"💵 السعر: {item['price']:.8g}"]
    if lv["trigger"] is not None: lines.append(f"🎯 تأكيد: {lv['trigger']:.8g} | ⛔ إبطال: {lv['stop']:.8g}"); lines.append(f"✅ {lv['tp1']:.8g} / {lv['tp2']:.8g}")
    lines.append("الأسباب: " + " • ".join(item["reasons"][:5])); lines.append("⚠️ تنبيه بحثي وليس نصيحة مالية\n@WHYNOTBLY7"); return "\n".join(lines)

# ============================ MEXC Up/Down — التعديلات هنا فقط ============================
PM_PRIOR = np.array([1.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
PM_NAMES = ["z", "z_late", "mom3", "rsi", "ema", "cvd", "volr", "bias"]
LEAD_NAMES = ["ob", "cvd", "spread", "mom"]
LEAD_LABELS = ["ضغط دفتر الأوامر", "تدفق الصفقات (CVD حقيقي)", "فرق سعر البورصات عن Index", "زخم البورصات الكبيرة"]
LEAD_PRIOR = np.array([0.35, 0.50, 0.60, 0.30])
LEAD_W = {"ob": {"BINANCE": 1.0, "BYBIT": 0.8, "OKX": 0.5}, "cvd": {"BINANCE": 1.0, "BYBIT": 0.8, "OKX": 0.5}, "sp": {"BINANCE": 1.0, "BYBIT": 0.8, "OKX": 0.6, "COINBASE": 0.6}}
PM_HYST_ENTER_UP = 0.65; PM_HYST_EXIT_UP = 0.40; PM_HYST_ENTER_DOWN = 0.35; PM_HYST_EXIT_DOWN = 0.70; PM_CONFIRM_N = 3; PM_STRONG_FLIP_P = 0.80; PM_SNAP_ATR_MULT = 1.5; PM_SNAP_MIN_HITS = 3
def pm_init():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS pm_predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, horizon INTEGER, window_start REAL, decision_min REAL, start_price REAL, price_now REAL, p_up REAL, side TEXT, payout_up REAL, payout_down REAL, ev REAL, features TEXT, outcome TEXT DEFAULT 'OPEN', end_price REAL, correct INTEGER, model_correct INTEGER, pnl REAL, lead TEXT)""")
        cols = {row[1] for row in conn.execute("PRAGMA table_info(pm_predictions)")}
        if "lead" not in cols: conn.execute("ALTER TABLE pm_predictions ADD COLUMN lead TEXT")
        conn.execute("CREATE TABLE IF NOT EXISTS pm_model (id INTEGER PRIMARY KEY, weights TEXT, n_updates INTEGER, updated_at TEXT)")
def _sig(x): return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))
def pm_load_vec(key, prior):
    with db() as conn: row = conn.execute("SELECT weights, n_updates FROM pm_model WHERE id=?", (key,)).fetchone()
    if row:
        try:
            w = np.array(json.loads(row[0]), dtype=float)
            if len(w) == len(prior): return w, int(row[1])
        except Exception: pass
    return prior.copy(), 0
def pm_save_vec(key, w, n_updates):
    with db() as conn: conn.execute("INSERT OR REPLACE INTO pm_model (id, weights, n_updates, updated_at) VALUES (?,?,?,?)", (key, json.dumps([float(v) for v in w]), int(n_updates), datetime.now(timezone.utc).isoformat()))
def pm_load(horizon): return pm_load_vec(horizon, PM_PRIOR)
def pm_save(horizon, w, n_updates): pm_save_vec(horizon, w, n_updates)
def _pm_norm(frame):
    f = frame.copy(); t = pd.to_numeric(f["time"], errors="coerce").to_numpy(dtype=float); f["time"] = np.where(t > 1e12, t / 1000, t); return f.reset_index(drop=True)
def get_pm_frame(n=1500):
    end = int(time.time())
    for path, label in (("kline/index_price/", "MEXC Index"), ("kline/", "MEXC Futures")):
        payload = api_json("https://contract.mexc.com/api/v1/contract/" + path + "BTC_USDT", {"interval": "Min1", "start": end - n * 60, "end": end}); data = (payload or {}).get("data")
        if isinstance(data, dict) and len(data.get("time", [])) >= 100:
            size = len(data["time"]); vol = data.get("vol") or data.get("amount") or [0] * size
            if len(vol) != size: vol = [0] * size
            frame = pd.DataFrame({"time": data["time"], "open": data["open"], "high": data["high"], "low": data["low"], "close": data["close"], "vol": vol}); frame = _finish(frame, "native")
            if frame is not None: return _pm_norm(frame), label
    frame = get_bybit_futures_klines("BTCUSDT", "1m", 1000)
    if frame is not None: return _pm_norm(frame), "Bybit (بديل)"
    return None, "تعذر جلب البيانات"
def get_live_index(symbol="BTC_USDT"):
    t_start = time.time(); payload = api_json("https://contract.mexc.com/api/v1/contract/ticker", {"symbol": symbol}, retries=0); data = (payload or {}).get("data")
    if isinstance(data, list): data = data[0] if data else None
    if isinstance(data, dict):
        idx = safe_float(data.get("indexPrice")); px = idx or safe_float(data.get("fairPrice")) or safe_float(data.get("lastPrice"))
        if px > 0: return px, ("MEXC Index" if idx else "MEXC Last"), time.time() - t_start
    payload = api_json("https://api.bybit.com/v5/market/tickers", {"category": "linear", "symbol": "BTCUSDT"}, retries=0); rows = ((payload or {}).get("result") or {}).get("list") or []
    if rows:
        px = safe_float(rows[0].get("indexPrice")) or safe_float(rows[0].get("lastPrice"))
        if px > 0: return px, "Bybit Index (بديل)", time.time() - t_start
    return None, "تعذر جلب السعر اللحظي", time.time() - t_start
def lead_fetch():
    jobs = {"bn_book": ("https://fapi.binance.com/fapi/v1/depth", {"symbol": "BTCUSDT", "limit": 50}), "bn_tr": ("https://fapi.binance.com/fapi/v1/aggTrades", {"symbol": "BTCUSDT", "limit": 1000}), "by_book": ("https://api.bybit.com/v5/market/orderbook", {"category": "linear", "symbol": "BTCUSDT", "limit": 50}), "by_tr": ("https://api.bybit.com/v5/market/recent-trade", {"category": "linear", "symbol": "BTCUSDT", "limit": 1000}), "okx_book": ("https://www.okx.com/api/v5/market/books", {"instId": "BTC-USDT-SWAP", "sz": 50}), "okx_tr": ("https://www.okx.com/api/v5/market/trades", {"instId": "BTC-USDT-SWAP", "limit": 500}), "cb": ("https://api.exchange.coinbase.com/products/BTC-USD/ticker", None)}
    t0 = time.time()
    def one(k):
        u, p = jobs[k]; return k, api_json(u, p, retries=0, timeout=2.5)
    with ThreadPoolExecutor(max_workers=7) as ex: raw = dict(ex.map(one, list(jobs)))
    return raw, time.time() - t0
def _lvls(rows, n=50):
    out = []
    for x in (rows or [])[:n]:
        try: out.append((float(x[0]), float(x[1])))
        except (TypeError, ValueError, IndexError): continue
    return out
def _imb(bids, asks):
    wb = sum(q / (1 + i / 10) for i, (_, q) in enumerate(bids)); wa = sum(q / (1 + i / 10) for i, (_, q) in enumerate(asks)); tot = wb + wa; return (wb - wa) / tot * 100 if tot > 0 else None
def _cvd_windows(trades):
    trades = [t for t in trades if t[0] > 0]
    if not trades: return {"fast": None, "slow": None, "cover": 0.0}
    ref = max(t[0] for t in trades); out = {"cover": (ref - min(t[0] for t in trades)) / 1000}
    for name, win in (("fast", 20), ("slow", 90)):
        cut = ref - win * 1000; sel = [t for t in trades if t[0] >= cut]; buy = sum(q for _, q, b in sel if b); sell = sum(q for _, q, b in sel if not b); tot = buy + sell; out[name] = (buy - sell) / tot * 100 if tot > 0 and len(sel) >= 5 else None
    return out
def parse_lead(raw):
    venues = {}
    def add(name, bids, asks, trades):
        mid = None
        if bids and asks: mid = (max(p for p, _ in bids) + min(p for p, _ in asks)) / 2
        cv = _cvd_windows(trades) if trades else {"fast": None, "slow": None, "cover": 0.0}; venues[name] = {"mid": mid, "imb": _imb(bids, asks) if bids and asks else None, "fast": cv["fast"], "slow": cv["slow"], "cover": cv["cover"]}
    b = raw.get("bn_book"); t = raw.get("bn_tr")
    if isinstance(b, dict) and b.get("bids"):
        trades = [(safe_float(x.get("T")), safe_float(x.get("q")), not x.get("m")) for x in t] if isinstance(t, list) else []; add("BINANCE", _lvls(b.get("bids")), _lvls(b.get("asks")), trades)
    b = ((raw.get("by_book") or {}).get("result") or {}); t = ((raw.get("by_tr") or {}).get("result") or {}).get("list") or []
    if b.get("b"):
        trades = [(safe_float(x.get("time")), safe_float(x.get("size")), x.get("side") == "Buy") for x in t]; add("BYBIT", _lvls(b.get("b")), _lvls(b.get("a")), trades)
    b = ((raw.get("okx_book") or {}).get("data") or [{}]); b = b[0] if b else {}; t = (raw.get("okx_tr") or {}).get("data") or []
    if b.get("bids"):
        trades = [(safe_float(x.get("ts")), safe_float(x.get("sz")), x.get("side") == "buy") for x in t]; add("OKX", _lvls(b.get("bids")), _lvls(b.get("asks")), trades)
    cb = raw.get("cb")
    if isinstance(cb, dict):
        bid, ask, price = safe_float(cb.get("bid")), safe_float(cb.get("ask")), safe_float(cb.get("price")); mid = (bid + ask) / 2 if bid > 0 and ask > 0 else price
        if mid > 0: venues["COINBASE"] = {"mid": mid, "imb": None, "fast": None, "slow": None, "cover": 0.0}
    return venues
def lead_compute(venues, px, ss, now):
    hist = ss.setdefault("pm_lead_hist", {}); acc = {k: [0.0, 0.0] for k in ("ob", "cvd", "sp", "mom")}; rows, calibrating, cal_have = [], False, 0
    for name, d in venues.items():
        mid = d.get("mid"); sp = sp_adj = mom_bps = None
        if mid and px:
            sp = (mid - px) / px * 1e4; h = hist.setdefault(name, []); base_pts = [s for ts, s, _ in h if ts <= now - 15]
            if len(base_pts) >= 20: sp_adj = sp - float(np.median(base_pts))
            else: calibrating = True; cal_have = max(cal_have, len(base_pts))
            past = [(ts, m) for ts, _, m in h if ts <= now - 10]
            if past and now - past[-1][0] <= 25: mom_bps = (mid - past[-1][1]) / mid * 1e4
            h.append((now, sp, mid))
            while h and h[0][0] < now - 900: h.pop(0)
        w = LEAD_W["ob"].get(name)
        if w and d.get("imb") is not None: acc["ob"][0] += w * float(np.tanh(d["imb"] / 30)); acc["ob"][1] += w
        w = LEAD_W["cvd"].get(name)
        if w and (d.get("fast") is not None or d.get("slow") is not None):
            val = (0.6 * np.tanh(d["fast"] / 40) if d.get("fast") is not None else 0.0) + (0.4 * np.tanh(d["slow"] / 40) if d.get("slow") is not None else 0.0); acc["cvd"][0] += w * float(val); acc["cvd"][1] += w
        w = LEAD_W["sp"].get(name)
        if w and sp_adj is not None: acc["sp"][0] += w * float(np.tanh(sp_adj / 2.0)); acc["sp"][1] += w
        if w and mom_bps is not None: acc["mom"][0] += w * float(np.tanh(mom_bps / 2.0)); acc["mom"][1] += w
        rows.append({"المنصة": name, "السعر": round(mid, 2) if mid else None, "فرق عن Index (bps)": round(sp, 2) if sp is not None else None, "الفرق المعدّل (bps)": round(sp_adj, 2) if sp_adj is not None else None, "دفتر الأوامر %": round(d["imb"], 1) if d.get("imb") is not None else None, "CVD 20ث %": round(d["fast"], 1) if d.get("fast") is not None else None, "CVD 90ث %": round(d["slow"], 1) if d.get("slow") is not None else None})
    L = [acc[k][0] / acc[k][1] if acc[k][1] > 0 else 0.0 for k in ("ob", "cvd", "sp", "mom")]; return {"L": L, "rows": rows, "n": len(venues), "calibrating": calibrating, "cal_have": cal_have}
def pm_eff_remaining(r):
    r = max(float(r), 0.0); return (r - 1.0) + 1.0 / 3.0 if r > 1.0 else max(r ** 3 / 3.0, 1e-4)
def pm_features(frame, i, t0, H, e=None, live_price=None, start=None):
    close = frame["close"].to_numpy(float).copy(); vol = frame["vol"].to_numpy(float)
    if live_price: close[i] = float(live_price)
    e_val = float(e) if e is not None else float(i - t0 + 1); r = max(H - e_val, 0.02); start_p = float(start) if start else float(frame["open"].iloc[t0]); lo = max(0, i - 30); rets = np.diff(np.log(close[lo:i+1])); sigma = max(float(rets.std()), 1e-5) if len(rets) >= 5 else 1e-4; z = float(np.clip(np.log(close[i] / start_p) / (sigma * np.sqrt(pm_eff_remaining(r))), -6, 6)); mom3 = float(np.clip(np.log(close[i] / close[max(i-3, 0)]) / (sigma * np.sqrt(3)), -4, 4)); d = np.diff(close[max(0, i-14):i+1]); gain, loss = d[d>0].sum(), -d[d<0].sum(); rsi = 50.0 if (gain+loss)==0 else 100 * gain / (gain+loss); s60 = pd.Series(close[max(0, i-59):i+1]); ema = float(np.clip((s60.ewm(span=9, adjust=False).mean().iloc[-1] - s60.ewm(span=21, adjust=False).mean().iloc[-1]) / (close[i] * sigma), -3, 3)); cvd = volr = 0.0
    if vol[max(0, i-20):i+1].sum() > 0:
        o15 = frame["open"].to_numpy(float)[max(0, i-14):i+1]; c15, v15 = close[max(0, i-14):i+1], vol[max(0, i-14):i+1]; g, rr = v15[c15>o15].sum(), v15[c15<o15].sum(); cvd = float((g - rr) / (g + rr) if (g+rr)>0 else 0.0); prev = max(i-1, 0); volr = float(np.clip(np.log((vol[prev]+1)/(vol[max(0, prev-20):prev].mean()+1)), -2, 2)) if prev>0 else 0.0
    return np.array([z, z*e_val/H, mom3, (rsi-50)/50, ema, cvd, volr, 1.0]), e_val, start_p
def pm_build_dataset(frame, H, offset=0):
    t = frame["time"].to_numpy(float); opens, highs = frame["open"].to_numpy(float), frame["high"].to_numpy(float); lows, closes = frame["low"].to_numpy(float), frame["close"].to_numpy(float); X, y, E, W = [], [], [], []; wid = 0
    for t0 in range(len(t) - H):
        if int(round(t[t0] - offset*60)) % (H*60) != 0: continue
        last = t0 + H - 1
        if abs(t[last] - t[t0] - (H-1)*60) > 1: continue
        start = opens[t0]; settle = (opens[last] + highs[last] + lows[last] + closes[last]) / 4; label = 1.0 if settle > start else 0.0; wid += 1
        for e in range(1, H):
            i = t0 + e - 1
            if i < 35: continue
            x, _, _ = pm_features(frame, i, t0, H); X.append(x); y.append(label); E.append(e); W.append(wid)
    return np.array(X), np.array(y), np.array(E), np.array(W)
def pm_fit(X, y, w0=None, steps=400, lr=0.4, l2=0.05):
    w = (PM_PRIOR if w0 is None else w0).copy(); n = max(len(y), 1)
    for _ in range(steps):
        p = _sig(X @ w); w -= lr * (X.T @ (p - y) / n + l2 * (w - PM_PRIOR))
    return w
def pm_online_step(w, x, y, lr=0.03, l2=0.01):
    p = _sig(float(x @ w)); return w - lr * ((p - y) * x + l2 * (w - PM_PRIOR))
def pm_decide(p_up, payout_up, payout_down, min_edge, min_conf):
    ev_up = p_up * payout_up - (1 - p_up); ev_dn = (1 - p_up) * payout_down - p_up; side, ev = ("UP", ev_up) if ev_up >= ev_dn else ("DOWN", ev_dn); conf = p_up if side == "UP" else 1 - p_up
    if ev < min_edge or conf < min_conf: return "SKIP", ev, conf
    return side, ev, conf
def pm_evaluate(X, y, E, W, payout, min_edge, min_conf):
    cut = np.quantile(W, 0.7); tr, te = W <= cut, W > cut
    if tr.sum() < 50 or te.sum() < 30: return None
    w = pm_fit(X[tr], y[tr]); out = {}
    for name, ww in (("Baseline", PM_PRIOR), ("المتعلم", w)):
        p = _sig(X[te] @ ww); bets = []
        for pi, yi in zip(p, y[te]):
            side, ev, _ = pm_decide(pi, payout, payout, min_edge, min_conf)
            if side == "SKIP": continue
            bets.append(payout if (side == "UP") == (yi == 1.0) else -1.0)
        out[name] = {"accuracy": float(((p>0.5)==(y[te]==1.0)).mean()), "brier": float(((p-y[te])**2).mean()), "bets": len(bets), "bet_win_rate": float(np.mean([b>0 for b in bets])) if bets else 0.0, "pnl_per_bet": float(np.mean(bets)) if bets else 0.0, "pnl_total": float(np.sum(bets))}
    p = _sig(X[te] @ w); conf = np.maximum(p, 1-p); correct = ((p>0.5)==(y[te]==1.0)); rows = []
    for lo_, hi_ in ((0.5,0.6),(0.6,0.7),(0.7,0.8),(0.8,0.9),(0.9,1.01)):
        m = (conf>=lo_) & (conf<hi_)
        if m.sum(): rows.append({"الثقة": f"{lo_:.0%}-{min(hi_,1):.0%}", "عدد": int(m.sum()), "الدقة": f"{correct[m].mean():.1%}"})
    by_e = []
    for e in sorted(set(E[te])):
        m = E[te]==e; by_e.append({"الدقيقة": int(e), "عدد": int(m.sum()), "الدقة": f"{correct[m].mean():.1%}"})
    return {"metrics": out, "calibration": rows, "by_elapsed": by_e, "weights": w, "n_train": int(tr.sum()), "n_test": int(te.sum()), "base_up": float(y[te].mean())}
def pm_window_start(H, offset, now=None):
    now = time.time() if now is None else now; W_sec = H*60; return ((now - offset*60)//W_sec)*W_sec + offset*60

# --- دوال جديدة: Snap-back + الحركة المطلوبة ---
def pm_snapback_detect(ticks, base, px, atr, z, lead, now, window_start):
    if not ticks or atr <= 0 or not base: return None, 0, []
    cyc = [(ts, p) for ts, p in ticks if ts >= window_start]
    if len(cyc) < 5: return None, 0, []
    lo = min(p for _, p in cyc); hi = max(p for _, p in cyc); drop = base - lo; rise = hi - base; reasons = []; hits_up = hits_dn = 0
    if drop > PM_SNAP_ATR_MULT * atr or z < -2.0: hits_up += 1; reasons.append(f"امتداد هبوطي {drop:.2f}$ (~{drop/atr:.1f} ATR)")
    if rise > PM_SNAP_ATR_MULT * atr or z > 2.0: hits_dn += 1; reasons.append(f"امتداد صعودي {rise:.2f}$ (~{rise/atr:.1f} ATR)")
    cvd_fast = None; ob_imb = None
    if lead and lead.get("rows"):
        for r in lead["rows"]:
            if r.get("المنصة") in ("BINANCE", "BYBIT"):
                if r.get("CVD 20ث %") is not None: cvd_fast = r["CVD 20ث %"] if cvd_fast is None else max(cvd_fast, r["CVD 20ث %"])
                if r.get("دفتر الأوامر %") is not None: ob_imb = r["دفتر الأوامر %"] if ob_imb is None else ob_imb + r["دفتر الأوامر %"]
    if cvd_fast is not None and cvd_fast > 15: hits_up += 1; reasons.append(f"CVD قلب موجب {cvd_fast:+.1f}%")
    if cvd_fast is not None and cvd_fast < -15: hits_dn += 1; reasons.append(f"CVD قلب سالب {cvd_fast:+.1f}%")
    if ob_imb is not None and ob_imb > 10: hits_up += 1; reasons.append(f"بيدز متفوقة {ob_imb:+.1f}%")
    if ob_imb is not None and ob_imb < -10: hits_dn += 1; reasons.append(f"أسك متفوقة {ob_imb:+.1f}%")
    if len(cyc) >= 3 and drop > 0:
        rec = (px - lo) / drop * 100
        if rec >= 30: hits_up += 1; reasons.append(f"استرداد {rec:.0f}% من النزول في <60ث")
    if len(cyc) >= 3 and rise > 0:
        rec = (hi - px) / rise * 100
        if rec >= 30: hits_dn += 1; reasons.append(f"استرداد {rec:.0f}% من الصعود في <60ث")
    if hits_up >= PM_SNAP_MIN_HITS: return "UP", hits_up, reasons
    if hits_dn >= PM_SNAP_MIN_HITS: return "DOWN", hits_dn, reasons
    return None, max(hits_up, hits_dn), reasons
def pm_required_move(base, px, remaining_sec, atr, ticks, now):
    if remaining_sec <= 0 or atr <= 0: return {"dist": 0.0, "need_per_sec": 0.0, "cur_per_sec": 0.0, "ratio": 0.0, "feasible": False, "score": 0.0}
    dist = abs(base - px) if px < base else 0.0; need = dist / max(remaining_sec, 1); rec = [(ts, p) for ts, p in ticks if ts >= now - 10]; cur = 0.0
    if len(rec) >= 2: cur = (rec[-1][1] - rec[0][1]) / max(rec[-1][0] - rec[0][0], 1)
    ratio = abs(cur) / need if need > 0 else 99.0; score = dist / (max(remaining_sec, 1) * atr) if atr > 0 else 0.0
    return {"dist": dist, "need_per_sec": need, "cur_per_sec": cur, "ratio": ratio, "score": score, "feasible": ratio >= 1.0 or dist == 0.0}

def pm_live_state(H, offset, payout_up, payout_down, min_edge, min_conf, cutoff_sec, auto_log, opts):
    ss = st.session_state; px, src, latency = get_live_index()
    if px is None: return {"error": "تعذر جلب السعر اللحظي من MEXC/Bybit."}
    now = time.time(); ticks = ss.setdefault("pm_ticks", []); ticks.append((now, px)); del ticks[:-4000]
    if ss.get("pm_frame") is None or now - ss.get("pm_frame_ts", 0) > 20:
        frame, fsrc = get_pm_frame()
        if frame is not None: ss["pm_frame"], ss["pm_frame_ts"], ss["pm_frame_src"] = frame, now, fsrc
    frame = ss.get("pm_frame")
    if frame is None: return {"error": "تعذر جلب شموع الدقيقة."}
    W_sec = H * 60; t0_time = pm_window_start(H, offset, now); t = frame["time"].to_numpy(float); idx0 = np.where(np.abs(t - t0_time) < 1)[0]
    if len(idx0) == 0: return {"error": "شمعة بداية الدورة مش في البيانات لسه؛ استنى ثواني."}
    t0, i = int(idx0[0]), len(frame) - 1; manual = ss.get("pm_base_manual")
    if manual and abs(manual[0] - t0_time) < 1 and manual[1] > 0: base, base_src = float(manual[1]), "يدوي من شاشة MEXC ✅"
    else:
        near = [p for (ts, p) in ticks if t0_time <= ts <= t0_time + 4]
        if near: base, base_src = near[0], "لحظي من التطبيق (أول Tick في الدورة)"
        else: base, base_src = float(frame["open"].iloc[t0]), "تقدير من افتتاح شمعة الدقيقة ⚠️"
    e = (now - t0_time) / 60; remaining = H * 60 - (now - t0_time)
    if e < 0.1: return {"error": "الدورة لسه بادئة؛ استنى ثواني."}
    running_avg, eff_px = None, px
    if remaining <= 60:
        pts = [p for ts, p in ticks if ts >= t0_time + W_sec - 60]
        if len(pts) >= 3:
            running_avg = float(np.mean(pts)); a = 1 - remaining / 60.0; eff_px = a * running_avg + (1 - a) * px
    lead, adj = None, 0.0
    if opts.get("use_lead", True):
        cached = ss.get("pm_lead_cache")
        if cached and now - cached[0] < 1.0: venues, lat_l = cached[1], cached[2]
        else:
            raw, lat_l = lead_fetch(); venues = parse_lead(raw); ss["pm_lead_cache"] = (now, venues, lat_l)
        lead = lead_compute(venues, px, ss, now); lead["lat"] = lat_l; wl, nl = pm_load_vec(100 + H, LEAD_PRIOR); Lv = np.array(lead["L"], dtype=float); mult = float(opts.get("lead_mult", 1.0)); adj = float((Lv * wl).sum() * mult); lead.update({"adj": adj, "n_updates": nl, "w": wl, "mult": mult})
    x, e, _ = pm_features(frame, i, t0, H, e=e, live_price=eff_px, start=base); w, n_upd = pm_load(H); p_base = float(_sig(x @ w)); p_up = float(_sig(float(x @ w) + adj)); side, ev, conf = pm_decide(p_up, payout_up, payout_down, min_edge, min_conf); gate = None
    if side != "SKIP" and lead and lead["n"] > 0 and opts.get("require_agree", True):
        d = 1 if side == "UP" else -1
        if abs(adj) >= 0.25 and np.sign(adj) != d: side, gate = "SKIP", "تعارض مع المؤشرات القائدة"
    if side != "SKIP" and latency > opts.get("max_latency", 2.5): side, gate = "SKIP", "تأخر بيانات السعر"
    closed = remaining < cutoff_sec; stake = 0.0
    if side != "SKIP":
        b = payout_up if side == "UP" else payout_down; kelly = (conf * b - (1 - conf)) / b; stake = float(np.clip(kelly * 0.25, 0, 0.05))
    # --- ATR للـ Snap-back ---
    try:
        fr2 = add_indicators(frame); atr_val = float(fr2["atr"].iloc[-2]) if len(fr2) >= 3 else float(px * 0.004)
        if atr_val <= 0: atr_val = float(px * 0.004)
    except Exception: atr_val = float(px * 0.004)
    snap_dir, snap_hits, snap_reasons = pm_snapback_detect(ticks, base, px, atr_val, float(x[0]), lead, now, t0_time)
    req_move = pm_required_move(base, px, remaining, atr_val, ticks, now)
    # --- 1) Hysteresis + تأكيد 3 قراءات + قفل الإشارة - متركبة هنا ---
    st_key = f"pm_hyst_{t0_time}"; stt = ss.setdefault(st_key, {"locked": None, "pending": None, "count": 0})
    if stt["locked"] == "UP":
        cand = "UP" if p_up > PM_HYST_EXIT_UP else "DOWN" if p_up < 0.20 else "UP"
        if p_up < 0.20 and snap_dir == "DOWN": cand = "DOWN"
    elif stt["locked"] == "DOWN":
        cand = "DOWN" if p_up < PM_HYST_EXIT_DOWN else "UP" if p_up > PM_HYST_ENTER_UP else "DOWN"
        if p_up > 0.80 and snap_dir == "UP": cand = "UP"
    else:
        cand = "UP" if p_up >= PM_HYST_ENTER_UP else ("DOWN" if p_up <= PM_HYST_ENTER_DOWN else "SKIP")
    if cand == stt["pending"]: stt["count"] += 1
    else: stt["pending"] = cand; stt["count"] = 1
    confirmed = stt["count"] >= PM_CONFIRM_N
    confirming = False
    if confirmed and cand in ("UP", "DOWN"):
        stt["locked"] = cand; side = cand
    elif stt["locked"] in ("UP", "DOWN"):
        side = stt["locked"]
    else:
        side = "SKIP"; confirming = True
    # لو Snap-back قوي وعكس القفل + p قوي جدا، اسمح بالقلب
    if snap_dir and stt["locked"] and snap_dir != stt["locked"] and ((snap_dir == "UP" and p_up > PM_STRONG_FLIP_P) or (snap_dir == "DOWN" and p_up < 1 - PM_STRONG_FLIP_P)):
        if stt["count"] >= PM_CONFIRM_N: stt["locked"] = snap_dir; side = snap_dir
    logged = False
    if auto_log and side != "SKIP" and not closed:
        with db() as conn:
            dup = conn.execute("SELECT 1 FROM pm_predictions WHERE horizon=? AND window_start=?", (H, t0_time)).fetchone()
            if not dup:
                lead_js = json.dumps({"L": [float(v) for v in lead["L"]], "mult": lead["mult"]}) if lead else None
                conn.execute("""INSERT INTO pm_predictions (created_at,horizon,window_start,decision_min,start_price,price_now,p_up,side,payout_up,payout_down,ev,features,lead) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (datetime.now(timezone.utc).isoformat(), H, t0_time, e, base, px, p_up, side, payout_up, payout_down, ev, json.dumps([float(v) for v in x]), lead_js)); logged = True
    chart = [(datetime.fromtimestamp(ts, CAIRO).strftime("%H:%M:%S"), p) for ts, p in ticks if ts >= t0_time]
    return {"p_up": p_up, "p_base": p_base, "side": side, "ev": ev, "conf": conf, "e": e, "remaining": remaining, "base": base, "base_src": base_src, "px": px, "src": src, "latency": latency, "z": float(x[0]), "closed": closed, "n_updates": n_upd, "n_ticks": len(ticks), "running_avg": running_avg, "eff_px": eff_px, "logged": logged, "lead": lead, "gate": gate, "stake": stake, "ends_at": datetime.fromtimestamp(t0_time + W_sec, CAIRO).strftime("%H:%M:%S"), "now": now_cairo().strftime("%H:%M:%S"), "chart": chart, "window_start": t0_time, "H": H, "snap_dir": snap_dir, "snap_hits": snap_hits, "snap_reasons": snap_reasons, "req_move": req_move, "confirming": confirming, "confirm_count": stt["count"], "locked": stt["locked"], "atr_val": atr_val}
def pm_resolve_open():
    with db() as conn: rows = conn.execute("SELECT id,horizon,window_start,start_price,side,payout_up,payout_down,p_up,features,lead FROM pm_predictions WHERE outcome='OPEN'").fetchall()
    now = time.time(); due = [r for r in rows if r[2] + r[1] * 60 + 20 <= now]
    if not due: return 0
    frame, _ = get_pm_frame()
    if frame is None: return 0
    t = frame["time"].to_numpy(float); ticks = st.session_state.get("pm_ticks", []); done = 0
    for sid, H, ws, start, side, pu, pd_, p_up, feats, lead_js in due:
        end_t = ws + H * 60; pts = [p for ts, p in ticks if end_t - 60 <= ts <= end_t]
        if len(pts) >= 8: settle = float(np.mean(pts))
        else:
            idx = np.where(np.abs(t - (ws + (H - 1) * 60)) < 1)[0]
            if len(idx) == 0:
                if now - ws > 7200:
                    with db() as conn: conn.execute("UPDATE pm_predictions SET outcome='EXPIRED' WHERE id=?", (sid,))
                continue
            k = idx[0]; settle = float((frame["open"].iloc[k] + frame["high"].iloc[k] + frame["low"].iloc[k] + frame["close"].iloc[k]) / 4)
        up = settle > start; model_correct = int((p_up > 0.5) == up); correct = int((side == "UP") == up) if side != "SKIP" else None; pnl = ((pu if side == "UP" else pd_) if correct else -1.0) if side != "SKIP" else 0.0; y = 1.0 if up else 0.0; xv = np.array(json.loads(feats), dtype=float); w, n_upd = pm_load(H)
        if lead_js:
            try:
                ld = json.loads(lead_js); Lv, mult = np.array(ld["L"], dtype=float), float(ld.get("mult", 1.0)); wl, nl = pm_load_vec(100 + H, LEAD_PRIOR); p_l = float(_sig(float(xv @ w) + float((Lv * wl).sum() * mult))); wl = wl - 0.05 * ((p_l - y) * Lv * mult + 0.01 * (wl - LEAD_PRIOR)); pm_save_vec(100 + H, np.clip(wl, -0.3, 2.0), nl + 1)
            except Exception: pass
        w = pm_online_step(w, xv, y); pm_save(H, w, n_upd + 1)
        with db() as conn: conn.execute("UPDATE pm_predictions SET outcome=?,end_price=?,correct=?,model_correct=?,pnl=? WHERE id=?", ("UP" if up else "DOWN", settle, correct, model_correct, pnl, sid))
        done += 1
    return done
def render_pm_section(tg_enabled):
    st.subheader("🎯 MEXC Up/Down — BTC"); st.caption("Up يكسب لو سعر التسوية > Baseline، والتساوي = Down. التسوية = متوسط Index آخر دقيقة.")
    with st.expander("⚙️ الإعدادات", expanded=False):
        c1, c2, c3 = st.columns(3); pm_h = 5 if c1.selectbox("الدورة", ["5 دقائق", "15 دقيقة"]) == "5 دقائق" else 15; pm_pu = c2.number_input("Payout لـ Up", min_value=0.1, max_value=5.0, value=0.85, step=0.01); pm_pd = c3.number_input("Payout لـ Down", min_value=0.1, max_value=5.0, value=0.85, step=0.01)
        c4, c5, c6 = st.columns(3); pm_edge = c4.slider("أقل ميزة EV", 0.0, 0.5, 0.08, 0.01); pm_conf = c5.slider("أقل ثقة", 0.50, 0.95, 0.62, 0.01); pm_off = c6.number_input("إزاحة بداية الدورة", min_value=0, max_value=14, value=0, step=1)
        c7, c8, c9 = st.columns(3); pm_cut = c7.number_input("قفل الدخول قبل النهاية (ثواني)", min_value=0, max_value=120, value=15, step=5); pm_live_on = c8.checkbox("⚡ تحديث لحظي كل ثانيتين", value=True, key="pm_live_on"); pm_auto = c9.checkbox("تسجيل تلقائي", value=True)
        c10, c11, c12 = st.columns(3); use_lead = c10.checkbox("🧭 استخدم المؤشرات القائدة", value=True); lead_mult = c11.slider("قوة المؤشرات القائدة", 0.0, 2.0, 1.0, 0.1); require_agree = c12.checkbox("امنع الدخول عند التعارض", value=True); pm_tg = st.checkbox("📡 أرسل إشارة إلى Telegram", value=False)
    st.caption(f"نقطة التعادل: Up ≥ {1/(1+pm_pu):.1%} | Down ≥ {1/(1+pm_pd):.1%}")
    b1, b2 = st.columns([3, 1]); base_in = b1.number_input("Baseline من شاشة MEXC", min_value=0.0, value=0.0, step=0.01, format="%.2f"); b2.write("")
    if b2.button("📌 ثبّت للدورة الحالية"): st.session_state["pm_base_manual"] = (pm_window_start(pm_h, pm_off), base_in); st.toast("تم تثبيت Baseline")
    _now_pm = time.time()
    if _now_pm - st.session_state.get("pm_resolve_ts", 0) > 15:
        st.session_state["pm_resolve_ts"] = _now_pm
        try:
            if pm_resolve_open(): st.toast("اتحسمت توقعات وتم تحديث النموذج")
        except Exception as exc: st.caption(f"تعذر حسم التوقعات: {exc}")
    manual_click = (not pm_live_on) and st.button("🎯 توكمل من نفس النقطة اللي وقفنا عندها — باقي دالة `render_pm_section` وباقي التطبيق، الصقها بعد السطر الأخير اللي وصلتله:

```python
    manual_click = (not pm_live_on) and st.button("🎯 توقّع الآن", type="primary")
    opts = {"use_lead": use_lead, "lead_mult": lead_mult, "require_agree": require_agree, "max_latency": 2.5}
    live = None
    if pm_live_on:
        live = pm_live_state(pm_h, pm_off, pm_pu, pm_pd, pm_edge, pm_conf, pm_cut, pm_auto, opts)
        st.markdown('<div class="live-dot"></div>', unsafe_allow_html=True)
    elif manual_click:
        live = pm_live_state(pm_h, pm_off, pm_pu, pm_pd, pm_edge, pm_conf, pm_cut, pm_auto, opts)

    if live is None:
        st.info("فعّل التحديث اللحظي أو اضغط توقّع الآن.")
        return
    if live.get("error"):
        st.error(live["error"])
        return

    # --- عرض Snap-back + التأكيد + القفل + الحركة المطلوبة ---
    if live.get("snap_dir"):
        st.warning(f"🚨 انعكاس {'صاعد ⬆️' if live['snap_dir']=='UP' else 'هابط ⬇️'} — Snap-back / Exhaustion ({live.get('snap_hits',0)}/4): " + " • ".join(live.get("snap_reasons", [])[:4]))
    if live.get("confirming"):
        st.info(f"⏳ الإشارة بتتأكد ({live.get('confirm_count',0)}/3) — لسه مش مؤكدة")
    if live.get("locked"):
        st.caption(f"🔒 إشارة مقفولة جوه الدورة: {live['locked']}")
    rm = live.get("req_move", {})
    if rm:
        st.caption(f"📏 الحركة المطلوبة: باقي {rm.get('dist',0):.2f}$ | مطلوب {rm.get('need_per_sec',0):.3f}$/ث | الحالي {rm.get('cur_per_sec',0):+.3f}$/ث | {'✅ قابلة للتحقق' if rm.get('feasible') else '❌ صعبة'}")

    side = live["side"]
    tone = "up" if side == "UP" else "down" if side == "DOWN" else "neutral"
    label = "⬆️ UP" if side == "UP" else "⬇️ DOWN" if side == "DOWN" else "⏸️ SKIP"
    decision_card(label, tone,
        f"الدورة تنتهي {live['ends_at']} | الآن {live['now']} | Baseline {live['base']:.2f} ({live['base_src']})",
        [("p(UP)", f"{live['p_up']:.1%}"), ("EV", f"{live['ev']:+.2f}"), ("الثقة", f"{live['conf']:.0%}"), ("المتبقي", f"{int(live['remaining'])}ث")])
    if live.get("gate"):
        st.warning(f"⛔ تم الحجب: {live['gate']}")
    if live.get("stake"):
        st.caption(f"💰 حجم مقترح (Kelly جزئي): {live['stake']:.1%} من المحفظة — إدارة رأس مال فقط، مش نصيحة.")
    if live.get("lead"):
        L = live["lead"]
        st.caption(f"🧭 المؤشرات القائدة — تعديل الاحتمال: {L.get('adj',0):+.2f} | منصات: {L.get('n',0)} | تأخير: {L.get('lat',0):.2f}ث")
        for i, name in enumerate(LEAD_NAMES):
            gauge(LEAD_LABELS[i], float(L["L"][i]), f"{float(L['L'][i]):+.2f}")
        if L.get("rows"):
            show_df(pd.DataFrame(L["rows"]))
        if L.get("calibrating"):
            st.caption(f"⏳ معايرة فرق السعر شغالة... جمعنا {L.get('cal_have',0)} نقطة من 20.")
    if live.get("chart"):
        st.line_chart(pd.DataFrame(live["chart"], columns=["الوقت", "السعر"]).set_index("الوقت"))
    if pm_tg and side != "SKIP" and not live.get("closed"):
        if st.button("📡 أرسل إشارة Up/Down للتيليجرام", key=f"pm_tg_{live['window_start']}"):
            ok, msg = send_telegram(f"{'⬆️ UP' if side=='UP' else '⬇️ DOWN'} — BTC MEXC Up/Down\np(UP)={live['p_up']:.1%} | EV={live['ev']:+.2f}\nBaseline: {live['base']:.2f}\nالسعر الآن: {live['px']:.2f}\nينتهي: {live['ends_at']}\n@WHYNOTBLY7")
            st.success(msg) if ok else st.error(msg)
    if pm_live_on:
        time.sleep(2)
        st.rerun()

# ============================ الواجهة الرئيسية ============================
init_db()
radar_init()
pm_init()

with st.sidebar:
    st.markdown("### ⚙️ إعدادات عامة")
    capital = st.number_input("رأس المال (USDT)", min_value=10.0, value=100.0, step=10.0)
    risk_pct = st.slider("نسبة المخاطرة %", 0.1, 5.0, 1.0, 0.1)
    fee_pct = st.number_input("العمولة %", min_value=0.0, value=0.10, step=0.01)
    slip_pct = st.number_input("الانزلاق %", min_value=0.0, value=0.05, step=0.01)
    st.caption("الإشارات بحثية فقط — إدارة رأس المال مسئوليتك.")

settings = {"capital_usdt": capital, "risk_pct": risk_pct, "fee_pct": fee_pct, "slippage_pct": slip_pct,
            "want_long": True, "want_short": True, "use_fvg": True, "killzone": False,
            "mtf_filter": False, "btc_filter": False, "funding_filter": False, "wall_filter": False,
            "confirm_exchanges": False, "min_score": 60, "timeframe": "1h"}

tab_scan, tab_radar, tab_pm, tab_hist, tab_bt = st.tabs(["🔍 الماسح", "📡 رادار Pump/Dump", "🎯 MEXC Up/Down", "📚 السجل", "🧪 باكتست"])

with tab_scan:
    st.subheader("🔍 ماسح Futures")
    c1, c2, c3 = st.columns(3)
    platform = c1.selectbox("المنصة", ["BINANCE", "BYBIT", "KUCOIN", "MEXC"])
    tf = c2.selectbox("الفريم", ["1h", "15m", "5m", "1m", "4h", "3m"], index=0)
    min_score = c3.slider("أقل Score", 50, 90, 60, 1)
    settings["min_score"] = min_score
    settings["timeframe"] = tf
    if st.button("🚀 افحص الآن", type="primary"):
        res = run_scan(platform, settings, 60, tf, 200)
        st.session_state["last_scan"] = res
        if res.get("signals"):
            save_signals(res["signals"], platform)
    render_scan_results("last_scan", min_score, True)
    mon = get_monitor_status()
    if mon.get("resolved"):
        st.success(f"تم حسم {len(mon['resolved'])} صفقة تلقائياً.")
        show_df(pd.DataFrame(mon["resolved"]))

with tab_radar:
    st.subheader("📡 رادار Pump/Dump")
    c1, c2 = st.columns(2)
    r_plat = c1.selectbox("منصة الرادار", ["【entity-BINANCE¦canonical_name=BINANCE】", "【entity-BYBIT¦canonical_name=BYBIT】", "【entity-KUCOIN¦canonical_name=KUCOIN】", "MEXC"], key="r_plat")
    r_tf = c2.selectbox("فريم الرادار", ["15m", "5m", "1h"], key="r_tf")
    if st.button("📡 شغّل الرادار", type="primary", key="run_radar"):
        radar_evaluate()
        res = run_radar(r_plat, 60, r_tf, 12)
        st.session_state["last_radar"] = res
        if res.get("rows"):
            radar_log_alerts(res["rows"], r_plat, 60)
    res = st.session_state.get("last_radar")
    if res and res.get("rows"):
        st.caption(f"آخر فحص: {res.get('ts','')} | فحصنا {res.get('scanned',0)} عملة")
        for i, item in enumerate(res["rows"]):
            render_radar_card(item, f"rd_{i}", r_plat, 60)
    elif res and res.get("error"):
        st.error(res["error"])

with tab_pm:
    render_pm_section(True)

with tab_hist:
    st.subheader("📚 سجل الإشارات")
    hist = load_signal_history(200)
    if not hist.empty:
        show_df(hist)
        st.caption(f"إجمالي المعروض: {len(hist)}")
    else:
        st.info("مفيش إشارات مسجلة لسه.")
    st.divider()
    st.subheader("📚 سجل Up/Down")
    with db() as conn:
        try:
            pm_hist = pd.read_sql_query("SELECT * FROM pm_predictions ORDER BY id DESC LIMIT 100", conn)
        except Exception:
            pm_hist = pd.DataFrame()
    if not pm_hist.empty:
        show_df(pm_hist)
    else:
        st.info("مفيش توقعات Up/Down مسجلة لسه.")

with tab_bt:
    st.subheader("🧪 باكتست سريع")
    st.caption("بيختبر استراتيجية الماسح على بيانات تاريخية — للتقييم فقط.")
    c1, c2 = st.columns(2)
    bt_sym = c1.text_input("الرمز", value="BTCUSDT")
    bt_plat = c2.selectbox("منصة الباكتست", ["BINANCE", "BYBIT", "KUCOIN", "MEXC"], key="bt_plat")
    if st.button("▶️ شغّل الباكتست"):
        fr = KLINE_SOURCES[bt_plat](bt_sym, "1h", 500)
        if fr is None:
            st.error("تعذر جلب الشموع للباكتست.")
        else:
            trades = run_backtest(fr, settings)
            if trades.empty:
                st.info("مفيش صفقات في الباكتست بالفلاتر الحالية.")
            else:
                show_df(trades)
                wins = (trades["outcome"] == "WIN").mean() * 100
                st.metric("نسبة الفوز في الباكتست", f"{wins:.1f}%")
                st.metric("إجمالي R", f"{trades['R'].sum():.2f}")
