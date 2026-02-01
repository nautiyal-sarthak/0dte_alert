from pydantic import BaseModel
from typing import List, Optional

class TradeDecision(BaseModel):
    trade: Optional[str]  # SELL_CALL, SELL_PUT, NONE
    confidence: float     # 0.0 - 1.0
    reasons: List[str]
    risk_flags: List[str]
