# ============================================================================
#  BLY7TRADER — AUTO BOT V1  
# ============================================================================

import os
import time
import hmac
import hashlib
import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlencode

import pandas as pd
import requests
import streamlit as st

CAIRO = ZoneInfo("Africa/Cairo")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "BLY7TRADER-BOT/1.0"})

# ============================================================================
#  01 — CONFIG (كل الحماية هنا)
# ============================================================================
@dataclass
class BotConfig:
    mode: str = "PAPER"              # PAPER | TESTNET | REAL
    exchange: str = "BINANCE_TESTNET"
    api_key: str = ""
    api_secret: str = ""
    # --- Risk (دي اللي بتحمي رأس مالك) ---
    capital: float = 100.0            # رأس المال الكلي
    risk_per_trade_pct: float = 1.0    # خاطر بـ 1% بس في الصفقة
    max_daily_loss_pct: float = 2.0    # لو خسرت 2% النهاردة -> البوت يقف
    max_open_positions: int = 1        # صفقة واحدة بس في نفس الوقت
    max_trades_per_day: int = 2        # صفقتين في اليوم كحد أقصى
    leverage: int = 5                  # ⚠️ مش 20 ولا 50 — 5 كفاية
    # --- Strategy ---
    timeframe: str = "15m"
    scan_every_sec: int = 60           # افحص كل دقيقة
    only_killzone: bool = True         # اشتغل في لندن / نيويورك بس
    only_grade_a: bool = True
    # --- Safety ---
    kill_switch: bool = False          # زرار إيقاف طارئ
    confirm_real: bool = False         # لازم تكتب CONFIRM عشان REAL يشتغل


# ============================================================================
#  02 — DATABASE (سجل كل حاجة البوت عملها)
# ============================================================================
DB = "bly7trader_bot.db"

def init_db():
    with sqlite3.connect(DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS bot_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT,
            symbol TEXT, side TEXT, mode TEXT, entry REAL, stop REAL,
            tp1 REAL, tp2 REAL, qty REAL, status TEXT DEFAULT 'OPEN',
            pnl_usd REAL DEFAULT 0, reason TEXT, exit_price REAL, closed_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS bot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, level TEXT, msg TEXT)""")
        c.commit()

def log(level, msg):
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO bot_logs (created_at, level, msg) VALUES (?,?,?)",
                  (datetime.now(timezone.utc).isoformat(), level, msg))
        c.commit()

def open_positions():
    with sqlite3.connect(DB) as c:
        return c.execute("SELECT * FROM bot_trades WHERE status='OPEN'").fetchall()

def today_pnl():
    with sqlite3.connect(DB) as c:
        r = c.execute("SELECT COALESCE(SUM(pnl_usd),0) FROM bot_trades WHERE date(created_at)=date('now') AND status='CLOSED'").fetchone()
        return float(r[0] or 0)

def today_trades():
    with sqlite3.connect(DB) as c:
        return c.execute("SELECT COUNT(*) FROM bot_trades WHERE date(created_at)=date('now')").fetchone()[0]

def save_trade(t):
    with sqlite3.connect(DB) as c:
        c.execute("""INSERT INTO bot_trades (created_at,symbol,side,mode,entry,stop,tp1,tp2,qty,reason)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (datetime.now(timezone.utc).isoformat(), t["symbol"], t["side"], t["mode"],
                   t["entry"], t["stop"], t["tp1"], t["tp2"], t["qty"], t.get("reason","")))
        c.commit()

def close_trade(tid, exit_price, pnl):
    with sqlite3.connect(DB) as c:
        c.execute("UPDATE bot_trades SET status='CLOSED', exit_price=?, pnl_usd=?, closed_at=? WHERE id=?",
                  (exit_price, pnl, datetime.now(timezone.utc).isoformat(), tid))
        c.commit()

# ============================================================================
#  03 — RISK MANAGER (أهم جزء في البوت كله)
# ============================================================================
def killzone_now():
    m = datetime.now(CAIRO).hour * 60 + datetime.now(CAIRO).minute
    return (600 <= m <= 720) or (930 <= m <= 1050)

def risk_check(cfg: BotConfig):
    """يرجع (مسموح؟, سبب الرفض). لو أي شرط فشل -> مفيش دخول."""
    if cfg.kill_switch:
        return False, "⛔ Kill Switch شغال — البوت واقف"
    if cfg.mode == "REAL" and not cfg.confirm_real:
        return False, "REAL مقفول — لازم تأكيد CONFIRM"
    if today_pnl() <= -(cfg.capital * cfg.max_daily_loss_pct / 100):
        return False, f"⛔ خسارة اليوم وصلت الحد ({cfg.max_daily_loss_pct}%) — البوت وقف لحد بكرة"
    if len(open_positions()) >= cfg.max_open_positions:
        return False, "في صفقة مفتوحة أصلاً — ممنوع صفقة تانية"
    if today_trades() >= cfg.max_trades_per_day:
        return False, "وصلت لحد صفقات اليوم"
    if cfg.only_killzone and not killzone_now():
        return False, "برة Killzone — البوت مستني وقت السيولة"
    return True, "OK"

def position_size(cfg: BotConfig, entry: float, stop: float) -> float:
    """حجم الصفقة = المبلغ اللي هتخسره ÷ مسافة الستوب. مش بالرافعة."""
    risk_usd = cfg.capital * cfg.risk_per_trade_pct / 100
    dist = abs(entry - stop)
    if entry <= 0 or dist <= 0:
        return 0
    qty = risk_usd / dist
    # سقف أمان: حجم الصفقة مش أكتر من 20% من رأس المال × الرافعة
    max_qty = (cfg.capital * 0.20 * cfg.leverage) / entry
    return round(min(qty, max_qty), 6)

# ============================================================================
#  04 — STRATEGY (نفس منطق V20 الصارم — مختصر)
# ============================================================================
def get_klines(symbol, tf="15m", limit=200):
    try:
        r = SESSION.get("https://fapi.binance.com/fapi/v1/klines",
                        params={"symbol": symbol, "interval": tf, "limit": limit}, timeout=8)
        cols = ["time","open","high","low","close","volume","ct","qv","tr","tb","tq","ig"]
        df = pd.DataFrame(r.json(), columns=cols)
        for c in ["open","high","low","close","volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df.dropna()
    except Exception:
        return pd.DataFrame()

def indicators(df):
    close = df["close"]
    d = close.diff()
    g = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    df["rsi"] = (100 - 100/(1 + g/l.replace(0, float("nan")))).fillna(50)
    df["ema9"] = close.ewm(span=9, adjust=False).mean()
    df["ema21"] = close.ewm(span=21, adjust=False).mean()
    df["ema200"] = close.ewm(span=200, adjust=False).mean()
    pc = close.shift(1)
    tr = pd.concat([df["high"]-df["low"], (df["high"]-pc).abs(), (df["low"]-pc).abs()], axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
    df["vol_avg"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_avg"].replace(0, float("nan"))
    return df

def scan_one(symbol, tf="15m"):
    """يرجع إشارة Grade A أو None + سبب الرفض."""
    df = indicators(get_klines(symbol, tf))
    if df.empty or len(df) < 50:
        return None, "بيانات غير كافية"
    htf = indicators(get_klines(symbol, "1h", 100))
    if htf.empty:
        return None, "HTF غير متاح"
    h = htf.iloc[-1]
    htf_trend = "UP" if h["ema9"] > h["ema21"] and h["close"] > h["ema200"] else "DOWN" if h["ema9"] < h["ema21"] and h["close"] < h["ema200"] else "SIDEWAYS"
    if htf_trend == "SIDEWAYS":
        return None, "HTF عرضي"
    last = df.iloc[-1]
    rsi, price, atr = float(last["rsi"]), float(last["close"]), float(last["atr"])
    if rsi >= 70 and htf_trend == "UP":
        return None, "RSI متشبع"
    if rsi <= 30 and htf_trend == "DOWN":
        return None, "RSI متشبع"
    ext = abs(price - float(last["ema21"])) / float(last["ema21"]) * 100
    if ext > 2.5:
        return None, "السعر بعيد عن EMA21"
    if float(last["vol_ratio"]) < 1.8:
        return None, "حجم ضعيف"
    side = "LONG" if htf_trend == "UP" else "SHORT"
    is_long = side == "LONG"
    entry = (float(last["ema9"]) + float(last["ema21"])) / 2
    risk = atr * 2.0
    stop = entry - risk if is_long else entry + risk
    tp1 = entry + risk*1.5 if is_long else entry - risk*1.5
    tp2 = entry + risk*3.0 if is_long else entry - risk*3.0
    return {"symbol": symbol, "side": side, "grade": "A", "price": price,
            "entry": entry, "stop": stop, "tp1": tp1, "tp2": tp2,
            "rsi": rsi, "vol": float(last["vol_ratio"]), "htf": htf_trend}, ""

# ============================================================================
#  05 — EXECUTOR (Paper / Testnet / Real)
# ============================================================================
def sign(params, secret):
    q = urlencode(params)
    return q + "&signature=" + hmac.new(secret.encode(), q.encode(), hashlib.sha256).hexdigest()

def execute_order(cfg: BotConfig, sig, qty):
    """ينفذ حسب الوضع. PAPER = محاكاة فقط، مش بيبعت أي أوردر حقيقي."""
    if cfg.mode == "PAPER":
        log("INFO", f"[PAPER] {sig['symbol']} {sig['side']} qty={qty} entry={sig['entry']:.6g}")
        return True, "PAPER — محاكاة، مفيش فلوس اتحركت"
    if cfg.mode == "TESTNET":
        base = "https://testnet.binancefuture.com"
    else:  # REAL
        base = "https://fapi.binance.com"
    try:
        # 1. ظبط الرافعة
        params = {"symbol": sig["symbol"], "leverage": cfg.leverage, "timestamp": int(time.time()*1000)}
        SESSION.post(base + "/fapi/v1/leverage", params=sign(params, cfg.api_secret),
                     headers={"X-MBX-APIKEY": cfg.api_key}, timeout=8)
        # 2. أوردر السوق + ستوب + TP (OCO مبسط: 3 أوامر منفصلة)
        side = "BUY" if sig["side"] == "LONG" else "SELL"
        opp = "SELL" if side == "BUY" else "BUY"
        for otype, price, extra in [
            ("MARKET", None, {"quantity": qty}),
            ("STOP_MARKET", sig["stop"], {"quantity": qty, "stopPrice": sig["stop"], "closePosition": "true"}),
            ("TAKE_PROFIT_MARKET", sig["tp1"], {"quantity": qty, "stopPrice": sig["tp1"], "closePosition": "true"}),
        ]:
            p = {"symbol": sig["symbol"], "side": side if otype == "MARKET" else opp,
                 "type": otype, "timestamp": int(time.time()*1000)}
            if price is not None:
                p.update(extra)
            else:
                p["quantity"] = qty
            r = SESSION.post(base + "/fapi/v1/order", params=sign(p, cfg.api_secret),
                              headers={"X-MBX-APIKEY": cfg.api_key}, timeout=8)
            if r.status_code != 200:
                return False, f"Order failed: {r.text[:200]}"
        log("INFO", f"[{cfg.mode}] {sig['symbol']} {sig['side']} qty={qty} executed")
        return True, f"{cfg.mode} — الأوردر اتنفذ"
    except Exception as e:
        return False, str(e)

# ============================================================================
#  06 — UI
# ============================================================================
def main():
    init_db()
    st.set_page_config(page_title="BLY7TRADER AUTO BOT", page_icon="🤖", layout="wide")
    st.title("🤖 BLY7TRADER — بوت تداول آلي")
    st.warning("⚠️ **البوت ده مش بيكسب لوحده.** شغّله Paper أسبوع، وبعدين Testnet أسبوع، وبعدين فكّر في Real. لو حد قالك بوت بيكسب أكيد، بيضحك عليك.")

    # --- Sidebar: Config ---
    st.sidebar.header("⚙️ إعدادات البوت")
    mode = st.sidebar.selectbox("الوضع", ["PAPER (محاكاة — آمن)", "TESTNET (فلوس وهمية)", "REAL (فلوس حقيقية ⚠️)"])
    mode_val = {"PAPER (محاكاة — آمن)": "PAPER", "TESTNET (فلوس وهمية)": "TESTNET", "REAL (فلوس حقيقية ⚠️)": "REAL"}[mode]
    capital = st.sidebar.number_input("رأس المال $", 10.0, 100000.0, 100.0, 10.0)
    risk_pct = st.sidebar.slider("مخاطرة الصفقة %", 0.5, 2.0, 1.0, 0.5)
    max_daily = st.sidebar.slider("أقصى خسارة يومية %", 1.0, 5.0, 2.0, 0.5)
    max_pos = st.sidebar.slider("أقصى صفقات مفتوحة", 1, 3, 1)
    max_day = st.sidebar.slider("أقصى صفقات في اليوم", 1, 5, 2)
    leverage = st.sidebar.slider("الرافعة", 1, 10, 5)
    only_kz = st.sidebar.checkbox("اشتغل في Killzone بس (موصى به)", True)
    kill = st.sidebar.checkbox("⛔ Kill Switch — وقّف البوت فوراً", False)

    api_key = st.sidebar.text_input("API Key (لـ Testnet / Real بس)", type="password")
    api_secret = st.sidebar.text_input("API Secret", type="password")
    confirm = ""
    if mode_val == "REAL":
        st.sidebar.error("⚠️ REAL = فلوس حقيقية. البوت ممكن يخسرها كلها.")
        confirm = st.sidebar.text_input('اكتب CONFIRM عشان REAL يشتغل (غير كده مقفول)')

    cfg = BotConfig(mode=mode_val, capital=capital, risk_per_trade_pct=risk_pct,
                    max_daily_loss_pct=max_daily, max_open_positions=max_pos,
                    max_trades_per_day=max_day, leverage=leverage,
                    only_killzone=only_kz, kill_switch=kill,
                    api_key=api_key, api_secret=api_secret,
                    confirm_real=(confirm == "CONFIRM"))

    # --- Status ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("الوضع", mode_val)
    c2.metric("صفقات مفتوحة", len(open_positions()))
    c3.metric("PnL اليوم $", f"{today_pnl():.2f}")
    c4.metric("صفقات اليوم", today_trades())
    ok, reason = risk_check(cfg)
    if ok:
        st.success(f"✅ البوت جاهز — {reason}")
    else:
        st.error(f"🚫 {reason}")

    # --- Watchlist ---
    st.subheader("👀 العملات اللي البوت هيراقبها")
    watch = st.text_input("اكتب العملات بفاصلة", "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT")
    symbols = [s.strip().upper() for s in watch.split(",") if s.strip()]
    run = st.button("▶️ شغّل فحص واحد (مرة واحدة — مش Loop)", type="primary")

    if run:
        if not ok:
            st.error(reason)
        else:
            for sym in symbols:
                sig, rej = scan_one(sym, "15m")
                if not sig:
                    st.write(f"⏭️ {sym}: {rej}")
                    continue
                qty = position_size(cfg, sig["entry"], sig["stop"])
                if qty <= 0:
                    st.error(f"{sym}: حجم الصفقة صفر — الستوب بعيد أوي")
                    continue
                st.success(f"🎯 {sym} {sig['side']} — Entry {sig['entry']:.6g} | Stop {sig['stop']:.6g} | TP1 {sig['tp1']:.6g} | Qty {qty}")
                done, msg = execute_order(cfg, sig, qty)
                if done:
                    save_trade({**sig, "mode": mode_val, "qty": qty, "reason": "Grade A + HTF + Pullback"})
                    st.info(msg)
                else:
                    st.error(msg)

    # --- History ---
    st.divider()
    st.subheader("📚 سجل البوت")
    with sqlite3.connect(DB) as c:
        trades = pd.read_sql_query("SELECT * FROM bot_trades ORDER BY id DESC LIMIT 100", c)
        logs = pd.read_sql_query("SELECT * FROM bot_logs ORDER BY id DESC LIMIT 50", c)
    if not trades.empty:
        st.dataframe(trades, use_container_width=True, hide_index=True)
    else:
        st.info("لسه مفيش صفقات.")
    if st.checkbox("عرض اللوجز"):
        st.dataframe(logs, use_container_width=True, hide_index=True)

    st.divider()
    st.caption("🤖 BLY7TRADER BOT — أداة تعليمية. التداول الآلي فيه مخاطرة عالية. جرّب Paper + Testnet أولاً. متشغلش REAL بمبلغ متقدرش تخسره.")

if __name__ == "__main__":
    main()
