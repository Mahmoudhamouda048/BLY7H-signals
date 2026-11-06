import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time, json, os

st.set_page_config(page_title="BLY7H ULTIMATE", layout="wide", page_icon="💎")

# ========== 🎨 واجهة فخمة ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@700;900&display=swap');
* { font-family: 'Cairo', sans-serif !important; }
.main { background: #0a0e1a; }
.block-container { padding-top: 1rem !important; max-width: 1300px; }

/* هيدر */
.hero {
  background: linear-gradient(135deg, #6a00ff 0%, #00d4ff 50%, #00ff88 100%);
  border-radius: 20px; padding: 28px 30px; color: white;
  box-shadow: 0 10px 40px rgba(106,0,255,0.4);
  margin-bottom: 18px; position: relative; overflow: hidden;
}
.hero h1 { font-size: 38px; font-weight: 900; margin: 0; text-shadow: 0 2px 20px rgba(0,0,0,0.3); }
.hero p { font-size: 15px; opacity: 0.95; margin: 6px 0 0 0; }
.hero-badge {
  display: inline-block; background: rgba(255,255,255,0.25); backdrop-filter: blur(10px);
  padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-top: 12px; margin-right: 6px;
}

/* كروت احصائيات */
.stat-grid { display: flex; gap: 12px; margin-bottom: 18px; }
.stat-card {
  flex: 1; background: #141a2e; border: 1px solid #1f2a4a; border-radius: 16px;
  padding: 16px; text-align: center;
}
.stat-card .num { font-size: 28px; font-weight: 900; color: white; }
.stat-card .lbl { font-size: 12px; color: #8b9bb4; margin-top: 2px; }
.stat-card.green .num { color: #00ff88; }
.stat-card.purple .num { color: #a855f7; }
.stat-card.blue .num { color: #00d4ff; }
.stat-card.orange .num { color: #ffaa00; }

/* كارت اشارة */
.sig-card {
  background: #141a2e; border: 1px solid #1f2a4a; border-radius: 18px;
  padding: 18px; margin-bottom: 14px; position: relative; overflow: hidden;
}
.sig-card.pump { border-right: 5px solid #00ff88; }
.sig-card.dump { border-right: 5px solid #ff3b5c; }
.sig-top { display: flex; justify-content: space-between; align-items: center; }
.sig-symbol { font-size: 22px; font-weight: 900; color: white; }
.sig-score {
  background: linear-gradient(135deg, #00ff88, #00d4ff); color: #000;
  padding: 6px 16px; border-radius: 20px; font-weight: 900; font-size: 16px;
}
.sig-score.low { background: linear-gradient(135deg, #ffaa00, #ff3b5c); color: white; }
.sig-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.pill {
  background: #1e2942; color: #cbd5e1; padding: 6px 12px; border-radius: 20px;
  font-size: 12px; font-weight: 700;
}
.pill.green { background: rgba(0,255,136,0.15); color: #00ff88; }
.pill.red { background: rgba(255,59,92,0.15); color: #ff6b81; }
.pill.blue { background: rgba(0,212,255,0.15); color: #00d4ff; }
.pill.purple { background: rgba(168,85,247,0.15); color: #c084fc; }
.levels { display: flex; gap: 10px; margin-top: 14px; }
.level {
  flex: 1; background: #0f1530; border-radius: 12px; padding: 12px; text-align: center;
}
.level .l-lbl { font-size: 11px; color: #8b9bb4; }
.level .l-val { font-size: 16px; font-weight: 900; color: white; margin-top: 2px; }
.level.entry .l-val { color: #00d4ff; }
.level.stop .l-val { color: #ff3b5c; }
.level.tp1 .l-val { color: #00ff88; }
.level.tp2 .l-val { color: #a855f7; }

/* ازرار */
.stButton > button {
  background: linear-gradient(135deg, #6a00ff, #00d4ff) !important;
  color: white !important; border: none !important; border-radius: 12px !important;
  font-weight: 900 !important; font-size: 16px !important; padding: 12px 24px !important;
  box-shadow: 0 4px 20px rgba(106,0,255,0.4) !important;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 25px rgba(106,0,255,0.6) !important; }

/* تابات */
.stTabs [data-baseweb="tab-list"] { gap: 8px; background: #141a2e; padding: 8px; border-radius: 14px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px; color: #8b9bb4; font-weight: 700; padding: 10px 18px; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #6a00ff, #00d4ff) !important; color: white !important; }

/* سايد بار */
section[data-testid="stSidebar"] { background: #0f1530 !important; }
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: white !important; }

/* جداول */
div[data-testid="stDataFrame"] { background: #141a2e; border-radius: 14px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ===== هيدر فخم =====
st.markdown("""
<div class="hero">
  <h1>💎 BLY7H ULTIMATE</h1>
  <p>🧠 ذكاء اصطناعي يتعلم &nbsp;|&nbsp; 🔮 تنبؤ قبل الحركة &nbsp;|&nbsp; ✅ تأكيد 5 منصات &nbsp;|&nbsp; 📊 باك تست حي</p>
  <span class="hero-badge">🔥 【entity-KUCOIN¦canonical_name=KUCOIN】 4x - 5x</span>
  <span class="hero-badge">📡 @WHYNOTBLY7</span>
  <span class="hero-badge">⚡ LIVE</span>
</div>
""", unsafe_allow_html=True)

# ===== سايد بار منسق =====
with st.sidebar:
    st.markdown("### ⚙️ لوحة التحكم")
    st.markdown("---")
    min_score = st.slider("🎯 اقل سكور للاشارة", 0, 100, 55)
    limit_coins = st.slider("🪙 عدد العملات للفحص", 20, 200, 80)
    focus = st.radio("🎯 ركز على", ["🔥 【entity-KUCOIN¦canonical_name=KUCOIN】 فقط", "🌐 【entity-KUCOIN¦canonical_name=KUCOIN】 + CEX + DEX"], index=0)
    ai_filter = st.radio("🧠 فلتر الذكاء", ["قياسي", "صارم", "إيقاف"], index=0)
    send_tg = st.checkbox("📡 ابعت تليجرام", value=True)
    filter_stable = st.checkbox("🛡️ فلتر المستقرة", value=True)
    st.markdown("---")
    st.markdown("**📊 حالة البوت**")
    st.markdown("🟢 متصل &nbsp;|&nbsp; 🧠 يتعلم &nbsp;|&nbsp; 📡 جاهز")

STABLES = ["USDCUSDT","BUSDUSDT","TUSDUSDT","USDPUSDT","DAIUSDT","FDUSDUSDT","USDeUSDT","USD1USDT","RLUSDUSDT","XUSDUSDT","EURUSDT","PYUSDUSDT","GUSDUSDT"]
MEMORY_FILE = "bly7h_memory.json"

def send_tg_alert(text):
    try:
        bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN")
        chat_id = st.secrets.get("TELEGRAM_CHANNEL_ID", st.secrets.get("TELEGRAM_CHAT_ID"))
        if not bot_token or not chat_id:
            return False
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        if r.status_code == 429:
            retry = r.json().get('parameters',{}).get('retry_after',30)
            time.sleep(retry+2)
            return send_tg_alert(text)
        return r.status_code == 200
    except:
        return False

def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"signals": [], "patterns": {"HighVol Pump": {"win": 0, "total": 0}, "FVG Breakout": {"win": 0, "total": 0}, "OI Accumulation": {"win": 0, "total": 0}}, "total_win": 0, "total": 0}

def get_learned_bonus(pattern, vol_spike):
    mem = load_memory()
    if pattern in mem["patterns"]:
        p = mem["patterns"][pattern]
        if p["total"] >= 5:
            win_rate = p["win"] / p["total"] * 100
            if win_rate >= 70:
                return 15, f"تعلم: {pattern} بينجح {win_rate:.0f}%"
            elif win_rate >= 55:
                return 10, f"تعلم: {pattern} بينجح {win_rate:.0f}%"
            elif win_rate < 35:
                return -10, f"تعلم: {pattern} بيفشل {100-win_rate:.0f}%"
    return 0, ""

PATTERNS = [
    {"name": "HighVol Pump", "vol": 3.0, "cvd": 15},
    {"name": "FVG Breakout", "vol": 2.0, "cvd": 8},
    {"name": "OI Accumulation", "vol": 2.5, "cvd": 10},
]

def calc_ai_similarity(vol_spike, cvd_score, change_1h):
    best = []
    for p in PATTERNS:
        vol_sim = max(0, 100 - abs(vol_spike - p["vol"]) * 20)
        cvd_sim = max(0, 100 - abs(cvd_score - p["cvd"]) * 3)
        sim = int((vol_sim + cvd_sim) / 2)
        if sim > 60:
            best.append((p["name"], sim))
    if not best:
        return 0, "نمط جديد", "نمط جديد"
    best_sorted = sorted(best, key=lambda x: x[1], reverse=True)
    name, sim = best_sorted[0]
    ai_bonus = int(sim * 0.2)
    learn_bonus, learn_msg = get_learned_bonus(name, vol_spike)
    ai_bonus += learn_bonus
    pattern_str = f"شبه {name} {sim}%"
    if learn_msg:
        pattern_str += f" | {learn_msg}"
    return ai_bonus, pattern_str, name

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
        green = 0; red = 0
        for i in range(-10, 0):
            c = float(df['close'].iloc[i]); o = float(df['open'].iloc[i]); v = float(df['vol'].iloc[i])
            if c > o: green += v
            else: red += v
        total = green + red
        if total == 0: return 0, "متوازن"
        pct = (green - red) / total * 100
        if pct > 30: return 15, f"CVD +{pct:.0f}% شراء قوي"
        elif pct < -30: return 15, f"CVD {pct:.0f}% بيع قوي"
        elif pct > 15: return 8, f"CVD +{pct:.0f}% شراء"
        elif pct < -15: return 8, f"CVD {pct:.0f}% بيع"
        else: return 0, f"CVD {pct:.0f}%"
    except:
        return 0, "CVD"

def calc_smc(df, price):
    try:
        bull_b = bull_m = bear_b = bear_m = bear_t = None
        for i in range(1, len(df)-1):
            try:
                low_next = float(df['low'].iloc[i+1]); high_prev = float(df['high'].iloc[i-1])
                high_next = float(df['high'].iloc[i+1]); low_prev = float(df['low'].iloc[i-1])
                if low_next > high_prev and bull_b is None:
                    bull_b = high_prev; bull_m = (high_prev + low_next)/2
                if high_next < low_prev and bear_b is None:
                    bear_b = high_next; bear_t = low_prev; bear_m = (high_next + low_prev)/2
            except: pass
        recent_low = float(df['low'].iloc[-10:].min())
        recent_high = float(df['high'].iloc[-10:].max())
        fvg_data = {'bull_b': bull_b, 'bull_m': bull_m, 'bear_b': bear_b, 'bear_m': bear_m, 'bear_t': bear_t}
        has_fvg = bull_b is not None or bear_b is not None
        return has_fvg, fvg_data, recent_low, recent_high
    except:
        return False, {}, price*0.99, price*1.01

def check_5_exchanges(sym_binance):
    try:
        base = sym_binance.replace('USDT','')
        count = 1; leaders = [" BINANCE"]
        try:
            r = requests.get(f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={base}-USDT", timeout=3)
            if r.status_code == 200: count += 1; leaders.append(" KUCOIN")
        except: pass
        try:
            r = requests.get(f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={base}_USDT", timeout=3)
            if r.status_code == 200: count += 1; leaders.append("GATE")
        except: pass
        try:
            r = requests.get(f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={base}USDT", timeout=3)
            if r.status_code == 200: count += 1; leaders.append("BITGET")
        except: pass
        try:
            r = requests.get(f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={base}USDT", timeout=3)
            if r.status_code == 200: count += 1; leaders.append("【entity-BYBIT¦canonical_name=BYBIT】")
        except: pass
        return count, leaders[0] if leaders else "【entity-BINANCE¦canonical_name=Binance】"
    except:
        return 1, "【entity-BINANCE¦canonical_name=Binance】"

def get_symbols_binance():
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200: continue
            data = r.json()
            usdt = [d for d in data if d.get('symbol','').endswith('USDT')]
            usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume') or 0), reverse=True)
            return [d['symbol'] for d in usdt_sorted[:400]]
        except: continue
    return []

@st.cache_data(ttl=300)
def get_all_symbols():
    s = get_symbols_binance()
    clean = []
    for x in s:
        if 'BULL' not in x and 'BEAR' not in x:
            if filter_stable and x in STABLES: continue
            clean.append(x)
    return clean[:400], " 【entity-binance¦canonical_name=Binance】"

def get_klines_binance(sym):
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={sym}&interval=1h&limit=100", timeout=10)
            if r.status_code != 200: continue
            data = r.json()
            if len(data) < 20: continue
            df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            for c in ['high','low','close','open']: df[c] = pd.to_numeric(df[c], errors='coerce')
            return df.dropna()
        except: continue
    return None

@st.cache_data(ttl=90)
def get_klines(sym):
    df = get_klines_binance(sym)
    if df is not None and len(df) >= 20: return df
    return None

def format_telegram_midas(sig, source="CEX"):
    now = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    direction = "UP" if "PUMP" in sig['type'] else "DOWN"
    emoji_dir = "💥"
    conf = sig.get('confidence', sig['score'])
    qual = "جيدة" if conf >= 60 else "متوسطة" if conf >= 40 else "منخفضة"
    phase = sig.get('phase', "بامب")
    rr = sig.get('rr', "1:0.5")
    leader = sig.get('leader', source)
    confirm = sig.get('confirm', "5 منصة")
    price = sig['price']
    msg = f"""💥 BLY7H AI SIGNAL 💥

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
        last = float(df['close'].iloc[-1]); prev = float(df['close'].iloc[-2])
        change_1h = (last - prev)/prev*100 if prev!=0 else 0
        if abs(change_1h) > 5: return None
        col = 'vol' if 'vol' in df.columns else 'volume'
        mean_vol = df[col].astype(float).iloc[-20:-1].mean()
        last_vol = float(df[col].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol>0 else 1
        if vol_spike < 2.0: return None
        oi_change = get_oi_change(sym) if source=="CEX" else 0
        cvd_score, cvd_reason = calc_cvd(df)
        if cvd_score < 8 and oi_change < 3: return None
        has_fvg, fvg_data, rec_low, rec_high = calc_smc(df, last)
        ai_bonus, ai_pattern, pattern_name = calc_ai_similarity(vol_spike, cvd_score, change_1h)
        base_score = 40 + (15 if oi_change>3 else 0) + cvd_score + min(vol_spike*3, 15)
        if has_fvg: base_score += 10
        base_score = min(int(base_score), 80)
        total_score = min(base_score + ai_bonus, 99)
        if ai_filter == "صارم" and total_score < 70: return None
        if ai_filter == "قياسي" and total_score < 60: return None
        if total_score < min_score: return None
        confirm_count, leader = check_5_exchanges(sym)
        if confirm_count >= 3: total_score = min(total_score + 5, 99)
        confidence = total_score
        if abs(change_1h) < 1 and vol_spike < 2.5: phase = "هادي"
        elif vol_spike > 2.5: phase = "بامب"
        else: phase = "متذبذب"
        bull_b = fvg_data.get('bull_b'); bull_m = fvg_data.get('bull_m')
        bear_m = fvg_data.get('bear_m'); bear_t = fvg_data.get('bear_t')
        if change_1h > -1:
            ptype = "PUMP"
            best = bull_m if bull_m is not None else last * 0.993
            no_ret = bull_b * 0.985 if bull_b else rec_low * 0.98
            best = min(best, last * 0.998); stop = no_ret * 0.99
            tp1 = last * 1.04; tp2 = last * 1.08
            if stop >= best: stop = best * 0.97
        else:
            ptype = "DUMP"
            best = bear_m if bear_m is not None else last * 1.007
            no_ret = bear_t * 1.015 if bear_t else rec_high * 1.02
            best = max(best, last * 1.002); stop = no_ret * 1.01
            tp1 = last * 0.96; tp2 = last * 0.92
            if stop <= best: stop = best * 1.03
        risk = abs(stop - last)/last*100 if last!=0 else 1
        reward = abs(tp1 - last)/last*100 if last!=0 else 1
        rr = reward / risk if risk>0 else 0
        return {'symbol': sym, 'score': total_score, 'base_score': base_score, 'ai_bonus': ai_bonus,
            'ai_pattern': ai_pattern, 'pattern_name': pattern_name, 'type': ptype, 'price': round(last,6),
            'change_1h': round(change_1h,2), 'vol_spike': round(vol_spike,2),
            'oi_change': round(oi_change,2), 'best_entry': round(best,6),
            'no_return_point': round(no_ret,6), 'stop_loss': round(stop,6),
            'TP1': round(tp1,6), 'TP2': round(tp2,6), 'vol_reason': f"Vol x{vol_spike:.1f}",
            'oi_reason': f"OI {oi_change:.1f}%", 'cvd_reason': cvd_reason,
            'confidence': confidence, 'phase': phase, 'rr': f"1:{rr:.1f}",
            'confirm': f"{confirm_count} منصة", 'leader': leader, 'has_fvg': has_fvg}
    except:
        return None

def get_kucoin_symbols():
    try:
        r = requests.get("https://api.kucoin.com/api/v1/market/allTickers", timeout=15)
        data = r.json().get('data', {}).get('ticker', [])
        usdt = []
        for d in data:
            sym = d.get('symbol','')
            if not sym.endswith('-USDT'): continue
            if 'USDC' in sym or 'DAI' in sym or 'BUSD' in sym: continue
            usdt.append(d)
        usdt_sorted = sorted(usdt, key=lambda x: float(x.get('volValue') or 0), reverse=True)
        return [d['symbol'] for d in usdt_sorted[:150]]
    except:
        return []

@st.cache_data(ttl=90)
def get_kucoin_klines(sym):
    try:
        end = int(time.time()); start = end - 100*3600
        url = f"https://api.kucoin.com/api/v1/market/candles?type=1hour&symbol={sym}&startAt={start}&endAt={end}"
        r = requests.get(url, timeout=10)
        data = r.json().get('data', [])
        if len(data) < 20: return None
        df = pd.DataFrame(data, columns=['time','open','close','high','low','vol','turnover'])
        for c in ['open','close','high','low','vol']: df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.sort_values('time')
        return df.dropna()
    except:
        return None

def pump_dump_kucoin(df, sym):
    try:
        last = float(df['close'].iloc[-1]); prev = float(df['close'].iloc[-2])
        change_1h = (last - prev)/prev*100 if prev!=0 else 0
        if len(df) >= 24:
            first24 = float(df['close'].iloc[-24])
            change_24 = (last - first24)/first24*100 if first24!=0 else 0
        else: change_24 = 0
        if change_24 > 50 or change_24 < -50: return None
        mean_vol = float(df['vol'].iloc[-20:-1].mean()); last_vol = float(df['vol'].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol>0 else 1
        if vol_spike < 2.5: return None
        if abs(change_1h) > 5: return None
        cvd_score, cvd_reason = calc_cvd(df)
        if cvd_score < 8: return None
        has_fvg, fvg_data, rec_low, rec_high = calc_smc(df, last)
        ai_bonus, ai_pattern, pattern_name = calc_ai_similarity(vol_spike, cvd_score, change_1h)
        base_score = 
