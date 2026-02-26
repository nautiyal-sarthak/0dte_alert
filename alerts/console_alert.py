from datetime import datetime
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from tabulate import tabulate
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv
import os



load_dotenv()

# ────────────────────────────────────────────────
#               Get the values
# ────────────────────────────────────────────────
TELEGRAM_LOG_TOKEN   = os.getenv("TELEGRAM_LOG_TOKEN")
TELEGRAM_ALERT_TOKEN   = os.getenv("TELEGRAM_ALERT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ────────────────────────────────────────────────
# Configuration (tune these)
# ────────────────────────────────────────────────

STATE_FILE = Path("last_alert_state.json")

# ────────────────────────────────────────────────
# Helper functions
# ────────────────────────────────────────────────

def load_last_alert_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                last_time_str = data.get("last_alert_time")
                last_time = datetime.fromisoformat(last_time_str) if last_time_str else None
                return {
                    "last_alert_time": last_time,
                    "last_alert_price": data.get("last_alert_price"),
                }
        except Exception as e:
            print(f"⚠️ Could not load state file: {e}")
    return {"last_alert_time": None, "last_alert_price": None}


def save_last_alert_state(last_time: datetime, last_price: float):
    state = {
        "last_alert_time": last_time.isoformat() if last_time else None,
        "last_alert_price": last_price,
        "updated": datetime.now().isoformat(),
    }
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        print("💾 Saved last alert state")
    except Exception as e:
        print(f"⚠️ Failed to save state: {e}")

def del_last_alert_state():
    if STATE_FILE.exists():
        try:
            STATE_FILE.unlink()
            print("🗑️ Deleted last alert state file")
        except Exception as e:
            print(f"⚠️ Could not delete state file: {e}")


def send_alert(signal, latest):
    alert_message = "\n" + "=" * 60 + "\n"
    alert_message += f"🚨 SPX 0-DTE ALERT @ {latest.name.strftime('%Y-%m-%d %H:%M:%S')}\n"
    alert_message += "=" * 60 + "\n"
    alert_message += f"Trade Type     : {signal['trade']}\n"
    alert_message += f"Confidence     : {signal['confidence']}\n"
    alert_message += f"SPX Price      : {latest['spx']}\n"
    alert_message += f"Expected Move  : {latest['spxExpectedMove']}\n"
    alert_message += f"OTM Ratio      : {latest['premium_ratio']}\n\n"
    alert_message += "Reasons:\n"
    for r in signal["reasons"]:
        alert_message += f"  - {r}\n"
    alert_message += "=" * 60 + "\n"

    # You can now use the alert_message variable as needed
    print(alert_message)
    alert(alert_message, silent=False)


def log_decision(signal, features):
    
    log_entry = {
        "timestamp": features.get("current_time"),
        "spx_price": features.get("current_price"),
        "expected_move": features.get("expected_move"),
        "vix": features.get("vix"),
        "rsi": features.get("rsi"),
        "macd": features.get("macd"),
        "macd_signal": features.get("macd_signal"),
        "macd_hist": features.get("macd_hist"),
        "bb_upper": features.get("bb_upper"),
        "bb_middle": features.get("bb_middle"),
        "bb_lower": features.get("bb_lower"),
        "premium_ratio": features.get("premium_ratio"),
        "time_to_close_min": features.get("time_to_close_min"),
        "ema9": features.get("ema9"),
        "ema21": features.get("ema21"),
        "ema50": features.get("ema50"),
        "ema21_slope_5min": features.get("ema21_slope_5min"),
        "ema21_slope_15min": features.get("ema21_slope_15min"),
        "ema21_slope_30min": features.get("ema21_slope_30min"),
        "ret_5min_pct": features.get("ret_5min_pct"),
        "ret_15min_pct": features.get("ret_15min_pct"),
        "ret_30min_pct": features.get("ret_30min_pct"),
        "suggestion": signal["trade"],
        "confidence": signal["confidence"],
        "reasons": "; ".join(signal["reasons"]),
        "action_taken_by_you": "", #entered trade, ignored
        "result": "" #profit, loss, breakeven
    }

    df = pd.DataFrame([log_entry])

    # Populate the confidence score and reasons for the signal in a string variable
    signal_details = f"Confidence Score: {signal['confidence']}\n"
    signal_details += "Reasons for the signal:\n"

    for reason in signal["reasons"]:
        signal_details += f"- {reason}\n"

    # You can now use the signal_details variable as needed

    # Background / low priority
    alert(features.get("current_time") + "--" +  signal_details, silent=True)
    print(signal_details)

    if signal["confidence"] >= 0.5:
        # Important alert with sound
        # create a dataframe and append to csv
        log_file = Path(features.get("current_time").split(" ")[0] + "_" "alert_log.csv")
        if log_file.exists():
            df.to_csv(log_file, mode='a', header=False, index=False)
        else:
            df.to_csv(log_file, index=False)

        # print the dataframe to the console 
        #print(tabulate(df, headers='keys', tablefmt='psql'))
    

async def send_telegram_message(message: str, silent: bool = False) -> bool:
    """
    Send a message to Telegram
    Returns True if successful, False otherwise
    """
    
    if silent:
        bot = Bot(token=TELEGRAM_LOG_TOKEN)
    else:
        bot = Bot(token=TELEGRAM_ALERT_TOKEN)
    
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            disable_notification=silent,      # silent = True → no sound/vibration
            disable_web_page_preview=True,
            # You can also add: parse_mode="MarkdownV2" or "HTML"
        )
        return True
        
    except TelegramError as e:
        print(f"Telegram error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


# ────────────────────────────────────────────────
#          SYNCHRONOUS WRAPPER (easier to use)
# ────────────────────────────────────────────────
def alert(message: str, silent: bool = False) -> bool:
    """Blocking version – most people prefer this for simple scripts"""
    return asyncio.run(send_telegram_message(message, silent))