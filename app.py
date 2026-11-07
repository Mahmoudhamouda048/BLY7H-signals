# BLY7H ULTIMATE V10 SCAN ALL - فحص كل عملات المنصات بكل الادوات
import streamlit as st
import requests, os, time
from datetime import datetime

st.set_page_config(page_title="BLY7H SCAN ALL", layout="wide", initial_sidebar_state="collapsed")

try:
    if os.path.exists("bly7h_logo.jpg"):
        c1,c2,c3 = st.columns([1,2,1])
        with c2: st.image("bly7h_logo.jpg", use_container_width=True)
    else:
        st.markdown("<div style='text-align:center;'><div style='font-size:42px;font-weight:900;color:#FFD700;letter-spacing:4px;'>BLY7H ELITE</div><div style='color:#FFD700;font-size:13px;letter-spacing:3px;'>@WHYNOTBLY7 - PREDICT BEFORE THE MOVE</div></div>", unsafe_allow_html=True)
except Exception: pass

st.markdown("### BLY7H SCAN ALL - فحص كل العملات - كل الادوات")

# ===== ادوات =====
def killzone_now():
    h=datetime.now().hour
    if h in [10,11,12]: return "لندن", True
    if h in [15,16,17]: return "نيويورك", True
    return "خارج", False

def get_klines_binance(symbol):
    try:
        r=requests.get("https://api.binance.com/api/v3/klines", params={"symbol":symbol,"interval":"15m","limit":50}, timeout=6)
        if r.status_code==200:
            d=r.json()
            return [float(x[2]) for x in d],[float(x[3]) for x in d],[float(x[4]) for x in d],[float(x[5]) for x in d]
    except Exception: pass
    return [],[],[],[]

def get_klines_mexc(symbol):
    try:
        r=requests.get("https://api.mexc.com/api/v3/klines", params={"symbol":symbol,"interval":"15m","limit":50}, timeout=6)
        if r.status_code==200:
            d=r.json()
            return [float(x[2]) for x in d],[float(x[3]) for x in d],[float(x[4]) for x in d],[float(x[5]) for x in d]
    except Exception: pass
    return [],[],[],[]

def analyze_one(live, highs, lows, closes, vols, direction):
    # FVG
    fvg=None
    if len(highs)>=3:
        for i in range(1,len(highs)-1):
            if direction=="PUMP" and lows[i+1] > highs[i-1]:
                fvg={"top":float(lows[i+1]),"bottom":float(highs[i-1]),"mid":float((lows[i+1]+highs[i-1])/2)}
            if direction=="DUMP" and highs[i+1] < lows[i-1]:
                fvg={"top":float(lows[i-1]),"bottom":float(highs[i+1]),"mid":float((lows[i-1]+highs[i+1])/2)}
    ob_low=float(lows[-3]) if len(lows)>=3 else live
    ob_high=float(highs[-3]) if len(highs)>=3 else live
    recent_high=float(max(highs[-20:])) if len(highs)>=5 else live
    recent_low=float(min(lows[-20:])) if len(lows)>=5 else live
    entry=live
    # نقطة اللاعودة
    if fvg and abs(fvg["mid"]-live)/live <= 0.015:
        no_return=float(fvg["bottom"]) if direction=="PUMP" else float(fvg["top"])
        nr_reason="قاع FVG" if direction=="PUMP" else "قمة FVG"
        has_fvg=True
    else:
        no_return=float(ob_low) if direction=="PUMP" else float(ob_high)
        nr_reason="قاع OB" if direction=="PUMP" else "قمة OB"
        has_fvg=False
    # اهداف من الستركشر
    if direction=="PUMP":
        if fvg and fvg["top"]>live: tp1=float(fvg["top"]); tp1_r="قمة FVG"
        elif ob_high>live: tp1=float(ob_high); tp1_r="قمة OB"
        else: tp1=float(recent_high); tp1_r="القمة الاخيرة"
        tp2=float(recent_high) if recent_high>tp1 else tp1; tp2_r="القمة الاخيرة"
        model_h=tp2-no_return if tp2>no_return else 0
        tp3=tp2+model_h if model_h>0 else tp2
    else:
        if fvg and fvg["bottom"]<live: tp1=float(fvg["bottom"]); tp1_r="قاع FVG"
        elif ob_low<live: tp1=float(ob_low); tp1_r="قاع OB"
        else: tp1=float(recent_low); tp1_r="القاع الاخير"
        tp2=float(recent_low) if recent_low<tp1 else tp1; tp2_r="القاع الاخير"
        model_h=no_return-tp2 if no_return>tp2 else 0
        tp3=tp2-model_h if model_h>0 else tp2
    # Score بكل الادوات
    score=50
    reasons=[]
    if has_fvg: score+=15; reasons.append("FVG")
    else: reasons.append("OB")
    if direction=="PUMP" and live>no_return: score+=10
    if direction=="DUMP" and live<no_return: score+=10
    kz_name,in_kz=killzone_now()
    if in_kz: score+=5; reasons.append(f"Killzone {kz_name}")
    # CVD
    cvd="محايد"
    if len(closes)>=5:
        up=sum(1 for i in range(1,5) if closes[-i]>closes[-i-1])
        if up>=3: cvd="شراء>بيع"
        elif up<=1: cvd="بيع>شراء"
        if direction=="PUMP" and up>=3: score+=10; reasons.append("CVD شراء")
        if direction=="DUMP" and up<=1: score+=10; reasons.append("CVD بيع")
    # Vol Spike
    vol_msg="x1.00"
    if len(vols)>=10:
        avg=sum(vols[-10:-1])/9 if len(vols)>=10 else 1
        vs=float(vols[-1]/avg) if avg else 1.0
        vol_msg=f"x{vs:.2f}"
        if vs>=2.5: score+=10; reasons.append(f"Vol {vol_msg}")
        elif vs>=1.5: score+=5
    # تغير 1h - لو العملة طارت 50%+ ارفض - مش تنبؤ ده تحليل بعد الحركة
    chg24=None
    if len(closes)>=5:
        chg24=(closes[-1]-closes[0])/closes[0]*100 if closes[0] else 0
        if abs(chg24)>50: score-=30; reasons.append("طارت 50%+ - مرفوض")
    risk=abs(live-no_return) if live!=no_return else 0.0001
    rr1=abs(tp1-live)/risk if risk else 0
    rr2=abs(tp2-live)/risk if risk else 0
    return {"entry":entry,"no_return":no_return,"nr_reason":nr_reason,"tp1":tp1,"tp1_r":tp1_r,"tp2":tp2,"tp2_r":tp2_r,"tp3":tp3,"score":min(100,score),"reasons":" + ".join(reasons),"cvd":cvd,"vol":vol_msg,"kz":kz_name,"rr1":round(rr1,2),"rr2":round(rr2,2),"chg":round(chg24,2) if chg24 is not None else 0,"has_fvg":has_fvg}

# ===== جلب كل العملات =====
def get_all_binance():
    try:
        r=requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10)
        if r.status_code==200:
            d=[x for x in r.json() if x["symbol"].endswith("USDT")]
            d=sorted(d, key=lambda x: float(x.get("quoteVolume",0)), reverse=True)[:80]
            return [(x["symbol"], float(x["lastPrice"]), float(x.get("quoteVolume",0))) for x in d]
    except Exception: pass
    return []

def get_all_mexc():
    try:
        r=requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=10)
        if r.status_code==200:
            d=[x for x in r.json() if x["symbol"].endswith("USDT")]
            d=sorted(d, key=lambda x: float(x.get("quoteVolume",0)), reverse=True)[:80]
            return [(x["symbol"], float(x["lastPrice"]), float(x.get("quoteVolume",0))) for x in d]
    except Exception: pass
    return []

def get_all_kucoin():
    try:
        r=requests.get("https://api.kucoin.com/api/v1/market/allTickers", timeout=10)
        if r.status_code==200:
            d=[x for x in r.json().get("data",{}).get("ticker",[]) if x["symbol"].endswith("-USDT")]
            d=sorted(d, key=lambda x: float(x.get("volValue",0)), reverse=True)[:80]
            out=[]
            for x in d:
                sym=x["symbol"].replace("-","").replace("USDT","USDT")
                out.append((sym, float(x["last"]), float(x.get("volValue",0))))
            return out
    except Exception: pass
    return []

def get_all_dex():
    try:
        # ترند BSC + ETH + SOL من DexScreener
        out=[]
        for chain in ["bsc","ethereum","solana"]:
            r=requests.get(f"https://api.dexscreener.com/latest/dex/tokens/trending", timeout=8)
            break
        r=requests.get("https://api.dexscreener.com/latest/dex/search?q=BSC", timeout=8)
        if r.status_code==200:
            for p in r.json().get("pairs",[])[:30]:
                liq=float(p.get("liquidity",{}).get("usd",0) or 0)
                fdv=float(p.get("fdv",0) or 0)
                out.append({"symbol":p.get("baseToken",{}).get("symbol",""),"chain":p.get("chainId",""),"price":float(p.get("priceUsd",0) or 0),"liq":liq,"fdv":fdv,"url":p.get("url",""),"vol5":float((p.get("volume",{}) or {}).get("m5",0) or 0),"ch5":float((p.get("priceChange",{}) or {}).get("m5",0) or 0),"ch1h":float((p.get("priceChange",{}) or {}).get("h1",0) or 0)})
        return out
    except Exception: return []

# ===== الواجهة - فحص شامل =====
st.markdown("#### ⚙️ اعدادات الفحص الشامل")
colA,colB,colC,colD=st.columns(4)
with colA: platform=st.selectbox("المنصة", ["BINANCE - كل العملات","MEXC - كل العملات","KUCOIN - كل العملات","DEX - كل العملات","الكل - 4 منصات"])
with colB: direction=st.selectbox("الاتجاه", ["PUMP","DUMP"])
with colC: min_score=st.slider("اقل Score", 50, 85, 70)
with colD: max_coins=st.slider("عدد العملات المفحوصة", 20, 80, 50)

if st.button("🔍 افحص كل العملات دلوقتي", use_container_width=True):
    results=[]
    progress=st.progress(0)
    status=st.empty()
    # حدد المنصات
    plats=[]
    if "BINANCE" in platform or "الكل" in platform: plats.append("binance")
    if "MEXC" in platform or "الكل" in platform: plats.append("mexc")
    if "KUCOIN" in platform or "الكل" in platform: plats.append("kucoin")
    if "DEX" in platform or "الكل" in platform: plats.append("dex")
    total_steps=0
    for plat in plats:
        if plat=="binance": coins=get_all_binance()
        elif plat=="mexc": coins=get_all_mexc()
        elif plat=="kucoin": coins=get_all_kucoin()
        else: coins=[]
        if plat=="dex":
            dex_list=get_all_dex()
            for d in dex_list:
                # ادوات DEX الـ 15
                liq=d["liq"]; fdv=d["fdv"]; ratio=(liq/fdv*100) if fdv else 0
                rug=liq<10000 or ratio<2
                sc=50
                if d["vol5"]>5000: sc+=10
                if d["ch5"]>=5: sc+=10
                if liq>15000: sc+=10
                if d["ch1h"]>20: sc+=10
                if fdv<20000000: sc-=30
                if not rug and sc>=min_score:
                    results.append({"المنصة":"DEX","العملة":f"{d['symbol']} / {d['chain']}","السعر":d["price"],"الدخول":d["price"],"نقطة اللاعودة":"قاع OB","TP1":"قمة FVG","TP2":"القمة الاخيرة","TP3":"امتداد","Score":sc,"CVD":"-","Vol":f"{d['vol5']:.0f}","Killzone":killzone_now()[0],"اسباب":f"Vol5 {d['vol5']:.0f} + تغير 5m {d['ch5']}% + سيولة {liq:.0f}","الرابط":d["url"]})
            continue
        coins=coins[:max_coins]
        for idx,(sym,live,vol) in enumerate(coins):
            status.text(f"يفحص {plat} - {sym} - {idx+1}/{len(coins)}")
            progress.progress(min(0.99, (idx+1)/max(len(coins),1)*0.9))
            # لو العملة طارت 50%+ في 24h - تخطاها - مش تنبؤ
            try:
                if plat=="binance": highs,lows,closes,vols=get_klines_binance(sym)
                else: highs,lows,closes,vols=get_klines_mexc(sym)
                if len(closes)<10: continue
                # رفض لو طارت
                chg=(closes[-1]-closes[0])/closes[0]*100 if closes[0] else 0
                if abs(chg)>50: continue
                res=analyze_one(live, highs, lows, closes, vols, direction)
                if res and res["score"]>=min_score:
                    # منع تكرار نفس العملة في PUMP و DUMP - Direction Lock: PUMP لازم شراء>بيع - DUMP لازم بيع>شراء
                    if direction=="PUMP" and res["cvd"]=="بيع>شراء": continue
                    if direction=="DUMP" and res["cvd"]=="شراء>بيع": continue
                    results.append({"المنصة":plat.upper(),"العملة":sym,"السعر":live,"الدخول":res["entry"],"نقطة اللاعودة":res["no_return"],"TP1":res["tp1"],"TP2":res["tp2"],"TP3":res["tp3"],"Score":res["score"],"CVD":res["cvd"],"Vol":res["vol"],"Killzone":res["kz"],"اسباب":res["reasons"],"RR1":res["rr1"],"RR2":res["rr2"],"تغير":res["chg"]})
            except Exception: continue
            time.sleep(0.05)
    progress.progress(1.0)
    status.text(f"تم - {len(results)} اشارة من {max_coins} عملة لكل منصة")
    if not results:
        st.warning("السوق هادي - مفيش اشارة قوية - ده احسن من اشارات ضعيفة")
        st.caption("جرب تنزل Score لـ 60 او غير المنصة")
    else:
        # ترتيب باعلى Score
        results=sorted(results, key=lambda x: x["Score"], reverse=True)
        st.success(f"✅ {len(results)} اشارة قوية - Score >= {min_score}")
        # جدول
        st.dataframe(results, use_container_width=True)
        # كروت لاول 10
        st.markdown("### 🔥 اقوى 10 اشارات")
        for r in results[:10]:
            with st.expander(f"{r['العملة']} - {r['المنصة']} - Score {r['Score']} - دخول {r['الدخول']}"):
                st.markdown(f"**السعر اللحظي:** {r['السعر']} | **الدخول:** {r['الدخول']} | **الاستوب - نقطة اللاعودة:** {r['نقطة اللاعودة']}")
                st.markdown(f"**TP1:** {r['TP1']} | **TP2:** {r['TP2']} | **TP3 رنر:** {r['TP3']}")
                st.markdown(f"**CVD:** {r['CVD']} | **Vol:** {r['Vol']} | **Killzone:** {r['Killzone']} | **RR1:** {r.get('RR1','-')} | **RR2:** {r.get('RR2','-')}")
                st.markdown(f"**الاسباب:** {r['اسباب']}")
                st.markdown("**الخطة:** TP1 40% - TP2 30% - حرك الوقف للدخول - 30% رنر لـ TP3")

st.markdown("---")
st.caption("BLY7H ELITE - @WHYNOTBLY7 - فحص كل العملات - الدخول لحظي - الاستوب = نقطة اللاعودة - الاهداف من الستركشر - لا ارقام عشوائية - المنصات: BINANCE + MEXC + KUCOIN + DEX")
