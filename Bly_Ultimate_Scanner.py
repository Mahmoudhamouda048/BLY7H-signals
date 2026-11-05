# Bly Ultimate Scanner - كل الطبقات
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
    message = f"""
🚀 Bly Ultimate Scanner
💰 العملة: {signal['symbol']}
📊 السكور: {signal['score']}/100
🎯 دخول: {signal['best_entry']}
🚫 الغاء: {signal['no_return_point']}
"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"خطأ: {e}")

class Tier1_SMC:
    def detect_fvg(self, df):
        fvg_list = []
        for i in range(1, len(df)-1):
            if df['low'].iloc[i+1] > df['high'].iloc[i-1]:
                fvg_list.append({'type':'bullish', 'top': df['low'].iloc[i+1], 'bottom': df['high'].iloc[i-1], 'mid': (df['low'].iloc[i+1] + df['high'].iloc[i-1])/2 })
        return fvg_list
    def detect_order_block(self, df):
        return {'ob_low': df['low'].iloc[-3], 'ob_high': df['high'].iloc[-3]}
    def get_best_entry_and_no_return(self, fvg, ob):
        if not fvg: return None
        last_fvg = fvg[-1]
        best_entry = last_fvg['mid']
        no_return_point = last_fvg['bottom'] * 0.99
        return {'best_entry': best_entry, 'no_return': no_return_point, 'fvg': last_fvg, 'ob': ob}

class Tier2_Professional:
    def check_oi_divergence(self, price_change, oi_change):
        if price_change > 0 and oi_change < -2:
            return {'signal': 'FAKE_PUMP', 'score': -20}
        if abs(price_change) < 1 and oi_change > 5:
            return {'signal': 'REAL_ACCUMULATION', 'score': +25}
        return {'signal': 'NEUTRAL', 'score': 0}
    def check_liquidation_map(self, liq_data):
        if liq_data['long_liq_above'] > 50:
            return {'target': 'UP', 'reason': f"فيه {liq_data['long_liq_above']}M تصفيات فوق"}
        return {'target': 'NEUTRAL'}

class Tier3_Institutional:
    def check_premium_gap(self, spot_price, futures_price):
        premium = (futures_price - spot_price) / spot_price * 100
        if premium > 0.3:
            return {'premium': premium, 'signal': 'WHALES_BUYING_FUTURES', 'score': +15}
        return {'premium': premium, 'signal': 'NEUTRAL'}
    def check_killzone(self, current_hour_egypt):
        if current_hour_egypt in [10,11,12,16,17,18]:
            return {'in_killzone': True, 'score': +10}
        return {'in_killzone': False, 'score': -10}
    def check_amd(self, price_action):
        if price_action == 'MANIPULATION_DOWN':
            return {'phase': 'MANIPULATION', 'entry_quality': 'GOLDEN', 'score': +30}
        return {'phase': 'UNKNOWN'}
    def check_stablecoin_flow(self, usdt_inflow):
        if usdt_inflow > 50:
            return {'flow': usdt_inflow, 'signal': 'FUEL_ADDED', 'score': +20}
        return {'signal': 'NONE'}

class BlyUltimateScanner:
    def __init__(self):
        self.t1 = Tier1_SMC()
        self.t2 = Tier2_Professional()
        self.t3 = Tier3_Institutional()
    def calculate_pump_score(self, df, market_data):
        score = 0
        reasons = []
        fvg = self.t1.detect_fvg(df)
        ob = self.t1.detect_order_block(df)
        entry_data = self.t1.get_best_entry_and_no_return(fvg, ob)
        if not entry_data: return None
        score += 40
        oi_res = self.t2.check_oi_divergence(market_data['price_change'], market_data['oi_change'])
        score += oi_res['score']
        liq_res = self.t2.check_liquidation_map(market_data['liq'])
        if liq_res['target'] == 'UP': score += 15
        prem = self.t3.check_premium_gap(market_data['spot'], market_data['futures'])
        score += prem.get('score',0)
        kill = self.t3.check_killzone(market_data['hour_eg'])
        score += kill['score']
        amd = self.t3.check_amd(market_data['amd_phase'])
        score += amd.get('score',0)
        flow = self.t3.check_stablecoin_flow(market_data['usdt_flow'])
        score += flow.get('score',0)
        final_signal = {
            'symbol': market_data['symbol'],
            'score': max(0, min(100, score)),
            'best_entry': entry_data['best_entry'],
            'no_return_point': entry_data['no_return'],
            'stop_loss': entry_data['no_return'] * 0.998,
            'take_profit_1': entry_data['best_entry'] * 1.02,
            'take_profit_2': entry_data['best_entry'] * 1.05,
            'reasons': reasons,
        }
        if final_signal['score'] >= 75:
            send_telegram_alert(final_signal)
        return final_signal
