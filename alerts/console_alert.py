from datetime import datetime
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

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
    print("\n" + "=" * 60)
    #get date time string
    
    print(f"🚨 SPX 0-DTE ALERT @ {latest.name.strftime(("%Y-%m-%d %H:%M:%S"))}")
    print("=" * 60)
    print(f"Trade Type     : {signal['trade']}")
    print(f"Confidence     : {signal['confidence']}")
    print(f"SPX Price      : {latest['spx']}")
    print(f"Expected Move  : {latest['spxExpectedMove']}")
    print(f"OTM Ratio      : {latest['premium_ratio']}")
    
    print("Reasons:")
    for r in signal["reasons"]:
        print(f"  - {r}")
    print("=" * 60 + "\n")


def log_decision(signal, features):
    log_entry = {
        "timestamp": features.get("current_time"),
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
        "trade": signal["trade"],
        "confidence": signal["confidence"],
    }
    
    # create a dataframe and append to csv
    df = pd.DataFrame([log_entry])
    log_file = Path("alert_log.csv")
    if log_file.exists():
        df.to_csv(log_file, mode='a', header=False, index=False)
    else:
        df.to_csv(log_file, index=False)

