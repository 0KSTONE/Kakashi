# src/models/schemas.py
from pydantic import BaseModel, Field, validator
from datetime import datetime

class Snapshot(BaseModel):
    market_id: str
    ts: datetime
    bid: float = Field(ge=0, le=1)
    ask: float = Field(ge=0, le=1)
    last: float = Field(ge=0, le=1)
    volume: int = Field(ge=0)

    @validator('ask')
    def ask_ge_bid(cls, v, values):
        if 'bid' in values and v < values['bid']:
            raise ValueError('ask must be >= bid')
        return v

class TradeDecision(BaseModel):
    market_id: str
    ts: datetime
    side: str  # "YES" or "NO"
    price: float
    size: int
    reason: str
