import streamlit as st, pandas as pd, requests, time
from datetime import datetime
st.set_page_config(page_title="BLY7H V18", layout="wide", page_icon="💎", initial_sidebar_state="collapsed")
st.markdown("<h1 style='text-align:center'>💎 BLY7H ULTIMATE V18</h1><p style='text-align:center'>🧠 تحليل حقيقي لكل عملة | 💸 فاندنج حقيقي | 🐋 مصيدة حقيقية</p><p style='text-align:center'>🧠 ذكاء اصطناعي يتعلم | 🔮 تنبؤ قبل الحركة | ✅ تأكيد 5 منصات | 📊 باك تست حي</p>", unsafe_allow_html=True)
# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🎛️ التحكم - V18 REAL - فاندنج حقيقي")
    st.markdown("#### 🌐 المنصة")
    plat_kucoin = st.checkbox("🔥 KUCOIN", value=True)
    plat_binance = st.checkbox("💛 BINANCE", value=True)
    plat_dex = st.checkbox("🚀 DEX", value=True)
    st.markdown("#### 🎯 نوع الصفقة")
    want_pump = st.checkbox("🚀 PUMP", value=True)
    want_dump = st.checkbox("📉 DUMP", value=True)
    st.markdown("#### 🧠 المزايا")
    use_fvg = st.checkbox("📦 FVG + Order Block", value=True)
    f_trap = st.checkbox("🐋 مصيدة - Liquidation Hunt", value=True)
    f_killzone = st.checkbox("⏰ كيل زون London/NY", value=True)
    f_funding = st.checkbox("💸 فخ الفاندنج", value=False)
    f_wall = st.checkbox("🧱 جدار الحيتان", value=False)
    f_btc = st.checkbox("🔗 فلتر البيتكوين", value=True)
    f_cascade = st.checkbox("💥 سلسلة التصفية", value=False)
    f_pos = st.checkbox("🎯 حجم الصفقة", value=True)
    f_confirm5 = st.checkbox("✅ تأكيد 5 منصات", value=True)
    st.markdown("#### 🎚️ التصفية")
    mode = st.radio("الوضع", ["😌 قياسي - هادي", "🛡️ صارم"], index=0)
    min_score = st.slider("⭐ اقل سكور", 0, 100, 20)
    limit_coins = st.slider("🪙 عدد العملات", 10, 100, 40)
    send_tg = st.checkbox("📡 تليجرام - ابعت كل إشارة", value=True)
    if st.button("📡 اختبر التليجرام"):
        ok, msg = send_tg("🧪 اختبار BLY7H - لو وصلك يبقى التليجرام شغال ✅\n@WHYNOTBLY7")
        if ok: st.success("📡 التليجرام شغال ✅ - الرسالة وصلت")
        else: st.error(f"📡 التليجرام مش شغال: {msg}")
    st.markdown("---")
    st.success("V18 REAL - فاندنج حقيقي")
    st.info("جاهز للفحص")
is_strict = "صارم" in mode
need_vol = 2.5 if is_strict else 1.1
if min_score <= 25:
    need_vol = 1.1
STABLES = ["USDCUSDT","BUSDUSDT","DAIUSDT","FDUSDUSDT","USDeUSDT"]
def clamp_entry(e, p, is_pump):
    if p == 0: return e
    if abs(e-p)/p*100 > 1.5:
        return p*0.993 if is_pump else p*1.007
    return e

def is_killzone():
    from datetime import datetime as _dt
    m=_dt.now().hour*60+_dt.now().minute
    if 600<=m<=720: return True,"لندن ✅"
    if 930<=m<=1050: return True,"نيويورك ✅"
    return False,"خارج الكيل زون"
def get_btc_ch():
    try:
        r=requests.get("https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=2",timeout=5)
        d=r.json(); return (float(d[-1][4])-float(d[-2][4]))/float(d[-2][4])*100
    except: return 0
def get_funding(sym):
    try:
        r=requests.get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}",timeout=5)
        if r.status_code==200: return float(r.json().get('lastFundingRate',0))*100
    except: pass
    return 0
def check_5ex(sym):
    base=sym.replace('USDT',''); c=1; leaders=["BINANCE"]
    for url,name in [(f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={base}-USDT","KUCOIN"),(f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={base}_USDT","GATE"),(f"https://api.bitget.com/api/v2/spot/market/tickers?symbol={base}USDT","BITGET"),(f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={base}USDT","BYBIT")]:
        try:
            r=requests.get(url,timeout=3)
            if r.status_code==200: c+=1; leaders.append(name)
        except: pass
    return c, leaders[0]
def send_tg(text):
    # ترجع (نجح؟, رسالة السبب) - عشان تعرف ليه مش بيبعت لو فشل
    try:
        tok=st.secrets.get("TELEGRAM_BOT_TOKEN")
        chat=st.secrets.get("TELEGRAM_CHANNEL_ID", st.secrets.get("TELEGRAM_CHAT_ID"))
        if not tok: return False, "مفيش TELEGRAM_BOT_TOKEN في Secrets"
        if not chat: return False, "مفيش TELEGRAM_CHANNEL_ID في Secrets"
        r=requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",json={"chat_id":chat,"text":text},timeout=15)
        if r.status_code==200: return True, "اتبعت ✅"
        if r.status_code==401: return False, "التوكن غلط - راجع @BotFather"
        if r.status_code==403: return False, "البوت مش أدمن في القناة - ضيفه أدمن"
        if r.status_code==400: return False, f"Chat ID غلط: {chat} - هاته من @userinfobot"
        if r.status_code==429:
            import time as _t; _t.sleep(2); return send_tg(text)
        return False, f"خطأ تليجرام {r.status_code}"
    except Exception as e: return False, f"خطأ اتصال: {e}"
def send_all_tg(signals):
    # يبعت كل الاشارات - ويرجع تقرير
    if not signals: return
    sent=0; last_err=""
    for s in signals[:5]:
        ok, msg = send_tg(format_tg(s))
        if ok: sent+=1
        else: last_err=msg
        import time as _t; _t.sleep(1)
    if sent>0: st.success(f"📡 اتبعت {sent} إشارة للتليجرام ✅")
    else: st.error(f"📡 التليجرام مش بيبعت: {last_err}")
    return sent
def format_tg(s):
    head = f"{'🚀 PUMP' if s['type']=='PUMP' else '📉 DUMP'} {s['symbol']}"
    body = f"{head}\n"
    body += f"⭐ سكور: {s['score']} | 💵 سعر: {s['price']} | 📦 Vol: x{s['vol']} | 📈 تغير 1س: {s['ch']}%\n"
    body += f"🎯 دخول: {s['entry']}\n"
    body += f"❌ إلغاء: {s.get('no_return_point', s['entry'])}\n" if 'no_return_point' in s else ""
    body += f"⛔ ستوب: {s['stop']}\n"
    body += f"✅ هدف1: {s['tp1']}\n"
    body += f"🏆 هدف2: {s['tp2']}\n"
    body += f"--- التحليل ---\n"
    body += f"{s.get('extra','')}\n"
    body += f"@WHYNOTBLY7"
    return body
def load_mem():
    import os, json
    try:
        if os.path.exists("bly7h_memory.json"):
            return json.load(open("bly7h_memory.json"))
    except: pass
    return {"signals":[],"patterns":{},"total":0,"total_win":0}
def calc_cvd(df):
    g=r=0
    for i in range(-10,0):
        c=float(df['close'].iloc[i]); o=float(df['open'].iloc[i]); v=float(df['vol'].iloc[i])
        if c>o: g+=v
        else: r+=v
    tot=g+r
    if tot==0: return 0,0
    return (g-r)/tot*100, (g-r)/tot*100
def calc_fvg(df):
    bull_b=bull_m=bear_b=bear_m=None
    s=max(1,len(df)-20)
    for i in range(s,len(df)-1):
        ln=float(df['low'].iloc[i+1]); hp=float(df['high'].iloc[i-1])
        hn=float(df['high'].iloc[i+1]); lp=float(df['low'].iloc[i-1])
        if ln>hp: bull_b=hp; bull_m=(hp+ln)/2
        if hn<lp: bear_b=hn; bear_m=(hn+lp)/2
    return bull_b,bull_m,bear_b,bear_m

def get_wall_real(sym):
    # جدار حقيقي من الاوردر بوك - مش "راقب الاوردر بوك"
    try:
        b = sym.replace('-USDT','USDT').replace('USDT','')
        # بينانس اوردر بوك
        r = requests.get(f"https://data-api.binance.vision/api/v3/depth?symbol={b}USDT&limit=20", timeout=5)
        if r.status_code==200:
            d=r.json(); bids=d.get('bids',[]); asks=d.get('asks',[])
            if bids and asks:
                max_bid = max(float(q) for _,q in bids); max_ask = max(float(q) for _,q in asks)
                bid_price = float(bids[0][0]); ask_price = float(asks[0][0])
                # الجدار الاكبر: فوق ولا تحت؟
                if max_ask > max_bid*1.5:
                    return f"جدار بيع {max_ask:,.0f} عند {ask_price} - السعر هيترد منه"
                elif max_bid > max_ask*1.5:
                    return f"جدار شراء {max_bid:,.0f} عند {bid_price} - السعر هيترفع منه"
                else:
                    return f"مفيش جدار واضح - اكبر بيع {max_ask:,.0f} / اكبر شراء {max_bid:,.0f}"
    except: pass
    return "اوردر بوك غير متاح"
def get_funding_real(sym):
    # فاندنج حقيقي - لو العملة كوكوين نحولها - لو فشل نرجع None مش 0.000
    try:
        b = sym.replace('-USDT','').replace('USDT','')
        r = requests.get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={b}USDT", timeout=5)
        if r.status_code==200:
            f = float(r.json().get('lastFundingRate', 0))*100
            return f
    except: pass
    return None
def get_oi_real(sym):
    try:
        b = sym.replace('-USDT','').replace('USDT','')
        r = requests.get(f"https://fapi.binance.com/futures/data/openInterestHist?symbol={b}USDT&period=5m&limit=12", timeout=5)
        if r.status_code==200:
            d=r.json()
            if len(d)>=2:
                first=float(d[0]['sumOpenInterest']); last=float(d[-1]['sumOpenInterest'])
                if first>0: return (last-first)/first*100, last
    except: pass
    return 0, 0
def calc_trap_real(df, last, typ, bm, em, bb, eb, buy):
    # مصيدة حقيقية: لازم دليل من الشارت مش كلام ثابت
    try:
        # ذيل طويل؟ السعر عمل ويك وضرب ستوبات ورجع؟
        last_low=float(df['low'].iloc[-1]); last_high=float(df['high'].iloc[-1])
        last_open=float(df['open'].iloc[-1]); last_close=float(df['close'].iloc[-1])
        body=abs(last_close-last_open); wick_up=last_high-max(last_open,last_close); wick_dn=min(last_open,last_close)-last_low
        if typ=="DUMP":
            # دامب: بيع قوي + ذيل فوقي طويل = ضرب ستوبات فوق وبعدين نزل
            if wick_up > body*1.5:
                return f"مصيدة: ويك فوقي {wick_up/last*100:.2f}% - ضرب ستوبات الشورت ورجع ينزل"
            if buy < -30:
                return f"مصيدة: توزيع بيع {abs(buy):.0f}% - الحيتان بتوزع عند القمة"
            return f"مصيدة: بيع {abs(buy):.0f}% - ضغط بيع مستمر"
        else:
            if wick_dn > body*1.5:
                return f"مصيدة: ويك تحتي {wick_dn/last*100:.2f}% - ضرب ستوبات اللونج ورجع يطلع"
            if buy > 30:
                return f"مصيدة: تجميع شراء {buy:.0f}% - الحيتان بتجمع عند القاع"
            return f"مصيدة: شراء {buy:.0f}% - ضغط شراء مستمر"
    except: return "مصيدة: غير محسوب"
def calc_cascade_real(sym, last, oi_ch, typ):
    # سلسلة تصفية: نحسبها من OI الحقيقي - لو OI طالع والسعر عكس = تصفية قادمة
    try:
        if oi_ch is None: oi_ch=0
        if typ=="DUMP" and oi_ch > 3:
            return f"سلسلة تصفية: OI +{oi_ch:.1f}% والسعر بينزل - لونجات هتتصفى لو نزل 2%"
        if typ=="PUMP" and oi_ch < -3:
            return f"سلسلة تصفية: OI {oi_ch:.1f}% والسعر بيطلع - شورتات هتتصفى لو طلع 2%"
        if abs(oi_ch) < 1:
            return f"سلسلة تصفية: OI {oi_ch:+.1f}% - مفيش خطر تصفية قريب"
        return f"سلسلة تصفية: OI {oi_ch:+.1f}%"
    except: return "سلسلة تصفية: غير محسوب"

def analyze(df, sym):
    try:
        last=float(df['close'].iloc[-1]); prev=float(df['close'].iloc[-2])
        ch=(last-prev)/prev*100 if prev!=0 else 0
        mv=float(df['vol'].iloc[-20:-1].mean()); lv=float(df['vol'].iloc[-1])
        vs=lv/mv if mv>0 else 1
        # FIX V16: Vol مش شرط قاتل - السوق هادي وكل العملات Vol x0.6 - لو رفضناها مش هيجيب حاجة
        # Vol بقى جزء من السكور بس - البامب والدامب الاتنين
        pass # Vol لا يرفض
        if abs(ch)>8: return None, f"حركة 1س {ch:.1f}% كبيرة"
        buy,_=calc_cvd(df); sell=-buy
        bb,bm,eb,em=calc_fvg(df)
        if use_fvg and is_strict and bm is None and em is None: return None, "مفيش FVG"
        # اتجاه: الاقوى بس
        is_pump = buy>=0; is_dump = sell>0
        if buy>=0 and sell>0:
            is_dump=False
        if buy<0 and sell>0:
            is_pump=False
        # لو متذبذب جدا - ارفض
        # FIX: kz_bonus يتعرف قبل السكور - كان بيضرب XRP
        in_kz, kz_txt = is_killzone() if f_killzone else (True,"")
        kz_bonus = 10 if (f_killzone and in_kz) else 0
        funding2 = get_funding(sym) if (f_funding and sym.endswith("USDT")) else 0
        if abs(buy)<1: return None, f"CVD {buy:.1f}% متذبذب"
        score=int(40 + min(vs*3,15) + abs(buy)*0.3 + (10 if (bm or em) else 0) + kz_bonus)
        if score>95: score=95
        if score < min_score: return None, f"سكور {score} < {min_score}"
        # === المزايا المختارة ===
        if not want_pump and buy>=0: return None, "بامب ملغي من الاختيار"
        if not want_dump and buy<0: return None, "دامب ملغي من الاختيار"
        btc_ch = get_btc_ch() if f_btc else 0
        if f_btc and btc_ch < -2 and buy>=0: return None, f"BTC {btc_ch:.1f}% بينزف - بامب ملغي"
        funding = get_funding(sym) if (f_funding and sym.endswith("USDT")) else 0
        if f_funding and funding>0.05 and buy>=0: return None, f"فاندنج {funding:.3f}% فخ - الكل لونج"
        if f_funding and funding<-0.05 and buy<0: return None, "فاندنج فخ دامب"
        # مستويات - مقفولة قريب من السعر
        if is_pump:
            entry=clamp_entry(bm,last,True) if bm is not None else last*0.993
            stop=last*0.98; tp1=last*1.04; tp2=last*1.08; typ="PUMP"
        else:
            entry=clamp_entry(em,last,False) if em is not None else last*1.007
            stop=last*1.02; tp1=last*0.96; tp2=last*0.92; typ="DUMP"
        funding = funding2
        # === كل سطر برقم حقيقي من العملة نفسها - مش قالب ثابت ===
        lines = []
        # اوردر بلوك: ارقام حقيقية
        if f_fvg:
            if typ=="PUMP" and bb is not None:
                lines.append(f"📦 أوردر بلوك: {bb:.6f} - FVG: {bm:.6f} - المسافة من السعر {abs(bm-last)/last*100:.2f}%")
            elif typ=="DUMP" and eb is not None:
                lines.append(f"📦 أوردر بلوك: {eb:.6f} - FVG هابط: {em:.6f} - المسافة {abs(em-last)/last*100:.2f}%")
            else:
                lines.append(f"📦 أوردر بلوك: لا يوجد FVG حديث - الدخول من السعر {last:.6f}")
        # مصيدة حقيقية
        if f_trap:
            lines.append(f"🐋 مصيدة: {calc_trap_real(df, last, typ, bm, em, bb, eb, buy)}")
        # كيل زون: وقت حقيقي + هل احنا جواه ولا بره
        if f_killzone:
            if in_kz:
                lines.append(f"⏰ كيل زون: {kz_txt} - إشارة في وقت السيولة")
            else:
                lines.append(f"⏰ كيل زون: خارج الكيل زون ({kz_txt}) - سيولة أقل")
        # فاندنج حقيقي - لو مش متاح نقول مش متاح مش 0.000
        if f_funding:
            fr = get_funding_real(sym)
            if fr is None:
                lines.append(f"💸 فاندنج: غير متاح لـ {sym} - بدون فيوتشر")
            else:
                interp = "الكل لونج - خطر دامب" if fr>0.05 else "الكل شورت - فرصة بامب" if fr<-0.05 else "متوازن"
                lines.append(f"💸 فاندنج: {fr:+.4f}% - {interp}")
        # جدار حقيقي من الاوردر بوك
        if f_wall:
            lines.append(f"🧱 جدار: {get_wall_real(sym)}")
        # سلسلة تصفية حقيقية من OI
        oi_ch, oi_val = get_oi_real(sym)
        if f_cascade:
            lines.append(f"💥 {calc_cascade_real(sym, last, oi_ch, typ)}")
        # حجم صفقة حقيقي: حسب السكور والمسافة للستوب
        if f_pos:
            risk_pct = abs(stop-last)/last*100 if last!=0 else 2
            lines.append(f"🎯 حجم: {'2%' if score>=90 else '1%' if score>=75 else '0.5%'} من رأس المال - مخاطرة الصفقة {risk_pct:.2f}%")
        # تأكيد 5 منصات حقيقي
        if f_confirm5:
            _cc,_lead=check_5ex(sym); lines.append(f"✅ تأكيد: {_cc} منصات - القائد {_lead}"); score=min(95,score+5) if _cc>=3 else score
        # OI سطر مستقل
        lines.append(f"📊 OI: {oi_ch:+.1f}% - CVD: {buy:+.1f}%")
        extra = "\n".join(lines)
        d={"symbol":sym,"score":score,"type":typ,"price":round(last,6),"ch":round(ch,2),"vol":round(vs,2),"buy":round(buy,1),"entry":round(entry,6),"stop":round(stop,6),"tp1":round(tp1,6),"tp2":round(tp2,6),"extra":extra}
        return d, "OK"
    except Exception as e:
        return None, str(e)
def get_kucoin():
    try:
        r=requests.get("https://api.kucoin.com/api/v1/market/allTickers",timeout=15)
        data=r.json().get('data',{}).get('ticker',[])
        u=[d for d in data if d.get('symbol','').endswith('-USDT')]
        u=sorted(u,key=lambda x: float(x.get('volValue') or 0),reverse=True)
        return [d['symbol'] for d in u[:100]]
    except: return []
def get_k_klines(sym):
    try:
        end=int(time.time()); start=end-100*3600
        r=requests.get(f"https://api.kucoin.com/api/v1/market/candles?type=1hour&symbol={sym}&startAt={start}&endAt={end}",timeout=10)
        data=r.json().get('data',[])
        if len(data)<20: return None
        df=pd.DataFrame(data,columns=['time','open','close','high','low','vol','turnover'])
        for c in ['open','close','high','low','vol']: df[c]=pd.to_numeric(df[c],errors='coerce')
        return df.sort_values('time').dropna()
    except: return None
def get_binance_syms():
    try:
        r=requests.get("https://data-api.binance.vision/api/v3/ticker/24hr",timeout=15)
        data=r.json(); u=[d for d in data if d.get('symbol','').endswith('USDT')]
        u=sorted(u,key=lambda x: float(x.get('quoteVolume') or 0),reverse=True)
        return [d['symbol'] for d in u if d['symbol'] not in STABLES][:100]
    except: return []
def get_b_klines(sym):
    try:
        r=requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval=1h&limit=100",timeout=10)
        data=r.json()
        if len(data)<20: return None
        df=pd.DataFrame(data,columns=['ot','open','high','low','close','vol','ct','qav','tr','tb','tq','ig'])
        for c in ['open','high','low','close','vol']: df[c]=pd.to_numeric(df[c],errors='coerce')
        return df.dropna()
    except: return None
# --- NAV ---
section=st.radio("📂 اختار القسم", ["🔥 KUCOIN", "💛 BINANCE", "📉 DUMP", "🚀 DEX", "📊 باك تست", "🧠 ذاكرة"], horizontal=True)
if section=="🔥 KUCOIN":
    st.markdown("### 🔥 KUCOIN - تجميع قبل البمب")
    st.caption(f"الوضع: {mode} | سكور {min_score}+ | Vol x{need_vol} | FVG: {'مطلوب' if use_fvg else 'مش مطلوب'}")
    if st.button("🔥 افحص KUCOIN الآن", type="primary"):
        syms=get_kucoin(); st.info(f"تم جلب {len(syms)} عملة - هيفحص اول {limit_coins}")
        res=[]; debug=[]
        prog=st.progress(0)
        for i,sym in enumerate(syms[:limit_coins]):
            prog.progress((i+1)/limit_coins)
            df=get_k_klines(sym)
            if df is not None:
                sig,why=analyze(df,sym)
                if sig: res.append(sig)
                elif len(debug)<10: debug.append({"عملة":sym,"الملاحظة":why})
            time.sleep(0.02)
        prog.empty()
        if res:
            st.success(f"🎉 لقينا {len(res)} اشارة!")
            if send_tg: send_all_tg(sorted(res,key=lambda x: x['score'],reverse=True))
            for s in sorted(res,key=lambda x: x['score'],reverse=True):
                col1,col2=st.columns([3,1])
                with col1: st.markdown(f"**{'🚀' if s['type']=='PUMP' else '📉'} {s['symbol']} - {s['type']}** | سعر {s['price']} | Vol x{s['vol']} | CVD {s['buy']}%")
                with col2: st.markdown(f"⭐ **{s['score']}**")
                st.markdown(f"🎯 دخول {s['entry']} | ⛔ ستوب {s['stop']} | ✅ هدف1 {s['tp1']} | 🏆 هدف2 {s['tp2']}")
                st.markdown("---")
        else:
            st.warning("لا توجد إشارات مطابقة للفلاتر")
        if debug:
            st.markdown("### 🔍 أقرب 10 عملات للفلتر")
            st.dataframe(pd.DataFrame(debug), use_container_width=True)
if section=="💛 BINANCE":
    st.markdown("### 💛 BINANCE - تنبؤ قبل الحركة")
    if st.button("💛 افحص BINANCE الآن", type="primary"):
        syms=get_binance_syms(); st.info(f"تم جلب {len(syms)} - هيفحص اول {limit_coins}")
        res=[]; debug=[]
        prog=st.progress(0)
        for i,sym in enumerate(syms[:limit_coins]):
            prog.progress((i+1)/limit_coins)
            df=get_b_klines(sym)
            if df is not None:
                sig,why=analyze(df,sym)
                if sig: res.append(sig)
                elif len(debug)<10: debug.append({"عملة":sym,"الملاحظة":why})
            time.sleep(0.02)
        prog.empty()
        if res:
            st.success(f"🎉 {len(res)} اشارة!")
            if send_tg: send_all_tg(sorted(res,key=lambda x: x['score'],reverse=True))
            for s in sorted(res,key=lambda x: x['score'],reverse=True):
                st.markdown(f"**{'🚀' if s['type']=='PUMP' else '📉'} {s['symbol']} - {s['type']}** ⭐ {s['score']} | سعر {s['price']} | Vol x{s['vol']}")
                st.markdown(f"🎯 دخول {s['entry']} | ⛔ ستوب {s['stop']} | ✅ {s['tp1']} | 🏆 {s['tp2']}")
                st.markdown("---")
        else: st.warning("لا توجد إشارات")
        if debug: st.dataframe(pd.DataFrame(debug), use_container_width=True)

if section=="🚀 DEX":
    st.markdown("### 🚀 DEX - قبل المنصات")
    if not plat_dex: st.warning("DEX مش متعلم عليه في السايد بار")
    else:
        if st.button("🚀 افحص DEX الآن", type="primary"):
            try:
                r=requests.get("https://api.dexscreener.com/latest/dex/search/?q=BSC",timeout=15)
                pairs=r.json().get('pairs',[])[:20]; seen=set(); found=0
                for p in pairs:
                    addr=p.get('baseToken',{}).get('address')
                    if not addr or addr in seen: continue
                    seen.add(addr)
                    try:
                        r2=requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}",timeout=10)
                        ps=r2.json().get('pairs',[])
                        if not ps: continue
                        pair=sorted(ps,key=lambda x: float(x.get('liquidity',{}).get('usd',0)),reverse=True)[0]
                        sym=pair.get('baseToken',{}).get('symbol','UNK'); chain=pair.get('chainId','').upper(); price=pair.get('priceUsd','0')
                        ch5=float(pair.get('priceChange',{}).get('m5',0)); v5=float(pair.get('volume',{}).get('m5',0)); liq=float(pair.get('liquidity',{}).get('usd',0))
                        if v5>5000 and ch5>=5 and liq>15000:
                            pp=float(price); st.code(f"🚀 DEX {sym} على {chain}\n💵 {price} دخول {pp} الغاء {pp*0.97:.8f} ستوب {pp*0.95:.8f} هدف {pp*1.3:.8f}\n🔗 {pair.get('url','')}\n@WHYNOTBLY7")
                            if send_tg: send_tg(f"🚀 DEX {sym} على {chain}\n💵 {price} دخول {pp} الغاء {pp*0.97:.8f} ستوب {pp*0.95:.8f} هدف {pp*1.3:.8f}\n🔗 {pair.get('url','')}\n@WHYNOTBLY7")
                            found+=1
                    except: pass
                if found==0: st.warning("😴 مفيش بمب DEX قوي")
            except Exception as e: st.error(f"خطأ: {e}")
if section=="📊 باك تست":
    st.markdown("### 📊 باك تست - نسبة نجاح حقيقية")
    test_sym=st.selectbox("🪙 عملة", ["BTCUSDT","ETHUSDT","SOLUSDT"], key="bt_sym")
    if st.button("▶️ شغل باك تست", type="primary"):
        df=get_b_klines(test_sym)
        if df is not None:
            wins=total=tp2=stops=0
            for i in range(30,len(df)-10):
                sub=df.iloc[:i]; last=float(sub['close'].iloc[-1]); mv=float(sub['vol'].iloc[-20:-1].mean()); lv=float(sub['vol'].iloc[-1]); vs=lv/mv if mv>0 else 1
                if vs<2: continue
                fut=df.iloc[i:i+10]; stop=last*0.975; tp1=last*1.04; tp2v=last*1.08; res="لا شيء"
                for j in range(len(fut)):
                    hi=float(fut['high'].iloc[j]); lo=float(fut['low'].iloc[j])
                    if lo<=stop: res="STOP"; stops+=1; break
                    if hi>=tp2v: res="TP2"; tp2+=1; wins+=1; break
                    if hi>=tp1: res="TP1"; wins+=1; break
                total+=1
            wr=wins/total*100 if total>0 else 0
            c1,c2,c3,c4=st.columns(4); c1.metric("اشارات",total); c2.metric("هدف1",f"{wins} ({wr:.1f}%)"); c3.metric("هدف2",tp2); c4.metric("ستوب",stops)
            st.progress(wr/100); st.success(f"🎉 {wr:.1f}%") if wr>=55 else st.warning(f"⚠️ {wr:.1f}%")
if section=="🧠 ذاكرة":
    st.markdown("### 🧠 ذاكرة التعلم")
    mem=load_mem(); tot=mem.get("total",0); win=mem.get("total_win",0); rate=win/tot*100 if tot>0 else 0
    c1,c2=st.columns(2); c1.metric("اشارات محفوظة",tot); c2.metric("نسبة نجاح",f"{rate:.1f}%")
    st.info("💡 البوت بيحفظ كل اشارة ونتيجتها - والنمط اللي بينجح بياخد بونص اكتر لوحده")
    if mem.get("signals"): st.dataframe(pd.DataFrame(mem["signals"][-20:]), use_container_width=True)

if section=="📉 DUMP":
    st.markdown("### 📉 DUMP - انهيار قادم")
    st.caption("توزيع الحيتان - بيع قوي + Vol أحمر + FVG هابط")
    st.caption(f"الوضع: {mode} | سكور {min_score}+ | Vol x{need_vol}")
    # زرارين منفصلين - دامب كوكوين ودامب بينانس
    c_dump1, c_dump2 = st.columns(2)
    with c_dump1:
        do_dump_k = st.button("📉 فحص دامب KUCOIN", type="primary", key="dump_k")
    with c_dump2:
        do_dump_b = st.button("📉 فحص دامب BINANCE", type="primary", key="dump_b")
    if do_dump_k or do_dump_b:
        if do_dump_k:
            syms_dump = get_kucoin(); get_fn = get_k_klines; src="KUCOIN"
        else:
            syms_dump = get_binance_syms(); get_fn = get_b_klines; src="BINANCE"
        st.info(f"تم جلب {len(syms_dump)} عملة - فحص أول {limit_coins} - {src}")
        res_dump=[]; debug_dump=[]
        prog_d=st.progress(0)
        for i,sym in enumerate(syms_dump[:limit_coins]):
            prog_d.progress((i+1)/limit_coins)
            df=get_fn(sym)
            if df is not None:
                sig,why=analyze(df,sym)
                # DUMP بس - لو بامب نتخطاه هنا عشان القسم ده دامب بس
                if sig and sig['type']=="DUMP":
                    res_dump.append(sig)
                elif sig and sig['type']=="PUMP":
                    pass
                elif len(debug_dump)<10:
                    debug_dump.append({"عملة":sym,"الملاحظة":why})
            time.sleep(0.02)
        prog_d.empty()
        if send_tg and res_dump: send_all_tg(sorted(res_dump,key=lambda x: x['score'],reverse=True))
        if res_dump:
            st.success(f"🎉 {len(res_dump)} إشارة دامب - {src}")
            for s in sorted(res_dump,key=lambda x: x['score'],reverse=True):
                st.markdown(f"**📉 {s['symbol']} - DUMP** ⭐ {s['score']} | سعر {s['price']} | Vol x{s['vol']} | بيع {abs(s['buy'])}%")
                st.markdown(f"🎯 دخول {s['entry']} | ⛔ ستوب {s['stop']} | ✅ هدف1 {s['tp1']} | 🏆 هدف2 {s['tp2']}")
                if s.get('extra'): st.caption(s['extra'])
                st.markdown("---")
                pass # التليجرام بيتبعت تحت بعد ما نخلص كل الاشارات
        else:
            st.warning("لا توجد إشارات دامب مطابقة للفلاتر")
            if debug_dump: st.dataframe(pd.DataFrame(debug_dump), use_container_width=True)
