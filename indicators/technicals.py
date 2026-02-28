from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.trend import MACD
import pandas as pd
import numpy as np


def add_indicators(df, rsi_period=14):
    """
    Adds standard technical indicators + context / regime features
    to help detect trend strength, exhaustion, crash/rally/chop regimes, etc.
    
    Assumes:
    - df has DatetimeIndex
    - 30-second SPX bars
    - columns: 'spx', 'spxExpectedMove', 'spxOTMBids', ...
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have DatetimeIndex")

    df = df.copy()  # avoid modifying original

    # ───────────────────────────────────────────────
    # 1. Standard indicators (your original ones)
    # ───────────────────────────────────────────────
    df['rsi'] = RSIIndicator(close=df['spx'], window=rsi_period).rsi()

    macd_ind = MACD(close=df['spx'], window_fast=12, window_slow=26, window_sign=9)
    df['macd']       = macd_ind.macd()
    df['macd_signal'] = macd_ind.macd_signal()
    df['macd_hist']  = macd_ind.macd_diff()

    bb = BollingerBands(close=df['spx'], window=20, window_dev=2)
    df['bb_upper']   = bb.bollinger_hband()
    df['bb_middle']  = bb.bollinger_mavg()
    df['bb_lower']   = bb.bollinger_lband()

    # Premium ratio: how expensive are OTM options relative to expected move?
    df['premium_ratio'] = df['spxOTMBids'] / df['spxExpectedMove'].replace(0, np.nan)

    # Time to close (assuming 16:00 ET close)
    df['time_to_close'] = (16 * 60) - (df.index.hour * 60 + df.index.minute)


    # ───────────────────────────────────────────────
    # 2. Context / lookback features (the important part)
    # ───────────────────────────────────────────────

    # EMAs — common reference levels
    df['ema9']   = df['spx'].ewm(span=9,  adjust=False).mean()
    df['ema21']  = df['spx'].ewm(span=21, adjust=False).mean()
    df['ema50']  = df['spx'].ewm(span=50, adjust=False).mean()
    

    # EMA slope / momentum (positive = rising, negative = falling)
    # scaled roughly to per-minute change
    df['ema21_slope_5min']  = df['ema21'].diff(1) / 5     # 5 min = 1 row
    df['ema21_slope_15min'] = df['ema21'].diff(3) / 15    # 15 min = 3 rows
    df['ema21_slope_30min'] = df['ema21'].diff(6) / 30    # 30 min = 6 rows

    # Recent returns (very interpretable for "keeps falling / rising")
    df['ret_5min']   = df['spx'].pct_change(1)            # 5 min = 1 row
    df['ret_15min']  = df['spx'].pct_change(3)            # 15 min = 3 rows
    df['ret_30min']  = df['spx'].pct_change(6)            # 30 min = 6 rows

    return df