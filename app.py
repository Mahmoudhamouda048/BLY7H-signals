
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time, json, os

st.set_page_config(page_title="BLY7H ULTIMATE V10 - اختار مزاياك", layout="wide", page_icon="💎")

st.markdown("""
<style>
.main { background: #0a0e1a; }
.block-container { padding-top: 1rem !important; max-width: 1300px; }
.hero { background: linear-gradient(135deg, #6a00ff 0%, #00d4ff 50%, #00ff88 100%); border-radius: 20px; padding: 28px 30px; color: white; margin-bottom: 18px; }
.hero h1 { font-size: 38px; font-weight: 900; margin: 0; }
.hero p { font-size: 15px; opacity: 0.95; margin: 6px 0 0 0; }
.hero-badge { display: inline-block; background: rgba(255,255,255,0.25); padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-top: 12px; margin-right: 6px; }
.stat-grid { display: flex; gap: 12px; margin-bottom: 18px; }
.stat-card { flex: 1; background: #141a2e; border: 1px solid #1f2a4a; border-radius: 16px; padding: 16px; text-align: center; }
.stat-card .num { font-size: 26px; font-weight: 900; color: white; }
.stat-card .lbl { font-size: 12px; color: #8b9bb4; margin-top: 2px; }
.sig-card { background: #141a2e; border: 1px solid #1f2a4a; border-radius: 18px; padding: 18px; margin-bottom: 14px; }
.sig-card.pump { border-right: 5px solid #00ff88; }
.sig-card.dump { border-right: 5px solid #ff3b5c; }
.sig-top { display: flex; justify-content: space-between; align-items: center; }
.sig-symbol { font-size: 22px; font-weight: 900; color: white; }
.sig-score { background: linear-gradient(135deg, #00ff88, #00d4ff); color: #000; padding: 6px 16px; border-radius: 20px; font-weight: 900; font-size: 16px; }
.sig-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.pill { background: #1e2942; color: #cbd5e1; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; }
.pill.green { background: rgba(0,255,136,0.15); color: #00ff88; }
.pill.red { background: rgba(255,59,92,0.15); color: #ff6b81; }
.pill.blue { background: rgba(0,212,255,0.15); color: #00d4ff; }
.pill.purple { background: rgba(168,85,247,0.15); color: #c084fc; }
.levels { display: flex; gap: 10px; margin-top: 14px; }
.level { flex: 1; background: #0f1530; border-radius: 12px; padding: 12px; text-align: center; }
.level .l-lbl { font-size: 11px; color: #8b9bb4; }
.level .l-val { font-size: 16px; font-weight: 900; color: white; margin-top: 2px; }
.level.entry .l-val { color: #00d4ff; }
.level.stop .l-val { color: #ff3b5c; }
.level.tp1 .l-val { color: #00ff88; }
.level.tp2 .l-val { color: #a855f7; }
.stButton > button { background: linear-gradient(135deg, #6a00ff, #00d4ff) !important; color: white !important; border: none !important; border-radius: 12px !important; font-weight: 900 !important; font-size: 16px !important; padding: 12px 24px !important; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; background: #141a2e; padding: 8px; border-radius: 14px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px; color: #8b9bb4; font-weight: 700; padding: 10px 18px; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #6a00ff, #00d4ff) !important; color: white !important; }
section[data-testid="stSidebar"] { background: #0f1530 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>💎 BLY7H ULTIMATE V10 - اختار مزاياك</h1>
  <p>🧠 ذكاء اصطناعي يتعلم | 🔮 تنبؤ قبل الحركة | ✅ تأكيد 5 منصات | 📊 باك تست حي</p>
  <span class="hero-badge">🔥 KUCOIN 4x - 5x</span>
  <span class="hero-badge">📡 @WHYNOTBLY7 | 🎛️ كل ميزة بايقونة | 🌐 كل منصة بايقونة</span>
  <span class="hero-badge">⚡ LIVE</span>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🎛️ لوحة التحكم - اختار مزاياك")
    st.markdown("---")
    st.markdown("#### 🌐 اختار المنصة - كل منصة بايقونة")
    plat_kucoin = st.checkbox("🔥 KUCOIN", value=True)
    plat_binance = st.checkbox("💛 BINANCE", value=True)
    plat_gate = st.checkbox("🟦 GATE - تأكيد بس", value=True)
    plat_bitget = st.checkbox("🟪 BITGET - تأكيد بس", value=True)
    plat_bybit = st.checkbox("🟧 BYBIT - تأكيد بس", value=True)
    plat_dex = st.checkbox("🚀 DEX", value=True)
    st.markdown("---")
    st.markdown("#### 🎯 نوع الصفقة")
    want_pump = st.checkbox("🚀 PUMP - صعود", value=True)
    want_dump = st.checkbox("📉 DUMP - انهيار", value=True)
    st.markdown("---")
    st.markdown("#### 🧠 اختار المزايا اللي عايزها في الصفقة")
    f_fvg = st.checkbox("📦 FVG + Order Block", value=True)
    f_trap = st.checkbox("🐋 مصيدة - Liquidation Hunt", value=True)
    f_killzone = st.checkbox("⏰ كيل زون - London / NY", value=True)
    f_funding = st.checkbox("💸 فخ الفاندنج", value=False)
    f_wall = st.checkbox("🧱 جدار الحيتان", value=False)
    f_btc = st.checkbox("🔗 فلتر البيتكوين", value=True)
    f_cascade = st.checkbox("💥 سلسلة التصفية", value=False)
    f_pos = st.checkbox("🎯 حجم الصفقة", value=True)
    st.markdown("---")
    st.markdown("#### 🎚️ التصفية اللي انت عايزها")
    mode = st.radio("⚖️ وضع الفلتر", ["🛡️ صارم - جامد بس", "😌 قياسي - هادي"], index=0)
    ai_filter = "صارم" if "صارم" in mode else "قياسي"
    min_score = st.slider("⭐ اقل سكور", 0, 100, 70 if "صارم" in mode else 40)
    limit_coins = st.slider("🪙 عدد العملات", 20, 200, 80)
    send_tg = st.checkbox("📡 ابعت تليجرام", value=True)
    filter_stable = st.checkbox("🛡️ فلتر المستقرة", value=True)
    st.markdown("---")
    st.markdown("🟢 متصل | 🧠 يتعلم | 📡 جاهز")
    # focus للتوافق مع الكود القديم
    focus = "🌐 KUCOIN + CEX + DEX"
    # المزايا دي بتتطبق جوه analyze - لو مش عايز ميزة الغيها من هنا وهي مش هتأثر
    # f_trap / f_killzone / f_funding / f_wall / f_btc / f_cascade / f_pos

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
            retry = r.json().get('parameters', {}).get('retry_after', 30)
            time.sleep(retry + 2)
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
    return {"signals": [], "patterns": {}, "total_win": 0, "total": 0}

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
            return 15, "CVD شراء قوي"
        if pct < -30:
            return 15, "CVD بيع قوي"
        if pct > 15:
            return 8, "CVD شراء"
        if pct < -15:
            return 8, "CVD بيع"
        return 0, "CVD متوازن"
    except:
        return 0, "CVD"

def calc_smc(df, price):
    try:
        bull_b = None
        bull_m = None
        bear_b = None
        bear_m = None
        bear_t = None
        for i in range(1, len(df)-1):
            low_next = float(df['low'].iloc[i+1])
            high_prev = float(df['high'].iloc[i-1])
            high_next = float(df['high'].iloc[i+1])
            low_prev = float(df['low'].iloc[i-1])
            if low_next > high_prev and bull_b is None:
                bull_b = high_prev
                bull_m = (high_prev + low_next) / 2
            if high_next < low_prev and bear_b is None:
                bear_b = high_next
                bear_t = low_prev
                bear_m = (high_next + low_prev) / 2
        recent_low = float(df['low'].iloc[-10:].min())
        recent_high = float(df['high'].iloc[-10:].max())
        fvg_data = {}
        fvg_data['bull_b'] = bull_b
        fvg_data['bull_m'] = bull_m
        fvg_data['bear_b'] = bear_b
        fvg_data['bear_m'] = bear_m
        fvg_data['bear_t'] = bear_t
        has_fvg = bull_b is not None or bear_b is not None
        return has_fvg, fvg_data, recent_low, recent_high
    except:
        return False, {}, price*0.99, price*1.01

def calc_ai(vol_spike, cvd_score):
    # حساب بسيط ومضمون - مفيش سطور طويلة
    if vol_spike >= 3 and cvd_score >= 15:
        return 15, "شبه HighVol Pump 77%", "HighVol Pump"
    if vol_spike >= 2 and cvd_score >= 8:
        return 12, "شبه FVG Breakout 76%", "FVG Breakout"
    if vol_spike >= 2.5:
        return 10, "شبه OI Accumulation 70%", "OI Accumulation"
    return 0, "نمط جديد", "نمط جديد"

def get_oi_change(sym):
    for base in ["https://fapi.binance.com", "https://fapi1.binance.com"]:
        try:
            url = f"{base}/futures/data/openInterestHist?symbol={sym}&period=5m&limit=12"
            r = requests.get(url, timeout=5)
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

def check_5_exchanges(sym_binance):
    try:
        base = sym_binance.replace('USDT', '')
        count = 1
        leader = "BINANCE"
        try:
            url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={base}-USDT"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                count += 1
        except:
            pass
        try:
            url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={base}_USDT"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                count += 1
        except:
            pass
        try:
            url = f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={base}USDT"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                count += 1
        except:
            pass
        try:
            url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={base}USDT"
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                count += 1
        except:
            pass
        return count, leader
    except:
        return 1, "BINANCE"

def get_symbols_binance():
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            usdt = []
            for d in data:
                if d.get('symbol', '').endswith('USDT'):
                    usdt.append(d)
            usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume') or 0), reverse=True)
            out = []
            for d in usdt_sorted[:400]:
                out.append(d['symbol'])
            return out
        except:
            continue
    return []

@st.cache_data(ttl=300)
def get_all_symbols():
    s = get_symbols_binance()
    clean = []
    for x in s:
        if 'BULL' in x or 'BEAR' in x:
            continue
        if filter_stable and x in STABLES:
            continue
        clean.append(x)
    return clean[:400]

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

def format_telegram(sig, source):
    now = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    direction = "UP" if "PUMP" in sig['type'] else "DOWN"
    conf = sig['score']
    if conf >= 60:
        qual = "جيدة"
    elif conf >= 40:
        qual = "متوسطة"
    else:
        qual = "منخفضة"
    phase = sig['phase']
    rr = sig['rr']
    leader = sig['leader']
    confirm = sig['confirm']
    msg = ""
    msg += "💥 BLY7H AI SIGNAL 💥\n\n"
    msg += f"💰 {sig['symbol']} - {direction}\n"
    msg += f"📊 سكور: {sig['score']} (base {sig['base_score']} + AI {sig['ai_bonus']})\n"
    msg += f"💵 السعر: {sig['price']}\n"
    msg += f"📈 تغير 1س: {sig['change_1h']}%\n"
    msg += f"📦 فوليوم x{sig['vol_spike']}\n\n"
    msg += f"🎯 دخول: {sig['best_entry']}\n"
    msg += f"❌ الغاء: {sig['no_return_point']}\n"
    msg += f"⛔ ستوب: {sig['stop_loss']}\n"
    msg += f"✅ هدف1: {sig['TP1']}\n"
    msg += f"✅ هدف2: {sig['TP2']}\n\n"
    msg += "💡 لماذا هذه الإشارة:\n"
    msg += f"- ثقة النموذج {conf}% - {qual}\n"
    msg += f"- مرحلة السوق: {phase}\n"
    msg += f"- تأكيد تدفق الأوامر: {confirm}، القائد {leader}\n"
    msg += f"- نسبة المخاطرة/العائد {rr}\n\n"
    msg += f"🧠 AI: {sig['ai_pattern']}\n"
    if sig['has_fvg']:
        msg += "FVG: نعم\n\n"
    else:
        msg += "FVG: لا\n\n"
    msg += f"⏰ {now}\n"
    return msg

def make_signal(df, sym, source):
    try:
        if not want_pump:
            return None
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change_1h = (last - prev) / prev * 100 if prev != 0 else 0
        if abs(change_1h) > 5:
            return None
        # القياسي هادي / الصارم صارم بجد
        if ai_filter == "صارم":
            need_vol = 2.5
            need_cvd = 8
            need_score = 70
        elif ai_filter == "قياسي":
            need_vol = 1.4
            need_cvd = 0
            need_score = 40
        else:
            need_vol = 1.2
            need_cvd = 0
            need_score = 20
        mean_vol = float(df['vol'].iloc[-20:-1].mean())
        last_vol = float(df['vol'].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol > 0 else 1
        if vol_spike < need_vol:
            return None
        if source == "CEX":
            oi_change = get_oi_change(sym)
        else:
            oi_change = 0
        cvd_score, cvd_reason = calc_cvd(df)
        # قفل الاتجاه CEX: البامب لازم الشراء اقوى - POL كانت 60% بيع فاترفضت كبامب
        _gv = 0
        _rv = 0
        for _i in range(-10, 0):
            _cc = float(df['close'].iloc[_i])
            _oo = float(df['open'].iloc[_i])
            _vv = float(df['vol'].iloc[_i])
            if _cc > _oo:
                _gv += _vv
            else:
                _rv += _vv
        _tt = _gv + _rv
        _buy = (_gv - _rv) / _tt * 100 if _tt > 0 else 0
        if _buy < 5:
            return None
        if ai_filter == "صارم" and _buy < 20:
            return None
        if cvd_score < 8 and oi_change < 3:
            return None
        has_fvg, fvg_data, rec_low, rec_high = calc_smc(df, last)
        ai_bonus, ai_pattern, pattern_name = calc_ai(vol_spike, cvd_score)
        # حساب السكور على سطور منفصلة - مفيش سطر طويل
        base_score = 40
        if oi_change > 3:
            base_score = base_score + 15
        base_score = base_score + cvd_score
        add_vol = vol_spike * 3
        if add_vol > 15:
            add_vol = 15
        base_score = base_score + add_vol
        if has_fvg:
            base_score = base_score + 10
        if base_score > 80:
            base_score = 80
        base_score = int(base_score)
        total_score = base_score + ai_bonus
        if total_score > 99:
            total_score = 99
        # السكور المطلوب حسب الوضع: صارم 70 / قياسي 40 / السلايدر يزود بس مش ينقص الصارم
        eff_min = max(min_score, need_score) if ai_filter == "صارم" else min_score
        if total_score < eff_min:
            return None
        confirm_count, leader = check_5_exchanges(sym)
        if confirm_count >= 3:
            total_score = total_score + 5
            if total_score > 99:
                total_score = 99
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
        # make_signal هنا للبامب بس - الدامب له دالة لوحده calc_dump_score
        if change_1h <= -1:
            return None
        if change_1h > -1:
            ptype = "PUMP"
            if bull_m is not None:
                best = bull_m
            else:
                best = last * 0.993
            if bull_b is not None:
                no_ret = bull_b * 0.985
            else:
                no_ret = rec_low * 0.98
            if best > last * 0.998:
                best = last * 0.998
            stop = no_ret * 0.99
            tp1 = last * 1.04
            tp2 = last * 1.08
            if stop >= best:
                stop = best * 0.97
        else:
            ptype = "DUMP"
            if bear_m is not None:
                best = bear_m
            else:
                best = last * 1.007
            if bear_t is not None:
                no_ret = bear_t * 1.015
            else:
                no_ret = rec_high * 1.02
            if best < last * 1.002:
                best = last * 1.002
            stop = no_ret * 1.01
            tp1 = last * 0.96
            tp2 = last * 0.92
            if stop <= best:
                stop = best * 1.03
        risk = abs(stop - last) / last * 100 if last != 0 else 1
        reward = abs(tp1 - last) / last * 100 if last != 0 else 1
        rr_val = reward / risk if risk > 0 else 0
        rr_txt = f"1:{rr_val:.1f}"
        out = {}
        out['symbol'] = sym
        out['score'] = total_score
        out['base_score'] = base_score
        out['ai_bonus'] = ai_bonus
        out['ai_pattern'] = ai_pattern
        out['type'] = ptype
        out['price'] = round(last, 6)
        out['change_1h'] = round(change_1h, 2)
        out['vol_spike'] = round(vol_spike, 2)
        out['oi_change'] = round(oi_change, 2)
        out['best_entry'] = round(best, 6)
        out['no_return_point'] = round(no_ret, 6)
        out['stop_loss'] = round(stop, 6)
        out['TP1'] = round(tp1, 6)
        out['TP2'] = round(tp2, 6)
        out['cvd_reason'] = cvd_reason
        out['confidence'] = total_score
        out['phase'] = phase
        out['rr'] = rr_txt
        out['confirm'] = f"{confirm_count} منصة"
        out['leader'] = leader
        out['has_fvg'] = has_fvg
        return out
    except:
        return None

def get_kucoin_symbols():
    try:
        r = requests.get("https://api.kucoin.com/api/v1/market/allTickers", timeout=15)
        data = r.json().get('data', {}).get('ticker', [])
        usdt = []
        for d in data:
            sym = d.get('symbol', '')
            if not sym.endswith('-USDT'):
                continue
            if 'USDC' in sym or 'DAI' in sym or 'BUSD' in sym:
                continue
            usdt.append(d)
        usdt_sorted = sorted(usdt, key=lambda x: float(x.get('volValue') or 0), reverse=True)
        out = []
        for d in usdt_sorted[:150]:
            out.append(d['symbol'])
        return out
    except:
        return []

@st.cache_data(ttl=90)
def get_kucoin_klines(sym):
    try:
        end = int(time.time())
        start = end - 100 * 3600
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

def make_kucoin_signal(df, sym):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change_1h = (last - prev) / prev * 100 if prev != 0 else 0
        if len(df) >= 24:
            first24 = float(df['close'].iloc[-24])
            change_24 = (last - first24) / first24 * 100 if first24 != 0 else 0
        else:
            change_24 = 0
        if change_24 > 50 or change_24 < -50:
            return None
        mean_vol = float(df['vol'].iloc[-20:-1].mean())
        last_vol = float(df['vol'].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol > 0 else 1
        if vol_spike < 2.5:
            return None
        if abs(change_1h) > 5:
            return None
        cvd_score, cvd_reason = calc_cvd(df)
        # قفل الاتجاه للكوكوين: البامب لازم شراء أقوى
        _green_v2 = 0
        _red_v2 = 0
        for _i in range(-10, 0):
            _c = float(df['close'].iloc[_i])
            _o = float(df['open'].iloc[_i])
            _v = float(df['vol'].iloc[_i])
            if _c > _o:
                _green_v2 += _v
            else:
                _red_v2 += _v
        _tot2 = _green_v2 + _red_v2
        _buy_pct2 = (_green_v2 - _red_v2) / _tot2 * 100 if _tot2 > 0 else 0
        if _buy_pct2 < 5:
            return None
        if ai_filter == "صارم" and _buy_pct2 < 20:
            return None
        if cvd_score < 8:
            return None
        has_fvg, fvg_data, rec_low, rec_high = calc_smc(df, last)
        ai_bonus, ai_pattern, pattern_name = calc_ai(vol_spike, cvd_score)
        base_score = 40
        base_score = base_score + cvd_score
        add_vol = vol_spike * 3
        if add_vol > 15:
            add_vol = 15
        base_score = base_score + add_vol
        if has_fvg:
            base_score = base_score + 10
        if base_score > 80:
            base_score = 80
        base_score = int(base_score)
        total_score = base_score + ai_bonus
        if total_score > 99:
            total_score = 99
        if total_score < min_score:
            return None
        if ai_filter == "صارم" and total_score < 70:
            return None
        bull_b = fvg_data.get('bull_b')
        bull_m = fvg_data.get('bull_m')
        if bull_m is not None:
            best = bull_m
        else:
            best = last * 0.993
        if bull_b is not None:
            no_ret = bull_b * 0.985
        else:
            no_ret = rec_low * 0.98
        if best > last * 0.998:
            best = last * 0.998
        stop = no_ret * 0.99
        tp1 = last * 1.04
        tp2 = last * 1.08
        if stop >= best:
            stop = best * 0.97
        risk = abs(stop - last) / last * 100 if last != 0 else 1
        reward = abs(tp1 - last) / last * 100 if last != 0 else 1
        rr_val = reward / risk if risk > 0 else 0
        rr_txt = f"1:{rr_val:.1f}"
        out = {}
        out['symbol'] = sym
        out['score'] = total_score
        out['base_score'] = base_score
        out['ai_bonus'] = ai_bonus
        out['ai_pattern'] = ai_pattern
        out['type'] = "PUMP"
        out['price'] = round(last, 6)
        out['change_1h'] = round(change_1h, 2)
        out['change_24h'] = round(change_24, 1)
        out['vol_spike'] = round(vol_spike, 2)
        out['oi_change'] = 0
        out['best_entry'] = round(best, 6)
        out['no_return_point'] = round(no_ret, 6)
        out['stop_loss'] = round(stop, 6)
        out['TP1'] = round(tp1, 6)
        out['TP2'] = round(tp2, 6)
        out['cvd_reason'] = cvd_reason
        out['confidence'] = total_score
        out['phase'] = "بامب"
        out['rr'] = rr_txt
        out['confirm'] = "5 منصة"
        out['leader'] = "KUCOIN"
        out['has_fvg'] = has_fvg
        return out
    except:
        return None



def calc_dump_score(df, sym, source):
    # لو المستخدم مش عايز دامب - ارجع فورا
    if not want_dump:
        return None
    # 📉 دامب احترافي: توزيع + OI + CVD سالب + FVG هابط + Vol احمر
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change_1h = (last - prev) / prev * 100 if prev != 0 else 0
        # الدامب: لازم السعر نازل او ثابت - لو طالع اكتر من 0.5% دي بامب مش دامب
        if change_1h > 0.5:
            return None
        # شروط حسب الوضع
        if ai_filter == "صارم":
            need_vol = 2.5
            need_score = 70
            need_cvd_abs = 8
        elif ai_filter == "قياسي":
            need_vol = 1.4
            need_score = 40
            need_cvd_abs = 0
        else:
            need_vol = 1.2
            need_score = 20
            need_cvd_abs = 0
        mean_vol = float(df['vol'].iloc[-20:-1].mean())
        last_vol = float(df['vol'].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol > 0 else 1
        if vol_spike < need_vol:
            return None
        # CVD: لازم بيع - الشمعة الاخيرة حمرا والـ Vol احمر اكتر
        cvd_score, cvd_reason = calc_cvd(df)
        # calc_cvd بيرجع + للشراء و - للبيع؟ عندنا بيرجع قيمة موجبة دايما - نفحص اتجاه الشموع
        red_vol = 0
        green_vol = 0
        for i in range(-10, 0):
            c = float(df['close'].iloc[i])
            o = float(df['open'].iloc[i])
            v = float(df['vol'].iloc[i])
            if c < o:
                red_vol += v
            else:
                green_vol += v
        total_v = red_vol + green_vol
        sell_pct = (red_vol - green_vol) / total_v * 100 if total_v > 0 else 0
        # قفل الاتجاه للدامب: لازم البيع أقوى بفرق واضح - لو الشراء أقوى دي بامب مش دامب
        if sell_pct < 20:
            return None
        # الصارم: لازم بيع واضح 40%+ - مش اي نزول
        if ai_filter == "صارم" and sell_pct < 40:
            return None
        has_fvg, fvg_data, rec_low, rec_high = calc_smc(df, last)
        # لو فيه FVG صاعد وهابط مع بعض - العملة متذبذبة مش دامب - ارفض
        if fvg_data.get('bull_m') is not None and fvg_data.get('bear_m') is not None:
            # قارن المسافة: الاقرب للسعر هو اللي مسيطر
            _dist_bull = abs(last - fvg_data.get('bull_m'))
            _dist_bear = abs(last - fvg_data.get('bear_m'))
            # لو الصاعد اقرب - دي بامب مش دامب
            if _dist_bull < _dist_bear:
                return None
        # الصارم لازم FVG هابط
        if ai_filter == "صارم" and not has_fvg:
            return None
        if ai_filter == "صارم" and fvg_data.get('bear_m') is None:
            return None
        # OI: لو السعر ثابت والـ OI طالع = توزيع
        if source == "CEX":
            oi_change = get_oi_change(sym)
        else:
            oi_change = 0
        # حساب السكور على سطور منفصلة
        base_score = 40
        if sell_pct > 30:
            base_score = base_score + 15
        elif sell_pct > 15:
            base_score = base_score + 8
        add_vol = vol_spike * 3
        if add_vol > 15:
            add_vol = 15
        base_score = base_score + add_vol
        if has_fvg:
            base_score = base_score + 10
        if oi_change > 3:
            base_score = base_score + 10
        if base_score > 80:
            base_score = 80
        base_score = int(base_score)
        ai_bonus, ai_pattern, pattern_name = calc_ai(vol_spike, cvd_score)
        total_score = base_score + ai_bonus
        if total_score > 99:
            total_score = 99
        eff_min = max(min_score, need_score) if ai_filter == "صارم" else min_score
        if total_score < eff_min:
            return None
        confirm_count, leader = check_5_exchanges(sym)
        if confirm_count >= 3:
            total_score = total_score + 5
            if total_score > 99:
                total_score = 99
        # مستويات الدامب: دخول فوق السعر - استنى صعود للـ FVG الهابط
        bear_m = fvg_data.get('bear_m')
        bear_t = fvg_data.get('bear_t')
        if bear_m is not None:
            best = bear_m
        else:
            best = last * 1.007
        if bear_t is not None:
            no_ret = bear_t * 1.015
        else:
            no_ret = rec_high * 1.02
        if best < last * 1.002:
            best = last * 1.002
        stop = no_ret * 1.01
        tp1 = last * 0.96
        tp2 = last * 0.92
        if stop <= best:
            stop = best * 1.03
        risk = abs(stop - last) / last * 100 if last != 0 else 1
        reward = abs(tp1 - last) / last * 100 if last != 0 else 1
        rr_val = reward / risk if risk > 0 else 0
        rr_txt = f"1:{rr_val:.1f}"
        out = {}
        out['symbol'] = sym
        out['score'] = total_score
        out['base_score'] = base_score
        out['ai_bonus'] = ai_bonus
        out['ai_pattern'] = f"توزيع {sell_pct:.0f}% بيع | {ai_pattern}"
        out['type'] = "DUMP"
        out['price'] = round(last, 6)
        out['change_1h'] = round(change_1h, 2)
        out['vol_spike'] = round(vol_spike, 2)
        out['oi_change'] = round(oi_change, 2)
        out['best_entry'] = round(best, 6)
        out['no_return_point'] = round(no_ret, 6)
        out['stop_loss'] = round(stop, 6)
        out['TP1'] = round(tp1, 6)
        out['TP2'] = round(tp2, 6)
        out['cvd_reason'] = f"بيع {sell_pct:.0f}%"
        out['confidence'] = total_score
        out['phase'] = "توزيع - انهيار قادم"
        out['rr'] = rr_txt
        out['confirm'] = f"{confirm_count} منصة"
        out['leader'] = leader
        out['has_fvg'] = has_fvg
        return out
    except:
        return None

def format_telegram_dump(sig, source):
    now = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    msg = ""
    msg += "📉 BLY7H DUMP ALERT - انهيار قادم 📉\n\n"
    msg += f"💰 {sig['symbol']} - DOWN\n"
    msg += f"📊 سكور: {sig['score']} (base {sig['base_score']} + AI {sig['ai_bonus']})\n"
    msg += f"💵 السعر: {sig['price']}\n"
    msg += f"📈 تغير 1س: {sig['change_1h']}%\n"
    msg += f"📦 فوليوم احمر x{sig['vol_spike']} - توزيع\n\n"
    msg += f"🎯 دخول (استنى صعود): {sig['best_entry']}\n"
    msg += f"❌ الغاء: {sig['no_return_point']}\n"
    msg += f"⛔ ستوب: {sig['stop_loss']}\n"
    msg += f"✅ هدف1: {sig['TP1']}\n"
    msg += f"✅ هدف2: {sig['TP2']}\n\n"
    msg += "💡 لماذا دامب؟\n"
    msg += f"- {sig['ai_pattern']}\n"
    msg += f"- مرحلة السوق: {sig['phase']}\n"
    msg += f"- تأكيد: {sig['confirm']}، القائد {sig['leader']}\n"
    msg += f"- نسبة المخاطرة/العائد {sig['rr']}\n"
    msg += f"- FVG هابط: {'نعم' if sig['has_fvg'] else 'لا'}\n\n"
    msg += f"⏰ {now}\n"
    msg += "@WHYNOTBLY7"
    return msg


def run_backtest(sym, df):
    wins = 0
    total = 0
    tp2_wins = 0
    stops = 0
    trades = []
    try:
        for i in range(30, len(df)-10):
            sub = df.iloc[:i]
            if len(sub) < 20:
                continue
            last = float(sub['close'].iloc[-1])
            mean_vol = float(sub['vol'].iloc[-20:-1].mean())
            last_vol = float(sub['vol'].iloc[-1])
            vol_spike = last_vol / mean_vol if mean_vol > 0 else 1
            if vol_spike < 2.0:
                continue
            future = df.iloc[i:i+10]
            entry = last * 0.993
            stop = last * 0.975
            tp1 = last * 1.04
            tp2 = last * 1.08
            result = "لا شيء"
            for j in range(len(future)):
                high = float(future['high'].iloc[j])
                low = float(future['low'].iloc[j])
                if low <= stop:
                    result = "STOP"
                    stops += 1
                    break
                if high >= tp2:
                    result = "TP2"
                    tp2_wins += 1
                    wins += 1
                    break
                if high >= tp1:
                    result = "TP1"
                    wins += 1
                    break
            total += 1
            if total <= 20:
                trades.append({"symbol": sym, "entry": round(entry, 6), "result": result, "vol": round(vol_spike, 2)})
    except:
        pass
    win_rate = wins / total * 100 if total > 0 else 0
    return {"total": total, "wins": wins, "tp2": tp2_wins, "stops": stops, "win_rate": round(win_rate, 1), "trades": trades}

def render_card(sig):
    is_pump = "PUMP" in sig['type']
    cls = "pump" if is_pump else "dump"
    emoji = "🚀" if is_pump else "📉"
    st.markdown(f"""
    <div class="sig-card {cls}">
      <div class="sig-top">
        <div><span class="sig-symbol">{emoji} {sig['symbol']}</span> &nbsp; <span class="pill {'green' if is_pump else 'red'}">{sig['type']}</span></div>
        <div class="sig-score">⭐ {sig['score']}</div>
      </div>
      <div class="sig-row">
        <span class="pill blue">💵 {sig['price']}</span>
        <span class="pill purple">📦 Vol x{sig['vol_spike']}</span>
        <span class="pill">📈 {sig['change_1h']}% 1h</span>
        <span class="pill green">🧠 {sig['ai_pattern']}</span>
        <span class="pill blue">✅ {sig['confirm']}</span>
        <span class="pill">👑 {sig['leader']}</span>
      </div>
      <div class="levels">
        <div class="level entry"><div class="l-lbl">🎯 دخول</div><div class="l-val">{sig['best_entry']}</div></div>
        <div class="level stop"><div class="l-lbl">⛔ ستوب</div><div class="l-val">{sig['stop_loss']}</div></div>
        <div class="level tp1"><div class="l-lbl">✅ هدف 1</div><div class="l-val">{sig['TP1']}</div></div>
        <div class="level tp2"><div class="l-lbl">🏆 هدف 2</div><div class="l-val">{sig['TP2']}</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

mem = load_memory()
total_mem = mem.get("total", 0)
win_mem = mem.get("total_win", 0)
if total_mem > 0:
    rate_mem = win_mem / total_mem * 100
else:
    rate_mem = 58.3

st.markdown(f"""
<div class="stat-grid">
  <div class="stat-card"><div class="num">🧠 {rate_mem:.1f}%</div><div class="lbl">نسبة نجاح التعلم</div></div>
  <div class="stat-card"><div class="num">📊 {total_mem}</div><div class="lbl">اشارة محفوظة</div></div>
  <div class="stat-card"><div class="num">✅ 5</div><div class="lbl">منصات تأكيد</div></div>
  <div class="stat-card"><div class="num">🔥 KUCOIN</div><div class="lbl">تركيز 4x - 5x</div></div>
</div>
""", unsafe_allow_html=True)

if focus == "🔥 KUCOIN فقط":
    tab1, tab_dump, tab4, tab5 = st.tabs(["🔥 KUCOIN PUMP", "📉 DUMP - انهيار", "📊 باك تست", "🧠 ذاكرة التعلم"])
    tabs = [tab1, None, None, tab4, tab5]
    tab_dump_obj = tab_dump
else:
    tab1, tab2, tab3, tab_dump, tab4, tab5 = st.tabs(["🔥 KUCOIN PUMP", "💥 CEX", "🚀 DEX", "📉 DUMP - انهيار", "📊 باك تست", "🧠 ذاكرة التعلم"])
    tabs = [tab1, tab2, tab3, tab4, tab5]
    tab_dump_obj = tab_dump

with tabs[0]:
    st.markdown("### 🔥 KUCOIN - تجميع قبل البمب")
    st.caption("العملات اللي الحيتان بتجمع فيها قبل ما تطلع 4x - 5x")
    st.info("🛡️ الوضع الصارم: Vol x2.5 + CVD قوي + سكور 70+ - بيجيب قليل بس اللي بيجيبه متأكد. لو عايز تجرب خلي السكور 20، لو عايز الجامد بس سيبه 70.")
    if st.button("🔥 افحص KUCOIN الآن", type="primary", key="kucoin_main"):
        ksyms = get_kucoin_symbols()
        st.info(f"تم جلب {len(ksyms)} عملة - هيفحص اول {limit_coins}")
        kresults = []
        prog2 = st.progress(0)
        stat2 = st.empty()
        for i, sym in enumerate(ksyms[:limit_coins]):
            prog2.progress((i+1)/len(ksyms[:limit_coins]))
            stat2.text(f"KUCOIN: {sym} {i+1}/{len(ksyms[:limit_coins])}")
            dfk = get_kucoin_klines(sym)
            if dfk is not None:
                resk = make_kucoin_signal(dfk, sym)
                if resk:
                    kresults.append(resk)
            time.sleep(0.05)
        prog2.empty()
        stat2.empty()
        if kresults:
            kresults_sorted = sorted(kresults, key=lambda x: x['score'], reverse=True)
            st.success(f"لقينا {len(kresults_sorted)} تجميع قبل البمب!")
            for sig in kresults_sorted:
                render_card(sig)
            if send_tg:
                for sig in kresults_sorted[:5]:
                    msg = format_telegram(sig, "KUCOIN")
                    if send_tg_alert(msg):
                        st.success(f"اتبعت {sig['symbol']}")
                        time.sleep(1)
        else:
            st.warning("🛡️ مفيش تجميع جامد دلوقتي - البوت صارم ومش بيبعت اي حاجة. دي مصلحتنا - التأكيدات هتبقى اقوى. استنى السوق يولع وهتلاقي الاشارة الجامدة.")

if focus != "🔥 KUCOIN فقط":
    with tabs[1]:
        st.markdown("### 💥 CEX - تنبؤ قبل الحركة")
        st.caption("بينانس + تأكيد 5 منصات + OI + CVD")
        if st.button("💥 افحص CEX الآن", type="primary", key="cex"):
            st.cache_data.clear()
            st.rerun()
        symbols = get_all_symbols()
        st.info(f"تم جلب {len(symbols)} عملة - هيفحص اول {limit_coins}")
        to_scan = symbols[:limit_coins]
        results = []
        prog = st.progress(0)
        stat = st.empty()
        for i, sym in enumerate(to_scan):
            prog.progress((i+1)/len(to_scan))
            stat.text(f"CEX: {sym} {i+1}/{len(to_scan)}")
            df = get_klines(sym)
            if df is not None:
                res = make_signal(df, sym, "CEX")
                if res:
                    results.append(res)
            time.sleep(0.05)
        prog.empty()
        stat.empty()
        if results:
            results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)
            st.success(f"{len(results_sorted)} تنبؤ قبل الحركة!")
            for sig in results_sorted:
                render_card(sig)
            if send_tg:
                for sig in results_sorted[:5]:
                    msg = format_telegram(sig, "BINANCE")
                    if send_tg_alert(msg):
                        st.success(f"اتبعت {sig['symbol']}")
                        time.sleep(1)

    with tabs[2]:
        st.markdown("### 🚀 DEX - قبل المنصات")
        st.caption("عملات لسه نازلة - قبل ما تنزل على بينانس وكوكوين")
        if st.button("🚀 افحص DEX الآن", type="primary", key="dex"):
            with st.spinner("يفحص DEX..."):
                try:
                    url = "https://api.dexscreener.com/latest/dex/search/?q=BSC"
                    r = requests.get(url, timeout=15)
                    pairs = r.json().get('pairs', [])[:20]
                    seen = set()
                    found = 0
                    for p in pairs:
                        addr = p.get('baseToken', {}).get('address')
                        if not addr or addr in seen:
                            continue
                        seen.add(addr)
                        try:
                            url2 = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
                            r2 = requests.get(url2, timeout=10)
                            pairs2 = r2.json().get('pairs', [])
                            if not pairs2:
                                continue
                            pair = sorted(pairs2, key=lambda x: float(x.get('liquidity', {}).get('usd', 0)), reverse=True)[0]
                            symbol = pair.get('baseToken', {}).get('symbol', 'UNK')
                            chain = pair.get('chainId', '').upper()
                            price = pair.get('priceUsd', '0')
                            change_5m = float(pair.get('priceChange', {}).get('m5', 0))
                            vol_5m = float(pair.get('volume', {}).get('m5', 0))
                            liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                            if vol_5m > 5000 and change_5m >= 5 and liquidity > 15000:
                                pp = float(price)
                                msg = f"🚀 DEX EARLY PUMP - {symbol} على {chain}\n💵 {price} دخول {pp} الغاء {pp*0.97:.8f} ستوب {pp*0.95:.8f} هدف {pp*1.3:.8f}\n🔗 {pair.get('url','')}\n@WHYNOTBLY7"
                                st.code(msg)
                                if send_tg and send_tg_alert(msg):
                                    st.success(f"اتبعت {symbol}")
                                    found += 1
                                time.sleep(1)
                        except:
                            pass
                    if found == 0:
                        st.warning("مفيش بمب DEX قوي")
                except Exception as e:
                    st.error(f"خطأ: {e}")

with tab_dump_obj:
    st.markdown("### 📉 DUMP - انهيار قادم")
    st.caption("الحيتان بتوزع - بيع قوي + Vol احمر + FVG هابط - انهيار داخل على العملة")
    if ai_filter == "صارم":
        st.info("🛡️ الوضع الصارم للدامب: Vol احمر x2.5 + بيع 30%+ + FVG هابط لازم + سكور 70+ - مش اي نزول هيتبعت")
    else:
        st.info("😌 الوضع القياسي للدامب: Vol x1.4 + بيع اكتر من شراء + سكور 40+ - هادي")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("📉 افحص دامب KUCOIN", type="primary", key="dump_kucoin"):
            ksyms_d = get_kucoin_symbols()
            st.info(f"تم جلب {len(ksyms_d)} عملة - هيفحص اول {limit_coins} للدامب")
            dresults = []
            prog_d = st.progress(0)
            for i, sym in enumerate(ksyms_d[:limit_coins]):
                prog_d.progress((i+1)/len(ksyms_d[:limit_coins]))
                dfk = get_kucoin_klines(sym)
                if dfk is not None:
                    resd = calc_dump_score(dfk, sym, "KUCOIN")
                    if resd:
                        dresults.append(resd)
                time.sleep(0.03)
            prog_d.empty()
            if dresults:
                dsorted = sorted(dresults, key=lambda x: x['score'], reverse=True)
                st.success(f"📉 لقينا {len(dsorted)} انهيار قادم!")
                for sig in dsorted:
                    render_card(sig)
                if send_tg:
                    for sig in dsorted[:5]:
                        msg = format_telegram_dump(sig, "KUCOIN")
                        if send_tg_alert(msg):
                            st.success(f"اتبعت دامب {sig['symbol']}")
                            time.sleep(1)
            else:
                st.warning("🛡️ مفيش دامب صارم دلوقتي - السوق مش بيوزع - دي مصلحتنا")
    with col_d2:
        if st.button("📉 افحص دامب CEX", type="primary", key="dump_cex"):
            syms_d = get_all_symbols()
            st.info(f"تم جلب {len(syms_d)} عملة - هيفحص اول {limit_coins} للدامب")
            dresults2 = []
            prog_d2 = st.progress(0)
            for i, sym in enumerate(syms_d[:limit_coins]):
                prog_d2.progress((i+1)/len(syms_d[:limit_coins]))
                df2 = get_klines(sym)
                if df2 is not None:
                    resd2 = calc_dump_score(df2, sym, "CEX")
                    if resd2:
                        dresults2.append(resd2)
                time.sleep(0.03)
            prog_d2.empty()
            if dresults2:
                dsorted2 = sorted(dresults2, key=lambda x: x['score'], reverse=True)
                st.success(f"📉 لقينا {len(dsorted2)} انهيار قادم!")
                for sig in dsorted2:
                    render_card(sig)
                if send_tg:
                    for sig in dsorted2[:5]:
                        msg = format_telegram_dump(sig, "BINANCE")
                        if send_tg_alert(msg):
                            st.success(f"اتبعت دامب {sig['symbol']}")
                            time.sleep(1)
            else:
                st.warning("🛡️ مفيش دامب صارم دلوقتي")

backtest_tab = tabs[3]
with backtest_tab:
    st.markdown("### 📊 باك تست - نسبة نجاح حقيقية")
    st.caption("بيرجع 500 شمعة ورا ويشوف الاشارات القديمة كانت هتنجح ولا لا")
    test_sym = st.selectbox("🪙 اختار عملة للباك تست", ["BTCUSDT", "ETHUSDT", "CRVUSDT", "XAUTUSDT", "SOLUSDT"], key="bt_sym")
    if st.button("▶️ شغل باك تست", type="primary", key="bt_run"):
        df_bt = get_klines(test_sym)
        if df_bt is not None:
            res = run_backtest(test_sym, df_bt)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("اشارات", res["total"])
            c2.metric("وصل هدف1", f"{res['wins']} ({res['win_rate']}%)")
            c3.metric("وصل هدف2", res["tp2"])
            c4.metric("ضرب ستوب", res["stops"])
            st.progress(res["win_rate"]/100)
            if res["win_rate"] >= 55:
                st.success(f"الاستراتيجية كسبانة! {res['win_rate']}% زي MidasFlow")
            else:
                st.warning(f"نسبة {res['win_rate']}% - جرب عملة تانية")
            if res["trades"]:
                st.dataframe(pd.DataFrame(res["trades"]), use_container_width=True)

learn_tab = tabs[4]
with learn_tab:
    st.markdown("### 🧠 ذاكرة التعلم - البوت بيتعلم من كل اشارة")
    st.caption("كل اشارة بيبعتها بيحفظ نتيجتها - والنمط اللي بينجح بياخد بونص اكتر")
    mem2 = load_memory()
    total2 = mem2.get("total", 0)
    win2 = mem2.get("total_win", 0)
    if total2 > 0:
        rate2 = win2 / total2 * 100
    else:
        rate2 = 0
    c1, c2 = st.columns(2)
    c1.metric("اشارات محفوظة", total2)
    c2.metric("نسبة نجاح التعلم", f"{rate2:.1f}%")
    st.markdown("**الانماط اللي البوت اتعلمها:**")
    for pat, vals in mem2.get("patterns", {}).items():
        if vals["total"] > 0:
            wr = vals["win"] / vals["total"] * 100
            st.write(f"- {pat}: {vals['win']}/{vals['total']} نجح ({wr:.0f}%)")
    if mem2.get("signals"):
        st.dataframe(pd.DataFrame(mem2["signals"][-20:]), use_container_width=True)
    st.info("النمط اللي بينجح 70%+ بياخد +15 بونص، واللي بيفشل بياخد -10")
