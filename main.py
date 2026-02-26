import time
import yaml
import pandas as pd

from data.fetcher import fetch_market_data
from indicators.technicals import add_indicators
from alerts.console_alert import send_alert, load_last_alert_state , log_decision , save_last_alert_state,del_last_alert_state, alert
from agent.agent import evaluate_with_agent
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np


# ✅ Load environment variables from .env file
load_dotenv()
ALERT_COOLDOWN_MINUTES = 30          # minimum time between alerts
PRICE_TOLERANCE_POINTS = 18          # skip if SPX moved less than this from last alert
MARKET_TZ = ZoneInfo("America/New_York")
MARKET_OPEN = (9, 30)     # 10:00 AM ET
MARKET_CLOSE = (16, 00)  # 2:30 PM ET


def is_market_window(now_et: datetime) -> bool:
    start = now_et.replace(hour=MARKET_OPEN[0], minute=MARKET_OPEN[1], second=0, microsecond=0)
    end = now_et.replace(hour=MARKET_CLOSE[0], minute=MARKET_CLOSE[1], second=0, microsecond=0)
    return start <= now_et <= end


def load_config():
    with open("config/strategy.yaml", "r") as f:
        return yaml.safe_load(f)


def should_consider_trade(features: dict) -> bool:
    """
    Basic gate / pre-filter: should we even look at PCS or CCS setups right now?
    Returns True only if general conditions are acceptable to consider a credit spread.
    """
    message = ""

    # ─── Required minimum conditions ────────────────────────────────────────
    
    # 1. VIX not too low → premiums need to be decent
    if features["vix"] < 14.0:
        message = f"VIX too low ({features['vix']}) — premiums likely too thin for good credit spreads."
    
    # 2. Not ridiculously high VIX (extreme fear / gap risk)
    elif features["vix"] > 38.0:
        message = f"VIX too high ({features['vix']}) — extreme fear, gap risk, and likely not ideal for new credit spreads."
    
    # 3. Time window — best theta decay & lower gamma risk
    else:
        minutes_left = features["time_to_close_min"]
        if minutes_left > 330:   # before ~9:45–10:00 ET
            message = f"Too early in the day ({features['current_time']}) — market just opened, not ideal for new credit spreads."
        elif minutes_left < 60:    # last hour — gamma explosion risk, especially 0DTE
            message = f"Too late in the day ({features['current_time']}) — last hour, gamma risk increases significantly for 0DTE credit spreads."
        
        # 4. Trend filter — avoid fighting very strong short-term momentum
        #    We want mild trend or range → good for credit spreads
        else:
            slope_5  = features["ema21_slope_5min"]
            slope_15 = features["ema21_slope_15min"]
            ret5     = features["ret_5min_pct"]
            ret15    = features["ret_15min_pct"]

            # Very strong momentum in last 5–15 min → usually bad for new credit spreads
            if abs(ret5) > 0.80 or abs(ret15) > 1.40:
                message = f"Strong momentum detected (5min: {ret5}%, 15min: {ret15}%) — usually not ideal for new credit spreads."
            # Very steep short-term slope → momentum is probably not exhausted yet
            elif abs(slope_5) > 3.0:   # adjust threshold after backtesting (~3–4 pts/min is fast)
                message = f"Steep short-term slope detected (5min EMA21 slope: {slope_5} pts/min) — momentum may not be exhausted, not ideal for new credit spreads."
            
            # ─── Optional / tunable filters (comment out if too restrictive) ─────────
            elif features["premium_ratio"] < 3.0:
                message = f"Premium ratio too low ({features['premium_ratio']}) — may indicate directional bias, not ideal for balanced credit spreads."
            elif features["rsi"] < 18 or features["rsi"] > 82:
                message = f"RSI in extreme territory ({features['rsi']}) — may indicate overbought/oversold conditions, often better to wait for mean reversion before opening new credit spreads."
            elif features["rsi"] > 40 and features["rsi"] < 60:
                message = f"RSI is neutral ({features['rsi']}) — may indicate lack of momentum, not ideal for new credit spreads which often benefit from some directional bias."

    # ─── If we passed everything → okay to evaluate PCS / CCS logic next ─────
    if not message:
        return True

    alert(features["current_time"] + "--" + message,silent=True)
    print(message)
    return False

def main():

    ##"2026-02-12" -- big down day
    date_in = "2026-02-23" #"2026-02-23" #"2026-01-29" #"2026-01-30" # live
    time_in = "09:30:00" #"09:30:00" #"10:30:00" #"10:30:00"
    config = load_config()

    state = load_last_alert_state()
    last_alert_time = state["last_alert_time"]
    last_alert_price = state["last_alert_price"]

    print(f"Loaded last alert: time={last_alert_time}, price={last_alert_price}")
    
    # get data for last working day from date_in as string
    if not date_in or date_in.strip() == "":
        last_working_day = pd.Timestamp.now(tz="America/New_York") - pd.offsets.BDay(1)
        run_type = "live"
    else:
        last_working_day = pd.to_datetime(date_in) - pd.offsets.BDay(1)
        run_type = "backtest"
    
    last_working_day = last_working_day.strftime("%Y-%m-%d")
    history = fetch_market_data(config["api"],config[run_type]['interval_min'],date_in=last_working_day)

    print("📡 SPX 0-DTE Monitor Started...\n")

    
    while True:
        try:
            df = fetch_market_data(config["api"],config[run_type]['interval_min'],date_in=date_in, time_in=time_in)

            history = pd.concat([history, df])
            history = history.tail(config[run_type]["history_size"])

            history = add_indicators(history, config["indicators"]["rsi_period"])

            latest = history.iloc[-1]

            # check if current_time is equal to the time_in or todays date if time_in is None
            


            features = {
                        # ─── Core level & fear ───
                        "current_price": round(latest["spx"], 2),
                        "expected_move": round(latest["spxExpectedMove"], 2),
                        "vix": round(latest["vix"], 2),
                        
                        # ─── Momentum classics ───
                        "rsi": round(latest["rsi"], 1),
                        "macd": round(latest["macd"], 4),
                        "macd_hist": round(latest["macd_hist"], 4),
                        "macd_signal": round(latest["macd_signal"], 4),

                        # Add missing BB fields (adjust calculation if not directly in 'latest')
                        "bb_upper": round(latest.get("bb_upper", np.nan), 2),  # e.g., if it's price relative to upper band
                        "bb_lower": round(latest.get("bb_lower", np.nan), 2),  # e.g., if it's price relative to lower band
                        "bb_middle": round(latest.get("bb_middle", np.nan), 2), # e.g., if it's price relative to middle band

                        # ─── 0DTE + time sensitive ───
                        "premium_ratio": round(latest["premium_ratio"], 2),
                        "time_to_close_min": int(latest["time_to_close"]),
                        "current_time": latest.name.strftime('%Y-%m-%d %H:%M:%S'),
                        

                        # ─── Position vs structure (most important upgrades) ───
                        "ema9": round(latest.get("ema9", np.nan), 4),
                        "ema21": round(latest.get("ema21", np.nan), 4),
                        "ema50": round(latest.get("ema50", np.nan), 4),
                        

                        "ema21_slope_5min": round(latest["ema21_slope_5min"], 6),
                        "ema21_slope_15min": round(latest["ema21_slope_15min"], 6),
                        "ema21_slope_30min": round(latest["ema21_slope_30min"], 6),

                        
                        "ret_5min_pct":   round(latest.get("ret_5min", 0) * 100, 2),
                        "ret_15min_pct":  round(latest.get("ret_15min", 0) * 100, 2),
                        "ret_30min_pct":  round(latest.get("ret_30min", 0) * 100, 2),

                        # Optional safety net: full row if you want to allow pattern spotting
                        #"raw_row": latest.to_dict()   # ← only if token budget allows
                    }
            

            # if time_in is is not none then increment time_in by config["runtime"]['interval_min']
            if time_in:
                t = pd.to_datetime(time_in) + pd.Timedelta(minutes=config[run_type]['interval_min'])
                time_in = t.strftime("%H:%M:%S")


            now = latest.name
            if last_alert_time:
                minutes_since = (now - last_alert_time).total_seconds() / 60
                if minutes_since < ALERT_COOLDOWN_MINUTES:
                    print(f"⏳ Cooldown active — {minutes_since:.1f} min since last alert (need ≥ {ALERT_COOLDOWN_MINUTES})")
                    time.sleep(config[run_type]["fetch_interval_sec"])
                    continue
                else:
                    print(f"✅ Cooldown passed — {minutes_since:.1f} min since last alert")
                    last_alert_time = None  # reset to allow new alerts
                    last_alert_price = None
                    del_last_alert_state()

            print(latest.name.strftime(("%Y-%m-%d %H:%M:%S")) )
            if should_consider_trade(features):   
                #print(latest)  
                decision = evaluate_with_agent(features)
                log_decision(decision.model_dump(), features)

                if decision.trade and decision.confidence >= 0.7:
                    send_alert(decision.model_dump(), latest)
                    
                    # Update persistent state
                    last_alert_time = now
                    last_alert_price = round(latest["spx"], 2)
                    save_last_alert_state(last_alert_time, last_alert_price)

                else:
                    print("🤖 Agent says: no clean setup.")     


        except Exception as e:
            print("❌ Error:", e)

        time.sleep(config[run_type]["fetch_interval_sec"])
        print("-" * 50)

        # close the while loop if features['time_to_close_min'] is zer0
        # if features["time_to_close_min"] <= 0:
        #     print("Market closed — ending monitor.")
        #     break

if __name__ == "__main__":
    main()
