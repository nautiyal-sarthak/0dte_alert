# Example of what it might look like now (guessing from errors)
from pydantic import BaseModel, Field
from typing import List, Optional

class TradeDecision(BaseModel):
    trade: str                          # e.g. "SELL_CALL", "SELL_PUT", "NONE"
    confidence: float                   # ← this is the problem: expects number like 0.3, not "Low"
    reasons: List[str]                  # ← plural + list
    risk_flags: List[str]               # ← missing entirely
    # maybe others like strategy: Optional[str], regime_considered: Optional[str], etc.