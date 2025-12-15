from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from src.data.sqlite_store import SQLiteStore
from src.models.schemas import TradeDecision
from src.strategy.threshold import size_by_risk

logger = logging.getLogger(__name__)


@dataclass
class PaperTradeResult:
    bankroll_before: float
    bankroll_after: float
    size_executed: int


class PaperTrader:
    """Simple paper-trade executor that records trades and bankroll path."""

    def __init__(self, store: SQLiteStore, initial_bankroll: float = 1000.0, risk_per_trade: float = 0.01):
        self.store = store
        self.risk_per_trade = risk_per_trade
        self.store.ensure_bankroll_initialized(initial_bankroll)

    def execute_trade(self, decision: TradeDecision) -> PaperTradeResult | None:
        bankroll = self.store.get_latest_bankroll()
        max_size = size_by_risk(bankroll, self.risk_per_trade, decision.price)
        size = min(max_size, decision.size)
        if size <= 0:
            logger.info("Skipping trade for %s; size zero after risk checks", decision.market_id)
            return None

        cost = decision.price * size
        bankroll_after = bankroll - cost
        ts_ms = int(decision.ts.timestamp() * 1000)

        self.store.record_trade(decision, pnl=0.0, size=size, ts_ms=ts_ms)
        self.store.record_bankroll(bankroll_after, ts_ms=ts_ms)

        logger.info(
            "Paper trade executed: market=%s side=%s size=%s price=%.3f bankroll_before=%.2f bankroll_after=%.2f",
            decision.market_id,
            decision.side,
            size,
            decision.price,
            bankroll,
            bankroll_after,
        )
        return PaperTradeResult(bankroll_before=bankroll, bankroll_after=bankroll_after, size_executed=size)


def simulate_fill(market_id: str, side: str, price: float, size: int, reason: str = "") -> TradeDecision:
    return TradeDecision(
        market_id=market_id,
        ts=datetime.utcnow(),
        side=side,
        price=price,
        size=size,
        reason=reason or "manual_simulation",
    )
