# BLY7H ULTIMATE V19 + MEXC Learner - كاملة
# Run: pip install -r requirements.txt && streamlit run bly7h_ultimate_v19.py
import os
import json
import time
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import requests
import streamlit as st
st.set_page_config(page_title="BLY7H ULTIMATE V20", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

# ===== BLY7H LOGO =====
import os as _os
import base64 as _b64
def _bly7h_show_logo():
    try:
        _logo_path = None
        for _p in ["bly7h_logo.jpg", "bly7h_logo.png", "logo.jpg", "assets/bly7h_logo.jpg"]:
            if _os.path.exists(_p):
                _logo_path = _p
                break
        if _logo_path:
            _c1, _c2, _c3 = st.columns([1, 2, 1])
            with _c2:
                st.image(_logo_path, use_container_width=True)
        else:
            st.markdown("""<div style="text-align:center; padding:12px 0 4px 0;"><div style="font-size:42px; font-weight:900; letter-spacing:4px; background: linear-gradient(90deg,#FFD700,#FF8C00,#FFD700); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">BLY7H ELITE</div><div style="color:#FFD700; font-size:13px; letter-spacing:3px;">@WHYNOTBLY7 &nbsp;•&nbsp; PREDICT BEFORE THE MOVE</div></div>""", unsafe_allow_html=True)
    except Exception:
        pass
try:
    _bly7h_show_logo()
except Exception:
    pass

APP_TITLE = "💎 BLY7H ULTIMATE V20 V7 - MEXC PREDICTION LAB"
DB_PATH = "bly7h_signals.db"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BLY7H-Scanner/19.0"})
TIMEOUT = 8
STABLES = {"USDCUSDT", "BUSDUSDT", "DAIUSDT", "FDUSDUSDT", "USDEUSDT"}
CAIRO = ZoneInfo("Africa/Cairo")
st.markdown(f"""<h1 style="text-align:center">{APP_TITLE}</h1><p style="text-align:center">ماسح فرص LONG / SHORT — بيانات سوق فعلية مع توضيح حدود كل مؤشر</p>""", unsafe_allow_html=True)
def api_json(url, params=None):
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
    current = now_cairo()
    minutes = current.hour * 60 + current.minute
    if 10 * 60 <= minutes <= 12 * 60:
        return True, "نافذة لندن التقريبية"
    if 15 * 60 + 30 <= minutes <= 17 * 60 + 30:
        return True, "نافذة نيويورك التقريبية"
    return False, "خارج النوافذ المحددة"
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, exchange TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL, score INTEGER NOT NULL, price REAL NOT NULL, entry REAL NOT NULL, stop REAL NOT NULL, tp1 REAL NOT NULL, tp2 REAL NOT NULL, change_pct REAL NOT NULL, volume_ratio REAL NOT NULL, cvd_proxy REAL NOT NULL, outcome TEXT DEFAULT 'OPEN')""")
        conn.commit()
def save_signals(signals, exchange):
    if not signals:
        return
    rows = []
    stamp = datetime.now(timezone.utc).isoformat()
    for signal in signals:
        rows.append((stamp, exchange, signal["symbol"], signal["type"], signal["score"], signal["price"], signal["entry"], signal["stop"], signal["tp1"], signal["tp2"], signal["ch"], signal["vol"], signal["buy"], "OPEN"))
    with sqlite3.connect(DB_PATH) as conn:
        conn.executemany("""INSERT INTO signals (created_at, exchange, symbol, side, score, price, entry, stop, tp1, tp2, change_pct, volume_ratio, cvd_proxy, outcome) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows)
        conn.commit()
def load_signal_history(limit=100):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT ?", conn, params=(limit,))
def send_telegram(message):
    token = st.secrets.get("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_id = st.secrets.get("TELEGRAM_CHANNEL_ID", st.secrets.get("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID", "")))
    if not token:
        return False, "أضف TELEGRAM_BOT_TOKEN داخل Streamlit Secrets"
    if not chat_id:
        return False, "أضف TELEGRAM_CHANNEL_ID أو TELEGRAM_CHAT_ID داخل Secrets"
    try:
        response = SESSION.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True}, timeout=15)
        data = response.json()
        if response.ok and data.get("ok"):
            return True, "تم الإرسال"
        return False, data.get("description", f"Telegram HTTP {response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        return False, str(exc)
def format_telegram(signal):
    side = "🚀 LONG" if signal["type"] == "LONG" else "📉 SHORT"
    return (f"{side} — {signal['symbol']}\n⭐ Score: {signal['score']}/100\n💵 السعر: {signal['price']}\n🎯 الدخول المقترح: {signal['entry']}\n⛔ وقف الخسارة: {signal['stop']}\n✅ TP1: {signal['tp1']}\n🏆 TP2: {signal['tp2']}\n📈 تغير آخر ساعة: {signal['ch']}%\n📦 حجم التداول: x{signal['vol']}\n📊 CVD proxy: {signal['buy']}%\n{signal['extra']}\n@WHYNOTBLY7")
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
def get_kucoin_symbols(limit=100):
    payload = api_json("https://api.kucoin.com/api/v1/market/allTickers")
    tickers = (payload or {}).get("data", {}).get("ticker", [])
    rows = [item for item in tickers if item.get("symbol", "").endswith("-USDT")]
    rows.sort(key=lambda item: safe_float(item.get("volValue")), reverse=True)
    return [item["symbol"] for item in rows[:limit]]
def get_kucoin_klines(symbol):
    end = int(time.time())
    start = end - 110 * 3600
    payload = api_json("https://api.kucoin.com/api/v1/market/candles", {"type": "1hour", "symbol": symbol, "startAt": start, "endAt": end})
    data = (payload or {}).get("data", [])
    if len(data) < 30:
        return None
    frame = pd.DataFrame(data, columns=["time", "open", "close", "high", "low", "vol", "turnover"])
    for column in ("open", "close", "high", "low", "vol"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("time").dropna().reset_index(drop=True)
def get_binance_symbols(limit=100):
    payload = api_json("https://data-api.binance.vision/api/v3/ticker/24hr")
    if not isinstance(payload, list):
        return []
    rows = [item for item in payload if item.get("symbol", "").endswith("USDT") and item.get("symbol") not in STABLES]
    rows.sort(key=lambda item: safe_float(item.get("quoteVolume")), reverse=True)
    return [item["symbol"] for item in rows[:limit]]
def get_binance_klines(symbol):
    payload = api_json("https://data-api.binance.vision/api/v3/klines", {"symbol": symbol, "interval": "1h", "limit": 100})
    if not isinstance(payload, list) or len(payload) < 30:
        return None
    frame = pd.DataFrame(payload, columns=["ot", "open", "high", "low", "close", "vol", "ct", "qav", "trades", "tb", "tq", "ignore"])
    for column in ("open", "high", "low", "close", "vol"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna().reset_index(drop=True)
def get_btc_change():
    payload = api_json("https://data-api.binance.vision/api/v3/klines", {"symbol": "BTCUSDT", "interval": "1h", "limit": 2})
    if not isinstance(payload, list) or len(payload) < 2:
        return None
    previous = safe_float(payload[-2][4])
    current = safe_float(payload[-1][4])
    return (current - previous) / previous * 100 if previous else None
def get_binance_funding(symbol):
    base = symbol.replace("-USDT", "").replace("USDT", "")
    payload = api_json("https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol": f"{base}USDT"})
    if not isinstance(payload, dict) or "lastFundingRate" not in payload:
        return None
    return safe_float(payload["lastFundingRate"]) * 100
def get_binance_oi_change(symbol):
    base = symbol.replace("-USDT", "").replace("USDT", "")
    payload = api_json("https://fapi.binance.com/futures/data/openInterestHist", {"symbol": f"{base}USDT", "period": "5m", "limit": 12})
    if not isinstance(payload, list) or len(payload) < 2:
        return None, None
    first = safe_float(payload[0].get("sumOpenInterest"))
    last = safe_float(payload[-1].get("sumOpenInterest"))
    if first <= 0:
        return None, last
    return (last - first) / first * 100, last
def get_orderbook_wall(symbol):
    base = symbol.replace("-USDT", "").replace("USDT", "")
    payload = api_json("https://data-api.binance.vision/api/v3/depth", {"symbol": f"{base}USDT", "limit": 20})
    if not isinstance(payload, dict):
        return "بيانات دفتر الأوامر غير متاحة"
    bids, asks = payload.get("bids", []), payload.get("asks", [])
    if not bids or not asks:
        return "دفتر الأوامر فارغ أو غير متاح"
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
    base = symbol.replace("-USDT", "").replace("USDT", "")
    checks = [("KUCOIN", f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={base}-USDT"), ("GATE", f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={base}_USDT"), ("BITGET", f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={base}USDT"), ("BYBIT", f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={base}USDT")]
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
def candle_volume_delta_proxy(frame, lookback=20):
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
        notes = [f"📊 CVD proxy: {cvd_proxy:+.1f}% (حجم الشموع، وليس CVD صفقات)", f"📦 حجم آخر شمعة: x{volume_ratio:.2f} من متوسط 20 شمعة", f"⏰ {kz_label}" if settings["killzone"] else "⏰ فلتر الوقت متوقف", f"🐋 {candle_trap_note(frame, side, cvd_proxy)}"]
        relevant_fvg = bull_fvg if side == "LONG" else bear_fvg
        if relevant_fvg:
            notes.append(f"FVG: {relevant_fvg[0]:.8g} إلى {relevant_fvg[1]:.8g}؛ المنتصف {relevant_fvg[2]:.8g}")
        if settings["funding_filter"]:
            notes.append(f"💸 Funding Binance: {funding:+.4f}%" if funding is not None else "💸 Funding: غير متاح لهذا الرمز")
        oi_change, oi_value = get_binance_oi_change(symbol)
        if oi_change is not None:
            notes.append(f"📈 OI Binance: {oi_change:+.2f}%")
        else:
            notes.append("📈 OI Binance: غير متاح")
        if settings["wall_filter"]:
            notes.append(f"🧱 دفتر أوامر Binance: {get_orderbook_wall(symbol)}")
        if settings["confirm_exchanges"]:
            count, exchanges = check_spot_listings(symbol)
            notes.append(f"🌐 الرمز متاح Spot على {count}/5 بحسب فحص endpoints: {', '.join(exchanges)}")
            if count >= 3:
                score = min(score + 3, 98)
        risk_pct = abs(stop - last) / last * 100
        notes.append(f"🎯 مسافة وقف الخسارة: {risk_pct:.2f}% من السعر")
        notes.append("⚠️ مستويات إرشادية مبنية على السعر الحالي؛ يلزم إعادة حسابها عند التنفيذ.")
        result = {"symbol": symbol, "type": side, "score": score, "price": round(last, 8), "ch": round(change, 2), "vol": round(volume_ratio, 2), "buy": round(cvd_proxy, 1), "entry": round(entry, 8), "stop": round(stop, 8), "tp1": round(tp1, 8), "tp2": round(tp2, 8), "extra": "\n".join(notes)}
        return result, "OK"
    except Exception as exc:
        return None, f"خطأ تحليل: {exc}"
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
            found.append({"symbol": token.get("symbol", "UNKNOWN"), "price": price, "change_5m": change_5m, "volume_5m": volume_5m, "liquidity": liquidity, "url": pair.get("url", "")})
    return sorted(found, key=lambda item: item["volume_5m"], reverse=True)
# ---------------- MEXC Learner - قسم لوحده ----------------
def get_mexc_klines_15m(limit=200):
    payload = api_json("https://api.mexc.com/api/v3/klines", {"symbol": "BTCUSDT", "interval": "15m", "limit": limit})
    if not isinstance(payload, list) or len(payload) < 30:
        return None
    frame = pd.DataFrame(payload, columns=["ot", "open", "high", "low", "close", "vol", "ct", "qav"])
    for c in ("open", "high", "low", "close", "vol"):
        frame[c] = pd.to_numeric(frame[c], errors="coerce")
    return frame.dropna().reset_index(drop=True)
def mexc_rsi(closes):
    diff = closes.diff().dropna()
    g = diff[diff > 0].mean() if len(diff[diff > 0]) else 0
    l = -diff[diff < 0].mean() if len(diff[diff < 0]) else 0.001
    if l == 0:
        return 100.0
    return float(100 - (100 / (1 + (g / l))))
def mexc_features(frame):
    last = frame.iloc[-1]
    price = safe_float(last["close"])
    rsi = mexc_rsi(frame["close"].tail(15))
    vol = safe_float(last["vol"])
    vol_avg = safe_float(frame["vol"].iloc[-21:-1].mean())
    vol_x = vol / vol_avg if vol_avg > 0 else 1
    o = safe_float(last["open"]); h = safe_float(last["high"]); l = safe_float(last["low"]); c = safe_float(last["close"])
    body = abs(c - o)
    up = h - max(o, c); down = min(o, c) - l
    wick = "فوق" if up > body * 1.5 else ("تحت" if down > body * 1.5 else "مفيش")
    streak = 0
    for k in range(len(frame)-1, max(0, len(frame)-6), -1):
        cc = safe_float(frame["close"].iloc[k]); oo = safe_float(frame["open"].iloc[k])
        if cc > oo:
            if streak >= 0:
                streak += 1
            else:
                break
        else:
            if streak <= 0:
                streak -= 1
            else:
                break
    hi = safe_float(frame["high"].tail(20).max()); lo = safe_float(frame["low"].tail(20).min())
    pos = (price - lo) / (hi - lo) * 100 if hi != lo else 50
    cvd = 0.0
    for k in range(max(0, len(frame)-10), len(frame)):
        cc = safe_float(frame["close"].iloc[k]); oo = safe_float(frame["open"].iloc[k]); vv = safe_float(frame["vol"].iloc[k])
        cvd += vv if cc > oo else -vv
    chg3 = (price - safe_float(frame["close"].iloc[-4])) / safe_float(frame["close"].iloc[-4]) * 100 if safe_float(frame["close"].iloc[-4]) else 0
    return {"price": price, "rsi": round(rsi,1), "vol_x": round(vol_x,2), "wick": wick, "streak": streak, "pos": round(pos,1), "cvd": round(cvd,0), "chg3": round(chg3,3)}
def mexc_predict(f):
    if f["rsi"] > 65 and f["wick"] == "فوق":
        return "ادخل بيع", "دوس هبوط في MEXC - RSI عالي + ويك فوق", 72
    if f["rsi"] < 35 and f["wick"] == "تحت":
        return "ادخل شراء", "دوس ارتفاع في MEXC - RSI واطي + ويك تحت", 72
    if f["streak"] >= 3:
        return "ادخل شراء", "دوس ارتفاع - 3 شموع شراء ورا بعض", 65
    if f["streak"] <= -3:
        return "ادخل بيع", "دوس هبوط - 3 شموع بيع ورا بعض", 65
    if f["cvd"] > 0 and f["chg3"] > 0:
        return "ادخل شراء", "دوس ارتفاع - CVD شراء + السعر طالع", 60
    if f["cvd"] < 0 and f["chg3"] < 0:
        return "ادخل بيع", "دوس هبوط - CVD بيع + السعر نازل", 60
    if f["pos"] > 85:
        return "ادخل بيع", "دوس هبوط - السعر عند القمة", 58
    if f["pos"] < 15:
        return "ادخل شراء", "دوس ارتفاع - السعر عند القاع", 58
    if f["vol_x"] < 0.8:
        return "متدخلش", "اتفرج - Vol ميت", 0
    return "متدخلش", "اتفرج - مش واضح", 0
# ===== MEXC PREDICTION LAB V20 - محركات 1-20 - مستقل عن الماسح =====
# حقيقة مهمة: MEXC لم تنشر API عام لجولات Up/Down.
# المصدر الرسمي: blog.mexc.com - Up or Down داخل prediction.mexc.com
# دورات 5 و 15 دقيقة، BTC اولا ثم ETH/SPCX/XAU، التسوية بـ Composite Real-Time Index + TWAP
# لذلك: الجولات هنا تُبنى كـ PROXY من شموع MEXC Spot 15m + تسجيل يدوي للنتيجة الرسمية.
# التعلم يتدرب فقط على ما تم تسجيله فعليا، ولا نزعم اننا نقرأ التسوية الرسمية من API غير موجود.
import hashlib, math
import numpy as np

LAB_DB = "bly7h_mexc_lab.db"
def lab_init_db():
    import sqlite3
    with sqlite3.connect(LAB_DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS lab_rounds (id INTEGER PRIMARY KEY AUTOINCREMENT, round_start TEXT NOT NULL, round_end TEXT NOT NULL, symbol TEXT, open_price REAL, close_price REAL, settlement_proxy REAL, official_result TEXT DEFAULT '', source TEXT DEFAULT 'PROXY_MEXC_SPOT', created_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS lab_predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, round_start TEXT NOT NULL, created_at TEXT NOT NULL, pred TEXT, prob REAL, confidence REAL, regime TEXT, reasons TEXT, counter TEXT, invalidation REAL, model_version TEXT, features_hash TEXT, UNIQUE(round_start, model_version))""")
        c.execute("""CREATE TABLE IF NOT EXISTS lab_features (round_start TEXT PRIMARY KEY, feats TEXT, label TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS lab_models (version TEXT PRIMARY KEY, created_at TEXT, train_n INTEGER, test_acc REAL, brier REAL, logloss REAL, is_active INTEGER DEFAULT 0)""")
        c.commit()

# --- 1 Data Engine ---

# ===== المصدر الحقيقي - V6 =====
# المصدر الحقيقي لجولات Up/Down هو prediction.mexc.com
# الموقع ده تطبيق JS - الـ API بتاعه خاص ومش منشور في docs الرسمية
# فـ V6 بيحاول يجيب من المصدر الحقيقي بالترتيب ده:
# 1) prediction.mexc.com API - لو فتح من غير Login
# 2) api.mexc.com Spot API - ده السعر الحقيقي بتاع MEXC نفسه - وهو جزء من Composite Index اللي بيتسوى بيه
# 3) Binance Public - مصدر حقيقي بديل - جزء من الـ Index برضه
# وبيسجل في كل مرة جاب منين بالظبط - مش بيقول PROXY من غير ما يوضح
def lab_fetch_real_source(symbol="BTCUSDT"):
    import requests as _rq
    # 1) حاول prediction.mexc.com
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://prediction.mexc.com/", "Origin": "https://prediction.mexc.com"}
    tries = [
        ("https://prediction.mexc.com/api/prediction/markets", {}),
        ("https://prediction.mexc.com/api/prediction/events", {}),
        ("https://prediction.mexc.com/api/v1/prediction/list", {}),
    ]
    for url, params in tries:
        try:
            r = _rq.get(url, params=params, headers=headers, timeout=8)
            if r.status_code == 200:
                j = r.json()
                # لو رجع داتا حقيقية - نستخدمها
                if isinstance(j, dict) and (j.get("data") or j.get("code") == 200):
                    return {"ok": True, "source": f"prediction.mexc.com REAL - {url}", "data": j, "note": "جاب من المصدر الحقيقي prediction.mexc.com"}
        except Exception:
            pass
    # 2) MEXC Spot الحقيقي - من غير API Key
    try:
        r = _rq.get("https://api.mexc.com/api/v3/ticker/price", params={"symbol": symbol}, timeout=8)
        if r.status_code == 200 and r.json().get("price"):
            # وكمان شموع حقيقية
            k = _rq.get("https://api.mexc.com/api/v3/klines", params={"symbol": symbol, "interval": "15m", "limit": 5}, timeout=8)
            return {"ok": True, "source": "api.mexc.com Spot REAL - السعر الحقيقي بتاع MEXC نفسه - جزء من Composite Index", "price": float(r.json()["price"]), "klines_ok": k.status_code==200, "note": "prediction.mexc.com API خاص ومحتاج Login - فجبنا من MEXC Spot الحقيقي اللي هو مكون اساسي في التسوية"}
    except Exception as e:
        pass
    # 3) Binance
    try:
        r = _rq.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": symbol}, timeout=8)
        if r.status_code == 200:
            return {"ok": True, "source": "Binance Public REAL - بديل حقيقي", "price": float(r.json()["price"]), "note": "MEXC Spot وقع - جبنا من Binance"}
    except Exception:
        pass
    return {"ok": False, "source": "NONE", "note": "كل المصادر الحقيقية فشلت"}

def lab_get_price_real(symbol="BTCUSDT"):
    res = lab_fetch_real_source(symbol)
    return res

def lab_get_klines(symbol="BTCUSDT", interval="15m", limit=200):
    p = api_json("https://api.mexc.com/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit})
    if not isinstance(p, list) or len(p) < 30: return None
    import pandas as pd
    f = pd.DataFrame(p, columns=["ot","open","high","low","close","vol","ct","qav"])
    for col in ("open","high","low","close","vol"): f[col]=pd.to_numeric(f[col], errors="coerce")
    return f.dropna().reset_index(drop=True)
def lab_round_windows(frame):
    # جولات 15m تبدأ :00 :15 :30 :45 - نعيد بناءها من الشموع
    return frame.copy()
def lab_sync_check():
    import time as _t
    return {"server_time_ms": int(_t.time()*1000), "note": "MEXC Spot time via klines - Prediction settlement is Composite Index + TWAP, not spot close. Proxy only."}

# --- 2 Candle Intelligence ---
def lab_candle_patterns(frame):
    if frame is None or len(frame)<5: return []
    out=[]
    last=frame.iloc[-1]; prev=frame.iloc[-2]
    o,h,l,c = safe_float(last["open"]), safe_float(last["high"]), safe_float(last["low"]), safe_float(last["close"])
    po,ph,pl,pc = safe_float(prev["open"]), safe_float(prev["high"]), safe_float(prev["low"]), safe_float(prev["close"])
    body=abs(c-o); up=h-max(o,c); down=min(o,c)-l
    rng=h-l if h>l else 1
    if c>o and c>=po and o<=pc and body>abs(pc-po)*1.2: out.append("Engulfing صاعد")
    if c<o and c<=po and o>=pc and body>abs(pc-po)*1.2: out.append("Engulfing هابط")
    if down>body*2 and down/rng>0.5: out.append("Hammer / Pin Bar صاعد")
    if up>body*2 and up/rng>0.5: out.append("Shooting Star / Pin Bar هابط")
    if h<=ph and l>=pl: out.append("Inside Bar")
    if h>=ph and l<=pl: out.append("Outside Bar")
    if up>body*1.5: out.append("Wick Rejection فوق")
    if down>body*1.5: out.append("Wick Rejection تحت")
    # Liquidity Sweep: كسر قاع ثم اغلاق فوقه
    if l < safe_float(frame["low"].iloc[-6:-1].min()) and c > safe_float(frame["low"].iloc[-6:-1].min()): out.append("Liquidity Sweep صاعد")
    if h > safe_float(frame["high"].iloc[-6:-1].max()) and c < safe_float(frame["high"].iloc[-6:-1].max()): out.append("Liquidity Sweep هابط")
    # Double Top/Bottom تقريبي
    highs=frame["high"].tail(20); lows=frame["low"].tail(20)
    if highs.iloc[-1] < highs.max()*1.001 and len(highs)>10: out.append("قرب Double Top")
    if lows.iloc[-1] > lows.min()*0.999 and len(lows)>10: out.append("قرب Double Bottom")
    if not out: out.append("لا يوجد نموذج واضح")
    return out

# --- 3 Volume Intelligence ---
def lab_volume(frame):
    if frame is None or len(frame)<21: return {"vol_x":1,"state":"غير متاح"}
    vol=safe_float(frame["vol"].iloc[-1]); avg=safe_float(frame["vol"].iloc[-21:-1].mean()); prev_avg=safe_float(frame["vol"].iloc[-42:-21].mean()) if len(frame)>=42 else avg
    vx=vol/avg if avg>0 else 1
    accel=(avg-prev_avg)/prev_avg*100 if prev_avg>0 else 0
    # Divergence: سعر طالع وحجم نازل
    chg=(safe_float(frame["close"].iloc[-1])-safe_float(frame["close"].iloc[-6]))/safe_float(frame["close"].iloc[-6])*100 if safe_float(frame["close"].iloc[-6]) else 0
    div="Volume Divergence هابط" if chg>0 and vx<0.8 else ("Volume Divergence صاعد" if chg<0 and vx<0.8 else "لا يوجد Divergence")
    state="Volume Explosion" if vx>1.8 else ("Accumulation" if vx>1.2 and chg>-0.3 else ("Distribution" if vx>1.2 and chg<0.3 else "عادي"))
    return {"vol_x":round(vx,2),"accel_pct":round(accel,1),"chg_5":round(chg,2),"divergence":div,"state":state}

# --- 4 Order Book ---
def lab_orderbook(symbol="BTCUSDT"):
    p=api_json("https://api.mexc.com/api/v3/depth", {"symbol": symbol, "limit": 20})
    if not isinstance(p, dict): return {"imbalance":0,"note":"غير متاح"}
    bids=p.get("bids",[]); asks=p.get("asks",[])
    if not bids or not asks: return {"imbalance":0,"note":"فارغ"}
    bv=sum(safe_float(q)*safe_float(pr) for pr,q in bids); av=sum(safe_float(q)*safe_float(pr) for pr,q in asks)
    imb=(bv-av)/(bv+av)*100 if bv+av>0 else 0
    max_bid=max(bids, key=lambda x: safe_float(x[0])*safe_float(x[1])); max_ask=max(asks, key=lambda x: safe_float(x[0])*safe_float(x[1]))
    wall="جدار شراء" if safe_float(max_bid[0])*safe_float(max_bid[1])>safe_float(max_ask[0])*safe_float(max_ask[1])*1.5 else ("جدار بيع" if safe_float(max_ask[0])*safe_float(max_ask[1])>safe_float(max_bid[0])*safe_float(max_bid[1])*1.5 else "لا يوجد جدار بارز")
    return {"imbalance":round(imb,1),"bid_notional":round(bv,0),"ask_notional":round(av,0),"wall":wall,"note":"MEXC Spot Depth - ليس دفتر Prediction الرسمي"}

# --- 5 Futures ---
def lab_futures(symbol="BTCUSDT"):
    fund=get_binance_funding(symbol)
    oi_ch, oi_val=get_binance_oi_change(symbol)
    squeeze="Short Squeeze محتمل" if fund is not None and fund<-0.05 else ("Long Squeeze محتمل" if fund is not None and fund>0.05 else "لا يوجد Squeeze واضح")
    return {"funding_pct": round(fund,4) if fund is not None else None, "oi_change_pct": round(oi_ch,2) if oi_ch is not None else None, "squeeze": squeeze, "note":"Binance Futures كمصدر مساعد - ليس MEXC Prediction"}

# --- 6 Order Flow ---
def lab_orderflow(symbol="BTCUSDT"):
    p=api_json("https://api.mexc.com/api/v3/trades", {"symbol": symbol, "limit": 100})
    if not isinstance(p, list) or not p: return {"delta":0,"cvd":0,"note":"غير متاح"}
    buy_v=sell_v=0; cvd=0
    for t in p:
        q=safe_float(t.get("qty", t.get("quantity",0))); pr=safe_float(t.get("price",0))
        # MEXC trades: isBuyerMaker
        is_maker=t.get("isBuyerMaker", False)
        if is_maker: sell_v+=q; cvd-=q
        else: buy_v+=q; cvd+=q
    delta=buy_v-sell_v
    return {"buy_vol":round(buy_v,3),"sell_vol":round(sell_v,3),"delta":round(delta,3),"real_cvd":round(cvd,3),"aggressive":"Aggressive Buying" if delta>0 else "Aggressive Selling","absorption":"Absorption محتمل" if abs(delta)<buy_v*0.2 and buy_v>0 else "لا يوجد Absorption واضح"}

# --- 7 Indicators ---
def lab_indicators(frame):
    if frame is None or len(frame)<50: return {}
    c=frame["close"]
    def ema(s,n): return s.ewm(span=n, adjust=False).mean()
    e9=ema(c,9).iloc[-1]; e21=ema(c,21).iloc[-1]; e50=ema(c,50).iloc[-1]
    # RSI
    diff=c.diff().dropna(); g=diff[diff>0].mean() if len(diff[diff>0]) else 0; l=-diff[diff<0].mean() if len(diff[diff<0]) else 0.001
    rsi=100-(100/(1+(g/l if l else 100)))
    # MACD
    macd=ema(c,12).iloc[-1]-ema(c,26).iloc[-1]; sig=ema(ema(c,12)-ema(c,26),9).iloc[-1]
    # ATR
    tr=(frame["high"]-frame["low"]).tail(14).mean()
    # Bollinger
    ma=c.tail(20).mean(); sd=c.tail(20).std(); up=ma+2*sd; dn=ma-2*sd
    # VWAP تقريبي
    vwap=(frame["close"]*frame["vol"]).tail(20).sum()/frame["vol"].tail(20).sum() if frame["vol"].tail(20).sum()>0 else c.iloc[-1]
    # ADX تقريبي
    adx=min(100, abs((safe_float(c.iloc[-1])-safe_float(c.iloc[-15]))/safe_float(c.iloc[-15])*100)*10) if safe_float(c.iloc[-15]) else 0
    # SR
    sup=safe_float(frame["low"].tail(50).min()); res=safe_float(frame["high"].tail(50).max())
    # Fib من اخر 50
    lo=sup; hi=res; fib38=hi-(hi-lo)*0.382; fib61=hi-(hi-lo)*0.618
    return {"ema9":round(e9,2),"ema21":round(e21,2),"ema50":round(e50,2),"rsi":round(float(rsi),1),"macd":round(float(macd),2),"macd_signal":round(float(sig),2),"atr":round(float(tr),2),"bb_up":round(float(up),2),"bb_dn":round(float(dn),2),"bb_mid":round(float(ma),2),"vwap":round(float(vwap),2),"adx_proxy":round(float(adx),1),"support":round(sup,2),"resistance":round(res,2),"fib382":round(fib38,2),"fib618":round(fib61,2),"momentum":round(float(c.iloc[-1]-c.iloc[-10]),2),"roc_pct":round(float((c.iloc[-1]-c.iloc[-10])/c.iloc[-10]*100),2)}

# --- 11 Regime + 12 Correlation ---
def lab_regime(frame, ind):
    if not ind: return "غير معروف"
    chg=ind.get("roc_pct",0); adx=ind.get("adx_proxy",0); rsi=ind.get("rsi",50)
    if adx>25 and chg>1: return "Bullish Trend"
    if adx>25 and chg<-1: return "Bearish Trend"
    if adx<15: return "Sideways / Low Volatility"
    if abs(chg)>3: return "High Volatility / Breakout"
    return "Sideways"
def lab_correlation():
    btc=lab_get_klines("BTCUSDT","15m",50); eth=lab_get_klines("ETHUSDT","15m",50)
    if btc is None or eth is None: return {"btc_eth_corr":None,"note":"غير متاح"}
    try:
        corr=btc["close"].tail(30).corr(eth["close"].tail(30))
        return {"btc_eth_corr":round(float(corr),2),"btc_change_15m":round(float((btc["close"].iloc[-1]-btc["close"].iloc[-2])/btc["close"].iloc[-2]*100),3),"eth_change_15m":round(float((eth["close"].iloc[-1]-eth["close"].iloc[-2])/eth["close"].iloc[-2]*100),3)}
    except: return {"btc_eth_corr":None,"note":"خطأ"}

# --- 8 Pattern Memory + Similarity ---
def lab_features_vector(frame, ind, vol, ob, flow, fut):
    if frame is None or ind=={}: return None
    last=frame.iloc[-1]
    return {"price":safe_float(last["close"]),"rsi":ind.get("rsi",50),"macd":ind.get("macd",0),"ema_diff":ind.get("ema9",0)-ind.get("ema21",0),"atr_pct":ind.get("atr",0)/safe_float(last["close"])*100 if safe_float(last["close"]) else 0,"vol_x":vol.get("vol_x",1),"ob_imb":ob.get("imbalance",0),"flow_delta":flow.get("delta",0),"funding":fut.get("funding_pct") or 0,"oi_ch":fut.get("oi_change_pct") or 0,"pos_20":(safe_float(last["close"])-safe_float(frame["low"].tail(20).min()))/(safe_float(frame["high"].tail(20).max())-safe_float(frame["low"].tail(20).min())+1e-9)*100,"chg3":(safe_float(last["close"])-safe_float(frame["close"].iloc[-4]))/safe_float(frame["close"].iloc[-4])*100 if safe_float(frame["close"].iloc[-4]) else 0}


def lab_backtest_1000():
    # يعلم النموذج من 1000 جولة فاتت من الشموع - من غير ما تستنى 10 ايام لايف
    # 1000 جولة × 15 دقيقة = 1000 شمعة 15m
    # Label = PROXY: اغلاق الشمعة اللي بعدها > فتح الشمعة = UP - مش التسوية الرسمية Composite+TWAP
    import sqlite3, json as _jj, datetime as _dt
    lab_init_db()
    f = lab_get_klines("BTCUSDT","15m",1000)
    if f is None or len(f)<100:
        return {"ok":False,"note":"تعذر جلب 1000 شمعة من MEXC - جرب تاني"}
    saved=0; ups=0
    # نحسب الخصائص لكل شمعة باستخدام الشموع اللي قبلها بس - مفيش تسرب مستقبل
    for i in range(60, len(f)-1):
        try:
            window = f.iloc[:i+1].copy()
            ind = lab_indicators(window)
            vol = lab_volume(window)
            # OrderBook و OrderFlow للحالات القديمة مش متاحة - بنستخدم 0 وبنعلم النموذج انها غير متاحة
            ob = {"imbalance":0,"note":"Backtest - OrderBook غير متاح تاريخيا"}
            fut = {"funding_pct":0,"oi_change_pct":0}
            flow = {"delta":0}
            feats = lab_features_vector(window, ind, vol, ob, flow, fut)
            if feats is None: continue
            feats["backtest_idx"]=i
            # Label من الشمعة اللي بعدها فقط - الشمعة اللي بعدها هي الجولة
            open_next = float(f["open"].iloc[i+1]); close_next = float(f["close"].iloc[i+1])
            label = "UP" if close_next > open_next else "DOWN"
            if label=="UP": ups+=1
            # وقت الجولة تقريبي: دلوقتي - (عدد الشموع المتبقية × 15 دقيقة)
            # MEXC بيرجع الشموع من الاقدم للاحدث - فنحسب الوقت بالعكس من دلوقتي
            mins_ago = (len(f)-1 - i)*15
            rs_dt = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(minutes=mins_ago)
            rs = rs_dt.strftime("%Y-%m-%d %H:%M")
            with sqlite3.connect(LAB_DB) as _c:
                _c.execute("INSERT OR REPLACE INTO lab_features (round_start,feats,label) VALUES (?,?,?)", (rs, _jj.dumps(feats), label))
            saved+=1
        except Exception as e:
            continue
    return {"ok":True,"saved":saved,"up":ups,"down":saved-ups,"up_rate":round(ups/saved*100,1) if saved else 0,"note":"Labels هي PROXY من اغلاق الشمعة - مش التسوية الرسمية. النموذج هيتعلم النمط العام، وبعدين يتصحح بالنتائج الرسمية اللي بتسجلها يدوي."}


def lab_auto_learn():
    # يشتغل لوحده اول ما التطبيق يفتح - لو مفيش ذاكرة - يجيب 1000 جولة ويتعلم منها لوحده
    # من غير ما تدوس اي زرار
    import sqlite3, os
    lab_init_db()
    try:
        with sqlite3.connect(LAB_DB) as _c:
            n = _c.execute("SELECT COUNT(*) FROM lab_features WHERE label IN ('UP','DOWN')").fetchone()[0]
            has_model = _c.execute("SELECT COUNT(*) FROM lab_models").fetchone()[0]
    except: n=0; has_model=0
    if n < 100:
        # ذاكرة فاضية - علمه من 1000 جولة فاتت لوحده
        res = lab_backtest_1000()
        if res.get("ok"):
            train = lab_train_model()
            return {"auto":True,"backtest":res,"train":train}
        return {"auto":True,"backtest":res,"train":{"ok":False}}
    # ذاكرة موجودة - شوف هل فيه جولات جديدة محتاجة اعادة تدريب؟
    return lab_self_evolve()

def lab_self_evolve():
    # التطور الذاتي: كل ما تيجي 20 جولة جديدة رسمية - يعيد التدريب ويقارن الجديد بالقديم ويحتفظ بالافضل
    import sqlite3, json as _jj
    lab_init_db()
    with sqlite3.connect(LAB_DB) as _c:
        total = _c.execute("SELECT COUNT(*) FROM lab_features WHERE label IN ('UP','DOWN')").fetchone()[0]
        models = _c.execute("SELECT version,test_acc FROM lab_models ORDER BY created_at DESC LIMIT 1").fetchall()
    old_acc = models[0][1] if models else 0
    # لو العدد زاد عن اخر تدريب بـ 20 - درب تاني
    # نعرف اخر تدريب كان على كام جولة من جدول lab_models
    with sqlite3.connect(LAB_DB) as _c:
        last = _c.execute("SELECT train_n FROM lab_models ORDER BY created_at DESC LIMIT 1").fetchall()
    last_n = last[0][0] if last else 0
    if total - last_n >= 20:
        new = lab_train_model()
        if new.get("ok"):
            # قارن الجديد بالقديم - احتفظ بالافضل
            if new.get("test_acc",0) < old_acc*100:
                # الجديد اوحش - رجع القديم كـ Active
                with sqlite3.connect(LAB_DB) as _c:
                    _c.execute("UPDATE lab_models SET is_active=0 WHERE version=?", (new.get("version"),))
                    if models: _c.execute("UPDATE lab_models SET is_active=1 WHERE version=?", (models[0][0],))
                    _c.commit()
                return {"evolved":False,"reason":f"النموذج الجديد {new.get('test_acc')}% اوحش من القديم {old_acc*100:.1f}% - احتفظنا بالقديم","total":total}
            return {"evolved":True,"new_acc":new.get("test_acc"),"old_acc":old_acc*100,"total":total}
    return {"evolved":False,"reason":f"لسه بدري - عندك {total} جولة - اخر تدريب كان على {last_n} - استنى لما يزيدوا 20","total":total}

def lab_get_price_no_key(symbol="BTCUSDT"):
    # يجيب السعر من غير API Key ومن غير تسجيل - 3 مصادر مجانية - لو واحد وقع التاني يشتغل
    # 1) MEXC Public - من غير مفتاح
    # 2) Binance Public - من غير مفتاح
    # 3) CoinGecko Public - من غير مفتاح
    p = api_json("https://api.mexc.com/api/v3/ticker/price", {"symbol": symbol})
    if isinstance(p, dict) and p.get("price"):
        return {"price": float(p["price"]), "source": "MEXC Public - من غير API Key"}
    p2 = api_json("https://api.binance.com/api/v3/ticker/price", {"symbol": symbol})
    if isinstance(p2, dict) and p2.get("price"):
        return {"price": float(p2["price"]), "source": "Binance Public - من غير API Key - بديل"}
    # CoinGecko
    cg = api_json("https://api.coingecko.com/api/v3/simple/price", {"ids":"bitcoin","vs_currencies":"usd"})
    if isinstance(cg, dict) and cg.get("bitcoin",{}).get("usd"):
        return {"price": float(cg["bitcoin"]["usd"]), "source": "CoinGecko Public - من غير API Key - بديل"}
    return {"price": None, "source": "كل المصادر فشلت - جرب تاني"}

def lab_backfill_features(round_start_str):
    # يجيب شموع MEXC لحد وقت الجولة ويحسب الخصائص بتاعتها - لـ الجولات الفاتت تتعلم منها بجد
    # round_start_str = "2026-11-07 06:45"
    try:
        import datetime as _dt
        rs = _dt.datetime.strptime(round_start_str, "%Y-%m-%d %H:%M").replace(tzinfo=_dt.timezone.utc)
        # نجيب شموع 15m كتير وناخد اللي قبل الجولة
        f = lab_get_klines("BTCUSDT","15m",500)
        if f is None: return None
        # الشموع في MEXC مفيهاش وقت واضح في الداتا فريم الحالي - نستخدم اخر 200 شمعة كتقريب
        # ونحسب الخصائص من اخر الشموع قبل الجولة
        ind = lab_indicators(f); vol = lab_volume(f); ob = lab_orderbook("BTCUSDT"); fut = lab_futures("BTCUSDT"); flow = lab_orderflow("BTCUSDT")
        feats = lab_features_vector(f, ind, vol, ob, flow, fut)
        if feats is not None:
            feats["backfilled_for"] = round_start_str
            feats["source"] = "BACKFILL_KLINES"
        return feats
    except Exception as e:
        return None

def lab_similarity(current, history):
    # history: list of (feats dict, label UP/DOWN)
    if not history or not current: return {"similar_n":0,"up_rate":None,"note":"لا توجد ذاكرة كافية"}
    keys=["rsi","vol_x","ob_imb","ema_diff","chg3","pos_20"]
    sims=[]
    for feats,label in history:
        try:
            d=sum((float(current.get(k,0))-float(feats.get(k,0)))**2 for k in keys)
            # تطبيع تقريبي
            sim=1/(1+math.sqrt(d)/100)
            sims.append((sim,label))
        except: continue
    sims=sorted(sims, reverse=True)[:50]
    if len(sims)<10: return {"similar_n":len(sims),"up_rate":None,"note":"ذاكرة قليلة - لا تعتمد على التشابه وحده"}
    ups=sum(1 for _,lb in sims if lb=="UP")
    return {"similar_n":len(sims),"up_rate":round(ups/len(sims)*100,1),"top_sim":round(sims[0][0],2) if sims else 0}

# --- 9 ML: RandomForest + Ensemble + Time Split ---
def lab_train_model():
    import sqlite3
    lab_init_db()
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
    except Exception as e:
        return {"ok":False,"note":f"sklearn غير متاح: {e} - سيتم استخدام Ensemble القواعد فقط"}
    with sqlite3.connect(LAB_DB) as conn:
        rows=conn.execute("SELECT feats,label FROM lab_features WHERE label IN ('UP','DOWN') ORDER BY round_start").fetchall()
    if len(rows)<40:
        return {"ok":False,"note":f"بيانات قليلة للتدريب: {len(rows)} - المطلوب 40+ جولة مسجلة فعليا. سجل جولات اولا."}
    import json as _j
    X=[]; y=[]
    for feats_s,label in rows:
        try:
            f=_j.loads(feats_s); X.append([f.get(k,0) for k in ["rsi","macd","ema_diff","atr_pct","vol_x","ob_imb","flow_delta","funding","oi_ch","pos_20","chg3"]]); y.append(1 if label=="UP" else 0)
        except: continue
    n=len(X); split=int(n*0.8)
    Xtr,ytr=X[:split],y[:split]; Xte,yte=X[split:],y[split:]
    clf=RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(Xtr,ytr)
    prob=clf.predict_proba(Xte)[:,1] if len(set(yte))>1 else [0.5]*len(Xte)
    pred=(prob>=0.5).astype(int)
    acc=float((pred==np.array(yte)).mean()) if yte else 0
    try: bl=float(brier_score_loss(yte, prob)) if len(set(yte))>1 else 1
    except: bl=1
    try: ll=float(log_loss(yte, prob, labels=[0,1])) if len(set(yte))>1 else 1
    except: ll=1
    ver=f"RF-{int(__import__('time').time())}"
    with sqlite3.connect(LAB_DB) as conn:
        conn.execute("INSERT OR REPLACE INTO lab_models VALUES (?,?,?,?,?,?)", (ver, __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(), n, acc, bl, ll, 1))
        conn.execute("UPDATE lab_models SET is_active=0 WHERE version!=?", (ver,))
        conn.commit()
    import pickle, os
    os.makedirs("lab_models", exist_ok=True)
    with open(f"lab_models/{ver}.pkl","wb") as f: pickle.dump(clf,f)
    return {"ok":True,"version":ver,"train_n":n,"test_n":len(Xte),"test_acc":round(acc*100,1),"brier":round(bl,3),"logloss":round(ll,3)}

# --- 13 Prediction + 14 Calibration + 15 Risk ---
def lab_predict_ensemble(feats, patterns, vol, ob, flow, regime, sim, ml_prob=None):
    votes_up=0; votes_dn=0; reasons=[]; counter=[]
    if feats["rsi"]<35: votes_up+=2; reasons.append("RSI تشبع بيع")
    if feats["rsi"]>65: votes_dn+=2; reasons.append("RSI تشبع شراء")
    if vol.get("vol_x",1)>1.5 and feats["chg3"]>0: votes_up+=1; reasons.append("Volume Explosion مع صعود")
    if vol.get("vol_x",1)>1.5 and feats["chg3"]<0: votes_dn+=1; reasons.append("Volume Explosion مع هبوط")
    if ob.get("imbalance",0)>10: votes_up+=1; reasons.append("Bid Imbalance")
    if ob.get("imbalance",0)<-10: votes_dn+=1; reasons.append("Ask Imbalance")
    if flow.get("delta",0)>0: votes_up+=1; reasons.append("Aggressive Buying")
    if flow.get("delta",0)<0: votes_dn+=1; reasons.append("Aggressive Selling")
    if "Engulfing صاعد" in patterns or "Hammer / Pin Bar صاعد" in patterns: votes_up+=2; reasons.append("نموذج شموع صاعد")
    if "Engulfing هابط" in patterns or "Shooting Star / Pin Bar هابط" in patterns: votes_dn+=2; reasons.append("نموذج شموع هابط")
    if "Liquidity Sweep صاعد" in patterns: votes_up+=1; reasons.append("Liquidity Sweep صاعد")
    if "Liquidity Sweep هابط" in patterns: votes_dn+=1; reasons.append("Liquidity Sweep هابط")
    if sim.get("up_rate") is not None:
        if sim["up_rate"]>60: votes_up+=1; reasons.append(f"تشابه تاريخي: {sim['up_rate']}% صعود في {sim['similar_n']} حالة مشابهة")
        if sim["up_rate"]<40: votes_dn+=1; reasons.append(f"تشابه تاريخي: {100-sim['up_rate']}% هبوط")
    total=votes_up+votes_dn
    if total==0: return {"pred":"NO_TRADE","prob":0.5,"votes_up":0,"votes_dn":0,"reasons":["أدلة غير كافية"],"counter":["لا يوجد توافق"],"regime":regime,"stage":"NO_TRADE"}
    # دمج ML ان وجد
    if ml_prob is not None:
        ensemble_up=(votes_up/total*0.6 + ml_prob*0.4) if total else ml_prob
    else:
        ensemble_up=votes_up/total if total else 0.5
    pred="UP" if ensemble_up>=0.55 else ("DOWN" if ensemble_up<=0.45 else "NO_TRADE")
    if pred=="UP": counter.append("احتمال Fakeout / سحب سيولة")
    if pred=="DOWN": counter.append("احتمال Short Squeeze")
    stage="CONFIRMED" if abs(ensemble_up-0.5)>0.2 and total>=4 else ("EARLY SETUP" if abs(ensemble_up-0.5)>0.1 else "WATCH")
    if pred=="NO_TRADE": stage="NO_TRADE"
    # معايرة بسيطة: لا يتم ادعاء 85% بدون بيانات - نحدد الثقة من عدد الأصوات والتشابه
    conf=round(min(85, max(50, abs(ensemble_up-0.5)*100 + total*3 + (10 if sim.get("similar_n",0)>=30 else 0))),1)
    return {"pred":pred,"prob":round(float(ensemble_up),3),"votes_up":votes_up,"votes_dn":votes_dn,"reasons":reasons,"counter":counter,"regime":regime,"stage":stage,"confidence":conf}

def lab_risk(pred, prob, price, atr):
    if pred=="NO_TRADE": return {"ev":0,"decision":"NO_TRADE","reason":"أدلة غير كافية"}
    # في Up/Down: العائد يعتمد على سعر المنتج - لا نفترض عائدا ثابتا
    # نفترض breakeven 50% كمثال توضيحي فقط ونطلب من المستخدم ادخال العائد الفعلي
    # EV = prob * payout - (1-prob)*1
    payout=0.8 # قابل للتعديل من الواجهة - يجب ادخال العائد الحقيقي من MEXC
    ev=prob*(payout) - (1-prob)*1
    decision="TRADE" if ev>0 and prob>=0.58 else "NO_TRADE"
    return {"ev":round(ev,3),"payout_assumed":payout,"breakeven":round(1/(1+payout),3),"decision":decision,"reason":"EV موجب" if ev>0 else "EV سالب - العائد لا يبرر المخاطرة","expected_range":[round(price-atr,2), round(price+atr,2)]}


lab_init_db()
# Auto-learn on startup - يتعلم من 1000 جولة لوحده من غير زرار
try:
    _auto = lab_auto_learn()
    print('AUTO-LEARN:', _auto)
except Exception as _e:
    print('AUTO-LEARN FAIL:', _e)
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
settings = {"want_long": want_long, "want_short": want_short, "use_fvg": use_fvg, "btc_filter": btc_filter, "funding_filter": funding_filter, "wall_filter": wall_filter, "killzone": killzone, "confirm_exchanges": confirm_exchanges, "min_score": min_score}
section = st.radio("القسم", ["🔎 الماسح", "📉 DUMP / SHORT", "🚀 DEX", "📊 سجل الإشارات", "🧪 اختبار تاريخي", "🟢 MEXC Learner", "🧪 MEXC PREDICTION LAB - V20"], horizontal=True)
if section in ("🔎 الماسح", "📉 DUMP / SHORT"):
    is_dump_section = section == "📉 DUMP / SHORT"
    st.subheader("📉 ماسح SHORT" if is_dump_section else "🔎 ماسح السوق")
    st.caption(f"المصدر: {platform} | العملات: {limit_coins} | أقل Score: {min_score} | توقيت القاهرة: {now_cairo().strftime('%H:%M')}")
    button_label = "📉 افحص فرص SHORT" if is_dump_section else "🔍 افحص السوق الآن"
    if st.button(button_label, type="primary"):
        symbols = get_kucoin_symbols(limit_coins) if platform == "KUCOIN" else get_binance_symbols(limit_coins)
        st.info(f"تم العثور على {len(symbols)} رمزًا للفحص.")
        signals, debug = [], []
        progress = st.progress(0)
        status = st.empty()
        for index, symbol in enumerate(symbols):
            progress.progress((index + 1) / max(len(symbols), 1))
            status.caption(f"يفحص {symbol} ({index + 1}/{len(symbols)})")
            frame = get_kucoin_klines(symbol) if platform == "KUCOIN" else get_binance_klines(symbol)
            if frame is not None:
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
                        st.markdown(f"### {'🚀' if signal['type'] == 'LONG' else '📉'} {signal['symbol']} — {signal['type']}")
                        st.write(f"السعر: **{signal['price']}** | تغير الساعة: **{signal['ch']}%** | Volume: **x{signal['vol']}** | CVD proxy: **{signal['buy']}%**")
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
                st.write(f"السعر: ${item['price']:.10g} | تغير 5 دقائق: {item['change_5m']:.2f}% | حجم 5 دقائق: ${item['volume_5m']:,.0f} | السيولة: ${item['liquidity']:,.0f}")
                if item["url"]:
                    st.markdown(f"[فتح الزوج على DexScreener]({item['url']})")
                if telegram_enabled:
                    message = (f"🚀 DEX {item['symbol']} على BSC\nالسعر: ${item['price']:.10g}\nتغير 5m: {item['change_5m']:.2f}%\nحجم 5m: ${item['volume_5m']:,.0f}\nالسيولة: ${item['liquidity']:,.0f}\n{item['url']}\n@WHYNOTBLY7")
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
        st.caption("السجل يحفظ الإشارات الصادرة فقط.")
elif section == "🧪 اختبار تاريخي":
    st.subheader("🧪 اختبار تاريخي مبسط — Binance")
    test_symbol = st.selectbox("العملة", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])
    if st.button("▶️ شغّل الاختبار", type="primary"):
        frame = get_binance_klines(test_symbol)
        if frame is None or len(frame) < 50:
            st.error("تعذر جلب بيانات كافية للاختبار.")
        else:
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
                trades.append({"index": index, "side": side, "entry": entry_price, "outcome": outcome})
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
            st.caption("تنبيه: الاختبار يستخدم آخر 100 شمعة فقط، ولا يشمل رسوم أو انزلاق.")
elif section == "🟢 MEXC Learner":
    st.subheader("🟢 MEXC Learner - BTC 15min - شراء / بيع")
    st.caption("بيتعلم من شموع MEXC نفسها - ادخل شراء = دوس ارتفاع / ادخل بيع = دوس هبوط")
    if st.button("🟢 جيب توقع MEXC دلوقتي", type="primary"):
        mframe = get_mexc_klines_15m(200)
        if mframe is None:
            st.error("تعذر جلب شموع MEXC - جرب تاني")
        else:
            mf = mexc_features(mframe)
            pred, reason, conf = mexc_predict(mf)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("سعر BTC على MEXC", f"{mf['price']:,.2f}")
            c2.metric("RSI", mf["rsi"])
            c3.metric("Vol", f"x{mf['vol_x']}")
            c4.metric("مكان السعر", f"{mf['pos']}%")
            if pred == "ادخل شراء":
                st.success("✅ ادخل شراء - دوس ارتفاع في MEXC")
            elif pred == "ادخل بيع":
                st.error("🔴 ادخل بيع - دوس هبوط في MEXC")
            else:
                st.warning("⏸️ متدخلش - متدوسش حاجة")
            st.write(f"السبب: {reason}")
            st.write(f"الثقة: {conf}% | ويك: {mf['wick']} | شموع متتالية: {mf['streak']} | CVD: {mf['cvd']}")
            st.caption("لعبة Guess على MEXC معمولة لـ المنصة تكسب على المدى الطويل - العب بـ 1 دولار بس.")
    if st.button("🧪 باك تست MEXC - 200 شمعة"):
        mframe2 = get_mexc_klines_15m(200)
        if mframe2 is None:
            st.error("تعذر جلب شموع MEXC")
        else:
            wins, played = 0, 0
            for i in range(30, len(mframe2)-1):
                sub = mframe2.iloc[:i+1].copy()
                ff = mexc_features(sub)
                pp, _, _ = mexc_predict(ff)
                if pp == "متدخلش":
                    continue
                played += 1
                nxt = safe_float(mframe2["close"].iloc[i+1]); cur = safe_float(mframe2["close"].iloc[i])
                actual = "ادخل شراء" if nxt > cur else "ادخل بيع"
                if pp == actual:
                    wins += 1
            rate = wins / played * 100 if played else 0
            st.metric("نسبة نجاح باك تست MEXC (200 شمعة)", f"{rate:.1f}%")
            st.write(f"لعب {played} جولة - كسب {wins}")
            if rate < 55:
                st.warning("نسبة النجاح تحت 55% - متلعبش بفلوس حقيقية النهاردة")
            else:
                st.success("نسبة النجاح فوق 55% - العب بحذر وبـ 1 دولار بس")
elif section == "🧪 MEXC PREDICTION LAB - V20":
    st.subheader("🧪 MEXC PREDICTION LAB - V20")
    st.warning("✅ المصدر الحقيقي: V6 بيجيب السعر من api.mexc.com Spot الحقيقي - وهو جزء من Composite Index اللي بتتسوى بيه جولات Up/Down - وبيحاول يجيب من prediction.mexc.com نفسه. لو prediction.mexc.com طلب Login - بيكمل من MEXC Spot الحقيقي وبيسجل المصدر بالظبط. التسوية الرسمية النهائية لسه بتتسجل يدوي من التطبيق.")
    cA,cB,cC,cD = st.columns(4)
    cA.metric("LIVE ROUNDS","15M"); cB.metric("AI ENGINE","ON"); cC.metric("PATTERN MEMORY","ON"); cD.metric("LEARNING","ON")
    tab1, tab2, tab3, tab4 = st.tabs(["Live Predictions","Candle / Volume / Order Book","AI Learning Center","Accuracy / Reports"])
    with tab1:
        _real = lab_fetch_real_source("BTCUSDT")
        st.info(f"📡 المصدر الحقيقي: {_real.get('source')} | السعر: {_real.get('price', '-')} | {_real.get('note','')}")
        st.caption("الجولة الحالية تُبنى من شمعة 15m الجارية - بداية الجولة :00 :15 :30 :45 - التسوية PROXY = اغلاق الشمعة القادمة")
        if st.button("🔴 حلل الجولة الحالية - V20", type="primary"):
            f15 = lab_get_klines("BTCUSDT","15m",200)
            if f15 is None:
                st.error("تعذر جلب شموع MEXC")
            else:
                ind = lab_indicators(f15); vol = lab_volume(f15); ob = lab_orderbook("BTCUSDT"); fut = lab_futures("BTCUSDT"); flow = lab_orderflow("BTCUSDT"); pats = lab_candle_patterns(f15); regime = lab_regime(f15, ind); corr = lab_correlation()
                feats = lab_features_vector(f15, ind, vol, ob, flow, fut)
                import sqlite3, json as _j
                lab_init_db()
                with sqlite3.connect(LAB_DB) as _c:
                    rows=_c.execute("SELECT feats,label FROM lab_features WHERE label IN ('UP','DOWN')").fetchall()
                hist=[]
                for fs,lb in rows:
                    try: hist.append((_j.loads(fs), lb))
                    except: pass
                sim = lab_similarity(feats, hist)
                pred = lab_predict_ensemble(feats, pats, vol, ob, flow, regime, sim, ml_prob=None)
                risk = lab_risk(pred["pred"], pred["prob"], feats["price"], ind.get("atr",0))
                import datetime as _dt
                rs = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
                fh = hashlib.md5(_j.dumps(feats, sort_keys=True).encode()).hexdigest()[:12]
                with sqlite3.connect(LAB_DB) as _c:
                    _c.execute("INSERT OR IGNORE INTO lab_predictions (round_start,created_at,pred,prob,confidence,regime,reasons,counter,invalidation,model_version,features_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (rs, _dt.datetime.now(_dt.timezone.utc).isoformat(), pred["pred"], pred["prob"], pred["confidence"], regime, " | ".join(pred["reasons"]), " | ".join(pred["counter"]), feats["price"], "ENSEMBLE-V20", fh))
                    _c.execute("INSERT OR REPLACE INTO lab_features (round_start,feats,label) VALUES (?,?,?)", (rs, _j.dumps(feats), ""))
                    _c.commit()
                col1,col2,col3,col4 = st.columns(4)
                col1.metric("التوقع", pred["pred"]); col2.metric("الاحتمال المعاير", f"{pred['prob']*100:.1f}%"); col3.metric("الثقة", f"{pred['confidence']}%"); col4.metric("المرحلة", pred["stage"])
                st.write(f"**السعر:** {feats['price']:,.2f} | **النظام:** {regime} | **اصوات UP:** {pred['votes_up']} | **اصوات DOWN:** {pred['votes_dn']}")
                st.write(f"**الاسباب:** {' | '.join(pred['reasons'])}")
                st.write(f"**الادلة المعارضة:** {' | '.join(pred['counter'])}")
                st.write(f"**نماذج الشموع:** {' | '.join(pats)}")
                st.write(f"**حجم:** {vol} | **دفتر:** {ob} | **فيوتشر:** {fut} | **Order Flow:** {flow}")
                st.write(f"**مؤشرات:** RSI {ind.get('rsi')} | MACD {ind.get('macd')} | EMA9/21 {ind.get('ema9')}/{ind.get('ema21')} | VWAP {ind.get('vwap')} | BB {ind.get('bb_dn')} - {ind.get('bb_up')} | Support {ind.get('support')} | Resistance {ind.get('resistance')} | Fib 38/61 {ind.get('fib382')}/{ind.get('fib618')}")
                st.write(f"**تشابه تاريخي:** {sim} | **ارتباط:** {corr}")
                st.write(f"**مخاطر:** EV {risk.get('ev')} | Breakeven {risk.get('breakeven')} | قرار {risk.get('decision')} - {risk.get('reason')} | النطاق المتوقع {risk.get('expected_range')} | سعر الالغاء: {feats['price']}")
                st.info("سجل النتيجة الرسمية بعد انتهاء الجولة من الاسفل - لا تعدل التوقع القديم بعد معرفة النتيجة.")
        st.markdown("#### ⚡ سجل 3 جولات فاتت مرة واحدة - للتلاتة اللي فاتوا")
        st.caption("لو التلاتة اللي فاتوا كلهم UP - سيبهم UP ودوس حفظ. لو واحدة مختلفة غيرها قبل الحفظ.")
        with st.form("log_3_past"):
            c1,c2,c3 = st.columns(3)
            # التلات جولات اللي قبل الجولة الحالية 07:30
            r1 = c1.text_input("الجولة 1 - وقت البداية", value="2026-11-07 06:45")
            l1 = c1.selectbox("نتيجة 1", ["UP","DOWN"], key="l1")
            r2 = c2.text_input("الجولة 2 - وقت البداية", value="2026-11-07 07:00")
            l2 = c2.selectbox("نتيجة 2", ["UP","DOWN"], key="l2")
            r3 = c3.text_input("الجولة 3 - وقت البداية", value="2026-11-07 07:15")
            l3 = c3.selectbox("نتيجة 3", ["UP","DOWN"], key="l3")
            if st.form_submit_button("💾 سجل التلاتة"):
                import sqlite3, json as _jj
                lab_init_db()
                saved=[]
                for rs_in, off in [(r1,l1),(r2,l2),(r3,l3)]:
                    if rs_in.strip():
                        with sqlite3.connect(LAB_DB) as _c:
                            # لو مفيش خصائص للجولة دي - نسجلها كجولة تاريخية يدوية من غير خصائص
                            bf = lab_backfill_features(rs_in.strip())
                            _feats_s = _jj.dumps(bf if bf else {"source":"MANUAL_PAST","note":"Backfill فشل - سجل يدوي بدون خصائص"})
                            _c.execute("INSERT OR IGNORE INTO lab_features (round_start,feats,label) VALUES (?,?,?)", (rs_in.strip(), _feats_s, off))
                            _c.execute("UPDATE lab_features SET label=? WHERE round_start=?", (off, rs_in.strip()))
                            _c.execute("INSERT OR IGNORE INTO lab_predictions (round_start,created_at,pred,prob,confidence,regime,reasons,counter,invalidation,model_version,features_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (rs_in.strip(), rs_in.strip(), off, 0, 0, "MANUAL", "تسجيل يدوي للجولات الفاتت", "", 0, "MANUAL_PAST", "manual"))
                            _c.commit()
                        saved.append(f"{rs_in} = {off}")
                st.success("تم تسجيل: " + " | ".join(saved))
                st.info("دلوقتي عندك 3 جولات متعلمة. كمل لحد 40 جولة وبعدين درب النموذج.")
        if st.button("🔁 املا خصائص الجولات القديمة - لـ يتعلم من النماذج"):
            import sqlite3, json as _jj2
            lab_init_db()
            with sqlite3.connect(LAB_DB) as _c:
                rows = _c.execute("SELECT round_start,feats FROM lab_features").fetchall()
                fixed=0
                for rs_old, fs_old in rows:
                    try:
                        d = _jj2.loads(fs_old) if fs_old else {}
                    except: d={}
                    if not d or d.get("source")=="MANUAL_PAST" or fs_old=="{}":
                        bf = lab_backfill_features(rs_old)
                        if bf:
                            _c.execute("UPDATE lab_features SET feats=? WHERE round_start=?", (_jj2.dumps(bf), rs_old)); fixed+=1
                _c.commit()
            st.success(f"تم ملء خصائص {fixed} جولة قديمة - دلوقتي النماذج هتشتغل")
        st.markdown("#### سجل النتيجة الرسمية للجولة (يدوي - من تطبيق MEXC)")
        with st.form("log_official"):
            rs_in = st.text_input("وقت بداية الجولة (YYYY-MM-DD HH:MM)", value="")
            off = st.selectbox("النتيجة الرسمية من MEXC", ["UP","DOWN"])
            if st.form_submit_button("💾 سجل النتيجة الرسمية"):
                if rs_in:
                    import sqlite3
                    lab_init_db()
                    with sqlite3.connect(LAB_DB) as _c:
                        bf2 = lab_backfill_features(rs_in)
                        _c.execute("INSERT OR IGNORE INTO lab_features (round_start,feats,label) VALUES (?,?,?)", (rs_in, _jj.dumps(bf2) if bf2 else "{}", off)); _c.execute("UPDATE lab_features SET label=? WHERE round_start=?", (off, rs_in)); _c.commit()
                    st.success(f"تم تسجيل {off} للجولة {rs_in} - سيتم استخدامها في التدريب القادم")
                else: st.error("اكتب وقت الجولة")
    with tab2:
        f15b = lab_get_klines("BTCUSDT","15m",100)
        if f15b is not None:
            st.write("**نماذج:**", lab_candle_patterns(f15b))
            st.write("**حجم:**", lab_volume(f15b))
            st.write("**دفتر:**", lab_orderbook("BTCUSDT"))
            st.write("**فيوتشر:**", lab_futures("BTCUSDT"))
            st.write("**Order Flow:**", lab_orderflow("BTCUSDT"))
            st.write("**مؤشرات:**", lab_indicators(f15b))
            st.write("**نظام السوق:**", lab_regime(f15b, lab_indicators(f15b)))
            st.write("**ارتباط:**", lab_correlation())
            st.write("**مزامنة:**", lab_sync_check())
    with tab3:
        # حالة التعلم التلقائي
        try:
            _st = lab_self_evolve()
            st.success(f"🤖 التعلم التلقائي شغال - عندك {_st.get('total',0)} جولة متعلمة - {_st.get('reason','')}") if not _st.get("evolved") else st.success(f"🤖 تطور لوحده! دقة جديدة {_st.get('new_acc')}% بدل {_st.get('old_acc')}%")
        except Exception as _e:
            st.caption(f"التعلم التلقائي: {_e}")
        st.write("**دورة التعلم:** جمع -> خصائص -> تدريب RandomForest (Time Split 80/20 - لا تسرب مستقبل) -> اختبار -> مقارنة -> اعتماد الافضل")
        st.markdown("### 📚 تعلم من 1000 جولة فاتت - Backtest")
        st.caption("هيجيب 1000 شمعة 15m من MEXC = 1000 جولة فاتت = 10 ايام. هيحسب لكل جولة RSI / MACD / EMA / Volume / شموع - من الشموع اللي قبلها بس. وبعدين هيدرب النموذج عليها.")
        st.warning("Labels هنا PROXY من اغلاق الشمعة - مش التسوية الرسمية Composite+TWAP. فالنموذج هيتعلم النمط العام، وبعدين يتصحح بالنتائج الرسمية اللي بتسجلها يدوي من تطبيق MEXC.")
        if st.button("📚 علمه من 1000 جولة فاتت - دلوقتي", type="primary"):
            with st.spinner("بجيب 1000 شمعة وبحسب 1000 نموذج... دقيقة واحدة"):
                res = lab_backtest_1000()
            st.json(res)
            if res.get("ok"):
                st.success(f"تم حفظ {res['saved']} جولة - {res['up']} UP / {res['down']} DOWN - دلوقتي دوس درب النموذج")
                st.info("بعدها ارجع لـ Live Predictions - يتم عرض التوقعات بقت UP/DOWN بدل NO_TRADE - لان بقى عنده ذاكرة 1000 نموذج")
        if st.button("🧠 درب النموذج الآن"):
            res = lab_train_model(); st.json(res)
        import sqlite3
        lab_init_db()
        with sqlite3.connect(LAB_DB) as _c:
            try: models=_c.execute("SELECT * FROM lab_models ORDER BY created_at DESC LIMIT 10").fetchall(); st.write("**اصدارات النماذج:**", models)
            except Exception as e: st.write(e)
        st.caption("XGBoost: سيتم استخدامه عند توفر المكتبة - حاليا RandomForest + Ensemble + Similarity Search + اعادة تدريب دورية.")
    with tab4:
        import sqlite3
        lab_init_db()
        with sqlite3.connect(LAB_DB) as _c:
            preds=_c.execute("SELECT * FROM lab_predictions ORDER BY id DESC LIMIT 50").fetchall(); feats_r=_c.execute("SELECT * FROM lab_features WHERE label IN ('UP','DOWN')").fetchall()
        st.write(f"**اجمالي توقعات مسجلة:** {len(preds)} | **جولات بعلامة فعلية:** {len(feats_r)}")
        if feats_r:
            mp={p[1]:p[3] for p in preds}
            correct=up_c=up_n=dn_c=dn_n=0
            for rs,fs,lb in feats_r:
                if rs in mp:
                    if mp[rs]==lb: correct+=1
                    if lb=="UP": up_n+=1; up_c+=1 if mp[rs]=="UP" else 0
                    else: dn_n+=1; dn_c+=1 if mp[rs]=="DOWN" else 0
            st.write(f"**دقة التوقعات المعلمة:** {correct}/{len(feats_r)} = {correct/len(feats_r)*100:.1f}% | UP {up_c}/{up_n} | DOWN {dn_c}/{dn_n}")
            st.caption("Brier / LogLoss / Calibration تظهر بعد التدريب في AI Learning Center - لا يتم ادعاء 85% بدون بيانات اختبار.")
        st.dataframe(preds, use_container_width=True) if preds else st.info("لا توجد توقعات بعد - حلل جولة من تبويب Live")

st.markdown("---")
st.caption("BLY7H V20 V7 - MEXC PREDICTION LAB | البيانات قد تتأخر أو تفشل حسب واجهات المنصات. لا تنفّذ صفقة اعتمادًا على الإشارة وحدها.")
