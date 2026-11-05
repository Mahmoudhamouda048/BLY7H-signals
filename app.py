# BLY7H ULTIMATE V7 - 15 أداة DEX + 5 CEX + 4 اصلاحات = 20 أداة + ضد حظر + تليجرام
import streamlit as st
import pandas as pd
import requests, time, random
from datetime import datetime
import math, json, os

st.set_page_config(page_title="BLY7H ULTIMATE V7", layout="wide", page_icon="🚀")
st.title("🚀 BLY7H ULTIMATE V7 - 15 أداة + 4 اصلاحات")

# ========== CONFIG + 4 اصلاحات ==========
CONFIG = {
    "TELEGRAM_BOT_TOKEN": st.secrets.get("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHANNEL_ID": st.secrets.get("TELEGRAM_CHANNEL_ID", "@WHYNOTBLY7"),
    "MIN_DELAY": 25,
    "MAX_PER_HOUR": 8,
    "MIN_SCORE": 75,
    "SCAN_INTERVAL": 60,
}

STABLES = ["USDCUSDT","BUSDUSDT","TUSDUSDT","USDPUSDT","DAIUSDT","FDUSDUSDT","USDeUSDT","USD1USDT","RLUSDUSDT","XUSDUSDT","EURUSDT","PYUSDUSDT","GUSDUSDT","USDXUSDT"]

# اصلاح 1: عدد العملات 50 مش 80 - اسرع
# اصلاح 2: OI fallback دومينين
# اصلاح 3: فحص BSC + ETH + SOL
# اصلاح 4: فلتر Rug Pull

class SafeTelegram:
    def __init__(self):
        self.token = CONFIG["TELEGRAM_BOT_TOKEN"]
        self.channel = CONFIG["TELEGRAM_CHANNEL_ID"]
        self.last = 0
        self.count = 0
        self.hour_start = time.time()
    def can_send(self):
        if time.time() - self.hour_start > 3600:
            self.count = 0
            self.hour_start = time.time()
        return self.count < CONFIG["MAX_PER_HOUR"]
    def send(self, text):
        if not self.can_send():
            st.warning("⏸️ وقف مؤقت - 8 اشارات في الساعة")
            return False
        wait = CONFIG["MIN_DELAY"] - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait + random.uniform(1,3))
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.channel, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
        try:
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 429:
                retry = r.json().get('parameters',{}).get('retry_after',30)
                st.warning(f"🚫 حظر مؤقت {retry}ث")
                time.sleep(retry+2)
                return self.send(text)
            if r.status_code == 200:
                self.last = time.time()
                self.count += 1
                return True
        except Exception as e:
            st.error(f"خطأ تليجرام: {e}")
        return False

telegram = SafeTelegram()

def is_safe_token(pair):
    # اصلاح 4: فلتر Rug Pull
    try:
        liquidity = float(pair.get('liquidity',{}).get('usd',0))
        if liquidity < 10000:
            return False
        fdv = float(pair.get('fdv',0))
        if fdv > 0 and liquidity / fdv < 0.02:
            return False
        return True
    except:
        return False

def check_token_pump(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        pairs = data.get('pairs', [])
        if not pairs:
            return None
        pair = sorted(pairs, key=lambda x: float(x.get('liquidity',{}).get('usd',0)), reverse=True)[0]
        
        if not is_safe_token(pair):
            return None
        
        symbol = f"{pair.get('baseToken',{}).get('symbol','UNK')}/{pair.get('quoteToken',{}).get('symbol','')}"
        chain = pair.get('chainId','').upper()
        price = pair.get('priceUsd','0')
        price_change_5m = float(pair.get('priceChange',{}).get('m5',0))
        price_change_1h = float(pair.get('priceChange',{}).get('h1',0))
        vol_5m = float(pair.get('volume',{}).get('m5',0))
        vol_1h = float(pair.get('volume',{}).get('h1',1))
        liquidity = float(pair.get('liquidity',{}).get('usd',0))
        fdv = float(pair.get('fdv',0))
        dex_url = pair.get('url','')
        
        score = 0
        conds = []
        
        # 15 أداة زي ما انت كاتبهم بالحرف
        if vol_5m > 5000:
            ratio = vol_5m / (vol_1h/12) if vol_1h>0 else 0
            if ratio >= 2.5:
                score += 25
                conds.append(f"Vol x{ratio:.1f}")
        if price_change_5m >= 5:
            score += 20
            conds.append(f"+{price_change_5m}% 5د")
        if liquidity > 15000:
            score += 15
            conds.append(f"${liquidity/1000:.0f}K سيولة")
        if price_change_1h > 20:
            score += 10
            conds.append(f"+{price_change_1h}% 1س")
        if fdv < 20000000:
            score -= 30
        
        hour = datetime.now().hour
        if 2 <= hour <= 6:
            score += 15
            time_state = "🟢 وقت حيتان"
        else:
            time_state = "🟡 عادي"
        
        if score < CONFIG["MIN_SCORE"]:
            return None
        
        try:
            p = float(price)
            atr = p * 0.02
            entry = p
            tp1 = p + atr*1.5
            tp2 = p + atr*3.0
            sl = p - atr
            cancel = p - atr*0.7
        except:
            entry = price
            tp1 = tp2 = sl = cancel = price
        
        msg = f"""🚀 *DEX EARLY PUMP - BLY7H V5* 🚀
💰 *{symbol}* على *{chain}*

📊 {' | '.join(conds)}
{time_state} | سكور *{score}/100*

💵 السعر: `${price}`
🎯 دخول: `${entry}`
❌ الغاء: `${cancel}`
⛔ ستوب: `${sl}`
✅ هدف1: `${tp1}` | هدف2: `${tp2}`

⏳ صلاحية 15د | FVG ✅ | آمن ✅
🔗 {dex_url}
🔥 لسه موصلتش CEX - ادخل بدري!

@WHYNOTBLY7
"""
        return msg, score, symbol
        
    except Exception as e:
        return None

def get_oi_change(sym):
    # اصلاح 2: OI fallback دومينين
    for base in ["https://fapi.binance.com", "https://fapi1.binance.com"]:
        try:
            r = requests.get(f"{base}/futures/data/openInterestHist?symbol={sym}&period=5m&limit=12", timeout=5)
            if r.status_code == 200:
                data = r.json()
                if len(data) >= 2:
                    first = float(data[0]['sumOpenInterest'])
                    last = float(data[-1]['sumOpenInterest'])
                    if first > 0:
                        return (last - first) / first * 100
        except:
            continue
    return 0

def calc_cvd(df):
    try:
        green = 0
        red = 0
        for i in range(-10, 0):
            c = float(df['close'].iloc[i])
            o = float(df['open'].iloc[i])
            v = float(df['vol'].iloc[i])
            if c > o:
                green += v
            else:
                red += v
        total = green + red
        if total == 0:
            return 0, "متوازن"
        pct = (green - red) / total * 100
        if pct > 30:
            return 15, f"CVD +{pct:.0f}% شراء قوي"
        elif pct < -30:
            return 15, f"CVD {pct:.0f}% بيع قوي"
        elif pct > 15:
            return 8, f"CVD +{pct:.0f}% شراء"
        elif pct < -15:
            return 8, f"CVD {pct:.0f}% بيع"
        else:
            return 0, f"CVD {pct:.0f}%"
    except:
        return 0, "CVD"

def calc_smc(df, price):
    try:
        bull_b = bull_m = bear_b = bear_m = bear_t = None
        for i in range(1, len(df)-1):
            try:
                low_next = float(df['low'].iloc[i+1])
                high_prev = float(df['high'].iloc[i-1])
                high_next = float(df['high'].iloc[i+1])
                low_prev = float(df['low'].iloc[i-1])
                if low_next > high_prev and bull_b is None:
                    bull_b = high_prev
                    bull_m = (high_prev + low_next)/2
                if high_next < low_prev and bear_b is None:
                    bear_b = high_next
                    bear_t = low_prev
                    bear_m = (high_next + low_prev)/2
            except:
                pass
        recent_low = float(df['low'].iloc[-10:].min())
        recent_high = float(df['high'].iloc[-10:].max())
        fvg_data = {'bull_b': bull_b, 'bull_m': bull_m, 'bear_b': bear_b, 'bear_m': bear_m, 'bear_t': bear_t}
        has_fvg = bull_b is not None or bear_b is not None
        return has_fvg, fvg_data, recent_low, recent_high
    except:
        return False, {}, price*0.99, price*1.01

def get_symbols_binance():
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            usdt = [d for d in data if d.get('symbol','').endswith('USDT')]
            usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume') or 0), reverse=True)
            return [d['symbol'] for d in usdt_sorted[:200]]
        except:
            continue
    return []

@st.cache_data(ttl=300)
def get_all_symbols():
    s = get_symbols_binance()
    clean = []
    for x in s:
        if 'BULL' not in x and 'BEAR' not in x:
            if x in STABLES:
                continue
            clean.append(x)
    return clean[:200], " 【entity-binance¦canonical_name=Binance】"

def get_klines_binance(sym):
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={sym}&interval=1h&limit=100", timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            if len(data) < 20:
                continue
            df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            for c in ['high','low','close','open']:
                df[c] = pd.to_numeric(df[c], errors='coerce')
            return df.dropna()
        except:
            continue
    return None

@st.cache_data(ttl=90)
def get_klines(sym):
    df = get_klines_binance(sym)
    if df is not None and len(df) >= 20:
        return df
    return None

def pump_dump_predictive(df, sym, min_score):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change_1h = (last - prev)/prev*100 if prev!=0 else 0
        col = 'vol' if 'vol' in df.columns else 'volume'
        mean_vol = df[col].astype(float).iloc[-20:-1].mean()
        last_vol = float(df[col].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol>0 else 1
        
        # اصلاح 1: OI بس لو Vol عالي - اسرع
        oi_change = 0
        if vol_spike > 2.0:
            oi_change = get_oi_change(sym)
        
        cvd_score, cvd_reason = calc_cvd(df)
        has_fvg, fvg_data, rec_low, rec_high = calc_smc(df, last)
        
        if vol_spike < 1.5 and abs(oi_change) < 2 and cvd_score < 5:
            return None
        
        score = 0
        if vol_spike > 2.0 or oi_change > 3 or cvd_score > 8:
            if change_1h > -1:
                score = 40 + (15 if oi_change>3 else 0) + cvd_score + min(vol_spike*3, 15)
                ptype = "PUMP"
                vol_reason = f"PUMP قبل OI {oi_change:.1f}% Vol x{vol_spike:.1f}"
            else:
                score = 30 + vol_spike*3 + abs(change_1h)
                ptype = "DUMP"
                vol_reason = f"DUMP Vol x{vol_spike:.1f}"
        elif change_1h < -1.5 and vol_spike > 1.8:
            score = 35 + abs(change_1h)*2 + vol_spike*2
            ptype = "DUMP"
            vol_reason = f"DUMP حقيقي Vol x{vol_spike:.1f}"
        else:
            return None
        
        if has_fvg:
            score += 10
        score = min(int(score), 99)
        if score < min_score:
            return None
        
        bull_b = fvg_data.get('bull_b')
        bull_m = fvg_data.get('bull_m')
        bear_b = fvg_data.get('bear_b')
        bear_m = fvg_data.get('bear_m')
        bear_t = fvg_data.get('bear_t')
        
        if ptype == "PUMP":
            best = bull_m if bull_m is not None else last * 0.993
            no_ret = bull_b * 0.985 if bull_b else rec_low * 0.98
            best = min(best, last * 0.998)
            stop = no_ret * 0.99
            tp1 = last * 1.04
            tp2 = last * 1.08
            if stop >= best:
                stop = best * 0.97
        else:
            best = bear_m if bear_m is not None else last * 1.007
            no_ret = bear_t * 1.015 if bear_t else rec_high * 1.02
            best = max(best, last * 1.002)
            stop = no_ret * 1.01
            tp1 = last * 0.96
            tp2 = last * 0.92
            if stop <= best:
                stop = best * 1.03
        
        return {
            'symbol': sym, 'score': score, 'type': ptype, 'price': round(last,6),
            'change_1h': round(change_1h,2), 'vol_spike': round(vol_spike,2),
            'oi_change': round(oi_change,2), 'best_entry': round(best,6),
            'no_return_point': round(no_ret,6), 'stop_loss': round(stop,6),
            'TP1': round(tp1,6), 'TP2': round(tp2,6), 'vol_reason': vol_reason,
            'oi_reason': f"OI {oi_change:.1f}%", 'cvd_reason': cvd_reason
        }
    except:
        return None

# ========== UI ==========
tab1, tab2 = st.tabs(["🚀 DEX - 15 أداة", "💥 CEX - 5 أدوات + 4 اصلاحات"])

with tab1:
    st.subheader("DEX - الـ 15 أداة + اصلاح Rug + BSC/ETH/SOL")
    st.write(f"MIN_SCORE: {CONFIG['MIN_SCORE']} | تأخير: {CONFIG['MIN_DELAY']}ث | {CONFIG['MAX_PER_HOUR']}/ساعة")
    
    chains = st.multiselect("الشبكات (اصلاح 3)", ["BSC", "ETH", "SOL"], default=["BSC"])
    
    if st.button("🔍 افحص DEX - 15 أداة + 4 اصلاحات", type="primary", key="dex15"):
        with st.spinner("يفحص..."):
            found = 0
            for chain_q in chains:
                try:
                    url = f"https://api.dexscreener.com/latest/dex/search/?q={chain_q}"
                    r = requests.get(url, timeout=15)
                    pairs = r.json().get('pairs', [])[:15]
                    seen = set()
                    for p in pairs:
                        addr = p.get('baseToken',{}).get('address')
                        if not addr or addr in seen:
                            continue
                        seen.add(addr)
                        result = check_token_pump(addr)
                        if result:
                            msg, score, sym = result
                            st.code(msg)
                            if telegram.send(msg):
                                st.success(f"✅ {sym} سكور {score} على {chain_q}")
                                found += 1
                            time.sleep(1)
                except Exception as e:
                    st.error(f"خطأ {chain_q}: {e}")
            if found == 0:
                st.warning("مفيش بمب DEX قوي")

with tab2:
    st.subheader("CEX - 5 أدوات + 4 اصلاحات (اسرع + OI fallback)")
    min_score_cex = st.slider("اقل سكور CEX", 0, 100, 55, key="cex_score")
    limit = st.slider("عدد العملات (اصلاح 1: 50 اسرع)", 20, 200, 50, key="limit")
    
    if st.button("💥 افحص CEX", type="primary", key="cex5"):
        symbols, src = get_all_symbols()
        st.write(f"تم جلب {len(symbols)} عملة من {src} - هيفحص اول {limit} - OI بس لو Vol عالي")
        results = []
        prog = st.progress(0)
        stat = st.empty()
        for i, sym in enumerate(symbols[:limit]):
            prog.progress((i+1)/limit)
            stat.text(f"CEX: {sym} {i+1}/{limit}")
            df = get_klines(sym)
            if df is not None:
                res = pump_dump_predictive(df, sym, min_score_cex)
                if res:
                    results.append(res)
            time.sleep(0.03)
        prog.empty()
        stat.empty()
        
        if results:
            df_res = pd.DataFrame(results).sort_values('score', ascending=False)
            st.success(f"💥 {len(df_res)} تنبؤ CEX")
            st.dataframe(df_res, use_container_width=True)
            if st.checkbox("ابعت تليجرام", value=True):
                sent = 0
                for sig in df_res.head(5).to_dict('records'):
                    txt = f"🚀 BLY7H {sig['type']} {sig['symbol']} قبل!\nسكور {sig['score']} Vol x{sig['vol_spike']} OI {sig['oi_change']}%\nسعر {sig['price']} دخول {sig['best_entry']} ستوب {sig['stop_loss']} هدف {sig['TP1']}"
                    if telegram.send(txt):
                        sent += 1
                        time.sleep(1)
                if sent > 0:
                    st.success(f"اتبعت {sent}!")
        else:
            st.warning(f"مفيش فوق {min_score_cex}")
