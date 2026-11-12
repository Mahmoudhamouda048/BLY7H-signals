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

def get_binance_fallback_klines(symbol, timeframe="15m", limit=300):
    """Fallback when MEXC kline is blocked/empty on Streamlit Cloud. Binance Futures public klines, same prices."""
    try:
        bsym = normalize_symbol(symbol).replace("_", "")
        bmap = {"5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h", "4h": "4h", "8h": "8h", "1d": "1d", "1w": "1w", "1m": "1m"}
        interval = bmap.get(timeframe, "15m")
        payload = api_json("https://fapi.binance.com/fapi/v1/klines", params={"symbol": bsym, "interval": interval, "limit": int(max(50, min(1500, safe_int(limit, 300))))})
        if not isinstance(payload, list) or not payload:
            return pd.DataFrame()
        rows = []
        for c in payload:
            try: rows.append({"timestamp": float(c[0]), "open": float(c[1]), "high": float(c[2]), "low": float(c[3]), "close": float(c[4]), "volume": float(c[5]), "amount": float(c[7]) if len(c) > 7 else 0.0})
            except Exception: continue
        if not rows: return pd.DataFrame()
        frame = pd.DataFrame(rows)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        frame = frame.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
        return frame
    except Exception as exc:
        log_event(f"Binance fallback failed for {symbol}: {exc}", "warning"); return pd.DataFrame()

def get_mexc_klines(symbol, timeframe="15m", limit=300):
    symbol=normalize_symbol(symbol)
    interval=MEXC_INTERVALS.get(timeframe)
    if not interval: return pd.DataFrame()
    seconds=TIMEFRAME_SECONDS.get(timeframe,900)
    limit=clamp(safe_int(limit,300),50,1500)
    end_time=int(time.time()); start_time=end_time-(seconds*limit)
    url=f"{MEXC_ENDPOINTS['KLINE']}/{symbol}"
    payload=mexc_request(url, params={"interval":interval,"start":start_time,"end":end_time})
    if not payload: return get_binance_fallback_klines(symbol, timeframe, limit)
    data=payload.get("data")
    if not isinstance(data,dict): return get_binance_fallback_klines(symbol, timeframe, limit)
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
        if len(frame) < 30:
            fb = get_binance_fallback_klines(symbol, timeframe, limit)
            if not fb.empty: return fb
        return frame
    except (ValueError, TypeError, KeyError) as exc:
        log_event(f"Kline parsing failed for {symbol}: {exc}","warning"); return get_binance_fallback_klines(symbol, timeframe, limit)
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
    recent_high=safe_float(df["high"].iloc
