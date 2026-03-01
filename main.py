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
    Regime-aware pre-filter for 0DTE credit spreads.
    Applies different logic depending on day_type:
    - "Trending"
    - "Range-bound"
    """

    message = ""
    day_type = features.get("day_type", "Trending")

    vix = features["vix"]
    minutes_left = features["time_to_close_min"]

    slope_5  = features["ema21_slope_5min"]
    slope_15 = features["ema21_slope_15min"]
    ret5     = features["ret_5min_pct"]
    ret15    = features["ret_15min_pct"]
    rsi      = features["rsi"]
    premium_ratio = features["premium_ratio"]
    bb_upper = features["bb_upper"]
    bb_lower = features["bb_lower"]
    current_price = features["current_price"]
    bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)

    # ─────────────────────────────────────────────────────────────
    # 1️⃣ Global Hard Risk Filters (Apply to ALL regimes)
    # ─────────────────────────────────────────────────────────────

    if vix < 13.0:
        message = f"VIX too low ({vix}) — premiums too thin."
    elif vix > 40.0:
        message = f"VIX extremely high ({vix}) — elevated gap risk."
    elif minutes_left > 360:
        message = f"Too early in the session ({features['current_time']})."
    elif minutes_left < 60:
        message = f"Too late in the session ({features['current_time']}) — gamma risk elevated."

    # ─────────────────────────────────────────────────────────────
    # 2️⃣ Regime-Specific Logic
    # ─────────────────────────────────────────────────────────────
    else:

        # ==========================================================
        # 📈 TRENDING DAY LOGIC
        # ==========================================================
        if day_type == "Trending":

            # Avoid explosive continuation
            if abs(ret5) > 0.8 or abs(ret15) > 1.4:
                message = f"Strong momentum (5m: {ret5}%, 15m: {ret15}%) — avoid chasing."

            # Avoid ultra steep slope
            elif abs(slope_5) > 3.0:
                message = f"Steep slope ({slope_5}) — trend not exhausted."

            # Neutral RSI = weak edge on trend days
            elif 35 < rsi < 65:
                message = f"RSI neutral ({rsi}) — weak directional edge for trending day."

            # Premium imbalance suggests directional pressure
            elif premium_ratio <= 3.0:
                message = f"Premium ratio low ({premium_ratio}) — possible directional skew."

        # ==========================================================
        # 📉 RANGE-BOUND DAY LOGIC
        # ==========================================================
        elif day_type == "Range-bound":

            # In range days, strong movement = breakout risk
            if abs(ret5) > 0.6 or abs(ret15) > 1.0:
                message = f"Movement too strong for range day (5m: {ret5}%, 15m: {ret15}%) — breakout risk."

            # Slopes should be flat
            elif abs(slope_5) > 2.0:
                message = f"Slope too steep ({slope_5}) — not ideal for range structure."

            # Extreme RSI in range day may signal breakout attempt
            elif rsi < 20 or rsi > 80:
                message = f"RSI extreme ({rsi}) — range may be breaking."

            # 3️⃣ HARD FILTER: avoid mid-range zone
            elif 0.35 < bb_position < 0.65:
                message = f"Price in middle of range (BB pos {bb_position:.2f}) — no edge."


            # 4️⃣ Require at least mild RSI stretch
            elif 42 <= rsi <= 58:
                message = f"RSI too neutral ({rsi}) for high-probability mean reversion."

            # Premium ratio can be lower in range days
            elif premium_ratio < 3.0:
                message = f"Premium ratio too compressed ({premium_ratio}) even for range day."

        else:
            message = f"Unknown day_type: {day_type}"

    # ─────────────────────────────────────────────────────────────
    # 3️⃣ Final Decision
    # ─────────────────────────────────────────────────────────────
    if not message:
        return True

    alert(features["current_time"] + "--" + message, silent=True)
    print(message)
    return False

def main():

    ##"2026-02-12" -- big down day
    ##"2026-02-27" -- range day

    date_in = "2026-02-23" #"2026-02-23" #"2026-02-23" #"2026-01-29" #"2026-01-30" # live
    time_in = "09:30:00" #"09:30:00" #"09:30:00" #"10:30:00" #"10:30:00"
    config = load_config()

    state = load_last_alert_state()
    last_alert_time = state["last_alert_time"]
    last_alert_price = state["last_alert_price"]

    print(f"Loaded last alert: time={last_alert_time}, price={last_alert_price}")
    
    # get data for last working day from date_in as string
    if not date_in or date_in.strip() == "":
        last_working_day = pd.Timestamp.now(tz="America/New_York") - pd.offsets.BDay(1)
        current_day_end = pd.Timestamp.now(tz="America/New_York").replace(hour=16, minute=0, second=0, microsecond=0)
        run_type = "live"
    else:
        last_working_day = pd.to_datetime(date_in) - pd.offsets.BDay(1)
        current_day_end = pd.to_datetime(date_in).replace(hour=16, minute=0, second=0, microsecond=0)
        run_type = "backtest"
    
    last_working_day = last_working_day.strftime("%Y-%m-%d")
    history = fetch_market_data(config["api"],config[run_type]['interval_min'],date_in=last_working_day)

    print("📡 SPX 0-DTE Monitor Started...\n")

    
    while True:
        try:
            df = fetch_market_data(config["api"],config[run_type]['interval_min'],date_in=date_in, time_in=time_in)

            all_df = pd.concat([history, df])
            all_df = all_df.tail(config[run_type]["history_size"])

            all_df = add_indicators(all_df, config["indicators"]["rsi_period"])

            latest = all_df.iloc[-1]

            # check if current_time is equal to the time_in or todays date if time_in is None
            


            features = {
                        # ─── Core level & fear ───
                        "current_price": round(latest["spx"], 2),
                        "expected_move": round(latest["spxExpectedMove"], 2),
                        "vix": round(latest["vix"], 2),
                        "day_type": latest["day_type"],
                        
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

                        
                        "ret_5min_pct":   round(latest.get("ret_5min", 0), 2),
                        "ret_15min_pct":  round(latest.get("ret_15min", 0), 2),
                        "ret_30min_pct":  round(latest.get("ret_30min", 0), 2),

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

        # exit the loop if we latest.name.strftime('%Y-%m-%d %H:%M:%S') is equal to  current_day_end
        if latest.name >= current_day_end.tz_localize(latest.name.tzinfo):
            print(f"Reached end of day ({current_day_end}), exiting.")
            break

        

if __name__ == "__main__":
    main()
