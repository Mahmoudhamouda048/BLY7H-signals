# BLY7H ULTIMATE V19 — Professional market scanner
# Run: pip install -r requirements.txt && streamlit run bly7h_ultimate_v19.py
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
    page_title="BLY7H ULTIMATE V19",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_TITLE = "💎 BLY7H ULTIMATE V19"
DB_PATH = "bly7h_signals.db"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BLY7H-Scanner/19.0"})
TIMEOUT = 8
STABLES = {"USDCUSDT", "BUSDUSDT", "DAIUSDT", "FDUSDUSDT", "USDEUSDT"}
CAIRO = ZoneInfo("Africa/Cairo")

st.markdown(
    f"""
    <h1 style="text-align:center">{APP_TITLE}</h1>
    <p style="text-align:center">
    ماسح فرص LONG / SHORT — بيانات سوق فعلية مع توضيح حدود كل مؤشر
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
        if isinstance(payload, dict) and payload.get("code") not in (None, "200000", 200):
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                score INTEGER NOT NULL,
                price REAL NOT NULL,
                entry REAL NOT NULL,
                stop REAL NOT NULL,
                tp1 REAL NOT NULL,
                tp2 REAL NOT NULL,
                change_pct REAL NOT NULL,
                volume_ratio REAL NOT NULL,
                cvd_proxy REAL NOT NULL,
                outcome TEXT DEFAULT 'OPEN'
            )
            """
        )
        conn.commit()


def save_signals(signals, exchange):
    if not signals:
        return
    rows = []
    stamp = datetime.now(timezone.utc).isoformat()
    for signal in signals:
        rows.append((
            stamp, exchange, signal["symbol"], signal["type"], signal["score"],
            signal["price"], signal["entry"], signal["stop"], signal["tp1"],
            signal["tp2"], signal["ch"], signal["vol"], signal["buy"], "OPEN"
        ))
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany(
            """INSERT INTO signals
            (created_at, exchange, symbol, side, score, price, entry, stop,
             tp1, tp2, change_pct, volume_ratio, cvd_proxy, outcome)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
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
        "https://data-api.binance.vision/api/v3/klines",
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
    """Checks spot ticker endpoints; does not prove futures listing or direction."""
    base = symbol.replace("-USDT", "").replace("USDT", "")
    checks = [
        (
            "KUCOIN",
            f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={base}-USDT",
        ),
        ("GATE", f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={base}_USDT"),
        ("BITGET", f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={base}USDT"),
        ("BYBIT", f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={base}USDT"),
    ]
    available = ["BINANCE"]
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
                valid = data.get("code") == "00000" and bool(data.get("data", {}).get("list"))
            else:
                valid = data.get("retCode") == 0 and bool(data.get("result", {}).get("list"))
            if valid:
                available.append(name)
        except (requests.RequestException, ValueError, TypeError):
            pass
    return len(available), available


# ----------------------------- Indicators -----------------------------

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


def analyze(frame, symbol, settings):
    try:
        if frame is None or len(frame) < 30:
            return None, "بيانات شموع غير كافية"

        last = safe_float(frame["close"].iloc[-1])
        previous = safe_float(frame["close"].iloc[-2])
        if last <= 0 or previous <= 0:
            return None, "سعر غير صالح"

        change = (last - previous) / previous * 100
        if abs(change) > 8:
            return None, f"حركة آخر ساعة كبيرة جدًا: {change:.2f}%"

        average_volume = safe_float(frame["vol"].iloc[-21:-1].mean())
        current_volume = safe_float(frame["vol"].iloc[-1])
        volume_ratio = current_volume / average_volume if average_volume > 0 else 0

        cvd_proxy = candle_volume_delta_proxy(frame)
        if abs(cvd_proxy) < 3:
            return None, f"ضغط الشموع ضعيف: {cvd_proxy:.1f}%"

        side = "LONG" if cvd_proxy > 0 else "SHORT"
        if side == "LONG" and not settings["want_long"]:
            return None, "LONG غير مفعّل"
        if side == "SHORT" and not settings["want_short"]:
            return None, "SHORT غير مفعّل"

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
        funding = get_binance_funding(symbol) if settings["funding_filter"] else None
        if settings["funding_filter"] and funding is not None:
            if side == "LONG" and funding > 0.05:
                return None, f"فاندنج مرتفع ضد LONG: {funding:.4f}%"
            if side == "SHORT" and funding < -0.05:
                return None, f"فاندنج سالب ضد SHORT: {funding:.4f}%"

        score = 40
        score += min(max(volume_ratio, 0) * 4, 20)
        score += min(abs(cvd_proxy) * 0.25, 20)
        score += 8 if ((side == "LONG" and bull_fvg) or (side == "SHORT" and bear_fvg)) else 0
        score += 5 if in_kz else 0
        score = min(int(score), 95)

        if score < settings["min_score"]:
            return None, f"السكور {score} أقل من المطلوب {settings['min_score']}"

        if side == "LONG":
            fvg_mid = bull_fvg[2] if bull_fvg else last * 0.997
            entry = clamp_entry(fvg_mid, last, True)
            stop = last * 0.98
            tp1, tp2 = last * 1.03, last * 1.06
        else:
            fvg_mid = bear_fvg[2] if bear_fvg else last * 1.003
            entry = clamp_entry(fvg_mid, last, False)
            stop = last * 1.02
            tp1, tp2 = last * 0.97, last * 0.94

        notes = [
            f"📊 CVD proxy: {cvd_proxy:+.1f}% (حجم الشموع، وليس CVD صفقات)",
            f"📦 حجم آخر شمعة: x{volume_ratio:.2f} من متوسط 20 شمعة",
            f"⏰ {kz_label}" if settings["killzone"] else "⏰ فلتر الوقت متوقف",
            f"🐋 {candle_trap_note(frame, side, cvd_proxy)}",
        ]
        relevant_fvg = bull_fvg if side == "LONG" else bear_fvg
        if relevant_fvg:
            notes.append(
                f"FVG: {relevant_fvg[0]:.8g} إلى {relevant_fvg[1]:.8g}؛ المنتصف {relevant_fvg[2]:.8g}"
            )
        if settings["funding_filter"]:
            notes.append(
                f"💸 Funding Binance: {funding:+.4f}%"
                if funding is not None else "💸 Funding: غير متاح لهذا الرمز"
            )

        oi_change, oi_value = get_binance_oi_change(symbol)
        if oi_change is not None:
            notes.append(f"📈 OI Binance: {oi_change:+.2f}%")
        else:
            notes.append("📈 OI Binance: غير متاح")

        if settings["wall_filter"]:
            notes.append(f"🧱 دفتر أوامر Binance: {get_orderbook_wall(symbol)}")

        if settings["confirm_exchanges"]:
            count, exchanges = check_spot_listings(symbol)
            notes.append(
                f"🌐 الرمز متاح Spot على {count}/5 بحسب فحص endpoints: {', '.join(exchanges)}"
            )
            if count >= 3:
                score = min(score + 3, 98)

        risk_pct = abs(stop - last) / last * 100
        notes.append(f"🎯 مسافة وقف الخسارة: {risk_pct:.2f}% من السعر")
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
    platform = st.selectbox("المنصة", ["KUCOIN", "BINANCE"])
    st.markdown("### اتجاه الصفقة")
    want_long = st.checkbox("🚀 LONG", value=True)
    want_short = st.checkbox("📉 SHORT", value=True)
    st.markdown("### الفلاتر")
    use_fvg = st.checkbox("FVG", value=False)
    btc_filter = st.checkbox("فلتر اتجاه BTC", value=True)
    funding_filter = st.checkbox("فلتر Funding (Binance Futures)", value=False)
    wall_filter = st.checkbox("دفتر أوامر Binance", value=False)
    killzone = st.checkbox("عرض نوافذ السيولة التقريبية", value=True)
    confirm_exchanges = st.checkbox("فحص توافر الرمز على 5 منصات Spot", value=False)
    st.markdown("### التصفية")
    min_score = st.slider("أقل Score", 0, 95, 55)
    limit_coins = st.slider("عدد العملات للفحص", 10, 100, 40, step=5)
    telegram_enabled = st.checkbox("إرسال أفضل الإشارات إلى Telegram", value=False)
    if st.button("📡 اختبار Telegram"):
        ok, message = send_telegram("🧪 اختبار BLY7H V19 — اتصال Telegram يعمل.")
        st.success(message) if ok else st.error(message)

settings = {
    "want_long": want_long,
    "want_short": want_short,
    "use_fvg": use_fvg,
    "btc_filter": btc_filter,
    "funding_filter": funding_filter,
    "wall_filter": wall_filter,
    "killzone": killzone,
    "confirm_exchanges": confirm_exchanges,
    "min_score": min_score,
}


# ----------------------------- Main navigation -----------------------------

section = st.radio(
    "القسم",
    ["🔎 الماسح", "📉 DUMP / SHORT", "🚀 DEX", "📊 سجل الإشارات", "🧪 اختبار تاريخي"],
    horizontal=True,
)

if section in ("🔎 الماسح", "📉 DUMP / SHORT"):
    is_dump_section = section == "📉 DUMP / SHORT"
    st.subheader("📉 ماسح SHORT" if is_dump_section else "🔎 ماسح السوق")
    st.caption(
        f"المصدر: {platform} | العملات: {limit_coins} | أقل Score: {min_score} | "
        f"توقيت القاهرة: {now_cairo().strftime('%H:%M')}"
    )

    button_label = "📉 افحص فرص SHORT" if is_dump_section else "🔍 افحص السوق الآن"
    if st.button(button_label, type="primary"):
        symbols = (
            get_kucoin_symbols(limit_coins)
            if platform == "KUCOIN"
            else get_binance_symbols(limit_coins)
        )
        st.info(f"تم العثور على {len(symbols)} رمزًا للفحص.")
        signals, debug = [], []
        progress = st.progress(0)
        status = st.empty()

        for index, symbol in enumerate(symbols):
            progress.progress((index + 1) / max(len(symbols), 1))
            status.caption(f"يفحص {symbol} ({index + 1}/{len(symbols)})")
            frame = (
                get_kucoin_klines(symbol)
                if platform == "KUCOIN"
                else get_binance_klines(symbol)
            )
            if frame is not None:
                # Binance futures-only filters are skipped for KuCoin symbols
                # because the current funding/OI endpoints are Binance-specific.
                signal, reason = analyze(frame, symbol, settings)
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
    "BLY7H V19 | البيانات قد تتأخر أو تفشل حسب واجهات المنصات. "
    "لا تنفّذ صفقة اعتمادًا على الإشارة وحدها؛ راجع السيولة والسبريد والمخاطرة."
)
