from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class Market(BaseModel):
    id: str
    question: str
    close_time: datetime
    resolution_source: str


class Snapshot(BaseModel):
    market_id: str
    ts: datetime
    bid: Optional[float] = Field(default=None, ge=0, le=1)
    ask: Optional[float] = Field(default=None, ge=0, le=1)
    last: Optional[float] = Field(default=None, ge=0, le=1)
    volume: Optional[int] = Field(default=None, ge=0)

    @field_validator("ts", mode="before")
    @classmethod
    def _parse_ts(cls, v: int | float | datetime):
        if isinstance(v, (int, float)):
            return datetime.utcfromtimestamp(v / 1000)
        return v

    @field_validator("ask")
    @classmethod
    def ask_ge_bid(cls, v: Optional[float], info: ValidationInfo):
        bid = info.data.get("bid")
        if v is not None and bid is not None and v < bid:
            raise ValueError("ask must be >= bid")
        return v


class TradeDecision(BaseModel):
    market_id: str
    ts: datetime
    side: str  # "YES" or "NO"
    price: float = Field(ge=0, le=1)
    size: int = Field(ge=1)
    reason: str

    @field_validator("side")
    @classmethod
    def side_upper(cls, v: str):
        value = v.upper()
        if value not in {"YES", "NO"}:
            raise ValueError("side must be YES or NO")
        return value


class Outcome(BaseModel):
    market_id: str
    resolved_value: int = Field(ge=0, le=1)
    pnl: float
