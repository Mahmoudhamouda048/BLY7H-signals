# BLY7TRADER — V19.1 interface / Futures intelligence (FIXED FULL)
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
    page_title="BLY7TRADER ULTIMATE V19.1",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_TITLE = "💎 BLY7TRADER — ULTIMATE V19.1"
DB_PATH = os.getenv("BLY7TRADER_DB", "bly7trader_memory.db")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BLY7TRADER/19.1"})
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
            "market_type": "TEXT DEFAULT 'FUTURES'",
            "status": "TEXT DEFAULT 'ENTRY_PENDING'", "entry_hit_at": "TEXT",
            "last_price": "REAL", "last_checked_at": "TEXT", "max_favorable_pct": "REAL DEFAULT 0",
            "max_adverse_pct": "REAL DEFAULT 0", "tp1_hit_at": "TEXT", "tp2_hit_at": "TEXT",
            "tp3_hit_at": "TEXT", "stop_hit_at": "TEXT", "trade_json": "TEXT",
            "timeframe": "TEXT", "leverage": "REAL DEFAULT 1", "entry_execution": "TEXT DEFAULT 'PRICE_TOUCH'"
        }
        for name, declaration in additions.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE signals ADD COLUMN {name} {declaration}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_outcome ON signals(outcome)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at)")
        conn.commit()


def calc_pnl_pct(side, entry, exit_price):
    if entry <= 0 or exit_price <= 0:
        return 0.0
    if side == "LONG":
        return (exit_price - entry) / entry * 100
    return (entry - exit_price) / entry * 100


def update_trade_outcome(signal_id, outcome):
    """Manual override remains available for corrections; auto tracker is primary."""
    if outcome not in ("WIN", "LOSS", "BREAKEVEN", "OPEN"):
        return
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT side, entry, stop, tp1, tp2, tp3 FROM signals WHERE id=?", (signal_id,)).fetchone()
        if not row:
            return
        side, entry, stop, tp1, tp2, tp3 = row
        if outcome == "WIN":
            # Manual WIN defaults to TP1 if no TP hit info, keep conservative
            pnl = calc_pnl_pct(side, entry, tp1)
        elif outcome == "LOSS":
            pnl = calc_pnl_pct(side, entry, stop)
        else:
            pnl = 0.0
        closed = None if outcome == "OPEN" else datetime.now(timezone.utc).isoformat()
        status = "ENTRY_PENDING" if outcome == "OPEN" else outcome
        conn.execute("UPDATE signals SET outcome=?, status=?, closed_at=?, pnl_pct=?, result_source='MANUAL' WHERE id=?",
                     (outcome, status, closed, pnl, signal_id))
        conn.commit()


def get_current_futures_price(exchange, symbol):
    """Fetch a live public mark/last price for an open futures signal."""
    try:
        if exchange == "BINANCE":
            data = api_json("https://fapi.binance.com/fapi/v1/ticker/price", {"symbol": symbol})
            return safe_float((data or {}).get("price"), 0) or None
        if exchange == "BYBIT":
            data = api_json("https://api.bybit.com/v5/market/tickers", {"category": "linear", "symbol": symbol})
            rows = (data or {}).get("result", {}).get("list", [])
            return safe_float(rows[0].get("lastPrice"), 0) if rows else None
        if exchange == "KUCOIN":
            data = api_json("https://api-futures.kucoin.com/api/v1/ticker", {"symbol": symbol})
            return safe_float((data or {}).get("data", {}).get("price"), 0) or None
        if exchange == "MEXC":
            data = api_json("https://contract.mexc.com/api/v1/contract/ticker", {"symbol": symbol})
            payload = (data or {}).get("data")
            if isinstance(payload, list):
                payload = payload[0] if payload else {}
            return safe_float((payload or {}).get("lastPrice"), 0) or None
    except Exception:
        return None
    return None


def track_open_trades():
    """Poll live prices and auto-resolve entry/TP/SL as theoretical price touches."""
    now = datetime.now(timezone.utc).isoformat()
    updated, errors = 0, []
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT id,exchange,symbol,side,entry,stop,tp1,tp2,tp3,status,last_price,max_favorable_pct,max_adverse_pct,entry_hit_at,tp1_hit_at,tp2_hit_at,tp3_hit_at,stop_hit_at FROM signals WHERE outcome='OPEN' ORDER BY id DESC LIMIT 500").fetchall()
        # Cache price per (exchange,symbol) to avoid duplicate API calls
        price_cache = {}
        for row in rows:
            (sid, exchange, symbol, side, entry, stop, tp1, tp2, tp3, status,
             old_price, max_fav, max_adv, entry_hit_at_old, tp1_hit_old, tp2_hit_old, tp3_hit_old, stop_hit_old) = row
            cache_key = (exchange, symbol)
            if cache_key not in price_cache:
                price_cache[cache_key] = get_current_futures_price(exchange, symbol)
            live = price_cache[cache_key]
            if not live or live <= 0:
                errors.append(f"{exchange}:{symbol}")
                continue
            entry, stop, tp1, tp2 = map(lambda x: safe_float(x), (entry, stop, tp1, tp2))
            tp3 = safe_float(tp3)
            if entry <= 0 or stop <= 0:
                continue
            stamp = datetime.now(timezone.utc).isoformat()
            if side == "LONG":
                favorable = (live - entry) / entry * 100
                adverse = (entry - live) / entry * 100
                entered = status != "ENTRY_PENDING" or live <= entry
                stop_hit = live <= stop
                hit1, hit2, hit3 = live >= tp1, live >= tp2, (tp3 > 0 and live >= tp3)
            else:
                favorable = (entry - live) / entry * 100
                adverse = (live - entry) / entry * 100
                entered = status != "ENTRY_PENDING" or live >= entry
                stop_hit = live >= stop
                hit1, hit2, hit3 = live <= tp1, live <= tp2, (tp3 > 0 and live <= tp3)
            # FIX: MFE/MAE only after entry
            if entered:
                max_fav = max(safe_float(max_fav), favorable)
                max_adv = max(safe_float(max_adv), adverse)
            else:
                max_fav = safe_float(max_fav)
                max_adv = safe_float(max_adv)
            new_status = status
            entry_hit_at = None
            closed_at = None
            outcome = "OPEN"
            pnl = None
            result_source = "LIVE_PRICE_TRACKER"
            if status == "ENTRY_PENDING" and entered:
                new_status = "IN_POSITION"
                entry_hit_at = stamp
            if entered:
                # Live floating PnL
                pnl_float = calc_pnl_pct(side, entry, live)
                # If a polling interval spans both SL and TP, conservatively prioritize SL.
                if stop_hit:
                    new_status, outcome, closed_at = "STOP_LOSS", "LOSS", stamp
                    # FIX: PnL at SL price, not live overshoot
                    pnl = calc_pnl_pct(side, entry, stop)
                elif hit3:
                    new_status, outcome, closed_at = "TP3_HIT", "WIN", stamp
                    pnl = calc_pnl_pct(side, entry, tp3)
                elif hit2:
                    new_status = "TP2_HIT"
                elif hit1:
                    new_status = "TP1_HIT"
                else:
                    pnl = None
            conn.execute("""UPDATE signals SET status=?, outcome=?, last_price=?, last_checked_at=?,
                entry_hit_at=COALESCE(entry_hit_at,?), tp1_hit_at=CASE WHEN ? THEN COALESCE(tp1_hit_at,?) ELSE tp1_hit_at END,
                tp2_hit_at=CASE WHEN ? THEN COALESCE(tp2_hit_at,?) ELSE tp2_hit_at END,
                tp3_hit_at=CASE WHEN ? THEN COALESCE(tp3_hit_at,?) ELSE tp3_hit_at END,
                stop_hit_at=CASE WHEN ? THEN COALESCE(stop_hit_at,?) ELSE stop_hit_at END,
                closed_at=COALESCE(?,closed_at), pnl_pct=COALESCE(?,pnl_pct),
                result_source=?, max_favorable_pct=?, max_adverse_pct=?
                WHERE id=?""",
                (new_status, outcome, live, stamp, entry_hit_at,
                 hit1, stamp, hit2, stamp, hit3, stamp, stop_hit, stamp,
                 closed_at, pnl if outcome != "OPEN" else None, result_source,
                 max_fav, max_adv, sid))
            updated += 1
        conn.commit()
    return updated, errors


def cornix_signal_text(signal, exchange, timeframe="15m", leverage=1):
    """Build a structured, Cornix-oriented signal message."""
    symbol = str(signal.get("symbol", "")).replace("/", "")
    side = signal.get("side", "LONG")
    entry = safe_float(signal.get("entry"))
    stop = safe_float(signal.get("stop"))
    tp1 = safe_float(signal.get("tp1"))
    tp2 = safe_float(signal.get("tp2"))
    tp3 = safe_float(signal.get("tp3"))
    if not symbol or not entry or not stop:
        return ""
    return (
        f"{symbol} {side}\n"
        f"Exchange: {exchange} | Market: FUTURES\n"
        f"Entry: {entry:.10g}\n"
        f"Stop: {stop:.10g}\n"
        f"Take-Profit: {tp1:.10g}, {tp2:.10g}, {tp3:.10g}\n"
        f"Leverage: {leverage}x\n"
        f"Timeframe: {timeframe}\n"
        f"Score: {signal.get('score', 0)}\n"
        f"RSI: {safe_float(signal.get('rsi')):.2f} | "
        f"EMA9: {safe_float(signal.get('ema9')):.10g} | "
        f"EMA21: {safe_float(signal.get('ema21')):.10g}\n"
        f"MACD: {safe_float(signal.get('macd')):.8g} | "
        f"ATR: {safe_float(signal.get('atr')):.8g}\n"
        f"Funding: {safe_float(signal.get('funding_pct')):.5f}% | "
        f"OI Change: {safe_float(signal.get('oi_change_pct')):.3f}%\n"
        f"CVD: {safe_float(signal.get('cvd')):.4f} "
        f"({signal.get('cvd_source', 'proxy')})\n"
        f"Liquidity: {signal.get('liquidity_note', 'N/A')}\n"
        f"Generated: {signal.get('created_at', datetime.now(timezone.utc).isoformat())}"
    )


def learning_profile():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT outcome, COUNT(*), AVG(pnl_pct) FROM signals "
            "WHERE outcome IN ('WIN','LOSS','BREAKEVEN') GROUP BY outcome"
        ).fetchall()
        total = sum(row[1] for row in rows)
        wins = sum(row[1] for row in rows if row[0] == "WIN")
        avg_pnl = conn.execute(
            "SELECT AVG(pnl_pct) FROM signals WHERE outcome IN ('WIN','LOSS','BREAKEVEN')"
        ).fetchone()[0]
    return {
        "total": total,
        "wins": wins,
        "losses": sum(row[1] for row in rows if row[0] == "LOSS"),
        "breakeven": sum(row[1] for row in rows if row[0] == "BREAKEVEN"),
        "win_rate": (wins / total * 100) if total else 0,
        "average_pnl": safe_float(avg_pnl),
    }


def save_signals(signals, exchange):
    if not signals:
        return 0
    saved = 0
    with sqlite3.connect(DB_PATH) as conn:
        for signal in signals:
            symbol = str(signal.get("symbol", ""))
            side = str(signal.get("side", ""))
            timeframe = str(signal.get("timeframe", "15m"))
            if not symbol or side not in ("LONG", "SHORT"):
                continue
            exists = conn.execute(
                "SELECT id FROM signals WHERE exchange=? AND symbol=? AND side=? AND timeframe=? "
                "AND created_at >= datetime('now','-20 minutes')",
                (exchange, symbol, side, timeframe),
            ).fetchone()
            if exists:
                continue
            created = signal.get("created_at", datetime.now(timezone.utc).isoformat())
            details = json.dumps(signal, ensure_ascii=False, default=str)
            conn.execute(
                """INSERT INTO signals
                (created_at,exchange,symbol,side,score,price,entry,stop,tp1,tp2,
                 change_pct,volume_ratio,cvd_proxy,tp3,funding_pct,oi_change_pct,
                 market_type,status,last_price,trade_json,timeframe,leverage)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    created, exchange, symbol, side, int(signal.get("score", 0)),
                    safe_float(signal.get("price")), safe_float(signal.get("entry")),
                    safe_float(signal.get("stop")), safe_float(signal.get("tp1")),
                    safe_float(signal.get("tp2")), safe_float(signal.get("change_pct")),
                    safe_float(signal.get("volume_ratio")), safe_float(signal.get("cvd")),
                    safe_float(signal.get("tp3")), safe_float(signal.get("funding_pct")),
                    safe_float(signal.get("oi_change_pct")), "FUTURES", "ENTRY_PENDING",
                    safe_float(signal.get("price")), details,
                    timeframe, safe_float(signal.get("leverage"), 1),
                ),
            )
            saved += 1
        conn.commit()
    return saved


def load_signal_history(limit=100):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT * FROM signals ORDER BY id DESC LIMIT ?",
            conn, params=(int(limit),),
        )


def send_telegram(message):
    token = st.secrets.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_id = st.secrets.get(
        "TELEGRAM_CHANNEL_ID",
        os.getenv("TELEGRAM_CHANNEL_ID", os.getenv("TELEGRAM_CHAT_ID", "")),
    )
    if not token or not chat_id:
        return False, "Telegram غير مضبوط"
    try:
        response = SESSION.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return True, "تم الإرسال"
    except requests.RequestException as exc:
        return False, str(exc)


def format_telegram(signal):
    return cornix_signal_text(
        signal,
        signal.get("exchange", "FUTURES"),
        signal.get("timeframe", "15m"),
        signal.get("leverage", 1),
    )


def send_signal_batch(signals):
    sent = 0
    for signal in signals:
        ok, _ = send_telegram(format_telegram(signal))
        sent += int(ok)
    return sent


# ----------------------------- Indicators -----------------------------

def add_indicators(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close", "volume"])
    if len(df) < 30:
        return pd.DataFrame()

    close = df["close"]
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["rsi"] = (100 - 100 / (1 + rs)).fillna(50)

    df["ema9"] = close.ewm(span=9, adjust=False).mean()
    df["ema21"] = close.ewm(span=21, adjust=False).mean()
    df["ema200"] = close.ewm(span=200, adjust=False).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    previous_close = close.shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - previous_close).abs(),
        (df["low"] - previous_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
    df["momentum"] = close.pct_change(10) * 100

    df["volume_avg"] = df["volume"].rolling(20).mean()
    df["volume_ratio"] = (
        df["volume"] / df["volume_avg"].replace(0, float("nan"))
    ).replace([float("inf"), -float("inf")], 0).fillna(0)

    signed_volume = df["volume"] * (
        (df["close"] - df["open"]) /
        (df["high"] - df["low"]).replace(0, float("nan"))
    )
    df["cvd_proxy"] = signed_volume.fillna(0).cumsum()
    return df


def market_structure(df):
    if df is None or len(df) < 25:
        return {"bsl": None, "ssl": None, "fvg": False, "ob": False,
                "sweep_high": False, "sweep_low": False}
    recent = df.tail(25)
    prior = recent.iloc[:-1]
    last = recent.iloc[-1]
    bsl = safe_float(prior["high"].max())
    ssl = safe_float(prior["low"].min())
    sweep_high = last["high"] > bsl and last["close"] < bsl
    sweep_low = last["low"] < ssl and last["close"] > ssl

    fvg_bull = False
    fvg_bear = False
    if len(df) >= 3:
        a, c = df.iloc[-3], df.iloc[-1]
        fvg_bull = c["low"] > a["high"]
        fvg_bear = c["high"] < a["low"]

    last_body = abs(last["close"] - last["open"])
    avg_body = (df["close"] - df["open"]).abs().tail(20).mean()
    ob = bool(last_body > safe_float(avg_body) * 1.5)

    return {
        "bsl": bsl, "ssl": ssl,
        "fvg": bool(fvg_bull or fvg_bear),
        "fvg_bull": bool(fvg_bull),
        "fvg_bear": bool(fvg_bear),
        "ob": ob,
        "sweep_high": bool(sweep_high),
        "sweep_low": bool(sweep_low),
    }


# ----------------------------- Futures APIs -----------------------------

def binance_futures_symbols(limit=100):
    data = api_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
    if not isinstance(data, list):
        return []
    rows = []
    for item in data:
        symbol = item.get("symbol", "")
        if not symbol.endswith("USDT") or symbol in STABLES:
            continue
        if safe_float(item.get("quoteVolume")) < 2_000_000:
            continue
        rows.append((symbol, safe_float(item.get("quoteVolume"))))
    rows.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in rows[:limit]]


def binance_futures_klines(symbol, interval="5m", limit=300):
    data = api_json(
        "https://fapi.binance.com/fapi/v1/klines",
        {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)},
    )
    if not isinstance(data, list) or not data:
        return pd.DataFrame()
    cols = ["time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy",
            "taker_quote", "ignore"]
    df = pd.DataFrame(data, columns=cols)
    df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    return df[["time", "open", "high", "low", "close", "volume"]]


def bybit_futures_symbols(limit=100):
    data = api_json(
        "https://api.bybit.com/v5/market/tickers",
        {"category": "linear"},
    )
    rows = (data or {}).get("result", {}).get("list", [])
    ranked = []
    for item in rows:
        symbol = item.get("symbol", "")
        if symbol.endswith("USDT") and safe_float(item.get("turnover24h")) >= 2_000_000:
            ranked.append((symbol, safe_float(item.get("turnover24h"))))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in ranked[:limit]]


def bybit_futures_klines(symbol, interval="5", limit=300):
    interval_map = {"1m": "1", "3m": "3", "5m": "5",
                    "15m": "15", "1h": "60", "4h": "240", "1d": "D"}
    data = api_json(
        "https://api.bybit.com/v5/market/kline",
        {"category": "linear", "symbol": symbol,
         "interval": interval_map.get(interval, interval),
         "limit": min(limit, 1000)},
    )
    rows = (data or {}).get("result", {}).get("list", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[
        "time", "open", "high", "low", "close", "volume", "turnover"
    ])
    df["time"] = pd.to_datetime(pd.to_numeric(df["time"]), unit="ms", utc=True)
    return df[["time", "open", "high", "low", "close", "volume"]].sort_values("time")


def kucoin_futures_symbols(limit=100):
    data = api_json("https://api-futures.kucoin.com/api/v1/contracts/active")
    rows = (data or {}).get("data", [])
    ranked = []
    for item in rows:
        symbol = item.get("symbol", "")
        if "USDTM" in symbol:
            ranked.append((symbol, safe_float(item.get("volumeOf24h"))))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in ranked[:limit]]


def kucoin_futures_klines(symbol, interval="5m", limit=300):
    granularity = {"1m": 1, "3m": 3, "5m": 5,
                   "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
    minutes = granularity.get(interval, 5)
    end = int(time.time())
    start = end - minutes * 60 * min(limit, 500)
    data = api_json(
        "https://api-futures.kucoin.com/api/v1/kline/query",
        {"symbol": symbol, "granularity": minutes,
         "from": start, "to": end},
    )
    rows = (data or {}).get("data", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=[
        "time", "open", "high", "low", "close", "volume", "turnover"
    ])
    df["time"] = pd.to_datetime(pd.to_numeric(df["time"]), unit="s", utc=True)
    return df[["time", "open", "high", "low", "close", "volume"]].sort_values("time").tail(limit)


def mexc_futures_symbols(limit=100):
    data = api_json("https://contract.mexc.com/api/v1/contract/ticker")
    rows = (data or {}).get("data", [])
    ranked = []
    for item in rows:
        symbol = item.get("symbol", "")
        if symbol.endswith("_USDT"):
            ranked.append((symbol, safe_float(item.get("amount24"))))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in ranked[:limit]]


def mexc_futures_klines(symbol, interval="Min5", limit=300):
    interval_map = {
        "1m": "Min1", "3m": "Min3", "5m": "Min5",
        "15m": "Min15", "1h": "Min60", "4h": "Hour4", "1d": "Day1"
    }
    end = int(time.time())
    seconds = {"1m": 60, "3m": 180, "5m": 300,
               "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
    start = end - seconds.get(interval, 300) * min(limit, 1500)
    data = api_json(
        "https://contract.mexc.com/api/v1/contract/kline/" + symbol,
        {"interval": interval_map.get(interval, interval),
         "start": start, "end": end},
    )
    payload = (data or {}).get("data", {})
    if not isinstance(payload, dict) or not payload.get("time"):
        return pd.DataFrame()
    df = pd.DataFrame({
        "time": payload["time"], "open": payload["open"],
        "high": payload["high"], "low": payload["low"],
        "close": payload["close"], "volume": payload["vol"],
    })
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df.tail(limit)


def fetch_futures_symbols(exchange, limit=100):
    funcs = {
        "BINANCE": binance_futures_symbols,
        "BYBIT": bybit_futures_symbols,
        "KUCOIN": kucoin_futures_symbols,
        "MEXC": mexc_futures_symbols,
    }
    try:
        return funcs[exchange](limit)
    except Exception:
        return []


def fetch_futures_klines(exchange, symbol, timeframe="5m", limit=300):
    funcs = {
        "BINANCE": binance_futures_klines,
        "BYBIT": bybit_futures_klines,
        "KUCOIN": kucoin_futures_klines,
        "MEXC": mexc_futures_klines,
    }
    try:
        return funcs[exchange](symbol, timeframe, limit)
    except Exception:
        return pd.DataFrame()


def fetch_funding(exchange, symbol):
    try:
        if exchange == "BINANCE":
            d = api_json("https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol": symbol})
            return safe_float((d or {}).get("lastFundingRate")) * 100
        if exchange == "BYBIT":
            d = api_json("https://api.bybit.com/v5/market/funding/history",
                         {"category": "linear", "symbol": symbol, "limit": 1})
            rows = (d or {}).get("result", {}).get("list", [])
            return safe_float(rows[0].get("fundingRate")) * 100 if rows else None
        if exchange == "KUCOIN":
            d = api_json("https://api-futures.kucoin.com/api/v1/funding-rate/" + symbol + "/current")
            return safe_float((d or {}).get("data", {}).get("value")) * 100
        if exchange == "MEXC":
            d = api_json("https://contract.mexc.com/api/v1/contract/funding_rate/" + symbol)
            return safe_float((d or {}).get("data", {}).get("fundingRate")) * 100
    except Exception:
        pass
    return None


def fetch_open_interest_change(exchange, symbol):
    try:
        if exchange == "BINANCE":
            d = api_json("https://fapi.binance.com/futures/data/openInterestHist",
                         {"symbol": symbol, "period": "5m", "limit": 2})
            if isinstance(d, list) and len(d) >= 2:
                old = safe_float(d[0].get("sumOpenInterestValue"))
                new = safe_float(d[-1].get("sumOpenInterestValue"))
                return (new / old - 1) * 100 if old else None
        if exchange == "BYBIT":
            d = api_json("https://api.bybit.com/v5/market/open-interest",
                         {"category": "linear", "symbol": symbol, "intervalTime": "5min", "limit": 2})
            rows = (d or {}).get("result", {}).get("list", [])
            if len(rows) >= 2:
                old = safe_float(rows[-1].get("openInterest"))
                new = safe_float(rows[0].get("openInterest"))
                return (new / old - 1) * 100 if old else None
    except Exception:
        pass
    return None


def fetch_orderbook_imbalance(exchange, symbol):
    try:
        if exchange == "BINANCE":
            d = api_json("https://fapi.binance.com/fapi/v1/depth",
                         {"symbol": symbol, "limit": 20})
            bids, asks = (d or {}).get("bids", []), (d or {}).get("asks", [])
        elif exchange == "BYBIT":
            d = api_json("https://api.bybit.com/v5/market/orderbook",
                         {"category": "linear", "symbol": symbol, "limit": 25})
            book = (d or {}).get("result", {})
            bids, asks = book.get("b", []), book.get("a", [])
        else:
            return None
        bid_qty = sum(safe_float(x[1]) for x in bids)
        ask_qty = sum(safe_float(x[1]) for x in asks)
        total = bid_qty + ask_qty
        return ((bid_qty - ask_qty) / total * 100) if total else None
    except Exception:
        return None


def build_trade_signal(exchange, symbol, timeframe="5m", limit=300, leverage=1):
    raw = fetch_futures_klines(exchange, symbol, timeframe, limit)
    df = add_indicators(raw)
    if df.empty or len(df) < 30:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = safe_float(last["close"])
    atr = safe_float(last["atr"])
    if price <= 0 or atr <= 0:
        return None

    structure = market_structure(df)
    funding = fetch_funding(exchange, symbol)
    oi_change = fetch_open_interest_change(exchange, symbol)
    imbalance = fetch_orderbook_imbalance(exchange, symbol)
    in_killzone, killzone_name = killzone_status()

    long_score = 0
    short_score = 0
    reasons_long, reasons_short = [], []

    if last["ema9"] > last["ema21"]:
        long_score += 2
        reasons_long.append("EMA9 أعلى EMA21")
    if last["ema9"] < last["ema21"]:
        short_score += 2
        reasons_short.append("EMA9 أسفل EMA21")
    if last["close"] > last["ema200"]:
        long_score += 1
        reasons_long.append("السعر أعلى EMA200")
    if last["close"] < last["ema200"]:
        short_score += 1
        reasons_short.append("السعر أسفل EMA200")
    if last["rsi"] >= 55 and last["rsi"] < 75:
        long_score += 1
        reasons_long.append("RSI يدعم الصعود")
    if last["rsi"] <= 45 and last["rsi"] > 25:
        short_score += 1
        reasons_short.append("RSI يدعم الهبوط")
    if last["macd_hist"] > 0:
        long_score += 1
        reasons_long.append("MACD إيجابي")
    if last["macd_hist"] < 0:
        short_score += 1
        reasons_short.append("MACD سلبي")
    if last["volume_ratio"] >= 1.5:
        long_score += 1
        short_score += 1
    if structure["sweep_low"]:
        long_score += 2
        reasons_long.append("سحب سيولة أسفل القاع ثم إغلاق أعلى")
    if structure["sweep_high"]:
        short_score += 2
        reasons_short.append("سحب سيولة أعلى القمة ثم إغلاق أسفل")
    if structure.get("fvg_bull"):
        long_score += 1
        reasons_long.append("Bullish FVG")
    if structure.get("fvg_bear"):
        short_score += 1
        reasons_short.append("Bearish FVG")
    if imbalance is not None:
        if imbalance > 15:
            long_score += 1
            reasons_long.append("دفتر الأوامر يميل للشراء")
        elif imbalance < -15:
            short_score += 1
            reasons_short.append("دفتر الأوامر يميل للبيع")
    if oi_change is not None and oi_change > 0.5:
        if last["close"] > prev["close"]:
            long_score += 1
            reasons_long.append("ارتفاع OI مع صعود السعر")
        elif last["close"] < prev["close"]:
            short_score += 1
            reasons_short.append("ارتفاع OI مع هبوط السعر")
    if in_killzone:
        # Small boost only, not decisive
        long_score += 0
        short_score += 0

    side = "LONG" if long_score >= short_score else "SHORT"
    score = max(long_score, short_score)
    if score < 5:
        return None

    is_long = side == "LONG"
    entry = price
    stop = price - atr * 1.5 if is_long else price + atr * 1.5
    risk = abs(entry - stop)
    tp1 = entry + risk if is_long else entry - risk
    tp2 = entry + risk * 2 if is_long else entry - risk * 2
    tp3 = entry + risk * 3 if is_long else entry - risk * 3

    return {
        "symbol": symbol, "exchange": exchange, "side": side,
        "score": int(score), "price": price, "entry": entry,
        "stop": stop, "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "rsi": safe_float(last["rsi"]), "ema9": safe_float(last["ema9"]),
        "ema21": safe_float(last["ema21"]), "ema200": safe_float(last["ema200"]),
        "macd": safe_float(last["macd"]), "atr": atr,
        "momentum": safe_float(last["momentum"]),
        "volume_ratio": safe_float(last["volume_ratio"]),
        "cvd": safe_float(last["cvd_proxy"]), "cvd_source": "CANDLE_PROXY",
        "funding_pct": funding if funding is not None else 0,
        "oi_change_pct": oi_change if oi_change is not None else 0,
        "orderbook_imbalance": imbalance,
        "bsl": structure["bsl"], "ssl": structure["ssl"],
        "fvg": structure["fvg"], "order_block_heuristic": structure["ob"],
        "sweep_high": structure["sweep_high"], "sweep_low": structure["sweep_low"],
        "reasons": reasons_long if is_long else reasons_short,
        "change_pct": safe_float((last["close"] / df.iloc[-2]["close"] - 1) * 100),
        "timeframe": timeframe,
        "leverage": safe_float(leverage, 1),
        "killzone": killzone_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "liquidity_note": "BSL/SSL تقديرات من الشموع وليست خريطة تصفيات فعلية",
    }


# ----------------------------- Pump / Dump Scanner -----------------------------

def scan_pump_dump(exchange="BINANCE", limit=80, timeframe="5m"):
    symbols = fetch_futures_symbols(exchange, limit)
    results = []
    for symbol in symbols:
        try:
            df = add_indicators(fetch_futures_klines(exchange, symbol, timeframe, 100))
            if df.empty or len(df) < 30:
                continue
            last = df.iloc[-1]
            prev = df.iloc[-2]
            price_change = safe_float((last["close"] / prev["close"] - 1) * 100)
            volume_ratio = safe_float(last["volume_ratio"])
            cvd = safe_float(last["cvd_proxy"])
            rsi = safe_float(last["rsi"])
            trend_up = last["ema9"] > last["ema21"]
            trend_down = last["ema9"] < last["ema21"]

            pump_score = 0
            dump_score = 0
            pump_reasons, dump_reasons = [], []

            if price_change >= 1:
                pump_score += 2
                pump_reasons.append("ارتفاع سعري سريع")
            if price_change <= -1:
                dump_score += 2
                dump_reasons.append("هبوط سعري سريع")
            if volume_ratio >= 2:
                pump_score += 2
                dump_score += 2
                pump_reasons.append("حجم تداول استثنائي")
                dump_reasons.append("حجم تداول استثنائي")
            if trend_up:
                pump_score += 1
                pump_reasons.append("اتجاه EMA صاعد")
            if trend_down:
                dump_score += 1
                dump_reasons.append("اتجاه EMA هابط")
            if cvd > 0:
                pump_score += 1
            elif cvd < 0:
                dump_score += 1
            if rsi >= 55:
                pump_score += 1
            if rsi <= 45:
                dump_score += 1

            if pump_score >= 4 and pump_score > dump_score:
                kind, score, reasons = "PUMP", pump_score, pump_reasons
            elif dump_score >= 4 and dump_score > pump_score:
                kind, score, reasons = "DUMP", dump_score, dump_reasons
            else:
                continue

            results.append({
                "exchange": exchange, "symbol": symbol,
                "type": kind, "score": score,
                "price": safe_float(last["close"]),
                "change_pct": price_change,
                "volume_ratio": volume_ratio,
                "rsi": rsi, "reasons": "، ".join(reasons),
                "time": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            continue
    return sorted(results, key=lambda x: x["score"], reverse=True)


# ----------------------------- DEX Scanner -----------------------------

def dex_search_pairs(query=""):
    url = "https://api.dexscreener.com/latest/dex/search"
    data = api_json(url, {"q": query or "BSC"})
    pairs = (data or {}).get("pairs", [])
    return pairs if isinstance(pairs, list) else []


def dex_latest_profiles():
    try:
        response = SESSION.get(
            "https://api.dexscreener.com/token-profiles/latest/v1",
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def dex_pair_metrics(pair):
    price_change = pair.get("priceChange") or {}
    volume = pair.get("volume") or {}
    liquidity = pair.get("liquidity") or {}
    txns = pair.get("txns") or {}
    m5 = txns.get("m5") or {}
    h1 = txns.get("h1") or {}
    buys5 = safe_float(m5.get("buys"))
    sells5 = safe_float(m5.get("sells"))
    buys1 = safe_float(h1.get("buys"))
    sells1 = safe_float(h1.get("sells"))
    buy_sell = buys5 / max(sells5, 1)
    liq = safe_float(liquidity.get("usd"))
    vol5 = safe_float(volume.get("m5"))
    vol1 = safe_float(volume.get("h1"))
    change5 = safe_float(price_change.get("m5"))
    change1 = safe_float(price_change.get("h1"))
    return {
        "change5": change5, "change1": change1,
        "volume5": vol5, "volume1": vol1,
        "liquidity": liq, "buys5": buys5, "sells5": sells5,
        "buys1": buys1, "sells1": sells1,
        "buy_sell_ratio": buy_sell,
    }


def scan_dex(chain="bsc", limit=80, min_liquidity=10000):
    candidates = []
    seen = set()
    queries = ["WBNB", "USDT", "BSC"]
    for query in queries:
        for pair in dex_search_pairs(query):
            if pair.get("chainId", "").lower() != chain.lower():
                continue
            pair_id = pair.get("pairAddress")
            if pair_id and pair_id not in seen:
                seen.add(pair_id)
                candidates.append(pair)

    profiles = dex_latest_profiles()[:20]
    for profile in profiles:
        if profile.get("chainId", "").lower() != chain.lower():
            continue
        token_address = profile.get("tokenAddress")
        if not token_address:
            continue
        url = f"https://api.dexscreener.com/token-pairs/v1/{chain}/{token_address}"
        try:
            response = SESSION.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            pairs = response.json()
            if isinstance(pairs, list):
                for pair in pairs:
                    pair_id = pair.get("pairAddress")
                    if pair_id and pair_id not in seen:
                        seen.add(pair_id)
                        candidates.append(pair)
        except Exception:
            continue

    results = []
    for pair in candidates:
        try:
            metrics = dex_pair_metrics(pair)
            liq = metrics["liquidity"]
            if liq < min_liquidity:
                continue

            base = pair.get("baseToken") or {}
            quote = pair.get("quoteToken") or {}
            price = safe_float(pair.get("priceUsd"))
            if price <= 0:
                continue

            vol_liq = metrics["volume1"] / liq if liq else 0
            score = 0
            reasons = []
            if metrics["change5"] >= 5:
                score += 2
                reasons.append("ارتفاع 5 دقائق")
            if metrics["change5"] <= -5:
                score += 2
                reasons.append("هبوط 5 دقائق")
            if metrics["volume5"] >= 10000:
                score += 2
                reasons.append("حجم تداول ملحوظ")
            if metrics["buy_sell_ratio"] >= 1.5:
                score += 2
                reasons.append("ضغط شراء")
            elif metrics["buy_sell_ratio"] <= 0.67:
                score += 2
                reasons.append("ضغط بيع")
            if vol_liq >= 0.2:
                score += 1
                reasons.append("نشاط مرتفع مقارنة بالسيولة")

            if score < 3:
                continue

            kind = "PUMP WATCH" if metrics["change5"] > 0 else "DUMP WATCH"
            results.append({
                "chain": chain.upper(),
                "dex": pair.get("dexId", ""),
                "symbol": base.get("symbol", ""),
                "name": base.get("name", ""),
                "address": base.get("address", ""),
                "pair": pair.get("pairAddress", ""),
                "url": pair.get("url", ""),
                "quote": quote.get("symbol", ""),
                "price": price,
                "change5": metrics["change5"],
                "change1": metrics["change1"],
                "volume5": metrics["volume5"],
                "volume1": metrics["volume1"],
                "liquidity": liq,
                "buys5": metrics["buys5"],
                "sells5": metrics["sells5"],
                "buy_sell_ratio": metrics["buy_sell_ratio"],
                "score": score,
                "type": kind,
                "reasons": "، ".join(reasons),
            })
        except Exception:
            continue

    return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]


# ----------------------------- Historical / Learning -----------------------------

def update_learning_score():
    profile = learning_profile()
    if profile["total"] < 10:
        return 0
    return max(-2, min(2, round((profile["win_rate"] - 50) / 20, 1)))


def get_signal_details(signal_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT * FROM signals WHERE id=?", (int(signal_id),)
        ).fetchone()
        columns = [x[1] for x in conn.execute("PRAGMA table_info(signals)")]
    return dict(zip(columns, row)) if row else None


def export_trade_records():
    history = load_signal_history(1000)
    if history.empty:
        return ""
    return history.to_csv(index=False)


def render_learning_section():
    st.subheader("🧠 الذاكرة الدائمة والتعلم من نتائج الصفقات")
    profile = learning_profile()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي الصفقات المحسومة", profile["total"])
    c2.metric("نسبة الفوز", f"{profile['win_rate']:.1f}%")
    c3.metric("الصفقات الرابحة", profile["wins"])
    c4.metric("متوسط العائد", f"{profile['average_pnl']:.2f}%")

    st.caption(
        "تُحدّث النتائج آليًا عند لمس السعر لمستوى الدخول أو TP3 أو SL. "
        "اللمس السعري لا يثبت تنفيذ أمر فعلي في حساب التداول."
    )
    history = load_signal_history(200)
    if history.empty:
        st.info("لا توجد صفقات محفوظة حتى الآن.")
        return

    display_cols = [
        c for c in [
            "id", "created_at", "exchange", "symbol", "side", "score",
            "price", "entry", "stop", "tp1", "tp2", "tp3", "last_price",
            "status", "outcome", "pnl_pct", "last_checked_at",
        ] if c in history.columns
    ]
    st.dataframe(history[display_cols], use_container_width=True, hide_index=True)

    st.markdown("#### تفاصيل صفقة أو تصحيح نتيجة")
    ids = history["id"].tolist()
    selected_id = st.selectbox("رقم الصفقة", ids, key="learning_trade_id")
    detail = get_signal_details(selected_id)
    if detail:
        st.json(detail)
    correction = st.selectbox(
        "تصحيح يدوي عند الحاجة",
        ["بدون تغيير", "WIN", "LOSS", "BREAKEVEN", "OPEN"],
        key="learning_correction",
    )
    if st.button("حفظ التصحيح", key="save_learning_correction"):
        if correction != "بدون تغيير":
            update_trade_outcome(selected_id, correction)
            st.success("تم حفظ التصحيح.")
            st.rerun()

    csv_data = export_trade_records()
    if csv_data:
        st.download_button(
            "تنزيل سجل الصفقات CSV",
            data=csv_data,
            file_name="BLY7TRADER_trade_history.csv",
            mime="text/csv",
        )


# ----------------------------- Main UI -----------------------------

def render_market_scanner():
    st.subheader("🔎 Futures Scanner — ماسح العقود")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        exchange = st.selectbox(
            "المنصة",
            ["BINANCE", "KUCOIN", "BYBIT", "MEXC"],
            key="scan_exchange",
        )
    with c2:
        timeframe = st.selectbox(
            "الإطار الزمني",
            ["1m", "3m", "5m", "15m", "1h", "4h"],
            index=2,
            key="scan_timeframe",
        )
    with c3:
        limit = st.slider("عدد العملات", 10, 100, 40, 10, key="scan_limit")
    with c4:
        min_score = st.slider("أقل قوة للإشارة", 3, 10, 5, key="scan_min_score")
    leverage = st.slider("الرافعة للعرض في Cornix (عرض فقط)", 1, 50, 10, key="scan_leverage")
    kz_active, kz_name = killzone_status()
    st.caption(f"Killzone: {kz_name} — {'داخل النافذة' if kz_active else 'خارج النافذة'}")

    if st.button("🚀 افحص السوق الآن", type="primary", key="run_futures_scan"):
        with st.spinner("جاري فحص عقود Futures وجمع البيانات..."):
            symbols = fetch_futures_symbols(exchange, limit)
            results = []
            progress = st.progress(0)
            status = st.empty()
            for index, symbol in enumerate(symbols):
                status.text(f"فحص {symbol} — {index + 1}/{len(symbols)}")
                signal = build_trade_signal(exchange, symbol, timeframe, 300, leverage=leverage)
                if signal and signal["score"] >= min_score:
                    results.append(signal)
                progress.progress((index + 1) / max(len(symbols), 1))
            status.empty()
            progress.empty()

        results.sort(key=lambda x: x["score"], reverse=True)
        st.session_state["latest_signals"] = results
        saved = save_signals(results, exchange)
        st.success(
            f"انتهى الفحص: {len(results)} إشارة مطابقة، "
            f"وتم حفظ {saved} إشارة جديدة."
        )
        if results and st.button("📩 إرسال الكل لتليجرام", key="send_all_telegram"):
            sent = send_signal_batch(results)
            st.info(f"تم إرسال {sent}/{len(results)} إشارة")

    results = st.session_state.get("latest_signals", [])
    if not results:
        st.info("اضغط افحص السوق الآن لبدء البحث عن فرص.")
        return

    for signal in results:
        title = (
            f"{'🟢' if signal['side'] == 'LONG' else '🔴'} "
            f"{signal['symbol']} — {signal['side']} — "
            f"Score {signal['score']}"
        )
        with st.expander(title, expanded=True):
            a, b, c = st.columns(3)
            a.metric("السعر الحالي وقت الفحص", f"{signal['price']:.10g}")
            b.metric("RSI", f"{signal['rsi']:.2f}")
            c.metric("نسبة الحجم", f"{signal['volume_ratio']:.2f}x")

            x, y, z = st.columns(3)
            x.metric("Entry", f"{signal['entry']:.10g}")
            y.metric("Stop Loss", f"{signal['stop']:.10g}")
            z.metric("Funding", f"{signal['funding_pct']:.5f}%")

            st.markdown(
                f"""
                **TP1:** `{signal['tp1']:.10g}`  
                **TP2:** `{signal['tp2']:.10g}`  
                **TP3:** `{signal['tp3']:.10g}`  
                **EMA9 / EMA21:** `{signal['ema9']:.8g}` / `{signal['ema21']:.8g}`  
                **MACD:** `{signal['macd']:.8g}`  
                **ATR:** `{signal['atr']:.8g}`  
                **OI Change:** `{signal['oi_change_pct']:.4f}%`  
                **CVD:** `{signal['cvd']:.4f}` — `{signal['cvd_source']}`  
                **Order Book Imbalance:** `{signal['orderbook_imbalance']}`  
                **BSL:** `{signal['bsl']}` | **SSL:** `{signal['ssl']}`
                """
            )
            st.write("**أسباب الإشارة:**", " — ".join(signal["reasons"]))
            cornix_text = cornix_signal_text(
                signal, exchange, timeframe, signal.get("leverage", leverage)
            )
            st.text_area(
                "صيغة الإشارة المتوافقة مع إعدادات Cornix",
                value=cornix_text,
                height=220,
                key=f"cornix_{exchange}_{signal['symbol']}_{signal['side']}",
            )
            st.caption(
                "CVD هنا تقديري من اتجاه الشمعة وحجمها، "
                "وليس CVD مبنيًا على سجل كل صفقة منفردة."
            )


def render_pump_dump():
    st.subheader("🚨 Pump / Dump — ماسح المضخات والتفريغ")
    c1, c2, c3 = st.columns(3)
    with c1:
        exchange = st.selectbox(
            "منصة العقود",
            ["BINANCE", "KUCOIN", "BYBIT", "MEXC"],
            key="pump_exchange",
        )
    with c2:
        limit = st.slider(
            "عدد العملات للفحص", 10, 100, 50, 10,
            key="pump_limit",
        )
    with c3:
        timeframe = st.selectbox(
            "إطار المضخة والتفريغ",
            ["1m", "5m", "15m"],
            index=1,
            key="pump_timeframe",
        )

    if st.button("⚡ ابدأ فحص Pump / Dump", key="run_pump_scan"):
        with st.spinner("تحليل تغير السعر والحجم والاتجاه..."):
            results = scan_pump_dump(exchange, limit, timeframe)
        st.session_state["pump_results"] = results
        st.success(f"تم الفحص. عدد الحالات المكتشفة: {len(results)}")

    results = st.session_state.get("pump_results", [])
    if results:
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد نتائج معروضة. ابدأ الفحص أولًا.")


def render_dex_scanner():
    st.subheader("🌐 DEX Scanner — فحص السيولة والنشاط")
    c1, c2, c3 = st.columns(3)
    with c1:
        chain = st.selectbox(
            "الشبكة", ["bsc", "ethereum", "base", "solana"],
            key="dex_chain",
        )
    with c2:
        minimum_liquidity = st.number_input(
            "أقل سيولة بالدولار",
            min_value=1000,
            max_value=10000000,
            value=10000,
            step=1000,
            key="dex_min_liquidity",
        )
    with c3:
        limit = st.slider(
            "عدد النتائج", 10, 100, 40, 10,
            key="dex_limit",
        )

    if st.button("🔍 افحص DEX الآن", key="run_dex_scan"):
        with st.spinner("جاري جمع أزواج التداول وفحص السيولة والحجم..."):
            results = scan_dex(chain, limit, minimum_liquidity)
        st.session_state["dex_results"] = results
        st.success(f"تم العثور على {len(results)} زوجًا مطابقًا.")

    results = st.session_state.get("dex_results", [])
    if results:
        for item in results:
            with st.expander(
                f"{item['symbol']} — {item['type']} — Score {item['score']}"
            ):
                a, b, c = st.columns(3)
                a.metric("السعر بالدولار", f"{item['price']:.10g}")
                b.metric("التغير 5 دقائق", f"{item['change5']:.2f}%")
                c.metric("السيولة", f"${item['liquidity']:,.0f}")
                st.write(f"**DEX:** {item['dex']} | **Quote:** {item['quote']}")
                st.write(f"**الحجم 5 دقائق:** ${item['volume5']:,.2f}")
                st.write(f"**الحجم ساعة:** ${item['volume1']:,.2f}")
                st.write(
                    f"**شراء 5 دقائق:** {item['buys5']} | "
                    f"**بيع 5 دقائق:** {item['sells5']}"
                )
                st.write(f"**نسبة الشراء إلى البيع:** {item['buy_sell_ratio']:.2f}")
                st.write(f"**التقييم:** {item['reasons']}")
                st.code(item["address"])
                if item["url"]:
                    st.markdown(f"[فتح الزوج على DexScreener]({item['url']})")
    else:
        st.info("ابدأ فحص DEX لعرض الأزواج المكتشفة.")


def render_live_trade_monitor():
    """Runs a periodic server-side price check while the app session is active."""
    updated, errors = track_open_trades()
    history = load_signal_history(500)
    open_count = 0
    if not history.empty and "outcome" in history.columns:
        open_count = int((history["outcome"] == "OPEN").sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("صفقات مفتوحة أو قيد الدخول", open_count)
    c2.metric("تحديثات الأسعار في هذه الدورة", updated)
    c3.metric("أخطاء جلب السعر", len(errors))

    if errors:
        st.caption(
            "تعذر تحديث بعض الأزواج: " + ", ".join(errors[:8])
        )

    if not history.empty:
        cols = [
            c for c in [
                "id", "exchange", "symbol", "side", "entry",
                "last_price", "stop", "tp1", "tp2", "tp3",
                "status", "outcome", "pnl_pct", "last_checked_at",
            ] if c in history.columns
        ]
        st.dataframe(
            history[history["outcome"] == "OPEN"][cols].head(100),
            use_container_width=True,
            hide_index=True,
        )


def render_history_section():
    st.subheader("📚 سجل الإشارات والصفقات")
    history = load_signal_history(300)
    if history.empty:
        st.info("لا توجد صفقات محفوظة.")
        return
    st.dataframe(history, use_container_width=True, hide_index=True)


def render_dashboard():
    st.subheader("📊 لوحة معلومات BLY7TRADER")
    profile = learning_profile()
    history = load_signal_history(500)
    total = len(history)
    open_trades = (
        int((history["outcome"] == "OPEN").sum())
        if not history.empty else 0
    )
    a, b, c, d = st.columns(4)
    a.metric("إجمالي الإشارات", total)
    b.metric("الصفقات المفتوحة", open_trades)
    c.metric("نسبة الفوز", f"{profile['win_rate']:.1f}%")
    d.metric("متوسط العائد", f"{profile['average_pnl']:.2f}%")


def main():
    init_db()

    st.sidebar.title("BLY7TRADER")
    st.sidebar.caption("Futures • Pump/Dump • DEX • Learning")
    st.sidebar.write("الوقت:", now_cairo().strftime("%Y-%m-%d %H:%M:%S"))

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 الرئيسية",
        "🔎 Futures Scanner",
        "🚨 Pump / Dump",
        "🌐 DEX",
        "🧠 التعلم والذاكرة",
        "📚 سجل الصفقات",
    ])

    with tab1:
        render_dashboard()
        st.divider()
        st.markdown("### 🔄 مراقبة الصفقات المفتوحة")
        st.caption(
            "تُحدّث الأسعار دوريًا أثناء بقاء جلسة التطبيق نشطة. "
            "هذا تتبع سعري افتراضي وليس تنفيذ أوامر في حساب التداول."
        )

        @st.fragment(run_every="10s")
        def live_monitor_fragment():
            render_live_trade_monitor()

        live_monitor_fragment()

    with tab2:
        render_market_scanner()

    with tab3:
        render_pump_dump()

    with tab4:
        render_dex_scanner()

    with tab5:
        render_learning_section()
        st.divider()
        st.write(
            "تعديل درجة التعلم الحالي:",
            update_learning_score(),
            "— يبدأ بعد 10 نتائج محسومة، وهو تعديل إحصائي بسيط وليس نموذج ذكاء اصطناعي."
        )

    with tab6:
        render_history_section()

    st.divider()
    st.caption(
        "BLY7TRADER — أدوات تحليل ومتابعة تعليمية. "
        "لا يوجد ضمان للربح. تحقق من الأسعار والتنفيذ الفعلي لدى منصتك."
    )


if __name__ == "__main__":
    main()
