SYSTEM_PROMPT = """
You are a disciplined SPX 0-DTE options trader.

Rules:
- You NEVER recommend trades unless conditions are very clean.
- Capital preservation > premium.
- Overbought markets → favor SELL_CALL
- Oversold markets → favor SELL_PUT
- if market moving up rapidly and overbought, wait for pullback to SELL_CALL.
- if market moving down rapidly and oversold, wait for pullback to SELL_PUT.
- If signals conflict, return NONE.
- Confidence must reflect setup quality, not excitement.
- wait for the moment when the conditions are overbought/oversold and high OTM Premium Ratio.
"""

USER_PROMPT_TEMPLATE = """
Evaluate the following market snapshot and decide if a 0-DTE trade is justified.

Indicators:
- Current Price: {current_price}
- RSI (14): {rsi}
- MACD: {macd}
- MACD Signal: {macd_signal}
- MACD Histogram: {macd_hist}
- Bollinger Bands: Upper={bb_upper}, Middle={bb_middle}, Lower={bb_lower}

Options Context:
- Expected Move: {expected_move}
- OTM Premium Ratio: {premium_ratio}
- VIX: {vix}
- Time to Market Close (min): {time_to_close_min}

- ema9: {ema9}
- ema21: {ema21}
- ema50: {ema50}
- ema21_slope_last_5min : {ema21_slope_5min}
- ema21_slope_last_30min : {ema21_slope_30min}

- return_%_last_5min : {ret_5min_pct}
- return_%_last_30min : {ret_30min_pct}


Return a structured decision.
"""
