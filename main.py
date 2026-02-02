import time
import yaml
import pandas as pd

from data.fetcher import fetch_market_data
from indicators.technicals import add_indicators
from alerts.console_alert import send_alert, load_last_alert_state , log_decision , save_last_alert_state,del_last_alert_state
from agent.agent import evaluate_with_agent
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ✅ Load environment variables from .env file
load_dotenv()
ALERT_COOLDOWN_MINUTES = 25          # minimum time between alerts
PRICE_TOLERANCE_POINTS = 18          # skip if SPX moved less than this from last alert
MARKET_TZ = ZoneInfo("America/New_York")
MARKET_OPEN = (10, 0)     # 10:00 AM ET
MARKET_CLOSE = (14, 30)  # 2:30 PM ET


def is_market_window(now_et: datetime) -> bool:
    start = now_et.replace(hour=MARKET_OPEN[0], minute=MARKET_OPEN[1], second=0, microsecond=0)
    end = now_et.replace(hour=MARKET_CLOSE[0], minute=MARKET_CLOSE[1], second=0, microsecond=0)
    return start <= now_et <= end


def load_config():
    with open("config/strategy.yaml", "r") as f:
        return yaml.safe_load(f)


def main():
    date_in = "2026-01-29" #"2026-01-30" # live
    time_in = "10:30:00" #"10:30:00"
    config = load_config()

    state = load_last_alert_state()
    last_alert_time = state["last_alert_time"]
    last_alert_price = state["last_alert_price"]

    print(f"Loaded last alert: time={last_alert_time}, price={last_alert_price}")
    
    # get data for last working day from date_in as string
    if not date_in or date_in.strip() == "":
        last_working_day = pd.Timestamp.now(tz="America/New_York") - pd.offsets.BDay(1)
    else:
        last_working_day = pd.to_datetime(date_in) - pd.offsets.BDay(1)
    
    last_working_day = last_working_day.strftime("%Y-%m-%d")
    history = fetch_market_data(config["api"],config["runtime"]['interval_min'],date_in=last_working_day)

    print("📡 SPX 0-DTE Monitor Started...\n")

    
    while True:
        now_et = datetime.now(tz=MARKET_TZ)

        if not is_market_window(now_et) and not time_in:
            if now_et.hour < MARKET_OPEN[0] or (
                now_et.hour == MARKET_OPEN[0] and now_et.minute < MARKET_OPEN[1]
            ):
                print(f"⏳ Waiting for market window... Current ET: {now_et.strftime('%H:%M:%S')}")
                time.sleep(60)  # check every minute before open
                continue
            else:
                print(f"🔕 Market window closed at {now_et.strftime('%H:%M:%S')} ET. Shutting down.")
                break

        try:
            df = fetch_market_data(config["api"],config["runtime"]['interval_min'],date_in=date_in, time_in=time_in)

            history = pd.concat([history, df])
            history = history.tail(config["runtime"]["history_size"])

            history = add_indicators(history, config["indicators"]["rsi_period"])

            latest = history.iloc[-1]

            features = {
                "current_price": round(latest["spx"], 2),
                "expected_move": round(latest["spxExpectedMove"], 2),
                "vix": round(latest["vix"], 2),
                "rsi": round(latest["rsi"], 2),
                "macd": round(latest["macd"], 4),
                "macd_signal": round(latest["macd_signal"], 4),
                "macd_hist": round(latest["macd_hist"], 4),
                "bb_upper": round(latest["bb_upper"], 4),
                "bb_middle": round(latest["bb_middle"], 4),
                "bb_lower": round(latest["bb_lower"], 4),
                "premium_ratio": round(latest["premium_ratio"], 2),
                "time_to_close_min": int(latest["time_to_close"]),
                "current_time": latest.name.strftime("%Y-%m-%d %H:%M:%S"),
                "data": latest.to_dict()
            }


            # if time_in is is not none then increment time_in by config["runtime"]['interval_min']
            if time_in:
                t = pd.to_datetime(time_in) + pd.Timedelta(minutes=config["runtime"]['interval_min'])
                time_in = t.strftime("%H:%M:%S")


            now = latest.name
            if last_alert_time:
                minutes_since = (now - last_alert_time).total_seconds() / 60
                if minutes_since < ALERT_COOLDOWN_MINUTES:
                    print(f"⏳ Cooldown active — {minutes_since:.1f} min since last alert (need ≥ {ALERT_COOLDOWN_MINUTES})")
                    time.sleep(config["runtime"]["fetch_interval_sec"])
                    continue
                else:
                    print(f"✅ Cooldown passed — {minutes_since:.1f} min since last alert")
                    last_alert_time = None  # reset to allow new alerts
                    last_alert_price = None
                    del_last_alert_state()

            
                
            decision = evaluate_with_agent(features)

            if decision.trade and decision.confidence >= 0.7:
                send_alert(decision.model_dump(), latest)
                log_decision(decision.model_dump(), features)

                # Update persistent state
                
                last_alert_time = now
                last_alert_price = round(latest["spx"], 2)
                save_last_alert_state(last_alert_time, last_alert_price)

            else:
                print(latest.name.strftime(("%Y-%m-%d %H:%M:%S")) + " -- " + "🤖 Agent says: no clean setup.")     


        except Exception as e:
            print("❌ Error:", e)

        time.sleep(config["runtime"]["fetch_interval_sec"])


if __name__ == "__main__":
    main()
