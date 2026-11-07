# Bly Ultimate Scanner V10 - الاستوب = نقطة اللاعودة - لا ارقام عشوائية - الدخول من السعر اللحظي - FIX FVG القديم
import pandas as pd
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(signal):
    if not TELEGRAM_BOT_TOKEN or signal['score'] < 75:
        return
    message = f"BLY7H Scanner - {signal['symbol']} Score {signal['score']}"
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except:
        pass

class Tier1_SMC:
    def detect_fvg(self, df):
        fvg_list = []
        try:
            for i in range(1, len(df)-1):
                if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
                    fvg_list.append({'type':'bullish', 'top': df['low'].iloc[i+1], 'bottom': df['high'].iloc[i-1], 'mid': (df['low'].iloc[i+1] + df['high'].iloc[i-1])/2 })
        except:
            pass
        return fvg_list
    def detect_order_block(self, df):
        try:
            return {'ob_low': df['low'].iloc[-3], 'ob_high': df['high'].iloc[-3]}
        except:
            return {'ob_low': df['low'].iloc[-1], 'ob_high': df['high'].iloc[-1]}
    def get_best_entry_and_no_return(self, fvg, ob, last_price):
        # V10: لا ارقام عشوائية
        # نقطة اللاعودة = قاع FVG بالظبط - مش قاع * 0.99 ولا * 0.98
        # لو السعر قفل تحت قاع FVG -> النموذج مات - خروج فورا
        # لو مفيش FVG -> نقطة اللاعودة = قاع Order Block بالظبط
        if fvg:
            last_fvg = fvg[-1]
            fvg_mid = last_fvg['mid']
            dist = abs(fvg_mid - last_price) / last_price if last_price else 1
            if dist > 0.015:
                # FVG قديم - نقطة اللاعودة = قاع Order Block - مش رقم عشوائي
                _nr = float(ob.get('ob_low', last_price)) if ob else last_price
                return {'best_entry': last_price, 'no_return': _nr, 'no_return_reason': 'قاع Order Block', 'fvg': last_fvg, 'ob': ob, 'has_fvg': False, 'fvg_stale': True, 'fvg_mid_old': fvg_mid}
            _nr = float(last_fvg['bottom'])  # قاع FVG بالظبط
            return {'best_entry': last_price, 'no_return': _nr, 'no_return_reason': 'قاع FVG - كسره = النموذج مات', 'fvg': last_fvg, 'ob': ob, 'has_fvg': True, 'fvg_stale': False}
        else:
            _nr = float(ob.get('ob_low', last_price)) if ob else last_price
            return {'best_entry': last_price, 'no_return': _nr, 'no_return_reason': 'قاع Order Block', 'fvg': {}, 'ob': ob, 'has_fvg': False, 'fvg_stale': False}

class Tier2_Professional:
    def check_oi_divergence(self, price_change, oi_change):
        if price_change > 0 and oi_change < -2:
            return {'signal': 'FAKE_PUMP', 'score': -10}
        if abs(price_change) < 1 and oi_change > 3:
            return {'signal': 'REAL_ACCUMULATION', 'score': 15}
        return {'signal': 'NEUTRAL', 'score': 5}
    def check_liquidation_map(self, liq_data):
        if liq_data['long_liq_above'] > 30:
            return {'target': 'UP', 'score': 10}
        return {'target': 'NEUTRAL', 'score': 0}

class Tier3_Institutional:
    def check_premium_gap(self, spot_price, futures_price):
        try:
            premium = (futures_price - spot_price) / spot_price * 100 if spot_price else 0
            if premium > 0.2:
                return {'premium': premium, 'score': 10}
            return {'premium': premium, 'score': 3}
        except:
            return {'premium': 0, 'score': 0}
    def check_killzone(self, current_hour_egypt):
        if current_hour_egypt in [10,11,12,13,14,15,16,17,18,19]:
            return {'in_killzone': True, 'score': 5}
        return {'in_killzone': False, 'score': 0}
    def check_amd(self, price_action):
        if price_action == 'MANIPULATION_DOWN':
            return {'phase': 'MANIPULATION', 'score': 15}
        return {'phase': 'ACCUMULATION', 'score': 5}
    def check_stablecoin_flow(self, usdt_inflow):
        if usdt_inflow > 30:
            return {'score': 10}
        return {'score': 3}

class BlyUltimateScanner:
    def __init__(self):
        self.t1 = Tier1_SMC()
        self.t2 = Tier2_Professional()
        self.t3 = Tier3_Institutional()
    def calculate_pump_score(self, df, market_data):
        try:
            score = 10
            reasons = []
            fvg = self.t1.detect_fvg(df)
            ob = self.t1.detect_order_block(df)
            last_price = market_data.get('spot', 0)
            if last_price == 0 and len(df)>0:
                last_price = float(df['close'].iloc[-1])
            entry_data = self.t1.get_best_entry_and_no_return(fvg, ob, last_price)
            if entry_data['has_fvg']:
                score += 25
                reasons.append("FVG")
            else:
                score += 5
                reasons.append("Watch")
            oi_res = self.t2.check_oi_divergence(market_data['price_change'], market_data['oi_change'])
            score += oi_res['score']
            liq_res = self.t2.check_liquidation_map(market_data['liq'])
            score += liq_res.get('score',0)
            prem = self.t3.check_premium_gap(market_data['spot'], market_data['futures'])
            score += prem.get('score',0)
            kill = self.t3.check_killzone(market_data['hour_eg'])
            score += kill['score']
            amd = self.t3.check_amd(market_data['amd_phase'])
            score += amd.get('score',0)
            flow = self.t3.check_stablecoin_flow(market_data['usdt_flow'])
            score += flow.get('score',0)
            # === V9: اهداف ديناميك على حسب النموذج - مش 2% و 5% ثابت ===
            # لو العملة هتعمل 50x - الهدف الثابت 5% بيقتلك
            # الهدف لازم يتحسب من: حجم FVG + ATR + اقرب قمة / سيولة
            try:
                # ATR من اخر 14 شمعة
                _hl = (df['high'] - df['low']).tail(14).mean() if len(df) >= 14 else last_price * 0.02
                _atr = float(_hl) if _hl and _hl > 0 else last_price * 0.02
                # ارتفاع FVG
                _fvg_h = 0
                if entry_data.get('fvg'):
                    _fvg_h = float(entry_data['fvg'].get('top', 0) - entry_data['fvg'].get('bottom', 0)) if entry_data['fvg'].get('top') else 0
                _fvg_h = abs(_fvg_h) if _fvg_h else 0
                # اقرب قمة اخر 20 شمعة = هدف السيولة
                _recent_high = float(df['high'].tail(20).max()) if len(df) >= 5 else last_price * 1.10
                _recent_low = float(df['low'].tail(20).min()) if len(df) >= 5 else last_price * 0.90
                # الوقف من الستركشر مش ثابت: تحت قاع FVG / قاع اخر 20 شمعة
                _sl_struct = float(entry_data['no_return'])  # الاستوب = نقطة اللاعودة بالظبط - مش * 0.998 ولا اي رقم عشوائي
                # V10: اهداف من الستركشر - مش ارقام عشوائية
                # TP1 = قمة FVG بالظبط - اول منطقة سيولة / عرض
                # TP2 = القمة الاخيرة - منطقة السيولة اللي السعر رايحلها
                # TP3 = الرنر - القمة اللي بعدها / امتداد النموذج - مش 3x رقم عشوائي
                # لو مفيش FVG - TP1 = قمة Order Block
                _fvg_top = float(entry_data['fvg'].get('top', 0)) if entry_data.get('fvg') and entry_data['fvg'].get('top') else 0
                _ob_high = float(ob.get('ob_high', 0)) if isinstance(ob, dict) and ob.get('ob_high') else 0
                if _fvg_top and _fvg_top > last_price:
                    _tp1 = _fvg_top
                    _tp1_reason = 'قمة FVG'
                elif _ob_high and _ob_high > last_price:
                    _tp1 = _ob_high
                    _tp1_reason = 'قمة Order Block'
                else:
                    _tp1 = _recent_high
                    _tp1_reason = 'القمة الاخيرة'
                if _recent_high > _tp1:
                    _tp2 = _recent_high
                    _tp2_reason = 'القمة الاخيرة - منطقة السيولة'
                else:
                    _tp2 = _tp1
                    _tp2_reason = 'قمة FVG - لا توجد قمة اعلى'
                # TP3: امتداد النموذج = مسافة الدخول -> TP2 مضروبة مرة واحدة - من قاع النموذج لقمته
                # مش رقم عشوائي: TP3 = TP2 + (TP2 - نقطة اللاعودة)
                _model_height = _tp2 - _sl_struct if _tp2 > _sl_struct else 0
                _tp3 = _tp2 + _model_height if _model_height > 0 else _tp2
                _tp3_reason = 'امتداد النموذج: TP2 + ارتفاع النموذج كامل'
                _tp2_dist = _tp2 - last_price if _tp2 > last_price else 0
                _rr1 = (_tp1 - last_price) / (last_price - _sl_struct) if last_price > _sl_struct else 0
                _rr2 = (_tp2 - last_price) / (last_price - _sl_struct) if last_price > _sl_struct else 0
            except Exception:
                _sl_struct = float(entry_data['no_return'])  # نقطة اللاعودة بالظبط
                _tp1 = _recent_high if '_recent_high' in locals() else last_price
                _tp2 = _tp1
                _tp3 = _tp1
                _tp1_reason = 'القمة الاخيرة - لا يوجد نموذج'
                _tp2_reason = 'القمة الاخيرة'
                _tp3_reason = 'لا يوجد امتداد - لا يوجد نموذج'
                _atr = last_price * 0.02
                _rr1 = 0; _rr2 = 0
                _recent_high = last_price * 1.10

            final_signal = {
                'symbol': market_data['symbol'],
                'score': max(5, min(100, score)),
                'best_entry': entry_data['best_entry'],
                'no_return_point': entry_data['no_return'],
                'live_price': last_price,
                'entry_is_live': True,
                'stop_loss': _sl_struct,
                # اهداف ديناميك - مش ثابتة
                'take_profit_1': _tp1,
                'take_profit_2': _tp2,
                'take_profit_3_runner': _tp3,
                'atr': _atr,
                'recent_high_liquidity_target': _recent_high,
                'rr_tp1': round(_rr1, 2),
                'rr_tp2': round(_rr2, 2),
                'stop_is_no_return': True,
                'stop_reason': entry_data.get('no_return_reason', 'قاع FVG'),
                'tp1_reason': _tp1_reason if '_tp1_reason' in locals() else 'قمة FVG',
                'tp2_reason': _tp2_reason if '_tp2_reason' in locals() else 'القمة الاخيرة',
                'tp3_reason': _tp3_reason if '_tp3_reason' in locals() else 'امتداد النموذج',
                # ادارة الصفقة للـ 50x: متقفلهاش كلها
                'plan': 'TP1: اقفل 40% - TP2: اقفل 30% - حرك الوقف لنقطة الدخول - سيب 30% رنر لـ TP3',
                'model_based': True,
                'reasons': reasons,
            }
            if final_signal['score'] >= 75:
                send_telegram_alert(final_signal)
            return final_signal
        except Exception as e:
            return {
                'symbol': market_data.get('symbol','UNKNOWN'),
                'score': 25,
                'best_entry': market_data.get('spot',0),
                'no_return_point': market_data.get('spot',0),
                'stop_loss': market_data.get('spot',0),  # نقطة اللاعودة
                'take_profit_1': market_data.get('spot',0) * 1.04,
                'take_profit_2': market_data.get('spot',0) * 1.10,
                'take_profit_3_runner': market_data.get('spot',0) * 1.35,
                'plan': 'TP1: 40% - TP2: 30% - رنر 30% لـ TP3',
                'reasons': ['fallback'],
            }
