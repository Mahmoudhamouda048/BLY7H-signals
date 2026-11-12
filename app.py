# BLY7TRADER — ULTIMATE V19 - FIXED FULL VERSION
# MEXC FUTURES SIGNAL ENGINE
# Run: pip install -r requirements.txt
# Then: streamlit run BLY7TRADER_FIXED.py
import os, json, time, sqlite3, logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import requests
import streamlit as st
st.set_page_config(page_title="BLY7TRADER ULTIMATE", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")
APP_TITLE = "💎 BLY7TRADER — ULTIMATE"
APP_VERSION = "20.0"
EXCHANGE = "MEXC"
DB_PATH = os.getenv("BLY7TRADER_DB", "bly7trader_memory.db")
TIMEOUT = 12
MAX_RETRIES = 3
SCAN_LIMIT_DEFAULT = 100
MIN_SIGNAL_SCORE = 75
CAIRO = ZoneInfo("Africa/Cairo")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"BLY7TRADER/{APP_VERSION}", "Accept": "application/json"})
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
LOGGER = logging.getLogger("BLY7TRADER")
st.markdown("""<style>.main{background-color:#080b12}[data-testid="stAppViewContainer"]{background:radial-gradient(circle at top,#172238 0%,#080b12 48%)}.bly-header{text-align:center;padding:22px 10px;border:1px solid #27364c;border-radius:16px;background:linear-gradient(135deg,#111b2c,#080b12);margin-bottom:18px}.bly-title{color:#e8bd62;font-size:32px;font-weight:900;letter-spacing:2px}.bly-subtitle{color:#9aa9bd;font-size:13px}.bly-card{background:#111827;border:1px solid #26364b;border-radius:12px;padding:14px;margin-bottom:10px}.bly-green{color:#00d395;font-weight:bold}.bly-red{color:#ff5364;font-weight:bold}.bly-gold{color:#e8bd62;font-weight:bold}</style><div class="bly-header"><div class="bly-title">BLY7TRADER</div><div class="bly-subtitle">ULTIMATE FUTURES INTELLIGENCE ENGINE | MEXC FUTURES ONLY</div></div>""", unsafe_allow_html=True)
TIMEFRAMES = {"5m":"Min5","15m":"Min15","30m":"Min30","1h":"Min60","4h":"Hour4","1d":"Day1"}
SCAN_TIMEFRAMES = ["5m","15m","1h","4h","1d"]
DEFAULT_SETTINGS = {"min_score":MIN_SIGNAL_SCORE,"scan_limit":SCAN_LIMIT_DEFAULT,"timeframes":SCAN_TIMEFRAMES,"enable_long":True,"enable_short":True,"btc_filter":True,"volume_filter":True,"oi_filter":True,"funding_filter":True,"orderbook_filter":True,"learning_enabled":True,"telegram_enabled":True,"minimum_rr":1.8,"risk_percent":1.0,"max_open_signals":30}
def now_utc(): return datetime.now(timezone.utc)
def now_cairo(): return datetime.now(CAIRO)
def utc_iso(): return now_utc().isoformat()
def format_time(value=None):
    value = value or now_cairo()
    return value.strftime("%Y-%m-%d %H:%M:%S")
def log_event(message, level="info"):
    if level=="error": LOGGER.error(message)
    elif level=="warning": LOGGER.warning(message)
    else: LOGGER.info(message)
def safe_float(value, default=0.0):
    try:
        result=float(value)
        if pd.isna(result): return default
        return result
    except (TypeError, ValueError, OverflowError): return default
def safe_int(value, default=0):
    try: return int(float(value))
    except (TypeError, ValueError, OverflowError): return default
def clamp(value, minimum, maximum): return max(minimum, min(maximum, value))
def percent_change(current, previous):
    current=safe_float(current); previous=safe_float(previous)
    if previous==0: return 0.0
    return ((current-previous)/previous)*100
def normalize_symbol(symbol): return str(symbol).upper().replace("/","").replace("-","").replace("_","").strip()
def is_valid_price(value):
    value=safe_float(value); return value>0 and value<1e15
def api_json(url, params=None, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            response=SESSION.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status(); payload=response.json()
            if not isinstance(payload,(dict,list)): return None
            if isinstance(payload,dict):
                code=payload.get("code")
                if code not in (None,0,"0",200,"200","200000","00000"): return None
            return payload
        except requests.Timeout: log_event(f"API timeout: {url}","warning")
        except requests.RequestException as exc: log_event(f"API request failed: {exc}","warning")
        except (ValueError, TypeError) as exc: log_event(f"Invalid API response: {exc}","warning")
        if attempt<retries-1: time.sleep(0.5*(attempt+1))
    return None
MEXC_BASE_URL="https://contract.mexc.com"
MEXC_ENDPOINTS={"DETAILS":f"{MEXC_BASE_URL}/api/v1/contract/detail","TICKER":f"{MEXC_BASE_URL}/api/v1/contract/ticker","KLINE":f"{MEXC_BASE_URL}/api/v1/contract/kline","DEPTH":f"{MEXC_BASE_URL}/api/v1/contract/depth","FUNDING":f"{MEXC_BASE_URL}/api/v1/contract/funding_rate","OPEN_INTEREST":f"{MEXC_BASE_URL}/api/v1/contract/open_interest"}
def mexc_request(endpoint, params=None): return api_json(endpoint, params=params)
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, exchange TEXT NOT NULL DEFAULT 'MEXC', symbol TEXT NOT NULL, side TEXT NOT NULL, timeframe TEXT, score INTEGER NOT NULL, price REAL NOT NULL, entry REAL NOT NULL, stop REAL NOT NULL, tp1 REAL NOT NULL, tp2 REAL NOT NULL, tp3 REAL, change_pct REAL DEFAULT 0, volume_ratio REAL DEFAULT 0, cvd_proxy REAL DEFAULT 0, funding_pct REAL DEFAULT 0, oi_change_pct REAL DEFAULT 0, outcome TEXT DEFAULT 'OPEN', status TEXT DEFAULT 'ENTRY_PENDING', last_price REAL, last_checked_at TEXT, entry_hit_at TEXT, tp1_hit_at TEXT, tp2_hit_at TEXT, tp3_hit_at TEXT, stop_hit_at TEXT, closed_at TEXT, pnl_pct REAL, max_favorable_pct REAL DEFAULT 0, max_adverse_pct REAL DEFAULT 0, result_source TEXT, trade_json TEXT, leverage REAL DEFAULT 1)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS scan_history (id INTEGER PRIMARY KEY AUTOINCREMENT, scanned_at TEXT NOT NULL, symbols_scanned INTEGER DEFAULT 0, signals_found INTEGER DEFAULT 0, scan_duration REAL DEFAULT 0, status TEXT DEFAULT 'OK')""")
        conn.execute("""CREATE TABLE IF NOT EXISTS learning_stats (id INTEGER PRIMARY KEY AUTOINCREMENT, updated_at TEXT NOT NULL, total_trades INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, win_rate REAL DEFAULT 0, expectancy REAL DEFAULT 0, profit_factor REAL DEFAULT 0)""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_outcome ON signals(outcome)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at)")
        conn.commit()
init_db()
@st.cache_data(ttl=60, show_spinner=False)
def get_mexc_contracts():
    payload=mexc_request(MEXC_ENDPOINTS["DETAILS"])
    if not payload: return []
    data=payload.get("data",[])
    if isinstance(data,dict): data=data.get("contracts",[])
    if not isinstance(data,list): return []
    contracts=[]
    for item in data:
        if not isinstance(item,dict): continue
        symbol=item.get("symbol")
        if not symbol: continue
        state=safe_int(item.get("state"),-1)
        if state not in (-1,0): continue
        contracts.append({"symbol":normalize_symbol(symbol),"base_coin":item.get("baseCoin",""),"quote_coin":item.get("quoteCoin",""),"contract_size":safe_float(item.get("contractSize")),"price_unit":safe_float(item.get("priceUnit")),"volume_unit":safe_float(item.get("volUnit")),"max_leverage":safe_float(item.get("maxLeverage")),"state":state})
    return contracts
@st.cache_data(ttl=10, show_spinner=False)
def get_mexc_tickers():
    payload=mexc_request(MEXC_ENDPOINTS["TICKER"])
    if not payload: return []
    data=payload.get("data",[])
    if isinstance(data,dict): data=[data]
    if not isinstance(data,list): return []
    tickers=[]
    for item in data:
        if not isinstance(item,dict): continue
        symbol=item.get("symbol")
        if not symbol: continue
        last_price=safe_float(item.get("lastPrice"))
        if not is_valid_price(last_price): continue
        tickers.append({"symbol":normalize_symbol(symbol),"last_price":last_price,"fair_price":safe_float(item.get("fairPrice")),"index_price":safe_float(item.get("indexPrice")),"bid":safe_float(item.get("bid1")),"ask":safe_float(item.get("ask1")),"volume_24h":safe_float(item.get("volume24")),"amount_24h":safe_float(item.get("amount24")),"change_pct":safe_float(item.get("riseFallRate"))*100,"funding_rate":safe_float(item.get("fundingRate")),"open_interest":safe_float(item.get("holdVol"))})
    return tickers
def get_market_snapshot():
    tickers=get_mexc_tickers()
    if not tickers: return pd.DataFrame()
    frame=pd.DataFrame(tickers)
    if frame.empty: return frame
    frame["symbol"]=frame["symbol"].astype(str)
    frame=frame.drop_duplicates(subset=["symbol"])
    frame=frame.sort_values(by="amount_24h", ascending=False)
    return frame.reset_index(drop=True)
def get_mexc_ticker(symbol):
    symbol=normalize_symbol(symbol); tickers=get_mexc_tickers()
    for ticker in tickers:
        if ticker["symbol"]==symbol: return ticker
    return None
def get_current_futures_price(exchange, symbol):
    if str(exchange).upper()!="MEXC": return None
    ticker=get_mexc_ticker(symbol)
    if not ticker: return None
    price=safe_float(ticker.get("last_price"))
    return price if is_valid_price(price) else None
TIMEFRAME_SECONDS={"1m":60,"5m":300,"15m":900,"30m":1800,"1h":3600,"4h":14400,"8h":28800,"1d":86400,"1w":604800}
MEXC_INTERVALS={"1m":"Min1","5m":"Min5","15m":"Min15","30m":"Min30","1h":"Min60","4h":"Hour4","8h":"Hour8","1d":"Day1","1w":"Week1"}
def get_mexc_klines(symbol, timeframe="15m", limit=300):
    symbol=normalize_symbol(symbol)
    interval=MEXC_INTERVALS.get(timeframe)
    if not interval: return pd.DataFrame()
    seconds=TIMEFRAME_SECONDS.get(timeframe,900)
    limit=clamp(safe_int(limit,300),50,1500)
    end_time=int(time.time()); start_time=end_time-(seconds*limit)
    url=f"{MEXC_ENDPOINTS['KLINE']}/{symbol}"
    payload=mexc_request(url, params={"interval":interval,"start":start_time,"end":end_time})
    if not payload: return pd.DataFrame()
    data=payload.get("data")
    if not isinstance(data,dict): return pd.DataFrame()
    try:
        frame=pd.DataFrame({"timestamp":data.get("time",[]),"open":data.get("open",[]),"high":data.get("high",[]),"low":data.get("low",[]),"close":data.get("close",[]),"volume":data.get("vol",[]),"amount":data.get("amount",[])})
        if frame.empty: return pd.DataFrame()
        for column in ["timestamp","open","high","low","close","volume","amount"]:
            frame[column]=pd.to_numeric(frame[column], errors="coerce")
        frame=frame.dropna(subset=["timestamp","open","high","low","close"])
        # FIX: MEXC sometimes returns ms, sometimes s
        _ts=frame["timestamp"].astype(float)
        _unit="ms" if (len(_ts) and _ts.max()>1e12) else "s"
        frame["timestamp"]=pd.to_datetime(frame["timestamp"], unit=_unit, utc=True)
        frame=frame.sort_values("timestamp"); frame=frame.drop_duplicates(subset=["timestamp"]); frame=frame.reset_index(drop=True)
        return frame
    except (ValueError, TypeError, KeyError) as exc:
        log_event(f"Kline parsing failed for {symbol}: {exc}","warning"); return pd.DataFrame()
def get_current_price(symbol):
    ticker=get_mexc_ticker(symbol)
    if not ticker: return None
    return safe_float(ticker.get("last_price"))
def get_klines(symbol, timeframe="15m", limit=300): return get_mexc_klines(symbol=symbol, timeframe=timeframe, limit=limit)
def get_mexc_orderbook(symbol, limit=20):
    symbol=normalize_symbol(symbol)
    url=f"{MEXC_ENDPOINTS['DEPTH']}/{symbol}"
    payload=mexc_request(url, params={"limit":clamp(safe_int(limit,20),5,50)})
    if not payload: return None
    data=payload.get("data")
    if not isinstance(data,dict): return None
    bids=data.get("bids",[]); asks=data.get("asks",[])
    def parse_levels(levels):
        parsed=[]
        for level in levels or []:
            try:
                price=safe_float(level[0]); quantity=safe_float(level[1])
                if price>0 and quantity>0: parsed.append({"price":price,"quantity":quantity,"value":price*quantity})
            except (IndexError, TypeError, ValueError): continue
        return parsed
    parsed_bids=parse_levels(bids); parsed_asks=parse_levels(asks)
    if not parsed_bids or not parsed_asks: return None
    bid_value=sum(item["value"] for item in parsed_bids); ask_value=sum(item["value"] for item in parsed_asks); total=bid_value+ask_value
    imbalance=((bid_value-ask_value)/total if total>0 else 0)
    return {"bids":parsed_bids,"asks":parsed_asks,"bid_value":bid_value,"ask_value":ask_value,"imbalance":imbalance,"spread":(parsed_asks[0]["price"]-parsed_bids[0]["price"]),"spread_pct":((parsed_asks[0]["price"]-parsed_bids[0]["price"])/parsed_bids[0]["price"])*100 if parsed_bids[0]["price"]>0 else 0}
def get_futures_orderbook(exchange, symbol, limit=20):
    if str(exchange).upper()!="MEXC": return None
    return get_mexc_orderbook(symbol, limit)
def get_mexc_funding_rate(symbol):
    symbol=normalize_symbol(symbol); url=f"{MEXC_ENDPOINTS['FUNDING']}/{symbol}"; payload=mexc_request(url)
    if not payload: return None
    data=payload.get("data")
    if isinstance(data,list): data=data[0] if data else None
    if not isinstance(data,dict): return None
    rate=data.get("fundingRate", data.get("funding_rate"))
    if rate is None: return None
    return safe_float(rate)
def get_mexc_open_interest(symbol):
    symbol=normalize_symbol(symbol); url=f"{MEXC_ENDPOINTS['OPEN_INTEREST']}/{symbol}"; payload=mexc_request(url)
    if not payload: return None
    data=payload.get("data")
    if isinstance(data,list): data=data[0] if data else None
    if isinstance(data,dict):
        value=data.get("holdVol", data.get("openInterest")); return safe_float(value) if value is not None else None
    if isinstance(data,(int,float,str)): return safe_float(data)
    return None
def get_tradeable_universe(min_volume=0, scan_limit=100, exclude_symbols=None):
    exclude_symbols=set(normalize_symbol(item) for item in (exclude_symbols or []))
    snapshot=get_market_snapshot()
    if snapshot.empty: return snapshot
    snapshot=snapshot[snapshot["amount_24h"]>=safe_float(min_volume)]
    snapshot=snapshot[~snapshot["symbol"].isin(exclude_symbols)]
    snapshot=snapshot[snapshot["last_price"]>0]
    snapshot=snapshot.sort_values("amount_24h", ascending=False)
    scan_limit=clamp(safe_int(scan_limit,100),1,500)
    return snapshot.head(scan_limit).reset_index(drop=True)
def get_btc_market_data(timeframe="1h", limit=300): return get_mexc_klines("BTC_USDT", timeframe, limit)
def get_btc_change():
    ticker=get_mexc_ticker("BTC_USDT")
    if not ticker: return None
    return safe_float(ticker.get("change_pct"))
def check_mexc_connection():
    payload=mexc_request(MEXC_ENDPOINTS["TICKER"])
    if not payload: return {"connected":False,"exchange":"MEXC","message":"MEXC API unavailable","checked_at":utc_iso()}
    data=payload.get("data",[])
    valid=(isinstance(data,list) and len(data)>0) or isinstance(data,dict)
    return {"connected":bool(valid),"exchange":"MEXC","message":("Public Futures API responding" if valid else "Unexpected API response"),"checked_at":utc_iso()}
def clear_market_cache():
    try: get_mexc_contracts.clear(); get_mexc_tickers.clear()
    except Exception as exc: log_event(f"Cache clear warning: {exc}","warning")

def add_indicators(frame):
    if frame is None or frame.empty: return pd.DataFrame()
    df=frame.copy()
    required=["open","high","low","close","volume"]
    if not all(c in df.columns for c in required): return pd.DataFrame()
    for c in required: df[c]=pd.to_numeric(df[c], errors="coerce")
    df=df.dropna(subset=required).reset_index(drop=True)
    if len(df)<30: return pd.DataFrame()
    close=df["close"]; high=df["high"]; low=df["low"]; volume=df["volume"]
    df["ema9"]=close.ewm(span=9, adjust=False).mean(); df["ema21"]=close.ewm(span=21, adjust=False).mean(); df["ema50"]=close.ewm(span=50, adjust=False).mean(); df["ema200"]=close.ewm(span=200, adjust=False).mean()
    delta=close.diff(); gain=delta.clip(lower=0); loss=-delta.clip(upper=0)
    avg_gain=gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean(); avg_loss=loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs=avg_gain/avg_loss.replace(0,float("nan")); df["rsi"]=100-(100/(1+rs)); df["rsi"]=df["rsi"].fillna(50)
    ema12=close.ewm(span=12, adjust=False).mean(); ema26=close.ewm(span=26, adjust=False).mean()
    df["macd"]=ema12-ema26; df["macd_signal"]=df["macd"].ewm(span=9, adjust=False).mean(); df["macd_hist"]=df["macd"]-df["macd_signal"]
    prev_close=close.shift(1)
    tr=pd.concat([high-low,(high-prev_close).abs(),(low-prev_close).abs()], axis=1).max(axis=1)
    df["tr"]=tr; df["atr"]=tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean(); df["atr_pct"]=(df["atr"]/close.replace(0,float("nan")))*100
    df["momentum"]=close.pct_change(10)*100; df["momentum_3"]=close.pct_change(3)*100
    df["volume_sma20"]=volume.rolling(20, min_periods=5).mean(); df["volume_ratio"]=(volume/df["volume_sma20"].replace(0,float("nan"))).fillna(1)
    typical=(high+low+close)/3; cumvol=volume.cumsum(); df["vwap"]=((typical*volume).cumsum()/cumvol.replace(0,float("nan")))
    df["bb_mid"]=close.rolling(20).mean(); bb_std=close.rolling(20).std(); df["bb_upper"]=df["bb_mid"]+(2*bb_std); df["bb_lower"]=df["bb_mid"]-(2*bb_std); df["bb_width"]=((df["bb_upper"]-df["bb_lower"])/df["bb_mid"].replace(0,float("nan")))*100
    candle_range=(high-low).replace(0,float("nan"))
    df["body_pct"]=((close-df["open"]).abs()/candle_range).fillna(0)
    df["upper_wick_pct"]=((high-df[["open","close"]].max(axis=1))/candle_range).fillna(0)
    df["lower_wick_pct"]=((df[["open","close"]].min(axis=1)-low)/candle_range).fillna(0)
    df["bullish"]=close>df["open"]; df["bearish"]=close<df["open"]
    df["trend_bull"]=((df["ema9"]>df["ema21"])&(df["ema21"]>df["ema50"])); df["trend_bear"]=((df["ema9"]<df["ema21"])&(df["ema21"]<df["ema50"]))
    return df.replace([float("inf"),-float("inf")], float("nan"))
def get_market_structure(frame, lookback=30):
    if frame is None or len(frame)<lookback: return {}
    df=frame.tail(lookback).copy(); current=df.iloc[-1]
    recent_high=safe_float(df["high"].iloc[:-1].max()); recent_low=safe_float(df["low"].iloc[:-1].min()); close=safe_float(current["close"])
    prev_high=safe_float(df["high"].iloc[-2]); prev_low=safe_float(df["low"].iloc[-2])
    return {"recent_high":recent_high,"recent_low":recent_low,"bullish_break":close>recent_high,"bearish_break":close<recent_low,"bullish_bos":(close>prev_high and safe_float(current["ema9"])>safe_float(current["ema21"])),"bearish_bos":(close<prev_low and safe_float(current["ema9"])<safe_float(current["ema21"])),"range_pct":((recent_high-recent_low)/close*100 if close>0 else 0)}
def detect_fvg(frame, lookback=20):
    result={"bullish_fvg":False,"bearish_fvg":False,"bullish_gap_low":None,"bullish_gap_high":None,"bearish_gap_low":None,"bearish_gap_high":None}
    if frame is None or len(frame)<3: return result
    df=frame.tail(lookback).reset_index(drop=True)
    for i in range(2,len(df)):
        c1=df.iloc[i-2]; c3=df.iloc[i]
        if safe_float(c3["low"])>safe_float(c1["high"]): result.update({"bullish_fvg":True,"bullish_gap_low":safe_float(c1["high"]),"bullish_gap_high":safe_float(c3["low"])})
        if safe_float(c3["high"])<safe_float(c1["low"]): result.update({"bearish_fvg":True,"bearish_gap_low":safe_float(c3["high"]),"bearish_gap_high":safe_float(c1["low"])})
    return result
def detect_order_blocks(frame, lookback=30):
    result={"bullish_ob":None,"bearish_ob":None}
    if frame is None or len(frame)<5: return result
    df=frame.tail(lookback).reset_index(drop=True)
    for i in range(1,len(df)-1):
        prev=df.iloc[i-1]; cur=df.iloc[i]; nxt=df.iloc[i+1]
        atr=safe_float(nxt.get("atr",0))
        if atr<=0: continue
        if safe_float(prev["close"])<safe_float(prev["open"]) and safe_float(nxt["close"])>safe_float(cur["high"]) and safe_float(nxt["close"])-safe_float(cur["high"])>atr*0.3:
            result["bullish_ob"]={"low":safe_float(prev["low"]),"high":safe_float(prev["open"])}
        if safe_float(prev["close"])>safe_float(prev["open"]) and safe_float(nxt["close"])<safe_float(cur["low"]) and safe_float(cur["low"])-safe_float(nxt["close"])>atr*0.3:
            result["bearish_ob"]={"low":safe_float(prev["open"]),"high":safe_float(prev["high"])}
    return result
def detect_liquidity_sweep(frame, lookback=20):
    result={"bullish_sweep":False,"bearish_sweep":False,"swept_high":None,"swept_low":None}
    if frame is None or len(frame)<lookback+2: return result
    prev=frame.iloc[-lookback-1:-1]; cur=frame.iloc[-1]
    ph=safe_float(prev["high"].max()); pl=safe_float(prev["low"].min()); ch=safe_float(cur["high"]); cl=safe_float(cur["low"]); cc=safe_float(cur["close"])
    if ch>ph and cc<ph: result["bearish_sweep"]=True; result["swept_high"]=ph
    if cl<pl and cc>pl: result["bullish_sweep"]=True; result["swept_low"]=pl
    return result
def get_cvd_proxy(frame, lookback=20):
    if frame is None or len(frame)<3: return {"value":0.0,"normalized":0.0,"method":"UNAVAILABLE"}
    df=frame.tail(lookback).copy()
    direction=(df["close"]-df["open"]); rng=(df["high"]-df["low"]).replace(0,float("nan"))
    est=(direction/rng).fillna(0)*df["volume"]; delta_sum=safe_float(est.sum()); total=safe_float(df["volume"].sum())
    norm=(delta_sum/total if total>0 else 0)
    return {"value":delta_sum,"normalized":clamp(norm,-1,1),"method":"CANDLE_VOLUME_PROXY"}
def get_real_cvd(exchange, symbol, timeframe="5m"):
    if str(exchange).upper()!="MEXC": return None
    frame=get_mexc_klines(symbol, timeframe, 100)
    if frame.empty: return None
    proxy=get_cvd_proxy(frame)
    return {"value":proxy["value"],"normalized":proxy["normalized"],"method":proxy["method"],"is_real_trade_cvd":False}
def detect_volume_anomaly(frame):
    if frame is None or len(frame)<25: return {"ratio":1.0,"spike":False,"drying":False}
    ratio=safe_float(frame.iloc[-1].get("volume_ratio",1))
    return {"ratio":ratio,"spike":ratio>=2.0,"strong_spike":ratio>=3.0,"drying":ratio<=0.55}
def detect_volatility_regime(frame):
    if frame is None or frame.empty: return "UNKNOWN"
    atr_pct=safe_float(frame.iloc[-1].get("atr_pct",0))
    if atr_pct>=5: return "EXTREME"
    if atr_pct>=2.5: return "HIGH"
    if atr_pct>=0.8: return "NORMAL"
    return "LOW"
def classify_trend(frame):
    if frame is None or len(frame)<30: return "UNKNOWN"
    cur=frame.iloc[-1]; close=safe_float(cur["close"]); ema9=safe_float(cur["ema9"]); ema21=safe_float(cur["ema21"]); ema50=safe_float(cur["ema50"]); mom=safe_float(cur["momentum"])
    if close>ema9>ema21>ema50 and mom>0: return "STRONG_BULLISH"
    if close<ema9<ema21<ema50 and mom<0: return "STRONG_BEARISH"
    if close>ema50: return "BULLISH"
    if close<ema50: return "BEARISH"
    return "SIDEWAYS"
def get_multi_timeframe_trend(symbol):
    result={}
    for tf in ["15m","1h","4h","1d"]:
        raw=get_mexc_klines(symbol, tf, 250)
        if raw.empty: result[tf]="UNKNOWN"; continue
        analyzed=add_indicators(raw)
        if analyzed.empty: result[tf]="UNKNOWN"; continue
        result[tf]=classify_trend(analyzed)
    return result
def extract_market_features(symbol, timeframe="15m"):
    raw=get_mexc_klines(symbol, timeframe, 300)
    if raw.empty: return None
    frame=add_indicators(raw)
    if frame.empty: return None
    cur=frame.iloc[-1]
    return {"symbol":normalize_symbol(symbol),"timeframe":timeframe,"frame":frame,"price":safe_float(cur["close"]),"ema9":safe_float(cur["ema9"]),"ema21":safe_float(cur["ema21"]),"ema50":safe_float(cur["ema50"]),"ema200":safe_float(cur["ema200"]),"rsi":safe_float(cur["rsi"]),"macd":safe_float(cur["macd"]),"macd_signal":safe_float(cur["macd_signal"]),"macd_hist":safe_float(cur["macd_hist"]),"atr":safe_float(cur["atr"]),"atr_pct":safe_float(cur["atr_pct"]),"momentum":safe_float(cur["momentum"]),"momentum_3":safe_float(cur["momentum_3"]),"volume_ratio":safe_float(cur["volume_ratio"]),"vwap":safe_float(cur["vwap"]),"trend":classify_trend(frame),"volatility":detect_volatility_regime(frame),"structure":get_market_structure(frame),"fvg":detect_fvg(frame),"order_blocks":detect_order_blocks(frame),"sweeps":detect_liquidity_sweep(frame),"volume":detect_volume_anomaly(frame),"cvd":get_cvd_proxy(frame),"last_candle_time":str(cur.get("timestamp",""))}

def learning_profile():
    try:
        with sqlite3.connect(DB_PATH) as conn: df=pd.read_sql_query("SELECT outcome, pnl_pct FROM signals WHERE outcome IN ('WIN','LOSS')", conn)
        if df.empty: return {"total":0,"wins":0,"losses":0,"win_rate":0.0,"expectancy":0.0,"adjustment":0}
        wins=df[df["outcome"]=="WIN"]; losses=df[df["outcome"]=="LOSS"]; total=len(df); win_rate=len(wins)/total*100; expectancy=safe_float(df["pnl_pct"].fillna(0).mean()); adjustment=0
        if total>=10:
            if win_rate>=65 and expectancy>0: adjustment=5
            elif win_rate>=55 and expectancy>0: adjustment=2
            elif win_rate<40 or expectancy<0: adjustment=-5
        return {"total":total,"wins":len(wins),"losses":len(losses),"win_rate":win_rate,"expectancy":expectancy,"adjustment":adjustment}
    except Exception as exc:
        log_event(f"Learning profile error: {exc}","error"); return {"total":0,"wins":0,"losses":0,"win_rate":0.0,"expectancy":0.0,"adjustment":0}
def btc_direction_filter(side):
    frame=get_mexc_klines("BTC_USDT","1h",250)
    if frame.empty: return {"allowed":True,"reason":"BTC data unavailable","trend":"UNKNOWN"}
    analyzed=add_indicators(frame)
    if analyzed.empty: return {"allowed":True,"reason":"BTC indicators unavailable","trend":"UNKNOWN"}
    trend=classify_trend(analyzed)
    if side=="LONG" and trend=="STRONG_BEARISH": return {"allowed":False,"reason":"BTC hourly trend strongly bearish","trend":trend}
    if side=="SHORT" and trend=="STRONG_BULLISH": return {"allowed":False,"reason":"BTC hourly trend strongly bullish","trend":trend}
    return {"allowed":True,"reason":"BTC filter passed","trend":trend}
def get_derivatives_features(symbol):
    ticker=get_mexc_ticker(symbol); funding=get_mexc_funding_rate(symbol); oi=get_mexc_open_interest(symbol)
    return {"funding_rate":(funding if funding is not None else safe_float(ticker.get("funding_rate",0) if ticker else 0)),"open_interest":(oi if oi is not None else safe_float(ticker.get("open_interest",0) if ticker else 0)),"funding_available":funding is not None,"oi_available":oi is not None}
def calculate_signal_score(features, side, mtf=None, orderbook=None, derivatives=None):
    mtf=mtf or {}; derivatives=derivatives or {}; score=0; reasons=[]; warnings=[]
    price=features["price"]; rsi=features["rsi"]; momentum=features["momentum"]; volume_ratio=features["volume_ratio"]
    structure=features["structure"]; sweeps=features["sweeps"]; fvg=features["fvg"]
    if side=="LONG":
        if features["ema9"]>features["ema21"]: score+=8; reasons.append("EMA 9 فوق EMA 21")
        if features["ema21"]>features["ema50"]: score+=8; reasons.append("الاتجاه المتوسط صاعد")
        if features["macd_hist"]>0: score+=7; reasons.append("MACD إيجابي")
        if 35 <= rsi <= 75: score+=6; reasons.append("RSI يدعم الصعود")  # FIX was 45-68
        if momentum>0: score+=5; reasons.append("الزخم إيجابي")
        if sweeps["bullish_sweep"]: score+=12; reasons.append("سحب سيولة أسفل القيعان")
        if structure["bullish_bos"]: score+=10; reasons.append("اختراق هيكل صاعد")
        if fvg["bullish_fvg"]: score+=5; reasons.append("وجود فجوة سعرية صاعدة")
        if features["cvd"]["normalized"]>0.12: score+=6; reasons.append("دلتا حجم تقديرية إيجابية")
        if price>features["vwap"]: score+=4; reasons.append("السعر أعلى VWAP")
    else:
        if features["ema9"]<features["ema21"]: score+=8; reasons.append("EMA 9 تحت EMA 21")
        if features["ema21"]<features["ema50"]: score+=8; reasons.append("الاتجاه المتوسط هابط")
        if features["macd_hist"]<0: score+=7; reasons.append("MACD سلبي")
        if 25 <= rsi <= 65: score+=6; reasons.append("RSI يدعم الهبوط")  # FIX was 32-55
        if momentum<0: score+=5; reasons.append("الزخم سلبي")
        if sweeps["bearish_sweep"]: score+=12; reasons.append("سحب سيولة أعلى القمم")
        if structure["bearish_bos"]: score+=10; reasons.append("كسر هيكل هابط")
        if fvg["bearish_fvg"]: score+=5; reasons.append("وجود فجوة سعرية هابطة")
        if features["cvd"]["normalized"]<-0.12: score+=6; reasons.append("دلتا حجم تقديرية سلبية")
        if price<features["vwap"]: score+=4; reasons.append("السعر أسفل VWAP")
    if volume_ratio>=2: score+=7; reasons.append("ارتفاع ملحوظ في حجم التداول")
    elif volume_ratio<0.6: score-=2; warnings.append("حجم التداول ضعيف")  # FIX was -5
    if orderbook:
        imb=safe_float(orderbook.get("imbalance"))
        if side=="LONG" and imb>0.15: score+=6; reasons.append("تفوق سيولة الشراء في دفتر الأوامر")
        elif side=="SHORT" and imb<-0.15: score+=6; reasons.append("تفوق سيولة البيع في دفتر الأوامر")
    else: warnings.append("بيانات دفتر الأوامر غير متاحة")
    funding=safe_float(derivatives.get("funding_rate"))
    if side=="LONG" and funding>0.001: score-=3; warnings.append("تمويل مرتفع نسبيًا ضد دخول لونج")
    if side=="SHORT" and funding<-0.001: score-=3; warnings.append("تمويل سلبي مرتفع نسبيًا ضد دخول شورت")
    trend_weights={"STRONG_BULLISH":1,"BULLISH":1,"STRONG_BEARISH":-1,"BEARISH":-1,"SIDEWAYS":0,"UNKNOWN":0}
    for tf in ["1h","4h","1d"]:
        trend=mtf.get(tf,"UNKNOWN"); direction=trend_weights.get(trend,0)
        if side=="LONG" and direction==1: score+=5; reasons.append(f"توافق الاتجاه على {tf}")
        elif side=="SHORT" and direction==-1: score+=5; reasons.append(f"توافق الاتجاه على {tf}")
        elif side=="LONG" and direction==-1: score-=3; warnings.append(f"الاتجاه الأكبر يعارض اللونج على {tf}")  # FIX was -7
        elif side=="SHORT" and direction==1: score-=3; warnings.append(f"الاتجاه الأكبر يعارض الشورت على {tf}")  # FIX was -7
    learning=learning_profile()
    if st.session_state.get("learning_enabled",True): score+=learning["adjustment"]
    score=int(clamp(score,0,100))
    return {"score":score,"reasons":reasons,"warnings":warnings}
def calculate_trade_levels(price, atr, side, minimum_rr=1.8):
    price=safe_float(price); atr=safe_float(atr)
    if price<=0 or atr<=0: return None
    atr_distance=max(atr*1.5, price*0.003)
    if side=="LONG":
        entry=price; stop=entry-atr_distance; risk=entry-stop; tp1=entry+risk*1.5; tp2=entry+risk*2.5; tp3=entry+risk*4.0
    else:
        entry=price; stop=entry+atr_distance; risk=stop-entry; tp1=entry-risk*1.5; tp2=entry-risk*2.5; tp3=entry-risk*4.0
    reward=abs(tp2-entry); rr=(reward/risk if risk>0 else 0)
    if rr<minimum_rr: return None
    return {"entry":entry,"stop":stop,"tp1":tp1,"tp2":tp2,"tp3":tp3,"risk_pct":risk/entry*100,"rr":rr}
def analyze(frame, symbol, settings, exchange="MEXC"):
    if str(exchange).upper()!="MEXC": return None
    if frame is None or frame.empty: return None
    if len(frame)<50: return None
    symbol=normalize_symbol(symbol)
    analyzed=add_indicators(frame)
    if analyzed.empty: return None
    current=analyzed.iloc[-1]; price=safe_float(current["close"]); atr=safe_float(current["atr"])
    if not is_valid_price(price) or atr<=0: return None
    change=safe_float(current["momentum_3"])
    if abs(change)>=30: return None  # FIX was 12
    features=extract_market_features(symbol, settings.get("timeframe","15m"))
    if not features: return None
    mtf=get_multi_timeframe_trend(symbol); orderbook=get_mexc_orderbook(symbol,20); derivatives=get_derivatives_features(symbol)
    candidates=[]
    if settings.get("enable_long",True): candidates.append("LONG")
    if settings.get("enable_short",True): candidates.append("SHORT")
    best_signal=None
    for side in candidates:
        score_data=calculate_signal_score(features, side, mtf, orderbook, derivatives); score=score_data["score"]
        minimum_score=safe_int(settings.get("min_score",75),75)
        if score<minimum_score: continue
        if settings.get("btc_filter",True):
            btc_filter=btc_direction_filter(side)
            if not btc_filter["allowed"]: continue
        levels=calculate_trade_levels(price, atr, side, safe_float(settings.get("minimum_rr",1.8)))
        if not levels: continue
        signal={"exchange":"MEXC","symbol":symbol,"side":side,"timeframe":settings.get("timeframe","15m"),"score":score,"price":price,"entry":levels["entry"],"stop":levels["stop"],"tp1":levels["tp1"],"tp2":levels["tp2"],"tp3":levels["tp3"],"risk_pct":levels["risk_pct"],"rr":levels["rr"],"atr":atr,"rsi":features["rsi"],"volume_ratio":features["volume_ratio"],"momentum":features["momentum"],"funding_pct":derivatives["funding_rate"]*100,"oi_change_pct":0,"cvd_proxy":features["cvd"]["normalized"],"mtf":mtf,"reasons":score_data["reasons"],"warnings":score_data["warnings"],"created_at":utc_iso(),"status":"ENTRY_PENDING","outcome":"OPEN"}
        if best_signal is None or signal["score"]>best_signal["score"]: best_signal=signal
    return best_signal
def scan_symbol(symbol, timeframe="15m", settings=None):
    settings=settings or {}; frame=get_mexc_klines(symbol, timeframe, 300)
    if frame.empty: return None
    local_settings=dict(settings); local_settings["timeframe"]=timeframe
    return analyze(frame, symbol, local_settings, exchange="MEXC")
def scan_market(settings=None):
    settings=settings or {}; start=time.time()
    scan_limit=safe_int(settings.get("scan_limit",100),100)
    universe=get_tradeable_universe(min_volume=settings.get("min_volume",0), scan_limit=scan_limit)
    signals=[]
    if universe.empty: return {"signals":[],"scanned":0,"duration":0,"status":"NO_MARKET_DATA"}
    timeframe=settings.get("timeframe","15m")
    for _, row in universe.iterrows():
        symbol=row["symbol"]
        try:
            signal=scan_symbol(symbol, timeframe, settings)
            if signal: signals.append(signal)
        except Exception as exc: log_event(f"Scan failed {symbol}: {exc}","warning")
    signals.sort(key=lambda item: item["score"], reverse=True)
    duration=time.time()-start
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO scan_history (scanned_at, symbols_scanned, signals_found, scan_duration, status) VALUES (?,?,?,?,?)",(utc_iso(),len(universe),len(signals),duration,"OK")); conn.commit()
    except Exception as exc: log_event(f"Scan history error: {exc}","warning")
    return {"signals":signals,"scanned":len(universe),"duration":duration,"status":"OK"}
def save_signal(signal):
    if not signal: return None
    symbol=normalize_symbol(signal["symbol"]); side=signal["side"]
    try:
        with sqlite3.connect(DB_PATH) as conn:
            duplicate=conn.execute("SELECT id FROM signals WHERE symbol=? AND side=? AND outcome='OPEN' AND created_at>=? ORDER BY id DESC LIMIT 1",(symbol,side,datetime.fromtimestamp(time.time()-1200, timezone.utc).isoformat())).fetchone()
            if duplicate: return duplicate[0]
            cursor=conn.execute("INSERT INTO signals (created_at, exchange, symbol, side, timeframe, score, price, entry, stop, tp1, tp2, tp3, change_pct, volume_ratio, cvd_proxy, funding_pct, oi_change_pct, outcome, status, last_price, trade_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(signal.get("created_at",utc_iso()),"MEXC",symbol,side,signal.get("timeframe","15m"),safe_int(signal.get("score")),safe_float(signal.get("price")),safe_float(signal.get("entry")),safe_float(signal.get("stop")),safe_float(signal.get("tp1")),safe_float(signal.get("tp2")),safe_float(signal.get("tp3")),safe_float(signal.get("momentum")),safe_float(signal.get("volume_ratio")),safe_float(signal.get("cvd_proxy")),safe_float(signal.get("funding_pct")),safe_float(signal.get("oi_change_pct")),"OPEN","ENTRY_PENDING",safe_float(signal.get("price")),json.dumps(signal, ensure_ascii=False, default=str)))
            conn.commit(); return cursor.lastrowid
    except Exception as exc: log_event(f"Save signal error: {exc}","error"); return None
def save_signals(signals):
    saved=[]
    for signal in signals or []:
        sid=save_signal(signal)
        if sid is not None: saved.append({"id":sid,"signal":signal})
    return saved
def calculate_trade_pnl(side, entry, price):
    entry=safe_float(entry); price=safe_float(price)
    if entry<=0 or price<=0: return 0.0
    if side=="LONG": return ((price-entry)/entry)*100
    return ((entry-price)/entry)*100
def update_trade_record(trade_id, price):
    price=safe_float(price)
    if price<=0: return None
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory=sqlite3.Row
            row=conn.execute("SELECT * FROM signals WHERE id=? AND outcome='OPEN'",(trade_id,)).fetchone()
            if not row: return None
            trade=dict(row); side=trade["side"]; entry=safe_float(trade["entry"]); stop=safe_float(trade["stop"]); tp1=safe_float(trade["tp1"]); tp2=safe_float(trade["tp2"]); tp3=safe_float(trade["tp3"])
            if entry<=0: return None
            prev_status=trade["status"]; pnl=calculate_trade_pnl(side, entry, price)
            max_fav=max(safe_float(trade["max_favorable_pct"]),pnl); max_adv=min(safe_float(trade["max_adverse_pct"]),pnl)
            status=prev_status; outcome="OPEN"; tp1_hit=trade["tp1_hit_at"]; tp2_hit=trade["tp2_hit_at"]; tp3_hit=trade["tp3_hit_at"]; stop_hit=trade["stop_hit_at"]; entry_hit=trade["entry_hit_at"]; ts=utc_iso()
            entry_reached=(price<=entry if side=="LONG" else price>=entry)
            if not entry_hit and entry_reached: entry_hit=ts; status="IN_POSITION"
            stop_reached=(price<=stop if side=="LONG" else price>=stop)
            if entry_hit and stop_reached:
                status="STOP_LOSS"; outcome="LOSS"; stop_hit=ts; pnl=calculate_trade_pnl(side, entry, stop)
            elif entry_hit:
                if side=="LONG":
                    if price>=tp3: status="TP3"; outcome="WIN"; tp1_hit=tp1_hit or ts; tp2_hit=tp2_hit or ts; tp3_hit=ts
                    elif price>=tp2: status="TP2"; tp1_hit=tp1_hit or ts; tp2_hit=ts
                    elif price>=tp1: status="TP1"; tp1_hit=ts
                else:
                    if price<=tp3: status="TP3"; outcome="WIN"; tp1_hit=tp1_hit or ts; tp2_hit=tp2_hit or ts; tp3_hit=ts
                    elif price<=tp2: status="TP2"; tp1_hit=tp1_hit or ts; tp2_hit=ts
                    elif price<=tp1: status="TP1"; tp1_hit=ts
            closed_at=(ts if outcome!="OPEN" else None)
            conn.execute("UPDATE signals SET status=?, outcome=?, last_price=?, last_checked_at=?, entry_hit_at=?, tp1_hit_at=?, tp2_hit_at=?, tp3_hit_at=?, stop_hit_at=?, closed_at=COALESCE(?, closed_at), pnl_pct=?, max_favorable_pct=?, max_adverse_pct=? WHERE id=?",(status,outcome,price,ts,entry_hit,tp1_hit,tp2_hit,tp3_hit,stop_hit,closed_at,pnl if outcome!="OPEN" else None,max_fav,max_adv,trade_id))
            conn.commit(); return {"id":trade_id,"symbol":trade["symbol"],"side":side,"status":status,"outcome":outcome,"pnl_pct":pnl,"last_price":price}
    except Exception as exc: log_event(f"Trade update error {trade_id}: {exc}","error"); return None
def track_open_trades():
    try:
        with sqlite3.connect(DB_PATH) as conn: rows=conn.execute("SELECT id, symbol FROM signals WHERE outcome='OPEN'").fetchall()
        updates=[]
        for tid, sym in rows:
            price=get_current_price(sym)
            if not price: continue
            r=update_trade_record(tid, price)
            if r: updates.append(r)
        return updates
    except Exception as exc: log_event(f"Tracking error: {exc}","error"); return []
def verify_trade_with_candles(trade_id, timeframe="1m"):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory=sqlite3.Row
            row=conn.execute("SELECT * FROM signals WHERE id=? AND outcome='OPEN'",(trade_id,)).fetchone()
            if not row: return None
            trade=dict(row)
        frame=get_mexc_klines(trade["symbol"], timeframe, 5)
        if frame.empty: return None
        candle=frame.iloc[-1]; high=safe_float(candle["high"]); low=safe_float(candle["low"]); side=trade["side"]
        entry=safe_float(trade["entry"]); stop=safe_float(trade["stop"]); tp1=safe_float(trade["tp1"]); tp2=safe_float(trade["tp2"]); tp3=safe_float(trade["tp3"])
        if side=="LONG": stop_hit=low<=stop; tp1_hit=high>=tp1; tp2_hit=high>=tp2; tp3_hit=high>=tp3; entry_hit=low<=entry
        else: stop_hit=high>=stop; tp1_hit=low<=tp1; tp2_hit=low<=tp2; tp3_hit=low<=tp3; entry_hit=high>=entry
        if entry_hit and stop_hit: return update_trade_record(trade_id, stop)
        if not entry_hit: return None
        if tp3_hit: price=tp3
        elif tp2_hit: price=tp2
        elif tp1_hit: price=tp1
        else: price=safe_float(candle["close"])
        return update_trade_record(trade_id, price)
    except Exception as exc: log_event(f"OHLC verification error: {exc}","warning"); return None
def get_performance_stats():
    try:
        with sqlite3.connect(DB_PATH) as conn: df=pd.read_sql_query("SELECT * FROM signals", conn)
        if df.empty: return {"total":0,"open":0,"wins":0,"losses":0,"win_rate":0,"expectancy":0,"profit_factor":0}
        closed=df[df["outcome"].isin(["WIN","LOSS"])]; wins=closed[closed["outcome"]=="WIN"]; losses=closed[closed["outcome"]=="LOSS"]
        win_rate=(len(wins)/len(closed)*100 if len(closed) else 0); win_sum=safe_float(wins["pnl_pct"].fillna(0).sum()); loss_sum=abs(safe_float(losses["pnl_pct"].fillna(0).sum()))
        profit_factor=(win_sum/loss_sum if loss_sum>0 else 0); expectancy=(safe_float(closed["pnl_pct"].fillna(0).mean()) if len(closed) else 0)
        return {"total":len(df),"open":len(df[df["outcome"]=="OPEN"]),"wins":len(wins),"losses":len(losses),"win_rate":win_rate,"expectancy":expectancy,"profit_factor":profit_factor}
    except Exception as exc: log_event(f"Performance stats error: {exc}","error"); return {"total":0,"open":0,"wins":0,"losses":0,"win_rate":0,"expectancy":0,"profit_factor":0}
def save_learning_snapshot():
    stats=get_performance_stats()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO learning_stats (updated_at, total_trades, wins, losses, win_rate, expectancy, profit_factor) VALUES (?,?,?,?,?,?,?)",(utc_iso(),stats["total"],stats["wins"],stats["losses"],stats["win_rate"],stats["expectancy"],stats["profit_factor"])); conn.commit()
        return stats
    except Exception as exc: log_event(f"Learning snapshot error: {exc}","warning"); return stats
def get_open_signals():
    try:
        with sqlite3.connect(DB_PATH) as conn: return pd.read_sql_query("SELECT * FROM signals WHERE outcome='OPEN' ORDER BY created_at DESC", conn)
    except Exception: return pd.DataFrame()
def get_recent_signals(limit=100):
    try:
        with sqlite3.connect(DB_PATH) as conn: return pd.read_sql_query("SELECT * FROM signals ORDER BY id DESC LIMIT ?",(safe_int(limit,100),), conn)
    except Exception: return pd.DataFrame()

def get_secret(name, default=""):
    try:
        v=st.secrets.get(name, default)
        if v: return str(v)
    except Exception: pass
    return os.getenv(name, default)
def get_telegram_config():
    token=get_secret("TELEGRAM_BOT_TOKEN"); chat_id=(get_secret("TELEGRAM_CHANNEL_ID") or get_secret("TELEGRAM_CHAT_ID"))
    return {"token":token,"chat_id":chat_id,"ready":bool(token and chat_id)}
def send_telegram(message):
    config=get_telegram_config()
    if not config["ready"]: log_event("Telegram credentials are not configured","warning"); return False
    url=f"https://api.telegram.org/bot{config['token']}/sendMessage"
    try:
        resp=SESSION.post(url, json={"chat_id":config["chat_id"],"text":message,"parse_mode":"HTML","disable_web_page_preview":True}, timeout=TIMEOUT)
        resp.raise_for_status(); payload=resp.json(); return bool(payload.get("ok"))
    except Exception as exc: log_event(f"Telegram send failed: {exc}","error"); return False
def format_telegram(signal):
    side=signal["side"]; icon=("🟢" if side=="LONG" else "🔴")
    reasons=signal.get("reasons",[]); warnings=signal.get("warnings",[])
    reason_text="\n".join(f"• {x}" for x in reasons[:8]); warning_text="\n".join(f"⚠️ {x}" for x in warnings[:4])
    return (f"💎 <b>BLY7TRADER ULTIMATE</b>\n━━━━━━━━━━━━━━━━━━\n{icon} <b>{side} | {signal['symbol']}</b>\n🏦 Exchange: <b>MEXC Futures</b>\n⏱ Timeframe: <b>{signal['timeframe']}</b>\n⭐ Score: <b>{signal['score']}/100</b>\n━━━━━━━━━━━━━━━━━━\n📍 Entry: <code>{signal['entry']:.10g}</code>\n🛑 Stop Loss: <code>{signal['stop']:.10g}</code>\n🎯 TP1: <code>{signal['tp1']:.10g}</code>\n🎯 TP2: <code>{signal['tp2']:.10g}</code>\n🎯 TP3: <code>{signal['tp3']:.10g}</code>\n━━━━━━━━━━━━━━━━━━\n📊 RSI: <b>{signal['rsi']:.2f}</b>\n📈 Volume Ratio: <b>{signal['volume_ratio']:.2f}x</b>\n📐 Risk: <b>{signal['risk_pct']:.2f}%</b>\n⚖️ Risk/Reward: <b>1:{signal['rr']:.2f}</b>\n━━━━━━━━━━━━━━━━━━\n🧠 <b>Analysis</b>\n{reason_text or 'No additional reasons'}\n{warning_text}\n━━━━━━━━━━━━━━━━━━\n📡 <b>TRADE WITH BLY7 TRADER</b>\n🔔 <a href='https://t.me/bly7trader'>Telegram Channel</a>\n⚠️ Risk management is essential.")
def cornix_signal_text(signal, exchange="MEXC", timeframe="15m", leverage=1):
    side=signal["side"]; direction=("LONG" if side=="LONG" else "SHORT")
    return (f"{direction} {signal['symbol']}\nEntry: {signal['entry']:.10g}\nStop: {signal['stop']:.10g}\nTargets:\nTP1: {signal['tp1']:.10g}\nTP2: {signal['tp2']:.10g}\nTP3: {signal['tp3']:.10g}\nLeverage: {leverage}x\nExchange: {exchange}\nTimeframe: {timeframe}\nSignal Score: {signal['score']}/100")
def send_signal_batch(saved_signals):
    results=[]
    for item in saved_signals or []:
        signal=item["signal"]; sent=send_telegram(format_telegram(signal)); results.append({"id":item["id"],"symbol":signal["symbol"],"sent":sent})
    return results
def send_trade_update(update):
    if not update: return False
    msg=("💎 <b>BLY7TRADER UPDATE</b>\n━━━━━━━━━━━━━━━━━━\n🪙 <b>"+update['symbol']+"</b>\nDirection: <b>"+update['side']+"</b>\nStatus: <b>"+update['status']+"</b>\nPrice: <code>"+f"{update['last_price']:.10g}"+"</code>\nPnL: <b>"+f"{update['pnl_pct']:.2f}%"+"</b>\n━━━━━━━━━━━━━━━━━━")
    return send_telegram(msg)
def initialize_session():
    defaults={"min_score":75,"scan_limit":100,"timeframe":"15m","enable_long":True,"enable_short":True,"btc_filter":True,"learning_enabled":True,"telegram_enabled":True,"minimum_rr":1.8,"risk_percent":1.0,"last_scan":None,"last_scan_result":None,"auto_refresh":False}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
initialize_session()
def render_sidebar():
    st.sidebar.markdown("## 💎 BLY7TRADER"); st.sidebar.caption("MEXC Futures Intelligence"); st.sidebar.markdown("---"); st.sidebar.markdown("### Scan Settings")
    st.session_state.min_score=st.sidebar.slider("Minimum Signal Score", min_value=50, max_value=95, value=st.session_state.min_score, step=5)
    st.session_state.scan_limit=st.sidebar.select_slider("Contracts to Scan", options=[20,40,60,80,100,150,200], value=st.session_state.scan_limit)
    st.session_state.timeframe=st.sidebar.selectbox("Main Timeframe", options=["5m","15m","30m","1h","4h","1d"], index=["5m","15m","30m","1h","4h","1d"].index(st.session_state.timeframe))
    st.sidebar.markdown("### Signal Direction")
    st.session_state.enable_long=st.sidebar.checkbox("Enable LONG", value=st.session_state.enable_long)
    st.session_state.enable_short=st.sidebar.checkbox("Enable SHORT", value=st.session_state.enable_short)
    st.sidebar.markdown("### Intelligence Filters")
    st.session_state.btc_filter=st.sidebar.checkbox("BTC Direction Filter", value=st.session_state.btc_filter)
    st.session_state.learning_enabled=st.sidebar.checkbox("Learning Adjustment", value=st.session_state.learning_enabled)
    st.session_state.telegram_enabled=st.sidebar.checkbox("Telegram Alerts", value=st.session_state.telegram_enabled)
    st.session_state.minimum_rr=st.sidebar.slider("Minimum Risk / Reward", min_value=1.0, max_value=5.0, value=float(st.session_state.minimum_rr), step=0.2)
    st.session_state.risk_percent=st.sidebar.slider("Risk Per Trade %", min_value=0.25, max_value=3.0, value=float(st.session_state.risk_percent), step=0.25)
    st.sidebar.markdown("---"); st.sidebar.caption("TRADE WITH BLY7 TRADER")
def render_dashboard_metrics():
    stats=get_performance_stats(); health=check_mexc_connection(); tickers=get_mexc_tickers()
    c1,c2,c3,c4=st.columns(4)
    c1.metric("MEXC Contracts", len(tickers)); c2.metric("Total Signals", stats["total"]); c3.metric("Open Trades", stats["open"]); c4.metric("Win Rate", f"{stats['win_rate']:.1f}%")
    if health["connected"]: st.success("MEXC Futures API: Connected")
    else: st.error("MEXC Futures API: Disconnected")
def render_market_overview():
    st.subheader("🌍 MEXC Futures Market Overview"); snapshot=get_market_snapshot()
    if snapshot.empty: st.warning("Market data is currently unavailable."); return
    display=snapshot[["symbol","last_price","change_pct","amount_24h","funding_rate"]].head(30).copy()
    display.columns=["Contract","Last Price","24h Change %","24h Turnover","Funding Rate"]
    st.dataframe(display, use_container_width=True, hide_index=True)
def render_signals(signals):
    st.subheader("🎯 Detected Trading Signals")
    if not signals: st.info("No qualified signals found in this scan."); return
    rows=[]
    for s in signals: rows.append({"Symbol":s["symbol"],"Side":s["side"],"Score":s["score"],"Timeframe":s["timeframe"],"Entry":s["entry"],"Stop Loss":s["stop"],"TP1":s["tp1"],"TP2":s["tp2"],"TP3":s["tp3"],"R/R":s["rr"]})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    for s in signals:
        with st.expander(f"{s['symbol']} | {s['side']} | {s['score']}/100"):
            st.write(f"Entry: {s['entry']:.10g}"); st.write(f"Stop: {s['stop']:.10g}"); st.write(f"TP1: {s['tp1']:.10g}"); st.write(f"TP2: {s['tp2']:.10g}"); st.write(f"TP3: {s['tp3']:.10g}")
            st.write("Reasons:", s["reasons"])
            if s["warnings"]: st.warning("\n".join(s["warnings"]))
def render_open_trades():
    st.subheader("📡 Open Trade Monitoring"); df=get_open_signals()
    if df.empty: st.info("No open trades."); return
    cols=["id","symbol","side","timeframe","score","entry","stop","tp1","tp2","tp3","status","last_price"]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)
def render_learning_dashboard():
    st.subheader("🧠 Automatic Learning & Performance"); stats=get_performance_stats()
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Completed Trades", stats["wins"]+stats["losses"]); c2.metric("Wins", stats["wins"]); c3.metric("Losses", stats["losses"]); c4.metric("Expectancy", f"{stats['expectancy']:.2f}%")
    st.metric("Profit Factor", f"{stats['profit_factor']:.2f}")
    learning=learning_profile(); st.write(f"Learning Adjustment: {learning['adjustment']}")
    st.caption("Learning adjustment is a simple statistical adjustment, not a trained machine-learning model.")
def execute_market_scan():
    settings={"min_score":st.session_state.min_score,"scan_limit":st.session_state.scan_limit,"timeframe":st.session_state.timeframe,"enable_long":st.session_state.enable_long,"enable_short":st.session_state.enable_short,"btc_filter":st.session_state.btc_filter,"learning_enabled":st.session_state.learning_enabled,"minimum_rr":st.session_state.minimum_rr,"risk_percent":st.session_state.risk_percent,"min_volume":0}
    with st.spinner("Scanning MEXC Futures contracts..."): result=scan_market(settings)
    st.session_state.last_scan=utc_iso(); st.session_state.last_scan_result=result
    saved=save_signals(result["signals"])
    if st.session_state.telegram_enabled:
        telegram_results=send_signal_batch(saved); sent_count=sum(1 for x in telegram_results if x["sent"]); st.info(f"Telegram notifications sent: {sent_count}")
    st.success(f"Scan completed: {result['scanned']} contracts checked, {len(result['signals'])} qualified signals found.")
    st.caption(f"Scan duration: {result['duration']:.2f} seconds")
    return result
def execute_trade_tracking():
    updates=track_open_trades()
    for u in updates:
        if u["status"] in ("TP1","TP2","TP3","STOP_LOSS"):
            if st.session_state.telegram_enabled: send_trade_update(u)
    save_learning_snapshot(); return updates
def render_history():
    st.subheader("📚 Signal History"); df=get_recent_signals(200)
    if df.empty: st.info("No recorded signals yet."); return
    cols=["id","created_at","symbol","side","timeframe","score","entry","stop","tp1","status","outcome","pnl_pct"]
    st.dataframe(df[cols], use_container_width=True, hide_index=True)
def render_telegram_status():
    st.subheader("📨 Telegram Integration"); config=get_telegram_config()
    if config["ready"]:
        st.success("Telegram credentials configured.")
        if st.button("Send Telegram Test", key="telegram_test"):
            sent=send_telegram("💎 BLY7TRADER ULTIMATE\nTelegram connection test successful.")
            if sent: st.success("Test message sent.")
            else: st.error("Telegram message failed.")
    else: st.warning("Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID in Streamlit Secrets.")
def main():
    render_sidebar(); render_dashboard_metrics(); st.markdown("---")
    tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(["Market","Scanner","Open Trades","Learning","History","Telegram"])
    with tab1: render_market_overview()
    with tab2:
        st.subheader("⚡ MEXC Futures Scanner")
        if st.button("START FULL MARKET SCAN", type="primary", use_container_width=True): execute_market_scan()
        result=st.session_state.last_scan_result
        if result: render_signals(result["signals"])
        if st.session_state.last_scan: st.caption(f"Last scan: {st.session_state.last_scan}")
    with tab3:
        if st.button("UPDATE OPEN TRADES", use_container_width=True):
            updates=execute_trade_tracking(); st.success(f"Updated {len(updates)} trade records.")
        render_open_trades()
    with tab4: render_learning_dashboard()
    with tab5: render_history()
    with tab6: render_telegram_status()
    st.markdown("---")
    st.markdown("""<div style="text-align:center;color:#d9b45c;padding:15px;font-weight:800;">TRADE WITH BLY7 TRADER<br><span style="color:#8290a5;font-size:12px;">MEXC FUTURES INTELLIGENCE ENGINE</span></div>""", unsafe_allow_html=True)
if __name__=="__main__": main()
