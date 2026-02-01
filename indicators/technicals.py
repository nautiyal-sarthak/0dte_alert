from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import pandas as pd
import numpy as np
from ta.trend import MACD

def add_indicators(df, rsi_period=14):
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have DatetimeIndex")

    df = df.copy()  # avoid modifying original

    # RSI
    df['rsi'] = RSIIndicator(close=df['spx'], window=rsi_period).rsi()

    # MACD components
    macd_ind = MACD(close=df['spx'], window_fast=12, window_slow=26, window_sign=9)
    df['macd']       = macd_ind.macd()
    df['macd_signal'] = macd_ind.macd_signal()
    df['macd_hist']  = macd_ind.macd_diff()

    # Bollinger Bands
    bb = BollingerBands(close=df['spx'], window=20, window_dev=2)
    df['bb_upper']  = bb.bollinger_hband()
    df['bb_middle'] = bb.bollinger_mavg()
    df['bb_lower']  = bb.bollinger_lband()

    # Your custom 0DTE-related metric
    df['premium_ratio'] = df['spxOTMBids'] / df['spxExpectedMove'].replace(0, np.nan)

    # Calculate time to market close in minutes (assuming market closes at 16:00)
    df['time_to_close'] = ((16 * 60) - (df.index.hour * 60 + df.index.minute))
    
    return df