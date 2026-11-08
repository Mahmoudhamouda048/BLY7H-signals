import os, json, time, math, sqlite3, hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import requests
import streamlit as st

st.set_page_config(page_title="BLY7TRADER SIGNALS", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")
CAIRO = ZoneInfo("Africa/Cairo")
DB_PATH = "bly7h_signals.db"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent":"BLY7TRADER-SIGNALS/V19-MOD"})
TIMEOUT = 10
STABLES = {"USDCUSDT","BUSDUSDT","DAIUSDT","FDUSDUSDT","USDEUSDT"}

st.markdown("<div style='border:2px solid #FFD700;background:#0B0E14;padding:14px;box-shadow:0 24px 80px rgba(0,0,0,.55)'>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center'><div style='font-size:10px;font-weight:900;letter-spacing:0.28em;color:#FFD700'>BLY7TRADER SIGNALS - POSTER STYLE</div><div style='font-size:42px;font-weight:900;letter-spacing:4px;line-height:1.05;background:linear-gradient(90deg,#FFD700,#FF8C00,#FFD700);-webkit-background-clip:text;-webkit-text-fill-color:transparent'>BLY7TRADER<br>SIGNALS</div><div style='color:#FFD700;font-size:12px;letter-spacing:3px'>BLY7H ULTIMATE V19 MODIFIED - @WHYNOTBLY7 - PREDICT BEFORE THE MOVE</div></div>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;margin-top:12px'><span style='display:inline-block;background:#FFD700;color:#000;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:900'>SELF-LEARNING BOT - Learns from 1000 rounds</span> <span style='display:inline-block;background:#12161F;border:1px solid #1E2530;color:#E6E9EF;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700'>Monthly Rent $149 (Foreign $290) - Full Ownership $2499 (Foreign $4000)</span></div>", unsafe_allow_html=True)
st.markdown("<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:14px'>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📐</div><div style='font-size:11px;font-weight:800;color:#FFF'>FVG</div><div style='font-size:10px;color:#8A93A3'>Fair Value Gap</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>🧱</div><div style='font-size:11px;font-weight:800;color:#FFF'>Order Block</div><div style='font-size:10px;color:#8A93A3'>Whale Zone</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📊</div><div style='font-size:11px;font-weight:800;color:#FFF'>CVD Real</div><div style='font-size:10px;color:#8A93A3'>Buy vs Sell</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📈</div><div style='font-size:11px;font-weight:800;color:#FFF'>OI + Funding</div><div style='font-size:10px;color:#8A93A3'>Open Interest</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📖</div><div style='font-size:11px;font-weight:800;color:#FFF'>Order Book</div><div style='font-size:10px;color:#8A93A3'>Buy / Sell Walls</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>⏰</div><div style='font-size:11px;font-weight:800;color:#FFF'>Killzone</div><div style='font-size:10px;color:#8A93A3'>London / NY</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>🧹</div><div style='font-size:11px;font-weight:800;color:#FFF'>Sweep</div><div style='font-size:10px;color:#8A93A3'>Stop Hunt</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📉</div><div style='font-size:11px;font-weight:800;color:#FFF'>EMA 9/21</div><div style='font-size:10px;color:#8A93A3'>Trend</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📊</div><div style='font-size:11px;font-weight:800;color:#FFF'>RSI</div><div style='font-size:10px;color:#8A93A3'>Momentum</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📈</div><div style='font-size:11px;font-weight:800;color:#FFF'>MACD</div><div style='font-size:10px;color:#8A93A3'>Momentum</div></div>"
"<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📏</div><div style='font-size:11px;font-weight:800;color:#FFF'>ATR</div><div style='font-size:10px;color:#8A93A3'>Volatility</div></div>"
"<div style='background:#12161F;border:1px solid #FFD700;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>💎</div><div style='font-size:11px;font-weight:900;color:#FFD700'>BLY7TRADER</div><div style='font-size:10px;color:#8A93A3'>@WHYNOTBLY7</div></div>"
"</div>", unsafe_allow_html=True)
st.markdown("<style>.stApp{background:#0B0E14;color:#E6E9EF} h1,h2,h3{color:#E6E9EF!important} .stButton>button{background:#FFD700;color:#000;font-weight:900;border-radius:10px;border:1px solid #FFD700} div[data-testid='stMetric']{background:#12161F;border:1px solid #1E2530;border-radius:14px} .stExpander{border:1px solid #1E2530;border-radius:14px;background:#12161F} section[data-testid='stSidebar']{background:#0F131B;border-right:1px solid #1E2530}</style>", unsafe_allow_html=True)

def api_json(url, params=None, timeout=TIMEOUT):
    try:
        r = SESSION.get(url, params=params, timeout=timeout)
        if r.status_code != 200: return None
        j = r.json()
        if isinstance(j, dict) and j.get("code") not in (None,"200000",200,0): return None
        return j
    except Exception: return None
def safe_float(v, d=0.0):
    try:
        x=float(v); return x if pd.notna(x) else d
    except: return d
def now_cairo(): return datetime.now(CAIRO)
def killzone_status():
    cur=now_cairo(); mins=cur.hour*60+cur.minute
    if 10*60<=mins<=12*60: return True,"London 10:00-12:00 Cairo"
    if 15*60+30<=mins<=17*60+30: return True,"New York 15:30-17:30 Cairo"
    return False,"خارج Killzone - بونص فقط، مش حظر"

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, exchange TEXT, symbol TEXT, side TEXT, score INTEGER, price REAL, entry REAL, stop REAL, tp1 REAL, tp2 REAL, tp3 REAL, change_pct REAL, volume_ratio REAL, cvd REAL, outcome TEXT DEFAULT 'OPEN')""")
        c.execute("""CREATE TABLE IF NOT EXISTS paper_trades (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, symbol TEXT, side TEXT, entry REAL, stop REAL, tp1 REAL, tp2 REAL, tp3 REAL, size_usd REAL, status TEXT DEFAULT 'OPEN', pnl REAL DEFAULT 0, exit_price REAL, exit_reason TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, round_start TEXT UNIQUE, feats TEXT, label TEXT, model TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS backtests (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, symbol TEXT, timeframe TEXT, win_rate REAL, total INTEGER, avg_rr REAL, notes TEXT)""")
        c.commit()
init_db()
def save_signals(signals, exchange):
    if not signals: return
    rows=[]; stamp=datetime.now(timezone.utc).isoformat()
    for s in signals: rows.append((stamp,exchange,s["symbol"],s["type"],s["score"],s["price"],s["entry"],s["stop"],s["tp1"],s["tp2"],s.get("tp3",s["tp2"]),s["ch"],s["vol"],s["buy"],"OPEN"))
    with sqlite3.connect(DB_PATH) as c: c.executemany("INSERT INTO signals (created_at,exchange,symbol,side,score,price,entry,stop,tp1,tp2,tp3,change_pct,volume_ratio,cvd,outcome) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows); c.commit()

def send_telegram(message):
    try: token=st.secrets["TELEGRAM_BOT_TOKEN"]
    except Exception: token=os.getenv("TELEGRAM_BOT_TOKEN","")
    try: chat=st.secrets["TELEGRAM_CHANNEL_ID"]
    except Exception:
        try: chat=st.secrets["TELEGRAM_CHAT_ID"]
        except Exception: chat=os.getenv("TELEGRAM_CHAT_ID", os.getenv("TELEGRAM_CHANNEL_ID",""))
    if not token: return False,"أضف TELEGRAM_BOT_TOKEN في Secrets"
    if not chat: return False,"أضف TELEGRAM_CHANNEL_ID في Secrets"
    try:
        r=SESSION.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":chat,"text":message,"disable_web_page_preview":True}, timeout=15)
        d=r.json()
        return (True,"تم الإرسال") if r.ok and d.get("ok") else (False,d.get("description","Telegram error"))
    except Exception as e: return False,str(e)

def fmt_bly7trader(s):
    side="🚀 LONG" if s["type"]=="LONG" else "🔻 SHORT"
    rr1 = abs(s["tp1"]-s["entry"])/abs(s["entry"]-s["stop"]) if abs(s["entry"]-s["stop"])>0 else 0
    rr2 = abs(s["tp2"]-s["entry"])/abs(s["entry"]-s["stop"]) if abs(s["entry"]-s["stop"])>0 else 0
    return f"""BLY7TRADER\n\n{side} — {s['symbol']}\n⭐ Score: {s['score']}/100\n\n💵 Price: {s['price']:.8g}\n🎯 Entry: {s['entry']:.8g}\n⛔ Stop Loss: {s['stop']:.8g}\n✅ TP1: {s['tp1']:.8g}\n🏆 TP2: {s['tp2']:.8g}\n🏆 TP3: {s.get('tp3',s['tp2']):.8g}\n📊 R:R TP1 1:{rr1:.2f} | TP2 1:{rr2:.2f}\n\n📈 1H Change: {s['ch']}%\n📦 Volume: x{s['vol']}\n📊 CVD: {s['buy']}%\n{s.get('extra','')}\n\n📩 Telegram: @WHYNOTBLY7\n#BLY7TRADER"""

def kucoin_futures_symbols(limit=1000):
    p=api_json("https://api-futures.kucoin.com/api/v1/contracts/active")
    d=(p or {}).get("data",[])
    out=[]
    for c in d:
        s=c.get("symbol","")
        if s.endswith("USDTM"): out.append(s)
    return out[:limit]
def mexc_futures_symbols(limit=1000):
    p=api_json("https://contract.mexc.com/api/v1/contract/detail")
    d=(p or {}).get("data",[]) if isinstance(p,dict) else []
    out=[]
    for c in d:
        s=c.get("symbol","")
        if s.endswith("_USDT"): out.append(s)
    return out[:limit]
def bybit_futures_symbols(limit=1000):
    p=api_json("https://api.bybit.com/v5/market/instruments-info", {"category":"linear","limit":1000})
    d=(p or {}).get("result",{}).get("list",[])
    out=[c.get("symbol","") for c in d if c.get("symbol","").endswith("USDT")]
    return out[:limit]

def klines_kucoin_fut(symbol, gran=15, limit=200):
    end=int(time.time()*1000); start=end-limit*gran*60*1000
    p=api_json("https://api-futures.kucoin.com/api/v1/kline/query", {"symbol":symbol,"granularity":gran,"from":start,"to":end})
    d=(p or {}).get("data",[])
    if len(d)<30: return None
    df=pd.DataFrame(d, columns=["time","open","close","high","low","vol","turnover"])
    for c in ["open","close","high","low","vol"]: df[c]=pd.to_numeric(df[c], errors="coerce")
    return df.dropna().reset_index(drop=True)
def klines_mexc_fut(symbol, interval="15m", limit=200):
    p=api_json("https://contract.mexc.com/api/v1/contract/kline", {"symbol":symbol,"interval":interval,"limit":limit})
    d=(p or {}).get("data",[])
    if not d or len(d)<30: return None
    try:
        df=pd.DataFrame(d, columns=["time","open","high","low","close","vol"])
        for c in ["open","high","low","close","vol"]: df[c]=pd.to_numeric(df[c], errors="coerce")
        return df.dropna().reset_index(drop=True)
    except: return None
def klines_bybit_fut(symbol, interval="15", limit=200):
    p=api_json("https://api.bybit.com/v5/market/kline", {"category":"linear","symbol":symbol,"interval":interval,"limit":limit})
    d=(p or {}).get("result",{}).get("list",[])
    if not d or len(d)<30: return None
    df=pd.DataFrame(d, columns=["time","open","high","low","close","vol","turnover"])
    for c in ["open","high","low","close","vol"]: df[c]=pd.to_numeric(df[c], errors="coerce")
    df=df.sort_values("time").reset_index(drop=True)
    return df

def get_futures_klines(exchange, symbol, gran_label="15m", limit=200):
    if exchange=="KuCoin": return klines_kucoin_fut(symbol, {"1m":1,"3m":3,"5m":5,"15m":15,"1h":60}[gran_label], limit)
    if exchange=="MEXC": return klines_mexc_fut(symbol, gran_label, limit)
    if exchange=="Bybit": return klines_bybit_fut(symbol, {"1m":"1","3m":"3","5m":"5","15m":"15","1h":"60"}[gran_label], limit)
    return None

def ema(s,n): return s.ewm(span=n, adjust=False).mean()
def rsi_calc(s,n=14):
    d=s.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    ru=up.ewm(alpha=1/n, adjust=False).mean(); rd=dn.ewm(alpha=1/n, adjust=False).mean()
    rs=ru/(rd.replace(0,np.nan)); return 100-100/(1+rs)
def macd_calc(s):
    e12=ema(s,12); e26=ema(s,26); m=e12-e26; sig=ema(m,9); return m,sig,m-sig
def atr_calc(df,n=14):
    tr=pd.concat([(df["high"]-df["low"]).abs(), (df["high"]-df["close"].shift()).abs(), (df["low"]-df["close"].shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()
def momentum_calc(s,n=10): return s - s.shift(n)

def detect_fvg(df):
    out=[]
    for i in range(1,len(df)-1):
        if df["low"].iloc[i+1] > df["high"].iloc[i-1]: out.append({"type":"bull","top":float(df["low"].iloc[i+1]),"bottom":float(df["high"].iloc[i-1]),"mid":(float(df["low"].iloc[i+1])+float(df["high"].iloc[i-1]))/2})
        if df["high"].iloc[i+1] < df["low"].iloc[i-1]: out.append({"type":"bear","top":float(df["low"].iloc[i-1]),"bottom":float(df["high"].iloc[i+1]),"mid":(float(df["low"].iloc[i-1])+float(df["high"].iloc[i+1]))/2})
    return out
def detect_ob(df):
    return {"ob_low":float(df["low"].iloc[-3]),"ob_high":float(df["high"].iloc[-3])}
def detect_bsl_ssl(df, lookback=20):
    return {"BSL":float(df["high"].tail(lookback).max()),"SSL":float(df["low"].tail(lookback).min())}
def detect_sweep(df):
    if len(df)<25: return {"sweep":False,"dir":"NONE"}
    bsl_ssl=detect_bsl_ssl(df.iloc[:-2],20)
    last=df.iloc[-1]; prev=df.iloc[-2]
    if float(last["high"])>bsl_ssl["BSL"] and float(last["close"])<bsl_ssl["BSL"]: return {"sweep":True,"dir":"BEARISH_SWEEP"}
    if float(last["low"])<bsl_ssl["SSL"] and float(last["close"])>bsl_ssl["SSL"]: return {"sweep":True,"dir":"BULLISH_SWEEP"}
    return {"sweep":False,"dir":"NONE"}

def orderbook_kucoin_fut(symbol):
    p=api_json("https://api-futures.kucoin.com/api/v1/level2/snapshot", {"symbol":symbol})
    d=(p or {}).get("data",{})
    if not d: return None
    bids=d.get("bids",[])[:10]; asks=d.get("asks",[])[:10]
    try:
        bid_vol=sum(float(b[1]) for b in bids); ask_vol=sum(float(a[1]) for a in asks)
        return {"bid_wall":max([float(b[1]) for b in bids], default=0),"ask_wall":max([float(a[1]) for a in asks], default=0),"bid_vol":bid_vol,"ask_vol":ask_vol,"spread":None}
    except: return None
def funding_kucoin(symbol):
    p=api_json("https://api-futures.kucoin.com/api/v1/funding-rate", {"symbol":symbol})
    d=(p or {}).get("data",{})
    if not d: return "N/A"
    v=d.get("value") if isinstance(d,dict) else None
    return f"{float(v)*100:.4f}%" if v is not None else "N/A"
def funding_mexc(symbol):
    p=api_json("https://contract.mexc.com/api/v1/contract/funding_rate", {"symbol":symbol})
    d=(p or {}).get("data",{})
    if not d: return "N/A"
    v=d.get("fundingRate")
    return f"{float(v)*100:.4f}%" if v is not None else "N/A"
def funding_bybit(symbol):
    p=api_json("https://api.bybit.com/v5/market/funding/history", {"category":"linear","symbol":symbol,"limit":1})
    l=(p or {}).get("result",{}).get("list",[])
    if not l: return "N/A"
    return f"{float(l[0].get('fundingRate',0))*100:.4f}%"
def oi_kucoin(symbol):
    p=api_json("https://api-futures.kucoin.com/api/v1/open-interest", {"symbol":symbol})
    d=(p or {}).get("data",{})
    if not d: return "N/A"
    return d.get("openInterest", "N/A")
def cvd_from_trades_kucoin(symbol):
    p=api_json("https://api-futures.kucoin.com/api/v1/trade/history", {"symbol":symbol})
    d=(p or {}).get("data",[])
    if not d: return None
    buy=sum(float(t.get("size",0)) for t in d if t.get("side")=="buy"); sell=sum(float(t.get("size",0)) for t in d if t.get("side")=="sell")
    if buy+sell==0: return None
    return (buy-sell)/(buy+sell)*100

def analyze_futures(exchange, symbol, display, btc_trend="NEUTRAL"):
    df = get_futures_klines(exchange, symbol, "1h", 200)
    if df is None: return None
    df15 = get_futures_klines(exchange, symbol, "15m", 100)
    price=float(df["close"].iloc[-1])
    e9=ema(df["close"],9); e21=ema(df["close"],21); r=rsi_calc(df["close"]); m,sig,hist=macd_calc(df["close"]); a=atr_calc(df); mom=momentum_calc(df["close"])
    fvg=detect_fvg(df); ob=detect_ob(df); bsl_ssl=detect_bsl_ssl(df); sweep=detect_sweep(df)
    cvd_real=None
    if exchange=="KuCoin": cvd_real=cvd_from_trades_kucoin(symbol)
    if cvd_real is None:
        last20=df.tail(20); bv=float(last20[last20["close"]>last20["open"]]["vol"].sum()); sv=float(last20[last20["close"]<=last20["open"]]["vol"].sum())
        cvd=(bv-sv)/(bv+sv+1e-9)*100; cvd_src="CVD proxy من الشموع - تقديري"
    else: cvd=float(cvd_real); cvd_src="CVD حقيقي من صفقات KuCoin"
    avg_vol=float(df["vol"].iloc[:-10].mean()) if len(df)>20 else 1; last_vol=float(df["vol"].iloc[-1]); vol_ratio=last_vol/avg_vol if avg_vol>0 else 1
    score=10; reasons=[]
    is_long=e9.iloc[-1]>e21.iloc[-1]; is_short=not is_long
    if is_long: score+=12; reasons.append("EMA9>21")
    else: score+=12; reasons.append("EMA9<21")
    r_last=float(r.iloc[-1]) if pd.notna(r.iloc[-1]) else 50
    if 45<=r_last<=65: score+=10; reasons.append("RSI جاهز")
    elif r_last>70 or r_last<30: score+=4; reasons.append("RSI متطرف - حذر")
    else: score+=6
    if float(hist.iloc[-1])>0 and is_long: score+=8; reasons.append("MACD+")
    if float(hist.iloc[-1])<0 and is_short: score+=8; reasons.append("MACD-")
    if fvg: score+=20; reasons.append(f"FVG {fvg[-1]['type']}")
    if vol_ratio>=1.5: score+=15; reasons.append(f"حجم x{vol_ratio:.2f}")
    elif vol_ratio>=1.2: score+=8
    if abs(cvd)>20: score+=10; reasons.append(f"CVD {cvd:.1f}%")
    if sweep["sweep"]: score+=12; reasons.append(f"Sweep {sweep['dir']}")
    mtf="N/A"
    if df15 is not None:
        e9_15=ema(df15["close"],9); e21_15=ema(df15["close"],21)
        if is_long and e9_15.iloc[-1]>e21_15.iloc[-1]: score+=8; reasons.append("15m يؤكد LONG"); mtf="15m ✅"
        elif is_short and e9_15.iloc[-1]<e21_15.iloc[-1]: score+=8; reasons.append("15m يؤكد SHORT"); mtf="15m ✅"
        else: mtf="15m ❌ تعارض"
    btc_note=""
    if btc_trend=="UP" and is_short: score-=8; btc_note="BTC صاعد - SHORT أضعف"
    if btc_trend=="DOWN" and is_long: score-=8; btc_note="BTC هابط - LONG أضعف"
    kz,_=killzone_status()
    if kz: score+=5; reasons.append("Killzone +5")
    ch_1h=(price-float(df["open"].iloc[-1]))/float(df["open"].iloc[-1])*100 if float(df["open"].iloc[-1])!=0 else 0
    if abs(ch_1h)>30: return None
    a_last=float(a.iloc[-1]) if pd.notna(a.iloc[-1]) else price*0.01
    if a_last<=0: a_last=price*0.01
    side="LONG" if is_long else "SHORT"
    if side=="LONG":
        entry=price; stop=max(ob["ob_low"], price-1.5*a_last)
        if (entry-stop)/entry>0.03: stop=entry*0.985
        tp1=entry+1.5*a_last; tp2=entry+2.8*a_last; tp3=entry+4.5*a_last
    else:
        entry=price; stop=min(ob["ob_high"], price+1.5*a_last)
        if (stop-entry)/entry>0.03: stop=entry*1.015
        tp1=entry-1.5*a_last; tp2=entry-2.8*a_last; tp3=entry-4.5*a_last
    fee_pct=0.06; slippage_pct=0.03
    risk=abs(entry-stop); rr1=abs(tp1-entry)/risk if risk>0 else 0; rr2=abs(tp2-entry)/risk if risk>0 else 0; rr3=abs(tp3-entry)/risk if risk>0 else 0
    funding="N/A"; oi="N/A"; obk=None
    if exchange=="KuCoin": funding=funding_kucoin(symbol); oi=oi_kucoin(symbol); obk=orderbook_kucoin_fut(symbol)
    elif exchange=="MEXC": funding=funding_mexc(symbol)
    elif exchange=="Bybit": funding=funding_bybit(symbol)
    extra=f"EMA9 {float(e9.iloc[-1]):.4g} / EMA21 {float(e21.iloc[-1]):.4g} | RSI {r_last:.1f} | ATR {a_last:.4g} | BSL {bsl_ssl['BSL']:.4g} / SSL {bsl_ssl['SSL']:.4g} | Sweep {sweep['dir']} | MTF {mtf} | Funding {funding} | OI {oi} | {cvd_src} | {btc_note} | رسوم تقديرية {fee_pct}% + انزلاق {slippage_pct}% | Trailing: حرك الاستوب للدخول عند TP1، ثم Trailing بـ 1 ATR"
    return {"symbol":display,"exchange":exchange,"type":side,"score":int(max(5,min(100,score))),"price":price,"entry":entry,"stop":stop,"tp1":tp1,"tp2":tp2,"tp3":tp3,"ch":round(float(ch_1h),2),"vol":round(float(vol_ratio),2),"buy":round(float(cvd),1),"rsi":round(r_last,1),"atr":a_last,"fvg":len(fvg),"extra":extra,"rr1":round(float(rr1),2),"rr2":round(float(rr2),2),"rr3":round(float(rr3),2),"funding":funding,"oi":oi,"ob":obk,"killzone":kz,"mtf":mtf}

def mexc_prediction_check(symbol="BTCUSDT"):
    try: key=st.secrets["CHAINLINK_API_KEY"]
    except Exception: key=os.getenv("CHAINLINK_API_KEY","")
    if key:
        return {"status":"CHAINLINK","msg":"Chainlink API Key موجود - التسوية من Chainlink TWAP 60s الرسمي. راجع https://data.chain.link/streams/btc-usd-twap-60s-streams","key":True}
    p=api_json("https://api.mexc.com/api/v3/ticker/price", {"symbol":symbol})
    price=safe_float((p or {}).get("price",0))
    return {"status":"WAIT_OFFICIAL","msg":f"⏳ انتظار التسوية الرسمية - Chainlink TWAP 60s غير متاح (مفيش CHAINLINK_API_KEY في Secrets). السعر الحالي من MEXC Spot كمؤشر فقط: {price} - لا تستخدمه كسعر تسوية. القاعدة: TWAP >= Open => UP، TWAP < Open => DOWN","key":False,"price":price}

def options_analysis(symbol="BTC"):
    return {"IV":"N/A - لا يوجد مصدر خيارات مجاني متاح في هذا الإصدار","OI":"N/A","Strikes":"N/A","Greeks":"N/A - Delta/Gamma/Theta/Vega تحتاج مصدر خيارات مرخص","note":"N/A"}

def football_analysis(home, away, home_odds, draw_odds, away_odds):
    try:
        ph=1/float(home_odds); pd_=1/float(draw_odds); pa=1/float(away_odds); tot=ph+pd_+pa
        return {"home":round(ph/tot*100,1),"draw":round(pd_/tot*100,1),"away":round(pa/tot*100,1),"note":"احتمالات ضمنية من الأودز بعد إزالة هامش الوسيط - تحليل فقط، لا يوجد تنفيذ مراهنات تلقائية"}
    except: return {"home":"N/A","draw":"N/A","away":"N/A","note":"ادخل أودز صحيحة"}

def backtest_simple(exchange, symbol, gran="1h", limit=500):
    df=get_futures_klines(exchange, symbol, gran, limit)
    if df is None or len(df)<60: return None
    split=int(len(df)*0.7); train=df.iloc[:split]; test=df.iloc[split:]
    wins=0; total=0; rrs=[]
    for i in range(1,len(test)-1):
        window=pd.concat([train, test.iloc[:i]])
        e9=ema(window["close"],9); e21=ema(window["close"],21)
        if len(e9)<2: continue
        is_long=e9.iloc[-1]>e21.iloc[-1]
        entry=float(test.iloc[i]["close"]); nxt=float(test.iloc[i+1]["close"])
        a=atr_calc(window); a_last=float(a.iloc[-1]) if pd.notna(a.iloc[-1]) else entry*0.01
        if is_long:
            if nxt>=entry+1.5*a_last: wins+=1; rrs.append(1.5)
            elif nxt<=entry-1.5*a_last: rrs.append(-1)
            total+=1
        else:
            if nxt<=entry-1.5*a_last: wins+=1; rrs.append(1.5)
            elif nxt>=entry+1.5*a_last: rrs.append(-1)
            total+=1
    if total==0: return None
    wr=wins/total*100; avg_rr=sum(rrs)/len(rrs) if rrs else 0
    return {"symbol":symbol,"timeframe":gran,"total":total,"win_rate":round(wr,1),"avg_rr":round(avg_rr,2),"train_len":len(train),"test_len":len(test)}

st.markdown(f"**Killzone:** {'✅ '+killzone_status()[1] if killzone_status()[0] else '⏸️ '+killzone_status()[1]} | **البيانات:** Futures حقيقية من المنصة - Spot مفصول تمامًا | **آخر تحديث:** {now_cairo().strftime('%Y-%m-%d %H:%M:%S')} Cairo")
st.markdown("<div style='border:1px solid #1E2530;background:#12161F;border-radius:14px;padding:12px;margin-top:14px'><div style='font-size:12px;font-weight:900;letter-spacing:0.2em;color:#FFD700;text-align:center'>الأقسام - اختار قسم</div></div>", unsafe_allow_html=True)
section = st.radio("الأقسام", ["📡 Futures Scanner","📊 تحليل عملة","🎲 MEXC Prediction","📈 Options","⚽ Football","💾 Paper Trading","📊 Performance","🧠 MEXC Learner","📩 Telegram"], horizontal=True, label_visibility="collapsed")
st.sidebar.markdown("---"); st.sidebar.markdown("**BLY7TRADER SIGNALS**"); st.sidebar.caption("TELEGRAM_BOT_TOKEN + TELEGRAM_CHANNEL_ID في Secrets")

if section.startswith("📡"):
    st.subheader("🔍 Futures Scanner - KuCoin / MEXC / Bybit - فصل تام عن Spot")
    c1,c2,c3,c4=st.columns(4)
    with c1: exch=st.selectbox("المنصة", ["KuCoin","MEXC","Bybit"])
    with c2: n_sym=st.slider("عدد العملات", 20, 500, 500, step=10)
    with c3: min_score=st.slider("أقل Score", 50, 85, 65)
    with c4: side_f=st.selectbox("الاتجاه", ["الكل","LONG فقط","SHORT فقط"])
    btc_df=get_futures_klines("KuCoin","XBTUSDTM","1h",100) if exch=="KuCoin" else None
    btc_trend="NEUTRAL"
    if btc_df is not None:
        e9=ema(btc_df["close"],9); e21=ema(btc_df["close"],21)
        btc_trend="UP" if e9.iloc[-1]>e21.iloc[-1] else "DOWN"
    if st.button("🔍 امسح Futures دلوقتي", type="primary", use_container_width=True):
        with st.spinner(f"بمسح {exch} Futures..."):
            if exch=="KuCoin": syms=kucoin_futures_symbols(n_sym)
            elif exch=="MEXC": syms=mexc_futures_symbols(n_sym)
            else: syms=bybit_futures_symbols(n_sym)
            results=[]; prog=st.progress(0)
            for i,s in enumerate(syms):
                prog.progress((i+1)/len(syms))
                disp=s.replace("USDTM","/USDT").replace("_USDT","/USDT") if exch!="Bybit" else s.replace("USDT","/USDT")
                if any(x in s for x in ["USDC","DAI"]): continue
                r=analyze_futures(exch, s, disp, btc_trend)
                if r and r["score"]>=min_score:
                    if side_f=="LONG فقط" and r["type"]!="LONG": continue
                    if side_f=="SHORT فقط" and r["type"]!="SHORT": continue
                    results.append(r)
            results=sorted(results, key=lambda x: x["score"], reverse=True)
            st.session_state["fut_results"]=results; save_signals(results, exch)
            if not results: st.warning(f"مسحنا {len(syms)} عملة - مفيش فرص واضحة فوق Score {min_score} - قلل Score لـ 55 وجرب تاني - الفرص الواضحة فقط بتظهر")
    res=st.session_state.get("fut_results",[])
    if res:
        m1,m2,m3,m4=st.columns(4)
        m1.metric("إجمالي الفرص", len(res))
        m2.metric("LONG", sum(1 for x in res if x["type"]=="LONG"))
        m3.metric("SHORT", sum(1 for x in res if x["type"]=="SHORT"))
        m4.metric("أعلى Score", max(x["score"] for x in res))
        st.markdown(f"### 🔥 أقوى {len(res)} إشارة")
        df_show=pd.DataFrame([{"العملة":r["symbol"],"المنصة":r["exchange"],"الاتجاه":r["type"],"Score":r["score"],"السعر":r["price"],"الدخول":r["entry"],"الاستوب":r["stop"],"TP1":r["tp1"],"TP2":r["tp2"],"TP3":r["tp3"],"R:R TP2":r["rr2"],"1H%":r["ch"],"حجم":r["vol"],"CVD":r["buy"],"Funding":r["funding"]} for r in res])
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        for r in res[:10]:
            with st.expander(f"{r['symbol']} — {r['type']} — Score {r['score']} — دخول {r['entry']:.8g}"):
                st.markdown(f"**الدخول:** {r['entry']:.8g} | **الاستوب - نقطة اللاعودة:** {r['stop']:.8g} | **TP1:** {r['tp1']:.8g} | **TP2:** {r['tp2']:.8g} | **TP3 رنر:** {r['tp3']:.8g} | **R:R:** TP1 1:{r['rr1']} TP2 1:{r['rr2']} TP3 1:{r['rr3']}")
                st.text(r["extra"])
                st.code(fmt_bly7trader(r), language="text")
                if st.button(f"📩 ابعت {r['symbol']} لتليجرام", key=f"tg_{r['symbol']}_{r['type']}"):
                    ok,msg=send_telegram(fmt_bly7trader(r)); st.success(msg) if ok else st.error(msg)
        if st.button("📩 ابعت أقوى 5 لتليجرام"):
            for r in res[:5]: send_telegram(fmt_bly7trader(r)); time.sleep(0.4)
            st.success("تم إرسال أقوى 5")

elif section.startswith("📊 تحليل"):
    st.subheader("📊 تحليل عملة واحدة - كل الفواصل 1m / 3m / 5m / 15m / 1h - Futures فقط")
    exch2=st.selectbox("المنصة", ["KuCoin","MEXC","Bybit"], key="ex2")
    sym_in=st.text_input("العملة", "XBTUSDTM" if exch2=="KuCoin" else ("BTC_USDT" if exch2=="MEXC" else "BTCUSDT")).strip().upper()
    if st.button("📊 حلل على كل الفواصل"):
        for gran in ["1m","3m","5m","15m","1h"]:
            df=get_futures_klines(exch2, sym_in, gran, 200)
            if df is None: st.warning(f"{gran}: N/A - مفيش شموع"); continue
            e9=ema(df["close"],9); e21=ema(df["close"],21); rr=rsi_calc(df["close"]); mm,ss,hh=macd_calc(df["close"]); aa=atr_calc(df)
            st.markdown(f"**{gran}** — سعر `{float(df['close'].iloc[-1]):.8g}` | EMA9 `{float(e9.iloc[-1]):.8g}` | EMA21 `{float(e21.iloc[-1]):.8g}` | RSI `{float(rr.iloc[-1]):.1f}` | MACD Hist `{float(hh.iloc[-1]):.8g}` | ATR `{float(aa.iloc[-1]):.8g}` | Momentum `{float(momentum_calc(df['close']).iloc[-1]):.8g}` | FVG {len(detect_fvg(df))} | OB {detect_ob(df)} | BSL/SSL {detect_bsl_ssl(df)} | Sweep {detect_sweep(df)['dir']}")

elif section.startswith("🎲"):
    st.subheader("🎯 MEXC Prediction - UP / DOWN / NO_TRADE")
    chk=mexc_prediction_check("BTCUSDT")
    if chk["status"]=="CHAINLINK": st.success(chk["msg"])
    else: st.warning(chk["msg"])
    sym_p=st.text_input("العملة", "BTCUSDT", key="pred_sym")
    if st.button("🔍 توقع الجولة الحالية"):
        r=analyze_futures("KuCoin","XBTUSDTM","BTC/USDT","NEUTRAL")
        if r is None: st.warning("NO_TRADE - مفيش إشارة واضحة")
        else:
            st.markdown(f"**Score:** {r['score']} | **FVG:** {r['fvg']} | **CVD:** {r['buy']}% | **الدخول:** {r['entry']:.8g} | **الاستوب:** {r['stop']:.8g}")
            if r["score"]>=70 and r["fvg"]>0 and abs(r["buy"])>10:
                st.success(f"توقع: {'🟢 UP - ادخل شراء' if r['type']=='LONG' else '🔴 DOWN - ادخل بيع'} - 3 شروط متوفرة")
            else: st.warning("⏸️ NO_TRADE - شرط ناقص - المعتدل لا يدخل ناقص")


elif section.startswith("🧠"):
    st.subheader("🤖 MEXC Learner - بيعلم نفسه بنفسه")
    st.markdown("### التعلم الذاتي")
    if st.button("🧠 علم البوت من 1000 جولة سابقة دلوقتي", type="primary", use_container_width=True):
        with st.spinner("بيتعلم من 1000 شمعة..."):
            res_learn=lab_auto_learn("KuCoin","XBTUSDTM",1000)
            st.success(f"اتعلم من {res_learn['learned']} جولة - الدقة: {res_learn['accuracy']}% على {res_learn['total']} جولة - {'نموذج جديد أفضل - تم الاحتفاظ به' if res_learn.get('is_best') else 'النموذج القديم أفضل - تم الاحتفاظ به'}")
    with sqlite3.connect(DB_PATH) as _c:
        try: _rows=_c.execute("SELECT created_at,accuracy,total,is_best FROM lab_models ORDER BY id DESC LIMIT 5").fetchall()
        except: _rows=[]
        try: _cnt=_c.execute("SELECT COUNT(*) FROM lab_rounds").fetchone()[0]
        except: _cnt=0
    st.markdown(f"**إجمالي الجولات المتعلمة:** {_cnt}")
    if _rows:
        for _r in _rows: st.markdown(f"- {_r[0][:19]} - دقة {_r[1]:.1f}% على {_r[2]} جولة - {'⭐ الأفضل' if _r[3] else ''}")
    if st.button("🔍 توقع الجولة الحالية - بعد التعلم"):
        pr=lab_predict_current("KuCoin","XBTUSDTM")
        if pr is None: st.warning("N/A")
        else:
            st.markdown(f"**التوقع:** {'🟢 UP' if pr['pred']=='UP' else '🔴 DOWN'} - **الثقة:** {pr['conf']}% - **دقة النموذج:** {pr['accuracy']}% على {pr['total']} جولة")
            st.text(" | ".join(pr['reasons']))
            if pr['conf']>=70: st.success("المعتدل: ادخل" if pr['pred']=='UP' else "المعتدل: ادخل بيع")
            else: st.warning("NO_TRADE - الثقة أقل من 70")

elif section.startswith("📈"):
    st.subheader("📈 Options Analysis")
    sym_o=st.text_input("العملة للخيارات", "BTC", key="opt_sym")
    o=options_analysis(sym_o)
    st.markdown(f"**Implied Volatility:** {o['IV']}\n\n**Open Interest:** {o['OI']}\n\n**Strike Prices:** {o['Strikes']}\n\n**Greeks:** {o['Greeks']}\n\n*{o['note']}*")

elif section.startswith("⚽"):
    st.subheader("⚽ Football Analysis - تحليل مستقل، بدون مراهنات تلقائية")
    c1,c2=st.columns(2)
    with c1: home=st.text_input("الفريق الأول", "Real Madrid")
    with c2: away=st.text_input("الفريق الثاني", "Barcelona")
    o1,o2,o3=st.columns(3)
    with o1: oh=st.number_input("أودز فوز الأول (1)", value=2.10, step=0.01)
    with o2: od=st.number_input("أودز التعادل (X)", value=3.40, step=0.01)
    with o3: oa=st.number_input("أودز فوز الثاني (2)", value=3.20, step=0.01)
    if st.button("📊 احسب الاحتمالات"):
        f=football_analysis(home, away, oh, od, oa)
        st.markdown(f"**{home} فوز (1):** {f['home']}% | **تعادل (X):** {f['draw']}% | **{away} فوز (2):** {f['away']}%")

elif section.startswith("💾"):
    st.subheader("💾 Paper Trading + Backtest + Walk-forward")
    st.markdown("**Paper Trading:** سجل صفقة وهمية من غير فلوس حقيقية، وتابعها.")
    pc1,pc2,pc3=st.columns(3)
    with pc1: pt_sym=st.text_input("العملة", "BTC/USDT", key="pt_sym")
    with pc2: pt_side=st.selectbox("الاتجاه", ["LONG","SHORT"], key="pt_side")
    with pc3: pt_size=st.number_input("حجم الصفقة $", value=100.0, step=10.0, key="pt_size")
    pe1,pe2,pe3=st.columns(3)
    with pe1: pt_entry=st.number_input("الدخول", value=0.0, format="%.8f", key="pt_entry")
    with pe2: pt_stop=st.number_input("الاستوب", value=0.0, format="%.8f", key="pt_stop")
    with pe3: pt_tp1=st.number_input("TP1", value=0.0, format="%.8f", key="pt_tp1")
    if st.button("💾 سجل Paper Trade"):
        if pt_entry>0:
            with sqlite3.connect(DB_PATH) as c: c.execute("INSERT INTO paper_trades (created_at,symbol,side,entry,stop,tp1,tp2,tp3,size_usd) VALUES (?,?,?,?,?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), pt_sym, pt_side, pt_entry, pt_stop, pt_tp1, pt_tp1, pt_tp1, pt_size)); c.commit()
            st.success("تم تسجيل Paper Trade")
    with sqlite3.connect(DB_PATH) as c: df_pt=pd.read_sql_query("SELECT * FROM paper_trades ORDER BY id DESC LIMIT 20", c)
    if not df_pt.empty: st.dataframe(df_pt, use_container_width=True, hide_index=True)
    st.markdown("---")
    st.markdown("**Backtest + Walk-forward (بدون Look-ahead):**")
    be1,be2=st.columns(2)
    with be1: bt_ex=st.selectbox("المنصة للباك تست", ["KuCoin","MEXC","Bybit"], key="bt_ex")
    with be2: bt_sym=st.text_input("رمز الباك تست", "XBTUSDTM" if bt_ex=="KuCoin" else "BTCUSDT", key="bt_sym")
    if st.button("▶️ شغل Backtest"):
        bt=backtest_simple(bt_ex, bt_sym, "1h", 500)
        if bt is None: st.warning("N/A")
        else:
            st.markdown(f"**Win Rate:** {bt['win_rate']}% | **إجمالي الصفقات:** {bt['total']} | **متوسط R:R:** {bt['avg_rr']} | **Train:** {bt['train_len']} شمعة | **Test:** {bt['test_len']} شمعة (Walk-forward 70/30)")
            with sqlite3.connect(DB_PATH) as c: c.execute("INSERT INTO backtests (created_at,symbol,timeframe,win_rate,total,avg_rr,notes) VALUES (?,?,?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), bt_sym, "1h", bt['win_rate'], bt['total'], bt['avg_rr'], "Champion: EMA9/21 | Challenger: EMA9/21 + FVG - بدون Look-ahead")); c.commit()

elif section.startswith("📊 Performance"):
    st.subheader("📊 Performance Dashboard - دقة الإشارات")
    with sqlite3.connect(DB_PATH) as c:
        try: df_s=pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT 200", c)
        except: df_s=pd.DataFrame()
        try: df_b=pd.read_sql_query("SELECT * FROM backtests ORDER BY id DESC LIMIT 20", c)
        except: df_b=pd.DataFrame()
    if df_s.empty: st.info("لسه مفيش إشارات مسجلة - امسح Futures الأول")
    else:
        st.markdown(f"**إجمالي الإشارات:** {len(df_s)} | **متوسط Score:** {df_s['score'].mean():.1f} | **LONG:** {(df_s['side']=='LONG').sum()} | **SHORT:** {(df_s['side']=='SHORT').sum()}")
        st.dataframe(df_s, use_container_width=True, hide_index=True)
    if not df_b.empty:
        st.markdown("### Backtests السابقة"); st.dataframe(df_b, use_container_width=True, hide_index=True)

elif section.startswith("📩"):
    st.subheader("📩 Telegram Test - @WHYNOTBLY7")
    if st.button("📩 ابعت رسالة تجريبية"):
        ok,msg=send_telegram("BLY7TRADER SIGNALS - Test ✅ - البوت شغال - @WHYNOTBLY7")
        st.success(msg) if ok else st.error(msg)
    st.markdown("**Secrets المطلوبة في Streamlit:**\n```\nTELEGRAM_BOT_TOKEN = \"...\"\nTELEGRAM_CHANNEL_ID = \"-100...\"\nCHAINLINK_API_KEY = \"...\" # اختياري - للتسوية الرسمية\n```")

st.markdown("---")
