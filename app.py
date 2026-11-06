import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time, json, os, math

st.set_page_config(page_title="BLY7H ULTIMATE - MIDAS", layout="wide", page_icon="🚀")
st.title("🚀 BLY7H ULTIMATE - MIDAS + 【entity-KUCOIN¦canonical_name=KUCOIN】 قبل الحركة")

st.sidebar.header("Settings")
min_score = st.sidebar.slider("اقل سكور", 0, 100, 55)
limit_coins = st.sidebar.slider("عدد العملات", 20, 200, 80)
filter_stable = st.sidebar.checkbox("فلتر المستقرة", value=True)
send_tg = st.sidebar.checkbox("تليجرام", value=True)
focus = st.sidebar.radio("ركز على", ["🔥 【entity-KUCOIN¦canonical_name=KUCOIN】 فقط - 4x 5x", " 【entity-KUCOIN¦canonical_name=KUCOIN】 + CEX + DEX"], index=0)
ai_filter = st.sidebar.radio("فلتر AI - زي MidasFlow", ["قياسي", "صارم", "إيقاف"], index=0)

STABLES = ["USDCUSDT","BUSDUSDT","TUSDUSDT","USDPUSDT","DAIUSDT","FDUSDUSDT","USDeUSDT","USD1USDT","RLUSDUSDT","XUSDUSDT","EURUSDT","PYUSDUSDT","GUSDUSDT"]

def send_tg_alert(text):
    try:
        bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN")
        chat_id = st.secrets.get("TELEGRAM_CHANNEL_ID", st.secrets.get("TELEGRAM_CHAT_ID"))
        if not bot_token or not chat_id:
            return False
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 429:
            retry = r.json().get('parameters',{}).get('retry_after',30)
            time.sleep(retry+2)
            return send_tg_alert(text)
        return r.status_code == 200
    except:
        return False

# ========== AI PATTERN MEMORY - زي MidasFlow ==========
PATTERNS = [
    {"name": "HighVol Pump", "vol": 3.0, "cvd": 15, "change": 1},
    {"name": "FVG Breakout", "vol": 2.0, "cvd": 8, "change": 0.5},
    {"name": "OI Accumulation", "vol": 2.5, "cvd": 10, "change": 0},
    {"name": "Quiet Accumulation", "vol": 2.8, "cvd": 12, "change": -0.5},
]

def calc_ai_similarity(vol_spike, cvd_score, change_1h):
    best = []
    for p in PATTERNS:
        # شبه قد ايه للنمط ده
        vol_sim = max(0, 100 - abs(vol_spike - p["vol"]) * 20)
        cvd_sim = max(0, 100 - abs(cvd_score - p["cvd"]) * 3)
        sim = int((vol_sim + cvd_sim) / 2)
        if sim > 60:
            best.append(f"شبه {p['name']} {sim}%")
    if not best:
        return 0, "نمط جديد"
    # AI بونص = اعلى شبه
    max_sim = 0
    for b in best:
        try:
            v = int(b.split()[-1].replace('%',''))
            if v > max_sim:
                max_sim = v
        except:
            pass
    ai_bonus = int(max_sim * 0.2)  # 77% -> 15
    return ai_bonus, " | ".join(best[:2])

def get_oi_change(sym):
    for base in ["https://fapi.binance.com", "https://fapi1.binance.com"]:
        try:
            r = requests.get(f"{base}/futures/data/openInterestHist?symbol={sym}&period=5m&limit=12", timeout=5)
            if r.status_code == 200:
                data = r.json()
                if len(data) >= 2:
                    first = float(data[0]['sumOpenInterest'])
                    last = float(data[-1]['sumOpenInterest'])
                    if first>0:
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
            usdt = []
            for d in data:
                sym = d.get('symbol','')
                if sym.endswith('USDT'):
                    usdt.append(d)
            usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume') or 0), reverse=True)
            res = []
            for d in usdt_sorted[:400]:
                res.append(d['symbol'])
            return res
        except:
            continue
    return []

@st.cache_data(ttl=300)
def get_all_symbols():
    s = get_symbols_binance()
    clean = []
    for x in s:
        if 'BULL' not in x and 'BEAR' not in x:
            if filter_stable and x in STABLES:
                continue
            clean.append(x)
    return clean[:400], " 【entity-binance¦canonical_name=Binance】"

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

# ========== صيغة تليجرام زي الصورة بالظبط ==========
def format_telegram_midas(sig, source="CEX"):
    # sig فيها كل البيانات
    now = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    direction = "UP" if sig['type'] == "PUMP" or "PUMP" in sig['type'] else "DOWN"
    emoji_dir = "💥" if direction == "UP" else "💥"
    # MidasFlow: ثقة + مرحلة + تأكيد + RR
    conf = sig.get('confidence', sig['score'])
    qual = "جيدة" if conf >= 60 else "متوسطة" if conf >= 40 else "منخفضة"
    phase = sig.get('phase', "بامب" if direction=="UP" else "هبوط")
    rr = sig.get('rr', "1:0.5")
    leader = sig.get('leader', source)
    confirm = sig.get('confirm', "5 منصة")
    # حساب نسب الوقف والاهداف
    price = sig['price']
    stop_pct = abs(sig['stop_loss'] - price)/price*100
    tp1_pct = abs(sig['TP1'] - price)/price*100
    tp2_pct = abs(sig['TP2'] - price)/price*100
    cancel_pct = abs(sig.get('no_return_point', price) - price)/price*100
    
    # الصيغة اللي في الصورة + MidasFlow
    msg = f"""{emoji_dir} BLY7H AI SIGNAL {emoji_dir}

💰 {sig['symbol']} - {direction}
📊 سكور: {sig['score']} (base {sig.get('base_score', 65)} + AI {sig.get('ai_bonus', 0)})
💵 السعر: {price}
📈 تغير 1س: {sig['change_1h']}%
📦 فوليوم x{sig['vol_spike']}

🎯 دخول: {sig['best_entry']}
❌ الغاء: {sig.get('no_return_point', sig['best_entry'])}
⛔ ستوب: {sig['stop_loss']}
✅ هدف1: {sig['TP1']}
✅ هدف2: {sig['TP2']}

💡 لماذا هذه الإشارة:
- ثقة النموذج {conf}% - {qual}
- مرحلة السوق: {phase}
- تأكيد تدفق الأوامر: {confirm}، القائد {leader}
- نسبة المخاطرة/العائد {rr}

🧠 AI: {sig.get('ai_pattern', 'نمط جديد')}
FVG: {'نعم' if sig.get('has_fvg') else 'لا'}

⏰ {now}
"""
    return msg

def pump_dump_predictive(df, sym, source="CEX"):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change_1h = (last - prev)/prev*100 if prev!=0 else 0
        # قبل الحركة فقط - لو طلع 5%+ خلاص فات
        if abs(change_1h) > 5:
            return None
        col = 'vol' if 'vol' in df.columns else 'volume'
        mean_vol = df[col].astype(float).iloc[-20:-1].mean()
        last_vol = float(df[col].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol>0 else 1
        if vol_spike < 2.0:
            return None
        oi_change = get_oi_change(sym) if source=="CEX" else 0
        cvd_score, cvd_reason = calc_cvd(df)
        if cvd_score < 8 and oi_change < 3:
            return None
        has_fvg, fvg_data, rec_low, rec_high = calc_smc(df, last)
        ai_bonus, ai_pattern = calc_ai_similarity(vol_spike, cvd_score, change_1h)
        base_score = 40 + (15 if oi_change>3 else 0) + cvd_score + min(vol_spike*3, 15)
        if has_fvg:
            base_score += 10
        base_score = min(int(base_score), 80)
        total_score = min(base_score + ai_bonus, 99)
        # فلتر MidasFlow
        if ai_filter == "صارم" and total_score < 70:
            return None
        if ai_filter == "قياسي" and total_score < 60:
            return None
        if total_score < min_score:
            return None
        # MidasFlow: ثقة + مرحلة + RR
        confidence = total_score
        if abs(change_1h) < 1 and vol_spike < 2.5:
            phase = "هادي"
        elif vol_spike > 2.5:
            phase = "بامب"
        else:
            phase = "متذبذب"
        bull_b = fvg_data.get('bull_b')
        bull_m = fvg_data.get('bull_m')
        bear_m = fvg_data.get('bear_m')
        bear_t = fvg_data.get('bear_t')
        if change_1h > -1:
            ptype = "PUMP"
            best = bull_m if bull_m is not None else last * 0.993
            no_ret = bull_b * 0.985 if bull_b else rec_low * 0.98
            best = min(best, last * 0.998)
            stop = no_ret * 0.99
            tp1 = last * 1.04
            tp2 = last * 1.08
            if stop >= best:
                stop = best * 0.97
        else:
            ptype = "DUMP"
            best = bear_m if bear_m is not None else last * 1.007
            no_ret = bear_t * 1.015 if bear_t else rec_high * 1.02
            best = max(best, last * 1.002)
            stop = no_ret * 1.01
            tp1 = last * 0.96
            tp2 = last * 0.92
            if stop <= best:
                stop = best * 1.03
        risk = abs(stop - last)/last*100 if last!=0 else 1
        reward = abs(tp1 - last)/last*100 if last!=0 else 1
        rr = reward / risk if risk>0 else 0
        return {
            'symbol': sym, 'score': total_score, 'base_score': base_score, 'ai_bonus': ai_bonus,
            'ai_pattern': ai_pattern, 'type': ptype, 'price': round(last,6),
            'change_1h': round(change_1h,2), 'vol_spike': round(vol_spike,2),
            'oi_change': round(oi_change,2), 'best_entry': round(best,6),
            'no_return_point': round(no_ret,6), 'stop_loss': round(stop,6),
            'TP1': round(tp1,6), 'TP2': round(tp2,6), 'vol_reason': f"Vol x{vol_spike:.1f}",
            'oi_reason': f"OI {oi_change:.1f}%", 'cvd_reason': cvd_reason,
            'confidence': confidence, 'phase': phase, 'rr': f"1:{rr:.1f}",
            'confirm': "5 منصة", 'leader': source, 'has_fvg': has_fvg
        }
    except:
        return None

def check_dex_pump(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        r = requests.get(url, timeout=10)
        pairs = r.json().get('pairs', [])
        if not pairs:
            return None
        pair = sorted(pairs, key=lambda x: float(x.get('liquidity',{}).get('usd',0)), reverse=True)[0]
        symbol = pair.get('baseToken',{}).get('symbol','UNK')
        chain = pair.get('chainId','').upper()
        price = pair.get('priceUsd','0')
        change_5m = float(pair.get('priceChange',{}).get('m5',0))
        vol_5m = float(pair.get('volume',{}).get('m5',0))
        vol_1h = float(pair.get('volume',{}).get('h1',1))
        liquidity = float(pair.get('liquidity',{}).get('usd',0))
        dex_url = pair.get('url','')
        score = 0
        conds = []
        if vol_5m > 5000:
            ratio = vol_5m / (vol_1h/12) if vol_1h>0 else 0
            if ratio >= 2.5:
                score += 25
                conds.append(f"Vol x{ratio:.1f}")
        if change_5m >= 5:
            score += 20
            conds.append(f"+{change_5m}% 5د")
        if liquidity > 15000:
            score += 15
            conds.append(f"${liquidity/1000:.0f}K")
        if score < min_score:
            return None
        p = float(price)
        msg = f"🚀 DEX EARLY PUMP - {symbol} على {chain}\n📊 {' | '.join(conds)} سكور {score}\n💵 {price} دخول {p} الغاء {p*0.97:.8f} ستوب {p*0.95:.8f} هدف {p*1.3:.8f}\n🔗 {dex_url}\n@WHYNOTBLY7"
        return msg, score, symbol
    except:
        return None

def get_kucoin_symbols():
    try:
        r = requests.get("https://api.kucoin.com/api/v1/market/allTickers", timeout=15)
        data = r.json().get('data', {}).get('ticker', [])
        usdt = []
        for d in data:
            sym = d.get('symbol','')
            if not sym.endswith('-USDT'):
                continue
            if 'USDC' in sym or 'DAI' in sym or 'BUSD' in sym:
                continue
            usdt.append(d)
        usdt_sorted = sorted(usdt, key=lambda x: float(x.get('volValue') or 0), reverse=True)
        res = []
        for d in usdt_sorted[:150]:
            res.append(d['symbol'])
        return res
    except:
        return []

@st.cache_data(ttl=90)
def get_kucoin_klines(sym):
    try:
        end = int(time.time())
        start = end - 100*3600
        url = f"https://api.kucoin.com/api/v1/market/candles?type=1hour&symbol={sym}&startAt={start}&endAt={end}"
        r = requests.get(url, timeout=10)
        data = r.json().get('data', [])
        if len(data) < 20:
            return None
        df = pd.DataFrame(data, columns=['time','open','close','high','low','vol','turnover'])
        for c in ['open','close','high','low','vol']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.sort_values('time')
        return df.dropna()
    except:
        return None

def pump_dump_kucoin(df, sym):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change_1h = (last - prev)/prev*100 if prev!=0 else 0
        if len(df) >= 24:
            first24 = float(df['close'].iloc[-24])
            change_24 = (last - first24)/first24*100 if first24!=0 else 0
        else:
            change_24 = 0
        if change_24 > 50:
            return None
        if change_24 < -50:
            return None
        mean_vol = float(df['vol'].iloc[-20:-1].mean())
        last_vol = float(df['vol'].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol>0 else 1
        if vol_spike < 2.5:
            return None
        if abs(change_1h) > 5:
            return None
        cvd_score, cvd_reason = calc_cvd(df)
        if cvd_score < 8:
            return None
        has_fvg, fvg_data, rec_low, rec_high = calc_smc(df, last)
        ai_bonus, ai_pattern = calc_ai_similarity(vol_spike, cvd_score, change_1h)
        base_score = 40 + cvd_score + min(vol_spike*3, 15)
        if has_fvg:
            base_score += 10
        base_score = min(int(base_score), 80)
        total_score = min(base_score + ai_bonus, 99)
        if total_score < min_score:
            return None
        if ai_filter == "صارم" and total_score < 70:
            return None
        bull_b = fvg_data.get('bull_b')
        bull_m = fvg_data.get('bull_m')
        best = bull_m if bull_m is not None else last * 0.993
        no_ret = bull_b * 0.985 if bull_b else rec_low * 0.98
        best = min(best, last * 0.998)
        stop = no_ret * 0.99
        tp1 = last * 1.04
        tp2 = last * 1.08
        if stop >= best:
            stop = best * 0.97
        risk = abs(stop - last)/last*100 if last!=0 else 1
        reward = abs(tp1 - last)/last*100 if last!=0 else 1
        rr = reward / risk if risk>0 else 0
        return {
            'symbol': sym, 'score': total_score, 'base_score': base_score, 'ai_bonus': ai_bonus,
            'ai_pattern': ai_pattern, 'type': "PUMP", 'price': round(last,6),
            'change_1h': round(change_1h,2), 'change_24h': round(change_24,1), 'vol_spike': round(vol_spike,2),
            'oi_change': 0, 'best_entry': round(best,6),
            'no_return_point': round(no_ret,6), 'stop_loss': round(stop,6),
            'TP1': round(tp1,6), 'TP2': round(tp2,6), 'vol_reason': f"تجميع Vol x{vol_spike:.1f}",
            'oi_reason': "KUCOIN -", 'cvd_reason': cvd_reason,
            'confidence': total_score, 'phase': "بامب" if vol_spike>2.5 else "هادي", 'rr': f"1:{rr:.1f}",
            'confirm': "5 منصة", 'leader': "KUCOIN", 'has_fvg': has_fvg
        }
    except:
        return None

if focus == "🔥 KUCOIN فقط - 4x 5x":
    tab1, = st.tabs(["🔥 KUCOIN 4x 5x - قبل الحركة"])
    tabs = [tab1]
else:
    tab1, tab2, tab3 = st.tabs(["🔥 KUCOIN 4x 5x - قبل الحركة", "💥 CEX", "🚀 DEX"])
    tabs = [tab1, tab2, tab3]

with tabs[0]:
    st.subheader("🔥 KUCOIN - MidasFlow - قبل الحركة")
    if st.button("🔥 افحص KUCOIN", type="primary", key="kucoin_main"):
        ksyms = get_kucoin_symbols()
        st.write(f"تم جلب {len(ksyms)} عملة - هيفحص اول {limit_coins}")
        kresults = []
        prog2 = st.progress(0)
        stat2 = st.empty()
        for i, sym in enumerate(ksyms[:limit_coins]):
            prog2.progress((i+1)/len(ksyms[:limit_coins]))
            stat2.text(f" KUCOIN: {sym} {i+1}/{len(ksyms[:limit_coins])}")
            dfk = get_kucoin_klines(sym)
            if dfk is not None:
                resk = pump_dump_kucoin(dfk, sym)
                if resk:
                    kresults.append(resk)
            time.sleep(0.05)
        prog2.empty()
        stat2.empty()
        if kresults:
            df_k = pd.DataFrame(kresults).sort_values('score', ascending=False)
            st.success(f"🔥 {len(df_k)} تجميع قبل البمب")
            st.dataframe(df_k, use_container_width=True)
            if send_tg:
                for sig in df_k.head(5).to_dict('records'):
                    msg = format_telegram_midas(sig, source="【entity-KUCOIN¦canonical_name=KUCOIN】")
                    st.code(msg)
                    if send_tg_alert(msg):
                        st.success(f"✅ {sig['symbol']}")
                        time.sleep(1)
        else:
            st.warning("مفيش تجميع قبل بمب - العملات اللي طلعت 100% مش هتتبعت")

if focus != "🔥 KUCOIN فقط - 4x 5x":
    with tabs[1]:
        st.subheader("CEX - MidasFlow قبل الحركة")
        if st.button("💥 افحص CEX", type="primary", key="cex"):
            st.cache_data.clear()
            st.rerun()
        symbols, src = get_all_symbols()
        st.write(f"تم جلب {len(symbols)} عملة - هيفحص اول {limit_coins}")
        to_scan = symbols[:limit_coins]
        results = []
    
