from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, validator


class Market(BaseModel):
    id: str
    question: str
    close_time: datetime
    resolution_source: str


class Snapshot(BaseModel):
    market_id: str
    ts: datetime
    bid: float = Field(ge=0, le=1)
    ask: float = Field(ge=0, le=1)
    last: float = Field(ge=0, le=1)
    volume: int = Field(ge=0)

    @validator("ask")
    def ask_ge_bid(cls, v: float, values):
        bid = values.get("bid")
        if bid is not None and v < bid:
            raise ValueError("ask must be >= bid")
        return v


class TradeDecision(BaseModel):
    market_id: str
    ts: datetime
    side: str  # "YES" or "NO"
    price: float = Field(ge=0, le=1)
    size: int = Field(ge=1)
    reason: str


class Outcome(BaseModel):
    market_id: str
    resolved_value: int = Field(ge=0, le=1)
    pnl: float
