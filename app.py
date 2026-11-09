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

st.markdown("<div style='border:2px solid #FFD700;background:#0B0E14;padding:14px;box-shadow:0 24px 80px rgba(0,0,0,.55)'>" + "<div style='text-align:center'><div style='font-size:10px;font-weight:900;letter-spacing:0.28em;color:#FFD700'>BLY7TRADER SIGNALS - POSTER STYLE</div><div style='font-size:42px;font-weight:900;letter-spacing:4px;line-height:1.05;background:linear-gradient(90deg,#FFD700,#FF8C00,#FFD700);-webkit-background-clip:text;-webkit-text-fill-color:transparent'>BLY7TRADER<br>SIGNALS</div><div style='color:#FFD700;font-size:12px;letter-spacing:3px'>BLY7H ULTIMATE V19 MODIFIED - @WHYNOTBLY7 - PREDICT BEFORE THE MOVE</div></div>" + "<div style='text-align:center;margin-top:12px'><span style='display:inline-block;background:#FFD700;color:#000;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:900'>SELF-LEARNING BOT - Learns from 1000 rounds</span></div>" + "<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:14px'>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📐</div><div style='font-size:11px;font-weight:800;color:#FFF'>FVG</div><div style='font-size:10px;color:#8A93A3'>Fair Value Gap</div></div>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>🧱</div><div style='font-size:11px;font-weight:800;color:#FFF'>Order Block</div><div style='font-size:10px;color:#8A93A3'>Whale Zone</div></div>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📊</div><div style='font-size:11px;font-weight:800;color:#FFF'>CVD Real</div><div style='font-size:10px;color:#8A93A3'>Buy vs Sell</div></div>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📈</div><div style='font-size:11px;font-weight:800;color:#FFF'>OI + Funding</div><div style='font-size:10px;color:#8A93A3'>Open Interest</div></div>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📖</div><div style='font-size:11px;font-weight:800;color:#FFF'>Order Book</div><div style='font-size:10px;color:#8A93A3'>Buy / Sell Walls</div></div>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>⏰</div><div style='font-size:11px;font-weight:800;color:#FFF'>Killzone</div><div style='font-size:10px;color:#8A93A3'>London / NY</div></div>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>🧹</div><div style='font-size:11px;font-weight:800;color:#FFF'>Sweep</div><div style='font-size:10px;color:#8A93A3'>Stop Hunt</div></div>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📉</div><div style='font-size:11px;font-weight:800;color:#FFF'>EMA 9/21</div><div style='font-size:10px;color:#8A93A3'>Trend</div></div>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📊</div><div style='font-size:11px;font-weight:800;color:#FFF'>RSI</div><div style='font-size:10px;color:#8A93A3'>Momentum</div></div>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📈</div><div style='font-size:11px;font-weight:800;color:#FFF'>MACD</div><div style='font-size:10px;color:#8A93A3'>Momentum</div></div>" + "<div style='background:#12161F;border:1px solid #1E2530;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>📏</div><div style='font-size:11px;font-weight:800;color:#FFF'>ATR</div><div style='font-size:10px;color:#8A93A3'>Volatility</div></div>" + "<div style='background:#12161F;border:1px solid #FFD700;padding:10px;text-align:center;border-radius:10px'><div style='font-size:20px'>💎</div><div style='font-size:11px;font-weight:900;color:#FFD700'>BLY7TRADER</div><div style='font-size:10px;color:#8A93A3'>@WHYNOTBLY7</div></div>" + "</div>" + "<div style='text-align:center;margin-top:12px'><span style='display:inline-block;background:#12161F;border:1px solid #1E2530;color:#E6E9EF;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700'>Monthly Rent $149 (Foreign $290) - Full Ownership $2499 (Foreign $4000)</span></div>" + "</div>", unsafe_allow_html=True)
st.markdown("<style>.stApp{background:#0B0E14;color:#E6E9EF} h1,h2,h3{color:#E6E9EF!important} .stButton>button{background:#FFD700;color:#000;font-weight:900;border-radius:10px;border:1px solid #FFD700} div[data-testid='stMetric']{background:#12161F;border:1px solid #1E2530;border-radius:14px} .stExpander{border:1px solid #1E2530;border-radius:14px;background:#12161F} section[data-testid='stSidebar']{background:#0F131B;border-right:1px solid #1E2530} div[data-testid='stRadio']>div{flex-wrap:wrap;gap:8px} div[data-testid='stRadio'] label{background:#12161F!important;border:1px solid #1E2530!important;border-radius:20px!important;padding:6px 12px!important;color:#E6E9EF!important}</style>", unsafe_allow_html=True)
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
        tp1=entry+1.5*a_las
