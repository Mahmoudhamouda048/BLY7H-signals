# BLY7TRADER — V19 interface / Futures intelligence
# Run: pip install -r requirements.txt && streamlit run BLY7TRADER.py
# Notes:
# - CVD below is candle-direction volume proxy, NOT trade-level CVD.
# - Cross-exchange check verifies spot symbol availability, not futures direction.
# - Signals are research alerts, not guaranteed predictions or financial advice.

import os
import json
import time
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="BLY7TRADER ULTIMATE V19",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_TITLE = "💎 BLY7TRADER — ULTIMATE V19"
DB_PATH = os.getenv("BLY7TRADER_DB", "bly7trader_memory.db")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BLY7TRADER/19.2"})
TIMEOUT = 8
STABLES = {"USDCUSDT", "BUSDUSDT", "DAIUSDT", "FDUSDUSDT", "USDEUSDT"}
CAIRO = ZoneInfo("Africa/Cairo")

st.markdown(
    f"""
    <h1 style="text-align:center">{APP_TITLE}</h1>
    <p style="text-align:center">
    BLY7TRADER | ماسح عقود Futures حقيقية + ذاكرة دائمة وتعلّم من نتائج الصفقات
    </p>
    """,
    unsafe_allow_html=True,
)


# ----------------------------- Utilities -----------------------------

def api_json(url, params=None):
    """GET JSON with basic validation; return None on network/API errors."""
    try:
        response = SESSION.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("code") not in (None, "200000", 200, 0, "0", "00000"):
            return None
        return payload
    except (requests.RequestException, ValueError, TypeError):
        return None


def safe_float(value, default=0.0):
    try:
        result = float(value)
        return result if pd.notna(result) else default
    except (TypeError, ValueError):
        return default


def clamp_entry(entry, price, is_long):
    if price <= 0:
        return entry
    if abs(entry - price) / price * 100 > 1.5:
        return price * (0.997 if is_long else 1.003)
    return entry


def now_cairo():
    return datetime.now(CAIRO)


def killzone_status():
    # Approximate Cairo-time windows. London/NY DST shifts mean these are
    # configurable reference windows, not an exchange-session guarantee.
    current = now_cairo()
    minutes = current.hour * 60 + current.minute
    if 10 * 60 <= minutes <= 12 * 60:
        return True, "نافذة لندن التقريبية"
    if 15 * 60 + 30 <= minutes <= 17 * 60 + 30:
        return True, "نافذة نيويورك التقريبية"
    return False, "خارج النوافذ المحددة"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
            exchange TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
            score INTEGER NOT NULL, price REAL NOT NULL, entry REAL NOT NULL,
            stop REAL NOT NULL, tp1 REAL NOT NULL, tp2 REAL NOT NULL,
            change_pct REAL NOT NULL, volume_ratio REAL NOT NULL,
            cvd_proxy REAL NOT NULL, outcome TEXT DEFAULT 'OPEN')""")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(signals)")}
        additions = {
            "tp3": "REAL", "closed_at": "TEXT", "pnl_pct": "REAL",
            "result_source": "TEXT", "funding_pct": "REAL", "oi_change_pct": "REAL",
            "market_type": "TEXT DEFAULT 'FUTURES'"
        }
        for name, declaration in additions.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE signals ADD COLUMN {name} {declaration}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_outcome ON signals(outcome)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at)")
        conn.commit()


def update_trade_outcome(signal_id, outcome):
    if outcome not in ("WIN", "LOSS", "BREAKEVEN", "OPEN"):
        return
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT side, price, entry, stop, tp1 FROM signals WHERE id=?", (signal_id,)).fetchone()
        if not row:
            return
        side, price, entry, stop, tp1 = row
        pnl = ((tp1-entry)/entry*100) if side == "LONG" else ((entry-tp1)/entry*100)
        if outcome == "LOSS":
            pnl = ((stop-entry)/entry*100) if side == "LONG" else ((entry-stop)/entry*100)
        elif outcome in ("OPEN", "BREAKEVEN"):
            pnl = 0.0
        closed = None if outcome == "OPEN" else datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE signals SET outcome=?, closed_at=?, pnl_pct=?, result_source='MANUAL' WHERE id=?",
                     (outcome, closed, pnl, signal_id))
        conn.commit()


def learning_profile():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT exchange, side, score, outcome FROM signals WHERE outcome IN ('WIN','LOSS','BREAKEVEN')", conn)
    if df.empty:
        return {"trades": 0, "win_rate": 0.0, "adjustment": 0, "by_side": {}}
    decided = df[df.outcome.isin(["WIN", "LOSS"])]
    win_rate = (decided.outcome == "WIN").mean() * 100 if not decided.empty else 0.0
    by_side = {}
    for side, group in df.groupby("side"):
        decided_side = group[group.outcome.isin(["WIN", "LOSS"])]
        by_side[side] = {"trades": len(group), "win_rate": round((decided_side.outcome == "WIN").mean()*100, 1) if len(decided_side) else 0.0}
    # Conservative Bayesian adjustment; only activates after 10 resolved trades.
    adjustment = max(-8, min(8, round((win_rate - 50) * min(len(decided)/30, 1) * 0.16))) if len(decided) >= 10 else 0
    return {"trades": len(df), "win_rate": round(win_rate, 1), "adjustment": adjustment, "by_side": by_side}


def save_signals(signals, exchange):
    if not signals:
        return
    stamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        for signal in signals:
            # Prevent duplicate snapshots of the same symbol/side within 20 minutes.
            exists = conn.execute("SELECT 1 FROM signals WHERE exchange=? AND symbol=? AND side=? AND created_at>=? LIMIT 1",
                (exchange, signal["symbol"], signal["type"], (datetime.now(timezone.utc)-pd.Timedelta(minutes=20)).isoformat())).fetchone()
            if exists:
                continue
            conn.execute("""INSERT INTO signals
                (created_at, exchange, symbol, side, score, price, entry, stop, tp1, tp2,
                 change_pct, volume_ratio, cvd_proxy, outcome, tp3, funding_pct, oi_change_pct, market_type)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'OPEN',?,?,?,'FUTURES')""",
                (stamp, exchange, signal["symbol"], signal["type"], signal["score"],
                 signal["price"], signal["entry"], signal["stop"], signal["tp1"], signal["tp2"],
                 signal["ch"], signal["vol"], signal["buy"], signal.get("tp3"),
                 signal.get("funding"), signal.get("oi_change")))
        conn.commit()


def load_signal_history(limit=100):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT * FROM signals ORDER BY id DESC LIMIT ?",
            conn,
            params=(limit,),
        )


def send_telegram(message):
    token = st.secrets.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_id = st.secrets.get(
        "TELEGRAM_CHANNEL_ID",
        st.secrets.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID", "")),
    )
    if not token:
        return False, "أضف TELEGRAM_BOT_TOKEN داخل Streamlit Secrets"
    if not chat_id:
        return False, "أضف TELEGRAM_CHANNEL_ID أو TELEGRAM_CHAT_ID داخل Secrets"
    try:
        response = SESSION.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
            timeout=15,
        )
        data = response.json()
        if response.ok and data.get("ok"):
            return True, "تم الإرسال"
        return False, data.get("description", f"Telegram HTTP {response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        return False, str(exc)


def format_telegram(signal):
    side = "🚀 LONG" if signal["type"] == "LONG" else "📉 SHORT"
    return (
        f"{side} — {signal['symbol']}\n"
        f"⭐ Score: {signal['score']}/100\n"
        f"💵 السعر: {signal['price']}\n"
        f"🎯 الدخول المقترح: {signal['entry']}\n"
        f"⛔ وقف الخسارة: {signal['stop']}\n"
        f"✅ TP1: {signal['tp1']}\n"
        f"🏆 TP2: {signal['tp2']}\n"
        f"🎯 TP3: {signal.get('tp3', '—')}\n"
        f"📈 تغير آخر ساعة: {signal['ch']}%\n"
        f"📦 حجم التداول: x{signal['vol']}\n"
        f"📊 CVD proxy: {signal['buy']}%\n"
        f"{signal['extra']}\n"
        "@WHYNOTBLY7"
    )


def send_signal_batch(signals):
    sent, errors = 0, []
    for signal in sorted(signals, key=lambda item: item["score"], reverse=True)[:5]:
        ok, message = send_telegram(format_telegram(signal))
        if ok:
            sent += 1
        else:
            errors.append(message)
        time.sleep(0.4)
    if sent:
        st.success(f"📡 تم إرسال {sent} إشارة إلى تليجرام")
    if errors and not sent:
        st.error(f"تعذر الإرسال: {errors[-1]}")


# ----------------------------- Market data -----------------------------

def get_kucoin_symbols(limit=100):
    payload = api_json("https://api.kucoin.com/api/v1/market/allTickers")
    tickers = (payload or {}).get("data", {}).get("ticker", [])
    rows = [
        item for item in tickers
        if item.get("symbol", "").endswith("-USDT")
    ]
    rows.sort(key=lambda item: safe_float(item.get("volValue")), reverse=True)
    return [item["symbol"] for item in rows[:limit]]


def get_kucoin_klines(symbol):
    end = int(time.time())
    start = end - 110 * 3600
    payload = api_json(
        "https://api.kucoin.com/api/v1/market/candles",
        {"type": "1hour", "symbol": symbol, "startAt": start, "endAt": end},
    )
    data = (payload or {}).get("data", [])
    if len(data) < 30:
        return None
    # KuCoin order: time, open, close, high, low, volume, turnover
    frame = pd.DataFrame(
        data, columns=["time", "open", "close", "high", "low", "vol", "turnover"]
    )
    for column in ("open", "close", "high", "low", "vol"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("time").dropna().reset_index(drop=True)


def aggregate_3m(frame):
    if frame is None or frame.empty: return frame
    f=frame.copy()
    f["bucket"]=(pd.to_numeric(f["time"],errors="coerce")//180).astype("Int64")
    return f.groupby("bucket",dropna=True).agg(time=("time","first"),open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),vol=("vol","sum")).reset_index(drop=True)


def get_kucoin_futures_symbols(limit=100):
    payload = api_json("https://api-futures.kucoin.com/api/v1/contracts/active")
    rows = (payload or {}).get("data", [])
    rows = [x for x in rows if x.get("quoteCurrency") == "USDT" and x.get("symbol", "").endswith("USDTM") and x.get("isQuanto") is False]
    rows.sort(key=lambda x: safe_float(x.get("turnoverOf24h")), reverse=True)
    return [x["symbol"] for x in rows[:limit]]


def get_kucoin_futures_klines(symbol, timeframe="1h", limit=500):
    end = int(time.time())
    granularity = {"1m":1,"3m":1,"5m":5,"15m":15,"1h":60,"4h":240}.get(timeframe,60)
    multiplier = 3 if timeframe == "3m" else 1
    start = end - limit*granularity*60*multiplier
    payload = api_json("https://api-futures.kucoin.com/api/v1/kline/query",
                       {"symbol":symbol,"granularity":granularity,"from":start,"to":end})
    rows = (payload or {}).get("data", [])
    if len(rows) < 30: return None
    frame = pd.DataFrame(rows, columns=["time","open","high","low","close","vol","turnover"])
    for c in ("open","high","low","close","vol"): frame[c] = pd.to_numeric(frame[c], errors="coerce")
    frame=frame.sort_values("time").dropna().reset_index(drop=True)
    return aggregate_3m(frame) if timeframe == "3m" else frame


def get_binance_futures_symbols(limit=100):
    payload = api_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
    if not isinstance(payload, list): return []
    rows = [x for x in payload if x.get("symbol", "").endswith("USDT") and x.get("symbol") not in STABLES]
    rows.sort(key=lambda x: safe_float(x.get("quoteVolume")), reverse=True)
    return [x["symbol"] for x in rows[:limit]]


def get_binance_futures_klines(symbol, timeframe="1h", limit=500):
    payload = api_json("https://fapi.binance.com/fapi/v1/klines", {"symbol": symbol, "interval": timeframe, "limit": min(int(limit),1000)})
    if not isinstance(payload, list) or len(payload) < 30: return None
    frame = pd.DataFrame(payload, columns=["ot","open","high","low","close","vol","ct","qav","trades","tb","tq","ignore"])
    for c in ("open","high","low","close","vol"): frame[c] = pd.to_numeric(frame[c], errors="coerce")
    return frame.dropna().reset_index(drop=True)


def get_bybit_futures_symbols(limit=100):
    payload = api_json("https://api.bybit.com/v5/market/tickers", {"category":"linear"})
    rows = (payload or {}).get("result", {}).get("list", [])
    rows = [x for x in rows if x.get("symbol", "").endswith("USDT")]
    rows.sort(key=lambda x: safe_float(x.get("turnover24h")), reverse=True)
    return [x["symbol"] for x in rows[:limit]]


def get_bybit_futures_klines(symbol, timeframe="1h", limit=500):
    payload = api_json("https://api.bybit.com/v5/market/kline", {"category":"linear", "symbol":symbol, "interval":{"1m":"1","3m":"3","5m":"5","15m":"15","1h":"60","4h":"240"}.get(timeframe,"60"), "limit":min(int(limit),1000)})
    rows = (payload or {}).get("result", {}).get("list", [])
    if len(rows) < 30: return None
    frame = pd.DataFrame(rows, columns=["time","open","high","low","close","vol","turnover"])
    for c in ("open","high","low","close","vol"): frame[c] = pd.to_numeric(frame[c], errors="coerce")
    return frame.sort_values("time").reset_index(drop=True)


def get_mexc_futures_symbols(limit=100):
    payload = api_json("https://contract.mexc.com/api/v1/contract/ticker")
    rows = (payload or {}).get("data", [])
    rows = [x for x in rows if x.get("symbol", "").endswith("_USDT")]
    rows.sort(key=lambda x: safe_float(x.get("amount24")), reverse=True)
    return [x["symbol"] for x in rows[:limit]]


def get_mexc_futures_klines(symbol, timeframe="1h", limit=500):
    gran={"1m":"Min1","3m":"Min1","5m":"Min5","15m":"Min15","1h":"Min60","4h":"Hour4"}.get(timeframe,"Min60")
    seconds={"1m":60,"3m":180,"5m":300,"15m":900,"1h":3600,"4h":14400}.get(timeframe,3600)
    multiplier=3 if timeframe == "3m" else 1
    end = int(time.time()); start = end - limit*seconds*multiplier
    payload = api_json("https://contract.mexc.com/api/v1/contract/kline/" + symbol,
                       {"interval":gran, "start":start, "end":end})
    data = (payload or {}).get("data", {})
    if not isinstance(data, dict) or len(data.get("time", [])) < 30: return None
    frame = pd.DataFrame({"time":data["time"], "open":data["open"], "high":data["high"], "low":data["low"], "close":data["close"], "vol":data.get("vol", [])})
    for c in ("open","high","low","close","vol"): frame[c] = pd.to_numeric(frame[c], errors="coerce")
    frame=frame.sort_values("time").dropna().reset_index(drop=True)
    return aggregate_3m(frame) if timeframe == "3m" else frame


def get_futures_funding_oi(exchange, symbol):
    try:
        if exchange == "BINANCE":
            base = symbol
            fund = api_json("https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol":base})
            oi = api_json("https://fapi.binance.com/futures/data/openInterestHist", {"symbol":base,"period":"5m","limit":12})
            funding = safe_float(fund.get("lastFundingRate"))*100 if isinstance(fund,dict) and "lastFundingRate" in fund else None
            if isinstance(oi,list) and len(oi)>1:
                first=safe_float(oi[0].get("sumOpenInterestValue")); last=safe_float(oi[-1].get("sumOpenInterestValue"))
                change=(last-first)/first*100 if first>0 else None
            else: change=None
            return funding, change
        if exchange == "BYBIT":
            f=api_json("https://api.bybit.com/v5/market/funding/history", {"category":"linear","symbol":symbol,"limit":2})
            o=api_json("https://api.bybit.com/v5/market/open-interest", {"category":"linear","symbol":symbol,"intervalTime":"5min","limit":12})
            fl=(f or {}).get("result",{}).get("list",[]); ol=(o or {}).get("result",{}).get("list",[])
            funding=safe_float(fl[0].get("fundingRate"))*100 if fl else None
            first=safe_float(ol[-1].get("openInterest")) if ol else 0; last=safe_float(ol[0].get("openInterest")) if ol else 0
            return funding, ((last-first)/first*100 if first>0 else None)
        if exchange == "KUCOIN":
            payload=api_json("https://api-futures.kucoin.com/api/v1/funding-rate/"+symbol+"/current")
            data=(payload or {}).get("data",{})
            return (safe_float(data.get("value"))*100 if data else None), None
        if exchange == "MEXC":
            payload=api_json("https://contract.mexc.com/api/v1/contract/funding_rate/"+symbol)
            data=(payload or {}).get("data",{})
            return (safe_float(data.get("fundingRate"))*100 if data else None), None
    except Exception:
        pass
    return None, None


def get_binance_symbols(limit=100):
    payload = api_json("https://data-api.binance.vision/api/v3/ticker/24hr")
    if not isinstance(payload, list):
        return []
    rows = [
        item for item in payload
        if item.get("symbol", "").endswith("USDT")
        and item.get("symbol") not in STABLES
    ]
    rows.sort(key=lambda item: safe_float(item.get("quoteVolume")), reverse=True)
    return [item["symbol"] for item in rows[:limit]]


def get_binance_klines(symbol):
    payload = api_json(
        "https://data-api.binance.vision/api/v3/klines",
        {"symbol": symbol, "interval": "1h", "limit": 100},
    )
    if not isinstance(payload, list) or len(payload) < 30:
        return None
    frame = pd.DataFrame(
        payload,
        columns=["ot", "open", "high", "low", "close", "vol",
                 "ct", "qav", "trades", "tb", "tq", "ignore"],
    )
    for column in ("open", "high", "low", "close", "vol"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna().reset_index(drop=True)


def get_btc_change():
    payload = api_json(
        "https://fapi.binance.com/fapi/v1/klines",
        {"symbol": "BTCUSDT", "interval": "1h", "limit": 2},
    )
    if not isinstance(payload, list) or len(payload) < 2:
        return None
    previous = safe_float(payload[-2][4])
    current = safe_float(payload[-1][4])
    return (current - previous) / previous * 100 if previous else None


def get_binance_funding(symbol):
    base = symbol.replace("-USDT", "").replace("USDT", "")
    payload = api_json(
        "https://fapi.binance.com/fapi/v1/premiumIndex",
        {"symbol": f"{base}USDT"},
    )
    if not isinstance(payload, dict) or "lastFundingRate" not in payload:
        return None
    return safe_float(payload["lastFundingRate"]) * 100


def get_binance_oi_change(symbol):
    base = symbol.replace("-USDT", "").replace("USDT", "")
    payload = api_json(
        "https://fapi.binance.com/futures/data/openInterestHist",
        {"symbol": f"{base}USDT", "period": "5m", "limit": 12},
    )
    if not isinstance(payload, list) or len(payload) < 2:
        return None, None
    first = safe_float(payload[0].get("sumOpenInterest"))
    last = safe_float(payload[-1].get("sumOpenInterest"))
    if first <= 0:
        return None, last
    return (last - first) / first * 100, last


def get_orderbook_wall(symbol):
    base = symbol.replace("-USDT", "").replace("USDT", "")
    payload = api_json(
        "https://data-api.binance.vision/api/v3/depth",
        {"symbol": f"{base}USDT", "limit": 20},
    )
    if not isinstance(payload, dict):
        return "بيانات دفتر الأوامر غير متاحة"
    bids, asks = payload.get("bids", []), payload.get("asks", [])
    if not bids or not asks:
        return "دفتر الأوامر فارغ أو غير متاح"
    # Compare quote notional at each level, not raw coin quantity.
    bid_levels = [(safe_float(p) * safe_float(q), safe_float(p)) for p, q in bids]
    ask_levels = [(safe_float(p) * safe_float(q), safe_float(p)) for p, q in asks]
    max_bid = max(bid_levels, key=lambda item: item[0])
    max_ask = max(ask_levels, key=lambda item: item[0])
    if max_ask[0] > max_bid[0] * 1.5:
        return f"عرض بيع أكبر نسبيًا: {max_ask[0]:,.0f} USDT عند {max_ask[1]}"
    if max_bid[0] > max_ask[0] * 1.5:
        return f"طلب شراء أكبر نسبيًا: {max_bid[0]:,.0f} USDT عند {max_bid[1]}"
    return f"لا يوجد جدار بارز؛ شراء {max_bid[0]:,.0f} / بيع {max_ask[0]:,.0f} USDT"


def check_spot_listings(symbol):
    """Spot availability check kept separate from the Futures scanner universe."""
    base = symbol.replace("_USDT", "").replace("-USDT", "").replace("USDTM", "").replace("USDT", "")
    if base == "XBT": base = "BTC"
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
            if not response.ok: continue
            data = response.json()
            if name == "KUCOIN": valid = data.get("code") == "200000" and bool(data.get("data"))
            elif name == "GATE": valid = isinstance(data, list) and len(data) > 0
            elif name == "BITGET": valid = data.get("code") == "00000" and bool(data.get("data", {}).get("list"))
            elif name == "BYBIT": valid = data.get("retCode") == 0 and bool(data.get("result", {}).get("list"))
            else: valid = isinstance(data, dict) and "price" in data
            if valid: available.append(name)
        except (requests.RequestException, ValueError, TypeError):
            continue
    return len(available), available


# ----------------------------- Indicators -----------------------------

def add_indicators(frame):
    """Return a copy of OHLCV data with the indicators required by analyze()."""
    if frame is None or frame.empty:
        return frame
    out = frame.copy()
    for column in ("open", "high", "low", "close", "vol"):
        if column not in out.columns:
            raise ValueError(f"عمود بيانات مفقود: {column}")
        out[column] = pd.to_numeric(out[column], errors="coerce")

    close = out["close"]
    high = out["high"]
    low = out["low"]
    out["ema9"] = close.ewm(span=9, adjust=False, min_periods=1).mean()
    out["ema21"] = close.ewm(span=21, adjust=False, min_periods=1).mean()
    out["ema200"] = close.ewm(span=200, adjust=False, min_periods=1).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, float("nan"))
    out["rsi"] = 100 - (100 / (1 + rs))
    out.loc[(loss == 0) & (gain > 0), "rsi"] = 100
    out.loc[(gain == 0) & (loss > 0), "rsi"] = 0
    out["rsi"] = out["rsi"].fillna(50)

    ema12 = close.ewm(span=12, adjust=False, min_periods=1).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=1).mean()
    out["macd"] = ema12 - ema26
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False, min_periods=1).mean()

    previous_close = close.shift(1)
    true_range = pd.concat([
        high - low, (high - previous_close).abs(), (low - previous_close).abs()
    ], axis=1).max(axis=1)
    out["atr"] = true_range.ewm(alpha=1/14, adjust=False, min_periods=1).mean()
    out["momentum"] = close.pct_change(5).replace([float("inf"), -float("inf")], 0).fillna(0) * 100
    return out.replace([float("inf"), -float("inf")], pd.NA).ffill().fillna(0)


def market_structure(frame, lookback=20):
    """Candle-derived liquidity/swing and order-block estimates (heuristics)."""
    recent = frame.tail(max(lookback, 5)).copy()
    last = recent.iloc[-1]
    prior = recent.iloc[:-1]
    bsl = safe_float(prior["high"].max(), safe_float(last["high"])) if not prior.empty else safe_float(last["high"])
    ssl = safe_float(prior["low"].min(), safe_float(last["low"])) if not prior.empty else safe_float(last["low"])
    high_now, low_now, close_now = safe_float(last["high"]), safe_float(last["low"]), safe_float(last["close"])
    bsl_sweep = high_now > bsl and close_now < bsl
    ssl_sweep = low_now < ssl and close_now > ssl

    bull_ob = bear_ob = None
    rows = frame.tail(12).reset_index(drop=True)
    for i in range(len(rows) - 1, 0, -1):
        candle = rows.iloc[i - 1]
        nxt = rows.iloc[i]
        o, c = safe_float(candle["open"]), safe_float(candle["close"])
        no, nc = safe_float(nxt["open"]), safe_float(nxt["close"])
        if c < o and nc > no and nc > safe_float(candle["high"]):
            bull_ob = (safe_float(candle["low"]), safe_float(candle["high"]))
            break
    for i in range(len(rows) - 1, 0, -1):
        candle = rows.iloc[i - 1]
        nxt = rows.iloc[i]
        o, c = safe_float(candle["open"]), safe_float(candle["close"])
        no, nc = safe_float(nxt["open"]), safe_float(nxt["close"])
        if c > o and nc < no and nc < safe_float(candle["low"]):
            bear_ob = (safe_float(candle["low"]), safe_float(candle["high"]))
            break
    return {"bsl": bsl, "ssl": ssl, "bsl_sweep": bsl_sweep,
            "ssl_sweep": ssl_sweep, "bull_ob": bull_ob, "bear_ob": bear_ob}


def get_real_cvd(exchange, symbol, limit=1000):
    """Trade-level CVD where public recent-trade endpoints are available."""
    try:
        if exchange == "BINANCE":
            data = api_json("https://fapi.binance.com/fapi/v1/aggTrades",
                            {"symbol": symbol, "limit": min(limit, 1000)})
            if not isinstance(data, list) or not data:
                return None
            buy = sell = 0.0
            for trade in data:
                qty = safe_float(trade.get("q"))
                if trade.get("m") is True: sell += qty
                else: buy += qty
            total = buy + sell
            return (buy - sell) / total * 100 if total else None
        if exchange == "BYBIT":
            payload = api_json("https://api.bybit.com/v5/market/recent-trade",
                               {"category": "linear", "symbol": symbol, "limit": min(limit, 1000)})
            trades = (payload or {}).get("result", {}).get("list", [])
            if not trades: return None
            buy = sum(safe_float(x.get("size")) for x in trades if x.get("side") == "Buy")
            sell = sum(safe_float(x.get("size")) for x in trades if x.get("side") == "Sell")
            total = buy + sell
            return (buy - sell) / total * 100 if total else None
    except Exception:
        return None
    return None


def get_futures_orderbook(exchange, symbol, depth=20):
    """Top-of-book bid/ask size imbalance for supported futures venues."""
    try:
        if exchange == "BINANCE":
            payload = api_json("https://fapi.binance.com/fapi/v1/depth",
                               {"symbol": symbol, "limit": min(depth, 100)})
            bids, asks = (payload or {}).get("bids", []), (payload or {}).get("asks", [])
        elif exchange == "BYBIT":
            payload = api_json("https://api.bybit.com/v5/market/orderbook",
                               {"category": "linear", "symbol": symbol, "limit": min(depth, 50)})
            book = (payload or {}).get("result", {})
            bids, asks = book.get("b", []), book.get("a", [])
        elif exchange == "KUCOIN":
            payload = api_json("https://api-futures.kucoin.com/api/v1/level2/snapshot", {"symbol": symbol})
            book = (payload or {}).get("data", {})
            bids, asks = book.get("bids", []), book.get("asks", [])
        elif exchange == "MEXC":
            payload = api_json("https://contract.mexc.com/api/v1/contract/depth/" + symbol, {"limit": depth})
            book = (payload or {}).get("data", {})
            bids, asks = book.get("bids", []), book.get("asks", [])
        else:
            return None, "منصة دفتر الأوامر غير مدعومة"

        def total_size(levels):
            total = 0.0
            for level in levels[:depth]:
                if isinstance(level, dict):
                    qty = level.get("size", level.get("qty", level.get("v", 0)))
                else:
                    qty = level[1] if len(level) > 1 else 0
                total += safe_float(qty)
            return total

        bid_size, ask_size = total_size(bids), total_size(asks)
        total = bid_size + ask_size
        if total <= 0:
            return None, "بيانات دفتر الأوامر غير متاحة"
        imbalance = (bid_size - ask_size) / total * 100
        return imbalance, f"اختلال دفتر الأوامر {exchange}: {imbalance:+.1f}% (أفضل {depth} مستويات متاحة)"
    except Exception as exc:
        return None, f"تعذر قراءة دفتر الأوامر: {exc}"


def candle_volume_delta_proxy(frame, lookback=20):
    """Green/red candle volume approximation; not exchange trade-level CVD."""
    recent = frame.tail(lookback)
    green = recent.loc[recent["close"] > recent["open"], "vol"].sum()
    red = recent.loc[recent["close"] < recent["open"], "vol"].sum()
    total = green + red
    return ((green - red) / total * 100) if total else 0.0


def find_recent_fvg(frame, lookback=30):
    bull = bear = None
    start = max(1, len(frame) - lookback)
    for index in range(start, len(frame) - 1):
        previous_high = safe_float(frame["high"].iloc[index - 1])
        previous_low = safe_float(frame["low"].iloc[index - 1])
        next_low = safe_float(frame["low"].iloc[index + 1])
        next_high = safe_float(frame["high"].iloc[index + 1])
        if next_low > previous_high:
            bull = (previous_high, next_low, (previous_high + next_low) / 2)
        if next_high < previous_low:
            bear = (next_high, previous_low, (next_high + previous_low) / 2)
    return bull, bear


def candle_trap_note(frame, side, cvd_proxy):
    candle = frame.iloc[-1]
    high, low = safe_float(candle["high"]), safe_float(candle["low"])
    open_price, close = safe_float(candle["open"]), safe_float(candle["close"])
    body = abs(close - open_price)
    upper_wick = high - max(open_price, close)
    lower_wick = min(open_price, close) - low
    if side == "SHORT" and body > 0 and upper_wick > body * 1.5:
        return "ذيل علوي طويل؛ احتمال رفض سعري، وليس إثباتًا لضرب ستوبات"
    if side == "LONG" and body > 0 and lower_wick > body * 1.5:
        return "ذيل سفلي طويل؛ احتمال رفض سعري، وليس إثباتًا لتجميع الحيتان"
    return f"ضغط الشموع التقريبي: {cvd_proxy:+.1f}%"


def analyze(frame, symbol, settings, exchange="BINANCE"):
    try:
        if frame is None or len(frame) < 30:
            return None, "بيانات شموع غير كافية"

        last = safe_float(frame["close"].iloc[-1])
        previous = safe_float(frame["close"].iloc[-2])
        if last <= 0 or previous <= 0:
            return None, "سعر غير صالح"

        frame = add_indicators(frame)
        change = (last - previous) / previous * 100
        if abs(change) > 8:
            return None, f"حركة الشمعة الأخيرة ({settings.get('timeframe','1h')}): {change:.2f}%"

        average_volume = safe_float(frame["vol"].iloc[-21:-1].mean())
        current_volume = safe_float(frame["vol"].iloc[-1])
        volume_ratio = current_volume / average_volume if average_volume > 0 else 0

        cvd_proxy = candle_volume_delta_proxy(frame)
        real_cvd = get_real_cvd(exchange, symbol)
        cvd_value = real_cvd if real_cvd is not None else cvd_proxy
        if abs(cvd_value) < 3:
            return None, f"ضغط الشموع ضعيف: {cvd_proxy:.1f}%"

        side = "LONG" if cvd_value > 0 else "SHORT"
        if side == "LONG" and not settings["want_long"]:
            return None, "LONG غير مفعّل"
        if side == "SHORT" and not settings["want_short"]:
            return None, "SHORT غير مفعّل"
        mtf_note = "MTF غير مفعل"
        if settings.get("mtf_filter"):
            higher_tf = "1h" if settings.get("timeframe") != "1h" else "4h"
            source = {"KUCOIN":get_kucoin_futures_klines,"BINANCE":get_binance_futures_klines,
                      "BYBIT":get_bybit_futures_klines,"MEXC":get_mexc_futures_klines}[exchange]
            higher = source(symbol, higher_tf, 120)
            if higher is None or len(higher) < 30: return None, "بيانات MTF غير متاحة"
            higher = add_indicators(higher)
            aligned = safe_float(higher["ema9"].iloc[-1]) > safe_float(higher["ema21"].iloc[-1]) if side == "LONG" else safe_float(higher["ema9"].iloc[-1]) < safe_float(higher["ema21"].iloc[-1])
            if not aligned: return None, f"اتجاه {higher_tf} غير مؤكد مع {side}"
            mtf_note = f"MTF مؤكد على {higher_tf}"

        btc_change = get_btc_change() if settings["btc_filter"] else None
        if settings["btc_filter"] and btc_change is not None:
            if side == "LONG" and btc_change < -2:
                return None, f"فلتر BTC: هبوط {btc_change:.2f}%"
            if side == "SHORT" and btc_change > 2:
                return None, f"فلتر BTC: صعود {btc_change:.2f}%"

        bull_fvg, bear_fvg = find_recent_fvg(frame)
        if settings["use_fvg"] and not (bull_fvg or bear_fvg):
            return None, "لا توجد فجوة FVG حديثة"

        in_kz, kz_label = killzone_status()
        funding, oi_change = get_futures_funding_oi(exchange, symbol)
        if settings["funding_filter"] and funding is not None:
            if side == "LONG" and funding > 0.05:
                return None, f"فاندنج مرتفع ضد LONG: {funding:.4f}%"
            if side == "SHORT" and funding < -0.05:
                return None, f"فاندنج سالب ضد SHORT: {funding:.4f}%"

        structure = market_structure(frame)
        ema_bull = safe_float(frame["ema9"].iloc[-1]) > safe_float(frame["ema21"].iloc[-1])
        ema_bear = safe_float(frame["ema9"].iloc[-1]) < safe_float(frame["ema21"].iloc[-1])
        macd_bull = safe_float(frame["macd"].iloc[-1]) > safe_float(frame["macd_signal"].iloc[-1])
        macd_bear = safe_float(frame["macd"].iloc[-1]) < safe_float(frame["macd_signal"].iloc[-1])
        rsi = safe_float(frame["rsi"].iloc[-1], 50)
        atr = safe_float(frame["atr"].iloc[-1])
        momentum = safe_float(frame["momentum"].iloc[-1])
        book_imbalance, book_note = get_futures_orderbook(exchange, symbol) if settings["wall_filter"] else (None, "")
        score = 38
        score += min(max(volume_ratio, 0) * 3, 15)
        score += min(abs(cvd_value) * 0.20, 18)
        score += 7 if ((side == "LONG" and ema_bull and macd_bull) or (side == "SHORT" and ema_bear and macd_bear)) else 0
        score += 4 if ((side == "LONG" and 45 <= rsi <= 68) or (side == "SHORT" and 32 <= rsi <= 55)) else 0
        score += 3 if ((side == "LONG" and momentum > 0) or (side == "SHORT" and momentum < 0)) else 0
        if book_imbalance is not None and ((side == "LONG" and book_imbalance > 8) or (side == "SHORT" and book_imbalance < -8)):
            score += 5
        score += 8 if ((side == "LONG" and bull_fvg) or (side == "SHORT" and bear_fvg)) else 0
        score += 5 if in_kz else 0
        learning = learning_profile()
        score = max(0, min(int(score) + learning["adjustment"], 98))

        if score < settings["min_score"]:
            return None, f"السكور {score} أقل من المطلوب {settings['min_score']}"

        if side == "LONG":
            fvg_mid = bull_fvg[2] if bull_fvg else last * 0.997
            entry = clamp_entry(fvg_mid, last, True)
            risk = max(atr * 1.5, last * 0.006)
            stop = last - risk
            tp1, tp2 = last + risk * 1.5, last + risk * 2.5
        else:
            fvg_mid = bear_fvg[2] if bear_fvg else last * 1.003
            entry = clamp_entry(fvg_mid, last, False)
            risk = max(atr * 1.5, last * 0.006)
            stop = last + risk
            tp1, tp2 = last - risk * 1.5, last - risk * 2.5

        notes = [
            f"📊 CVD: {cvd_value:+.1f}% ({'تدفق صفقات حقيقي' if real_cvd is not None else 'Proxy من اتجاه الشموع؛ ليس CVD حقيقيًا'})",
            f"📦 حجم آخر شمعة: x{volume_ratio:.2f} من متوسط 20 شمعة",
            f"⏰ {kz_label}" if settings["killzone"] else "⏰ فلتر الوقت متوقف",
            f"🐋 {candle_trap_note(frame, side, cvd_proxy)}",
        ]
        notes.append(f"🧭 {mtf_note}")
        notes.append(f"📐 EMA9/21: {'صاعد' if ema_bull else 'هابط'} | RSI14: {rsi:.1f} | MACD: {'إيجابي' if macd_bull else 'سلبي'}")
        notes.append(f"⚡ ATR14: {atr:.8g} | Momentum(5): {momentum:+.2f}%")
        notes.append(f"💧 BSL: {structure['bsl']:.8g} | SSL: {structure['ssl']:.8g} | Sweep: {'BSL' if structure['bsl_sweep'] else ('SSL' if structure['ssl_sweep'] else 'لا يوجد تأكيد')}")
        ob = structure['bull_ob'] if side == 'LONG' else structure['bear_ob']
        notes.append(f"🧱 Order Block heuristic: {ob[0]:.8g}–{ob[1]:.8g}" if ob else "🧱 لا يوجد OB واضح وفق شرط الشموع")
        if book_imbalance is not None: notes.append(f"📚 {book_note}")
        notes.append("🧨 Liquidations: لا تتوفر بيانات موحدة موثوقة عبر جميع المنصات في هذا الفحص؛ لم يتم اختلاق خريطة تصفيات.")
        relevant_fvg = bull_fvg if side == "LONG" else bear_fvg
        if relevant_fvg:
            notes.append(
                f"FVG: {relevant_fvg[0]:.8g} إلى {relevant_fvg[1]:.8g}؛ المنتصف {relevant_fvg[2]:.8g}"
            )
        if settings["funding_filter"]:
            notes.append(
                f"💸 Funding {exchange} Futures: {funding:+.4f}%"
                if funding is not None else "💸 Funding: غير متاح لهذا الرمز"
            )

        if oi_change is not None:
            notes.append(f"📈 OI {exchange} Futures: {oi_change:+.2f}%")
        else:
            notes.append(f"📈 OI {exchange}: غير متاح من الواجهة العامة")

        if settings["wall_filter"] and book_imbalance is None:
            notes.append("📚 دفتر الأوامر: لم تتوفر بيانات صالحة لهذا الرمز")

        if settings["confirm_exchanges"]:
            count, exchanges = check_spot_listings(symbol)
            notes.append(
                f"🌐 الرمز متاح Spot على {count}/5 بحسب فحص endpoints: {', '.join(exchanges)}"
            )
            if count >= 3:
                score = min(score + 3, 98)

        stop_distance = abs(entry-stop)
        risk_cash = settings.get("capital_usdt",100.0) * settings.get("risk_pct",1.0) / 100
        estimated_cost_pct = settings.get("fee_pct",0.10) + settings.get("slippage_pct",0.05)
        effective_risk_per_unit = stop_distance + entry * estimated_cost_pct / 100
        position_qty = risk_cash / effective_risk_per_unit if effective_risk_per_unit > 0 else 0
        position_notional = position_qty * entry
        risk_pct = abs(stop - last) / last * 100
        notes.append(f"🎯 مسافة وقف الخسارة: {risk_pct:.2f}% من السعر | R:R TP1 {abs(tp1-entry)/max(stop_distance,1e-12):.2f}")
        notes.append(f"📏 حجم المركز النظري: {position_qty:.6g} وحدة | القيمة {position_notional:.2f} USDT | مخاطرة {risk_cash:.2f} USDT")
        notes.append(f"🧾 تكلفة تقديرية رسوم+انزلاق: {estimated_cost_pct:.2f}%")
        notes.append("⚠️ مستويات إرشادية مبنية على السعر الحالي؛ يلزم إعادة حسابها عند التنفيذ.")

        result = {
            "symbol": symbol,
            "type": side,
            "score": score,
            "price": round(last, 8),
            "ch": round(change, 2),
            "vol": round(volume_ratio, 2),
            "buy": round(cvd_proxy, 1),
            "entry": round(entry, 8),
            "stop": round(stop, 8),
            "tp1": round(tp1, 8),
            "tp2": round(tp2, 8),
            "tp3": round((last + risk * 3.5) if side == "LONG" else (last - risk * 3.5), 8),
            "funding": funding, "oi_change": oi_change, "real_cvd": real_cvd,
            "rr_tp1": round(abs(tp1-entry)/max(abs(entry-stop), 1e-12), 2),
            "position_qty": round(position_qty, 8), "position_notional": round(position_notional, 2),
            "extra": "\n".join(notes),
        }
        return result, "OK"
    except Exception as exc:
        return None, f"خطأ تحليل: {exc}"


# ----------------------------- DEX scanner -----------------------------

def scan_dex():
    payload = api_json("https://api.dexscreener.com/latest/dex/search/", {"q": "BSC"})
    pairs = (payload or {}).get("pairs", [])
    found, seen = [], set()
    for pair in pairs:
        if pair.get("chainId") != "bsc":
            continue
        token = pair.get("baseToken") or {}
        address = token.get("address")
        if not address or address in seen:
            continue
        seen.add(address)
        price = safe_float(pair.get("priceUsd"))
        liquidity = safe_float((pair.get("liquidity") or {}).get("usd"))
        volume_5m = safe_float((pair.get("volume") or {}).get("m5"))
        change_5m = safe_float((pair.get("priceChange") or {}).get("m5"))
        if price > 0 and volume_5m >= 5000 and change_5m >= 5 and liquidity >= 15000:
            found.append({
                "symbol": token.get("symbol", "UNKNOWN"),
                "price": price,
                "change_5m": change_5m,
                "volume_5m": volume_5m,
                "liquidity": liquidity,
                "url": pair.get("url", ""),
            })
    return sorted(found, key=lambda item: item["volume_5m"], reverse=True)


# ----------------------------- Sidebar -----------------------------

init_db()

with st.sidebar:
    st.markdown("## 🎛️ إعدادات الماسح")
    platform = st.selectbox("منصة العقود الآجلة", ["KUCOIN", "BINANCE", "BYBIT", "MEXC"])
    st.markdown("### اتجاه الصفقة")
    want_long = st.checkbox("🚀 LONG", value=True)
    want_short = st.checkbox("📉 SHORT", value=True)
    st.markdown("### الفلاتر")
    use_fvg = st.checkbox("FVG", value=False)
    mtf_filter = st.checkbox("تأكيد الاتجاه متعدد الأطر (MTF)", value=False)
    btc_filter = st.checkbox("فلتر اتجاه BTC", value=True)
    funding_filter = st.checkbox("فلتر Funding Futures", value=False)
    wall_filter = st.checkbox("دفتر أوامر Futures (حسب المنصة)", value=False)
    killzone = st.checkbox("عرض نوافذ السيولة التقريبية", value=True)
    confirm_exchanges = st.checkbox("فحص توافر الرمز على 5 منصات Spot", value=False)
    st.markdown("### التصفية")
    min_score = st.slider("أقل Score", 0, 95, 20)
    limit_coins = st.slider("عدد العملات للفحص", 10, 100, 40, step=5)
    timeframe = st.selectbox("الإطار الزمني للعقود", ["1m", "3m", "5m", "15m", "1h"], index=2)
    bars_limit = st.select_slider("عدد الشموع", options=[100, 250, 500, 1000], value=500)
    capital_usdt = st.number_input("رأس المال USDT لحساب الحجم", min_value=10.0, value=100.0, step=10.0)
    risk_pct = st.number_input("المخاطرة لكل صفقة %", min_value=0.1, max_value=5.0, value=1.0, step=0.1)
    fee_pct = st.number_input("رسوم تقديرية للدخول والخروج %", min_value=0.0, max_value=2.0, value=0.10, step=0.01)
    slippage_pct = st.number_input("انزلاق تقديري %", min_value=0.0, max_value=2.0, value=0.05, step=0.01)
    telegram_enabled = st.checkbox("إرسال أفضل الإشارات إلى Telegram", value=False)
    if st.button("📡 اختبار Telegram"):
        ok, message = send_telegram("🧪 اختبار BLY7TRADER — اتصال Telegram يعمل.")
        st.success(message) if ok else st.error(message)

settings = {
    "want_long": want_long,
    "want_short": want_short,
    "use_fvg": use_fvg,
    "mtf_filter": mtf_filter,
    "btc_filter": btc_filter,
    "funding_filter": funding_filter,
    "wall_filter": wall_filter,
    "killzone": killzone,
    "confirm_exchanges": confirm_exchanges,
    "min_score": min_score,
    "capital_usdt": capital_usdt, "risk_pct": risk_pct,
    "fee_pct": fee_pct, "slippage_pct": slippage_pct,
    "timeframe": timeframe,
}


# ----------------------------- Main navigation -----------------------------

section = st.radio(
    "القسم",
    ["🔎 الماسح", "📉 DUMP / SHORT", "🚀 DEX", "📊 سجل الإشارات", "🧠 الذاكرة والتعلّم", "🧪 اختبار تاريخي"],
    horizontal=True,
)

if section in ("🔎 الماسح", "📉 DUMP / SHORT"):
    is_dump_section = section == "📉 DUMP / SHORT"
    st.subheader("📉 ماسح SHORT" if is_dump_section else "🔎 ماسح السوق")
    st.caption(
        f"المصدر: {platform} USDT-M Futures | TF: {timeframe} | الشموع: {bars_limit} | العملات: {limit_coins} | أقل Score: {min_score} | "
        f"توقيت القاهرة: {now_cairo().strftime('%H:%M')}"
    )

    button_label = "📉 افحص فرص SHORT" if is_dump_section else "🔍 افحص السوق الآن"
    if st.button(button_label, type="primary"):
        symbol_sources = {"KUCOIN": get_kucoin_futures_symbols,
                          "BINANCE": get_binance_futures_symbols,
                          "BYBIT": get_bybit_futures_symbols,
                          "MEXC": get_mexc_futures_symbols}
        symbols = symbol_sources[platform](limit_coins)
        st.info(f"تم العثور على {len(symbols)} رمزًا للفحص.")
        signals, debug = [], []
        progress = st.progress(0)
        status = st.empty()

        for index, symbol in enumerate(symbols):
            progress.progress((index + 1) / max(len(symbols), 1))
            status.caption(f"يفحص {symbol} ({index + 1}/{len(symbols)})")
            candle_sources = {"KUCOIN": get_kucoin_futures_klines,
                              "BINANCE": get_binance_futures_klines,
                              "BYBIT": get_bybit_futures_klines,
                              "MEXC": get_mexc_futures_klines}
            frame = candle_sources[platform](symbol, timeframe, bars_limit)
            if frame is not None:
                signal, reason = analyze(frame, symbol, settings, platform)
                if signal and (not is_dump_section or signal["type"] == "SHORT"):
                    signals.append(signal)
                elif len(debug) < 15:
                    debug.append({"العملة": symbol, "السبب": reason})
            else:
                if len(debug) < 15:
                    debug.append({"العملة": symbol, "السبب": "تعذر جلب الشموع"})
            time.sleep(0.08)

        progress.empty()
        status.empty()

        signals.sort(key=lambda item: item["score"], reverse=True)
        if signals:
            save_signals(signals, platform)
            st.success(f"تم العثور على {len(signals)} إشارة مطابقة.")
            if telegram_enabled:
                send_signal_batch(signals)

            for signal in signals:
                with st.container(border=True):
                    left, right = st.columns([4, 1])
                    with left:
                        st.markdown(
                            f"### {'🚀' if signal['type'] == 'LONG' else '📉'} "
                            f"{signal['symbol']} — {signal['type']}"
                        )
                        st.write(
                            f"السعر: **{signal['price']}** | "
                            f"تغير الساعة: **{signal['ch']}%** | "
                            f"Volume: **x{signal['vol']}** | "
                            f"CVD proxy: **{signal['buy']}%**"
                        )
                    with right:
                        st.metric("Score", f"{signal['score']}/100")
                    a, b, c, d = st.columns(4)
                    a.metric("الدخول", signal["entry"])
                    b.metric("وقف الخسارة", signal["stop"])
                    c.metric("TP1", signal["tp1"])
                    d.metric("TP2", signal["tp2"])
                    st.metric("TP3", signal["tp3"])
                    st.caption(f"R:R إلى TP1 = {signal['rr_tp1']} | حجم المركز النظري = {signal['position_qty']} | مصدر CVD: {'تداولات فعلية' if signal['real_cvd'] is not None else 'Proxy شموع'}")
                    with st.expander("تفاصيل التحليل"):
                        st.text(signal["extra"])
        else:
            st.warning("لم تظهر إشارات مطابقة للفلاتر الحالية.")
        if debug:
            with st.expander("أسباب استبعاد بعض العملات"):
                st.dataframe(pd.DataFrame(debug), use_container_width=True)


elif section == "🚀 DEX":
    st.subheader("🚀 ماسح DEX — BNB Smart Chain")
    st.caption("شروط افتراضية: حجم 5 دقائق ≥ 5,000$، تغير ≥ 5%، سيولة ≥ 15,000$.")
    if st.button("🚀 افحص DEX الآن", type="primary"):
        dex_signals = scan_dex()
        if not dex_signals:
            st.info("لا توجد أزواج مطابقة للشروط حاليًا.")
        for item in dex_signals:
            with st.container(border=True):
                st.markdown(f"### 🚀 {item['symbol']}")
                st.write(
                    f"السعر: ${item['price']:.10g} | تغير 5 دقائق: "
                    f"{item['change_5m']:.2f}% | حجم 5 دقائق: "
                    f"${item['volume_5m']:,.0f} | السيولة: ${item['liquidity']:,.0f}"
                )
                if item["url"]:
                    st.markdown(f"[فتح الزوج على DexScreener]({item['url']})")
                if telegram_enabled:
                    message = (
                        f"🚀 DEX {item['symbol']} على BSC\n"
                        f"السعر: ${item['price']:.10g}\n"
                        f"تغير 5m: {item['change_5m']:.2f}%\n"
                        f"حجم 5m: ${item['volume_5m']:,.0f}\n"
                        f"السيولة: ${item['liquidity']:,.0f}\n"
                        f"{item['url']}\n@WHYNOTBLY7"
                    )
                    ok, error = send_telegram(message)
                    if not ok:
                        st.warning(f"تعذر إرسال {item['symbol']}: {error}")


elif section == "📊 سجل الإشارات":
    st.subheader("📊 سجل الإشارات المحفوظ")
    history = load_signal_history(200)
    if history.empty:
        st.info("لا توجد إشارات محفوظة بعد. شغّل الماسح أولاً.")
    else:
        st.dataframe(history, use_container_width=True, hide_index=True)
        st.caption(
            "السجل يحفظ الإشارات الصادرة فقط. لا تُحسب نسبة نجاح تلقائية حتى تتم إضافة "
            "آلية متابعة مستقبلية موثوقة لأسعار TP وSL."
        )


elif section == "🧠 الذاكرة والتعلّم":
    st.subheader("🧠 الذاكرة الدائمة — سجل نتائج الصفقات")
    profile = learning_profile()
    a,b,c = st.columns(3)
    a.metric("صفقات محسومة", profile["trades"])
    b.metric("Win Rate", f"{profile['win_rate']:.1f}%")
    c.metric("تعديل السكور المتعلّم", f"{profile['adjustment']:+d}")
    st.caption("قاعدة البيانات SQLite محلية ودائمة. لا يُفعّل تعديل السكور إلا بعد 10 نتائج WIN/LOSS مؤكدة يدويًا.")
    st.write("**الأداء حسب الاتجاه**")
    st.dataframe(pd.DataFrame([{"الاتجاه":k, **v} for k,v in profile["by_side"].items()]), use_container_width=True, hide_index=True)
    with sqlite3.connect(DB_PATH) as conn:
        open_trades = pd.read_sql_query("SELECT id,created_at,exchange,symbol,side,score,entry,stop,tp1,tp2,tp3,outcome FROM signals WHERE outcome='OPEN' ORDER BY id DESC LIMIT 300", conn)
        all_trades = pd.read_sql_query("SELECT id,created_at,exchange,symbol,side,score,entry,stop,tp1,tp2,tp3,outcome,pnl_pct,result_source FROM signals ORDER BY id DESC LIMIT 500", conn)
    st.markdown("#### تحديث نتيجة صفقة")
    if not open_trades.empty:
        options = {f"#{int(r.id)} {r.exchange} {r.symbol} {r.side} | {r.created_at[:16]}": int(r.id) for r in open_trades.itertuples()}
        selected_label = st.selectbox("اختر الإشارة", list(options))
        result_choice = st.selectbox("النتيجة المؤكدة", ["WIN", "LOSS", "BREAKEVEN", "OPEN"])
        if st.button("💾 حفظ نتيجة الصفقة"):
            update_trade_outcome(options[selected_label], result_choice)
            st.success("تم حفظ النتيجة في الذاكرة الدائمة وتحديث إحصاءات التعلّم.")
    else:
        st.info("لا توجد صفقات مفتوحة في السجل.")
    st.markdown("#### سجل النتائج")
    if not all_trades.empty:
        st.dataframe(all_trades, use_container_width=True, hide_index=True)
    else:
        st.info("سيظهر السجل بعد أول عملية فحص.")


elif section == "🧪 اختبار تاريخي":
    st.subheader("🧪 اختبار تاريخي مبسط — Binance")
    test_symbol = st.selectbox("العملة", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])
    if st.button("▶️ شغّل الاختبار", type="primary"):
        frame = get_binance_klines(test_symbol)
        if frame is None or len(frame) < 50:
            st.error("تعذر جلب بيانات كافية للاختبار.")
        else:
            # This is a transparent baseline test, not a simulation of every live filter.
            # It evaluates a simple candle-volume directional signal on subsequent bars.
            wins, losses, unresolved = 0, 0, 0
            trades = []
            for index in range(25, len(frame) - 5):
                history_frame = frame.iloc[: index + 1].copy()
                proxy = candle_volume_delta_proxy(history_frame)
                if abs(proxy) < 20:
                    continue
                entry_price = safe_float(frame["close"].iloc[index])
                side = "LONG" if proxy > 0 else "SHORT"
                stop_price = entry_price * (0.98 if side == "LONG" else 1.02)
                target_price = entry_price * (1.03 if side == "LONG" else 0.97)
                outcome = "UNRESOLVED"
                future = frame.iloc[index + 1 : index + 6]
                for _, candle in future.iterrows():
                    high, low = safe_float(candle["high"]), safe_float(candle["low"])
                    hit_stop = low <= stop_price if side == "LONG" else high >= stop_price
                    hit_target = high >= target_price if side == "LONG" else low <= target_price
                    # Conservative tie-break: if both hit in one candle, count stop first.
                    if hit_stop:
                        outcome = "LOSS"
                        break
                    if hit_target:
                        outcome = "WIN"
                        break
                if outcome == "WIN":
                    wins += 1
                elif outcome == "LOSS":
                    losses += 1
                else:
                    unresolved += 1
                trades.append({
                    "index": index, "side": side, "entry": entry_price,
                    "outcome": outcome,
                })

            total = wins + losses
            win_rate = wins / total * 100 if total else 0
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("الإشارات", len(trades))
            c2.metric("رابحة", wins)
            c3.metric("خاسرة", losses)
            c4.metric("غير محسومة", unresolved)
            st.metric("نسبة الفوز من الصفقات المحسومة", f"{win_rate:.1f}%")
            if trades:
                st.dataframe(pd.DataFrame(trades), use_container_width=True)
            st.caption(
                "تنبيه: الاختبار يستخدم آخر 100 شمعة متاحة فقط، ولا يشمل رسوم التداول "
                "أو الانزلاق أو التمويل، ولا يمثل ضمانًا للأداء المستقبلي."
            )


st.markdown("---")
st.caption(
    "BLY7TRADER | Futures market data from public exchange APIs; outages/rate limits may occur. "
    "لا تنفّذ صفقة اعتمادًا على الإشارة وحدها؛ راجع السيولة والسبريد والمخاطرة."
)
