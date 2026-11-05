import streamlit as st
import pandas as pd
import requests, time
from datetime import datetime

st.set_page_config(page_title="BLY7H V7 FINAL", layout="wide", page_icon="🚀")
st.title("🚀 BLY7H V7 FINAL - شغال 100% تليجرام")

TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = st.secrets.get("TELEGRAM_CHANNEL_ID", "@WHYNOTBLY7")
CHAT = st.secrets.get("TELEGRAM_CHAT_ID", "")

if not TOKEN:
    st.error("❌ مفيش TELEGRAM_BOT_TOKEN في Secrets")
    st.stop()

def send_telegram(text, chat_id=None):
    target = chat_id if chat_id else CHANNEL
    if not target:
        return False
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": target, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            return True
        st.error(f"تليجرام: {r.text}")
        return False
    except Exception as e:
        st.error(f"تليجرام خطأ: {e}")
        return False

st.sidebar.header("📱 اختبار تليجرام")
st.sidebar.write(f"TOKEN: {'موجود' if TOKEN else 'مش موجود'}")
st.sidebar.write(f"CHANNEL: {CHANNEL}")
if st.sidebar.button("🧪 جرب ابعت للقناة"):
    if send_telegram("✅ BLY7H V7 شغال - اختبار قناة"):
        st.sidebar.success("✅ اتبعت!")
    else:
        st.sidebar.error("❌ فشل - البوت مش Admin")

if st.sidebar.button("🧪 جرب للخاص"):
    t = CHAT if CHAT else CHANNEL
    if send_telegram("✅ اختبار خاص", chat_id=t):
        st.sidebar.success(f"✅ اتبعت لـ {t}")
    else:
        st.sidebar.error("❌ فشل")

STABLES = ["USDCUSDT","BUSDUSDT","TUSDUSDT","USDPUSDT","DAIUSDT","FDUSDUSDT","USDeUSDT","USD1USDT","RLUSDUSDT","XUSDUSDT","EURUSDT","PYUSDUSDT","GUSDUSDT","USDXUSDT"]

def is_safe_token(pair):
    try:
        liq_obj = pair.get('liquidity', {})
        liq_val = liq_obj.get('usd', 0)
        liq = float(liq_val or 0)
        if liq < 10000:
            return False
        fdv_raw = pair.get('fdv', 0)
        fdv = float(fdv_raw or 0)
        if fdv > 0 and liq / fdv < 0.02:
            return False
        return True
    except:
        return True

def check_token_pump(token_address):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        pairs = data.get('pairs', [])
        if not pairs:
            return None
        best_pair = None
        best_liq = 0
        for p in pairs:
            lo = p.get('liquidity', {})
            lv = float(lo.get('usd', 0) or 0)
            if lv > best_liq:
                best_liq = lv
                best_pair = p
        pair = best_pair
        if not pair:
            return None
        if not is_safe_token(pair):
            return None
        
        base = pair.get('baseToken', {})
        quote = pair.get('quoteToken', {})
        symbol = base.get('symbol','UNK') + "/" + quote.get('symbol','')
        chain = pair.get('chainId','').upper()
        price = pair.get('priceUsd','0')
        
        pc = pair.get('priceChange', {})
        ch5 = float(pc.get('m5',0) or 0)
        ch1 = float(pc.get('h1',0) or 0)
        
        vol = pair.get('volume', {})
        v5 = float(vol.get('m5',0) or 0)
        v1 = float(vol.get('h1',1) or 1)
        
        liq_o = pair.get('liquidity', {})
        liq = float(liq_o.get('usd',0) or 0)
        
        fdv_raw = pair.get('fdv',0)
        fdv = float(fdv_raw or 0)
        dex_url = pair.get('url','')
        
        score = 0
        conds = []
        if v5 > 5000:
            ratio = v5 / (v1/12) if v1>0 else 0
            if ratio >= 2.5:
                score += 25
                conds.append(f"Vol x{ratio:.1f}")
        if ch5 >= 5:
            score += 20
            conds.append(f"+{ch5}% 5د")
        if liq > 15000:
            score += 15
            conds.append(f"${liq/1000:.0f}K")
        if ch1 > 20:
            score += 10
            conds.append(f"+{ch1}% 1س")
        if fdv > 0 and fdv < 20000000:
            score -= 30
        
        hour = datetime.now().hour
        if 2 <= hour <= 6:
            score += 15
            tstate = "🟢 وقت حيتان"
        else:
            tstate = "🟡 عادي"
        
        if score < 75:
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
            tp1 = price
            tp2 = price
            sl = price
            cancel = price
        
        msg = f"🚀 DEX PUMP - BLY7H V7\n💰 {symbol} على {chain}\n📊 {' | '.join(conds)}\n{tstate} | سكور {score}/100\n💵 ${price}\n🎯 دخول ${entry}\n❌ الغاء ${cancel}\n⛔ ستوب ${sl}\n✅ هدف1 ${tp1} | هدف2 ${tp2}\n🔗 {dex_url}\n@WHYNOTBLY7"
        return msg, score, symbol
    except Exception as e:
        return None

def get_symbols_binance():
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/ticker/24hr", timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            usdt = [d for d in data if d.get('symbol','').endswith('USDT')]
            usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume') or 0), reverse=True)
            syms = [d['symbol'] for d in usdt_sorted[:100]]
            clean = []
            for s in syms:
                if s in STABLES: continue
                if 'BULL' in s: continue
                if 'BEAR' in s: continue
                clean.append(s)
            return clean
        except:
            continue
    return []

@st.cache_data(ttl=60)
def get_klines(sym):
    for base in ["https://data-api.binance.vision", "https://api1.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/klines?symbol={sym}&interval=1h&limit=100", timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            if len(data) < 20:
                continue
            df = pd.DataFrame(data, columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
            for c in ['high','low','close','open','vol']:
                df[c] = pd.to_numeric(df[c], errors='coerce')
            return df.dropna()
        except:
            continue
    return None

def predict_pump_dump(df, sym, min_score):
    try:
        last = float(df['close'].iloc[-1])
        prev = float(df['close'].iloc[-2])
        change = (last - prev)/prev*100 if prev!=0 else 0
        mean_vol = float(df['vol'].iloc[-20:-1].mean())
        last_vol = float(df['vol'].iloc[-1])
        vol_spike = last_vol / mean_vol if mean_vol>0 else 1
        
        if vol_spike < 1.8 and abs(change) < 1.5:
            return None
        
        score = 0
        if change > -1:
            score = 40 + min(vol_spike*5, 20)
            ptype = "PUMP"
        else:
            score = 35 + abs(change)*2 + vol_spike*2
            ptype = "DUMP"
        
        score = min(int(score), 99)
        if score < min_score:
            return None
        
        rec_low = float(df['low'].iloc[-10:].min())
        rec_high = float(df['high'].iloc[-10:].max())
        
        if ptype == "PUMP":
            best = last * 0.995
            stop = rec_low * 0.98
            tp1 = last * 1.04
            tp2 = last * 1.08
        else:
            best = last * 1.005
            stop = rec_high * 1.02
            tp1 = last * 0.96
            tp2 = last * 0.92
        
        return {
            'symbol': sym, 'score': score, 'type': ptype, 'price': round(last,6),
            'change_1h': round(change,2), 'vol_spike': round(vol_spike,2),
            'best_entry': round(best,6), 'stop_loss': round(stop,6),
            'TP1': round(tp1,6), 'TP2': round(tp2,6)
        }
    except:
        return None

tab1, tab2 = st.tabs(["🚀 DEX", "💥 CEX"])

with tab1:
    st.subheader("DEX - BSC / ETH / SOL - 15 أداة")
    chains = st.multiselect("الشبكات", ["BSC", "ETH", "SOL"], default=["BSC"])
    if st.button("🔍 افحص DEX + ابعت تليجرام", type="primary"):
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
                        if send_telegram(msg):
                            st.success(f"✅ اتبعت {sym} سكور {score}")
                            found += 1
                        time.sleep(2)
            except Exception as e:
                st.error(f"خطأ {chain_q}: {e}")
        if found == 0:
            st.warning("مفيش بمب قوي - جرب كمان شوية")

with tab2:
    st.subheader("CEX - Binance")
    min_score_cex = st.slider("اقل سكور", 0, 100, 55)
    limit = st.slider("عدد العملات", 20, 100, 50)
    auto_send = st.checkbox("ابعت تليجرام تلقائي", value=True)
    if st.button("💥 افحص CEX + ابعت تليجرام", type="primary"):
        symbols = get_symbols_binance()
        st.write(f"هيفحص {min(limit, len(symbols))} عملة")
        results = []
        prog = st.progress(0)
        for i, sym in enumerate(symbols[:limit]):
            prog.progress((i+1)/limit)
            df = get_klines(sym)
            if df is not None:
                res = predict_pump_dump(df, sym, min_score_cex)
                if res:
                    results.append(res)
            time.sleep(0.02)
        prog.empty()
        if results:
            df_res = pd.DataFrame(results).sort_values('score', ascending=False)
            st.dataframe(df_res, use_container_width=True)
            if auto_send:
                sent = 0
                for sig in df_res.head(5).to_dict('records'):
                    txt = f"🚀 BLY7H {sig['type']} {sig['symbol']}\nسكور {sig['score']} Vol x{sig['vol_spike']} {sig['change_1h']}%\nسعر {sig['price']} دخول {sig['best_entry']} ستوب {sig['stop_loss']} هدف {sig['TP1']}"
                    if send_telegram(txt):
                        sent += 1
                        st.success(f"✅ اتبعت {sig['symbol']}")
                        time.sleep(2)
                st.success(f"اتبعت {sent} اشارات!")
        else:
            st.warning("مفيش")

st.divider()
st.write(f"V7 FINAL | CHANNEL {CHANNEL} | @WHYNOTBLY7")
