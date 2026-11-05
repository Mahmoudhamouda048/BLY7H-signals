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
                    fvg_list.append({'mid': (df['low'].iloc[i+1] + df['high'].iloc[i-1])/2, 'bottom': df['high'].iloc[i-1]})
        except:
            pass
        return fvg_list
    def detect_order_block(self, df):
        try:
            return {'ob_low': df['low'].iloc[-3]}
        except:
            return {'ob_low': df['low'].iloc[-1]}
    def get_best_entry_and_no_return(self, fvg, ob, last_price):
        if fvg:
            return {'best_entry': fvg[-1]['mid'], 'no_return': fvg[-1]['bottom']*0.99, 'has_fvg': True}
        else:
            return {'best_entry': last_price, 'no_return': last_price*0.97, 'has_fvg': False}

class Tier2_Professional:
    def check_oi_divergence(self, price_change, oi_change):
        return {'score': 15} if abs(price_change)<1 and oi_change>3 else {'score': 5}
    def check_liquidation_map(self, liq_data):
        return {'score': 10} if liq_data['long_liq_above']>30 else {'score': 0}

class Tier3_Institutional:
    def check_premium_gap(self, s, f):
        try:
            premium = (f-s)/s*100 if s else 0
            return {'score': 10} if premium>0.2 else {'score': 3}
        except:
            return {'score': 0}
    def check_killzone(self, h):
        return {'score': 5} if h in [10,11,12,13,14,15,16,17,18,19] else {'score': 0}
    def check_amd(self, p):
        return {'score': 15} if p=='MANIPULATION_DOWN' else {'score': 5}
    def check_stablecoin_flow(self, u):
        return {'score': 10} if u>30 else {'score': 3}

class BlyUltimateScanner:
    def __init__(self):
        self.t1=Tier1_SMC(); self.t2=Tier2_Professional(); self.t3=Tier3_Institutional()
    def calculate_pump_score(self, df, market_data):
        try:
            score=10; last_price=market_data.get('spot', float(df['close'].iloc[-1]) if len(df)>0 else 0)
            fvg=self.t1.detect_fvg(df); ob=self.t1.detect_order_block(df)
            entry=self.t1.get_best_entry_and_no_return(fvg, ob, last_price)
            score+= 25 if entry['has_fvg'] else 5
            score+= self.t2.check_oi_divergence(market_data['price_change'], market_data['oi_change'])['score']
            score+= self.t2.check_liquidation_map(market_data['liq'])['score']
            score+= self.t3.check_premium_gap(market_data['spot'], market_data['futures'])['score']
            score+= self.t3.check_killzone(market_data['hour_eg'])['score']
            score+= self.t3.check_amd(market_data['amd_phase'])['score']
            score+= self.t3.check_stablecoin_flow(market_data['usdt_flow'])['score']
            final={'symbol':market_data['symbol'],'score':max(5,min(100,score)),'best_entry':entry['best_entry'],'no_return_point':entry['no_return'],'stop_loss':entry['no_return']*0.998,'take_profit_1':entry['best_entry']*1.02,'take_profit_2':entry['best_entry']*1.05,'reasons':[]}
            return final
        except:
            return {'symbol':market_data.get('symbol','UNKNOWN'),'score':25,'best_entry':market_data.get('spot',0),'no_return_point':market_data.get('spot',0)*0.97,'stop_loss':0,'take_profit_1':0,'take_profit_2':0,'reasons':[]}
